"""
Integration tests: run the full process() chain without RabbitMQ or DB.
These tests verify that data flows correctly from one worker to the next
and that the final output shape matches the API contract.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workers", "matcher"))

from unittest.mock import patch
from shared.context import PipelineContext
from workers.validator.worker import process as validate
from workers.normalizer.worker import process as normalize
from workers.matcher.worker import process as match_findings
from workers.pricer.worker import process as price
from workers.assembler.worker import process as assemble

VALID_RAW = {
    "customer": {"name": "Jane Smith", "email": "jane@example.com"},
    "property": {"address": "123 Main St, Austin, TX", "type": "single_family"},
    "findings": [
        {"title": "Missing shingles", "severity": "high",
         "notes": "Visible damage on north slope", "photos": ["p1.jpg", "p2.jpg"]},
        {"title": "Clogged gutters", "severity": "medium", "notes": "", "photos": []},
    ],
}


def run_pipeline(raw_input, finding_ids=None):
    ctx = PipelineContext(job_id="test_job", report_id="rpt_test", raw_input=raw_input)
    ctx = validate(ctx)
    ctx = normalize(ctx)
    ctx = match_findings(ctx)
    ctx = price(ctx)

    fids = finding_ids or ["fnd_001", "fnd_002"]
    with patch("workers.assembler.worker.get_finding_ids", return_value=fids), \
         patch("workers.assembler.worker.save_proposal", return_value="prop_test"):
        ctx = assemble(ctx)

    return ctx


def test_full_pipeline_completes():
    ctx = run_pipeline(VALID_RAW)
    assert ctx.status == "complete"
    assert ctx.proposal_draft["proposal_id"] == "prop_test"


def test_pipeline_produces_one_line_item_per_finding():
    ctx = run_pipeline(VALID_RAW)
    # must go through assembler to capture the draft
    from unittest.mock import patch

    captured = {}

    def capture(draft, fids):
        captured["draft"] = draft
        return "prop_x"

    raw_ctx = PipelineContext(job_id="j", report_id="r", raw_input=VALID_RAW)
    raw_ctx = validate(raw_ctx)
    raw_ctx = normalize(raw_ctx)
    raw_ctx = match_findings(raw_ctx)
    raw_ctx = price(raw_ctx)

    with patch("workers.assembler.worker.get_finding_ids", return_value=["f1", "f2"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture):
        assemble(raw_ctx)

    assert len(captured["draft"].line_items) == len(VALID_RAW["findings"])


def test_pipeline_spec_example_cost():
    """Spec: Missing shingles, high, 2 photos → $1400."""
    raw = {
        "customer": {"name": "Jane", "email": "j@j.com"},
        "property": {"address": "1 St", "type": "single_family"},
        "findings": [
            {"title": "Missing shingles", "severity": "high",
             "notes": "", "photos": ["p1.jpg", "p2.jpg"]},
        ],
    }
    captured = {}

    def capture(draft, fids):
        captured["draft"] = draft
        return "prop_x"

    ctx = PipelineContext(job_id="j", report_id="r", raw_input=raw)
    ctx = validate(ctx)
    ctx = normalize(ctx)
    ctx = match_findings(ctx)
    ctx = price(ctx)

    with patch("workers.assembler.worker.get_finding_ids", return_value=["f1"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture):
        assemble(ctx)

    item = captured["draft"].line_items[0]
    assert item.code == "roof.patch_shingles"
    assert item.estimated_cost == 1400


def test_pipeline_all_priced_items_have_required_fields():
    """Regression: PricedLineItem must be fully constructed by assembler."""
    captured = {}

    def capture(draft, fids):
        captured["draft"] = draft
        return "prop_x"

    ctx = PipelineContext(job_id="j", report_id="r", raw_input=VALID_RAW)
    ctx = validate(ctx)
    ctx = normalize(ctx)
    ctx = match_findings(ctx)
    ctx = price(ctx)

    with patch("workers.assembler.worker.get_finding_ids", return_value=["f1", "f2"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture):
        assemble(ctx)

    for item in captured["draft"].line_items:
        assert item.finding_id
        assert item.code
        assert item.estimated_cost > 0
        assert item.match_reason


def test_pipeline_unknown_finding_falls_back():
    raw = {
        "customer": {"name": "Joe", "email": "j@j.com"},
        "property": {"address": "1 St", "type": "condo"},
        "findings": [
            {"title": "Unknown exterior damage", "severity": "medium",
             "notes": "Needs review", "photos": []},
        ],
    }
    captured = {}

    def capture(draft, fids):
        captured["draft"] = draft
        return "prop_x"

    ctx = PipelineContext(job_id="j", report_id="r", raw_input=raw)
    ctx = validate(ctx)
    ctx = normalize(ctx)
    ctx = match_findings(ctx)
    ctx = price(ctx)

    with patch("workers.assembler.worker.get_finding_ids", return_value=["f1"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture):
        assemble(ctx)

    assert captured["draft"].line_items[0].code == "general.assessment_tm"


def test_pipeline_validation_error_raises():
    import pytest
    raw = {**VALID_RAW, "findings": []}
    ctx = PipelineContext(job_id="j", report_id="r", raw_input=raw)
    with pytest.raises(ValueError, match="findings"):
        validate(ctx)


def test_pipeline_context_fields_populated_at_each_stage():
    ctx = PipelineContext(job_id="j", report_id="r", raw_input=VALID_RAW)

    assert ctx.validated is False
    ctx = validate(ctx)
    assert ctx.validated is True

    assert ctx.report_input is None
    ctx = normalize(ctx)
    assert ctx.report_input is not None

    assert ctx.matches == []
    ctx = match_findings(ctx)
    assert len(ctx.matches) == 2

    assert ctx.priced_items == []
    ctx = price(ctx)
    assert len(ctx.priced_items) == 2
