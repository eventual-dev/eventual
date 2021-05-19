import abc
import uuid
from typing import Generic, Iterable, Optional, TypeVar

from eventual.model import Entity

M = TypeVar("M", bound=Entity)


class RepositoryAllMixin(Generic[M], abc.ABC):
    @abc.abstractmethod
    async def all(self) -> Iterable[M]:
        raise NotImplementedError


class RepositoryCountMixin(Generic[M], abc.ABC):
    @abc.abstractmethod
    async def count(self) -> int:
        raise NotImplementedError


class RepositoryGetMixin(Generic[M], abc.ABC):
    @abc.abstractmethod
    async def get(self, unique_id: uuid.UUID) -> Optional[M]:
        raise NotImplementedError


class RepositoryCreateMixin(Generic[M], abc.ABC):
    @abc.abstractmethod
    async def create(self, value: M) -> M:
        raise NotImplementedError


class RepositoryUpdateMixin(Generic[M], abc.ABC):
    @abc.abstractmethod
    async def update(self, value: M) -> Optional[M]:
        raise NotImplementedError


class RepositoryDeleteMixin(Generic[M], abc.ABC):
    async def delete(self, value: M) -> Optional[M]:
        return await self.delete_by_id(value.id)

    @abc.abstractmethod
    async def delete_by_id(self, unique_id: uuid.UUID) -> Optional[M]:
        raise NotImplementedError


class RepositoryMixin(
    RepositoryAllMixin[M],
    RepositoryCountMixin[M],
    RepositoryGetMixin[M],
    RepositoryCreateMixin[M],
    RepositoryUpdateMixin[M],
    RepositoryDeleteMixin[M],
    abc.ABC,
):
    pass
