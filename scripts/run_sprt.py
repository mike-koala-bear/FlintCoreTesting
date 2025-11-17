#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _ensure_repo_on_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_ensure_repo_on_path()

from flintcoretest.sprt import EngineOptions, SPRTBounds, SPRTConfig, SPRTRunner, load_openings


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    default_openings = repo_root / "flintcoretest" / "data" / "sprt_openings.epd"

    parser = argparse.ArgumentParser(description="Run an SPRT match between two FlintCore binaries")
    parser.add_argument("--engine-a", type=Path, required=True, help="Path to the baseline engine binary")
    parser.add_argument("--engine-b", type=Path, required=True, help="Path to the contender engine binary")
    parser.add_argument("--name-a", default="Baseline", help="Display name for engine A")
    parser.add_argument("--name-b", default="Contender", help="Display name for engine B")
    parser.add_argument("--games", type=int, default=200, help="Maximum number of games to play")
    parser.add_argument("--movetime", type=float, default=0.40, help="Move time in seconds for each engine")
    parser.add_argument("--base-moves", type=float, default=40.0, help="Base moves displayed in the summary")
    parser.add_argument("--threads", type=int, default=1, help="Default Threads value when supported")
    parser.add_argument("--threads-a", type=int, dest="threads_a", help="Override Threads for engine A")
    parser.add_argument("--threads-b", type=int, dest="threads_b", help="Override Threads for engine B")
    parser.add_argument("--hash-mb", type=int, default=8, help="Default Hash value in MB when supported")
    parser.add_argument("--hash-a", type=int, dest="hash_a", help="Override Hash (MB) for engine A")
    parser.add_argument("--hash-b", type=int, dest="hash_b", help="Override Hash (MB) for engine B")
    parser.add_argument("--openings", type=Path, default=default_openings, help="EPD/startpos list used to seed games")
    parser.add_argument("--sprt-elo0", type=float, default=-2.0, help="Null hypothesis Elo for SPRT")
    parser.add_argument("--sprt-elo1", type=float, default=2.0, help="Alternative hypothesis Elo for SPRT")
    parser.add_argument("--alpha", type=float, default=0.05, help="SPRT alpha (Type I error)")
    parser.add_argument("--beta", type=float, default=0.05, help="SPRT beta (Type II error)")
    parser.add_argument("--report", type=Path, help="Optional file to write the summary output")
    return parser.parse_args()


def _verify_engine(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        raise SystemExit(
            f"Engine '{label}' not found at {resolved}. Build FlintCore (scripts/build_engine.py) or"
            " adjust the --engine-* arguments."
        )
    if not resolved.is_file():
        raise SystemExit(f"Engine path for '{label}' is not a file: {resolved}")
    if not os.access(resolved, os.X_OK):
        raise SystemExit(f"Engine binary for '{label}' is not executable: {resolved}")
    return resolved


def main() -> None:
    args = parse_args()
    bounds = SPRTBounds(elo0=args.sprt_elo0, elo1=args.sprt_elo1, alpha=args.alpha, beta=args.beta)
    config = SPRTConfig(
        games=args.games,
        movetime_s=args.movetime,
        base_moves=args.base_moves,
        hash_mb=args.hash_mb,
        threads=args.threads,
        bounds=bounds,
    )
    openings = load_openings(args.openings)
    options_a = EngineOptions(
        threads=args.threads_a if args.threads_a is not None else args.threads,
        hash_mb=args.hash_a if args.hash_a is not None else args.hash_mb,
    )
    options_b = EngineOptions(
        threads=args.threads_b if args.threads_b is not None else args.threads,
        hash_mb=args.hash_b if args.hash_b is not None else args.hash_mb,
    )
    engine_a = _verify_engine(args.engine_a, args.name_a)
    engine_b = _verify_engine(args.engine_b, args.name_b)
    runner = SPRTRunner(
        engine_a=engine_a,
        engine_b=engine_b,
        openings=openings,
        config=config,
        name_a=args.name_a,
        name_b=args.name_b,
        options_a=options_a,
        options_b=options_b,
    )
    result = runner.run()
    lines = result.summary_lines(config, args.name_a, args.name_b, options_a, options_b)
    for line in lines:
        print(line)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
