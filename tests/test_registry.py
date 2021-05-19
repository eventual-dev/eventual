from typing import Any

import pytest

from eventual.abc.broker import Message
from eventual.abc.guarantee import Guarantee
from eventual.abc.registry import HandlerSpecification
from eventual.abc.schedule import EventScheduler
from eventual.registry import Registry


async def _msg_handler(msg: Message, scheduler: EventScheduler[Any]) -> None:
    raise NotImplementedError


async def _other_msg_handler(msg: Message, scheduler: EventScheduler[Any]) -> None:
    raise NotImplementedError


def test_registry_rejects_negative_delay(
    registry: Registry[Any],
) -> None:
    with pytest.raises(ValueError):
        registry.register([], _msg_handler, Guarantee.AT_LEAST_ONCE, -1.0)


def test_registry_rejects_zero_delay(
    registry: Registry[Any],
) -> None:
    with pytest.raises(ValueError):
        registry.register([], _msg_handler, Guarantee.AT_LEAST_ONCE, 0.0)


def test_no_multiple_handlers_for_one_subject(
    registry: Registry[Any],
) -> None:
    with pytest.raises(ValueError):
        registry.register(["xxx"], _msg_handler, Guarantee.AT_LEAST_ONCE, 1.0)
        registry.register(["xxx"], _msg_handler, Guarantee.AT_LEAST_ONCE, 1.0)


def test_registry_contains_handler_specifications(
    registry: Registry[Any],
) -> None:
    registry.register(["xxx"], _msg_handler, Guarantee.AT_LEAST_ONCE, 1.0)

    for spec in registry.mapping().values():
        assert isinstance(spec, HandlerSpecification)


def test_registry_maps_handlers(
    registry: Registry[Any],
) -> None:
    xxx = HandlerSpecification[Any](
        guarantee=Guarantee.AT_LEAST_ONCE,
        delay_on_exc=1.0,
        message_handler=_msg_handler,
    )

    zzz = HandlerSpecification[Any](
        guarantee=Guarantee.NO_MORE_THAN_ONCE,
        delay_on_exc=2.0,
        message_handler=_other_msg_handler,
    )

    registry.register(
        ["xxx", "yyy"], xxx.message_handler, xxx.guarantee, xxx.delay_on_exc
    )
    registry.register(["zzz"], zzz.message_handler, zzz.guarantee, zzz.delay_on_exc)

    assert registry.mapping() == dict(xxx=xxx, yyy=xxx, zzz=zzz)


def test_subscribe(registry: Registry[Any]) -> None:
    xxx = HandlerSpecification[Any](
        guarantee=Guarantee.AT_LEAST_ONCE,
        delay_on_exc=1.0,
        message_handler=_msg_handler,
    )

    handler = registry.subscribe(
        ["xxx", "yyy"], guarantee=xxx.guarantee, delay_on_exc=xxx.delay_on_exc
    )(xxx.message_handler)

    assert handler == xxx.message_handler
    assert registry.mapping() == dict(xxx=xxx, yyy=xxx)
