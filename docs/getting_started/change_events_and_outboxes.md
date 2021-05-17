# Change, events and outboxes

Any event, once it happened, can not change, because it is in the past. Hence, it's very convenient to model events
as instances of a frozen dataclass. Every event is uniquely identifiable by an id and carries a
`occured_on` timestamp in UTC.

```python
from dataclasses import dataclass

from eventual.model import Event


@dataclass(frozen=True)
class EmailChanged(Event):
    pass
```

Events are a product of change. Things that change in a meaningful way have an identity. The identity conceptually links
the series of values into one changing thing. In domain-driven design things with identity are known as entities.

```python
from eventual.model import Entity


class User(Entity):
    pass
```

We often want to react to a particular entity changing. For that purpose entities have outboxes they put events in. 

```python
from eventual.model import Entity


class User(Entity):
    def change_email(self):
        ...
        self._outbox.append(EmailChanged())
```
