import orjson

from eventual.model import EventPayload


def test_event_payload_from_event_body(event_payload: EventPayload) -> None:
    assert event_payload == EventPayload.from_event_body(event_payload.body)


def test_event_payload_from_event_body_supports_json(
    event_payload: EventPayload,
) -> None:
    plain_event_payload = EventPayload.from_event_body(
        orjson.loads(orjson.dumps(event_payload.body))
    )
    assert event_payload.id == plain_event_payload.id
    assert event_payload.occurred_on == plain_event_payload.occurred_on
    assert event_payload.subject == plain_event_payload.subject
