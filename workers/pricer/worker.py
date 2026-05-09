import pika
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue

CONSUME_QUEUE = "price"
PUBLISH_QUEUE = "assemble"

SEVERITY_MULT = {"low": 0.8, "medium": 1.0, "high": 1.5}


def price(base_price: int, severity: str, photos: list) -> int:
    mult = SEVERITY_MULT[severity]
    photo_mod = min(len(photos) * 25, 150)
    raw = base_price * mult + photo_mod
    return round(raw / 10) * 10


def process(ctx: PipelineContext) -> PipelineContext:
    ctx.priced_items = [
        {
            "finding_id": m["finding_id"],
            "source_finding": m["source_finding"],
            "code": m["code"],
            "category": m["category"],
            "description": m["description"],
            "estimated_cost": price(m["base_price"], m["severity"], m["photos"]),
            "match_reason": m["match_reason"],
        }
        for m in ctx.matches
    ]
    return ctx


def callback(ch, method, _properties, body):
    ctx = PipelineContext.from_json(body)
    try:
        ctx = process(ctx)
        ch.basic_publish(
            exchange="",
            routing_key=PUBLISH_QUEUE,
            body=ctx.to_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        ctx.status = "failed"
        ctx.error = str(e)
        ch.basic_publish(
            exchange="",
            routing_key=f"reply_{ctx.job_id}",
            body=ctx.to_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


if __name__ == "__main__":
    conn = get_connection()
    ch = conn.channel()
    for q in [CONSUME_QUEUE, PUBLISH_QUEUE]:
        declare_queue(ch, q)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)
    print(f"[pricer] waiting for messages on '{CONSUME_QUEUE}'")
    ch.start_consuming()
