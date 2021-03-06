# Thoughts on retrying

Suppose a service called A produces a message M. A service called B
wants to send an email for every such message M that it gets.

B uses a REST API to submit letters to be sent. What happens if that API is not available at the moment that B gets M and tries to handle it?

In the client-server model B doesn't get a message from A, but instead A sends a request to B. If B can't handle the request, it indicates failure to A by sending an appropriate HTTP response code. In this case it's on A to retry whatever it's trying to achieve via B at a later time. But how do we deal with these kinds of failures when messages are involved?

One of the great advantages of message driven systems is that A doesn't have to know anything about B. So it would be unwise to involve A in any way in case B fails to handle M.

Furthermore, one of the design goals of this particular library is to never lose a message, which means B can't just drop M and move on. M has to be stored somewhere where B (and only B, because other services might not have failed to handle M) has access to it and then M has to be retrieved and retired by B.

Taking into account that B may actually be deployed as multiple pods there are two such places:

- B's database
- B's queue

One of the primary concerns in designing the retry flow is to make sure that it's not possible to overwhelm the system. If a retry operation can lead to a cascade of errors then the entire system can collapse.

It's also important to actually delay a retry attempt, to give the system a chance to recover. Retrying over and over immediately can also lead to a collapse.

## Queue

Let's explore the queue option. There are two points of interest:

1. Dispatcher checking if M was already handled by B,
2. B marking M as handled with respect to a particular guarantee.

If M was already handled then dispatcher acknowledges the message as if it was handled (because it was) and doesn't in fact dispatch it.

If B raises an exception during the handling of M, M is scheduled to be sent by B at some point in the future. It will be sent as is to everyone, as if it was sent by A again.

If there are other services besides B that failed to handle M, they will resend it to. The case of *several* services failing to handle a message is actually common, that happens when a common dependency is unavailable.

There is always a possiblity that M will be sent to the queue multiple times, this is not directly related to retries. We have idempotency keys and different guarantees exactly for that. Every service that handled M successfully the first time will ignore it. But we have a situation in which a failure can lead from one M message to as many M messages as there are services that failed, so we have to be careful to prevent any possibility that the number failures will grow exponentially.

### Sequential processing

Suppose that B gets M two times (M1 and M2) sequentially meaning first it runs points 1 and 2 for M1 and only then does the same for M2. In that case dispatcher will silently acknowledge M2 and move on.

### Concurrent processing

Suppose now that B gets M two times (M1 and M2) concurrently meaning that before it runs 2 for M1 it runs 1 for M2. Handling M1 and M2 becomes a race. The race is won by the thread that first marks M as handled in the database. 