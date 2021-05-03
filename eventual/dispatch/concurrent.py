import datetime as dt
from types import MappingProxyType
from typing import (
    AsyncContextManager,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Mapping,
)

from anyio.abc import TaskGroup

from eventual import util

from ..model import EventBody
from .abc import (
    WU,
    EventStore,
    Guarantee,
    HandlerRegistry,
    HandlerSpecification,
    Message,
    MessageBroker,
    MessageDispatcher,
    MessageHandler,
)


def _manager_from_guarantee(
    msg: Message, event_store: EventStore, guarantee: Guarantee
) -> AsyncContextManager[EventBody]:
    if guarantee == guarantee.AT_LEAST_ONCE:
        return event_store.handle_at_least_once(msg)
    if guarantee == guarantee.EXACTLY_ONCE:
        return event_store.handle_exactly_once(msg)
    if guarantee == guarantee.NO_MORE_THAN_ONCE:
        return event_store.handle_no_more_than_once(msg)
    raise AssertionError("there are no more guarantees")


async def _wait_and_pop(
    message_dispatcher: "ConcurrentMessageDispatcher",
    fn: Callable[[Message, EventStore], Awaitable[None]],
    message: Message,
    guarantee: Guarantee,
    delay_on_exc: float,
) -> None:
    try:
        async with _manager_from_guarantee(
            message, message_dispatcher.event_store, guarantee
        ):
            await fn(message, message_dispatcher.event_store)
    except Exception:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay_on_exc)
        await message_dispatcher.event_store.schedule_event_to_send(
            message.event_body,
            send_after=send_after,
        )
        # TODO: Make sure that no as few messages as possible get stuck in a sent/rejected loop.
        # This should not violate any guarantees, but can possibly create a lot of messages.
        message.acknowledge()
        raise


class Registry(HandlerRegistry, Generic[WU]):
    def __init__(
        self,
    ) -> None:
        self.handler_spec_from_subject: Dict[
            str,
            HandlerSpecification[WU],
        ] = {}

    def register(
        self,
        subject_seq: List[str],
        handler: MessageHandler[WU],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        if delay_on_exc <= 0:
            raise ValueError("delay has to be non-negative")
        for subject in subject_seq:
            if subject in self.handler_spec_from_subject:
                # TODO: Change error type to something more appropriate.
                raise ValueError(
                    "it is not possible to register multiple functions to handle the same event type"
                )
            self.handler_spec_from_subject[subject] = (handler, guarantee, delay_on_exc)

    def mapping(self) -> Mapping[str, HandlerSpecification[WU]]:
        return MappingProxyType(self.handler_spec_from_subject)


class ConcurrentMessageDispatcher(MessageDispatcher, Generic[WU]):
    def __init__(
        self,
        task_group: TaskGroup,
        event_store: EventStore[WU],
        handler_registry: HandlerRegistry[WU],
    ):
        self.task_group = task_group
        self.event_store = event_store
        self.handler_spec_from_subject = handler_registry.mapping()

    async def dispatch_from_broker(self, message_broker: MessageBroker) -> None:
        message_stream = await message_broker.message_receive_stream()
        async for message in message_stream:
            event_body = message.event_body

            is_event_handled = await self.event_store.is_event_handled(message.event_id)
            if is_event_handled:
                # There is no guarantee that messages that we've marked as handled
                # were actually acknowledged, so it's not an error to get the handled message.
                # Furthermore, even if someone sends the same message multiple times,
                # but we consider it handled, we do nothing in a truly idempotent manner.
                message.acknowledge()
                continue

            triplet = self.handler_spec_from_subject.get(message.event_subject)
            if triplet is None:
                continue

            fn, guarantee, delay_on_exc = triplet
            # We save every event that we attempt to dispatch, not every event we receive,
            # because we can get a lot of events that we do not care about.
            await self.event_store.mark_event_dispatched(event_body)

            self.task_group.start_soon(
                _wait_and_pop, self, fn, message, guarantee, delay_on_exc
            )
