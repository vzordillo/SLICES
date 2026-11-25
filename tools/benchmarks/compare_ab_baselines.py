#!/usr/bin/env python3
r"""Paired statistical A/B comparison CLI for SLICES MP-20 benchmark archives.

Compares a candidate benchmark archive (``per_structure_metrics.csv`` and
``summary.json``, e.g., ``benchmark/v4_1_experimental``) against a locked
control archive (e.g., ``benchmark/v4_0_2_baseline``) and optionally evaluates
``SLICES.check_SLICES`` validity-rate and Smith Normal Form rescue/rejection
counts across the repository's conditioned-RNN (``cRNN``) SLICES corpora.

Statistical methods:
    * Paired binary outcomes (``ok``, ``match_strict``, ``match_loose``,
      ``sg_match``, ``struct_valid``, ``roundtrip_canonical_match``,
      ``|eform - DFT| <= 0.05`` / ``0.10 eV/atom``): exact two-sided McNemar
      test via ``scipy.stats.binomtest(gained, gained + lost, p=0.5)``.
    * Paired continuous formation-energy residuals on shared ``ok`` crystals:
      two-sided Wilcoxon signed-rank test via ``scipy.stats.wilcoxon``.
    * Per-structure latency speedups across all shared ``ok`` crystals and
      stratified across all seven crystallographic systems.

Example::

    python tools/benchmarks/compare_ab_baselines.py \\
        --candidate-dir benchmark/v4_1_experimental \\
        --baseline-dir benchmark/v4_0_2_baseline \\
        --out benchmark/v4_1_experimental/ab_vs_v4_0_2.json
"""

from __future__ import annotations

import argparse
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
import sys
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from collections.abc import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_CANDIDATE_DIR = REPO_ROOT / "benchmark" / "v4_1_experimental"
DEFAULT_BASELINE_DIR = REPO_ROOT / "benchmark" / "v4_0_2_baseline"
DEFAULT_CRNN_DIR = REPO_ROOT / "benchmark" / "Validity_rate_ucRNN__Success_rate_cRNN"

BOOLEAN_METRICS: tuple[str, ...] = (
    "ok",
    "match_strict",
    "match_loose",
    "sg_match",
    "struct_valid",
    "roundtrip_canonical_match",
)

COMPARISON_SPECS: tuple[tuple[str, str, str], ...] = (
    ("v41_default_vs_v402_default", "default", "default"),
    ("v41_lorentz_vs_v402_lorentz", "lorentz", "lorentz"),
    ("v41_lorentz_vs_v402_default", "lorentz", "default"),
    ("v41_robust_vs_v402_robust", "robust", "robust"),
    ("v41_default_vs_v402_robust", "default", "robust"),
)

CRYSTAL_SYSTEM_ORDER: tuple[str, ...] = (
    "cubic",
    "hexagonal",
    "trigonal",
    "tetragonal",
    "orthorhombic",
    "monoclinic",
    "triclinic",
)


def _round_opt(val: float | None, digits: int = 6) -> float | None:
    """Round an optional finite float to ``digits`` decimal places."""
    if val is None or not math.isfinite(val):
        return None
    return round(float(val), digits)


