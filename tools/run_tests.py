#!/usr/bin/env python3
"""Developer test and lint runner for SLICES v4.0.2.

Wraps ``pytest`` with reproducible environment defaults (``PYTHONHASHSEED=0``,
``OMP_NUM_THREADS=1``) and convenient flags for project markers (``unit``,
``integration``, ``regression``, ``baseline``, ``mlip``, ``gfnff``, ``slow``),
coverage reporting, and ``ruff`` static analysis.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
LINT_TARGETS: tuple[str, ...] = ("src", "examples", "tools", "tests")


def _build_env() -> dict[str, str]:
    """Construct a reproducible subprocess environment rooted at the repository."""
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    src_path = str(REPO_ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    parts = [p for p in existing.split(os.pathsep) if p]
    if src_path not in parts:
        env["PYTHONPATH"] = os.pathsep.join([src_path, *parts])
    return env


def _resolve_ruff_cmd() -> list[str]:
    """Locate the ``ruff`` executable on PATH or via ``python -m ruff``."""
    ruff_bin = shutil.which("ruff")
    if ruff_bin is not None:
        return [ruff_bin]
    return [sys.executable, "-m", "ruff"]


def _run_step(cmd: list[str], description: str, env: dict[str, str]) -> int:
    """Execute ``cmd`` in ``REPO_ROOT`` and return its exit code."""
    print(f"\n{'=' * 68}\n{description}\n  $ {' '.join(cmd)}\n{'=' * 68}", flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=False)
    return proc.returncode


def _build_marker_expr(args: argparse.Namespace) -> str | None:
    """Combine selected marker convenience flags into a pytest ``-m`` expression."""
    selected: list[str] = []
    for marker_name in ("unit", "integration", "regression", "baseline", "mlip", "gfnff", "slow"):
        if getattr(args, marker_name, False):
            selected.append(marker_name)

    clauses: list[str] = []
    if selected:
        clauses.append("(" + " or ".join(selected) + ")")
    if args.marker:
        clauses.append(f"({args.marker})")
    if args.exclude_slow and "slow" not in selected:
        clauses.append("not slow")
    if not clauses:
        return None
    return " and ".join(clauses)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run requested ``ruff`` and/or ``pytest`` suites.

    Args:
        argv: Optional sequence of command-line arguments.

    Returns:
        Exit code (``0`` if all executed steps succeed, non-zero otherwise).
    """
    parser = argparse.ArgumentParser(description="SLICES v4.0.2 Test & Lint Runner")
    parser.add_argument("--unit", action="store_true", help="select @pytest.mark.unit tests")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="select @pytest.mark.integration tests",
    )
    parser.add_argument(
        "--regression",
        action="store_true",
        help="select @pytest.mark.regression tests",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="select @pytest.mark.baseline golden equivalence tests",
    )
    parser.add_argument(
        "--mlip",
        action="store_true",
        help="select @pytest.mark.mlip optional backend tests",
    )
    parser.add_argument(
        "--gfnff",
        action="store_true",
        help="select @pytest.mark.gfnff topology helper tests",
    )
    parser.add_argument("--slow", action="store_true", help="select @pytest.mark.slow tests")
    parser.add_argument(
        "--exclude-slow",
        action="store_true",
        help="exclude @pytest.mark.slow tests",
    )
    parser.add_argument(
        "-m",
        "--marker",
        default=None,
        help="additional custom pytest marker expression",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="collect branch/line coverage for src/slices",
    )
    parser.add_argument(
        "--lint",
        "--ruff",
        dest="lint",
        action="store_true",
        help="run `ruff check` before pytest",
    )
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="run `ruff check` only and skip pytest",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="disable ruff/pytest cache writes (`--no-cache` / `-p no:cacheprovider`)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose pytest output")
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="extra arguments forwarded directly to pytest (prefix with `--`)",
    )
    args = parser.parse_args(argv)
    env = _build_env()

    if args.lint or args.lint_only:
        ruff_cmd = [*_resolve_ruff_cmd(), "check"]
        if args.no_cache:
            ruff_cmd.append("--no-cache")
        existing_targets = [t for t in LINT_TARGETS if (REPO_ROOT / t).exists()]
        ruff_cmd.extend(existing_targets)
        rc = _run_step(ruff_cmd, "Running Ruff Static Analysis", env)
        if rc != 0 or args.lint_only:
            return rc

    pytest_cmd = [sys.executable, "-m", "pytest"]
    if args.no_cache:
        pytest_cmd.extend(["-p", "no:cacheprovider"])
    marker_expr = _build_marker_expr(args)
    if marker_expr:
        pytest_cmd.extend(["-m", marker_expr])
    if args.coverage:
        pytest_cmd.extend(["--cov=src/slices", "--cov-report=term-missing"])
    pytest_cmd.append("-v" if args.verbose else "-q")

    extra = list(args.pytest_args)
    if extra and extra[0] == "--":
        extra = extra[1:]
    if extra:
        pytest_cmd.extend(extra)
    elif args.baseline and not any(
        [args.unit, args.integration, args.regression, args.mlip, args.gfnff, args.slow]
    ):
        pytest_cmd.append("tests/baseline")
    else:
        pytest_cmd.append("tests")

    return _run_step(pytest_cmd, "Running SLICES Pytest Suite (PYTHONHASHSEED=0)", env)


if __name__ == "__main__":
    sys.exit(main())
