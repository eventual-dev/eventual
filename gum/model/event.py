import dataclasses
import datetime as dt
import re
from typing import Dict, Any
import uuid

from gum import util

EventBody = Dict[str, Any]


def _kebab_from_camel(s: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", s).lower()


@dataclasses.dataclass(frozen=True)
class Event:
    id: uuid.UUID = dataclasses.field(init=False, default_factory=uuid.uuid4)
    occurred_on: dt.datetime = dataclasses.field(
        init=False, default_factory=util.tz_aware_utcnow
    )

    def encode_body(self) -> EventBody:
        mapping = dataclasses.asdict(self)
        mapping["type"] = re.sub(r"(?<!^)(?=[A-Z])", "-", type(self).__name__).lower()
        return mapping
