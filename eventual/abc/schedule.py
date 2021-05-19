import abc
import datetime as dt
import uuid
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncGenerator,
    AsyncIterable,
    Generic,
    Iterable,
    Optional,
    Tuple,
)

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.model import Entity, EventPayload

from .work_unit import WU


class EventSchedule(abc.ABC, Generic[WU]):
    def __init__(self, claim_duration: float):
        self.claim_duration = claim_duration

    @abc.abstractmethod
    def create_work_unit(self) -> AsyncContextManager[WU]:
        raise NotImplementedError

    @abc.abstractmethod
    async def add_claimed_event_entry(
        self, event_payload: EventPayload, due_after: Optional[dt.datetime] = None
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def is_event_entry_claimed(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def every_open_unclaimed_event_entry_due_now(
        self,
    ) -> AsyncIterable[EventPayload]:
        raise NotImplementedError

    @abc.abstractmethod
    async def is_event_entry_closed(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def close_event_entry(self, event_id: uuid.UUID) -> None:
        raise NotImplementedError


class EventScheduler(Generic[WU]):
    def __init__(
        self,
        event_payload_send_stream: MemoryObjectSendStream[EventPayload],
        event_schedule: EventSchedule[WU],
    ) -> None:
        self.event_payload_send_stream = event_payload_send_stream
        self._event_schedule = event_schedule

        confirmation_stream_pair: Tuple[
            MemoryObjectSendStream[EventPayload],
            MemoryObjectReceiveStream[EventPayload],
        ] = anyio.create_memory_object_stream()
        (
            self.confirmation_send_stream,
            self._confirmation_stream,
        ) = confirmation_stream_pair

    @abc.abstractmethod
    async def schedule_event(
        self,
        event_payload: EventPayload,
        delay: float = 0.0,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def schedule_every_open_unclaimed_event_entry_due_now(
        self,
    ) -> None:
        raise NotImplementedError

    async def receive_confirmation_stream(self) -> None:
        async with self._confirmation_stream:
            async for event_payload in self._confirmation_stream:
                await self._event_schedule.close_event_entry(event_payload.id)

    async def schedule_outbox(self, entity_seq: Iterable[Entity[Any]]) -> None:
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
                await self.schedule_event(event_payload=EventPayload.from_event(event))

    @asynccontextmanager
    async def schedule_outbox_in_work_unit(
        self, *entity_seq: Entity[Any]
    ) -> AsyncGenerator[WU, None]:
        async with self._event_schedule.create_work_unit() as work_unit:
            yield work_unit
            await self.schedule_outbox(entity_seq)
