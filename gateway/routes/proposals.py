import asyncio
import uuid
import os
import aio_pika
from fastapi import APIRouter, HTTPException
from shared.context import PipelineContext
from shared.repos.reports_repo import get_report
from shared.repos.proposals_repo import get_proposal, list_proposals
from schemas import ProposalCreatedResponse

router = APIRouter()

PIPELINE_TIMEOUT = 30
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")


async def get_amqp_connection():
    return await aio_pika.connect_robust(f"amqp://guest:guest@{RABBITMQ_HOST}/")


@router.post("/reports/{report_id}/generate-proposal",
             response_model=ProposalCreatedResponse, status_code=202)
async def generate_proposal(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    job_id = uuid.uuid4().hex
    reply_queue_name = f"reply_{job_id}"

    ctx = PipelineContext(
        job_id=job_id,
        report_id=report_id,
        raw_input=report,
    )

    result_future: asyncio.Future = asyncio.get_event_loop().create_future()

    connection = await get_amqp_connection()
    try:
        channel = await connection.channel()

        await channel.declare_queue("validate", durable=True)
        reply_queue = await channel.declare_queue(
            reply_queue_name, durable=False, exclusive=True, auto_delete=True
        )

        async def on_result(message: aio_pika.IncomingMessage):
            async with message.process():
                if not result_future.done():
                    result_future.set_result(PipelineContext.from_json(message.body))

        await reply_queue.consume(on_result)

        await channel.default_exchange.publish(
            aio_pika.Message(
                body=ctx.to_json(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key="validate",
        )

        try:
            result_ctx = await asyncio.wait_for(result_future, timeout=PIPELINE_TIMEOUT)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Pipeline timed out")
    finally:
        await connection.close()

    if result_ctx.status == "failed":
        raise HTTPException(status_code=422, detail=result_ctx.errors)

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
