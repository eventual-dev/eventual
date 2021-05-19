# Broker and messages

To reliably exchange events over the network we need a broker. Broker can receive and forward messages that are usually
represented as bytes. If we can encode an event object as bytes then broker can receive and forward events.

## Messages

Messages are events encoded in a particular way. You can do two things with a message:

- decode its contents
- acknowledge it

A message is never decoded into an instance of a particular event that it was produced from. The receiving side doesn't
know anything about code organization of the sender. How do you know what event is represented by a message then? There
is a special `subject` property which is derived from a class name. For example, a message that encodes a
`MoneyReceived` event has a `"money-received"` subject.

## Brokers

A broker can do two things:
- push messages to the receiver
- send messages from the sender (with a confirmation for each one)

In `eventual` every message is guaranteed to be sent to the broker at least once.
