import uuid
from datetime import datetime, timezone
from shared.db import transaction, get_connection
from shared.models import ProposalDraft


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def save_proposal(draft: ProposalDraft, finding_ids: list[str]) -> str:
    """Persist a ProposalDraft. Returns proposal_id."""
    proposal_id = _new_id("prop")
    now = datetime.now(timezone.utc).isoformat()

    with transaction() as conn:
        version = (conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM proposals WHERE report_id = ?",
            (draft.report_id,),
        ).fetchone()[0] or 0) + 1

        conn.execute(
            """INSERT INTO proposals (id, report_id, version, created_at, summary, total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (proposal_id, draft.report_id, version, now, draft.summary, draft.total),
        )

        for seq, (item, fid) in enumerate(zip(draft.line_items, finding_ids)):
            conn.execute(
                """INSERT INTO proposal_line_items
                   (id, proposal_id, seq, finding_id, code, category, description,
                    estimated_cost, source_finding, match_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (_new_id("li"), proposal_id, seq, fid, item.code, item.category,
                 item.description, item.estimated_cost, item.source_finding, item.match_reason),
            )

    return proposal_id


def get_proposal(proposal_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
        if not row:
            return None
        items = conn.execute(
            "SELECT * FROM proposal_line_items WHERE proposal_id = ? ORDER BY seq",
            (proposal_id,),
        ).fetchall()
        return _format(row, items)
    finally:
        conn.close()


def get_latest_proposal(report_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM proposals WHERE report_id = ? ORDER BY version DESC LIMIT 1",
            (report_id,),
        ).fetchone()
        if not row:
            return None
        items = conn.execute(
            "SELECT * FROM proposal_line_items WHERE proposal_id = ? ORDER BY seq",
            (row["id"],),
        ).fetchall()
        return _format(row, items)
    finally:
        conn.close()


def list_proposals(report_id: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM proposals WHERE report_id = ? ORDER BY version",
            (report_id,),
        ).fetchall()
        return [
            {"proposalId": r["id"], "version": r["version"],
             "createdAt": r["created_at"], "total": r["total"]}
            for r in rows
        ]
    finally:
        conn.close()


def _format(row, items) -> dict:
    return {
        "proposalId": row["id"],
        "reportId": row["report_id"],
        "version": row["version"],
        "summary": row["summary"],
        "lineItems": [
            {
                "code": i["code"],
                "category": i["category"],
                "description": i["description"],
                "estimatedCost": i["estimated_cost"],
                "sourceFinding": i["source_finding"],
                "matchReason": i["match_reason"],
            }
            for i in items
        ],
        "total": row["total"],
    }
