[comment]: <> (# Entities and events)

[comment]: <> (`eventual` includes two important concepts that you can be familiar with if you dabbled with DDD before. Entities)

[comment]: <> (represent mutable things that have an immutable identity. Events represent things that happen in your system and cause)

[comment]: <> (changes and interactions.)

[comment]: <> (## Entities)

[comment]: <> (Imagine you have a blue car, and one day you repaint it green. Is it still the same car? Well, of course it is the same)

[comment]: <> (car, it just has a different color paint. How do you express this idea in code? If you were to represent your car)

[comment]: <> (as a simple dictionary with keys corresponding to your car's attributes, then Python's `==` operator would happily)

[comment]: <> (let you know that your cat painted green is, in fact, not the same car. A dataclass representation would give the same)

[comment]: <> (effect.)

[comment]: <> (On the other hand, imagine you and your buddy got yourselves matching cars. Everything about them is the same: they are)

[comment]: <> (the same model, the same color and both new. Are they the same car though? Clearly, they are two different cars. Unfortunately,)

[comment]: <> (`==` operator would disagree. We have to be able to explain the notion of identity in code.)

[comment]: <> (This documentation is not the best place to go into why it's important to clearly track identity in you system. You can)

[comment]: <> (learn about it more in any DDD book that you have access to. What's important here about `Entity` is that it's designed)

[comment]: <> (to track identity, which helps to conceptually link the series of values into one changing thing.)

[comment]: <> (`Entity` is generic over the id type. It can be anything, but it is commonplace to use a UUID. When you check if one)

[comment]: <> (entity is equal to another, only two things are checked: that the types match and that ids are equal.)

[comment]: <> (## Events)

[comment]: <> (Every event has a number of attributes. Let's look at an example:)

[comment]: <> (```python)

[comment]: <> (from dataclasses import dataclass)

[comment]: <> (from eventual.model import Event)


[comment]: <> (@dataclass&#40;frozen=True&#41;)

[comment]: <> (class EmailChanged&#40;Event&#41;:)
    
[comment]: <> (```)

[comment]: <> (Once event happened, can not change. Hence, it's very convenient to model events as instances of a frozen dataclass.)

[comment]: <> (Every event is uniquely identifiable by an id and carries an `occured_on` timestamp in UTC.)

[comment]: <> (Events are tightly bound to change and interaction. Things that change in a meaningful way have an identity. The)

[comment]: <> (identity conceptually links the series of values into one changing thing. In domain-driven design things with identity)

[comment]: <> (are known as entities.)

[comment]: <> (```python)

[comment]: <> (from eventual.model import Entity)


[comment]: <> (class User&#40;Entity&#41;:)

[comment]: <> (    pass)

[comment]: <> (```)

[comment]: <> (We often want to react to a particular entity changing. For that purpose entities have outboxes they put events in.)

[comment]: <> (```python)

[comment]: <> (from eventual.model import Entity)


[comment]: <> (class User&#40;Entity&#41;:)

[comment]: <> (    def change_email&#40;self&#41;:)

[comment]: <> (        ...)

[comment]: <> (        self._outbox.append&#40;EmailChanged&#40;&#41;&#41;)

[comment]: <> (```)
