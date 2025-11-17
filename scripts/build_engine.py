#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_source = Path(os.environ.get("FLINTCORE_SOURCE_DIR", repo_root.parent / "FlintCore"))
    default_build = Path(os.environ.get("FLINTCORE_BUILD_DIR", default_source / "build-ci"))

    parser = argparse.ArgumentParser(description="Configure and build the FlintCore engine via CMake")
    parser.add_argument("--source", type=Path, default=default_source, help="Path to the FlintCore source tree")
    parser.add_argument("--build-dir", type=Path, default=default_build, help="Out-of-tree build directory")
    parser.add_argument("--build-type", default=os.environ.get("CMAKE_BUILD_TYPE", "Release"), help="CMake build type")
    parser.add_argument("--generator", default=os.environ.get("CMAKE_GENERATOR"), help="Optional CMake generator")
    parser.add_argument("--parallel", type=int, default=0, help="Number of parallel build jobs to request")
    parser.add_argument("--target", default=None, help="Optional specific target to build")
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    build_dir = args.build_dir.expanduser().resolve()

    if not source.exists():
        raise SystemExit(f"FlintCore source directory not found: {source}")
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake_cmd = [
        "cmake",
        "-S",
        str(source),
        "-B",
        str(build_dir),
        f"-DCMAKE_BUILD_TYPE={args.build_type}",
    ]
    if args.generator:
        cmake_cmd.extend(["-G", args.generator])

    run(cmake_cmd)

    build_cmd = [
        "cmake",
        "--build",
        str(build_dir),
        "--config",
        args.build_type,
    ]
    if args.target:
        build_cmd.extend(["--target", args.target])
    if args.parallel > 0:
        build_cmd.extend(["-j", str(args.parallel)])

    run(build_cmd)

    binary = next(
        (cand for cand in (build_dir / "FlintCore", build_dir / "FlintCore.exe") if cand.exists()),
        None,
    )
    if binary:
        print(f"FlintCore binary ready at: {binary}")
        print("Set FLINTCORE_ENGINE_PATH to this file so pytest can find it.")
    else:
        print("Build finished but FlintCore executable was not found in the build directory.")


if __name__ == "__main__":
    main()
