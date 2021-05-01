import contextlib
from typing import AsyncGenerator

from tortoise.transactions import in_transaction

from eventual.work_unit import WorkUnit, InterruptWork


class TortoiseWorkUnit(WorkUnit):
    async def rollback(self):
        raise InterruptWork


@contextlib.asynccontextmanager
async def tortoise_unit_of_work() -> AsyncGenerator[TortoiseWorkUnit, None]:
    try:
        async with in_transaction("default"):
            uow = TortoiseWorkUnit()
            yield uow
            uow.was_committed = True
    except InterruptWork:
        pass
