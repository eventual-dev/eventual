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
    Optional,
    TypeVar,
)

from eventual.model import Entity, EventBody
from eventual.work_unit import WorkUnit


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
        self, event_body_stream: AsyncIterable[EventBody]
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def message_stream(self) -> AsyncIterable[Message]:
        raise NotImplementedError


class Guarantee(str, enum.Enum):
    NO_MORE_THAN_ONCE = "NO_MORE_THAN_ONCE"
    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"


class MessageDispatcher(abc.ABC):
    @abc.abstractmethod
    async def dispatch_from_stream(
        self, message_stream: AsyncIterable[Message]
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def dispatch_from_exchange(self, message_exchange: MessageBroker) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def register(
        self,
        event_type_seq: List[str],
        fn: Callable[[Message], Awaitable[None]],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        raise NotImplementedError

    def subscribe(
        self,
        event_type_seq: List[str],
        guarantee: Guarantee = Guarantee.AT_LEAST_ONCE,
        delay_on_exc: float = 1.0,
    ) -> Callable[
        [Callable[[Message], Awaitable[None]]], Callable[[Message], Awaitable[None]]
    ]:
        def decorator(
            fn: Callable[[Message], Awaitable[None]]
        ) -> Callable[[Message], Awaitable[None]]:
            self.register(event_type_seq, fn, guarantee, delay_on_exc)
            return fn

        return decorator


WU = TypeVar("WU", bound=WorkUnit)


class EventStore(abc.ABC, Generic[WU]):
    @abc.abstractmethod
    def create_work_unit(self) -> AsyncContextManager[WU]:
        raise NotImplementedError

    async def clear_outbox(self, entity_seq: Iterable[Entity[Any]]) -> None:
        for entity in entity_seq:
            # Make a copy because during asynchronous processing
            # someone can add messages to the outbox.
            event_seq = entity.clear_outbox()
            # One may think that the order, in which the events are written here,
            # is important for sourcing the events later. In reality every event has a timestamp, which dictates
            # its position in the sequence.
            for event in event_seq:
                await self.schedule_event_out(event_body=event.encode_body())
            if entity.outbox:
                raise ValueError("writing to outbox after clearing loses events")

    @asynccontextmanager
    async def clear_outbox_in_work_unit(
        self, *entity_seq: Entity[Any]
    ) -> AsyncGenerator[WU, None]:
        async with self.create_work_unit() as work_unit:
            yield work_unit
            await self.clear_outbox(entity_seq)

    @abc.abstractmethod
    async def schedule_event_out(
        self,
        event_body: EventBody,
        send_after: Optional[dt.datetime] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def is_event_handled(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_handled(
        self,
        event_body: EventBody,
        guarantee: Guarantee,
    ) -> uuid.UUID:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_dispatched(self, event_body: EventBody) -> uuid.UUID:
        raise NotImplementedError

    @asynccontextmanager
    async def handle_exactly_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        async with self.create_work_unit():
            yield message.event_body
            await self.mark_event_handled(
                message.event_body, guarantee=Guarantee.EXACTLY_ONCE
            )
        message.acknowledge()

    @asynccontextmanager
    async def handle_no_more_than_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        await self.mark_event_handled(
            message.event_body, guarantee=Guarantee.NO_MORE_THAN_ONCE
        )
        message.acknowledge()
        yield message.event_body

    @asynccontextmanager
    async def handle_at_least_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        yield message.event_body
        await self.mark_event_handled(
            message.event_body, guarantee=Guarantee.AT_LEAST_ONCE
        )
        message.acknowledge()

    @abc.abstractmethod
    def event_body_stream(self) -> AsyncIterable[EventBody]:
        raise NotImplementedError
