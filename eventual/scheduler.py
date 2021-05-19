import abc
import datetime as dt

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from eventual import util
from eventual.abc.schedule import EventSchedule, EventScheduler
from eventual.abc.work_unit import WU
from eventual.model import EventPayload


async def enqueue_after_delay(
    event_payload_send_stream: MemoryObjectSendStream[EventPayload],
    event_payload: EventPayload,
    delay: float,
) -> None:
    async with event_payload_send_stream:
        await anyio.sleep(delay)
        await event_payload_send_stream.send(event_payload)


class Scheduler(EventScheduler[WU], abc.ABC):
    def __init__(
        self,
        event_body_send_stream: MemoryObjectSendStream[EventPayload],
        event_schedule: EventSchedule[WU],
        task_group: TaskGroup,
    ):
        super().__init__(event_body_send_stream, event_schedule)
        self.task_group = task_group

    async def schedule_event(
        self,
        event_payload: EventPayload,
        delay: float = 0.0,
    ) -> None:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay)
        await self._event_schedule.add_claimed_event_entry(event_payload, send_after)
        self.task_group.start_soon(
            enqueue_after_delay,
            self.event_payload_send_stream.clone(),
            event_payload,
            delay,
        )
        await self.schedule_every_open_unclaimed_event_entry_due_now()

    async def schedule_every_open_unclaimed_event_entry_due_now(
        self,
    ) -> None:
        async for event_payload in self._event_schedule.every_open_unclaimed_event_entry_due_now():
            delay = 0.0
            self.task_group.start_soon(
                enqueue_after_delay,
                self.event_payload_send_stream.clone(),
                event_payload,
                delay,
            )
