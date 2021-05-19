import datetime as dt
import uuid
from typing import AsyncIterable, Set, Tuple

import anyio
import orjson
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.abc.broker import Message, MessageBroker
from eventual.model import EventPayload


class StreamMessage(Message):
    def __init__(self, message_bytes: bytes, broker: "StreamMessageBroker"):
        body = orjson.loads(message_bytes)
        self._event_payload = EventPayload(
            id=uuid.UUID(body["id"]),
            occurred_on=dt.datetime.fromisoformat(body["occurred_on"]),
            subject=body["_subject"],
            body=body,
        )
        self._broker = broker

    @property
    def event_payload(self) -> EventPayload:
        return self._event_payload

    def acknowledge(self) -> None:
        self._broker.acknowledge_msg(self.event_payload.id)


class StreamMessageBroker(MessageBroker):
    def __init__(self, max_size: int = 0) -> None:
        stream_pair: Tuple[
            MemoryObjectSendStream[bytes], MemoryObjectReceiveStream[bytes]
        ] = anyio.create_memory_object_stream(max_size)
        (
            self._send_stream,
            self._receive_stream,
        ) = stream_pair
        self._event_id_set: Set[uuid.UUID] = set()

    async def send_event_payload_stream(
        self,
        event_payload_stream: MemoryObjectReceiveStream[EventPayload],
        confirmation_send_stream: MemoryObjectSendStream[EventPayload],
    ) -> None:

        async with self._send_stream:
            async with confirmation_send_stream:
                async with event_payload_stream:
                    async for event_payload in event_payload_stream:
                        await self._send_stream.send(
                            self.event_payload_as_bytes(event_payload)
                        )
                        await confirmation_send_stream.send(event_payload)

    async def message_receive_stream(self) -> AsyncIterable[Message]:
        async with self._receive_stream:
            async for message_bytes in self._receive_stream:
                yield self.create_msg(message_bytes)

    @classmethod
    def event_payload_as_bytes(cls, event_payload: EventPayload) -> bytes:
        return orjson.dumps(event_payload.body)

    def create_msg(self, message_bytes: bytes) -> StreamMessage:
        msg = StreamMessage(message_bytes, self)
        self._event_id_set.add(msg.event_payload.id)
        return msg

    def acknowledge_msg(self, event_id: uuid.UUID) -> None:
        self._event_id_set.remove(event_id)

    @property
    def unacknowledged_msg_count(self) -> int:
        return len(self._event_id_set)

    def is_msg_acknowledged(self, event_id: uuid.UUID) -> bool:
        return event_id not in self._event_id_set
