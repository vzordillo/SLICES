#!/usr/bin/env python3
"""Run and archive the 2,383-structure MP-20 quantitative baseline benchmark.

Evaluates SLICES v4.0.2 crystal reconstruction across three paired passes on all
2,383 entries of ``data/mp20_nonmetal/mp20_v4_benchmark_2383.csv``:

1. ``default``: ``relax_model="auto"`` (``nequip-s+l``), ``lj_mixing="legacy"``,
   standard :meth:`slices.core.SLICES.SLICES2structure`.
2. ``lorentz``: ``relax_model="auto"``, ``lj_mixing="lorentz"``, standard
   :meth:`slices.core.SLICES.SLICES2structure`.
3. ``robust``: ``relax_model="auto"``, ``lj_mixing="legacy"``, opt-in
   :meth:`slices.core.SLICES.robust_SLICES2structure` (``n_starts=3, seed=0``).

When ``data/mp20/{train,val,test}.csv`` is present, rows are uniquely joined to
their reference Materials Project CIF structures via
``(formation_energy_per_atom, band_gap, reduced_formula)`` to compute strict and
loose ``StructureMatcher`` recovery rates alongside DFT formation-energy error,
structural validity, space-group preservation, canonical SLICES round-trip
consistency, and non-invasive NequIP relaxation telemetry.

Example::

    python tools/benchmarks/run_mp20_baseline.py --workers 24
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import contextlib
import csv
import datetime
import io
import json
import math
import multiprocessing as mp
import os
import statistics
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
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
DEFAULT_MP20_DIR = REPO_ROOT / "data" / "mp20"
DEFAULT_OUT_DIR = REPO_ROOT / "benchmark" / "v4_0_2_baseline"
PASS_NAMES: tuple[str, ...] = ("default", "lorentz", "robust")


@dataclass(frozen=True)
class PassSpec:
    """Configuration for a single full-dataset benchmark pass.

    Attributes:
        name: Short identifier used in ``summary.json`` and CSV column prefixes.
        relax_model: Force-field model identifier passed to ``SLICES``.
        lj_mixing: Heteronuclear LJ combining rule (``"legacy"`` or ``"lorentz"``).
        use_robust: Whether to call ``robust_SLICES2structure`` instead of
            ``SLICES2structure``.
        n_starts: Number of seeded ZL* starts when ``use_robust`` is ``True``.
        seed: Deterministic RNG seed when ``use_robust`` is ``True``.
    """

    name: str
    relax_model: str
    lj_mixing: str
    use_robust: bool
    n_starts: int = 3
    seed: int = 0


class _RelaxTelemetryProxy:
    """Non-invasive proxy around ``cg.relaxer`` capturing per-structure metrics."""

    def __init__(self, inner: Any) -> None:
        """Initialize the telemetry proxy around a backend relaxer instance."""
        self._inner = inner
        self.called: bool = False
        self.succeeded: bool = False
        self.steps: int = 0
        self.preoptimized: bool = False
        self.retry: int = 0
        self.error_type: str = ""

    def reset(self) -> None:
        """Clear accumulated per-structure relaxation counters."""
        self.called = False
        self.succeeded = False
        self.steps = 0
        self.preoptimized = False
        self.retry = 0
        self.error_type = ""

    def __getattr__(self, attr: str) -> Any:
        """Delegate attribute lookups to the underlying relaxer."""
        return getattr(self._inner, attr)

    def relax(self, structure: Structure, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Invoke ``self._inner.relax`` and record step/preoptimize/retry metadata."""
        self.called = True
        try:
            res: dict[str, Any] = self._inner.relax(structure, *args, **kwargs)
        except Exception as exc:
            self.succeeded = False
            self.error_type = type(exc).__name__
            raise
        self.succeeded = True
        self.error_type = ""
        self.steps += int(res.get("steps", 0))
        self.preoptimized = bool(res.get("preoptimized", False))
        self.retry = int(res.get("retry", 0))
        return res


_WORKER_STATE: dict[str, Any] = {}


