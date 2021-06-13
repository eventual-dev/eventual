import abc
import dataclasses
import sys
from typing import Awaitable, Callable, Generic, List, Mapping

if sys.version_info >= (3, 8):
    from typing import Protocol
else:
    from typing_extensions import Protocol

from .broker import Message
from .router import Guarantee
from .schedule import EventScheduler
from .work_unit import WU


class MessageHandler(Protocol[WU]):
    def __call__(
        self, __msg: Message, __scheduler: EventScheduler[WU]
    ) -> Awaitable[None]:
        raise NotImplementedError


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
