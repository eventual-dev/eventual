import uuid
from typing import TypeVar, Iterable, Optional, Generic, Dict

from eventual.repo import (
    RepositoryAllMixin,
    RepositoryCountMixin,
    RepositoryGetMixin,
    RepositoryCreateMixin,
    RepositoryUpdateMixin,
    RepositoryDeleteMixin,
)
from eventual.model import Entity

M = TypeVar("M", bound=Entity)


class MemoryRepository(Generic[M]):
    def __init__(self):
        self._mapping: Dict[uuid.UUID, M] = {}


class MemoryRepositoryAllMixin(RepositoryAllMixin[M], MemoryRepository[M]):
    async def all(self) -> Iterable[M]:
        return list(self._mapping.values())


class MemoryRepositoryCountMixin(RepositoryCountMixin[M], MemoryRepository[M]):
    async def count(self) -> int:
        return len(self._mapping)


class MemoryRepositoryGetMixin(RepositoryGetMixin[M], MemoryRepository[M]):
    async def get(self, unique_id: uuid.UUID) -> Optional[M]:
        return self._mapping.get(unique_id)


class MemoryRepositoryCreateMixin(RepositoryCreateMixin[M], MemoryRepository[M]):
    async def create(self, value: M) -> M:
        self._mapping[value.id] = value
        return value


class MemoryRepositoryUpdateMixin(RepositoryUpdateMixin[M], MemoryRepository[M]):
    async def update(self, value: M) -> Optional[M]:
        m = self._mapping.get(value.id)
        if m is None:
            return None
        self._mapping[value.id] = value
        return value


class MemoryRepositoryDeleteMixin(RepositoryDeleteMixin[M], MemoryRepository[M]):
    async def delete_by_id(self, unique_id: uuid.UUID) -> Optional[M]:
        m = self._mapping.get(unique_id)
        if m is None:
            return None
        return self._mapping.pop(unique_id)


class MemoryRepositoryMixin(
    MemoryRepositoryAllMixin[M],
    MemoryRepositoryCountMixin[M],
    MemoryRepositoryGetMixin[M],
    MemoryRepositoryCreateMixin[M],
    MemoryRepositoryUpdateMixin[M],
    MemoryRepositoryDeleteMixin[M],
):
    pass
