from __future__ import annotations

from flintcoretest.engine_runner import EngineHarness


def _extract_field(summary_line: str, key: str) -> int:
    parts = summary_line.split()
    for idx, token in enumerate(parts[:-1]):
        if token == key:
            try:
                return int(parts[idx + 1])
            except (ValueError, IndexError):
                continue
    raise AssertionError(f"Key '{key}' not present in summary: {summary_line}")


def test_bench_summary_reports_progress(engine: EngineHarness) -> None:
    result = engine.run_bench()
    summary = next(
        (line for line in result.stdout.splitlines() if "bench summary" in line),
        None,
    )
    assert summary is not None, f"Bench summary missing. Output was:\n{result.stdout}"
    nodes = _extract_field(summary, "nodes")
    positions = _extract_field(summary, "positions")
    assert nodes > 0
    assert positions > 0
