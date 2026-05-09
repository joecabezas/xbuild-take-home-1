import uuid
import pika
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue

CONSUME_QUEUE = "normalize"
PUBLISH_QUEUE = "match"


def process(ctx: PipelineContext) -> PipelineContext:
    r = ctx.raw_input
    customer = r["customer"]
    prop = r["property"]

    findings = []
    for seq, f in enumerate(r["findings"]):
        findings.append({
            "id": f"fnd_{uuid.uuid4().hex[:12]}",
            "title": f["title"].strip(),
            "severity": f["severity"].strip().lower(),
            "notes": f.get("notes", "").strip(),
            "photos": [p for p in f.get("photos", []) if p],
            "seq": seq,
        })

    ctx.report_input = {
        "customer": {"name": customer["name"].strip(), "email": customer["email"].strip()},
        "property": {"address": prop["address"].strip(), "type": prop["type"].strip()},
        "findings": findings,
    }
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
    print(f"[normalizer] waiting for messages on '{CONSUME_QUEUE}'")
    ch.start_consuming()
