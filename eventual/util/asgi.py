import asyncio

from eventual.dispatch import (
    EventStore,
    MessageDispatcher,
    MessageBroker,
)


def register_eventual(
    app,
    message_exchange: MessageBroker,
    message_dispatcher: MessageDispatcher,
    event_storage: EventStore,
):
    task_from_name = dict()

    @app.on_event("startup")
    async def start_eventual():
        task_from_name["dispatch_task"] = asyncio.create_task(
            message_dispatcher.dispatch_from_exchange(message_exchange)
        )
        task_from_name["publish_task"] = asyncio.create_task(
            message_exchange.send_event_body_stream(event_storage.event_body_stream())
        )

    @app.on_event("shutdown")
    async def stop_eventual():
        # This can be called with a delay.
        # For example, uvicorn apparently waits for all tasks to complete,
        # before it invokes this callback. The timeout seems to be 10 seconds,
        # and we don't know if it can be configured.
        # Nothing actually changes for us, because nothing gets cancelled.
        task_from_name["dispatch_task"].cancel()
        task_from_name["publish_task"].cancel()
        await asyncio.gather(*task_from_name.values(), return_exceptions=True)
