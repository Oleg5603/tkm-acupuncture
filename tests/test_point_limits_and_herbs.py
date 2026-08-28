import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from engine import build_protocol, recommend_herbs


SCORES = {"F": 10, "E": 9, "P": 8, "C": 7, "R": 6, "VB": 5}


def test_point_limits_are_deterministic_and_unique():
    all_points = build_protocol(SCORES, point_limit=None)
    assert len(all_points) >= 9
    assert len({item["point"] for item in all_points}) == len(all_points)
    for limit in (5, 7, 9):
        assert build_protocol(SCORES, point_limit=limit) == all_points[:limit]


def test_default_keeps_legacy_selection_rules():
    legacy = build_protocol(SCORES)
    assert legacy == build_protocol(SCORES, point_limit=0)
    assert len(legacy) <= 5


def test_herbs_are_unique_and_include_safety_information():
    herbs = recommend_herbs(SCORES)
    assert herbs
    assert len({item["id"] for item in herbs}) == len(herbs)
    assert all(item["herbs"] and item["caution"] for item in herbs)
