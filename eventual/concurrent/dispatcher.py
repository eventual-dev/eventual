from typing import AsyncContextManager

from anyio.abc import TaskGroup

from eventual.broker import Message, MessageBroker
from eventual.dispatcher import MessageDispatcher
from eventual.event_store import EventReceiveStore, EventSendStore, Guarantee
from eventual.model import EventBody
from eventual.registry import HandlerRegistry, MessageHandler
from eventual.work_unit import WU, WorkUnit


def _manager_from_guarantee(
    msg: Message, event_store: EventReceiveStore, guarantee: Guarantee
) -> AsyncContextManager[EventBody]:
    if guarantee == guarantee.AT_LEAST_ONCE:
        return event_store.handle_at_least_once(msg)
    if guarantee == guarantee.EXACTLY_ONCE:
        return event_store.handle_exactly_once(msg)
    if guarantee == guarantee.NO_MORE_THAN_ONCE:
        return event_store.handle_no_more_than_once(msg)
    raise AssertionError("there are no more guarantees")


async def _handle_with_retry(
    event_receive_store: EventReceiveStore[WorkUnit],
    event_send_store: EventSendStore[WU],
    fn: MessageHandler[WU],
    message: Message,
    guarantee: Guarantee,
    delay_on_exc: float,
) -> None:
    # Receive store and send store can be two completely different stores,
    # so ReceiveStore is bounded only by WorkUnit.
    try:
        async with _manager_from_guarantee(message, event_receive_store, guarantee):
            await fn(message, event_send_store)
    except Exception:
        await event_send_store.schedule_event_to_be_sent(
            message.event_body,
            delay=delay_on_exc,
        )
        message.acknowledge()
        raise


class ConcurrentMessageDispatcher(MessageDispatcher):
    def __init__(
        self,
        task_group: TaskGroup,
    ):
        self.task_group = task_group

    async def dispatch_from_broker(
        self,
        handler_registry: HandlerRegistry[WU],
        message_broker: MessageBroker,
        event_receive_store: EventReceiveStore[WU],
        event_send_store: EventSendStore[WU],
    ) -> None:
        handler_spec_from_subject = handler_registry.mapping()
        message_stream = message_broker.message_receive_stream()

        async for message in message_stream:
            event_body = message.event_body

            is_event_handled = await event_receive_store.is_event_handled(
                message.event_id
            )
            if is_event_handled:
                # There is no guarantee that messages that we've marked as handled
                # were actually acknowledged, so it's not an error to get the handled message.
                # Furthermore, even if someone sends the same message multiple times,
                # but we consider it handled, we do nothing in a truly idempotent manner.
                message.acknowledge()
                continue

            handler_spec = handler_spec_from_subject.get(message.event_subject)
            if handler_spec is None:
                continue

            # We save every event that we attempt to dispatch, not every event we receive,
            # because we can get a lot of events that we do not care about.
            await event_receive_store.mark_event_as_dispatched(event_body)

            self.task_group.start_soon(
                _handle_with_retry,
                event_receive_store,
                event_send_store,
                handler_spec.message_handler,
                message,
                handler_spec.guarantee,
                handler_spec.delay_on_exc,
            )
