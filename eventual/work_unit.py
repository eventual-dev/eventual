import abc
from typing import AsyncContextManager, Callable


class InterruptWork(Exception):
    pass


class WorkUnit(abc.ABC):
    def __init__(self) -> None:
        self.was_committed = False

    @abc.abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


WorkUnitFactory = Callable[[], AsyncContextManager[WorkUnit]]
