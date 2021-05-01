import abc
import datetime as dt
import enum
import uuid
from typing import (
    Any,
    Dict,
    AsyncContextManager,
    List,
    Iterable,
    AsyncIterable,
    Callable,
    Awaitable,
    Optional,
)

from eventual.model import Entity, EventBody


class Message(abc.ABC):
    @property
    @abc.abstractmethod
    def body(self) -> EventBody:
        raise NotImplementedError

    @abc.abstractmethod
    def acknowledge(self):
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.body["id"]


class MessageExchange(abc.ABC):
    @abc.abstractmethod
    async def send_event_body_stream(self, event_body_stream: AsyncIterable[EventBody]):
        raise NotImplementedError

    @abc.abstractmethod
    async def message_stream(self) -> AsyncIterable[Message]:
        raise NotImplementedError


class MessageDispatcher(abc.ABC):
    @abc.abstractmethod
    async def dispatch_from_stream(self, message_stream: AsyncIterable[Message]):
        raise NotImplementedError

    @abc.abstractmethod
    async def dispatch_from_exchange(self, message_exchange: MessageExchange):
        raise NotImplementedError

    @abc.abstractmethod
    def register(
        self, event_type_seq: List[str], fn: Callable[[Message], Awaitable[None]]
    ):
        raise NotImplementedError

    def subscribe(
        self, event_type_seq: List[str]
    ) -> Callable[
        [Callable[[Message], Awaitable[None]]], Callable[[Message], Awaitable[None]]
    ]:
        def decorator(fn: Callable[[Message], Awaitable[None]]):
            self.register(event_type_seq, fn)
            return fn

        return decorator


class ProcessingGuarantee(str, enum.Enum):
    NO_MORE_THAN_ONCE = "NO_MORE_THAN_ONCE"
    EXACTLY_ONCE = "EXACTLY_ONCE"
    AT_LEAST_ONCE = "AT_LEAST_ONCE"


class EventStorage(abc.ABC):
    @abc.abstractmethod
    def clear_outbox_atomically(self, *entity_seq: Entity) -> AsyncContextManager[None]:
        raise NotImplementedError

    async def clear_outbox(self, entity_seq: Iterable[Entity]):
        for entity in entity_seq:
            # Make a copy because during asynchronous processing
            # someone can add messages to the outbox.
            event_seq = entity.clear_outbox()
            # One may think that the order, in which the events are written here,
            # is important for sourcing the events later. In reality every event has a timestamp, which dictates
            # its position in the sequence.
            for event in event_seq:
                await self.schedule_event_out(
                    event_id=event.id, body=event.encode_body()
                )
            if entity.outbox:
                raise ValueError("writing to outbox after clearing loses events")

    @abc.abstractmethod
    async def schedule_event_out(
        self,
        event_id: uuid.UUID,
        body: EventBody,
        send_after: Optional[dt.datetime] = None,
    ):
        raise NotImplementedError

    @abc.abstractmethod
    async def is_event_handled(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_handled(
        self,
        event_body: EventBody,
        guarantee: ProcessingGuarantee,
    ) -> uuid.UUID:
        raise NotImplementedError

    @abc.abstractmethod
    async def mark_event_dispatched(self, event_body: EventBody) -> uuid.UUID:
        raise NotImplementedError

    @abc.abstractmethod
    def handle_exactly_once(self, message: Message) -> AsyncContextManager[EventBody]:
        raise NotImplementedError

    @abc.abstractmethod
    def handle_no_more_than_once(
        self, message: Message
    ) -> AsyncContextManager[EventBody]:
        raise NotImplementedError

    @abc.abstractmethod
    def handle_at_least_once(self, message: Message) -> AsyncContextManager[EventBody]:
        raise NotImplementedError

    @abc.abstractmethod
    def event_body_stream(self) -> AsyncIterable[EventBody]:
        raise NotImplementedError
