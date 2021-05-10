import abc
import datetime as dt

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from eventual import util
from eventual.event_store import EventSendStore
from eventual.model import EventBody
from eventual.work_unit import WU


async def enqueue_after_delay(
    event_body_send_stream: MemoryObjectSendStream[EventBody],
    event_body: EventBody,
    delay: float,
) -> None:
    async with event_body_send_stream:
        await anyio.sleep(delay)
        await event_body_send_stream.send(event_body)


class ConcurrentEventSendStore(EventSendStore[WU], abc.ABC):
    def __init__(
        self,
        event_body_send_stream: MemoryObjectSendStream[EventBody],
        task_group: TaskGroup,
    ):
        super().__init__(event_body_send_stream)
        self.task_group = task_group

    async def schedule_event_to_be_sent(
        self,
        event_body: EventBody,
        delay: float = 0.0,
    ) -> None:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay)
        await self._write_event_being_scheduled(event_body, send_after)
        self.task_group.start_soon(
            enqueue_after_delay, self.event_body_send_stream.clone(), event_body, delay
        )
        await self.schedule_every_written_event_to_be_sent()
