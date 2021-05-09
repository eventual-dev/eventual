import contextlib
from typing import AsyncGenerator, Type

from eventual.work_unit import InterruptWork, WorkUnit


class MemoryWorkUnit(WorkUnit):
    def __init__(self) -> None:
        self._commit = False

    @classmethod
    @contextlib.asynccontextmanager
    async def create(
        cls: Type["MemoryWorkUnit"],
    ) -> AsyncGenerator["MemoryWorkUnit", None]:
        work_unit = MemoryWorkUnit()
        try:
            yield work_unit
            if not work_unit._commit:
                raise InterruptWork
        except InterruptWork:
            work_unit._commit = False

    async def commit(self) -> None:
        self._commit = True

    @property
    def committed(self) -> bool:
        return self._commit
