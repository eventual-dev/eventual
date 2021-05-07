from types import MappingProxyType
from typing import Dict, Generic, List, Mapping

from .abc import WU, Guarantee, HandlerRegistry, HandlerSpecification, MessageHandler


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
