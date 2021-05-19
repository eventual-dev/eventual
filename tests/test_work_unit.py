import pytest

from tests.memory.work_unit import MemoryWorkUnit


@pytest.mark.anyio
async def test_rollback_means_no_commit() -> None:
    async with MemoryWorkUnit.create() as work_unit:
        await work_unit.rollback()

    assert not work_unit.committed
