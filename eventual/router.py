from typing import Any, AsyncContextManager

from anyio.abc import TaskGroup

from eventual.abc.broker import Message, MessageBroker
from eventual.abc.guarantee import Guarantee
from eventual.abc.router import IntegrityGuard, MessageRouter
from eventual.abc.schedule import EventScheduler
from eventual.abc.work_unit import WU
from eventual.model import EventPayload
from eventual.registry import HandlerRegistry, MessageHandler


def _manager_from_guarantee(
    msg: Message, integrity_guard: IntegrityGuard[Any], guarantee: Guarantee
) -> AsyncContextManager[EventPayload]:
    if guarantee == guarantee.AT_LEAST_ONCE:
        return integrity_guard.handle_at_least_once(msg)
    if guarantee == guarantee.EXACTLY_ONCE:
        return integrity_guard.handle_exactly_once(msg)
    if guarantee == guarantee.NO_MORE_THAN_ONCE:
        return integrity_guard.handle_no_more_than_once(msg)
    raise AssertionError("there are no more guarantees")


async def _handle_with_retry(
    integrity_guard: IntegrityGuard[WU],
    scheduler: EventScheduler[WU],
    fn: MessageHandler[WU],
    message: Message,
    guarantee: Guarantee,
    delay_on_exc: float,
) -> None:
    try:
        async with _manager_from_guarantee(message, integrity_guard, guarantee):
            await fn(message, scheduler)
    except Exception:
        await scheduler.schedule_event(
            message.event_payload,
            delay=delay_on_exc,
        )
        message.acknowledge()
        raise


class Router(MessageRouter):
    def __init__(
        self,
        task_group: TaskGroup,
    ):
        self.task_group = task_group

    async def dispatch_from_broker(
        self,
        handler_registry: HandlerRegistry[WU],
        message_broker: MessageBroker,
        integrity_guard: IntegrityGuard[WU],
        scheduler: EventScheduler[WU],
    ) -> None:
        handler_spec_from_subject = handler_registry.mapping()
        message_stream = message_broker.message_receive_stream()

        async for message in message_stream:
            is_event_handled = await integrity_guard.is_dispatch_forbidden(
                message.event_payload.id
            )
            if is_event_handled:
                # There is no guarantee that messages that we've marked as handled
                # were actually acknowledged, so it's not an error to get the handled message.
                # Furthermore, even if someone sends the same message multiple times,
                # but we consider it handled, we do nothing in a truly idempotent manner.
                message.acknowledge()
                continue

            handler_spec = handler_spec_from_subject.get(message.event_payload.subject)
            if handler_spec is None:
                continue

            # We save every event that we attempt to dispatch, not every event we receive,
            # because we can get a lot of events that we do not care about.
            await integrity_guard.record_dispatch_attempt(message.event_payload)

            self.task_group.start_soon(
                _handle_with_retry,
                integrity_guard,
                scheduler,
                handler_spec.message_handler,
                message,
                handler_spec.guarantee,
                handler_spec.delay_on_exc,
            )