def _configure_worker_env() -> None:
    """Apply deterministic single-thread environment settings inside a process."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["SLICES_TORCH_THREADS"] = "1"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    warnings.filterwarnings("ignore")


def formation_energy(
    structure: Structure,
    energy_per_atom: float,
    chem_pot: dict[str, float],
) -> float:
    """Compute elemental-reference formation energy per atom in eV/atom.

    Matches ``examples/3.benchmark_relax_models.py`` verbatim so benchmark
    results are bit-for-bit comparable across single- and multi-process runs.

    Args:
        structure: Relaxed crystal structure.
        energy_per_atom: Predicted total energy per atom in eV/atom.
        chem_pot: Elemental chemical potentials in eV/atom keyed by element symbol.

    Returns:
        Predicted formation energy per atom in eV/atom.
    """
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


def _init_worker(
    spec: PassSpec,
    chem_pot: dict[str, float],
) -> None:
    """Initialize one cached ``SLICES`` instance and matchers in a spawned worker."""
    _configure_worker_env()
    if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher

    from slices.core import SLICES

    cg = SLICES(relax_model=spec.relax_model, lj_mixing=spec.lj_mixing)  # type: ignore[arg-type]
    proxy = _RelaxTelemetryProxy(cg.relaxer) if cg.relaxer is not None else None
    if proxy is not None:
        cg.relaxer = proxy

    sm_strict = StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
        comparator=ElementComparator(),
    )
    sm_loose = StructureMatcher(
        ltol=0.3,
        stol=0.5,
        angle_tol=10,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
        comparator=ElementComparator(),
    )
    _WORKER_STATE.clear()
    _WORKER_STATE.update(
        {
            "spec": spec,
            "cg": cg,
            "proxy": proxy,
            "chem_pot": chem_pot,
            "sm_strict": sm_strict,
            "sm_loose": sm_loose,
        }
    )


def _evaluate_task(task: dict[str, Any]) -> dict[str, Any]:
    """Decode a single SLICES benchmark entry and compute all per-pass metrics."""
    from pymatgen.core.structure import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    from slices.core import SLICES

    spec: PassSpec = _WORKER_STATE["spec"]
    cg: SLICES = _WORKER_STATE["cg"]
    proxy: _RelaxTelemetryProxy | None = _WORKER_STATE["proxy"]
    chem_pot: dict[str, float] = _WORKER_STATE["chem_pot"]
    sm_strict = _WORKER_STATE["sm_strict"]
    sm_loose = _WORKER_STATE["sm_loose"]

    if proxy is not None:
        proxy.reset()

    slices_str: str = task["slices"]
    dft_eform: float = task["dft_eform"]
    ref_sg: int | None = task["ref_sg"]
    canon_in: str = task["canon_in"]
    ori_poscar: str | None = task["ori_poscar"]

    t0 = time.perf_counter()
    decode_exc: Exception | None = None
    structure: Structure | None = None
    energy: float = 0.0
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            if spec.use_robust:
                structure, energy = cg.robust_SLICES2structure(
                    slices_str,
                    n_starts=spec.n_starts,
                    seed=spec.seed,
                )
            else:
                structure, energy = cg.SLICES2structure(slices_str)
    except Exception as exc:
        decode_exc = exc
    elapsed_s = time.perf_counter() - t0

    gfnff_incomplete = bool(getattr(cg, "_last_gfnff_incomplete", False))
    preoptimized = bool(proxy.preoptimized) if proxy is not None else False
    retry = int(proxy.retry) if proxy is not None else 0
    relax_steps = int(proxy.steps) if proxy is not None else 0
    relax_succeeded = bool(proxy.succeeded) if proxy is not None else (decode_exc is None)

    if decode_exc is not None or structure is None:
        err_name = type(decode_exc).__name__ if decode_exc is not None else "UnknownDecodeError"
        return {
            "row_index": task["row_index"],
            "decoded": False,
            "ok": False,
            "eform": None,
            "abs_err": None,
            "match_strict": None,
            "match_loose": None,
            "struct_valid": None,
            "pred_sg": None,
            "sg_match": None,
            "roundtrip_canonical_match": None,
            "preoptimized": preoptimized,
            "retry": retry,
            "relax_steps": relax_steps,
            "gfnff_incomplete": gfnff_incomplete,
            "seconds": elapsed_s,
            "error_type": err_name,
        }

    ok = relax_succeeded
    if ok:
        eform_val: float | None = formation_energy(structure, float(energy), chem_pot)
        abs_err_val: float | None = abs(eform_val - dft_eform)
        error_type = ""
    else:
        eform_val = None
        abs_err_val = None
        sub_err = proxy.error_type if (proxy is not None and proxy.error_type) else "RelaxFailed"
        error_type = f"RelaxFallback:{sub_err}"

    struct_valid = bool(SLICES.check_structural_validity(structure))

    pred_sg: int | None = None
    prim_std: Structure = structure
    try:
        sga = SpacegroupAnalyzer(structure)
        pred_sg = int(sga.get_space_group_number())
        prim_std = sga.get_primitive_standard_structure()
    except Exception:
        pred_sg = None
        prim_std = structure

    sg_match: bool | None = (pred_sg == ref_sg) if (pred_sg is not None and ref_sg) else False

    roundtrip_match = False
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            re_sli = cg.structure2SLICES(prim_std, strategy=4)
            canon_out = cg.get_canonical_SLICES(re_sli, strategy=4)
        roundtrip_match = canon_out == canon_in
    except Exception:
        roundtrip_match = False

    match_strict: bool | None = None
    match_loose: bool | None = None
    if ori_poscar is not None:
        if not ok:
            match_strict = False
            match_loose = False
        else:
            try:
                ori_checked = Structure.from_str(ori_poscar, "poscar")
                opt2_checked = Structure.from_str(structure.to(fmt="poscar"), "poscar")
                match_strict = bool(sm_strict.fit(ori_checked, opt2_checked))
                match_loose = bool(sm_loose.fit(ori_checked, opt2_checked))
            except Exception:
                match_strict = False
                match_loose = False

    return {
        "row_index": task["row_index"],
        "decoded": True,
        "ok": ok,
        "eform": eform_val,
        "abs_err": abs_err_val,
        "match_strict": match_strict,
        "match_loose": match_loose,
        "struct_valid": struct_valid,
        "pred_sg": pred_sg,
        "sg_match": sg_match,
        "roundtrip_canonical_match": roundtrip_match,
        "preoptimized": preoptimized,
        "retry": retry,
        "relax_steps": relax_steps,
        "gfnff_incomplete": gfnff_incomplete,
        "seconds": elapsed_s,
        "error_type": error_type,
    }


def _load_reference_cifs(
    mp20_dir: Path,
    needed_keys: set[tuple[str, str, str]],
    needed_round_keys: set[tuple[float, float, str]],
) -> tuple[
    dict[tuple[str, str, str], dict[str, str]],
    dict[tuple[float, float, str], dict[str, str]],
]:
    """Index matching MP-20 reference CIF rows from ``train/val/test.csv``."""
    from pymatgen.core.composition import Composition

    exact_map: dict[tuple[str, str, str], dict[str, str]] = {}
    round_map: dict[tuple[float, float, str], dict[str, str]] = {}
    if not mp20_dir.is_dir():
        return exact_map, round_map

    csv.field_size_limit(10**9)
    for split in ("train", "val", "test"):
        split_path = mp20_dir / f"{split}.csv"
        if not split_path.is_file():
            continue
        with split_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                rf = Composition(row["pretty_formula"]).reduced_formula
                ef_str = row["formation_energy_per_atom"]
                bg_str = row["band_gap"]
                ekey = (ef_str, bg_str, rf)
                if ekey in needed_keys and ekey not in exact_map:
                    exact_map[ekey] = {
                        "material_id": row["material_id"],
                        "cif": row["cif"],
                        "split": split,
                    }
                rkey = (round(float(ef_str), 10), round(float(bg_str), 10), rf)
                if rkey in needed_round_keys and rkey not in round_map:
                    round_map[rkey] = {
                        "material_id": row["material_id"],
                        "cif": row["cif"],
                        "split": split,
                    }
    return exact_map, round_map


def _prepare_tasks(
    csv_path: Path,
    mp20_dir: Path,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load benchmark CSV entries, precompute metadata, and attach reference POSCARs."""
    from pymatgen.core.composition import Composition
    from pymatgen.core.structure import Structure

    from slices.core import SLICES

    csv.field_size_limit(10**9)
    with csv_path.open(encoding="utf-8") as fh:
        raw_rows = list(csv.DictReader(fh))
    if limit is not None:
        raw_rows = raw_rows[:limit]

    probe = SLICES(relax_model=None)
    needed_exact: set[tuple[str, str, str]] = set()
    needed_round: set[tuple[float, float, str]] = set()
    parsed_meta: list[dict[str, Any]] = []

    for idx, row in enumerate(raw_rows):
        slices_str = row["SLICES"]
        formula = probe.SLICES2formula(slices_str) or ""
        reduced_formula = Composition(formula).reduced_formula if formula else ""
        probe.from_SLICES(slices_str, strategy=4)
        n_atoms = len(probe.atom_types)
        ref_sg = int(probe.space_group_num) if probe.space_group_num is not None else None
        canon_in = probe.get_canonical_SLICES(slices_str, strategy=4)
        ef_str = row["formation_energy_per_atom"]
        bg_str = row["band_gap"]
        ekey = (ef_str, bg_str, reduced_formula)
        rkey = (round(float(ef_str), 10), round(float(bg_str), 10), reduced_formula)
        needed_exact.add(ekey)
        needed_round.add(rkey)
        parsed_meta.append(
            {
                "row_index": idx,
                "slices": slices_str,
                "formula": formula,
                "reduced_formula": reduced_formula,
                "n_atoms": n_atoms,
                "crystal_system": row.get("crystal_system", ""),
                "ref_sg": ref_sg,
                "dft_eform": float(ef_str),
                "dft_band_gap": float(bg_str),
                "canon_in": canon_in,
                "ekey": ekey,
                "rkey": rkey,
            }
        )

    exact_map, round_map = _load_reference_cifs(mp20_dir, needed_exact, needed_round)

    tasks: list[dict[str, Any]] = []
    for item in parsed_meta:
        matched = exact_map.get(item["ekey"]) or round_map.get(item["rkey"])
        material_id = ""
        ori_poscar: str | None = None
        if matched is not None:
            material_id = matched["material_id"]
            with contextlib.redirect_stdout(io.StringIO()):
                ori_struct = SLICES.to_primitive_if_smaller(
                    Structure.from_str(matched["cif"], "cif")
                )
                ori_poscar = ori_struct.to(fmt="poscar")
        tasks.append(
            {
                "row_index": item["row_index"],
                "material_id": material_id,
                "formula": item["formula"],
                "n_atoms": item["n_atoms"],
                "crystal_system": item["crystal_system"],
                "ref_sg": item["ref_sg"],
                "dft_eform": item["dft_eform"],
                "dft_band_gap": item["dft_band_gap"],
                "slices": item["slices"],
                "canon_in": item["canon_in"],
                "ori_poscar": ori_poscar,
            }
        )
    return tasks


