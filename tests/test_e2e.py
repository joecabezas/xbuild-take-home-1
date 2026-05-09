"""
End-to-end tests against the running stack (docker-compose up).
Skipped automatically when the gateway is not reachable.

Run:
    pytest tests/test_e2e.py -v
"""
import pytest
import httpx

BASE = "http://localhost:8000"

VALID_REPORT = {
    "customer": {"name": "Jane Smith", "email": "jane@example.com"},
    "property": {"address": "123 Main St, Austin, TX", "type": "single_family"},
    "findings": [
        {
            "title": "Missing shingles",
            "severity": "high",
            "notes": "Visible damage on north slope",
            "photos": ["photo-1.jpg", "photo-2.jpg"],
        },
        {
            "title": "Clogged gutters",
            "severity": "medium",
            "notes": "",
            "photos": [],
        },
    ],
}


def gateway_available():
    try:
        httpx.get(f"{BASE}/docs", timeout=2)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not gateway_available(), reason="Gateway not reachable — run docker-compose up"
)


# ── helpers ────────────────────────────────────────────────────────────────────

def create_report(payload=None) -> str:
    r = httpx.post(f"{BASE}/reports", json=payload or VALID_REPORT, timeout=10)
    assert r.status_code == 201, r.text
    report_id = r.json()["reportId"]
    assert report_id.startswith("rpt_")
    return report_id


def generate_proposal(report_id: str) -> str:
    r = httpx.post(f"{BASE}/reports/{report_id}/generate-proposal", timeout=35)
    assert r.status_code == 202, r.text
    proposal_id = r.json()["proposalId"]
    assert proposal_id.startswith("prop_")
    return proposal_id


# ── report CRUD ────────────────────────────────────────────────────────────────

def test_create_report_returns_report_id():
    report_id = create_report()
    assert report_id.startswith("rpt_")


def test_get_report_returns_stored_data():
    report_id = create_report()
    r = httpx.get(f"{BASE}/reports/{report_id}", timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert body["customer"]["name"] == "Jane Smith"
    assert body["property"]["address"] == "123 Main St, Austin, TX"
    assert len(body["findings"]) == 2


def test_get_report_not_found():
    r = httpx.get(f"{BASE}/reports/rpt_doesnotexist", timeout=10)
    assert r.status_code == 404


# ── proposal generation ────────────────────────────────────────────────────────

def test_generate_proposal_returns_proposal_id():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)
    assert proposal_id.startswith("prop_")


def test_generate_proposal_not_found():
    r = httpx.post(f"{BASE}/reports/rpt_doesnotexist/generate-proposal", timeout=10)
    assert r.status_code == 404


def test_proposal_structure():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    assert r.status_code == 200
    body = r.json()

    assert body["proposalId"] == proposal_id
    assert body["reportId"] == report_id
    assert "summary" in body
    assert "123 Main St, Austin, TX" in body["summary"]
    assert isinstance(body["lineItems"], list)
    assert isinstance(body["total"], int)
    assert body["total"] > 0


def test_proposal_one_line_item_per_finding():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    body = r.json()

    assert len(body["lineItems"]) == len(VALID_REPORT["findings"])


def test_proposal_line_item_fields():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    items = r.json()["lineItems"]

    for item in items:
        assert item["code"]
        assert item["category"]
        assert item["description"]
        assert isinstance(item["estimatedCost"], int)
        assert item["estimatedCost"] > 0
        assert item["sourceFinding"]
        assert item["matchReason"]


def test_spec_example_cost():
    """Spec: Missing shingles, high severity, 2 photos → $1400."""
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    items = r.json()["lineItems"]

    shingles = next(i for i in items if i["sourceFinding"] == "Missing shingles")
    assert shingles["code"] == "roof.patch_shingles"
    assert shingles["estimatedCost"] == 1400


def test_proposal_total_equals_sum_of_line_items():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    body = r.json()

    expected_total = sum(i["estimatedCost"] for i in body["lineItems"])
    assert body["total"] == expected_total


