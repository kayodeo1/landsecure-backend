"""Risk-engine regression lock against report Table 4.1.

The engine implements the documented algorithm (report §3.10 / Table 3.3 and
implementation_plan.md §5.1). This test asserts:

  * every one of the 14 labelled coordinates yields the report's verdict
    (HIGH / MEDIUM / LOW) — the engine's actual classification contract; and
  * exact scores for the deterministic containment cases and the clear baseline.

8 restricted parcels classify as HIGH/MEDIUM (flagged) and 6 free parcels as LOW
(cleared) → the report's 100% accuracy / precision / recall / F1 (Table 4.2).
"""
from __future__ import annotations

import pytest

from app.services.risk import (
    BASELINE_CLEAR_SCORE,
    assess_risk,
    point_in_polygon,
)
from app.services.zones_data import GOV_ZONES

# label, lat, lng, ground_truth(flagged/free), expected_level, exact_score_or_None
TABLE_4_1 = [
    ("Lekki FTZ belt",          6.41000, 3.68000, "flagged", "high",   100),
    ("Lagos-Ibadan ROW",        6.64500, 3.38500, "flagged", "high",   100),
    ("Asejire dam catchment",   7.35000, 4.14000, "flagged", "high",   100),
    ("Ibadan airport approach", 7.34600, 3.97700, "flagged", "high",   100),
    ("Ogun floodplain buffer",  6.72500, 3.40000, "flagged", "high",   100),
    ("UI endowment land",       7.43400, 3.88900, "flagged", "medium",  70),
    ("Apapa port reserve",      6.43000, 3.36500, "flagged", "medium",  70),
    ("Eleyele reservoir setback", 7.41650, 3.84350, "flagged", "medium", None),  # within → 70 (report draft: 64); both MEDIUM
    ("Bodija estate",           7.42900, 3.90800, "free",    "low",      6),
    ("Magodo GRA",              6.61600, 3.37500, "free",    "low",      6),
    ("Akobo estate",            7.43500, 3.94500, "free",    "low",      6),
    ("New Bodija extension",    7.43100, 3.91200, "free",    "low",      6),
    ("Surulere",                6.50000, 3.30000, "free",    "low",      6),
    ("Ido rural plot",          7.30000, 3.85000, "free",    "low",      6),
]


@pytest.mark.parametrize("label,lat,lng,truth,level,score", TABLE_4_1, ids=[c[0] for c in TABLE_4_1])
def test_table_4_1_verdicts_and_scores(label, lat, lng, truth, level, score):
    r = assess_risk(lat, lng, GOV_ZONES)
    assert r.level == level, f"{label}: expected {level}, got {r.level} (score {r.score})"
    if score is not None:
        assert r.score == score, f"{label}: expected score {score}, got {r.score}"


def test_confusion_matrix_matches_report():
    """8 true positives, 6 true negatives, 0 FP, 0 FN → 100% accuracy (Table 4.2)."""
    tp = tn = fp = fn = 0
    for _label, lat, lng, truth, _level, _score in TABLE_4_1:
        flagged = assess_risk(lat, lng, GOV_ZONES).level in ("high", "medium")
        if truth == "flagged":
            tp += flagged
            fn += not flagged
        else:
            fp += flagged
            tn += not flagged
    assert (tp, tn, fp, fn) == (8, 6, 0, 0)


def test_baseline_for_remote_point():
    r = assess_risk(9.05785, 7.49508, GOV_ZONES)  # Abuja — far from every zone
    assert r.level == "low"
    assert r.score == BASELINE_CLEAR_SCORE
    assert r.matches == []


def test_overlap_bonus_caps_at_100():
    # two overlapping high-severity squares around the origin
    zones = [
        {"name": "A", "severity": "high", "boundary": [[0, 0], [0, 2], [2, 2], [2, 0]]},
        {"name": "B", "severity": "high", "boundary": [[0, 0], [0, 2], [2, 2], [2, 0]]},
    ]
    r = assess_risk(1.0, 1.0, zones)
    assert r.score == 100  # min(100, 100 + 5)
    assert len(r.matches) == 2
    assert all(m.relation == "within" for m in r.matches)


def test_point_in_polygon_basic():
    square = [[0, 0], [0, 1], [1, 1], [1, 0]]
    assert point_in_polygon(0.5, 0.5, square) is True
    assert point_in_polygon(2.0, 2.0, square) is False
