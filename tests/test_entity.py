import uuid
from collections import deque

import pytest

from tests.model import Building, Person


def test_entity_equality() -> None:
    person = Person.create()
    building = Building.from_floor_count(2)
    another_building = Building.from_floor_count(2)

    assert building == building
    assert building != person
    assert building != another_building


def test_entity_as_dictionary() -> None:
    building = Building.from_floor_count(2)

    assert building.as_dictionary() == dict(
        _outbox=deque(), _unique_id=building.id, floor_count=2
    )


def test_entity_has_no_constructor() -> None:
    with pytest.raises(TypeError):
        _ = Building(unique_id=uuid.uuid4(), floor_count=1)
