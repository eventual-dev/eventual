import contextlib
from typing import AsyncGenerator

from .abc import UnitOfWork, WorkInterrupted


class MemoryUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__()

    async def rollback(self):
        raise WorkInterrupted


@contextlib.asynccontextmanager
async def memory_unit_of_work() -> AsyncGenerator[MemoryUnitOfWork, None]:
    try:
        uow = MemoryUnitOfWork()
        yield uow
        uow.was_committed = True
    except WorkInterrupted:
        pass
