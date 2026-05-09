import os
import time
import pika


def get_connection() -> pika.BlockingConnection:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    for attempt in range(10):
        try:
            return pika.BlockingConnection(pika.ConnectionParameters(
                host=host,
                heartbeat=60,
                blocked_connection_timeout=30,
            ))
        except pika.exceptions.AMQPConnectionError:
            if attempt == 9:
                raise
            time.sleep(3)


def declare_queue(channel: pika.adapters.blocking_connection.BlockingChannel, name: str) -> None:
    channel.queue_declare(queue=name, durable=True)


QUEUES = ["validate", "normalize", "match", "price", "assemble", "results"]
