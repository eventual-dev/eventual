import abc
from typing import Callable, AsyncContextManager


class InterruptWork(Exception):
    pass


class WorkUnit(abc.ABC):
    def __init__(self):
        self.was_committed = False

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError


WorkUnitFactory = Callable[[], AsyncContextManager[WorkUnit]]
