import abc
import uuid
from contextlib import asynccontextmanager
from typing import AsyncContextManager, AsyncGenerator, Generic

from eventual.model import EventPayload

from .broker import Message, MessageBroker
from .guarantee import Guarantee
from .registry import HandlerRegistry
from .schedule import EventScheduler
from .work_unit import WU


class IntegrityGuard(abc.ABC, Generic[WU]):
    @abc.abstractmethod
    def create_work_unit(self) -> AsyncContextManager[WU]:
        raise NotImplementedError

    @abc.abstractmethod
    async def is_dispatch_forbidden(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def record_completion_with_guarantee(
        self,
        event_payload: EventPayload,
        guarantee: Guarantee,
    ) -> uuid.UUID:
        raise NotImplementedError

    @abc.abstractmethod
    async def record_dispatch_attempt(self, event_payload: EventPayload) -> uuid.UUID:
        raise NotImplementedError

    @asynccontextmanager
    async def handle_exactly_once(
        self, message: Message
    ) -> AsyncGenerator[EventPayload, None]:
        async with self.create_work_unit() as _:
            yield message.event_payload
            await self.record_completion_with_guarantee(
                message.event_payload, guarantee=Guarantee.EXACTLY_ONCE
            )
        message.acknowledge()

    @asynccontextmanager
    async def handle_no_more_than_once(
        self, message: Message
    ) -> AsyncGenerator[EventPayload, None]:
        await self.record_completion_with_guarantee(
            message.event_payload, guarantee=Guarantee.NO_MORE_THAN_ONCE
        )
        message.acknowledge()
        yield message.event_payload

    @asynccontextmanager
    async def handle_at_least_once(
        self, message: Message
    ) -> AsyncGenerator[EventPayload, None]:
        yield message.event_payload
        await self.record_completion_with_guarantee(
            message.event_payload, guarantee=Guarantee.AT_LEAST_ONCE
        )
        message.acknowledge()


class MessageRouter(abc.ABC):
    @abc.abstractmethod
    async def dispatch_from_broker(
        self,
        handler_registry: HandlerRegistry[WU],
        message_broker: MessageBroker,
        integrity_guard: IntegrityGuard[WU],
        scheduler: EventScheduler[WU],
    ) -> None:
        raise NotImplementedError
