import contextlib
from collections import deque
from typing import AsyncGenerator, Deque, List

import anyio
import pytest
from anyio.streams.memory import MemoryObjectSendStream

from eventual.abc.broker import Message
from eventual.model import EventPayload
from tests.memory.broker import StreamMessageBroker
from tests.model import SomethingHappened

EVENT_COUNT = 3

pytestmark = pytest.mark.anyio


async def _event_producer(
    event_payload_send_stream: MemoryObjectSendStream[EventPayload], event_count: int
) -> None:
    async with event_payload_send_stream:
        for _ in range(event_count):
            await event_payload_send_stream.send(
                EventPayload.from_event(SomethingHappened())
            )


@contextlib.asynccontextmanager
async def background_stream_broker(
    confirmation_send_stream: MemoryObjectSendStream[EventPayload], event_count: int
) -> AsyncGenerator[StreamMessageBroker, None]:
    stream_broker = StreamMessageBroker()
    (
        event_payload_send_stream,
        event_payload_stream,
    ) = anyio.create_memory_object_stream()

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_event_producer, event_payload_send_stream, event_count)
        task_group.start_soon(
            stream_broker.send_event_payload_stream,
            event_payload_stream,
            confirmation_send_stream,
        )
        yield stream_broker


async def test_no_message_is_dropped() -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)

    msg_seq: List[Message] = []

    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            msg_seq.append(msg)

    assert len(msg_seq) == EVENT_COUNT


async def test_every_message_is_confirmed() -> None:
    confirmation_send_stream, confirmation_stream = anyio.create_memory_object_stream(
        EVENT_COUNT
    )
    msg_seq: Deque[Message] = deque()

    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            msg_seq.append(msg)

    async for event_payload in confirmation_stream:
        msg = msg_seq.popleft()
        assert msg.event_payload.id == event_payload.id
        assert msg.event_payload.subject == event_payload.subject


async def test_every_message_acknowledged() -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)

    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        msg_seq: List[Message] = []

        async for msg in stream_broker.message_receive_stream():
            msg_seq.append(msg)

        assert stream_broker.unacknowledged_msg_count == EVENT_COUNT

        for msg in msg_seq:
            msg.acknowledge()

        assert stream_broker.unacknowledged_msg_count == 0
