from typing import Any, AsyncGenerator, Callable, Optional, Tuple

import anyio
from anyio.abc import TaskGroup
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.broker import MessageBroker
from eventual.concurrent.dispatcher import ConcurrentMessageDispatcher
from eventual.concurrent.event_send_store import ConcurrentEventSendStore
from eventual.event_store import EventReceiveStore
from eventual.model import EventBody
from eventual.registry import HandlerRegistry
from eventual.work_unit import WU, WorkUnit


def eventual_concurrent_lifespan(
    handler_registry: HandlerRegistry[WU],
    message_broker: MessageBroker,
    event_receive_store: EventReceiveStore[WorkUnit],
    event_body_stream_pair: Tuple[
        MemoryObjectSendStream[EventBody], MemoryObjectReceiveStream[EventBody]
    ],
    concurrent_event_send_store_factory: Callable[
        [MemoryObjectSendStream[EventBody], TaskGroup], ConcurrentEventSendStore[WU]
    ],
    concurrent_message_dispatcher_factory: Callable[
        [TaskGroup], ConcurrentMessageDispatcher
    ],
) -> Callable:
    event_body_send_stream, event_body_stream = event_body_stream_pair

    async def lifespan_context(_: Optional[Any] = None) -> AsyncGenerator[None, None]:
        async with anyio.create_task_group() as handler_group:
            async with anyio.create_task_group() as eventual_group:
                message_dispatcher = concurrent_message_dispatcher_factory(
                    handler_group
                )
                event_send_store = concurrent_event_send_store_factory(
                    event_body_send_stream, handler_group
                )

                eventual_group.start_soon(
                    message_dispatcher.dispatch_from_broker,
                    handler_registry,
                    message_broker,
                    event_receive_store,
                    event_send_store,
                )
                eventual_group.start_soon(event_send_store.receive_confirmation_stream)
                eventual_group.start_soon(
                    message_broker.send_event_body_stream,
                    event_body_stream,
                    event_send_store.confirmation_send_stream,
                )
                await event_send_store.schedule_every_written_event_to_be_sent()
                yield
                await eventual_group.cancel_scope.cancel()

    return lifespan_context
