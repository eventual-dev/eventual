from typing import Any, AsyncGenerator, Callable, Optional, Tuple

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.abc.broker import MessageBroker
from eventual.abc.registry import HandlerRegistry
from eventual.abc.router import IntegrityGuard
from eventual.abc.work_unit import WU, WorkUnit
from eventual.model import EventPayload
from eventual.router import Router
from eventual.scheduler import EventSchedule, Scheduler


def default_lifespan(
    handler_registry: HandlerRegistry[WU],
    message_broker: MessageBroker,
    integrity_guard: IntegrityGuard[WorkUnit],
    event_payload_stream_pair: Tuple[
        MemoryObjectSendStream[EventPayload], MemoryObjectReceiveStream[EventPayload]
    ],
    event_schedule: EventSchedule[WU],
    scheduler_factory: Callable[
        [MemoryObjectSendStream[EventPayload], EventSchedule[WU], TaskGroup],
        Scheduler[WU],
    ],
    router_factory: Callable[[TaskGroup], Router],
) -> Callable:
    event_payload_send_stream, event_payload_stream = event_payload_stream_pair

    async def generator(_: Optional[Any] = None) -> AsyncGenerator[None, None]:
        async with anyio.create_task_group() as callback_group:
            async with anyio.create_task_group() as background_group:
                router = router_factory(callback_group)
                scheduler = scheduler_factory(
                    event_payload_send_stream, event_schedule, callback_group
                )

                background_group.start_soon(
                    router.dispatch_from_broker,
                    handler_registry,
                    message_broker,
                    integrity_guard,
                    scheduler,
                )
                background_group.start_soon(scheduler.receive_confirmation_stream)
                background_group.start_soon(
                    message_broker.send_event_payload_stream,
                    event_payload_stream,
                    scheduler.confirmation_send_stream,
                )
                await scheduler.schedule_every_open_unclaimed_event_entry_due_now()
                yield
                background_group.cancel_scope.cancel()

    return generator
