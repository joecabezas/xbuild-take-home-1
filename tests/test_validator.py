import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from shared.context import PipelineContext
from workers.validator.worker import process

VALID = {
    "customer": {"name": "Jane Smith", "email": "jane@example.com"},
    "property": {"address": "123 Main St", "type": "single_family"},
    "findings": [{"title": "Missing shingles", "severity": "high", "notes": "", "photos": []}],
}


def ctx(raw):
    return PipelineContext(job_id="j1", report_id="rpt_test", raw_input=raw)


def test_valid_input_passes():
    result = process(ctx(VALID))
    assert result.validated is True


def test_missing_customer_name():
    bad = {**VALID, "customer": {"name": "", "email": "jane@example.com"}}
    with pytest.raises(ValueError, match="customer.name"):
        process(ctx(bad))


def test_missing_customer_email():
    bad = {**VALID, "customer": {"name": "Jane", "email": ""}}
    with pytest.raises(ValueError, match="customer.email"):
        process(ctx(bad))


def test_missing_property_address():
    bad = {**VALID, "property": {"address": "", "type": "single_family"}}
    with pytest.raises(ValueError, match="property.address"):
        process(ctx(bad))


def test_empty_findings():
    bad = {**VALID, "findings": []}
    with pytest.raises(ValueError, match="findings"):
        process(ctx(bad))


def test_missing_findings():
    bad = {k: v for k, v in VALID.items() if k != "findings"}
    with pytest.raises(ValueError, match="findings"):
        process(ctx(bad))


def test_invalid_severity():
    bad = {**VALID, "findings": [
        {"title": "Damage", "severity": "extreme", "notes": "", "photos": []}
    ]}
    with pytest.raises(ValueError, match="severity"):
        process(ctx(bad))


def test_multiple_errors_reported():
    bad = {"customer": {"name": "", "email": ""}, "property": {"address": "", "type": ""},
           "findings": []}
    with pytest.raises(ValueError) as exc:
        process(ctx(bad))
    assert exc.value.args[0].count(";") >= 2
