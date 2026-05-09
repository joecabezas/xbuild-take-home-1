import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workers.pricer.worker import price


def test_spec_example():
    # spec: base=900, high (1.5), 2 photos → 900*1.5 + 50 = 1400
    assert price(900, "high", ["p1", "p2"]) == 1400


def test_low_severity_no_photos():
    # 900 * 0.8 = 720 → rounds to 720
    assert price(900, "low", []) == 720


def test_medium_severity_no_photos():
    assert price(650, "medium", []) == 650


def test_photo_modifier_cap():
    # 6 photos → capped at 150, not 6*25=150 (exactly at cap)
    assert price(300, "medium", ["p"] * 6) == 450
    # 7 photos → still capped at 150
    assert price(300, "medium", ["p"] * 7) == 450


def test_rounding_to_nearest_ten():
    # 400 * 0.8 = 320 → 320
    assert price(400, "low", []) == 320
    # 750 * 1.0 + 25 = 775 → 780
    assert price(750, "medium", ["p1"]) == 780


def test_high_severity_with_photos():
    # 650 * 1.5 = 975 + 25 = 1000 → 1000
    assert price(650, "high", ["p1"]) == 1000
