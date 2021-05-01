import contextlib
from typing import AsyncGenerator

from tortoise.transactions import in_transaction

from .abc import UnitOfWork, WorkInterrupted


class TortoiseUnitOfWork(UnitOfWork):
    async def rollback(self):
        raise WorkInterrupted


@contextlib.asynccontextmanager
async def tortoise_unit_of_work() -> AsyncGenerator[TortoiseUnitOfWork, None]:
    try:
        async with in_transaction("default"):
            uow = TortoiseUnitOfWork()
            yield uow
            uow.was_committed = True
    except WorkInterrupted:
        pass
