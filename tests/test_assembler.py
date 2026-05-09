import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.context import PipelineContext
from shared.models import PricedLineItem


# Build a realistic priced_items list as the assembler receives it
def make_priced_items():
    return [
        {
            "finding_id": "fnd_aaa",
            "source_finding": "Missing shingles",
            "code": "roof.patch_shingles",
            "category": "roofing",
            "description": "Replace missing/damaged shingles in affected areas.",
            "estimated_cost": 1400,
            "match_reason": "Matched keywords: shingle, shingles, missing",
        },
        {
            "finding_id": "fnd_bbb",
            "source_finding": "Clogged gutters",
            "code": "gutters.clean_flush",
            "category": "gutters",
            "description": "Clean and flush gutters and downspouts.",
            "estimated_cost": 250,
            "match_reason": "Matched keywords: gutter, clog, clogged",
        },
    ]


def make_ctx(priced_items=None):
    return PipelineContext(
        job_id="job_test",
        report_id="rpt_test",
        raw_input={},
        report_input={
            "customer": {"name": "Jane Smith", "email": "jane@example.com"},
            "property": {"address": "123 Main St, Austin, TX", "type": "single_family"},
            "findings": [],
        },
        priced_items=priced_items or make_priced_items(),
    )


def assemble(ctx):
    """Run assembler process() without DB by patching repos."""
    from unittest.mock import patch
    from workers.assembler.worker import process

    fake_finding_ids = ["fnd_aaa", "fnd_bbb"]
    with patch("workers.assembler.worker.get_finding_ids", return_value=fake_finding_ids), \
         patch("workers.assembler.worker.save_proposal", return_value="prop_xyz"):
        return process(ctx)


def test_assembler_sets_status_complete():
    result = assemble(make_ctx())
    assert result.status == "complete"


def test_assembler_sets_proposal_draft():
    result = assemble(make_ctx())
    assert result.proposal_draft is not None
    assert result.proposal_draft["proposal_id"] == "prop_xyz"


def test_assembler_summary_includes_address():
    result = assemble(make_ctx())
    # summary is built inside save_proposal via ProposalDraft — check via the draft passed in
    from unittest.mock import patch, call
    from workers.assembler.worker import process

    captured = {}

    def capture_save(draft, finding_ids):
        captured["draft"] = draft
        return "prop_captured"

    with patch("workers.assembler.worker.get_finding_ids", return_value=["fnd_aaa", "fnd_bbb"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture_save):
        process(make_ctx())

    assert "123 Main St, Austin, TX" in captured["draft"].summary


def test_assembler_total_is_sum_of_line_items():
    from unittest.mock import patch

    captured = {}

    def capture_save(draft, finding_ids):
        captured["draft"] = draft
        return "prop_x"

    with patch("workers.assembler.worker.get_finding_ids", return_value=["fnd_aaa", "fnd_bbb"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture_save):
        from workers.assembler.worker import process
        process(make_ctx())

    assert captured["draft"].total == 1650  # 1400 + 250


def test_assembler_line_items_preserve_all_fields():
    """Regression: PricedLineItem must receive finding_id — the original bug."""
    from unittest.mock import patch

    captured = {}

    def capture_save(draft, finding_ids):
        captured["draft"] = draft
        return "prop_x"

    with patch("workers.assembler.worker.get_finding_ids", return_value=["fnd_aaa", "fnd_bbb"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture_save):
        from workers.assembler.worker import process
        process(make_ctx())

    items = captured["draft"].line_items
    assert len(items) == 2
    # All PricedLineItem fields must be populated — this is what was broken
    for item in items:
        assert isinstance(item, PricedLineItem)
        assert item.finding_id
        assert item.source_finding
        assert item.code
        assert item.category
        assert item.description
        assert item.estimated_cost > 0
        assert item.match_reason


def test_assembler_finding_ids_passed_to_save():
    """Assembler must pass finding IDs from DB to save_proposal for FK linking."""
    from unittest.mock import patch

    captured = {}

    def capture_save(draft, finding_ids):
        captured["finding_ids"] = finding_ids
        return "prop_x"

    with patch("workers.assembler.worker.get_finding_ids", return_value=["fnd_aaa", "fnd_bbb"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture_save):
        from workers.assembler.worker import process
        process(make_ctx())

    assert captured["finding_ids"] == ["fnd_aaa", "fnd_bbb"]


def test_assembler_single_finding():
    items = [make_priced_items()[0]]  # just the shingles item
    from unittest.mock import patch

    captured = {}

    def capture_save(draft, finding_ids):
        captured["draft"] = draft
        return "prop_x"

    with patch("workers.assembler.worker.get_finding_ids", return_value=["fnd_aaa"]), \
         patch("workers.assembler.worker.save_proposal", side_effect=capture_save):
        from workers.assembler.worker import process
        process(make_ctx(priced_items=items))

    assert captured["draft"].total == 1400
    assert len(captured["draft"].line_items) == 1
