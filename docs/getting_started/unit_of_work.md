# Unit of work

Unit of work is an abstraction that represents an atomic operation – something that either happens entirely (as a unit)
or does not happen at all. If you are familiar with database transactions then you are already familiar with the concept
of unit of work.

It's useful to define such an abstraction because it gives way to multiple implementations,
which makes the concept more broad than just a database transaction. Unit of work can represent
any kind of work, not just saving data to disk. A particular implementation can even have semantics
that slightly differ from a transaction in its traditional sense.

## Creating units of work

A natural way to define a unit of work in Python is via a context manager. Every implementation of `WorkUnit` has
a context manager that yields a unit of work instance upon entry:

``` python
async with WorkUnit.create() as work_unit:
    ...
```

!!! note
    The code above will not work as is, because `WorkUnit` is an abstract class. You will have to use
    an implementation that suits your use case, e.g. [eventual-tortoise](https://github.com/eventual-dev/eventual-tortoise).

Be careful about creating nested units of work:

``` python
async with WorkUnit.create() as work_unit:
    async with WorkUnit.create() as sub_work_unit:
        ...
```

Each particular implementation is free to handle such usages differently. Generally speaking, think twice about what
you are trying to achieve with nesting.

!!! tip
    Chances are your application does not have a clear [layered structure](../design_and_internals/placeholder.md),
    which can lead to messy and rigid code.

## Committing work

A unit of work is committed upon the exit from the context manager. If an unhandled exception reaches
the unit of work context manager then work will not be committed.
This can happen for a number of reasons including you raising an exception or a particular `WorkUnit` implementation
failing to actually commit the work. Any such exceptions are reraised for you to deal with them.

!!! warning
    The context manager block shouldn't contain anything but work compatible with the
    unit of work implementation you are using. Other operations can not be properly rolled back,
    and the abstraction fails.
    
    If you have some kind of retry logic in place and you are sure that commit will eventually happen, then it should
    be fine to perform idempotent operations inside the block.

## Interrupting work

You can explicitly interrupt a unit of work by raising an `InterruptWork` exception:

``` python
async with WorkUnit.create() as work_unit:
    ...
    raise InterruptWork
    ...
```

This exception is special,
because it's suppressed by the unit of work context manager. Suppressing this exception in your code
can lead to unwanted work being committed, so always reraise it.

Another way to interrupt a unit of work is to roll it back:

``` python
async with WorkUnit.create() as work_unit:
    ...
    async work_unit.rollback()
    ...
```

!!! note
    Rolling back is equivalent to raising `InterruptWork`. In fact, this is how rolling back works, so anything
    that comes after it in the context manager block is not executed.

## Checking if unit of work was committed

After the context manager block is over you can check if work was successfully committed or not:

``` python
async with WorkUnit.create() as work_unit:
    ...
    async work_unit.rollback()
    ...
    
assert not work_unit.committed
```

!!! warning
    Checking if unit of work was committed inside the context manager block always returns `False`.
