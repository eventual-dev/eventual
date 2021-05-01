import abc
from typing import Callable, AsyncContextManager


class WorkInterrupted(Exception):
    pass


class UnitOfWork(abc.ABC):
    def __init__(self):
        self.was_committed = False

    @abc.abstractmethod
    async def rollback(self):
        raise NotImplementedError


UnitOfWorkFactory = Callable[[], AsyncContextManager[UnitOfWork]]