def test_proposal_match_reason_present():
    report_id = create_report()
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    for item in r.json()["lineItems"]:
        assert item["matchReason"], f"matchReason missing for {item['code']}"


def test_get_proposal_not_found():
    r = httpx.get(f"{BASE}/proposals/prop_doesnotexist", timeout=10)
    assert r.status_code == 404


# ── proposal versioning ────────────────────────────────────────────────────────

def test_regenerate_creates_new_version():
    report_id = create_report()
    prop1 = generate_proposal(report_id)
    prop2 = generate_proposal(report_id)

    assert prop1 != prop2

    r1 = httpx.get(f"{BASE}/proposals/{prop1}", timeout=10).json()
    r2 = httpx.get(f"{BASE}/proposals/{prop2}", timeout=10).json()

    assert r1["version"] == 1
    assert r2["version"] == 2


def test_old_proposal_remains_retrievable():
    report_id = create_report()
    prop1 = generate_proposal(report_id)
    generate_proposal(report_id)  # create version 2

    # version 1 still accessible by its ID
    r = httpx.get(f"{BASE}/proposals/{prop1}", timeout=10)
    assert r.status_code == 200
    assert r.json()["version"] == 1


def test_list_proposals_history():
    report_id = create_report()
    generate_proposal(report_id)
    generate_proposal(report_id)

    r = httpx.get(f"{BASE}/reports/{report_id}/proposals", timeout=10)
    assert r.status_code == 200
    history = r.json()

    assert len(history) == 2
    assert history[0]["version"] == 1
    assert history[1]["version"] == 2
    assert history[0]["proposalId"].startswith("prop_")


def test_list_proposals_not_found():
    r = httpx.get(f"{BASE}/reports/rpt_doesnotexist/proposals", timeout=10)
    assert r.status_code == 404


# ── validation ────────────────────────────────────────────────────────────────

def error_fields(r) -> list[str]:
    return [e["field"] for e in r.json()["detail"]]


def test_validation_missing_customer_name():
    bad = {**VALID_REPORT, "customer": {"name": "", "email": "x@x.com"}}
    report_id = create_report(bad)
    r = httpx.post(f"{BASE}/reports/{report_id}/generate-proposal", timeout=35)
    assert r.status_code == 422
    assert "customer.name" in error_fields(r)


def test_validation_empty_findings():
    bad = {**VALID_REPORT, "findings": []}
    report_id = create_report(bad)
    r = httpx.post(f"{BASE}/reports/{report_id}/generate-proposal", timeout=35)
    assert r.status_code == 422
    assert "findings" in error_fields(r)


def test_validation_invalid_severity():
    bad = {
        **VALID_REPORT,
        "findings": [{"title": "Damage", "severity": "extreme", "notes": "", "photos": []}],
    }
    report_id = create_report(bad)
    r = httpx.post(f"{BASE}/reports/{report_id}/generate-proposal", timeout=35)
    assert r.status_code == 422
    assert any("severity" in f for f in error_fields(r))


def test_validation_error_is_list_of_objects():
    bad = {**VALID_REPORT, "customer": {"name": "", "email": ""}}
    report_id = create_report(bad)
    r = httpx.post(f"{BASE}/reports/{report_id}/generate-proposal", timeout=35)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert isinstance(detail, list)
    for err in detail:
        assert "field" in err
        assert "message" in err


# ── unknown finding fallback ───────────────────────────────────────────────────

def test_unknown_finding_falls_back_to_general():
    payload = {
        **VALID_REPORT,
        "findings": [
            {"title": "Unknown exterior damage", "severity": "medium",
             "notes": "Needs review", "photos": []}
        ],
    }
    report_id = create_report(payload)
    proposal_id = generate_proposal(report_id)

    r = httpx.get(f"{BASE}/proposals/{proposal_id}", timeout=10)
    items = r.json()["lineItems"]

    assert items[0]["code"] == "general.assessment_tm"
    assert "No specific match" in items[0]["matchReason"]
