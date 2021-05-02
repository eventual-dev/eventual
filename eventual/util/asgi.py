from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

import anyio
from anyio.abc._tasks import TaskGroup

from eventual.dispatch.abc import EventStore, MessageBroker, MessageDispatcher


@asynccontextmanager
async def eventual_lifespan(
    message_broker: MessageBroker,
    event_store: EventStore,
    message_from_task_group: Callable[[TaskGroup], MessageDispatcher],
) -> AsyncGenerator[None, None]:
    async with anyio.create_task_group() as task_group:
        message_dispatcher = message_from_task_group(task_group)

        task_group.start_soon(message_dispatcher.dispatch_from_exchange, message_broker)
        # TODO: It would look nicer if broker could reference event store directly...
        task_group.start_soon(
            message_broker.send_event_body_stream,
            event_store.unconfirmed_receive_stream,
            event_store.confirmation_send_stream,
        )
        yield
        await task_group.cancel_scope.cancel()
