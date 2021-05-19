import datetime as dt
import uuid
from typing import Any, AsyncContextManager, AsyncIterable, Dict, Optional

from anyio.streams.memory import MemoryObjectSendStream

from eventual import util
from eventual.abc.schedule import EventSchedule, EventScheduler
from eventual.model import EventPayload
from tests.memory.work_unit import MemoryWorkUnit


class MemoryEventSchedule(EventSchedule[MemoryWorkUnit]):
    def __init__(self, claim_duration: float) -> None:
        super().__init__(claim_duration)
        self._event_entry_from_event_id: Dict[uuid.UUID, Dict[str, Any]] = {}

    def create_work_unit(self) -> AsyncContextManager[MemoryWorkUnit]:
        return MemoryWorkUnit.create()

    async def add_claimed_event_entry(
        self, event_payload: EventPayload, due_after: Optional[dt.datetime] = None
    ) -> None:
        self._event_entry_from_event_id[event_payload.id] = dict(
            event_payload=event_payload,
            claimed_at=util.tz_aware_utcnow(),
            due_after=due_after,
            closed=False,
        )

    async def is_event_entry_closed(self, event_id: uuid.UUID) -> bool:
        event = self._event_entry_from_event_id[event_id]
        return event["closed"]

    async def close_event_entry(self, event_id: uuid.UUID) -> None:
        event = self._event_entry_from_event_id[event_id]
        event["closed"] = True

    async def is_event_entry_claimed(self, event_id: uuid.UUID) -> bool:
        raise NotImplementedError

    def every_open_unclaimed_event_entry_due_now(self) -> AsyncIterable[EventPayload]:
        raise NotImplementedError


class MemoryScheduler(EventScheduler[MemoryWorkUnit]):
    def __init__(
        self,
        event_payload_send_stream: MemoryObjectSendStream[EventPayload],
        event_schedule: EventSchedule[MemoryWorkUnit],
    ):
        super().__init__(event_payload_send_stream, event_schedule)
        self._scheduled_event_body_from_id: Dict[uuid.UUID, Dict[str, Any]] = {}

    async def schedule_event(
        self, event_payload: EventPayload, delay: float = 0.0
    ) -> None:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay)
        await self._event_schedule.add_claimed_event_entry(event_payload, send_after)
        self._scheduled_event_body_from_id[event_payload.id] = dict(
            event_payload=event_payload, delay=delay
        )
        await self.event_payload_send_stream.send(event_payload)

    async def schedule_every_open_unclaimed_event_entry_due_now(self) -> None:
        raise NotImplementedError
