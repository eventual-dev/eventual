import dataclasses
import datetime as dt
import re
import uuid
from typing import Any, Dict

from eventual import util

EventBody = Dict[str, Any]


def _kebab_from_camel(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


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

    def encode_body(self) -> EventBody:
        mapping = dataclasses.asdict(self)
        mapping["_subject"] = re.sub(
            r"(?<!^)(?=[A-Z])", "-", type(self).__name__
        ).lower()
        return mapping
