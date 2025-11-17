from __future__ import annotations

from flintcoretest.sprt import elo_from_score, elo_with_confidence, logistic_from_elo


def test_logistic_round_trip() -> None:
    original_elo = 35.0
    expected = logistic_from_elo(original_elo)
    recovered = elo_from_score(expected)
    assert abs(recovered - original_elo) < 1e-6


def test_confidence_interval_monotonicity() -> None:
    elo, margin = elo_with_confidence(0.55, 200)
    assert elo > 0
    assert margin > 0
    elo_more, margin_more = elo_with_confidence(0.55, 800)
    assert margin_more < margin
