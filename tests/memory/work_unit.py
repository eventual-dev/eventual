import contextlib
from typing import AsyncGenerator, Type

from eventual.abc.work_unit import InterruptWork, WorkUnit


class MemoryWorkUnit(WorkUnit):
    def __init__(self) -> None:
        self._committed = False

    @classmethod
    @contextlib.asynccontextmanager
    async def create(
        cls: Type["MemoryWorkUnit"],
    ) -> AsyncGenerator["MemoryWorkUnit", None]:
        work_unit = MemoryWorkUnit()
        try:
            yield work_unit
            if not work_unit._committed:
                raise InterruptWork
        except InterruptWork:
            work_unit._committed = False

    async def commit(self) -> None:
        self._committed = True

    @property
    def committed(self) -> bool:
        return self._committed
