import pytest

from tests.memory.repository import MemoryRepositoryMixin
from tests.model import Building


class BuildingMemoryRepository(MemoryRepositoryMixin[Building]):
    pass


@pytest.mark.anyio
async def test_repository() -> None:
    repo = BuildingMemoryRepository()

    building = Building.from_floor_count(floor_count=1)
    await repo.create(building)
    assert await repo.count() == 1

    retrieved_building = await repo.get(building.id)
    assert retrieved_building is not None
    assert retrieved_building.as_dictionary() == building.as_dictionary()

    await repo.delete(retrieved_building)
    assert await repo.count() == 0
