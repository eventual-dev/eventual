import asyncio
import datetime as dt
import uuid
from typing import (
    AsyncContextManager,
    AsyncIterable,
    Awaitable,
    Callable,
    Dict,
    List,
    Tuple,
)

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
    unique_task_id: uuid.UUID,
    fn: Callable[[Message], Awaitable[None]],
    message: Message,
    guarantee: Guarantee,
    delay_on_exc: float,
) -> None:
    try:
        async with _manager_from_guarantee(
            message, message_dispatcher.event_storage, guarantee
        ):
            await fn(message)
    except Exception:
        send_after = util.tz_aware_utcnow() + dt.timedelta(seconds=delay_on_exc)
        body = message.body
        await message_dispatcher.event_storage.schedule_event_out(
            body["id"],
            body,
            send_after=send_after,
        )
        # TODO: Make sure that no as few messages as possible get stuck in a sent/rejected loop.
        # This should not violate any guarantees, but can possibly create a lot of messages.
        message.acknowledge()
        raise
    finally:
        del message_dispatcher.task_from_id[unique_task_id]


class ConcurrentMessageDispatcher(MessageDispatcher):
    def __init__(self, event_storage: EventStore, delay_on_exc: float):
        self.event_storage = event_storage
        self.delay_on_exc = delay_on_exc

        self.fn_from_message_type: Dict[
            str, Tuple[Callable[[Message], Awaitable[None]], Guarantee, float]
        ] = {}
        self.task_from_id: Dict[uuid.UUID, asyncio.Task] = {}

    def register(
        self,
        event_type_seq: List[str],
        fn: Callable[[Message], Awaitable[None]],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        if delay_on_exc <= 0:
            raise ValueError("delay has to be non-negative")
        for event_type in event_type_seq:
            if event_type in self.fn_from_message_type:
                # TODO: Change error type to something more appropriate.
                raise ValueError(
                    "it is not possible to register multiple functions to handle the same event type"
                )
            self.fn_from_message_type[event_type] = (fn, guarantee, delay_on_exc)

    async def dispatch_from_exchange(self, message_exchange: MessageBroker) -> None:
        while True:
            message_stream = await message_exchange.message_stream()
            self.interrupt_dispatch = False
            await self.dispatch_from_stream(message_stream)

    async def dispatch_from_stream(
        self, message_stream: AsyncIterable[Message]
    ) -> None:
        try:
            async for message in message_stream:
                event_body = message.body

                is_event_handled = await self.event_storage.is_event_handled(
                    event_body["id"]
                )
                if is_event_handled:
                    # There is no guarantee that messages that we've marked as handled
                    # were actually acknowledged, so it's not an error to get the handled message.
                    # Furthermore, even if someone sends the same message multiple times,
                    # but we consider it handled, we do nothing in a truly idempotent manner.
                    message.acknowledge()
                    continue

                triplet = self.fn_from_message_type.get(event_body["type"])
                if triplet is None:
                    continue

                fn, guarantee, delay_on_exc = triplet
                # We save every event that we attempt to dispatch, not every event we receive,
                # because we can get a lot of events that we do not care about.
                await self.event_storage.mark_event_dispatched(event_body)

                # We want to remove tasks from `self.task_from_id` upon their completion.
                # To do that we have to associate each one with a unique key. Such a key
                # should be unique for every task, so we can't use a message id -
                # during the handling of a message we can get the same message again.
                # For now we've settled on a uuid, but it's certainly not the fastest option.
                unique_id = uuid.uuid4()
                task = asyncio.create_task(
                    _wait_and_pop(self, unique_id, fn, message, guarantee, delay_on_exc)
                )
                self.task_from_id[unique_id] = task
        except asyncio.CancelledError:
            pass
        except Exception:
            # TODO: Add logging here to signal that we are shutting down.
            raise
        finally:
            await asyncio.gather(*self.task_from_id.values(), return_exceptions=True)
