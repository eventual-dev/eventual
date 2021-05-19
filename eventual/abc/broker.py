import abc
from typing import AsyncIterable

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.model import EventPayload


class Message(abc.ABC):
    @property
    @abc.abstractmethod
    def event_payload(self) -> EventPayload:
        raise NotImplementedError

    @abc.abstractmethod
    def acknowledge(self) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.event_payload.id}/{self.event_payload.subject}"


class MessageBroker(abc.ABC):
    @abc.abstractmethod
    async def send_event_payload_stream(
        self,
        event_payload_stream: MemoryObjectReceiveStream[EventPayload],
        confirmation_send_stream: MemoryObjectSendStream[EventPayload],
    ) -> None:
        # We could be more general and say that event_body_stream is an AsyncIterable, but memory streams
        # have ability to do a clean shutdown, which is convenient.
        raise NotImplementedError

    @abc.abstractmethod
    def message_receive_stream(self) -> AsyncIterable[Message]:
        raise NotImplementedError
