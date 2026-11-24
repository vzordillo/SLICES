#!/usr/bin/env python3
"""Compare SLICES v4.0.2 NequIP relaxers against optional MLIP backends.

Evaluates SLICES decoding latency, reconstruction success rate, and (when DFT
reference formation energies and elemental chemical potentials are provided)
formation-energy MAE/median error across the built-in NequIP models (``auto``,
``nequip-s+l``, ``nequip-m+l``, ``nequip-l``) and optional MLIP adapters
(``chgnet``, ``mattersim``, ``orbv3``, ``mace``, ``m3gnet``). Uninstalled
optional MLIPs are gracefully skipped and recorded in the summary without
failing the benchmark.

Examples::

    python tools/benchmarks/run_comparison_test.py --n 16
    python tools/benchmarks/run_comparison_test.py --use-examples --include-robust
    python tools/benchmarks/run_comparison_test.py --models auto chgnet mace --out comparison.json
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import os
import random
import statistics
import sys
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pymatgen.core.structure import Structure

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_CSV = REPO_ROOT / "data" / "mp20_nonmetal" / "mp20_v4_benchmark_2383.csv"
DEFAULT_CHEM_POT = REPO_ROOT / "data" / "mp20_nonmetal" / "chemPotMP.json"
DEFAULT_MODELS: tuple[str, ...] = ("auto", "chgnet", "mattersim", "orbv3", "mace", "m3gnet")


def _formation_energy(
    structure: Structure,
    energy_per_atom: float,
    chem_pot: dict[str, float],
) -> float:
    """Compute elemental-reference formation energy per atom in eV/atom."""
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    try:
        prim = SpacegroupAnalyzer(structure).get_primitive_standard_structure()
    except Exception:
        prim = structure
    comp = prim.composition
    total = energy_per_atom * comp.num_atoms - sum(
        amt * chem_pot[el] for el, amt in comp.get_el_amt_dict().items()
    )
    return float(total / comp.num_atoms)


def _load_benchmark_samples(
    csv_path: Path,
    n_samples: int,
    seed: int,
    max_atoms: int,
    use_examples: bool,
) -> list[dict[str, Any]]:
    """Load SLICES benchmark entries from MP-20 CSV or ``examples/*.cif``."""
    from pymatgen.core.structure import Structure

    from slices.core import SLICES

    probe = SLICES(relax_model=None)
    if use_examples or not csv_path.is_file():
        samples: list[dict[str, Any]] = []
        for cif_path in sorted((REPO_ROOT / "examples").glob("*.cif")):
            struct = Structure.from_file(filename=str(cif_path))
            if len(struct) <= max_atoms:
                slices_str = probe.structure2SLICES(struct)
                samples.append(
                    {"id": cif_path.stem, "SLICES": slices_str, "ref_eform": None}
                )
        return samples[:n_samples]

    csv.field_size_limit(10**9)
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    random.Random(seed).shuffle(rows)

    picked: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        slices_str = row.get("SLICES", "")
        if not slices_str:
            continue
        try:
            probe.from_SLICES(slices_str)
        except Exception:
            continue
        if len(probe.atom_types) <= max_atoms:
            ref_val = row.get("formation_energy_per_atom")
            picked.append(
                {
                    "id": row.get("material_id") or f"row_{idx}",
                    "SLICES": slices_str,
                    "ref_eform": float(ref_val) if ref_val not in (None, "") else None,
                }
            )
        if len(picked) >= n_samples:
            break
    return picked


def _evaluate_model(
    model_name: str,
    samples: list[dict[str, Any]],
    chem_pot: dict[str, float] | None,
    *,
    use_robust: bool = False,
) -> dict[str, Any]:
    """Benchmark a single ``relax_model`` (standard or robust decoding)."""
    from slices.core import SLICES

    mode_label = "robust" if use_robust else "standard"
    t0 = time.perf_counter()
    try:
        backend = SLICES(relax_model=model_name)
    except Exception as exc:
        return {
            "model": model_name,
            "mode": mode_label,
            "status": "skipped",
            "reason": f"{type(exc).__name__}: {exc}",
        }
    setup_s = time.perf_counter() - t0
    device = getattr(backend.relaxer, "device", "none")
    description = getattr(backend.relaxer, "description", "")

    if samples:
        with contextlib.suppress(Exception):
            backend.SLICES2structure(samples[0]["SLICES"])

    times: list[float] = []
    abs_errors: list[float] = []
    records: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for item in samples:
        t_start = time.perf_counter()
        try:
            if use_robust:
                structure, energy = backend.robust_SLICES2structure(item["SLICES"])
            else:
                structure, energy = backend.SLICES2structure(item["SLICES"])
            elapsed = time.perf_counter() - t_start
            times.append(elapsed)
            succeeded += 1
            rec: dict[str, Any] = {
                "id": item["id"],
                "success": True,
                "energy_per_atom": float(energy),
                "time_s": elapsed,
            }
            if chem_pot is not None and item["ref_eform"] is not None and energy != 0.0:
                pred_ef = _formation_energy(structure, float(energy), chem_pot)
                err = abs(pred_ef - float(item["ref_eform"]))
                abs_errors.append(err)
                rec["pred_eform"] = pred_ef
                rec["ref_eform"] = item["ref_eform"]
                rec["abs_error"] = err
            records.append(rec)
        except Exception as exc:
            elapsed = time.perf_counter() - t_start
            times.append(elapsed)
            failed += 1
            records.append(
                {
                    "id": item["id"],
                    "success": False,
                    "error": f"{type(exc).__name__}: {exc}"[:200],
                    "time_s": elapsed,
                }
            )

    return {
        "model": model_name,
        "resolved_model": backend.relax_model,
        "mode": mode_label,
        "status": "completed",
        "device": device,
        "description": description,
        "setup_s": setup_s,
        "total": len(samples),
        "succeeded": succeeded,
        "failed": failed,
        "mean_time_s": statistics.mean(times) if times else 0.0,
        "median_time_s": statistics.median(times) if times else 0.0,
        "eform_mae": statistics.mean(abs_errors) if abs_errors else None,
        "eform_median_ae": statistics.median(abs_errors) if abs_errors else None,
        "records": records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the NequIP vs optional-MLIP comparison."""
    parser = argparse.ArgumentParser(
        description="Compare SLICES v4.0.2 NequIP relaxers vs optional MLIP backends."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="benchmark CSV path")
    parser.add_argument(
        "--chem-pot",
        type=Path,
        default=DEFAULT_CHEM_POT,
        help="elemental chemical potentials JSON path",
    )
    parser.add_argument("--n", type=int, default=16, help="number of SLICES samples (default 16)")
    parser.add_argument("--seed", type=int, default=0, help="random shuffle seed (default 0)")
    parser.add_argument(
        "--max-atoms",
        type=int,
        default=20,
        help="maximum atoms per unit cell (default 20)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="relax_model names to compare (uninstalled optional MLIPs are skipped)",
    )
    parser.add_argument(
        "--use-examples",
        action="store_true",
        help="benchmark on examples/*.cif instead of the MP-20 CSV dataset",
    )
    parser.add_argument(
        "--include-robust",
        action="store_true",
        help="also evaluate opt-in robust_SLICES2structure for each available model",
    )
    parser.add_argument("--out", type=Path, default=None, help="optional JSON output file")
    args = parser.parse_args(argv)

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    warnings.filterwarnings("ignore")

    chem_pot: dict[str, float] | None = None
    if not args.use_examples and args.chem_pot.is_file():
        with args.chem_pot.open(encoding="utf-8") as fh:
            chem_pot = json.load(fh)

    samples = _load_benchmark_samples(
        csv_path=args.csv,
        n_samples=args.n,
        seed=args.seed,
        max_atoms=args.max_atoms,
        use_examples=args.use_examples,
    )
    print(
        f"Loaded {len(samples)} SLICES sample(s) "
        f"(max_atoms={args.max_atoms}, seed={args.seed})\n"
    )

    all_runs: list[dict[str, Any]] = []
    modes = [False, True] if args.include_robust else [False]
    for model in args.models:
        for use_robust in modes:
            res = _evaluate_model(model, samples, chem_pot, use_robust=use_robust)
            all_runs.append(res)
            if res["status"] == "skipped":
                print(f"[SKIP] {model:11s} ({res['mode']:8s}): {res['reason']}")
                continue
            line = (
                f"[OK]   {model:11s} -> {res['resolved_model']:10s} ({res['mode']:8s}) "
                f"on {res['device']:4s}  setup {res['setup_s']:5.1f}s  "
                f"decode {res['mean_time_s']:6.2f}s  "
                f"ok {res['succeeded']}/{res['total']}"
            )
            if res["eform_mae"] is not None:
                line += (
                    f"  |eform-DFT| MAE {res['eform_mae']:.3f} "
                    f"median {res['eform_median_ae']:.3f} eV/atom"
                )
            print(line, flush=True)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8") as fh:
            json.dump({"samples": len(samples), "runs": all_runs}, fh, indent=2)
        print(f"\nSaved comparison report to {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