def _rel_path_str(path: Path) -> str:
    """Format ``path`` relative to ``REPO_ROOT`` when possible for portability."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.name)


def _parse_bool_cell(raw: str | None) -> bool:
    """Return ``True`` strictly when a CSV boolean cell equals ``'1'``."""
    return raw == "1"


def _parse_float_cell(raw: str | None) -> float | None:
    """Parse an optional float cell from ``per_structure_metrics.csv``."""
    if raw is None or raw == "":
        return None
    return float(raw)


def _parse_int_cell(raw: str | None) -> int | None:
    """Parse an optional integer cell from ``per_structure_metrics.csv``."""
    if raw is None or raw == "":
        return None
    return int(raw)


def _percentile(values: list[float], q: float) -> float | None:
    """Compute linear-interpolated percentile ``q`` in ``[0, 100]``."""
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _mcnemar_exact_pvalue(gained: int, lost: int) -> float:
    """Compute the exact two-sided McNemar p-value via ``scipy.stats.binomtest``."""
    discordant = int(gained) + int(lost)
    if discordant == 0:
        return 1.0
    return float(stats.binomtest(int(gained), n=discordant, p=0.5, alternative="two-sided").pvalue)


def _wilcoxon_two_sided_pvalue(diffs: list[float]) -> float | None:
    """Compute the two-sided Wilcoxon signed-rank p-value over paired differences."""
    if not diffs:
        return None
    arr = np.asarray(diffs, dtype=float)
    non_zero = arr[arr != 0.0]
    if non_zero.size == 0:
        return 1.0
    res = stats.wilcoxon(non_zero, zero_method="wilcox", alternative="two-sided")
    return float(res.pvalue)


def _load_csv_by_index(csv_path: Path) -> list[dict[str, str]]:
    """Load ``per_structure_metrics.csv`` ordered by ``row_index``."""
    with csv_path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: int(r["row_index"]))
    return rows


def _paired_boolean_transition(
    base_rows: list[dict[str, str]],
    cand_rows: list[dict[str, str]],
    base_col: str,
    cand_col: str,
    sample_cap: int = 25,
) -> dict[str, Any]:
    """Compute paired ``0/1`` transition counts and exact McNemar p-value."""
    both_true = 0
    both_false = 0
    gained_ids: list[str] = []
    lost_ids: list[str] = []

    for rb, rc in zip(base_rows, cand_rows, strict=True):
        vb = _parse_bool_cell(rb.get(base_col))
        vc = _parse_bool_cell(rc.get(cand_col))
        mid = rb.get("material_id") or f"row_{rb['row_index']}"
        if vb and vc:
            both_true += 1
        elif (not vb) and vc:
            gained_ids.append(mid)
        elif vb and (not vc):
            lost_ids.append(mid)
        else:
            both_false += 1

    n_total = len(base_rows)
    base_true = both_true + len(lost_ids)
    cand_true = both_true + len(gained_ids)
    pval = _mcnemar_exact_pvalue(len(gained_ids), len(lost_ids))

    return {
        "base_true_count": base_true,
        "cand_true_count": cand_true,
        "base_rate_all": _round_opt(base_true / n_total if n_total else None),
        "cand_rate_all": _round_opt(cand_true / n_total if n_total else None),
        "both_true": both_true,
        "gained_count": len(gained_ids),
        "lost_count": len(lost_ids),
        "both_false": both_false,
        "net_delta": len(gained_ids) - len(lost_ids),
        "rate_delta_pp": _round_opt(
            ((cand_true - base_true) / n_total) * 100.0 if n_total else None,
            4,
        ),
        "mcnemar_two_sided_p": _round_opt(pval, 8),
        "gained_ids_sample": gained_ids[:sample_cap],
        "lost_ids_sample": lost_ids[:sample_cap],
    }


def _paired_threshold_transition(
    pairs: list[tuple[str, bool, bool]],
    sample_cap: int = 20,
) -> dict[str, Any]:
    """Compute paired boolean transitions from pre-evaluated ``(id, base_ok, cand_ok)``."""
    both_true = 0
    both_false = 0
    gained_ids: list[str] = []
    lost_ids: list[str] = []
    for mid, vb, vc in pairs:
        if vb and vc:
            both_true += 1
        elif (not vb) and vc:
            gained_ids.append(mid)
        elif vb and (not vc):
            lost_ids.append(mid)
        else:
            both_false += 1
    n_total = len(pairs)
    base_true = both_true + len(lost_ids)
    cand_true = both_true + len(gained_ids)
    return {
        "count": n_total,
        "base_true_count": base_true,
        "cand_true_count": cand_true,
        "both_true": both_true,
        "gained_count": len(gained_ids),
        "lost_count": len(lost_ids),
        "both_false": both_false,
        "net_delta": len(gained_ids) - len(lost_ids),
        "mcnemar_two_sided_p": _round_opt(_mcnemar_exact_pvalue(len(gained_ids), len(lost_ids)), 8),
        "gained_ids_sample": gained_ids[:sample_cap],
        "lost_ids_sample": lost_ids[:sample_cap],
    }


def _latency_block(base_secs: list[float], cand_secs: list[float]) -> dict[str, Any]:
    """Summarize paired latency statistics, percentage changes, and speedup factors."""
    if not base_secs or not cand_secs:
        return {"count": 0}
    b_mean = statistics.mean(base_secs)
    c_mean = statistics.mean(cand_secs)
    b_med = statistics.median(base_secs)
    c_med = statistics.median(cand_secs)
    b_sum = sum(base_secs)
    c_sum = sum(cand_secs)
    deltas = [c - b for b, c in zip(base_secs, cand_secs, strict=True)]
    ratios = [c / b for b, c in zip(base_secs, cand_secs, strict=True) if b > 0.0]

    return {
        "count": len(base_secs),
        "base_mean_s": _round_opt(b_mean, 4),
        "cand_mean_s": _round_opt(c_mean, 4),
        "mean_delta_s": _round_opt(c_mean - b_mean, 4),
        "mean_pct_change": _round_opt(
            ((c_mean - b_mean) / b_mean) * 100.0 if b_mean > 0 else None,
            3,
        ),
        "mean_speedup_x": _round_opt(b_mean / c_mean if c_mean > 0 else None, 4),
        "base_median_s": _round_opt(b_med, 4),
        "cand_median_s": _round_opt(c_med, 4),
        "median_delta_s": _round_opt(c_med - b_med, 4),
        "median_pct_change": _round_opt(
            ((c_med - b_med) / b_med) * 100.0 if b_med > 0 else None,
            3,
        ),
        "median_speedup_x": _round_opt(b_med / c_med if c_med > 0 else None, 4),
        "paired_delta_median_s": _round_opt(statistics.median(deltas), 4),
        "paired_ratio_median": _round_opt(statistics.median(ratios) if ratios else None, 4),
        "faster_in_cand_count": sum(1 for d in deltas if d < 0.0),
        "slower_in_cand_count": sum(1 for d in deltas if d > 0.0),
        "base_sum_cpu_s": _round_opt(b_sum, 2),
        "cand_sum_cpu_s": _round_opt(c_sum, 2),
        "sum_cpu_delta_s": _round_opt(c_sum - b_sum, 2),
        "sum_cpu_pct_change": _round_opt(
            ((c_sum - b_sum) / b_sum) * 100.0 if b_sum > 0 else None,
            3,
        ),
        "sum_cpu_speedup_x": _round_opt(b_sum / c_sum if c_sum > 0 else None, 4),
    }


def _compare_pass_pair(
    base_rows: list[dict[str, str]],
    cand_rows: list[dict[str, str]],
    base_pass_summary: dict[str, Any],
    cand_pass_summary: dict[str, Any],
    base_pass: str,
    cand_pass: str,
) -> dict[str, Any]:
    """Compute comprehensive paired A/B metrics between ``cand_pass`` and ``base_pass``."""
    transitions: dict[str, Any] = {}
    for metric in BOOLEAN_METRICS:
        transitions[metric] = _paired_boolean_transition(
            base_rows,
            cand_rows,
            f"{base_pass}_{metric}",
            f"{cand_pass}_{metric}",
        )

    all_b_secs = [float(r[f"{base_pass}_seconds"]) for r in base_rows]
    all_c_secs = [float(r[f"{cand_pass}_seconds"]) for r in cand_rows]

    shared_b_secs: list[float] = []
    shared_c_secs: list[float] = []
    cs_secs: dict[str, tuple[list[float], list[float]]] = {
        cs: ([], []) for cs in CRYSTAL_SYSTEM_ORDER
    }

    base_abs_errs_shared: list[float] = []
    cand_abs_errs_shared: list[float] = []
    abs_err_deltas: list[float] = []
    eform_abs_shifts: list[float] = []
    eform_signed_shifts: list[float] = []
    bit_identical_count = 0
    within_1e6_count = 0
    max_shift_record: dict[str, Any] | None = None

    shared_005_pairs: list[tuple[str, bool, bool]] = []
    shared_010_pairs: list[tuple[str, bool, bool]] = []
    all_005_pairs: list[tuple[str, bool, bool]] = []
    all_010_pairs: list[tuple[str, bool, bool]] = []

    for rb, rc in zip(base_rows, cand_rows, strict=True):
        mid = rb.get("material_id") or f"row_{rb['row_index']}"
        b_ok = _parse_bool_cell(rb.get(f"{base_pass}_ok"))
        c_ok = _parse_bool_cell(rc.get(f"{cand_pass}_ok"))
        b_ef = _parse_float_cell(rb.get(f"{base_pass}_eform"))
        c_ef = _parse_float_cell(rc.get(f"{cand_pass}_eform"))
        dft_ef = float(rb["dft_eform"])

        b_err = abs(b_ef - dft_ef) if (b_ok and b_ef is not None) else None
        c_err = abs(c_ef - dft_ef) if (c_ok and c_ef is not None) else None

        all_005_pairs.append(
            (
                mid,
                bool(b_err is not None and b_err <= 0.05),
                bool(c_err is not None and c_err <= 0.05),
            )
        )
        all_010_pairs.append(
            (
                mid,
                bool(b_err is not None and b_err <= 0.10),
                bool(c_err is not None and c_err <= 0.10),
            )
        )

        if (
            b_ok
            and c_ok
            and b_ef is not None
            and c_ef is not None
            and b_err is not None
            and c_err is not None
        ):
            bs = float(rb[f"{base_pass}_seconds"])
            cs_val = float(rc[f"{cand_pass}_seconds"])
            shared_b_secs.append(bs)
            shared_c_secs.append(cs_val)
            cs_name = rb.get("crystal_system", "")
            if cs_name not in cs_secs:
                cs_secs[cs_name] = ([], [])
            cs_secs[cs_name][0].append(bs)
            cs_secs[cs_name][1].append(cs_val)

            base_abs_errs_shared.append(b_err)
            cand_abs_errs_shared.append(c_err)
            abs_err_deltas.append(c_err - b_err)

            shift = abs(c_ef - b_ef)
            eform_abs_shifts.append(shift)
            eform_signed_shifts.append(c_ef - b_ef)
            if shift == 0.0:
                bit_identical_count += 1
            if shift <= 1e-6:
                within_1e6_count += 1
            if max_shift_record is None or shift > float(max_shift_record["abs_eform_shift"]):
                max_shift_record = {
                    "row_index": int(rb["row_index"]),
                    "material_id": mid,
                    "formula": rb["formula"],
                    "crystal_system": rb["crystal_system"],
                    "base_eform": _round_opt(b_ef),
                    "cand_eform": _round_opt(c_ef),
                    "abs_eform_shift": _round_opt(shift),
                    "base_abs_err": _round_opt(b_err),
                    "cand_abs_err": _round_opt(c_err),
                }

            shared_005_pairs.append((mid, b_err <= 0.05, c_err <= 0.05))
            shared_010_pairs.append((mid, b_err <= 0.10, c_err <= 0.10))

    b_wall = float(base_pass_summary["wall_seconds"])
    c_wall = float(cand_pass_summary["wall_seconds"])
    b_ef_agg = base_pass_summary["all_structures"]["eform_error_ev_per_atom"]
    c_ef_agg = cand_pass_summary["all_structures"]["eform_error_ev_per_atom"]

    shared_b_rmse = (
        math.sqrt(sum(e * e for e in base_abs_errs_shared) / len(base_abs_errs_shared))
        if base_abs_errs_shared
        else None
    )
    shared_c_rmse = (
        math.sqrt(sum(e * e for e in cand_abs_errs_shared) / len(cand_abs_errs_shared))
        if cand_abs_errs_shared
        else None
    )
    shared_b_mae = statistics.mean(base_abs_errs_shared) if base_abs_errs_shared else None
    shared_c_mae = statistics.mean(cand_abs_errs_shared) if cand_abs_errs_shared else None
    shared_b_med = statistics.median(base_abs_errs_shared) if base_abs_errs_shared else None
    shared_c_med = statistics.median(cand_abs_errs_shared) if cand_abs_errs_shared else None

    latency_by_cs: dict[str, Any] = {}
    for cs_name in CRYSTAL_SYSTEM_ORDER:
        b_list, c_list = cs_secs.get(cs_name, ([], []))
        if b_list:
            latency_by_cs[cs_name] = _latency_block(b_list, c_list)

    return {
        "candidate_pass": f"v4.1:{cand_pass}",
        "baseline_pass": f"v4.0.2:{base_pass}",
        "paired_boolean_transitions": transitions,
        "latency": {
            "wall_clock": {
                "base_wall_s": _round_opt(b_wall, 3),
                "cand_wall_s": _round_opt(c_wall, 3),
                "wall_delta_s": _round_opt(c_wall - b_wall, 3),
                "wall_pct_change": _round_opt(
                    ((c_wall - b_wall) / b_wall) * 100.0 if b_wall > 0 else None,
                    3,
                ),
                "wall_speedup_x": _round_opt(b_wall / c_wall if c_wall > 0 else None, 4),
            },
            "all_2383_structures": _latency_block(all_b_secs, all_c_secs),
            "shared_ok_structures": _latency_block(shared_b_secs, shared_c_secs),
            "shared_ok_by_crystal_system": latency_by_cs,
        },
        "eform_accuracy_ev_per_atom": {
            "aggregate_all_ok": {
                "base_ok_count": b_ef_agg["count"],
                "cand_ok_count": c_ef_agg["count"],
                "base_mae": b_ef_agg["mae"],
                "cand_mae": c_ef_agg["mae"],
                "delta_mae": _round_opt(float(c_ef_agg["mae"]) - float(b_ef_agg["mae"])),
                "base_median_ae": b_ef_agg["median_ae"],
                "cand_median_ae": c_ef_agg["median_ae"],
                "delta_median_ae": _round_opt(
                    float(c_ef_agg["median_ae"]) - float(b_ef_agg["median_ae"])
                ),
                "base_rmse": b_ef_agg["rmse"],
                "cand_rmse": c_ef_agg["rmse"],
                "delta_rmse": _round_opt(float(c_ef_agg["rmse"]) - float(b_ef_agg["rmse"])),
                "within_0_05_ev_all_rows": _paired_threshold_transition(all_005_pairs),
                "within_0_10_ev_all_rows": _paired_threshold_transition(all_010_pairs),
            },
            "paired_shared_ok": {
                "shared_ok_count": len(base_abs_errs_shared),
                "base_mae": _round_opt(shared_b_mae),
                "cand_mae": _round_opt(shared_c_mae),
                "delta_mae": _round_opt(
                    (shared_c_mae - shared_b_mae)
                    if (shared_c_mae is not None and shared_b_mae is not None)
                    else None
                ),
                "base_median_ae": _round_opt(shared_b_med),
                "cand_median_ae": _round_opt(shared_c_med),
                "delta_median_ae": _round_opt(
                    (shared_c_med - shared_b_med)
                    if (shared_c_med is not None and shared_b_med is not None)
                    else None
                ),
                "base_rmse": _round_opt(shared_b_rmse),
                "cand_rmse": _round_opt(shared_c_rmse),
                "delta_rmse": _round_opt(
                    (shared_c_rmse - shared_b_rmse)
                    if (shared_c_rmse is not None and shared_b_rmse is not None)
                    else None
                ),
                "bit_identical_eform_count": bit_identical_count,
                "within_1e_6_ev_shift_count": within_1e6_count,
                "abs_eform_shift": {
                    "mean": _round_opt(
                        statistics.mean(eform_abs_shifts) if eform_abs_shifts else None
                    ),
                    "median": _round_opt(
                        statistics.median(eform_abs_shifts) if eform_abs_shifts else None
                    ),
                    "p90": _round_opt(_percentile(eform_abs_shifts, 90.0)),
                    "p95": _round_opt(_percentile(eform_abs_shifts, 95.0)),
                    "p99": _round_opt(_percentile(eform_abs_shifts, 99.0)),
                    "max": _round_opt(max(eform_abs_shifts) if eform_abs_shifts else None),
                    "max_crystal": max_shift_record,
                },
                "abs_err_delta": {
                    "mean": _round_opt(statistics.mean(abs_err_deltas) if abs_err_deltas else None),
                    "median": _round_opt(
                        statistics.median(abs_err_deltas) if abs_err_deltas else None
                    ),
                    "improved_gt_1mev_count": sum(1 for d in abs_err_deltas if d < -1e-3),
                    "worsened_gt_1mev_count": sum(1 for d in abs_err_deltas if d > 1e-3),
                    "wilcoxon_abs_err_two_sided_p": _round_opt(
                        _wilcoxon_two_sided_pvalue(abs_err_deltas),
                        8,
                    ),
                    "wilcoxon_signed_eform_two_sided_p": _round_opt(
                        _wilcoxon_two_sided_pvalue(eform_signed_shifts),
                        8,
                    ),
                },
                "within_0_05_ev_shared_ok": _paired_threshold_transition(shared_005_pairs),
                "within_0_10_ev_shared_ok": _paired_threshold_transition(shared_010_pairs),
            },
        },
    }


def _build_crystal_level_reports(
    base_rows: list[dict[str, str]],
    cand_rows: list[dict[str, str]],
) -> dict[str, Any]:
    """Build detailed crystal-level reports for rescued, gfnff, and match-flip cases."""
    rescued_snf: list[dict[str, Any]] = []
    remaining_failures: list[dict[str, Any]] = []

    for rb, rc in zip(base_rows, cand_rows, strict=True):
        b_ok = _parse_bool_cell(rb.get("default_ok"))
        c_ok = _parse_bool_cell(rc.get("default_ok"))
        if not b_ok:
            c_ef = _parse_float_cell(rc.get("default_eform"))
            b_rob_ef = _parse_float_cell(rb.get("robust_eform"))
            entry: dict[str, Any] = {
                "row_index": int(rb["row_index"]),
                "material_id": rb["material_id"],
                "formula": rb["formula"],
                "n_atoms": int(rb["n_atoms"]),
                "crystal_system": rb["crystal_system"],
                "ref_sg": _parse_int_cell(rb["ref_sg"]),
                "dft_eform": _round_opt(float(rb["dft_eform"])),
                "v402_default_error": rb["default_error_type"],
                "v41_default_ok": c_ok,
                "v41_default_error": rc["default_error_type"],
                "v41_default_eform": _round_opt(c_ef),
                "v41_default_abs_err": _round_opt(_parse_float_cell(rc.get("default_abs_err"))),
                "v41_default_match_strict": _parse_bool_cell(rc.get("default_match_strict")),
                "v41_default_match_loose": _parse_bool_cell(rc.get("default_match_loose")),
                "v41_default_struct_valid": _parse_bool_cell(rc.get("default_struct_valid")),
                "v41_default_pred_sg": _parse_int_cell(rc.get("default_pred_sg")),
                "v41_default_sg_match": _parse_bool_cell(rc.get("default_sg_match")),
                "v41_default_relax_steps": _parse_int_cell(rc.get("default_relax_steps")),
                "v41_default_seconds": _round_opt(_parse_float_cell(rc.get("default_seconds")), 4),
                "v402_robust_eform": _round_opt(b_rob_ef),
                "abs_eform_diff_vs_v402_robust": _round_opt(
                    abs(c_ef - b_rob_ef) if (c_ef is not None and b_rob_ef is not None) else None
                ),
            }
            if c_ok:
                rescued_snf.append(entry)
            else:
                remaining_failures.append(entry)

    gfnff_cases: list[dict[str, Any]] = []
    for rb, rc in zip(base_rows, cand_rows, strict=True):
        if _parse_bool_cell(rb.get("default_gfnff_incomplete")) or _parse_bool_cell(
            rc.get("default_gfnff_incomplete")
        ):
            pass_comparison: dict[str, Any] = {}
            for pname in ("default", "lorentz", "robust"):
                b_ef = _parse_float_cell(rb.get(f"{pname}_eform"))
                c_ef = _parse_float_cell(rc.get(f"{pname}_eform"))
                b_err = _parse_float_cell(rb.get(f"{pname}_abs_err"))
                c_err = _parse_float_cell(rc.get(f"{pname}_abs_err"))
                pass_comparison[pname] = {
                    "v402_eform": _round_opt(b_ef),
                    "v41_eform": _round_opt(c_ef),
                    "eform_delta": _round_opt(
                        (c_ef - b_ef) if (c_ef is not None and b_ef is not None) else None
                    ),
                    "v402_abs_err": _round_opt(b_err),
                    "v41_abs_err": _round_opt(c_err),
                    "abs_err_delta": _round_opt(
                        (c_err - b_err) if (c_err is not None and b_err is not None) else None
                    ),
                    "v402_match_strict": _parse_bool_cell(rb.get(f"{pname}_match_strict")),
                    "v41_match_strict": _parse_bool_cell(rc.get(f"{pname}_match_strict")),
                    "v402_match_loose": _parse_bool_cell(rb.get(f"{pname}_match_loose")),
                    "v41_match_loose": _parse_bool_cell(rc.get(f"{pname}_match_loose")),
                    "v402_pred_sg": _parse_int_cell(rb.get(f"{pname}_pred_sg")),
                    "v41_pred_sg": _parse_int_cell(rc.get(f"{pname}_pred_sg")),
                    "v402_preoptimized": _parse_bool_cell(rb.get(f"{pname}_preoptimized")),
                    "v41_preoptimized": _parse_bool_cell(rc.get(f"{pname}_preoptimized")),
                    "v402_relax_steps": _parse_int_cell(rb.get(f"{pname}_relax_steps")),
                    "v41_relax_steps": _parse_int_cell(rc.get(f"{pname}_relax_steps")),
                }
            gfnff_cases.append(
                {
                    "row_index": int(rb["row_index"]),
                    "material_id": rb["material_id"],
                    "formula": rb["formula"],
                    "n_atoms": int(rb["n_atoms"]),
                    "crystal_system": rb["crystal_system"],
                    "ref_sg": _parse_int_cell(rb["ref_sg"]),
                    "dft_eform": _round_opt(float(rb["dft_eform"])),
                    "passes": pass_comparison,
                }
            )

    def _collect_match_flips(base_p: str, cand_p: str) -> dict[str, list[dict[str, Any]]]:
        flips: dict[str, list[dict[str, Any]]] = {
            "strict_gained_shared_ok": [],
            "strict_lost_shared_ok": [],
            "loose_gained_shared_ok": [],
            "loose_lost_shared_ok": [],
        }
        for rb, rc in zip(base_rows, cand_rows, strict=True):
            b_ok_flag = _parse_bool_cell(rb.get(f"{base_p}_ok"))
            c_ok_flag = _parse_bool_cell(rc.get(f"{cand_p}_ok"))
            if not (b_ok_flag and c_ok_flag):
                continue
            b_st = _parse_bool_cell(rb.get(f"{base_p}_match_strict"))
            c_st = _parse_bool_cell(rc.get(f"{cand_p}_match_strict"))
            b_lo = _parse_bool_cell(rb.get(f"{base_p}_match_loose"))
            c_lo = _parse_bool_cell(rc.get(f"{cand_p}_match_loose"))
            if b_st == c_st and b_lo == c_lo:
                continue
            rec = {
                "row_index": int(rb["row_index"]),
                "material_id": rb["material_id"],
                "formula": rb["formula"],
                "crystal_system": rb["crystal_system"],
                "v402_eform": _round_opt(_parse_float_cell(rb.get(f"{base_p}_eform"))),
                "v41_eform": _round_opt(_parse_float_cell(rc.get(f"{cand_p}_eform"))),
                "v402_abs_err": _round_opt(_parse_float_cell(rb.get(f"{base_p}_abs_err"))),
                "v41_abs_err": _round_opt(_parse_float_cell(rc.get(f"{cand_p}_abs_err"))),
                "v402_strict": b_st,
                "v41_strict": c_st,
                "v402_loose": b_lo,
                "v41_loose": c_lo,
                "v402_pred_sg": _parse_int_cell(rb.get(f"{base_p}_pred_sg")),
                "v41_pred_sg": _parse_int_cell(rc.get(f"{cand_p}_pred_sg")),
            }
            if (not b_st) and c_st:
                flips["strict_gained_shared_ok"].append(rec)
            elif b_st and (not c_st):
                flips["strict_lost_shared_ok"].append(rec)
            if (not b_lo) and c_lo:
                flips["loose_gained_shared_ok"].append(rec)
            elif b_lo and (not c_lo):
                flips["loose_lost_shared_ok"].append(rec)
        return flips

    return {
        "rescued_lattice_basis_crystals_v41_default": rescued_snf,
        "remaining_non_decodable_crystals_v41_default": remaining_failures,
        "gfnff_incomplete_oxyhydrides_def031": gfnff_cases,
        "shared_ok_match_flips": {
            "v41_default_vs_v402_default": _collect_match_flips("default", "default"),
            "v41_lorentz_vs_v402_lorentz": _collect_match_flips("lorentz", "lorentz"),
            "v41_robust_vs_v402_robust": _collect_match_flips("robust", "robust"),
        },
    }


def _evaluate_crnn_chunk(lines: list[str]) -> tuple[dict[str, int], list[str]]:
    """Evaluate ``v4.0.2`` vs ``v4.1`` ``check_SLICES`` and SNF outcomes on a chunk."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    warnings.filterwarnings("ignore")

    if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    import networkx as nx
    from networkx.algorithms import tree

    from slices.core import SLICES
    from slices.tobascco_net import Net

    class _InstrumentedNet(Net):
        """``Net`` subclass recording whether exact SNF fallback was invoked."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.snf_invoked: bool = False
            self.snf_succeeded: bool = False

        def _get_lattice_basis_via_snf(self) -> bool:
            self.snf_invoked = True
            ok = super()._get_lattice_basis_via_snf()
            self.snf_succeeded = ok
            return ok

    cg = SLICES(relax_model=None)
    counts: dict[str, int] = {
        "total_rows": 0,
        "v402_check_slices_valid": 0,
        "v41_check_slices_valid": 0,
        "v402_primary_decodable": 0,
        "rescued_unimodular_snf_def003": 0,
        "rejected_by_def021_total": 0,
        "rejected_rank_deficient_1d_2d": 0,
        "rejected_proper_sublattice": 0,
        "rejected_cocycle_rank_deficient": 0,
        "rejected_both_basis_and_cocycle": 0,
    }
    rejected_strings: list[str] = []

    sink = io.StringIO()
    for raw in lines:
        sli = raw.strip()
        if not sli:
            continue
        counts["total_rows"] += 1

        try:
            cg.from_SLICES(sli, strategy=3, fix_duplicate_edge=True, strict=False)
        except Exception:
            continue

        g_multi = nx.MultiGraph()
        g_multi.add_nodes_from(range(len(cg.atom_types)))
        g_multi.add_edges_from(cg.edge_indices)
        mst = tree.minimum_spanning_edges(g_multi, algorithm="kruskal", data=False)
        if g_multi.size() - len(list(mst)) < 3:
            continue

        nodes_covered = {u for edge in cg.edge_indices for u in edge}
        if len(nodes_covered) != len(cg.atom_types):
            continue

        edge_cov: list[list[int]] = [[], [], []]
        for idx_e, jimg in enumerate(cg.to_jimages):
            for axis in range(3):
                if jimg[axis] != 0:
                    edge_cov[axis].append(idx_e)
        if any(len(ax_list) == 0 for ax_list in edge_cov):
            continue

        if len(edge_cov[1]) >= len(edge_cov[0]):
            b_sub_a = [i for i in edge_cov[1] if i not in edge_cov[0]]
        else:
            b_sub_a = [i for i in edge_cov[0] if i not in edge_cov[1]]
        a_add_b = edge_cov[0] + edge_cov[1]
        if len(a_add_b) >= len(edge_cov[2]):
            c_sub_ab = [i for i in a_add_b if i not in edge_cov[2]]
        else:
            c_sub_ab = [i for i in edge_cov[2] if i not in a_add_b]
        if not b_sub_a or not c_sub_ab:
            continue

        try:
            with contextlib.redirect_stdout(sink):
                x_dat, net_voltage = cg.convert_graph()
                net = _InstrumentedNet(x_dat, dim=3)
                net.voltage = net_voltage
                net.simple_cycle_basis()
                basis_v41 = net.get_lattice_basis()
                net.get_cocycle_basis()
        except Exception:
            continue

        # Reaching this point without exception is exact v4.0.2 check_SLICES == True.
        counts["v402_check_slices_valid"] += 1

        basis_ok = basis_v41 != -1 and net.lattice_basis is not None
        cocycle_ok = not (
            net.order > 1
            and (
                net.cocycle is None
                or net.cocycle_rep is None
                or net.cocycle.ndim != 2
                or len(net.cocycle) < net.order - 1
            )
        )

        if basis_ok and cocycle_ok:
            counts["v41_check_slices_valid"] += 1
            if net.snf_invoked and net.snf_succeeded:
                counts["rescued_unimodular_snf_def003"] += 1
            else:
                counts["v402_primary_decodable"] += 1
        else:
            counts["rejected_by_def021_total"] += 1
            rejected_strings.append(sli)
            if not basis_ok:
                c_arr = np.asarray(net.cycle_rep) if net.cycle_rep is not None else np.zeros((0, 3))
                rank = int(np.linalg.matrix_rank(c_arr)) if c_arr.ndim == 2 and c_arr.size else 0
                if rank < 3:
                    counts["rejected_rank_deficient_1d_2d"] += 1
                else:
                    counts["rejected_proper_sublattice"] += 1
            if not cocycle_ok:
                counts["rejected_cocycle_rank_deficient"] += 1
            if (not basis_ok) and (not cocycle_ok):
                counts["rejected_both_basis_and_cocycle"] += 1

    return counts, rejected_strings


def _scan_crnn_corpora(crnn_dir: Path, workers: int) -> dict[str, Any]:
    """Scan ``sampled.sli`` and ``results_3_fix_valid_check_unique.sli`` corpora."""
    if not crnn_dir.is_dir():
        return {"available": False}

    sli_files: list[Path] = sorted(
        list(crnn_dir.glob("**/sampled.sli"))
        + list(crnn_dir.glob("**/results_3_fix_valid_check_unique.sli"))
    )
    if not sli_files:
        return {"available": False}

    t0 = time.perf_counter()
    ctx = mp.get_context("spawn")
    datasets_report: dict[str, Any] = {}
    unique_totals: dict[str, int] = {
        "total_rows": 0,
        "v402_check_slices_valid": 0,
        "v41_check_slices_valid": 0,
        "v402_primary_decodable": 0,
        "rescued_unimodular_snf_def003": 0,
        "rejected_by_def021_total": 0,
        "rejected_rank_deficient_1d_2d": 0,
        "rejected_proper_sublattice": 0,
        "rejected_cocycle_rank_deficient": 0,
        "rejected_both_basis_and_cocycle": 0,
        "survived_4_inverse_among_rejected": 0,
    }

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
        for sli_path in sli_files:
            lines = [ln for ln in sli_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            n_chunks = min(max(1, workers), max(1, (len(lines) + 249) // 250))
            chunk_size = (len(lines) + n_chunks - 1) // n_chunks
            chunks = [lines[i : i + chunk_size] for i in range(0, len(lines), chunk_size)]
            merged: dict[str, int] = {}
            rejected_all: set[str] = set()
            for chunk_res, chunk_rej in pool.map(_evaluate_crnn_chunk, chunks):
                for k, v in chunk_res.items():
                    merged[k] = merged.get(k, 0) + int(v)
                rejected_all.update(chunk_rej)

            # Check whether a sibling 4_inverse/results_4_inverse.csv exists to verify 0% loss.
            inv_csv = sli_path.parent.parent / "4_inverse" / "results_4_inverse.csv"
            survived_among_rejected: int | None = None
            if inv_csv.is_file():
                survived_set: set[str] = set()
                with inv_csv.open(encoding="utf-8", newline="") as fh:
                    reader = csv.reader(fh)
                    for row in reader:
                        for cell in row:
                            if " " in cell and any(ch.isdigit() for ch in cell):
                                survived_set.add(cell.strip())
                survived_among_rejected = len(rejected_all & survived_set)

            n_tot = merged["total_rows"]
            v402_v = merged["v402_check_slices_valid"]
            v41_v = merged["v41_check_slices_valid"]
            rel_key = _rel_path_str(sli_path)
            entry: dict[str, Any] = {
                **merged,
                "v402_validity_rate": _round_opt(v402_v / n_tot if n_tot else None),
                "v41_validity_rate": _round_opt(v41_v / n_tot if n_tot else None),
                "validity_rate_delta_pp": _round_opt(
                    ((v41_v - v402_v) / n_tot) * 100.0 if n_tot else None,
                    4,
                ),
                "v402_false_positive_crash_count": (
                    merged["rescued_unimodular_snf_def003"] + merged["rejected_by_def021_total"]
                ),
                "v402_false_positive_rate_among_valid_pct": _round_opt(
                    (merged["rejected_by_def021_total"] / v402_v) * 100.0 if v402_v else None,
                    4,
                ),
                "survived_4_inverse_among_rejected": survived_among_rejected,
            }
            datasets_report[rel_key] = entry

            if sli_path.name == "results_3_fix_valid_check_unique.sli":
                for k in merged:
                    unique_totals[k] += merged[k]
                if survived_among_rejected is not None:
                    unique_totals["survived_4_inverse_among_rejected"] += survived_among_rejected

    u_tot = unique_totals["total_rows"]
    u_v402 = unique_totals["v402_check_slices_valid"]
    u_v41 = unique_totals["v41_check_slices_valid"]

    return {
        "available": True,
        "scan_wall_seconds": _round_opt(time.perf_counter() - t0, 3),
        "datasets": datasets_report,
        "published_unique_sli_aggregate_4_targets": {
            **unique_totals,
            "v402_validity_rate": _round_opt(u_v402 / u_tot if u_tot else None),
            "v41_validity_rate": _round_opt(u_v41 / u_tot if u_tot else None),
            "validity_rate_delta_pp": _round_opt(
                ((u_v41 - u_v402) / u_tot) * 100.0 if u_tot else None,
                4,
            ),
            "rejected_rate_among_v402_valid_pct": _round_opt(
                (unique_totals["rejected_by_def021_total"] / u_v402) * 100.0 if u_v402 else None,
                4,
            ),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run paired statistical A/B comparison and write structured JSON output.

    Args:
        argv: Optional CLI argument sequence.

    Returns:
        Exit code (``0`` on success).
    """
    parser = argparse.ArgumentParser(
        description="Compare SLICES v4.1 experimental MP-20 benchmark against v4.0.2-baseline."
    )
    parser.add_argument(
        "--candidate-dir",
        type=Path,
        default=DEFAULT_CANDIDATE_DIR,
        help="directory containing candidate per_structure_metrics.csv and summary.json",
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=DEFAULT_BASELINE_DIR,
        help="directory containing baseline per_structure_metrics.csv and summary.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output JSON path (default: <candidate-dir>/ab_vs_v4_0_2.json)",
    )
    parser.add_argument(
        "--crnn-dir",
        type=Path,
        default=DEFAULT_CRNN_DIR,
        help="directory containing cRNN sampled.sli and unique.sli benchmarks",
    )
    parser.add_argument(
        "--skip-crnn",
        action="store_true",
        help="skip cRNN check_SLICES validity-rate scan",
    )
    parser.add_argument(
        "--crnn-workers",
        type=int,
        default=min(16, os.cpu_count() or 1),
        help="worker count for cRNN validity scan (default: min(16, cpu_count))",
    )
    args = parser.parse_args(argv)

    out_path = args.out if args.out is not None else (args.candidate_dir / "ab_vs_v4_0_2.json")

    base_csv = args.baseline_dir / "per_structure_metrics.csv"
    cand_csv = args.candidate_dir / "per_structure_metrics.csv"
    base_json = args.baseline_dir / "summary.json"
    cand_json = args.candidate_dir / "summary.json"

    base_rows = _load_csv_by_index(base_csv)
    cand_rows = _load_csv_by_index(cand_csv)
    if len(base_rows) != len(cand_rows):
        raise ValueError(
            f"Row count mismatch: baseline={len(base_rows)} vs candidate={len(cand_rows)}"
        )

    base_summary = json.loads(base_json.read_text(encoding="utf-8"))
    cand_summary = json.loads(cand_json.read_text(encoding="utf-8"))

    comparisons: dict[str, Any] = {}
    for comp_key, cand_pass, base_pass in COMPARISON_SPECS:
        if cand_pass in cand_summary["passes"] and base_pass in base_summary["passes"]:
            comparisons[comp_key] = _compare_pass_pair(
                base_rows=base_rows,
                cand_rows=cand_rows,
                base_pass_summary=base_summary["passes"][base_pass],
                cand_pass_summary=cand_summary["passes"][cand_pass],
                base_pass=base_pass,
                cand_pass=cand_pass,
            )

    crystal_reports = _build_crystal_level_reports(base_rows, cand_rows)
    crnn_report = (
        {"available": False, "skipped": True}
        if args.skip_crnn
        else _scan_crnn_corpora(args.crnn_dir, max(1, int(args.crnn_workers)))
    )

    payload: dict[str, Any] = {
        "metadata": {
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "candidate_dir": _rel_path_str(args.candidate_dir),
            "baseline_dir": _rel_path_str(args.baseline_dir),
            "candidate_git_commit": cand_summary["benchmark_metadata"]["environment"]["git_commit"],
            "baseline_git_commit": base_summary["benchmark_metadata"]["environment"]["git_commit"],
            "total_structures": len(base_rows),
            "candidate_total_wall_seconds": cand_summary["benchmark_metadata"][
                "total_wall_seconds"
            ],
            "baseline_total_wall_seconds": base_summary["benchmark_metadata"]["total_wall_seconds"],
        },
        "paired_comparisons": comparisons,
        "crystal_level_reports": crystal_reports,
        "crnn_validity_impact": crnn_report,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    print(
        f"Wrote paired A/B report to {out_path} ({out_path.stat().st_size} bytes).",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
