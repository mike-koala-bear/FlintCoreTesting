from __future__ import annotations

import pytest

from flintcoretest.engine_runner import EngineHarness, EngineNotFoundError


@pytest.fixture(scope="session")
def engine() -> EngineHarness:
    try:
        return EngineHarness()
    except EngineNotFoundError as exc:
        pytest.skip(
            f"FlintCore executable is missing: {exc}. "
            "Build it via scripts/build_engine.py or set FLINTCORE_ENGINE_PATH before running tests."
        )
