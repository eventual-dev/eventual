import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from eventual import util
from eventual.infra.exchange.abc import (
    EventStorage,
    EventBody,
    Message,
    ProcessingGuarantee,
)
from eventual.infra.relation import (
    EventOutRelation,
    HandledEventRelation,
    DispatchedEventRelation,
)
from eventual.infra.uow import tortoise_unit_of_work
from eventual.model import Entity


class RelationalEventStorage(EventStorage):
    @asynccontextmanager
    async def clear_outbox_atomically(
        self, *entity_seq: Entity
    ) -> AsyncGenerator[None, None]:
        async with tortoise_unit_of_work():
            yield None
            await self.clear_outbox(entity_seq)

    async def schedule_event_out(
        self, event_id: uuid.UUID, body: EventBody, send_after: bool = False
    ):
        await EventOutRelation.create(
            event_id=event_id, body=body, send_after=send_after
        )

    async def is_event_handled(self, event_id: uuid.UUID) -> bool:
        event_count = await HandledEventRelation.filter(id=event_id).count()
        return event_count > 0

    async def mark_event_handled(
        self, event_body: EventBody, guarantee: ProcessingGuarantee
    ) -> uuid.UUID:
        event_id = event_body["id"]
        await HandledEventRelation.create(
            id=event_id, body=event_body, guarantee=guarantee
        )
        return event_id

    async def mark_event_dispatched(self, event_body: EventBody) -> uuid.UUID:
        event_id = event_body["id"]
        await DispatchedEventRelation.create(body=event_body, event_id=event_id)
        return event_id

    @asynccontextmanager
    async def handle_exactly_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        async with tortoise_unit_of_work():
            yield message.body
            await self.mark_event_handled(
                message.body, guarantee=ProcessingGuarantee.EXACTLY_ONCE
            )
        message.acknowledge()

    @asynccontextmanager
    async def handle_no_more_than_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        await self.mark_event_handled(
            message.body, guarantee=ProcessingGuarantee.NO_MORE_THAN_ONCE
        )
        message.acknowledge()
        yield message.body

    @asynccontextmanager
    async def handle_at_least_once(
        self, message: Message
    ) -> AsyncGenerator[EventBody, None]:
        yield message.body
        await self.mark_event_handled(
            message.body, guarantee=ProcessingGuarantee.AT_LEAST_ONCE
        )
        message.acknowledge()

    async def event_body_stream(self) -> AsyncGenerator[EventBody, None]:
        while True:
            event_seq = await EventOutRelation.filter(
                confirmed=False, send_after__lt=util.tz_aware_utcnow()
            ).order_by("created_at")

            for event in event_seq:
                yield event.body
                event.confirmed = True
                await event.save()
            await asyncio.sleep(1)
