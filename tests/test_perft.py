from __future__ import annotations

import pytest

from flintcoretest.perft_cases import DEFAULT_PERFT_CASES, PerftExpectation


@pytest.mark.parametrize("case", DEFAULT_PERFT_CASES)
def test_perft_command(engine, case: PerftExpectation) -> None:
    assert engine.perft_command(case) == case.nodes


def test_go_perft_matches_reference(engine) -> None:
    target = next(case for case in DEFAULT_PERFT_CASES if case.name == "startpos_depth3")
    assert engine.go_perft(target) == target.nodes
