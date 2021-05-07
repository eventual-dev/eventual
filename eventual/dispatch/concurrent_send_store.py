import abc
import datetime as dt

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectSendStream

from eventual import util
from eventual.dispatch.abc import WU, EventSendStore
from eventual.model import EventBody


class ConcurrentEventSendStore(EventSendStore[WU], abc.ABC):
    def __init__(
            self,
            event_body_send_stream: MemoryObjectSendStream[EventBody],
            task_group: TaskGroup,
    ):
        super().__init__(event_body_send_stream)
        self.task_group = task_group

    async def enqueue_to_send_after_delay(
            self, event_body: EventBody, delay: float
    ) -> None:
        await anyio.sleep(delay)
        await self.event_body_send_stream.send(event_body)

    async def schedule_event_to_send(
            self,
            event_body: EventBody,
            delay: float = 0.0,
    ) -> None:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay)
        await self._write_event_to_send_soon(event_body, send_after)
        self.task_group.start_soon(self.enqueue_to_send_after_delay, event_body, delay)