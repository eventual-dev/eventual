import abc
import uuid
from typing import AsyncIterable

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from eventual.model import EventBody


class Message(abc.ABC):
    @property
    def event_id(self) -> uuid.UUID:
        return uuid.UUID(self.event_body["id"])

    @property
    def event_subject(self) -> str:
        return self.event_body["_subject"]

    @property
    @abc.abstractmethod
    def event_body(self) -> EventBody:
        raise NotImplementedError

    @abc.abstractmethod
    def acknowledge(self) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.event_id}/{self.event_subject}"


class MessageBroker(abc.ABC):
    @abc.abstractmethod
    async def send_event_body_stream(
        self,
        event_body_stream: MemoryObjectReceiveStream[EventBody],
        confirmation_send_stream: MemoryObjectSendStream[EventBody],
    ) -> None:
        # We could be more general and say that event_body_stream is an AsyncIterable, but memory streams
        # have ability to do a clean shutdown, which is convenient.
        raise NotImplementedError

    @abc.abstractmethod
    def message_receive_stream(self) -> AsyncIterable[Message]:
        raise NotImplementedError
