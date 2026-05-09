import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.context import PipelineContext
from workers.normalizer.worker import process

RAW = {
    "customer": {"name": "  Jane Smith  ", "email": "JANE@EXAMPLE.COM"},
    "property": {"address": "123 Main St", "type": "single_family"},
    "findings": [
        {"title": " Missing shingles ", "severity": "HIGH", "notes": "  damage  ", "photos": ["p1"]},
        {"title": "Clogged gutters", "severity": "medium", "notes": "", "photos": []},
    ],
}


def test_strips_whitespace():
    ctx = PipelineContext(job_id="j1", report_id="rpt_1", raw_input=RAW)
    result = process(ctx)
    assert result.report_input["customer"]["name"] == "Jane Smith"
    assert result.report_input["property"]["address"] == "123 Main St"


def test_normalizes_severity_to_lowercase():
    ctx = PipelineContext(job_id="j1", report_id="rpt_1", raw_input=RAW)
    result = process(ctx)
    assert result.report_input["findings"][0]["severity"] == "high"


def test_finding_count_preserved():
    ctx = PipelineContext(job_id="j1", report_id="rpt_1", raw_input=RAW)
    result = process(ctx)
    assert len(result.report_input["findings"]) == 2


def test_finding_ids_assigned():
    ctx = PipelineContext(job_id="j1", report_id="rpt_1", raw_input=RAW)
    result = process(ctx)
    for f in result.report_input["findings"]:
        assert f["id"].startswith("fnd_")


def test_seq_assigned():
    ctx = PipelineContext(job_id="j1", report_id="rpt_1", raw_input=RAW)
    result = process(ctx)
    assert result.report_input["findings"][0]["seq"] == 0
    assert result.report_input["findings"][1]["seq"] == 1
