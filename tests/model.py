import uuid

from eventual.model import Entity, Event


class SomethingHappened(Event):
    content: str = "something"


class Person(Entity):
    @classmethod
    def create(cls) -> "Person":
        return cls._create(unique_id=uuid.uuid4())

    def new_day(self) -> None:
        self._outbox.append(SomethingHappened())


class Building(Entity[uuid.UUID]):
    def __init__(self, *, unique_id: uuid.UUID, floor_count: int):
        super().__init__(unique_id=unique_id)
        self.floor_count = floor_count

    @classmethod
    def from_floor_count(cls, floor_count: int) -> "Building":
        return cls._create(unique_id=uuid.uuid4(), floor_count=floor_count)
