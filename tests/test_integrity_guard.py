from typing import Type

import anyio
import pytest

from eventual.abc.router import IntegrityGuard
from eventual.abc.work_unit import InterruptWork
from tests.memory.work_unit import MemoryWorkUnit
from tests.test_broker import background_stream_broker

EVENT_COUNT = 1

pytestmark = pytest.mark.anyio


async def test_exactly_once_commit_and_acknowledge_when_ok(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)
    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            async with integrity_guard.handle_exactly_once(msg) as event_payload:
                assert msg.event_payload == event_payload
                assert not await integrity_guard.is_dispatch_forbidden(
                    msg.event_payload.id
                )
            assert await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
            assert stream_broker.is_msg_acknowledged(msg.event_payload.id)


async def test_exactly_once_acknowledge_when_interrupt_work(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)
    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            async with integrity_guard.handle_exactly_once(msg):
                raise InterruptWork
            assert not await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
            assert stream_broker.is_msg_acknowledged(msg.event_payload.id)


@pytest.mark.parametrize("exc_cls", [ValueError, TypeError])
async def test_exactly_once_no_acknowledge_when_exception(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
    exc_cls: Type[BaseException],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)
    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            with pytest.raises(exc_cls):
                async with integrity_guard.handle_exactly_once(msg):
                    raise exc_cls
            assert not stream_broker.is_msg_acknowledged(msg.event_payload.id)


async def test_no_more_than_once_commit_and_acknowledge_when_ok(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)
    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            async with integrity_guard.handle_no_more_than_once(msg) as event_payload:
                assert msg.event_payload == event_payload
                assert await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
                assert stream_broker.is_msg_acknowledged(msg.event_payload.id)


@pytest.mark.parametrize("exc_cls", [ValueError, TypeError, InterruptWork])
async def test_no_more_than_once_commit_and_acknowledge_when_exception(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
    exc_cls: Type[BaseException],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)

    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            with pytest.raises(exc_cls):
                async with integrity_guard.handle_no_more_than_once(msg):
                    raise exc_cls
            assert await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
            assert stream_broker.is_msg_acknowledged(msg.event_payload.id)


async def test_at_least_once_commit_and_acknowledge_when_ok(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)
    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            async with integrity_guard.handle_at_least_once(msg) as event_payload:
                assert msg.event_payload == event_payload
                assert not await integrity_guard.is_dispatch_forbidden(
                    msg.event_payload.id
                )
                assert not stream_broker.is_msg_acknowledged(msg.event_payload.id)
            assert await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
            assert stream_broker.is_msg_acknowledged(msg.event_payload.id)


@pytest.mark.parametrize("exc_cls", [ValueError, TypeError, InterruptWork])
async def test_at_least_once_no_commit_and_no_acknowledge_when_ok(
    integrity_guard: IntegrityGuard[MemoryWorkUnit],
    exc_cls: Type[BaseException],
) -> None:
    confirmation_send_stream, _ = anyio.create_memory_object_stream(EVENT_COUNT)

    async with background_stream_broker(
        confirmation_send_stream, EVENT_COUNT
    ) as stream_broker:
        async for msg in stream_broker.message_receive_stream():
            with pytest.raises(exc_cls):
                async with integrity_guard.handle_at_least_once(msg):
                    raise exc_cls
            assert not await integrity_guard.is_dispatch_forbidden(msg.event_payload.id)
            assert not stream_broker.is_msg_acknowledged(msg.event_payload.id)