def _percentile(values: list[float], q: float) -> float | None:
    """Compute linear-interpolated percentile ``q`` (0..100) over ``values``."""
    if not values:
        return None
    import numpy as np

    return float(np.percentile(np.asarray(values, dtype=float), q))


def _round_opt(val: float | None, digits: int = 6) -> float | None:
    """Round an optional float cleanly for compact JSON serialization."""
    if val is None or not math.isfinite(val):
        return None
    return round(float(val), digits)


def _aggregate_subset(
    tasks: list[dict[str, Any]],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate benchmark metrics for a subset of ``(task, result)`` pairs."""
    n_total = len(results)
    if n_total == 0:
        return {"total_count": 0}

    n_cif = sum(1 for t in tasks if t["ori_poscar"] is not None)
    decoded_list = [r for r in results if r["decoded"]]
    ok_list = [r for r in results if r["ok"]]
    n_decoded = len(decoded_list)
    n_ok = len(ok_list)
    n_failed = n_total - n_ok
    n_failed_decode = n_total - n_decoded
    n_unrelaxed_fallback = n_decoded - n_ok

    strict_hits = sum(1 for r in results if r["match_strict"] is True)
    loose_hits = sum(1 for r in results if r["match_loose"] is True)
    sv_hits = sum(1 for r in ok_list if r["struct_valid"] is True)
    sg_hits = sum(1 for r in ok_list if r["sg_match"] is True)
    rt_hits = sum(1 for r in ok_list if r["roundtrip_canonical_match"] is True)
    preopt_hits = sum(1 for r in ok_list if r["preoptimized"] is True)
    retry_structs = sum(1 for r in ok_list if r["retry"] > 0)
    retry_total = sum(int(r["retry"]) for r in ok_list)
    gfnff_inc = sum(1 for r in results if r["gfnff_incomplete"] is True)

    abs_errs = [float(r["abs_err"]) for r in ok_list if r["abs_err"] is not None]
    signed_errs = [
        float(r["eform"]) - float(t["dft_eform"])
        for t, r in zip(tasks, results, strict=True)
        if r["ok"] and r["eform"] is not None
    ]
    within_005 = sum(1 for e in abs_errs if e <= 0.05)
    within_010 = sum(1 for e in abs_errs if e <= 0.10)
    rmse = math.sqrt(sum(e * e for e in abs_errs) / len(abs_errs)) if abs_errs else None

    steps_ok = [float(r["relax_steps"]) for r in ok_list]
    secs_all = [float(r["seconds"]) for r in results]

    err_counts = collections.Counter(r["error_type"] for r in results if r["error_type"])
    failure_taxonomy = dict(sorted(err_counts.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "total_count": n_total,
        "cif_matched_count": n_cif,
        "decoded_count": n_decoded,
        "ok_count": n_ok,
        "failed_count": n_failed,
        "failed_decode_count": n_failed_decode,
        "unrelaxed_fallback_count": n_unrelaxed_fallback,
        "ok_rate": _round_opt(n_ok / n_total),
        "decoded_rate": _round_opt(n_decoded / n_total),
        "match_strict_count": strict_hits if n_cif else None,
        "match_strict_rate_all": _round_opt(strict_hits / n_cif) if n_cif else None,
        "match_strict_rate_ok": _round_opt(strict_hits / n_ok) if (n_cif and n_ok) else None,
        "match_loose_count": loose_hits if n_cif else None,
        "match_loose_rate_all": _round_opt(loose_hits / n_cif) if n_cif else None,
        "match_loose_rate_ok": _round_opt(loose_hits / n_ok) if (n_cif and n_ok) else None,
        "struct_valid_count": sv_hits,
        "struct_valid_rate_all": _round_opt(sv_hits / n_total),
        "struct_valid_rate_ok": _round_opt(sv_hits / n_ok) if n_ok else None,
        "sg_match_count": sg_hits,
        "sg_match_rate_all": _round_opt(sg_hits / n_total),
        "sg_match_rate_ok": _round_opt(sg_hits / n_ok) if n_ok else None,
        "roundtrip_canonical_match_count": rt_hits,
        "roundtrip_canonical_match_rate_all": _round_opt(rt_hits / n_total),
        "roundtrip_canonical_match_rate_ok": _round_opt(rt_hits / n_ok) if n_ok else None,
        "preoptimized_count": preopt_hits,
        "preoptimized_rate_ok": _round_opt(preopt_hits / n_ok) if n_ok else None,
        "retry_struct_count": retry_structs,
        "retry_total_count": retry_total,
        "retry_rate_ok": _round_opt(retry_structs / n_ok) if n_ok else None,
        "gfnff_incomplete_count": gfnff_inc,
        "gfnff_incomplete_rate_all": _round_opt(gfnff_inc / n_total),
        "eform_error_ev_per_atom": {
            "count": len(abs_errs),
            "mae": _round_opt(statistics.mean(abs_errs) if abs_errs else None),
            "median_ae": _round_opt(statistics.median(abs_errs) if abs_errs else None),
            "rmse": _round_opt(rmse),
            "std_ae": _round_opt(statistics.pstdev(abs_errs) if len(abs_errs) > 1 else None),
            "p90_ae": _round_opt(_percentile(abs_errs, 90.0)),
            "p95_ae": _round_opt(_percentile(abs_errs, 95.0)),
            "max_ae": _round_opt(max(abs_errs) if abs_errs else None),
            "mean_signed_error": _round_opt(
                statistics.mean(signed_errs) if signed_errs else None
            ),
            "within_0_05_ev_count": within_005,
            "within_0_05_ev_rate_ok": _round_opt(within_005 / len(abs_errs))
            if abs_errs
            else None,
            "within_0_05_ev_rate_all": _round_opt(within_005 / n_total),
            "within_0_10_ev_count": within_010,
            "within_0_10_ev_rate_ok": _round_opt(within_010 / len(abs_errs))
            if abs_errs
            else None,
            "within_0_10_ev_rate_all": _round_opt(within_010 / n_total),
        },
        "relax_steps": {
            "mean": _round_opt(statistics.mean(steps_ok) if steps_ok else None, 3),
            "median": _round_opt(statistics.median(steps_ok) if steps_ok else None, 3),
            "p90": _round_opt(_percentile(steps_ok, 90.0), 3),
            "p95": _round_opt(_percentile(steps_ok, 95.0), 3),
            "max": int(max(steps_ok)) if steps_ok else None,
            "total": int(sum(steps_ok)) if steps_ok else 0,
        },
        "timing_seconds": {
            "mean_s": _round_opt(statistics.mean(secs_all), 4),
            "median_s": _round_opt(statistics.median(secs_all), 4),
            "p90_s": _round_opt(_percentile(secs_all, 90.0), 4),
            "p95_s": _round_opt(_percentile(secs_all, 95.0), 4),
            "p99_s": _round_opt(_percentile(secs_all, 99.0), 4),
            "max_s": _round_opt(max(secs_all), 4),
            "sum_cpu_s": _round_opt(sum(secs_all), 2),
        },
        "failure_taxonomy": failure_taxonomy,
    }


def _summarize_pass(
    spec: PassSpec,
    tasks: list[dict[str, Any]],
    results: list[dict[str, Any]],
    wall_seconds: float,
    resolved_model: str,
) -> dict[str, Any]:
    """Build the full ``summary.json`` entry for one completed benchmark pass."""
    le20_pairs = [
        (t, r) for t, r in zip(tasks, results, strict=True) if int(t["n_atoms"]) <= 20
    ]
    le20_tasks = [p[0] for p in le20_pairs]
    le20_results = [p[1] for p in le20_pairs]

    by_cs: dict[str, dict[str, Any]] = {}
    cs_names = sorted({t["crystal_system"] for t in tasks if t["crystal_system"]})
    for cs in cs_names:
        cs_pairs = [
            (t, r) for t, r in zip(tasks, results, strict=True) if t["crystal_system"] == cs
        ]
        cs_agg = _aggregate_subset([p[0] for p in cs_pairs], [p[1] for p in cs_pairs])
        by_cs[cs] = {
            "total_count": cs_agg["total_count"],
            "ok_rate": cs_agg["ok_rate"],
            "match_strict_rate_all": cs_agg["match_strict_rate_all"],
            "match_loose_rate_all": cs_agg["match_loose_rate_all"],
            "sg_match_rate_all": cs_agg["sg_match_rate_all"],
            "eform_mae": cs_agg["eform_error_ev_per_atom"]["mae"],
        }

    return {
        "config": {
            "name": spec.name,
            "relax_model": spec.relax_model,
            "resolved_relax_model": resolved_model,
            "lj_mixing": spec.lj_mixing,
            "decode_method": (
                f"robust_SLICES2structure(n_starts={spec.n_starts}, seed={spec.seed})"
                if spec.use_robust
                else "SLICES2structure()"
            ),
            "n_starts": spec.n_starts if spec.use_robust else None,
            "seed": spec.seed if spec.use_robust else None,
        },
        "wall_seconds": round(wall_seconds, 3),
        "throughput_structures_per_sec": _round_opt(
            len(results) / wall_seconds if wall_seconds > 0 else None,
            4,
        ),
        "all_structures": _aggregate_subset(tasks, results),
        "subset_le_20_atoms": _aggregate_subset(le20_tasks, le20_results),
        "by_crystal_system": by_cs,
    }


def _transition_counts(
    tasks: list[dict[str, Any]],
    res_a: list[dict[str, Any]],
    res_b: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    """Tabulate paired boolean transitions (A -> B) and cap ID lists at 25 entries."""
    both_true = 0
    gained: list[str] = []
    lost: list[str] = []
    both_false = 0
    for t, ra, rb in zip(tasks, res_a, res_b, strict=True):
        va = bool(ra.get(key) is True)
        vb = bool(rb.get(key) is True)
        label = t["material_id"] or f"row_{t['row_index']}"
        if va and vb:
            both_true += 1
        elif (not va) and vb:
            gained.append(label)
        elif va and (not vb):
            lost.append(label)
        else:
            both_false += 1
    return {
        "both_true": both_true,
        "gained_count": len(gained),
        "lost_count": len(lost),
        "both_false": both_false,
        "net_delta": len(gained) - len(lost),
        "gained_ids_sample": gained[:25],
        "lost_ids_sample": lost[:25],
    }


def _paired_comparison(
    tasks: list[dict[str, Any]],
    base_summary: dict[str, Any],
    cand_summary: dict[str, Any],
    base_res: list[dict[str, Any]],
    cand_res: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute paired head-to-head statistics between candidate pass and baseline."""
    b_all = base_summary["all_structures"]
    c_all = cand_summary["all_structures"]
    b_ef = b_all["eform_error_ev_per_atom"]
    c_ef = c_all["eform_error_ev_per_atom"]

    eform_shifts: list[float] = []
    abs_err_deltas: list[float] = []
    sec_deltas: list[float] = []
    bit_identical = 0

    for rb, rc in zip(base_res, cand_res, strict=True):
        sec_deltas.append(float(rc["seconds"]) - float(rb["seconds"]))
        if rb["ok"] and rc["ok"] and rb["eform"] is not None and rc["eform"] is not None:
            shift = abs(float(rc["eform"]) - float(rb["eform"]))
            eform_shifts.append(shift)
            if shift == 0.0:
                bit_identical += 1
            abs_err_deltas.append(float(rc["abs_err"]) - float(rb["abs_err"]))

    gfnff_rows: list[dict[str, Any]] = []
    for t, rb, rc in zip(tasks, base_res, cand_res, strict=True):
        if rb["gfnff_incomplete"] or rc["gfnff_incomplete"]:
            gfnff_rows.append(
                {
                    "row_index": t["row_index"],
                    "material_id": t["material_id"],
                    "formula": t["formula"],
                    "base_ok": rb["ok"],
                    "cand_ok": rc["ok"],
                    "base_match_strict": rb["match_strict"],
                    "cand_match_strict": rc["match_strict"],
                    "base_match_loose": rb["match_loose"],
                    "cand_match_loose": rc["match_loose"],
                    "base_abs_err": _round_opt(rb["abs_err"]),
                    "cand_abs_err": _round_opt(rc["abs_err"]),
                }
            )

    def _diff_opt(v_cand: float | None, v_base: float | None, digits: int = 6) -> float | None:
        if v_cand is None or v_base is None:
            return None
        return round(float(v_cand) - float(v_base), digits)

    return {
        "candidate_pass": cand_summary["config"]["name"],
        "baseline_pass": base_summary["config"]["name"],
        "headline_deltas": {
            "delta_ok_count": c_all["ok_count"] - b_all["ok_count"],
            "delta_ok_rate": _diff_opt(c_all["ok_rate"], b_all["ok_rate"]),
            "delta_match_strict_count": (
                (c_all["match_strict_count"] - b_all["match_strict_count"])
                if c_all["match_strict_count"] is not None
                and b_all["match_strict_count"] is not None
                else None
            ),
            "delta_match_strict_rate_all": _diff_opt(
                c_all["match_strict_rate_all"],
                b_all["match_strict_rate_all"],
            ),
            "delta_match_loose_count": (
                (c_all["match_loose_count"] - b_all["match_loose_count"])
                if c_all["match_loose_count"] is not None
                and b_all["match_loose_count"] is not None
                else None
            ),
            "delta_match_loose_rate_all": _diff_opt(
                c_all["match_loose_rate_all"],
                b_all["match_loose_rate_all"],
            ),
            "delta_struct_valid_count": (
                c_all["struct_valid_count"] - b_all["struct_valid_count"]
            ),
            "delta_sg_match_count": c_all["sg_match_count"] - b_all["sg_match_count"],
            "delta_roundtrip_canonical_match_count": (
                c_all["roundtrip_canonical_match_count"]
                - b_all["roundtrip_canonical_match_count"]
            ),
            "delta_eform_mae": _diff_opt(c_ef["mae"], b_ef["mae"]),
            "delta_eform_median_ae": _diff_opt(c_ef["median_ae"], b_ef["median_ae"]),
            "delta_eform_rmse": _diff_opt(c_ef["rmse"], b_ef["rmse"]),
            "delta_mean_seconds": _diff_opt(
                c_all["timing_seconds"]["mean_s"],
                b_all["timing_seconds"]["mean_s"],
                4,
            ),
            "wall_seconds_ratio": _round_opt(
                cand_summary["wall_seconds"] / base_summary["wall_seconds"]
                if base_summary["wall_seconds"] > 0
                else None,
                4,
            ),
        },
        "ok_transitions": _transition_counts(tasks, base_res, cand_res, "ok"),
        "match_strict_transitions": _transition_counts(tasks, base_res, cand_res, "match_strict"),
        "match_loose_transitions": _transition_counts(tasks, base_res, cand_res, "match_loose"),
        "sg_match_transitions": _transition_counts(tasks, base_res, cand_res, "sg_match"),
        "paired_both_ok": {
            "shared_ok_count": len(eform_shifts),
            "bit_identical_eform_count": bit_identical,
            "abs_eform_shift_ev_per_atom": {
                "mean": _round_opt(statistics.mean(eform_shifts) if eform_shifts else None),
                "median": _round_opt(statistics.median(eform_shifts) if eform_shifts else None),
                "p90": _round_opt(_percentile(eform_shifts, 90.0)),
                "p95": _round_opt(_percentile(eform_shifts, 95.0)),
                "max": _round_opt(max(eform_shifts) if eform_shifts else None),
            },
            "abs_err_delta_ev_per_atom": {
                "mean": _round_opt(statistics.mean(abs_err_deltas) if abs_err_deltas else None),
                "median": _round_opt(
                    statistics.median(abs_err_deltas) if abs_err_deltas else None
                ),
                "improved_gt_1mev_count": sum(1 for d in abs_err_deltas if d < -1e-3),
                "worsened_gt_1mev_count": sum(1 for d in abs_err_deltas if d > 1e-3),
            },
            "seconds_delta": {
                "mean_s": _round_opt(statistics.mean(sec_deltas) if sec_deltas else None, 4),
                "median_s": _round_opt(statistics.median(sec_deltas) if sec_deltas else None, 4),
                "p90_s": _round_opt(_percentile(sec_deltas, 90.0), 4),
                "p95_s": _round_opt(_percentile(sec_deltas, 95.0), 4),
            },
        },
        "gfnff_incomplete_cases": gfnff_rows[:25],
    }


def _fmt_bool_int(val: bool | None) -> str:
    """Format an optional boolean as ``'1'``, ``'0'``, or ``''`` for CSV output."""
    if val is None:
        return ""
    return "1" if val else "0"


def _write_per_structure_csv(
    out_csv: Path,
    tasks: list[dict[str, Any]],
    pass_order: list[str],
    results_by_pass: dict[str, list[dict[str, Any]]],
) -> None:
    """Write wide-format ``per_structure_metrics.csv`` with lossless float64 ``eform``."""
    meta_cols = [
        "row_index",
        "material_id",
        "formula",
        "n_atoms",
        "crystal_system",
        "ref_sg",
        "dft_eform",
        "dft_band_gap",
    ]
    pass_suffixes = [
        "ok",
        "eform",
        "abs_err",
        "match_strict",
        "match_loose",
        "struct_valid",
        "pred_sg",
        "sg_match",
        "roundtrip_canonical_match",
        "preoptimized",
        "retry",
        "relax_steps",
        "gfnff_incomplete",
        "seconds",
        "error_type",
    ]
    fieldnames = list(meta_cols)
    for pname in pass_order:
        fieldnames.extend(f"{pname}_{sfx}" for sfx in pass_suffixes)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for idx, task in enumerate(tasks):
            row_dict: dict[str, Any] = {
                "row_index": task["row_index"],
                "material_id": task["material_id"],
                "formula": task["formula"],
                "n_atoms": task["n_atoms"],
                "crystal_system": task["crystal_system"],
                "ref_sg": task["ref_sg"] if task["ref_sg"] is not None else "",
                "dft_eform": f"{task['dft_eform']:.17g}",
                "dft_band_gap": f"{task['dft_band_gap']:.8g}",
            }
            for pname in pass_order:
                r = results_by_pass[pname][idx]
                row_dict[f"{pname}_ok"] = "1" if r["ok"] else "0"
                row_dict[f"{pname}_eform"] = (
                    f"{r['eform']:.17g}" if r["eform"] is not None else ""
                )
                row_dict[f"{pname}_abs_err"] = (
                    f"{r['abs_err']:.8g}" if r["abs_err"] is not None else ""
                )
                row_dict[f"{pname}_match_strict"] = _fmt_bool_int(r["match_strict"])
                row_dict[f"{pname}_match_loose"] = _fmt_bool_int(r["match_loose"])
                row_dict[f"{pname}_struct_valid"] = _fmt_bool_int(r["struct_valid"])
                row_dict[f"{pname}_pred_sg"] = r["pred_sg"] if r["pred_sg"] is not None else ""
                row_dict[f"{pname}_sg_match"] = _fmt_bool_int(r["sg_match"])
                row_dict[f"{pname}_roundtrip_canonical_match"] = _fmt_bool_int(
                    r["roundtrip_canonical_match"]
                )
                row_dict[f"{pname}_preoptimized"] = "1" if r["preoptimized"] else "0"
                row_dict[f"{pname}_retry"] = r["retry"]
                row_dict[f"{pname}_relax_steps"] = r["relax_steps"]
                row_dict[f"{pname}_gfnff_incomplete"] = "1" if r["gfnff_incomplete"] else "0"
                row_dict[f"{pname}_seconds"] = f"{r['seconds']:.4f}"
                row_dict[f"{pname}_error_type"] = r["error_type"]
            writer.writerow(row_dict)


def _run_single_pass(
    spec: PassSpec,
    tasks: list[dict[str, Any]],
    chem_pot: dict[str, float],
    workers: int,
) -> tuple[list[dict[str, Any]], float]:
    """Execute one full benchmark pass across a spawned ``ProcessPoolExecutor``."""
    ctx = mp.get_context("spawn")
    n_tasks = len(tasks)
    ordered_results: list[dict[str, Any] | None] = [None] * n_tasks
    t_pass = time.perf_counter()

    print(
        f"[{spec.name}] Starting {n_tasks} structures across {workers} spawned workers "
        f"(relax_model={spec.relax_model!r}, lj_mixing={spec.lj_mixing!r}, "
        f"robust={spec.use_robust})...",
        flush=True,
    )
    completed = 0
    step_report = max(1, min(250, max(1, n_tasks // 8)))

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=ctx,
        initializer=_init_worker,
        initargs=(spec, chem_pot),
    ) as pool:
        futures = [pool.submit(_evaluate_task, task) for task in tasks]
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            ordered_results[int(res["row_index"])] = res
            completed += 1
            if completed % step_report == 0 or completed == n_tasks:
                elapsed = time.perf_counter() - t_pass
                rate = completed / elapsed if elapsed > 0 else 0.0
                print(
                    f"  [{spec.name}] {completed:4d}/{n_tasks} "
                    f"({elapsed:6.1f}s, {rate:5.2f} struct/s)",
                    flush=True,
                )

    wall_s = time.perf_counter() - t_pass
    final_results: list[dict[str, Any]] = [r for r in ordered_results if r is not None]
    return final_results, wall_s


def _collect_env_metadata(relax_model: str, workers: int) -> dict[str, Any]:
    """Gather git commit, package versions, and relaxer backend metadata."""
    import ase
    import nequip
    import numpy as np
    import pymatgen.core
    import scipy
    import torch

    import slices
    from slices.relax_backends import make_relaxer

    git_commit = "unknown"
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        git_commit = proc.stdout.strip()

    relaxer, resolved_name = make_relaxer(relax_model)
    device = getattr(relaxer, "device", "none") if relaxer is not None else "none"
    description = getattr(relaxer, "description", "") if relaxer is not None else ""

    return {
        "git_commit": git_commit,
        "slices_version": getattr(slices, "__version__", "4.0.2"),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "nequip_version": nequip.__version__,
        "pymatgen_version": getattr(pymatgen.core, "__version__", "unknown"),
        "ase_version": ase.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "cpu_count": os.cpu_count(),
        "workers": workers,
        "omp_num_threads": os.environ.get("OMP_NUM_THREADS", ""),
        "slices_torch_threads": os.environ.get("SLICES_TORCH_THREADS", ""),
        "pythonhashseed": os.environ.get("PYTHONHASHSEED", ""),
        "pythondontwritebytecode": os.environ.get("PYTHONDONTWRITEBYTECODE", ""),
        "resolved_relax_model": resolved_name,
        "device": device,
        "relaxer_description": description,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, run requested MP-20 passes, and write CSV/JSON outputs.

    Args:
        argv: Optional command-line argument list.

    Returns:
        Process exit status (``0`` on success).
    """
    parser = argparse.ArgumentParser(
        description="Run the 2,383-structure MP-20 SLICES v4.0.2 baseline benchmark."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="input MP-20 CSV path")
    parser.add_argument(
        "--chem-pot",
        type=Path,
        default=DEFAULT_CHEM_POT,
        help="elemental chemical potentials JSON path",
    )
    parser.add_argument(
        "--mp20-dir",
        type=Path,
        default=DEFAULT_MP20_DIR,
        help="directory containing MP-20 train/val/test.csv reference CIFs",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="output directory for summary.json and per_structure_metrics.csv",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=24,
        help="number of spawned worker processes (default: 24)",
    )
    parser.add_argument(
        "--passes",
        nargs="+",
        choices=PASS_NAMES,
        default=list(PASS_NAMES),
        help="ordered benchmark passes to execute (default: default lorentz robust)",
    )
    parser.add_argument(
        "--relax-model",
        default="auto",
        help="force-field model identifier (default: auto -> nequip-s+l)",
    )
    parser.add_argument(
        "--robust-starts",
        type=int,
        default=3,
        help="multi-start count for the robust pass (default: 3)",
    )
    parser.add_argument(
        "--robust-seed",
        type=int,
        default=0,
        help="deterministic RNG seed for the robust pass (default: 0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="optional row limit for quick validation runs (default: all 2,383 rows)",
    )
    args = parser.parse_args(argv)

    _configure_worker_env()
    t_suite = time.perf_counter()

    with args.chem_pot.open(encoding="utf-8") as fh:
        chem_pot: dict[str, float] = json.load(fh)

    env_meta = _collect_env_metadata(args.relax_model, args.workers)
    resolved_model = env_meta["resolved_relax_model"]

    print("Preparing MP-20 benchmark tasks and joining reference CIFs...", flush=True)
    tasks = _prepare_tasks(args.csv, args.mp20_dir, limit=args.limit)
    cif_matched = sum(1 for t in tasks if t["ori_poscar"] is not None)
    le20_count = sum(1 for t in tasks if int(t["n_atoms"]) <= 20)
    print(
        f"Loaded {len(tasks)} structures (<=20 atoms: {le20_count}, "
        f"reference CIFs matched: {cif_matched}/{len(tasks)})\n",
        flush=True,
    )

    spec_registry: dict[str, PassSpec] = {
        "default": PassSpec(
            name="default",
            relax_model=args.relax_model,
            lj_mixing="legacy",
            use_robust=False,
        ),
        "lorentz": PassSpec(
            name="lorentz",
            relax_model=args.relax_model,
            lj_mixing="lorentz",
            use_robust=False,
        ),
        "robust": PassSpec(
            name="robust",
            relax_model=args.relax_model,
            lj_mixing="legacy",
            use_robust=True,
            n_starts=args.robust_starts,
            seed=args.robust_seed,
        ),
    }

    pass_order: list[str] = list(dict.fromkeys(args.passes))
    results_by_pass: dict[str, list[dict[str, Any]]] = {}
    pass_summaries: dict[str, dict[str, Any]] = {}

    for pname in pass_order:
        spec = spec_registry[pname]
        res_list, wall_s = _run_single_pass(spec, tasks, chem_pot, args.workers)
        results_by_pass[pname] = res_list
        p_sum = _summarize_pass(spec, tasks, res_list, wall_s, resolved_model)
        pass_summaries[pname] = p_sum
        agg = p_sum["all_structures"]
        ef_agg = agg["eform_error_ev_per_atom"]
        print(
            f"[{pname}] DONE in {wall_s:.1f}s | ok {agg['ok_count']}/{agg['total_count']} "
            f"| strict {agg['match_strict_count']}/{agg['cif_matched_count']} "
            f"({(agg['match_strict_rate_all'] or 0.0) * 100:.2f}%) "
            f"| loose {agg['match_loose_count']}/{agg['cif_matched_count']} "
            f"({(agg['match_loose_rate_all'] or 0.0) * 100:.2f}%) "
            f"| |eform-DFT| MAE {ef_agg['mae']} med {ef_agg['median_ae']} eV/atom\n",
            flush=True,
        )

    paired: dict[str, Any] = {}
    if "default" in results_by_pass:
        for cand_name in ("lorentz", "robust"):
            if cand_name in results_by_pass:
                paired[f"{cand_name}_vs_default"] = _paired_comparison(
                    tasks=tasks,
                    base_summary=pass_summaries["default"],
                    cand_summary=pass_summaries[cand_name],
                    base_res=results_by_pass["default"],
                    cand_res=results_by_pass[cand_name],
                )

    total_wall_s = time.perf_counter() - t_suite
    try:
        rel_csv = str(args.csv.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel_csv = str(args.csv)
    try:
        rel_pot = str(args.chem_pot.resolve().relative_to(REPO_ROOT))
    except ValueError:
        rel_pot = str(args.chem_pot)

    summary_payload: dict[str, Any] = {
        "benchmark_metadata": {
            "baseline_tag": "v4.0.2-baseline",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "dataset_csv": rel_csv,
            "chem_pot_json": rel_pot,
            "reference_cif_source": "data/mp20/{train,val,test}.csv",
            "total_rows": len(tasks),
            "rows_le_20_atoms": le20_count,
            "rows_gt_20_atoms": len(tasks) - le20_count,
            "cif_matched_rows": cif_matched,
            "total_wall_seconds": round(total_wall_s, 3),
            "environment": env_meta,
        },
        "passes": pass_summaries,
        "paired_comparisons": paired,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / "per_structure_metrics.csv"
    out_json = args.out_dir / "summary.json"

    _write_per_structure_csv(out_csv, tasks, pass_order, results_by_pass)
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)
        fh.write("\n")

    print(
        f"Wrote {out_csv} ({out_csv.stat().st_size} bytes) and "
        f"{out_json} ({out_json.stat().st_size} bytes) in {total_wall_s:.1f}s.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
