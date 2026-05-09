import pika
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue
from catalog import match

CONSUME_QUEUE = "match"
PUBLISH_QUEUE = "price"


def process(ctx: PipelineContext) -> PipelineContext:
    matches = []
    for f in ctx.report_input["findings"]:
        item, reason = match(f["title"], f["notes"])
        matches.append({
            "finding_id": f["id"],
            "source_finding": f["title"],
            "code": item.code,
            "category": item.category,
            "description": item.description,
            "base_price": item.base_price,
            "match_reason": reason,
            "severity": f["severity"],
            "photos": f["photos"],
        })
    ctx.matches = matches
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
            routing_key="results",
            body=ctx.to_json(),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


if __name__ == "__main__":
    conn = get_connection()
    ch = conn.channel()
    for q in [CONSUME_QUEUE, PUBLISH_QUEUE, "results"]:
        declare_queue(ch, q)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)
    print(f"[matcher] waiting for messages on '{CONSUME_QUEUE}'")
    ch.start_consuming()
