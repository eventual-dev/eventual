import contextlib
from typing import AsyncGenerator

from eventual.work_unit import WorkUnit, InterruptWork


class MemoryWorkUnit(WorkUnit):
    def __init__(self) -> None:
        super().__init__()

    async def rollback(self) -> None:
        raise InterruptWork


@contextlib.asynccontextmanager
async def create_work_unit() -> AsyncGenerator[MemoryWorkUnit, None]:
    try:
        uow = MemoryWorkUnit()
        yield uow
        uow.was_committed = True
    except InterruptWork:
        pass
