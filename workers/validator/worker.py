import pika
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue

CONSUME_QUEUE = "validate"
PUBLISH_QUEUE = "normalize"
VALID_SEVERITIES = {"low", "medium", "high"}


def process(ctx: PipelineContext) -> PipelineContext:
    r = ctx.raw_input
    errors = []

    customer = r.get("customer") or {}
    if not customer.get("name", "").strip():
        errors.append("customer.name is required")
    if not customer.get("email", "").strip():
        errors.append("customer.email is required")

    prop = r.get("property") or {}
    if not prop.get("address", "").strip():
        errors.append("property.address is required")
    if not prop.get("type", "").strip():
        errors.append("property.type is required")

    findings = r.get("findings")
    if not findings:
        errors.append("findings must be a non-empty array")
    else:
        for i, f in enumerate(findings):
            if f.get("severity", "").lower() not in VALID_SEVERITIES:
                errors.append(f"findings[{i}].severity must be low, medium, or high")

    if errors:
        raise ValueError("; ".join(errors))

    ctx.validated = True
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
    print(f"[validator] waiting for messages on '{CONSUME_QUEUE}'")
    ch.start_consuming()
