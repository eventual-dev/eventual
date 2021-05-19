import uuid
from typing import Any, AsyncContextManager, Dict, cast

from eventual.abc.router import Guarantee, IntegrityGuard
from eventual.model import EventPayload
from tests.memory.work_unit import MemoryWorkUnit


class MemoryIntegrityGuard(IntegrityGuard[MemoryWorkUnit]):
    def __init__(self) -> None:
        self._handled_event_from_id: Dict[uuid.UUID, Dict[str, Any]] = {}
        self._dispatched_event_from_id: Dict[uuid.UUID, Dict[str, Any]] = {}

    def create_work_unit(self) -> AsyncContextManager[MemoryWorkUnit]:
        return MemoryWorkUnit.create()

    async def is_dispatch_forbidden(self, event_id: uuid.UUID) -> bool:
        return event_id in self._handled_event_from_id

    async def record_completion_with_guarantee(
        self, event_payload: EventPayload, guarantee: Guarantee
    ) -> uuid.UUID:
        event_id = event_payload.id
        if event_id in self._handled_event_from_id:
            raise ValueError

        self._handled_event_from_id[event_id] = dict(
            id=event_id, payload=event_payload, guarantee=guarantee
        )
        return event_id

    async def record_dispatch_attempt(self, event_payload: EventPayload) -> uuid.UUID:
        event_id = event_payload.id
        entry = {"payload": event_payload, " event_id": event_id}
        entry = self._dispatched_event_from_id.setdefault(event_id, entry)
        entry["__count__"] = cast(int, entry.get("__count__", 0)) + 1
        return event_id
