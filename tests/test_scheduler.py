import contextlib
from typing import AsyncGenerator

import anyio
import pytest
from anyio.streams.memory import MemoryObjectSendStream

from eventual.abc.schedule import EventSchedule
from eventual.model import EventPayload
from tests.memory.scheduler import MemoryScheduler
from tests.memory.work_unit import MemoryWorkUnit
from tests.model import Person, SomethingHappened

EVENT_COUNT = 3

pytestmark = pytest.mark.anyio


@contextlib.asynccontextmanager
async def background_scheduler(
    event_schedule: EventSchedule[MemoryWorkUnit],
    event_payload_send_stream: MemoryObjectSendStream[EventPayload],
    receive_confirmation_stream: bool = False,
) -> AsyncGenerator[MemoryScheduler, None]:
    async def _producer(event_body_count: int) -> None:
        async with event_payload_send_stream:
            for _ in range(event_body_count):
                await scheduler.schedule_event(
                    EventPayload.from_event(SomethingHappened())
                )

    scheduler = MemoryScheduler(event_payload_send_stream, event_schedule)

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_producer, EVENT_COUNT)
        if receive_confirmation_stream:
            task_group.start_soon(scheduler.receive_confirmation_stream)
        yield scheduler


async def test_scheduler_schedules_every_event(
    event_schedule: EventSchedule,
) -> None:
    (
        event_payload_send_stream,
        event_payload_stream,
    ) = anyio.create_memory_object_stream()

    async with background_scheduler(event_schedule, event_payload_send_stream):
        event_body_seq = []
        async with event_payload_stream:
            async for event_body in event_payload_stream:
                event_body_seq.append(event_body)
            assert len(event_body_seq) == EVENT_COUNT


async def test_scheduler_clear_outbox(
    event_schedule: EventSchedule, person: Person
) -> None:
    event_payload_send_stream, event_payload_stream = anyio.create_memory_object_stream(
        EVENT_COUNT
    )

    scheduler = MemoryScheduler(event_payload_send_stream, event_schedule)
    event_payload_seq = []
    async with event_payload_send_stream:
        async with scheduler.schedule_outbox_in_work_unit(person):
            for _ in range(EVENT_COUNT):
                person.new_day()
        person.new_day()
        assert len(person.outbox) == 1
    async with event_payload_stream:
        async for event_payload in event_payload_stream:
            event_payload_seq.append(event_payload)
        assert len(event_payload_seq) == EVENT_COUNT


async def test_scheduler_marks_confirmed_events_as_sent(
    event_schedule: EventSchedule,
) -> None:
    (
        event_payload_send_stream,
        event_payload_stream,
    ) = anyio.create_memory_object_stream()

    async with background_scheduler(
        event_schedule, event_payload_send_stream, True
    ) as scheduler:
        event_payload_seq = []
        async with event_payload_stream:
            async for event_payload in event_payload_stream:
                event_payload_seq.append(event_payload)
        for event_payload in event_payload_seq:
            assert not await event_schedule.is_event_entry_closed(event_payload.id)

        async with scheduler.confirmation_send_stream:
            for event_payload in event_payload_seq:
                await scheduler.confirmation_send_stream.send(event_payload)

        await anyio.sleep(0.1)

        for event_payload in event_payload_seq:
            assert await event_schedule.is_event_entry_closed(event_payload.id)
