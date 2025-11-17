from __future__ import annotations

from flintcoretest.engine_runner import CommandResult, EngineHarness


def _line_with_prefix(result: CommandResult, prefix: str) -> str | None:
    for line in result.stdout_lines:
        if line.startswith(prefix):
            return line
    return None


def test_uci_handshake_reports_metadata(engine: EngineHarness) -> None:
    result = engine.handshake()
    assert _line_with_prefix(result, "id name "), "missing engine name"
    assert _line_with_prefix(result, "id author "), "missing author line"
    assert any(line == "uciok" for line in result.stdout_lines), "uciok not returned"
    assert any(line == "readyok" for line in result.stdout_lines), "isready acknowledgement missing"


def test_search_returns_legal_move(engine: EngineHarness) -> None:
    result = engine.run_simple_search(moves=("e2e4", "e7e5"), depth=2)
    line = _line_with_prefix(result, "bestmove ")
    assert line is not None, f"bestmove missing in output:\n{result.stdout}"
    assert line.split()[1] != "0000", "engine returned null move"
