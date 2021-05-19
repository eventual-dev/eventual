"""
An implementation of the DDD entity concept.
"""
import abc
import typing
from collections import deque

from .event import Event

T = typing.TypeVar("T")


class NoPublicConstructor(abc.ABCMeta):
    """Metaclass that enforces a class to be final (i.e., subclass not allowed)
    and ensures a private constructor.

    If a class uses this metaclass like this::

        class SomeClass(metaclass=NoPublicConstructor):
            pass

    The metaclass will ensure that no sub class can be created, and that no instance
    can be initialized.

    If you try to instantiate your class (SomeClass()), a TypeError will be thrown.

    Raises
    ------
    - TypeError if a sub class or an instance is created.
    """

    def __call__(cls: typing.Type[T], *args: typing.Any, **kwargs: typing.Any) -> T:
        raise TypeError(
            f"{cls.__module__}.{cls.__qualname__} has no public constructor"
        )

    def _create(cls: typing.Type[T], *args: typing.Any, **kwargs: typing.Any) -> T:
        return super().__call__(*args, **kwargs)  # type: ignore


ID = typing.TypeVar("ID")


class Entity(typing.Generic[ID], metaclass=NoPublicConstructor):
    def __init__(self, *, unique_id: ID):
        self._unique_id = unique_id
        self._outbox: typing.Deque[Event] = deque()

    @property
    def id(self) -> ID:
        return self._unique_id

    @property
    def outbox(self) -> typing.Deque[Event]:
        return self._outbox

    def clear_outbox(self) -> typing.List[Event]:
        consumed_data = list(self._outbox)
        self._outbox.clear()
        return consumed_data

    def as_dictionary(self) -> typing.Dict[str, typing.Any]:
        return self.__dict__

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False
