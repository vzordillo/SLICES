#!/usr/bin/env python3
"""Validate a SLICES v4.0.2 installation, backends, CLI, and optional MLIPs.

Checks Python runtime compatibility (>= 3.10), core scientific dependencies,
``slices`` package modules, bundled GFN-FF topology generation (or external ``xtb``
fallback), NequIP default relaxation backend configuration, CLI entry-point
availability, and installed optional MLIP adapters without requiring M3GNet or
any optional force-field package.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

CORE_DEPENDENCIES: tuple[tuple[str, str], ...] = (
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("pandas", "pandas"),
    ("networkx", "networkx"),
    ("sympy", "sympy"),
    ("pymatgen", "pymatgen"),
    ("sklearn", "scikit-learn"),
    ("ase", "ase"),
    ("torch", "torch"),
    ("nequip", "nequip"),
    ("matscipy", "matscipy"),
)

OPTIONAL_BACKENDS: tuple[tuple[str, str], ...] = (
    ("chgnet", "CHGNet (relax_model='chgnet')"),
    ("mattersim", "MatterSim (relax_model='mattersim')"),
    ("orb_models", "ORBv3 (relax_model='orbv3')"),
    ("mace", "MACE-MP (relax_model='mace')"),
    ("m3gnet", "M3GNet (relax_model='m3gnet')"),
    ("openequivariance", "OpenEquivariance (faster CUDA NequIP kernels)"),
)


def _check_module(module_name: str, label: str, *, required: bool = True) -> tuple[bool, str]:
    """Import or probe a module and format a single-line status report."""
    try:
        if required:
            mod = importlib.import_module(module_name)
            ver = getattr(mod, "__version__", None)
            detail = f" (v{ver})" if ver else ""
            return True, f"[OK]   {label}{detail}"
        found = importlib.util.find_spec(module_name) is not None
        if found:
            return True, f"[OK]   {label}: installed"
        return False, f"[INFO] {label}: not installed (optional)"
    except Exception as exc:
        tag = "[FAIL]" if required else "[WARN]"
        return False, f"{tag} {label}: {type(exc).__name__}: {exc}"


def _check_python_version() -> tuple[bool, str]:
    """Verify Python >= 3.10."""
    ver = sys.version_info
    ver_str = f"{ver.major}.{ver.minor}.{ver.micro}"
    if (ver.major, ver.minor) >= (3, 10):
        return True, f"[OK]   Python {ver_str} (>= 3.10 required)"
    return False, f"[FAIL] Python {ver_str} (< 3.10 is unsupported)"


def _check_gfnff() -> tuple[bool, str]:
    """Verify GFN-FF topology generation on a 5-atom methane NBF fixture."""
    try:
        from slices.gfnff_helper import run_gfnff_helper

        methane_nbf = (
            "5\nC H H H H\n2 1 1 1 1\n3 0 0 0 0\n4 0 0 0 0\n5 0 0 0 0\n"
            + "0 0 0 0 0\n" * 15
            + "4 1 1 1 1\n"
        )
        topo = run_gfnff_helper(methane_nbf)
        n_bonds = len(topo.get("blist", []))
        n_angles = len(topo.get("alist", []))
        mode = topo.get("metadata", {}).get("param_mode", "unknown")
        if n_bonds == 4 and n_angles == 6:
            return True, f"[OK]   slices.gfnff_helper: methane 4 bonds, 6 angles ({mode})"
        msg = (
            f"[FAIL] slices.gfnff_helper: unexpected methane topology "
            f"({n_bonds} bonds, {n_angles} angles)"
        )
        return False, msg
    except Exception as exc:
        return False, f"[FAIL] slices.gfnff_helper: {type(exc).__name__}: {exc}"


def _check_relax_backends() -> tuple[bool, str]:
    """Verify default NequIP resolution and inspect local compiled-model cache."""
    try:
        from slices import relax_backends

        resolved_name, device = relax_backends.resolve_relax_model("auto")
        cache_dir = Path(relax_backends._cache_dir())
        cached = sorted(p.name for p in cache_dir.glob("*.pth")) if cache_dir.is_dir() else []
        cache_note = (
            f"{len(cached)} compiled artifact(s) in {cache_dir}"
            if cached
            else "no compiled cache yet (run `python -m slices.relax_backends --prepare`)"
        )
        return (
            True,
            f"[OK]   slices.relax_backends: auto -> {resolved_name} on {device} ({cache_note})",
        )
    except Exception as exc:
        return False, f"[FAIL] slices.relax_backends: {type(exc).__name__}: {exc}"


def _check_cli() -> tuple[bool, str]:
    """Check availability of the ``slices`` CLI module and console script."""
    cli_bin = shutil.which("slices")
    spec = importlib.util.find_spec("slices.cli")
    if spec is not None:
        try:
            cli_mod = importlib.import_module("slices.cli")
            if callable(getattr(cli_mod, "main", None)):
                bin_note = f"console script `{cli_bin}`" if cli_bin else "`python -m slices.cli`"
                return True, f"[OK]   slices.cli: entry point ready ({bin_note})"
        except Exception as exc:
            return False, f"[FAIL] slices.cli: import failed ({type(exc).__name__}: {exc})"
    if cli_bin:
        return True, f"[OK]   slices CLI binary found at {cli_bin}"
    return False, "[INFO] slices.cli: module not yet installed"


def _run_quick_roundtrip(use_relax: bool = False) -> tuple[bool, str]:
    """Run a fast structure -> SLICES -> canonical -> ZL* (or NequIP) check."""
    try:
        from pymatgen.core import Lattice, Structure

        from slices.core import SLICES

        sample_cif = REPO_ROOT / "examples" / "NdSiRu.cif"
        if sample_cif.is_file():
            structure = Structure.from_file(filename=str(sample_cif))
            label = "NdSiRu.cif"
        else:
            structure = Structure(
                Lattice.cubic(5.64),
                ["Na", "Cl"],
                [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
            )
            label = "NaCl (cubic)"

        relax_model: str | None = "auto" if use_relax else None
        backend = SLICES(relax_model=relax_model)
        slices_str = backend.structure2SLICES(structure)
        is_valid = backend.check_SLICES(slices_str, strategy=4)
        canonical = backend.get_canonical_SLICES(slices_str, strategy=4)
        if not is_valid or not canonical.strip():
            return False, f"[FAIL] quick round-trip ({label}): validation/canonicalization failed"

        reconstructed, energy = backend.SLICES2structure(slices_str)
        if use_relax:
            msg = (
                f"[OK]   quick round-trip ({label}, auto relax): "
                f"{len(reconstructed)} sites, E={energy:.6f} eV/atom"
            )
            return True, msg
        msg = (
            f"[OK]   quick round-trip ({label}, ZL* geometry): "
            f"{len(reconstructed)} sites reconstructed (E={energy:.1f})"
        )
        return True, msg
    except Exception as exc:
        return False, f"[FAIL] quick round-trip: {type(exc).__name__}: {exc}"


def main(argv: Sequence[str] | None = None) -> int:
    """Execute SLICES installation validation checks.

    Args:
        argv: Optional command-line arguments.

    Returns:
        Exit code ``0`` when all required checks pass, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description="Validate SLICES v4.0.2 installation.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="run a fast encode/validate/canonicalize/ZL* geometry round-trip check",
    )
    parser.add_argument(
        "--quick-relax",
        action="store_true",
        help="run --quick with full relax_model='auto' NequIP relaxation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit validation summary as JSON",
    )
    args = parser.parse_args(argv)

    summary: dict[str, Any] = {"passed": True, "sections": {}}

    def record(section: str, ok: bool, message: str, *, required: bool = True) -> None:
        summary["sections"].setdefault(section, []).append(
            {"ok": ok, "required": required, "message": message}
        )
        if required and not ok:
            summary["passed"] = False
        if not args.json:
            print(f"  {message}")

    if not args.json:
        print("=" * 68)
        print("SLICES v4.0.2 Installation Validation")
        print("=" * 68)
        print("\n1. Python Runtime:")
    ok, msg = _check_python_version()
    record("python", ok, msg)

    if not args.json:
        print("\n2. Core Scientific Dependencies:")
    for mod_name, label in CORE_DEPENDENCIES:
        ok, msg = _check_module(mod_name, label, required=True)
        record("core_dependencies", ok, msg)

    if not args.json:
        print("\n3. SLICES Package & Backends:")
    for mod_name in ("slices", "slices.exceptions", "slices.core", "slices.tobascco_net"):
        ok, msg = _check_module(mod_name, mod_name, required=True)
        record("slices_package", ok, msg)
    ok, msg = _check_gfnff()
    record("slices_package", ok, msg)
    ok, msg = _check_relax_backends()
    record("slices_package", ok, msg)
    ok, msg = _check_cli()
    record("slices_package", ok, msg, required=False)
    for opt_mod in ("slices.mlip_relaxer", "slices.decoding_strategies"):
        ok, msg = _check_module(opt_mod, opt_mod, required=False)
        record("slices_package", ok, msg, required=False)

    if not args.json:
        print("\n4. Optional Force-Field / Acceleration Packages:")
    for mod_name, label in OPTIONAL_BACKENDS:
        ok, msg = _check_module(mod_name, label, required=False)
        record("optional_backends", ok, msg, required=False)

    if args.quick or args.quick_relax:
        if not args.json:
            print("\n5. Quick Functional Round-Trip:")
        ok, msg = _run_quick_roundtrip(use_relax=args.quick_relax)
        record("quick_roundtrip", ok, msg, required=True)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("\n" + "=" * 68)
        if summary["passed"]:
            print("[OK]   SLICES v4.0.2 installation validation passed.")
        else:
            print("[FAIL] One or more required checks failed; review messages above.")
        print("=" * 68)

    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
