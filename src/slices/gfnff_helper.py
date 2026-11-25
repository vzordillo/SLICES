"""Topology-only GFN-FF helper used by SLICES crystal reconstruction.

``SLICES.get_inner_p_target`` needs GFN-FF bond and angle parameters
(``blist``, ``vbond``, ``alist``, ``vangl``) for the finite neighbor table that
``SLICES.get_nbf_blist`` builds (the ``testBonds_cut.top`` text format). On Linux
x86_64, they come from the open-source GFN-FF library (pprcht/gfnff, LGPL-3.0-or-later)
with the SLICES topology-export patch, bundled under ``slices/_vendor`` (portable
manylinux2014 x86_64 build, loaded via ``ctypes``, independent of the Python version).

By default, the bundled helper uses the 86-element parameter table of the modified
``xtb`` helper that SLICES used previously, so elements ``Z = 1..86`` follow that
parametrisation and ``Z = 87..103`` use the library's own parameters. Setting
``SLICES_VENDOR_GFNFF_PARAM_MODE=modern`` uses the library's own parameters for all
elements; ``SLICES_VENDOR_GFNFF_PARAM_FILE`` points to an alternate ``xtb``-style
parameter table.

On non-Linux platforms where the bundled ``libgfnff.so`` shared library cannot load
(raising ``ImportError`` or ``OSError``), ``run_gfnff_helper`` falls back to an
external modified ``xtb`` executable configured via ``SLICES_XTB_PATH`` (or legacy
``XTB_MOD_PATH`` / ``PATH`` lookup for ``xtb_noring_nooutput_nostdout_noCN``).

On the 2,383 MP-20 benchmark structures (``data/mp20_nonmetal/mp20_v4_benchmark_2383.csv``),
the bundled helper produced identical reconstruction targets for 88%; where they
differed, decoding matched the reference structure for 165/194 vs 79/194 with ``xtb``
(``xtb`` produced non-finite targets for actinides and crashed on 39 inputs). A
40,000-structure benchmark in symSLICES confirmed the same behavior (+262 net strict
matches, -30 net loose matches).

Self-test: ``python -m slices.gfnff_helper``
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np

from slices.exceptions import GFNFFExecutionError

__all__ = [
    "LEGACY86_PARAM_FILE",
    "parse_nbf_text",
    "run_gfnff_helper",
    "write_debug_files",
]

_VENDOR_DIR = Path(__file__).resolve().parent / "_vendor"
LEGACY86_PARAM_FILE = _VENDOR_DIR / "gfnff_extra" / "param_gfnff_legacy86.xtb"
_XTB_BINARY_NAME = "xtb_noring_nooutput_nostdout_noCN"
_XTB_TIMEOUT_SECONDS = 30
_MIN_GFNFF_Z = 1
_MAX_GFNFF_Z = 103

_PARAM_ALIASES: dict[str, str] = {
    "": "legacy86_overlay",
    "default": "legacy86_overlay",
    "legacy86": "legacy86_overlay",
    "legacy86_overlay": "legacy86_overlay",
    "modern": "modern",
    "internal": "modern",
    "none": "modern",
}
_SYMBOL_TO_Z: dict[str, int] | None = None


def _selected_params() -> tuple[str, str]:
    """Return ``(param_mode, param_file_path)`` for the bundled GFN-FF library."""
    mode = os.environ.get("SLICES_VENDOR_GFNFF_PARAM_MODE", "").strip().lower()
    if mode not in _PARAM_ALIASES:
        raise ValueError(
            "SLICES_VENDOR_GFNFF_PARAM_MODE must be 'legacy86_overlay' or 'modern', "
            f"got {mode!r}"
        )
    mode = _PARAM_ALIASES[mode]
    if mode == "modern":
        return mode, ""
    path = Path(
        os.environ.get("SLICES_VENDOR_GFNFF_PARAM_FILE", "") or LEGACY86_PARAM_FILE
    ).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"GFN-FF legacy86 parameter file not found: {path}")
    return mode, str(path)


@contextmanager
def _env_default(key: str, value: str) -> Iterator[None]:
    """Set environment variable ``key`` only if unset, restoring previous state afterwards."""
    previous = os.environ.get(key)
    os.environ.setdefault(key, value)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


def parse_nbf_text(nbf_text: str) -> tuple[np.ndarray, np.ndarray]:
    """Parse ``testBonds_cut.top`` text into atomic numbers and a ``(20, nat)`` neighbor table.

    Args:
        nbf_text: Multi-line neighbor-list text (atom count, element symbols, 20 neighbor rows).

    Returns:
        Tuple ``(atomic_numbers, nbf_table)`` of ``int32`` NumPy arrays.

    Raises:
        ValueError: If ``nbf_text`` has fewer than 22 non-empty lines, mismatched shapes,
            or unrecognized chemical element symbols.
        GFNFFExecutionError: If any parsed atomic number lies outside ``1 <= Z <= 103``
            (e.g., trans-lawrencium elements ``Rf..Og``).
    """
    global _SYMBOL_TO_Z
    if _SYMBOL_TO_Z is None:
        from pymatgen.core.periodic_table import Element

        _SYMBOL_TO_Z = {el.symbol: el.Z for el in Element}
    lines = [line for line in str(nbf_text).splitlines() if line.strip()]
    if len(lines) < 22:
        raise ValueError(
            f"NBF text needs nat, symbols and 20 neighbor rows; got {len(lines)} lines"
        )
    nat = int(lines[0].split()[0])
    symbols = lines[1].split()
    if len(symbols) != nat:
        raise ValueError(f"NBF symbol row has {len(symbols)} entries, expected {nat}")
    nbf = np.array([[int(v) for v in line.split()] for line in lines[2:22]], dtype=np.int32)
    if nbf.shape != (20, nat):
        raise ValueError(f"NBF neighbor table has shape {nbf.shape}, expected (20, {nat})")
    unknown = [s for s in symbols if s not in _SYMBOL_TO_Z]
    if unknown:
        unique_unknown = ", ".join(dict.fromkeys(unknown))
        raise ValueError(f"Unknown chemical element symbol(s) in NBF text: {unique_unknown}")
    z_arr = np.array([_SYMBOL_TO_Z[s] for s in symbols], dtype=np.int32)
    if np.any((z_arr < _MIN_GFNFF_Z) | (z_arr > _MAX_GFNFF_Z)):
        unsupported = ", ".join(
            dict.fromkeys(
                f"{sym} (Z={int(z)})"
                for sym, z in zip(symbols, z_arr, strict=True)
                if z < _MIN_GFNFF_Z or z > _MAX_GFNFF_Z
            )
        )
        raise GFNFFExecutionError(
            f"GFN-FF only supports atomic numbers {_MIN_GFNFF_Z} <= Z <= {_MAX_GFNFF_Z} "
            f"(H..Lr); got unsupported element(s): {unsupported}"
        )
    return z_arr, nbf


def _resolve_external_xtb_binary() -> Path | None:
    """Locate an external modified ``xtb`` binary for non-Linux fallback execution."""
    for env_var in ("SLICES_XTB_PATH", "XTB_MOD_PATH"):
        configured = os.environ.get(env_var, "").strip()
        if configured:
            candidate = Path(configured).expanduser()
            if candidate.is_file():
                return candidate
    found = shutil.which(_XTB_BINARY_NAME)
    return Path(found) if found else None


def _run_external_xtb_fallback(
    nbf_text: str,
    reason: BaseException | None = None,
) -> dict[str, Any]:
    """Execute an external modified ``xtb`` binary when bundled ``libgfnff`` cannot load.

    Args:
        nbf_text: Multi-line ``testBonds_cut.top`` neighbor-list text.
        reason: Underlying ``ImportError`` or ``OSError`` from loading ``slices._vendor.gfnff``.

    Returns:
        Dictionary with ``blist``, ``vbond``, ``alist``, ``vangl``, and ``metadata``.

    Raises:
        GFNFFExecutionError: If no external ``xtb`` binary is configured or execution fails.
    """
    xtb_bin = _resolve_external_xtb_binary()
    if xtb_bin is None:
        detail = f" ({type(reason).__name__}: {reason})" if reason is not None else ""
        raise GFNFFExecutionError(
            f"Bundled Linux x86_64 libgfnff could not be loaded{detail}, and no external "
            f"modified xtb binary was found. Build '{_XTB_BINARY_NAME}' for this platform "
            "and set SLICES_XTB_PATH=/path/to/xtb_noring_nooutput_nostdout_noCN."
        ) from reason

    with tempfile.TemporaryDirectory() as tmp_dir:
        top_path = Path(tmp_dir) / "testBonds_cut.top"
        json_path = Path(tmp_dir) / "gfnff_lists.json"
        top_path.write_text(str(nbf_text), encoding="utf-8")
        try:
            proc = subprocess.run(
                [
                    str(xtb_bin),
                    "--gfnff",
                    "testBonds_cut.top",
                    "--wrtopo",
                    "blist,vbond,alist,vangl",
                ],
                cwd=tmp_dir,
                shell=False,
                capture_output=True,
                text=True,
                timeout=_XTB_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GFNFFExecutionError(
                f"External xtb topology helper timed out after {_XTB_TIMEOUT_SECONDS} s: {xtb_bin}"
            ) from exc
        except OSError as exc:
            raise GFNFFExecutionError(
                f"Failed to execute external xtb topology helper ({xtb_bin}): {exc}"
            ) from exc

        if not json_path.is_file():
            stderr_tail = (proc.stderr or proc.stdout or "").strip()[-400:]
            raise GFNFFExecutionError(
                f"External xtb helper ({xtb_bin}, exit={proc.returncode}) did not produce "
                f"gfnff_lists.json" + (f": {stderr_tail}" if stderr_tail else "")
            )
        raw_text = json_path.read_text(encoding="utf-8").replace("********", "       0")
        try:
            data: dict[str, Any] = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise GFNFFExecutionError(
                f"External xtb helper produced invalid JSON in gfnff_lists.json: {exc}"
            ) from exc

    data.setdefault("metadata", {}).update(
        {"param_mode": "external_xtb", "xtb_binary": str(xtb_bin)}
    )
    return data


def run_gfnff_helper(nbf_text: str) -> dict[str, Any]:
    """Run GFN-FF topology generation on an NBF neighbor table.

    Uses the bundled Linux x86_64 ``libgfnff`` shared library in memory by default,
    falling back to ``_run_external_xtb_fallback`` only if ``slices._vendor.gfnff``
    raises ``ImportError`` or ``OSError`` on non-Linux hosts.

    Args:
        nbf_text: ``testBonds_cut.top`` text produced by ``SLICES.get_nbf_blist``.

    Returns:
        Dictionary containing ``blist``, ``vbond``, ``alist``, ``vangl`` (1-based atom
        indices), and ``metadata``.
    """
    numbers, nbf = parse_nbf_text(nbf_text)
    try:
        from slices._vendor import gfnff
    except (ImportError, OSError) as exc:
        return _run_external_xtb_fallback(nbf_text, reason=exc)

    param_mode, param_file = _selected_params()
    with _env_default("SLICES_VENDOR_GFNFF_RAB_MODE", param_mode):
        data: dict[str, Any] = gfnff.GFNFFTopology.from_nbf(
            numbers, nbf, printlevel=0, parametrisation=param_file
        ).to_legacy_lists()
    data.setdefault("metadata", {}).update({"param_mode": param_mode})
    return data


def write_debug_files(
    nbf_text: str,
    data: dict[str, Any],
    directory: str | os.PathLike[str] = ".",
) -> None:
    """Write ``testBonds_cut.top`` and ``gfnff_lists.json`` when ``check_results=True``.

    Args:
        nbf_text: Input ``testBonds_cut.top`` text.
        data: Topology output dictionary returned by ``run_gfnff_helper``.
        directory: Destination directory path.
    """
    target_dir = Path(directory)
    (target_dir / "testBonds_cut.top").write_text(nbf_text, encoding="utf-8")
    with (target_dir / "gfnff_lists.json").open("w", encoding="utf-8") as handle:
        json.dump(data, handle)


def _self_test() -> None:
    """Validate methane topology and ``Na3MnCoNiO6`` against stored reference targets."""
    methane = (
        "5\nC H H H H\n2 1 1 1 1\n3 0 0 0 0\n4 0 0 0 0\n5 0 0 0 0\n"
        + "0 0 0 0 0\n" * 15
        + "4 1 1 1 1\n"
    )
    data = run_gfnff_helper(methane)
    assert sorted(map(tuple, data["blist"])) == [(2, 1), (3, 1), (4, 1), (5, 1)], data["blist"]
    assert len(data["alist"]) == 6, len(data["alist"])
    print(f"methane: 4 bonds, 6 angles ({data['metadata']['param_mode']})")

    from slices.core import SLICES

    # First structure of data/mp20_nonmetal/mp20_v4_benchmark_2383.csv
    example = (
        "o x a DDO j OOO o Na Na Na Mn Co Ni O O O O O O 0 8 oo- 0 10 o-o 0 10 -oo 0 6 o-- "
        "0 6 -o- 0 11 ooo 1 6 ooo 1 11 +o+ 1 11 o++ 1 7 +oo 1 7 o+o 1 9 +++ 2 7 ooo 2 9 +o+ "
        "2 9 o++ 2 8 +oo 2 8 o+o 2 10 oo+ 3 11 ooo 3 6 o-o 3 6 -oo 3 9 +oo 3 9 o+o 3 7 ooo "
        "4 10 ooo 4 8 +oo 4 8 o+o 4 11 +oo 4 11 o+o 4 6 ooo 5 9 ooo 5 7 o-o 5 7 -oo 5 10 o-o "
        "5 10 -oo 5 8 ooo"
    )
    s = SLICES()
    s.from_SLICES(example)
    inner_p, inds, weights = s.get_inner_p_target()
    got = (
        float(np.trace(inner_p)),
        float(np.abs(inner_p).sum()),
        len(inds[0]),
        float(sum(weights)),
    )
    want = (178.74144, 178.74144, 126, 61.23)  # computed with the xtb-era code path (d40c909)
    assert np.allclose(got, want, rtol=1e-6), (got, want)
    print(f"Na3MnCoNiO6: reconstruction targets match the stored reference {want}")


if __name__ == "__main__":
    _self_test()
