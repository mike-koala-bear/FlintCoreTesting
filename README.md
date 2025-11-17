# FlintCore Testing Platform

This repository hosts repeatable integration and regression tests for the C++ FlintCore engine.  It
is designed to live next to the main `FlintCore` source tree (for example inside the
`FlintCoreFull` directory) and to run the same checks locally and on GitHub Actions.

## Layout

- `flintcoretest/` – reusable helpers for launching the engine, parsing UCI output, and pre-defined
  perft expectations.
- `tests/` – pytest-powered scenarios (UCI handshake, perft regressions, and the reference bench).
- `scripts/build_engine.py` – convenience wrapper that configures & builds FlintCore via CMake.
- `.github/workflows/ci.yml` – ready-to-use workflow that builds the engine and executes the suite.

## Prerequisites

- Python 3.10+
- CMake 3.16+ and a C++20 compiler (gcc, clang, or MSVC available on the $PATH)
- The FlintCore repository cloned as a sibling directory (override with env vars below)

## Environment variables

The helpers attempt to auto-detect where the engine lives, but you can override anything explicitly:

- `FLINTCORE_SOURCE_DIR` – path to the FlintCore source tree (defaults to `../FlintCore`).
- `FLINTCORE_BUILD_DIR` – build directory to re-use; defaults to `<source>/build-ci`.
- `FLINTCORE_ENGINE_PATH` – explicit path to the compiled engine binary.  When set the lookup stops
  immediately, which is useful if you keep multiple builds around.

## Building the engine

Use the helper script to configure and compile the engine the way CI does:

```bash
python scripts/build_engine.py --build-type Release
```

The script respects the environment variables above and accepts `--source` / `--build-dir` flags if
you prefer to pass paths via the command line.

## Running the tests locally

1. Create a virtual environment and install the dev dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e .[dev]
   ```
2. Build the engine (see the section above) so that `FlintCore/build-ci/FlintCore` exists, or set
   `FLINTCORE_ENGINE_PATH` to any already-built binary.
3. Execute the suite:
   ```bash
   pytest -q
   ```

The tests perform a UCI handshake, run reference perft positions, and execute the speed test/bench
command to verify nothing regresses silently.

## GitHub Actions

`.github/workflows/ci.yml` contains a job that checks this repository out, fetches the FlintCore
source, builds it, and runs pytest.  Update the `FLINTCORE_REPOSITORY` environment variable inside
that workflow to point at the repository/owner that hosts your FlintCore sources.

## SPRT head-to-head testing

Use `scripts/run_sprt.py` to run a sequential probability ratio test between two FlintCore binaries.
The script relies on `python-chess` to drive both engines, rotates colors automatically, and prints a
summary with Elo, confidence interval, raw scores, and a five-bucket game length histogram.

Example:

```bash
python scripts/run_sprt.py \
  --engine-a ../FlintCore-base/build-sprt/FlintCore --name-a baseline \
  --engine-b ../FlintCore-contender/build-sprt/FlintCore --name-b contender \
  --games 400 --movetime 0.40 --threads 1 --hash-mb 8 \
  --report sprt_summary.txt
```

The bundled `flintcoretest/data/sprt_openings.epd` file supplies a neutral set of starting positions,
but you can point `--openings` at any EPD/plain-text file you prefer.  Use `--sprt-elo0/--sprt-elo1` to
set the H0/H1 boundaries, and adjust `--alpha/--beta` for the desired false-positive / false-negative
rates.

## GitHub Actions workflows

Alongside `ci.yml`, this repo provides `.github/workflows/sprt.yml` which targets head-to-head engine
matches for two FlintCore commits.  The workflow is `workflow_dispatch`-only and accepts the
following inputs:

- `base_ref` – git ref/commit for the baseline engine.
- `contender_ref` – git ref/commit for the candidate engine.
- `games`, `movetime`, `hash_mb`, and `threads` – forwarded to `scripts/run_sprt.py`.

Because the FlintCore repository is private, add a classic personal access token (PAT) with `repo`
read access as a repository secret on the *FlintCoreTesting* repo (the workflow expects
`FLINTCORE_TOKEN`).  The workflow now validates the secret at the start and fails fast with a helpful
message when it is missing.  With the secret in place, the action clones the private engine twice,
builds each ref in its own directory, runs the SPRT script, and uploads the textual summary as an
artifact and job summary.

## Extending the suite

Add more scenarios under `tests/` and share helpers inside `flintcoretest/`.  When a new scenario
requires extra artifacts or opening book files, commit small deterministic test fixtures directly in
this repository so the workflow can pull everything it needs without network access.
