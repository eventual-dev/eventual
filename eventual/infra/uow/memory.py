import contextlib
from typing import AsyncGenerator

from eventual.work_unit import WorkUnit, InterruptWork


class MemoryWorkUnit(WorkUnit):
    def __init__(self):
        super().__init__()

    async def rollback(self):
        raise InterruptWork


@contextlib.asynccontextmanager
async def memory_unit_of_work() -> AsyncGenerator[MemoryWorkUnit, None]:
    try:
        uow = MemoryWorkUnit()
        yield uow
        uow.was_committed = True
    except InterruptWork:
        pass
