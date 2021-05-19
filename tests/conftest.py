from typing import Any

import pytest

from eventual.abc.router import IntegrityGuard
from eventual.abc.schedule import EventSchedule
from eventual.model import Event, EventPayload
from eventual.registry import Registry
from tests.memory.integrity_guard import MemoryIntegrityGuard
from tests.memory.scheduler import MemoryEventSchedule
from tests.memory.work_unit import MemoryWorkUnit
from tests.model import Person, SomethingHappened


@pytest.fixture
def event() -> SomethingHappened:
    return SomethingHappened()


@pytest.fixture
def person() -> Person:
    return Person.create()


@pytest.fixture
def event_payload(event: Event) -> EventPayload:
    return EventPayload.from_event(event)


@pytest.fixture
def registry() -> Registry[Any]:
    return Registry[Any]()


@pytest.fixture
async def event_schedule() -> EventSchedule[MemoryWorkUnit]:
    return MemoryEventSchedule(1.0)


@pytest.fixture
async def integrity_guard() -> IntegrityGuard[MemoryWorkUnit]:
    return MemoryIntegrityGuard()
