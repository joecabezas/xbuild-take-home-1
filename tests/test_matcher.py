import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workers", "matcher"))

from catalog import match


def test_shingle_match():
    item, reason = match("Missing shingles", "Visible roof damage")
    assert item.code == "roof.patch_shingles"
    assert "shingle" in reason.lower() or "missing" in reason.lower()


def test_gutter_clog_match():
    item, reason = match("Clogged gutters full of leaves", "")
    assert item.code == "gutters.clean_flush"


def test_loose_gutter_match():
    item, reason = match("Loose gutter section", "Pulling away from fascia")
    assert item.code == "gutters.resecure"


def test_window_seal_match():
    # "water" + "stain" score 2 for roof.leak_investigation vs "window" + "seal" score 2 for
    # openings.reseal — tie broken by catalog order, leak_investigation comes first
    item, reason = match("Water staining near window", "Possible failed seal")
    assert item.code == "roof.leak_investigation"

def test_window_seal_direct_match():
    item, reason = match("Cracked window seal needs recaulking", "")
    assert item.code == "openings.reseal"


def test_fallback_on_unknown():
    item, reason = match("Squeaky floorboard inside unit", "")
    assert item.code == "general.assessment_tm"
    assert "No specific match" in reason


def test_leak_match():
    item, reason = match("Active roof leak", "Water dripping into attic")
    assert item.code == "roof.leak_investigation"


def test_siding_match():
    item, reason = match("Damaged siding panel", "")
    assert item.code == "siding.repair_local"


def test_deterministic():
    r1 = match("Missing shingles", "roof damage")
    r2 = match("Missing shingles", "roof damage")
    assert r1[0].code == r2[0].code
    assert r1[1] == r2[1]
