"""Compare the force fields used in the final relaxation step of SLICES decoding.

Decodes real SLICES strings from the MP-20 non-metal benchmark dataset
(``data/mp20_nonmetal/mp20_v4_benchmark_2383.csv``) with each requested ``relax_model``,
reporting single-process decode latency per structure, failure counts, and formation
energy error against DFT reference values (using ``data/mp20_nonmetal/chemPotMP.json``).

Run from the repository root, for example::

    python -m slices.relax_backends --prepare
    python examples/3.benchmark_relax_models.py --n 32
    python examples/3.benchmark_relax_models.py --n 32 --models auto nequip-m+l
    SLICES_DEVICE=cuda python examples/3.benchmark_relax_models.py --models nequip-l
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
from typing import TYPE_CHECKING, Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
warnings.filterwarnings("ignore")

from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from slices.core import SLICES

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pymatgen.core.structure import Structure

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_CSV = os.path.join(ROOT, "data/mp20_nonmetal/mp20_v4_benchmark_2383.csv")
DEFAULT_CHEM_POT = os.path.join(ROOT, "data/mp20_nonmetal/chemPotMP.json")


def formation_energy(
    structure: Structure,
    energy_per_atom: float,
    chem_pot: dict[str, float],
) -> float:
    """Compute elemental-reference formation energy per atom in eV/atom.

    Args:
        structure: Relaxed crystal structure.
        energy_per_atom: Predicted total energy per atom in eV/atom.
        chem_pot: Elemental chemical potentials in eV/atom keyed by element symbol.

    Returns:
        Predicted formation energy per atom in eV/atom.
    """
    try:
        prim = SpacegroupAnalyzer(structure).get_primitive_standard_structure()
    except Exception:
        prim = structure
    comp = prim.composition
    total = energy_per_atom * comp.num_atoms - sum(
        amt * chem_pot[el] for el, amt in comp.get_el_amt_dict().items()
    )
    return float(total / comp.num_atoms)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the SLICES relaxation model benchmark.

    Args:
        argv: Optional sequence of command-line arguments.

    Returns:
        Process exit code (``0`` on completion).
    """
    description = (__doc__ or "").splitlines()[0]
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--chem-pot", default=DEFAULT_CHEM_POT)
    parser.add_argument(
        "--n",
        type=int,
        default=32,
        help="number of SLICES to decode (default 32)",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--max-atoms",
        type=int,
        default=20,
        help="skip SLICES with more atoms (default 20, the fast relax() path)",
    )
    parser.add_argument("--models", nargs="+", default=["auto", "nequip-m+l"])
    parser.add_argument(
        "--out",
        default=None,
        help="optional JSON file for per-structure results",
    )
    args = parser.parse_args(argv)

    csv.field_size_limit(10**9)
    with open(args.csv, encoding="utf-8") as csv_fh:
        rows = list(csv.DictReader(csv_fh))
    with open(args.chem_pot, encoding="utf-8") as pot_fh:
        chem_pot: dict[str, float] = json.load(pot_fh)

    random.Random(args.seed).shuffle(rows)
    probe = SLICES(relax_model=None)
    picked: list[dict[str, str]] = []
    for row in rows:
        try:
            probe.from_SLICES(row["SLICES"])
        except Exception:
            continue
        if len(probe.atom_types) <= args.max_atoms:
            picked.append(row)
        if len(picked) == args.n:
            break
    rel_csv = os.path.relpath(args.csv, ROOT)
    print(f"{len(picked)} SLICES from {rel_csv} (seed {args.seed}, <= {args.max_atoms} atoms)\n")

    report: list[str] = []
    details: dict[str, list[dict[str, Any]]] = {}
    for model in args.models:
        t0 = time.time()
        try:
            cg = SLICES(relax_model=model)
        except Exception as exc:
            print(f"{model}: cannot be used here ({type(exc).__name__}: {exc})\n")
            continue
        setup = time.time() - t0
        desc = getattr(cg.relaxer, "description", "")
        device = getattr(cg.relaxer, "device", "cpu")
        if picked:
            with contextlib.suppress(Exception):
                cg.SLICES2structure(picked[0]["SLICES"])  # warm-up
        times: list[float] = []
        errors: list[float] = []
        failed = 0
        details[model] = []
        for row in picked:
            t1 = time.time()
            try:
                structure, energy = cg.SLICES2structure(row["SLICES"])
                ef = formation_energy(structure, energy, chem_pot)
                ref_ef = float(row["formation_energy_per_atom"])
                err = ef - ref_ef
                errors.append(abs(err))
                details[model].append({"slices": row["SLICES"], "eform": ef, "ref": ref_ef})
            except Exception as exc:
                failed += 1
                details[model].append({"slices": row["SLICES"], "error": repr(exc)[:200]})
            times.append(time.time() - t1)
        mean_time = statistics.mean(times) if times else 0.0
        line = (
            f"{model:11s} -> {cg.relax_model:10s} on {device:4s}  setup {setup:5.1f}s  "
            f"decode {mean_time:6.2f} s/structure  failed {failed}/{len(picked)}"
        )
        if errors:
            within_tol = sum(err <= 0.05 for err in errors)
            line += (
                f"  |eform - DFT| mean {statistics.mean(errors):.3f} "
                f"median {statistics.median(errors):.3f} "
                f"eV/atom, <=0.05 eV: {within_tol}/{len(errors)}"
            )
        print(line + (f"\n            {desc}" if desc else "") + "\n", flush=True)
        report.append(line)

    print("summary:\n  " + "\n  ".join(report))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as out_fh:
            json.dump(details, out_fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
