import abc

from .broker import MessageBroker
from .event_store import EventReceiveStore, EventSendStore
from .registry import HandlerRegistry
from .work_unit import WU


class MessageDispatcher(abc.ABC):
    @abc.abstractmethod
    async def dispatch_from_broker(
        self,
        handler_registry: HandlerRegistry[WU],
        message_broker: MessageBroker,
        event_receive_store: EventReceiveStore[WU],
        event_send_store: EventSendStore[WU],
    ) -> None:
        raise NotImplementedError
