from typing import AsyncIterable, AsyncGenerator, Optional, Callable

import aio_pika
import orjson

from eventual.infra.exchange.abc import Message, MessageExchange, EventBody


class AmqpMessage(Message):
    def __init__(self, message: aio_pika.IncomingMessage):
        self._body = orjson.loads(message.body)
        self._message = message

    @property
    def body(self) -> EventBody:
        return self._body

    def acknowledge(self):
        self._message.ack()


class AmqpMessageExchange(MessageExchange):
    def __init__(
        self,
        amqp_dsn: str,
        amqp_exchange: str,
        amqp_queue: str,
        routing_key_from_type: Optional[Callable[[str], str]] = None,
    ):
        self.amqp_dsn = amqp_dsn
        self.amqp_exchange = amqp_exchange
        self.amqp_queue = amqp_queue

        def default_routing_key_from_type(event_type: str) -> str:
            return f"{self.amqp_queue}.{event_type}"

        self.routing_key_from_type = default_routing_key_from_type

    async def _message_stream(self, connection) -> AsyncGenerator[AmqpMessage, None]:
        channel: aio_pika.Channel = await connection.channel()
        async with channel:
            exchange = await channel.declare_exchange(
                self.amqp_exchange, aio_pika.ExchangeType.FANOUT
            )
            queue: aio_pika.Queue = await channel.declare_queue(
                self.amqp_queue, durable=True
            )
            await queue.bind(exchange)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    yield AmqpMessage(message)

    async def message_stream(self) -> AsyncIterable[AmqpMessage]:
        connection: aio_pika.RobustConnection = await aio_pika.connect_robust(
            self.amqp_dsn
        )

        async with connection:
            return self._message_stream(connection)

    async def send_event_body_stream(self, event_body_stream: AsyncIterable[EventBody]):
        connection: aio_pika.RobustConnection = await aio_pika.connect_robust(
            self.amqp_dsn
        )

        async with connection:
            channel: aio_pika.Channel = await connection.channel(
                publisher_confirms=True
            )
            exchange = await channel.declare_exchange(
                self.amqp_exchange, aio_pika.ExchangeType.FANOUT
            )

            async for event_body in event_body_stream:
                event_type = event_body["type"]
                await exchange.publish(
                    aio_pika.Message(
                        body=orjson.dumps(event_body),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=self.routing_key_from_type(event_type),
                )
