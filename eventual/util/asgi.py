from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

import anyio
from anyio.abc._tasks import TaskGroup

from eventual.dispatch.abc import MessageBroker, MessageDispatcher


@asynccontextmanager
async def eventual_lifespan(
    message_broker: MessageBroker,
    message_from_task_group: Callable[[TaskGroup], MessageDispatcher],
) -> AsyncGenerator[None, None]:
    async with anyio.create_task_group() as task_group:
        message_dispatcher = message_from_task_group(task_group)

        task_group.start_soon(message_dispatcher.dispatch_from_broker, message_broker)
        task_group.start_soon(message_broker.send_event_body_stream)
        yield
        await task_group.cancel_scope.cancel()
