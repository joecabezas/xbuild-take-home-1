import pika
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue
from shared.db import init_schema
from shared.models import ProposalDraft, PricedLineItem
from shared.repos.reports_repo import get_finding_ids
from shared.repos.proposals_repo import save_proposal

CONSUME_QUEUE = "assemble"


def process(ctx: PipelineContext) -> PipelineContext:
    items = ctx.priced_items
    address = ctx.report_input["property"]["address"]
    total = sum(i["estimated_cost"] for i in items)

    finding_ids = get_finding_ids(ctx.report_id)

    draft = ProposalDraft(
        report_id=ctx.report_id,
        summary=f"Exterior repairs for {address}",
        line_items=[PricedLineItem(**{k: v for k, v in item.items() if k != "finding_id"})
                    for item in items],
        total=total,
    )

    proposal_id = save_proposal(draft, finding_ids)
    ctx.proposal_draft = {"proposal_id": proposal_id}
    ctx.status = "complete"
    return ctx


def callback(ch, method, _properties, body):
    ctx = PipelineContext.from_json(body)
    try:
        ctx = process(ctx)
        ch.basic_publish(
            exchange="",
            routing_key="results",
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
    init_schema()
    conn = get_connection()
    ch = conn.channel()
    for q in [CONSUME_QUEUE, "results"]:
        declare_queue(ch, q)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=CONSUME_QUEUE, on_message_callback=callback)
    print(f"[assembler] waiting for messages on '{CONSUME_QUEUE}'")
    ch.start_consuming()
