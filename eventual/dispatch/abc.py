import abc
import datetime as dt
import enum
import uuid
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncGenerator,
    AsyncIterable,
    Awaitable,
    Callable,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
)

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.model import Entity, EventBody
from eventual.work_unit import WorkUnit

WU = TypeVar("WU", bound=WorkUnit)


class Message(abc.ABC):
    @property
    def event_id(self) -> uuid.UUID:
        return uuid.UUID(self.event_body["id"])

    @property
    def event_subject(self) -> str:
        return self.event_body["_subject"]

    @property
    @abc.abstractmethod
    def event_body(self) -> EventBody:
        raise NotImplementedError

    @abc.abstractmethod
    def acknowledge(self) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.event_id}/{self.event_subject}"


class MessageBroker(abc.ABC):
    @abc.abstractmethod
    async def send_event_body_stream(
        self,
        event_body_stream: MemoryObjectReceiveStream[EventBody],
        confirmation_send_stream: MemoryObjectSendStream[EventBody],
    ) -> None:
        # We could be more general and say that event_body_stream is an AsyncIterable, but memory streams
        # have ability to do a clean shutdown, which is convenient.
        raise NotImplementedError

    @abc.abstractmethod
    async def message_receive_stream(self) -> AsyncIterable[Message]:
        raise NotImplementedError


class EventStore(abc.ABC, Generic[WU]):
    @abc.abstractmethod
    def create_work_unit(self) -> AsyncContextManager[WU]:
        raise NotImplementedError


class EventSendStore(EventStore[WU]):
    def __init__(self, event_body_send_stream: MemoryObjectSendStream[EventBody]) -> None:
        self.event_body_send_stream = event_body_send_stream

        confirmation_stream_pair: Tuple[
            MemoryObjectSendStream[EventBody], MemoryObjectReceiveStream[EventBody]
        ] = anyio.create_memory_object_stream()
        (
            self.confirmation_send_stream,
            self._confirmation_stream,
        ) = confirmation_stream_pair

    @abc.abstractmethod
    async def _write_event_to_send_soon(
        self, event_body: EventBody, send_after: Optional[dt.datetime] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def _mark_event_as_sent(self, event_body: EventBody) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def schedule_event_to_send(
        self,
        event_body: EventBody,
        delay: float = 0.0,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def schedule_every_written_event_to_send(
        self,
    ) -> None:
        raise NotImplementedError

    async def receive_confirmation_stream(self) -> None:
        async with self._confirmation_stream:
            async for event_body in self._confirmation_stream:
                await self._mark_event_as_sent(event_body)

    async def clear_outbox(self, entity_seq: Iterable[Entity[Any]]) -> None:
        for entity in entity_seq:
            # Make a copy because during asynchronous processing
            # someone can add messages to the outbox.
            event_seq = entity.clear_outbox()
            # One may think that the order, in which the events are written here,
            # is important for sourcing the events later. In reality every event has a timestamp, which dictates
            # its position in the sequence.
            # TODO: Maybe timestamp data is not reliable enough in the context of tracking changes to entities.
            # For such purposes we would have to store origin of the message.
            # TODO: It could be better to explicitly use the stream here to achieve clean shutdown.
            for event in event_seq:
                await self.schedule_event_to_send(event_body=event.encode_body())
            if entity.outbox:
                raise ValueError("writing to outbox after clearing loses events")

    @asynccontextmanager
    async def clear_outbox_in_work_unit(
        self, *entity_seq: Entity[Any]
    ) -> AsyncGenerator[WU, None]:
        async with self.create_work_unit() as work_unit:
            yield work_unit
            await self.clear_outbox(entity_seq)


class Guarantee(str, enum.Enum):
    NO_MORE_THAN_ONCE = "NO_MORE_THAN_ONCE"
    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"


class EventReceiveStore(EventStore[WU]):
    @abc.abstractmethod
    async def is_event_handled(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_as_handled(
        self,
        event_body: EventBody,
        guarantee: Guarantee,
    ) -> uuid.UUID:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_as_dispatched(self, event_body: EventBody) -> uuid.UUID:
        raise NotImplementedError

    @asynccontextmanager
    async def handle_exactly_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        async with self.create_work_unit():
            yield message.event_body
            await self.mark_event_as_handled(
                message.event_body, guarantee=Guarantee.EXACTLY_ONCE
            )
        message.acknowledge()

    @asynccontextmanager
    async def handle_no_more_than_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        await self.mark_event_as_handled(
            message.event_body, guarantee=Guarantee.NO_MORE_THAN_ONCE
        )
        message.acknowledge()
        yield message.event_body

    @asynccontextmanager
    async def handle_at_least_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        yield message.event_body
        await self.mark_event_as_handled(
            message.event_body, guarantee=Guarantee.AT_LEAST_ONCE
        )
        message.acknowledge()


MessageHandler = Callable[[Message, EventSendStore[WU]], Awaitable[None]]
HandlerSpecification = Tuple[MessageHandler[WU], Guarantee, float]


class HandlerRegistry(abc.ABC, Generic[WU]):
    @abc.abstractmethod
    def register(
        self,
        subject_seq: List[str],
        handler: MessageHandler[WU],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def mapping(self) -> Mapping[str, HandlerSpecification[WU]]:
        raise NotImplementedError

    def subscribe(
        self,
        event_type_seq: List[str],
        guarantee: Guarantee = Guarantee.AT_LEAST_ONCE,
        delay_on_exc: float = 1.0,
    ) -> Callable[[MessageHandler[WU]], MessageHandler[WU]]:
        def decorator(handler: MessageHandler[WU]) -> MessageHandler[WU]:
            self.register(event_type_seq, handler, guarantee, delay_on_exc)
            return handler

        return decorator


class MessageDispatcher(abc.ABC):
    @abc.abstractmethod
    async def dispatch_from_broker(
        self,
        handler_registry: HandlerRegistry[WU],
        message_broker: MessageBroker,
        event_receive_store: EventReceiveStore[WU],
        event_send_store: EventSendStore[WU],
    ) -> None:
        raise NotImplementedError
