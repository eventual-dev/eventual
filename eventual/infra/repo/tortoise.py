import abc
import uuid
from typing import TypeVar, Iterable, Optional, Type, Generic

from eventual.repo import (
    RepositoryAllMixin,
    RepositoryCountMixin,
    RepositoryGetMixin,
    RepositoryCreateMixin,
    RepositoryUpdateMixin,
    RepositoryDeleteMixin,
)
from eventual.infra.relation import PkUuidModel
from eventual.model import Entity

M = TypeVar("M", bound=Entity)
R = TypeVar("R", bound=PkUuidModel)


class TortoiseRepository(Generic[M, R], abc.ABC):
    @property
    @abc.abstractmethod
    def _relation_cls(self) -> Type[R]:
        raise NotImplementedError

    @abc.abstractmethod
    def store(self, obj: M) -> R:
        raise NotImplementedError

    @abc.abstractmethod
    async def reconstitute(self, obj: R) -> M:
        raise NotImplementedError


class TortoiseRepositoryAllMixin(
    RepositoryAllMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def all(self) -> Iterable[M]:
        seq = await self._relation_cls.all()
        return [await self.reconstitute(p) for p in seq]


class TortoiseRepositoryCountMixin(
    RepositoryCountMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def count(self) -> int:
        return await self._relation_cls.all().count()


class TortoiseRepositoryGetMixin(
    RepositoryGetMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def get(self, unique_id: uuid.UUID) -> Optional[M]:
        p = await self._relation_cls.filter(id=unique_id).get_or_none()
        if p is None:
            return None
        return await self.reconstitute(p)


class TortoiseRepositoryCreateMixin(
    RepositoryCreateMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def create(self, value: M) -> M:
        p = self.store(value)
        await p.save()
        return await self.reconstitute(p)


class TortoiseRepositoryUpdateMixin(
    RepositoryUpdateMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def update(self, value: M) -> Optional[M]:
        p = await self._relation_cls.filter(id=value.id).get_or_none()
        if p is None:
            return None
        p = self.store(value)
        await p.save()
        return await self.reconstitute(p)


class TortoiseRepositoryDeleteMixin(
    RepositoryDeleteMixin[M], TortoiseRepository[M, R], abc.ABC
):
    async def delete_by_id(self, unique_id: uuid.UUID) -> Optional[M]:
        p = await self._relation_cls.filter(id=unique_id).get_or_none()
        if p is None:
            return None
        await self._relation_cls.filter(id=unique_id).delete()
        return await self.reconstitute(p)


class TortoiseRepositoryMixin(
    TortoiseRepositoryAllMixin[M, R],
    TortoiseRepositoryCountMixin[M, R],
    TortoiseRepositoryGetMixin[M, R],
    TortoiseRepositoryCreateMixin[M, R],
    TortoiseRepositoryUpdateMixin[M, R],
    TortoiseRepositoryDeleteMixin[M, R],
    abc.ABC,
):
    pass
