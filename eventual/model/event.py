import dataclasses
import datetime as dt
import re
import uuid
from typing import Any, Dict

from eventual import util


def _kebab_from_camel(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


@dataclasses.dataclass(frozen=True)
class EventPayload:
    id: uuid.UUID
    occurred_on: dt.datetime
    subject: str
    body: Dict[str, Any]

    @classmethod
    def from_event_body(cls, event_body: Dict[str, Any]) -> "EventPayload":
        event_id = event_body["id"]
        occurred_on = event_body["occurred_on"]
        if isinstance(event_id, str):
            event_id = uuid.UUID(event_id)
        if isinstance(occurred_on, str):
            occurred_on = dt.datetime.fromisoformat(occurred_on)
        return cls(
            id=event_id,
            occurred_on=occurred_on,
            subject=event_body["_subject"],
            body=event_body,
        )

    @classmethod
    def from_event(cls, event: "Event") -> "EventPayload":
        body = dataclasses.asdict(event)
        subject = _kebab_from_camel(type(event).__name__)
        body["_subject"] = subject
        return EventPayload(
            id=event.id,
            occurred_on=event.occurred_on,
            subject=subject,
            body=body,
        )


@dataclasses.dataclass(frozen=True)
class Event:
    id: uuid.UUID = dataclasses.field(init=False, default_factory=uuid.uuid4)
    occurred_on: dt.datetime = dataclasses.field(
        init=False, default_factory=util.tz_aware_utcnow
    )

    # I really want to keep events as simple as possible.
    # Events in `eventsourcing` have `.apply(entity)` and I don't know how I feel about that.
    # TODO: Does it make sense for event to be produced by different kinds of entities?
    # If yes, then `.apply(entity)` can become very messy and separate entities behavior from its class definition.
