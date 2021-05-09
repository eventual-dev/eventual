"""
A Python variation of the abstraction often called "unit of work".
"""
import abc
from typing import AsyncContextManager, Type, TypeVar

WU = TypeVar("WU", bound="WorkUnit")


class InterruptWork(Exception):
    """
    An exception that is raised to signal that work unit
    should be interrupted similar to StopIteration.

    Avoid catching this exception, because doing so can lead to unwanted work being committed.
    """


class WorkUnit(abc.ABC):
    """
    Describes a work unit that can be either committed or rolled back entirely. Work unit
    should be created via the `WorkUnit.create()` context manager. Any work contained in the block is considered part
    of the work unit. What exactly constitutes work should be clear from the context.

    Nothing should be committed by default. Work is committed upon exit from the block only if:
     - `work_unit.commit()` was called
     - `InterruptWork` was not raised inside the block.
    """

    @classmethod
    @abc.abstractmethod
    def create(cls: Type[WU]) -> AsyncContextManager[WU]:
        """
        Begins the block that contains work considered to be a part of the work unit.

        After the block is over use `work_unit.committed` to check if the work has been committed.

        Returns:
            A context manager that produces a work unit upon entry and commits work upon exit.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def commit(self) -> None:
        """
        Communicates that the work contained in the block should be committed upon exit from the block.

        The work includes everything in the block, before and after the `.commit()`. If `InterruptWork` is raised
        before the block is over then work is not committed.

        Returns:
            None.
        """
        raise NotImplementedError

    @property
    def committed(self) -> bool:
        """
        A property that indicates if the work was actually committed successfully upon exit from the block.

        Returns:
            True if the work unit has been committed, False otherwise.
        """
        raise NotImplementedError

    async def rollback(self) -> None:
        """
        Raises `InterruptWork`.

        Returns:
            None.
        """
        raise InterruptWork
