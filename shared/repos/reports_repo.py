import json
import uuid
from datetime import datetime, timezone
from shared.db import transaction


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def save_report(raw_input: dict) -> tuple[str, list[str]]:
    """Persist report + findings. Returns (report_id, [finding_id, ...])."""
    report_id = _new_id("rpt")
    now = datetime.now(timezone.utc).isoformat()

    with transaction() as conn:
        conn.execute(
            "INSERT INTO reports (id, created_at, raw_json) VALUES (?, ?, ?)",
            (report_id, now, json.dumps(raw_input)),
        )
        finding_ids = []
        for seq, f in enumerate(raw_input.get("findings", [])):
            fid = _new_id("fnd")
            conn.execute(
                """INSERT INTO findings (id, report_id, seq, title, severity, notes, photos_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (fid, report_id, seq, f["title"], f["severity"],
                 f.get("notes", ""), json.dumps(f.get("photos", []))),
            )
            finding_ids.append(fid)

    return report_id, finding_ids


def get_report(report_id: str) -> dict | None:
    from shared.db import get_connection
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            return None
        findings = conn.execute(
            "SELECT * FROM findings WHERE report_id = ? ORDER BY seq", (report_id,)
        ).fetchall()
        report = json.loads(row["raw_json"])
        report["reportId"] = row["id"]
        report["createdAt"] = row["created_at"]
        report["findings"] = [
            {
                "id": f["id"],
                "title": f["title"],
                "severity": f["severity"],
                "notes": f["notes"],
                "photos": json.loads(f["photos_json"]),
            }
            for f in findings
        ]
        return report
    finally:
        conn.close()


def get_finding_ids(report_id: str) -> list[str]:
    from shared.db import get_connection
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id FROM findings WHERE report_id = ? ORDER BY seq", (report_id,)
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()
