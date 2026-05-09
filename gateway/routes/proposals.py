import uuid
import pika
from fastapi import APIRouter, HTTPException
from shared.context import PipelineContext
from shared.queue_client import get_connection, declare_queue
from shared.repos.reports_repo import get_report
from shared.repos.proposals_repo import get_proposal, get_latest_proposal, list_proposals
from gateway.schemas import ProposalCreatedResponse

router = APIRouter()

PIPELINE_TIMEOUT = 30  # seconds


@router.post("/reports/{report_id}/generate-proposal",
             response_model=ProposalCreatedResponse, status_code=202)
def generate_proposal(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    job_id = uuid.uuid4().hex
    reply_queue = f"reply_{job_id}"

    ctx = PipelineContext(
        job_id=job_id,
        report_id=report_id,
        raw_input=report,
    )

    mq_conn = get_connection()
    ch = mq_conn.channel()
    declare_queue(ch, "validate")
    ch.queue_declare(queue=reply_queue, durable=False, exclusive=True, auto_delete=True)

    ch.basic_publish(
        exchange="",
        routing_key="validate",
        body=ctx.to_json(),
        properties=pika.BasicProperties(
            delivery_mode=2,
            reply_to=reply_queue,
        ),
    )

    result_ctx: PipelineContext | None = None

    def on_result(ch, method, _properties, body):
        nonlocal result_ctx
        result_ctx = PipelineContext.from_json(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        ch.stop_consuming()

    ch.basic_consume(queue=reply_queue, on_message_callback=on_result)
    mq_conn.process_data_events(time_limit=PIPELINE_TIMEOUT)

    mq_conn.close()

    if result_ctx is None:
        raise HTTPException(status_code=504, detail="Pipeline timed out")

    if result_ctx.status == "failed":
        status = 422 if "required" in (result_ctx.error or "") else 500
        raise HTTPException(status_code=status, detail=result_ctx.error)

    proposal_id = result_ctx.proposal_draft["proposal_id"]
    return {"proposalId": proposal_id}


@router.get("/proposals/{proposal_id}")
def fetch_proposal(proposal_id: str):
    proposal = get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.get("/reports/{report_id}/proposals")
def list_report_proposals(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return list_proposals(report_id)
