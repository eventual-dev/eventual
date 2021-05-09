import abc
import dataclasses
from typing import Awaitable, Callable, Generic, List, Mapping, Protocol

from .broker import Message
from .event_store import EventSendStore, Guarantee
from .work_unit import WU


class MessageHandler(Protocol[WU]):
    def __call__(
        self, __msg: Message, __event_send_store: EventSendStore[WU]
    ) -> Awaitable[None]:
        ...


@dataclasses.dataclass
class HandlerSpecification(Generic[WU]):
    guarantee: Guarantee
    delay_on_exc: float
    message_handler: MessageHandler[WU]


class HandlerRegistry(abc.ABC, Generic[WU]):
    @abc.abstractmethod
    def register(
        self,
        subject_seq: List[str],
        handler: MessageHandler[WU],
        guarantee: Guarantee,
        delay_on_exc: float,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def mapping(self) -> Mapping[str, HandlerSpecification[WU]]:
        raise NotImplementedError

    def subscribe(
        self,
        event_type_seq: List[str],
        guarantee: Guarantee = Guarantee.AT_LEAST_ONCE,
        delay_on_exc: float = 1.0,
    ) -> Callable[[MessageHandler[WU]], MessageHandler[WU]]:
        def decorator(handler: MessageHandler[WU]) -> MessageHandler[WU]:
            self.register(event_type_seq, handler, guarantee, delay_on_exc)
            return handler

        return decorator
