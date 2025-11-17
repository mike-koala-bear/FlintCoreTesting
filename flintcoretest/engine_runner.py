from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import os
import subprocess

from .perft_cases import PerftExpectation


class EngineNotFoundError(RuntimeError):
    """Raised when the FlintCore executable cannot be located."""


@dataclass
class CommandResult:
    """Holds stdout/stderr for a finished process."""

    stdout: str
    stderr: str

    @property
    def stdout_lines(self) -> list[str]:
        return [line.rstrip("\r\n") for line in self.stdout.splitlines()]

    @property
    def stderr_lines(self) -> list[str]:
        return [line.rstrip("\r\n") for line in self.stderr.splitlines()]


def _resolve(path_str: str | None) -> Path | None:
    if not path_str:
        return None
    return Path(path_str).expanduser().resolve()


def _candidate_engine_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = repo_root.parent

    env_engine = _resolve(os.environ.get("FLINTCORE_ENGINE_PATH"))
    env_source = _resolve(os.environ.get("FLINTCORE_SOURCE_DIR"))
    env_build = _resolve(os.environ.get("FLINTCORE_BUILD_DIR"))

    candidates: list[Path] = []
    if env_engine:
        candidates.append(env_engine)

    source_hint = env_source or (workspace / "FlintCore")
    build_hints: list[Path] = []
    if env_build:
        build_hints.append(env_build)
    if source_hint:
        build_hints.extend([
            source_hint / "build",
            source_hint / "build-ci",
            source_hint / "cmake-build-release",
            source_hint / "build-release",
        ])

    for build_dir in build_hints:
        candidates.append(build_dir / "FlintCore")
        candidates.append(build_dir / "FlintCore.exe")

    # Fallback to common locations when the repo is vendored inside the source tree.
    candidates.append(repo_root / "build" / "FlintCore")

    # Deduplicate while preserving order.
    seen: set[Path] = set()
    ordered: list[Path] = []
    for cand in candidates:
        if not cand:
            continue
        try:
            resolved = cand.resolve()
        except FileNotFoundError:
            resolved = cand
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered.append(resolved)
    return ordered


def discover_engine_binary() -> Path:
    for cand in _candidate_engine_paths():
        if cand.is_file() and os.access(cand, os.X_OK):
            return cand
    raise EngineNotFoundError(
        "Could not locate a FlintCore executable. Set FLINTCORE_ENGINE_PATH or run scripts/build_engine.py."
    )


def _ensure_quit(commands: Sequence[str]) -> list[str]:
    lines = list(commands)
    if not lines or lines[-1].strip().lower() != "quit":
        lines.append("quit")
    return lines


def _parse_perft_nodes(output: str) -> int:
    for line in reversed(output.splitlines()):
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("total nodes:"):
            return int(stripped.split(":", 1)[1].strip())
        if lower.startswith("nodes "):
            return int(stripped.split()[1])
    raise ValueError(f"Unable to parse perft nodes from output:\n{output}")


def _position_command(case: PerftExpectation) -> str:
    if case.startpos:
        base = "position startpos"
    elif case.fen:
        base = f"position fen {case.fen}"
    else:
        raise ValueError(f"Perft case '{case.name}' missing FEN/startpos")
    if case.moves:
        base += " moves " + " ".join(case.moves)
    return base


class EngineHarness:
    """Thin wrapper around the FlintCore executable for tests and CI."""

    def __init__(self, engine_path: str | Path | None = None, timeout: float = 60.0):
        resolved = Path(engine_path).expanduser().resolve() if engine_path else discover_engine_binary()
        if not resolved.is_file() or not os.access(resolved, os.X_OK):
            raise EngineNotFoundError(f"Engine binary is not executable: {resolved}")
        self.engine_path = resolved
        self.timeout = timeout

    def run_uci_script(self, commands: Sequence[str], timeout: float | None = None) -> CommandResult:
        script_lines = _ensure_quit(commands)
        script = "\n".join(script_lines) + "\n"
        proc = subprocess.run(
            [str(self.engine_path)],
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout or self.timeout,
            check=True,
        )
        return CommandResult(proc.stdout, proc.stderr)

    def handshake(self) -> CommandResult:
        return self.run_uci_script(["uci", "isready"])

    def go_perft(self, case: PerftExpectation) -> int:
        commands = [
            "uci",
            "isready",
            "ucinewgame",
            _position_command(case),
            f"go perft {case.depth}",
        ]
        result = self.run_uci_script(commands, timeout=max(self.timeout, 90.0))
        return _parse_perft_nodes(result.stdout)

    def perft_command(self, case: PerftExpectation) -> int:
        commands = [
            "uci",
            "isready",
            "ucinewgame",
            _position_command(case),
            f"perft {case.depth}",
        ]
        result = self.run_uci_script(commands, timeout=max(self.timeout, 90.0))
        return _parse_perft_nodes(result.stdout)

    def run_simple_search(self, moves: Iterable[str] | None = None, depth: int = 1) -> CommandResult:
        moves_str = " moves " + " ".join(moves) if moves else ""
        commands = [
            "uci",
            "isready",
            "ucinewgame",
            f"position startpos{moves_str}",
            f"go depth {depth}",
        ]
        return self.run_uci_script(commands)

    def run_bench(self, extra_args: Sequence[str] | None = None, timeout: float | None = None) -> CommandResult:
        args = [str(self.engine_path)]
        if extra_args:
            args.extend(extra_args)
        else:
            args.append("bench")
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout or max(self.timeout, 120.0),
            check=True,
        )
        return CommandResult(proc.stdout, proc.stderr)
