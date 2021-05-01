from typing import Dict, Any

import orjson
from tortoise import fields, Model
from tortoise.indexes import Index

from eventual.infra import mixin
from eventual.infra.exchange.abc import ProcessingGuarantee


class PkUuidModel(Model):
    id = fields.UUIDField(pk=True)

    class Meta:
        abstract = True


def _dump_str(mapping: Dict[str, Any]) -> str:
    return orjson.dumps(mapping).decode()


class EventOutRelation(Model, mixin.Timestamp):
    event_id = fields.UUIDField()
    body = fields.JSONField(encoder=_dump_str, decoder=orjson.loads)
    confirmed = fields.BooleanField(default=False)
    send_after = fields.DatetimeField(index=True, null=True, default=None)

    class Meta:
        table = "event_out"
        indexes = [
            Index(fields={"created_at"}),
        ]


class DispatchedEventRelation(Model, mixin.Timestamp):
    body = fields.JSONField(encoder=_dump_str, decoder=orjson.loads)
    event_id = fields.UUIDField()

    class Meta:
        table = "dispatched_event"


class HandledEventRelation(PkUuidModel, mixin.Timestamp):
    body = fields.JSONField(encoder=_dump_str, decoder=orjson.loads)
    guarantee = fields.CharEnumField(ProcessingGuarantee)

    class Meta:
        table = "handled_event"
