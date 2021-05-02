import datetime as dt
from typing import (
    AsyncContextManager,
    AsyncIterable,
    Awaitable,
    Callable,
    Dict,
    List,
    Tuple,
)

from anyio.abc import TaskGroup

from eventual import util

from ..model import EventBody
from .abc import EventStore, Guarantee, Message, MessageBroker, MessageDispatcher


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


class ConcurrentMessageDispatcher(MessageDispatcher):
    def __init__(
        self, task_group: TaskGroup, event_store: EventStore, delay_on_exc: float
    ):
        self.task_group = task_group
        self.event_store = event_store
        self.delay_on_exc = delay_on_exc

        self.fn_from_subject: Dict[
            str,
            Tuple[Callable[[Message, EventStore], Awaitable[None]], Guarantee, float],
        ] = {}

    def register(
        self,
        subject_seq: List[str],
        fn: Callable[[Message, EventStore], Awaitable[None]],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        if delay_on_exc <= 0:
            raise ValueError("delay has to be non-negative")
        for subject in subject_seq:
            if subject in self.fn_from_subject:
                # TODO: Change error type to something more appropriate.
                raise ValueError(
                    "it is not possible to register multiple functions to handle the same event type"
                )
            self.fn_from_subject[subject] = (fn, guarantee, delay_on_exc)

    async def dispatch_from_exchange(self, message_exchange: MessageBroker) -> None:
        while True:
            message_stream = await message_exchange.message_stream()
            await self.dispatch_from_stream(message_stream)

    async def dispatch_from_stream(
        self, message_stream: AsyncIterable[Message]
    ) -> None:
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

            triplet = self.fn_from_subject.get(message.event_subject)
            if triplet is None:
                continue

            fn, guarantee, delay_on_exc = triplet
            # We save every event that we attempt to dispatch, not every event we receive,
            # because we can get a lot of events that we do not care about.
            await self.event_store.mark_event_dispatched(event_body)

            self.task_group.start_soon(
                _wait_and_pop, self, fn, message, guarantee, delay_on_exc
            )
