#!/usr/bin/env python3
"""Run SLICES v4.1 extended GPU benchmarks across MP-20, QMOF-21-40, and MP-21-40.

Implements three uncontended benchmark suites for multi-GPU evaluation:

1. ``mp20``: Full 2,383-structure MP-20 multi-model GPU reconstruction benchmark
   across ``nequip-s+l``, ``nequip-m+l``, ``nequip-l``, ``chgnet``, and ``mace``,
   plus a 64-crystal single-worker stage-timing breakdown comparing CPU and CUDA
   backends and paired statistical tests against the archived CPU v4.1 baseline.
2. ``qmof``: Full 339-structure QMOF-21-40 Strategy-4 CIF round-trip benchmark
   (``graph_method="econnn"``) comparing ``legacy`` vs ``lorentz`` LJ mixing.
3. ``mp21-40``: Deterministic crystal-system-stratified 1,000-structure MP-21-40
   held-out test benchmark (``graph_method="crystalnn"``) comparing ``legacy`` vs
   ``lorentz`` LJ mixing with DFT formation-energy accuracy and paired tests.

Supports ``--work-dir`` checkpointing so models hosted in separate Python
environments (e.g., ``nequip`` vs optional ``chgnet``/``mace`` environments) can
be executed sequentially and merged cleanly into unified JSON and CSV archives.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import contextlib
import csv
import datetime
import hashlib
import io
import json
import math
import multiprocessing as mp
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import stats

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pymatgen.core.structure import Structure

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

DEFAULT_MP20_CSV = REPO_ROOT / "data" / "mp20_nonmetal" / "mp20_v4_benchmark_2383.csv"
DEFAULT_CHEM_POT = REPO_ROOT / "data" / "mp20_nonmetal" / "chemPotMP.json"
DEFAULT_MP20_DIR = REPO_ROOT / "data" / "mp20"
DEFAULT_CPU_BASELINE_DIR = REPO_ROOT / "benchmark" / "v4_1_experimental"
DEFAULT_QMOF_JSON = (
    REPO_ROOT / "benchmark" / "Match_rate_QMOF-21-40" / "0_get_json" / "cifs_filtered.json"
)
DEFAULT_MP21_40_DIR = REPO_ROOT / "data" / "mp-21-40"
DEFAULT_OUT_DIR = REPO_ROOT / "benchmark" / "v4_1_extended"

MP20_MODEL_ORDER: tuple[str, ...] = (
    "nequip-s+l",
    "nequip-m+l",
    "nequip-l",
    "chgnet",
    "mace",
)
STAGE_CONFIG_ORDER: tuple[str, ...] = (
    "cpu:nequip-s+l",
    "cuda:nequip-s+l",
    "cuda:nequip-m+l",
    "cuda:nequip-l",
    "cuda:chgnet",
    "cuda:mace",
)
PAIRED_PASS_ORDER: tuple[str, ...] = ("default", "lorentz")
CRYSTAL_SYSTEM_ORDER: tuple[str, ...] = (
    "cubic",
    "hexagonal",
    "trigonal",
    "tetragonal",
    "orthorhombic",
    "monoclinic",
    "triclinic",
)
ATOM_COUNT_BINS: tuple[tuple[str, int, int], ...] = (
    ("21_25", 21, 25),
    ("26_30", 26, 30),
    ("31_35", 31, 35),
    ("36_40", 36, 40),
)
OUTLIER_ABS_ERR_THRESHOLD: float = 10.0

# Published SLICES paper Table S1 reconstruction baselines (M3GNet pipeline).
UPSTREAM_TABLE_S1_QMOF: dict[str, float] = {
    "strict_rate": 0.0295,
    "loose_rate": 0.0619,
    "strict_pct": 2.95,
    "loose_pct": 6.19,
    "dataset_size": 339,
}
UPSTREAM_TABLE_S1_MP21_40: dict[str, float] = {
    "strict_rate": 0.8607,
    "loose_rate": 0.8897,
    "strict_pct": 86.07,
    "loose_pct": 88.97,
    "dataset_size": 23560,
}


@dataclass(frozen=True)
class RunSpec:
    """Configuration for a single benchmark pass across worker processes.

    Attributes:
        name: Short pass or model key used in JSON and CSV outputs.
        mode: Evaluation mode (``"decode_slices"`` or ``"cif_roundtrip"``).
        device: Target compute device (``"cuda"`` or ``"cpu"``).
        relax_model: Force-field identifier passed to ``SLICES``.
        graph_method: Local-environment graph builder name.
        lj_mixing: Heteronuclear LJ mixing mode (``"legacy"`` or ``"lorentz"``).
        workers: Number of spawned worker processes.
        n_gpus: Number of GPUs used for ``worker_id % n_gpus`` pinning.
        compute_roundtrip_canon: Whether to re-encode relaxed structures to test
            canonical SLICES round-trip equivalence.
    """

    name: str
    mode: str
    device: str
    relax_model: str
    graph_method: str
    lj_mixing: str
    workers: int
    n_gpus: int = 2
    compute_roundtrip_canon: bool = False


class _RelaxTelemetryProxy:
    """Non-invasive proxy around ``cg.relaxer`` recording per-structure metrics."""

    def __init__(self, inner: Any) -> None:
        """Initialize the proxy around an underlying relaxer object."""
        self._inner = inner
        self.called: bool = False
        self.succeeded: bool = False
        self.steps: int = 0
        self.preoptimized: bool = False
        self.retry: int = 0
        self.relax_s: float = 0.0
        self.error_type: str = ""

    def reset(self) -> None:
        """Reset per-structure counters prior to a new decode call."""
        self.called = False
        self.succeeded = False
        self.steps = 0
        self.preoptimized = False
        self.retry = 0
        self.relax_s = 0.0
        self.error_type = ""

    def __getattr__(self, attr: str) -> Any:
        """Delegate attribute access to the wrapped relaxer."""
        return getattr(self._inner, attr)

    def relax(self, structure: Structure, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Run ``self._inner.relax`` while recording elapsed time and step counts."""
        self.called = True
        t0 = time.perf_counter()
        try:
            res: dict[str, Any] = self._inner.relax(structure, *args, **kwargs)
        except Exception as exc:
            self.relax_s += time.perf_counter() - t0
            self.succeeded = False
            self.error_type = type(exc).__name__
            raise
        self.relax_s += time.perf_counter() - t0
        self.succeeded = True
        self.error_type = ""
        self.steps += int(res.get("steps", 0))
        self.preoptimized = bool(res.get("preoptimized", False))
        self.retry = int(res.get("retry", 0))
        return res


class _NvidiaSmiMonitor:
    """Lightweight background sampler polling GPU VRAM and utilization via ``nvidia-smi``."""

    def __init__(self, interval_s: float = 1.0) -> None:
        """Initialize the sampler with polling interval ``interval_s`` seconds."""
        self._interval_s = interval_s
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._samples_by_gpu: dict[int, list[tuple[float, float]]] = collections.defaultdict(list)
        self._gpu_meta: dict[int, dict[str, Any]] = {}
        self._baseline_mib: dict[int, float] = {}

    def _poll_once(self) -> dict[int, tuple[str, float, float, float]]:
        """Execute a single ``nvidia-smi`` query and parse per-GPU metrics."""
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        parsed: dict[int, tuple[str, float, float, float]] = {}
        if proc.returncode != 0:
            return parsed
        for line in proc.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            with contextlib.suppress(ValueError):
                idx = int(parts[0])
                name = parts[1]
                mem_used = float(parts[2])
                mem_total = float(parts[3])
                util = float(parts[4])
                parsed[idx] = (name, mem_used, mem_total, util)
        return parsed

    def start(self) -> None:
        """Record baseline VRAM and launch the background polling thread."""
        with contextlib.suppress(Exception):
            snap = self._poll_once()
            for idx, (name, mem_used, mem_total, util) in snap.items():
                self._gpu_meta[idx] = {"name": name, "memory_total_mib": mem_total}
                self._baseline_mib[idx] = mem_used
                self._samples_by_gpu[idx].append((mem_used, util))

        def _loop() -> None:
            while not self._stop_event.wait(self._interval_s):
                with contextlib.suppress(Exception):
                    snap_now = self._poll_once()
                    for idx, (name, mem_used, mem_total, util) in snap_now.items():
                        self._gpu_meta.setdefault(
                            idx, {"name": name, "memory_total_mib": mem_total}
                        )
                        self._samples_by_gpu[idx].append((mem_used, util))

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> dict[str, Any]:
        """Stop polling and return aggregated per-GPU VRAM and utilization telemetry."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        with contextlib.suppress(Exception):
            snap_end = self._poll_once()
            for idx, (name, mem_used, mem_total, util) in snap_end.items():
                self._gpu_meta.setdefault(idx, {"name": name, "memory_total_mib": mem_total})
                self._samples_by_gpu[idx].append((mem_used, util))

        gpus_out: dict[str, Any] = {}
        overall_peak_mib = 0.0
        for idx in sorted(self._samples_by_gpu):
            samples = self._samples_by_gpu[idx]
            mems = [m for m, _ in samples]
            utils = [u for _, u in samples]
            peak_mib = max(mems) if mems else 0.0
            base_mib = self._baseline_mib.get(idx, 0.0)
            overall_peak_mib = max(overall_peak_mib, peak_mib)
            gpus_out[f"gpu_{idx}"] = {
                "name": self._gpu_meta.get(idx, {}).get("name", ""),
                "memory_total_mib": _round_opt(
                    self._gpu_meta.get(idx, {}).get("memory_total_mib"), 1
                ),
                "baseline_used_mib": _round_opt(base_mib, 1),
                "peak_used_mib": _round_opt(peak_mib, 1),
                "peak_delta_mib": _round_opt(max(0.0, peak_mib - base_mib), 1),
                "mean_gpu_util_pct": _round_opt(statistics.mean(utils) if utils else None, 2),
                "max_gpu_util_pct": _round_opt(max(utils) if utils else None, 1),
                "sample_count": len(samples),
            }
        return {
            "max_gpu_peak_used_mib": _round_opt(overall_peak_mib, 1),
            "per_gpu": gpus_out,
        }


_WORKER_STATE: dict[str, Any] = {}
_STAGE_TIMERS: dict[str, float] = {}


def _clean_path_label(path: Path) -> str:
    """Format ``path`` relative to ``REPO_ROOT`` without exposing host user paths."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return f"<external>/{path.name}"


def _round_opt(val: float | None, digits: int = 6) -> float | None:
    """Round an optional finite float to ``digits`` decimal places."""
    if val is None or not math.isfinite(val):
        return None
    return round(float(val), digits)


def _percentile(values: list[float], q: float) -> float | None:
    """Compute linear-interpolated percentile ``q`` in ``[0, 100]``."""
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), q))


def _mcnemar_exact_pvalue(gained: int, lost: int) -> float:
    """Compute exact two-sided McNemar p-value via ``scipy.stats.binomtest``."""
    discordant = int(gained) + int(lost)
    if discordant == 0:
        return 1.0
    return float(
        stats.binomtest(int(gained), n=discordant, p=0.5, alternative="two-sided").pvalue
    )


def _wilcoxon_two_sided_pvalue(diffs: list[float]) -> float | None:
    """Compute two-sided Wilcoxon signed-rank p-value over finite differences."""
    finite_diffs = [d for d in diffs if math.isfinite(d)]
    if not finite_diffs:
        return None
    arr = np.asarray(finite_diffs, dtype=float)
    non_zero = arr[arr != 0.0]
    if non_zero.size == 0:
        return 1.0
    return float(stats.wilcoxon(non_zero, zero_method="wilcox", alternative="two-sided").pvalue)


def _configure_single_thread_env() -> None:
    """Apply deterministic single-thread environment variables in the current process."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
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

    Matches ``tools/benchmarks/run_mp20_baseline.py`` verbatim.

    Args:
        structure: Relaxed crystal structure.
        energy_per_atom: Predicted total energy per atom in eV/atom.
        chem_pot: Elemental chemical potentials in eV/atom keyed by symbol.

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


def _install_stage_hooks(cg: Any) -> _RelaxTelemetryProxy | None:
    """Attach non-invasive GFN-FF, ZL*, and relaxer timing hooks to ``cg``."""
    import slices.core as core_mod

    if not getattr(core_mod, "_ext_bench_fmin_hooked", False):
        orig_fmin = core_mod.fmin_l_bfgs_b

        def _timed_fmin(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                res = orig_fmin(*args, **kwargs)
            finally:
                _STAGE_TIMERS["zl_s"] = _STAGE_TIMERS.get("zl_s", 0.0) + (
                    time.perf_counter() - t0
                )
            if isinstance(res, tuple) and len(res) >= 3 and isinstance(res[2], dict):
                _STAGE_TIMERS["zl_funcalls"] = _STAGE_TIMERS.get("zl_funcalls", 0.0) + float(
                    res[2].get("funcalls", 0)
                )
            return res

        core_mod.fmin_l_bfgs_b = _timed_fmin
        core_mod._ext_bench_fmin_hooked = True  # type: ignore[attr-defined]

    orig_gfnff = cg.get_inner_p_target

    def _timed_gfnff(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig_gfnff(*args, **kwargs)
        finally:
            _STAGE_TIMERS["gfnff_s"] = _STAGE_TIMERS.get("gfnff_s", 0.0) + (
                time.perf_counter() - t0
            )

    cg.get_inner_p_target = _timed_gfnff

    if cg.relaxer is None:
        return None
    proxy = _RelaxTelemetryProxy(cg.relaxer)
    cg.relaxer = proxy
    return proxy


def _init_worker(
    id_queue: Any,
    spec: RunSpec,
    chem_pot: dict[str, float] | None,
) -> None:
    """Initialize a spawned worker pinned to ``worker_id % spec.n_gpus``."""
    wid = int(id_queue.get())
    _configure_single_thread_env()

    if spec.device == "cuda":
        gpu_id = wid % max(1, spec.n_gpus)
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
        os.environ["SLICES_DEVICE"] = "cuda"
    else:
        gpu_id = -1
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        os.environ["SLICES_DEVICE"] = "cpu"

    if spec.relax_model == "mace":
        os.environ.setdefault("SLICES_MACE_MODEL", "medium")

    if SRC_DIR.is_dir() and str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    import torch
    from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
    from pymatgen.core import Lattice, Structure

    from slices.core import SLICES

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        cg = SLICES(
            relax_model=spec.relax_model,
            graph_method=spec.graph_method,
            lj_mixing=spec.lj_mixing,  # type: ignore[arg-type]
        )

    actual_device = getattr(cg.relaxer, "device", "none") if cg.relaxer is not None else "none"
    if spec.device == "cuda" and actual_device != "cuda":
        raise RuntimeError(
            f"Worker {wid} requested CUDA for {spec.relax_model!r} "
            f"but resolved to device={actual_device!r}"
        )

    if cg.relaxer is not None:
        warm = Structure(Lattice.cubic(4.3), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cg.relaxer.relax(warm, fmax=0.5, steps=2)
        if spec.device == "cuda" and torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()

    proxy = _install_stage_hooks(cg)

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
            "wid": wid,
            "gpu_id": gpu_id,
            "spec": spec,
            "cg": cg,
            "proxy": proxy,
            "chem_pot": chem_pot,
            "sm_strict": sm_strict,
            "sm_loose": sm_loose,
            "relaxer_description": getattr(cg.relaxer, "description", ""),
            "resolved_relax_model": cg.relax_model,
        }
    )


def _check_validity_27_images(structure: Structure) -> bool:
    """Evaluate exact ``0.5 A`` pair-distance validity via 3x3x3 periodic images.

    Mathematically identical to ``SLICES.check_structural_validity`` whenever all
    three perpendicular cell heights are at least ``0.5 A``, while avoiding large
    Cython voxel-grid allocations when ``ExpCellFilter`` expands lattice vectors to
    hundreds of Angstroms.
    """
    if len(structure) == 0:
        return False
    frac = np.mod(np.asarray(structure.frac_coords, dtype=float), 1.0)
    lat = np.asarray(structure.lattice.matrix, dtype=float)
    cart0 = frac @ lat
    shifts = np.array(
        [[i, j, k] for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)],
        dtype=float,
    )
    shift_cart = shifts @ lat  # (27, 3)
    for idx_s, s_vec in enumerate(shift_cart):
        diff = cart0[:, None, :] - (cart0[None, :, :] + s_vec[None, None, :])
        dists = np.linalg.norm(diff, axis=-1)
        if shifts[idx_s, 0] == 0.0 and shifts[idx_s, 1] == 0.0 and shifts[idx_s, 2] == 0.0:
            np.fill_diagonal(dists, np.inf)
        if bool(np.any(dists <= 0.5)):
            return False
    return True


def _evaluate_task(task: dict[str, Any]) -> dict[str, Any]:
    """Execute encoding/decoding and structural evaluation for one crystal task."""
    import torch
    from pymatgen.core.structure import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    from slices.core import SLICES

    spec: RunSpec = _WORKER_STATE["spec"]
    cg: SLICES = _WORKER_STATE["cg"]
    proxy: _RelaxTelemetryProxy | None = _WORKER_STATE["proxy"]
    chem_pot: dict[str, float] | None = _WORKER_STATE["chem_pot"]
    sm_strict = _WORKER_STATE["sm_strict"]
    sm_loose = _WORKER_STATE["sm_loose"]
    wid: int = _WORKER_STATE["wid"]
    gpu_id: int = _WORKER_STATE["gpu_id"]

    if proxy is not None:
        proxy.reset()
    _STAGE_TIMERS.clear()
    _STAGE_TIMERS.update({"gfnff_s": 0.0, "zl_s": 0.0, "zl_funcalls": 0.0})

    ori_poscar: str | None = task.get("ori_poscar")
    ref_sg: int | None = task.get("ref_sg")
    dft_eform: float | None = task.get("dft_eform")
    canon_in: str | None = task.get("canon_in")

    encode_s = 0.0
    decode_s = 0.0
    slices_str: str = ""
    encode_exc: Exception | None = None
    decode_exc: Exception | None = None
    structure: Structure | None = None
    energy: float = 0.0

    t_start = time.perf_counter()
    if spec.mode == "cif_roundtrip":
        t_enc0 = time.perf_counter()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                ori_cif_struct = Structure.from_str(task["ori_cif"], "cif")
                slices_str = cg.structure2SLICES(ori_cif_struct, strategy=4)
        except Exception as exc:
            encode_exc = exc
        encode_s = time.perf_counter() - t_enc0
    else:
        slices_str = task["slices"]

    if encode_exc is None:
        t_dec0 = time.perf_counter()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                structure, energy = cg.SLICES2structure(slices_str, strategy=4)
        except Exception as exc:
            decode_exc = exc
        decode_s = time.perf_counter() - t_dec0

    total_s = time.perf_counter() - t_start
    gfnff_s = float(_STAGE_TIMERS.get("gfnff_s", 0.0))
    zl_s = float(_STAGE_TIMERS.get("zl_s", 0.0))
    zl_funcalls = int(_STAGE_TIMERS.get("zl_funcalls", 0.0))
    relax_s = float(proxy.relax_s) if proxy is not None else 0.0
    topo_s = max(0.0, decode_s - gfnff_s - zl_s - relax_s)

    gfnff_incomplete = bool(getattr(cg, "_last_gfnff_incomplete", False))
    preoptimized = bool(proxy.preoptimized) if proxy is not None else False
    retry = int(proxy.retry) if proxy is not None else 0
    relax_steps = int(proxy.steps) if proxy is not None else 0
    relax_succeeded = bool(proxy.succeeded) if proxy is not None else (decode_exc is None)

    peak_alloc_mib = 0.0
    peak_reserved_mib = 0.0
    if spec.device == "cuda" and torch.cuda.is_available():
        peak_alloc_mib = float(torch.cuda.max_memory_allocated()) / (1024.0 * 1024.0)
        peak_reserved_mib = float(torch.cuda.max_memory_reserved()) / (1024.0 * 1024.0)

    if encode_exc is not None or decode_exc is not None or structure is None:
        if encode_exc is not None:
            err_name = f"EncodeError:{type(encode_exc).__name__}"
        elif decode_exc is not None:
            err_name = type(decode_exc).__name__
        else:
            err_name = "UnknownDecodeError"
        return {
            "row_index": task["row_index"],
            "encoded": encode_exc is None,
            "decoded": False,
            "ok": False,
            "energy_per_atom": None,
            "eform": None,
            "abs_err": None,
            "vol_per_atom": None,
            "extreme_outlier": False,
            "match_strict": False if ori_poscar is not None else None,
            "match_loose": False if ori_poscar is not None else None,
            "struct_valid": None,
            "pred_sg": None,
            "sg_match": None,
            "roundtrip_canonical_match": None,
            "preoptimized": preoptimized,
            "retry": retry,
            "relax_steps": relax_steps,
            "zl_funcalls": zl_funcalls,
            "gfnff_incomplete": gfnff_incomplete,
            "encode_s": encode_s,
            "gfnff_s": gfnff_s,
            "zl_s": zl_s,
            "relax_s": relax_s,
            "topo_s": topo_s,
            "decode_s": decode_s,
            "seconds": total_s if spec.mode == "cif_roundtrip" else decode_s,
            "error_type": err_name,
            "wid": wid,
            "gpu_id": gpu_id,
            "worker_peak_alloc_mib": peak_alloc_mib,
            "worker_peak_reserved_mib": peak_reserved_mib,
            "resolved_relax_model": _WORKER_STATE["resolved_relax_model"],
            "relaxer_description": _WORKER_STATE["relaxer_description"],
        }

    ok = relax_succeeded
    finite_cell = bool(
        np.all(np.isfinite(structure.lattice.matrix))
        and np.all(np.isfinite(structure.frac_coords))
    )
    vol_per_atom = (
        float(abs(structure.volume)) / max(1, len(structure)) if finite_cell else 0.0
    )
    abc_vals = [float(x) for x in structure.lattice.abc] if finite_cell else [0.0, 0.0, 0.0]
    min_abc = min(abc_vals)
    max_abc = max(abc_vals)
    min_perp_h = 0.0
    if finite_cell and vol_per_atom > 1e-9:
        with contextlib.suppress(Exception):
            recip_abc = [float(x) for x in structure.lattice.reciprocal_lattice.abc]
            if all(x > 0.0 and math.isfinite(x) for x in recip_abc):
                min_perp_h = min((2.0 * math.pi) / x for x in recip_abc)

    niggli_struct: Structure = structure
    niggli_min_h = min_perp_h
    niggli_max_abc = max_abc
    if finite_cell and vol_per_atom > 1e-9:
        with contextlib.suppress(Exception):
            niggli_struct = structure.get_reduced_structure("niggli")
            n_abc = [float(x) for x in niggli_struct.lattice.abc]
            n_rec = [float(x) for x in niggli_struct.lattice.reciprocal_lattice.abc]
            if all(x > 0.0 and math.isfinite(x) for x in n_rec):
                niggli_min_h = min((2.0 * math.pi) / x for x in n_rec)
                niggli_max_abc = max(n_abc)

    severe_collapse = (
        (not finite_cell)
        or vol_per_atom < 0.25
        or min_abc < 0.25
        or niggli_min_h < 0.5
    )
    cell_exploded = (not severe_collapse) and (
        vol_per_atom > 1000.0
        or niggli_max_abc > 80.0
        or (niggli_min_h > 0.0 and (niggli_max_abc / niggli_min_h) > 15.0)
    )

    energy_val: float | None = float(energy) if ok else None
    eform_val: float | None = None
    abs_err_val: float | None = None
    if ok:
        error_type = ""
        if chem_pot is not None and dft_eform is not None:
            eform_val = formation_energy(niggli_struct, float(energy), chem_pot)
            abs_err_val = abs(eform_val - dft_eform)
    else:
        sub_err = proxy.error_type if (proxy is not None and proxy.error_type) else "RelaxFailed"
        error_type = f"RelaxFallback:{sub_err}"

    extreme_outlier = bool(
        ok
        and (
            severe_collapse
            or cell_exploded
            or vol_per_atom < 2.0
            or (energy_val is not None and not math.isfinite(energy_val))
            or (
                abs_err_val is not None
                and (not math.isfinite(abs_err_val) or abs_err_val > OUTLIER_ABS_ERR_THRESHOLD)
            )
        )
    )

    if severe_collapse:
        struct_valid = False
    else:
        try:
            struct_valid = _check_validity_27_images(niggli_struct)
        except Exception:
            struct_valid = False

    pred_sg: int | None = None
    prim_std: Structure = niggli_struct
    if not severe_collapse and not cell_exploded:
        try:
            sga = SpacegroupAnalyzer(niggli_struct)
            pred_sg = int(sga.get_space_group_number())
            prim_std = sga.get_primitive_standard_structure()
        except Exception:
            pred_sg = None
            prim_std = niggli_struct

    sg_match: bool | None = (pred_sg == ref_sg) if (pred_sg is not None and ref_sg) else False

    roundtrip_match: bool | None = None
    if spec.compute_roundtrip_canon and canon_in is not None:
        if severe_collapse or cell_exploded or vol_per_atom < 2.0:
            roundtrip_match = False
        else:
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
        if not ok or severe_collapse or cell_exploded:
            match_strict = False
            match_loose = False
        else:
            try:
                ori_checked = Structure.from_str(ori_poscar, "poscar")
                opt2_checked = Structure.from_str(niggli_struct.to(fmt="poscar"), "poscar")
                match_strict = bool(sm_strict.fit(ori_checked, opt2_checked))
                match_loose = bool(sm_loose.fit(ori_checked, opt2_checked))
            except Exception:
                match_strict = False
                match_loose = False

    return {
        "row_index": task["row_index"],
        "encoded": True,
        "decoded": True,
        "ok": ok,
        "energy_per_atom": energy_val,
        "eform": eform_val,
        "abs_err": abs_err_val,
        "vol_per_atom": vol_per_atom,
        "extreme_outlier": extreme_outlier,
        "match_strict": match_strict,
        "match_loose": match_loose,
        "struct_valid": struct_valid,
        "pred_sg": pred_sg,
        "sg_match": sg_match,
        "roundtrip_canonical_match": roundtrip_match,
        "preoptimized": preoptimized,
        "retry": retry,
        "relax_steps": relax_steps,
        "zl_funcalls": zl_funcalls,
        "gfnff_incomplete": gfnff_incomplete,
        "encode_s": encode_s,
        "gfnff_s": gfnff_s,
        "zl_s": zl_s,
        "relax_s": relax_s,
        "topo_s": topo_s,
        "decode_s": decode_s,
        "seconds": total_s if spec.mode == "cif_roundtrip" else decode_s,
        "error_type": error_type,
        "wid": wid,
        "gpu_id": gpu_id,
        "worker_peak_alloc_mib": peak_alloc_mib,
        "worker_peak_reserved_mib": peak_reserved_mib,
        "resolved_relax_model": _WORKER_STATE["resolved_relax_model"],
        "relaxer_description": _WORKER_STATE["relaxer_description"],
    }


def _run_pool_pass(
    spec: RunSpec,
    tasks: list[dict[str, Any]],
    chem_pot: dict[str, float] | None,
) -> tuple[list[dict[str, Any]], float, dict[str, Any]]:
    """Run ``tasks`` across ``spec.workers`` spawned processes with VRAM telemetry."""
    ctx = mp.get_context("spawn")
    id_queue = ctx.Queue()
    for w in range(spec.workers):
        id_queue.put(w)

    n_tasks = len(tasks)
    ordered_results: list[dict[str, Any] | None] = [None] * n_tasks

    monitor: _NvidiaSmiMonitor | None = None
    if spec.device == "cuda":
        monitor = _NvidiaSmiMonitor(interval_s=1.0)
        monitor.start()

    print(
        f"[{spec.name}] Starting {n_tasks} structures across {spec.workers} worker(s) "
        f"(device={spec.device}, model={spec.relax_model}, graph={spec.graph_method}, "
        f"lj={spec.lj_mixing})...",
        flush=True,
    )
    t_pass = time.perf_counter()
    completed = 0
    step_report = max(1, min(250, max(1, n_tasks // 8)))

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=spec.workers,
        mp_context=ctx,
        initializer=_init_worker,
        initargs=(id_queue, spec, chem_pot),
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
    smi_telemetry = monitor.stop() if monitor is not None else {}

    final_results: list[dict[str, Any]] = [r for r in ordered_results if r is not None]
    worker_alloc_by_wid: dict[int, float] = {}
    worker_resv_by_wid: dict[int, float] = {}
    worker_gpu_by_wid: dict[int, int] = {}
    resolved_model = spec.relax_model
    relaxer_desc = ""
    for r in final_results:
        w = int(r["wid"])
        worker_gpu_by_wid[w] = int(r["gpu_id"])
        worker_alloc_by_wid[w] = max(
            worker_alloc_by_wid.get(w, 0.0), float(r["worker_peak_alloc_mib"])
        )
        worker_resv_by_wid[w] = max(
            worker_resv_by_wid.get(w, 0.0), float(r["worker_peak_reserved_mib"])
        )
        if r.get("resolved_relax_model"):
            resolved_model = str(r["resolved_relax_model"])
        if r.get("relaxer_description"):
            relaxer_desc = str(r["relaxer_description"])

    vram_summary: dict[str, Any] = {
        "gpus_assigned": sorted({g for g in worker_gpu_by_wid.values() if g >= 0}),
        "workers_spawned": len(worker_gpu_by_wid),
        "max_worker_torch_allocated_mib": _round_opt(
            max(worker_alloc_by_wid.values()) if worker_alloc_by_wid else 0.0, 2
        ),
        "max_worker_torch_reserved_mib": _round_opt(
            max(worker_resv_by_wid.values()) if worker_resv_by_wid else 0.0, 2
        ),
        "sum_worker_torch_allocated_mib": _round_opt(sum(worker_alloc_by_wid.values()), 2),
        "nvidia_smi": smi_telemetry,
    }
    run_meta = {
        "resolved_relax_model": resolved_model,
        "relaxer_description": relaxer_desc,
        "vram_telemetry": vram_summary,
        "runtime_env": _collect_runtime_versions(),
    }
    return final_results, wall_s, run_meta


def _collect_runtime_versions() -> dict[str, Any]:
    """Collect package and GPU runtime versions without absolute filesystem paths."""
    import ase
    import pymatgen.core
    import scipy
    import torch

    import slices

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

    opt_pkgs: dict[str, str] = {}
    for mod_name in ("nequip", "openequivariance", "chgnet", "mace"):
        with contextlib.suppress( Exception):
            mod = __import__(mod_name)
            opt_pkgs[f"{mod_name}_version"] = str(getattr(mod, "__version__", "installed"))

    gpu_names: list[str] = []
    if torch.cuda.is_available():
        for idx in range(torch.cuda.device_count()):
            gpu_names.append(torch.cuda.get_device_name(idx))

    return {
        "git_commit": git_commit,
        "slices_version": getattr(slices, "__version__", "4.1.0"),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "cuda_version": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        "gpu_names": gpu_names,
        "pymatgen_version": getattr(pymatgen.core, "__version__", "unknown"),
        "ase_version": ase.__version__,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "cpu_count": os.cpu_count(),
        **opt_pkgs,
    }


def _aggregate_eform_block(
    abs_errs: list[float],
    signed_errs: list[float],
    n_total: int,
) -> dict[str, Any]:
    """Compute formation-energy residual statistics over ``abs_errs``."""
    finite_abs = [e for e in abs_errs if math.isfinite(e)]
    finite_signed = [s for s in signed_errs if math.isfinite(s)]
    within_005 = sum(1 for e in finite_abs if e <= 0.05)
    within_010 = sum(1 for e in finite_abs if e <= 0.10)
    rmse: float | None = None
    if finite_abs:
        with contextlib.suppress(OverflowError):
            rmse = math.sqrt(sum(e * e for e in finite_abs) / len(finite_abs))
    return {
        "count": len(finite_abs),
        "mae": _round_opt(statistics.mean(finite_abs) if finite_abs else None),
        "median_ae": _round_opt(statistics.median(finite_abs) if finite_abs else None),
        "rmse": _round_opt(rmse),
        "std_ae": _round_opt(statistics.pstdev(finite_abs) if len(finite_abs) > 1 else None),
        "p90_ae": _round_opt(_percentile(finite_abs, 90.0)),
        "p95_ae": _round_opt(_percentile(finite_abs, 95.0)),
        "max_ae": _round_opt(max(finite_abs) if finite_abs else None),
        "mean_signed_error": _round_opt(
            statistics.mean(finite_signed) if finite_signed else None
        ),
        "within_0_05_ev_count": within_005,
        "within_0_05_ev_rate_ok": _round_opt(within_005 / len(finite_abs))
        if finite_abs
        else None,
        "within_0_05_ev_rate_all": _round_opt(within_005 / n_total) if n_total else None,
        "within_0_10_ev_count": within_010,
        "within_0_10_ev_rate_ok": _round_opt(within_010 / len(finite_abs))
        if finite_abs
        else None,
        "within_0_10_ev_rate_all": _round_opt(within_010 / n_total) if n_total else None,
    }


def _aggregate_stage_timings(results: list[dict[str, Any]], include_encode: bool) -> dict[str, Any]:
    """Summarize mean, median, p90, and sum across instrumented pipeline stages."""
    if not results:
        return {}
    keys = ["gfnff_s", "zl_s", "relax_s", "topo_s", "decode_s", "seconds"]
    if include_encode:
        keys = ["encode_s", *keys]
    out: dict[str, Any] = {}
    for key in keys:
        vals = [float(r[key]) for r in results]
        out[key] = {
            "mean_s": _round_opt(statistics.mean(vals), 4),
            "median_s": _round_opt(statistics.median(vals), 4),
            "p90_s": _round_opt(_percentile(vals, 90.0), 4),
            "p95_s": _round_opt(_percentile(vals, 95.0), 4),
            "max_s": _round_opt(max(vals), 4),
            "sum_s": _round_opt(sum(vals), 2),
        }
    return out


def _aggregate_subset(
    tasks: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    has_eform: bool,
    include_encode: bool,
    include_roundtrip_canon: bool,
) -> dict[str, Any]:
    """Compute aggregate reconstruction, validity, energy, and timing metrics."""
    n_total = len(results)
    if n_total == 0:
        return {"total_count": 0}

    n_cif = sum(1 for t in tasks if t.get("ori_poscar") is not None)
    encoded_list = [r for r in results if r.get("encoded", True)]
    decoded_list = [r for r in results if r["decoded"]]
    ok_list = [r for r in results if r["ok"]]
    n_encoded = len(encoded_list)
    n_decoded = len(decoded_list)
    n_ok = len(ok_list)

    strict_hits = sum(1 for r in results if r["match_strict"] is True)
    loose_hits = sum(1 for r in results if r["match_loose"] is True)
    sv_hits = sum(1 for r in ok_list if r["struct_valid"] is True)
    sg_hits = sum(1 for r in ok_list if r["sg_match"] is True)
    preopt_hits = sum(1 for r in ok_list if r["preoptimized"] is True)
    retry_structs = sum(1 for r in ok_list if int(r["retry"]) > 0)
    retry_total = sum(int(r["retry"]) for r in ok_list)
    gfnff_inc = sum(1 for r in results if r["gfnff_incomplete"] is True)

    steps_ok = [float(r["relax_steps"]) for r in ok_list]
    secs_all = [float(r["seconds"]) for r in results]

    err_counts = collections.Counter(r["error_type"] for r in results if r["error_type"])
    failure_taxonomy = dict(sorted(err_counts.items(), key=lambda kv: (-kv[1], kv[0])))

    outliers: list[dict[str, Any]] = []
    for t, r in zip(tasks, results, strict=True):
        if r.get("extreme_outlier"):
            outliers.append(
                {
                    "row_index": int(t["row_index"]),
                    "id": t.get("material_id") or t.get("qmof_id") or f"row_{t['row_index']}",
                    "formula": t.get("formula", ""),
                    "n_atoms": int(t["n_atoms"]),
                    "vol_per_atom": _round_opt(r.get("vol_per_atom"), 4),
                    "energy_per_atom": _round_opt(r.get("energy_per_atom"), 4),
                    "eform": _round_opt(r.get("eform"), 4),
                    "abs_err": _round_opt(r.get("abs_err"), 4),
                }
            )

    payload: dict[str, Any] = {
        "total_count": n_total,
        "cif_matched_count": n_cif,
        "encoded_count": n_encoded,
        "failed_encode_count": n_total - n_encoded,
        "decoded_count": n_decoded,
        "ok_count": n_ok,
        "failed_count": n_total - n_ok,
        "failed_decode_count": n_encoded - n_decoded,
        "unrelaxed_fallback_count": n_decoded - n_ok,
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
    }

    if include_roundtrip_canon:
        rt_hits = sum(1 for r in ok_list if r.get("roundtrip_canonical_match") is True)
        payload["roundtrip_canonical_match_count"] = rt_hits
        payload["roundtrip_canonical_match_rate_all"] = _round_opt(rt_hits / n_total)
        payload["roundtrip_canonical_match_rate_ok"] = _round_opt(rt_hits / n_ok) if n_ok else None

    payload.update(
        {
            "preoptimized_count": preopt_hits,
            "preoptimized_rate_ok": _round_opt(preopt_hits / n_ok) if n_ok else None,
            "retry_struct_count": retry_structs,
            "retry_total_count": retry_total,
            "retry_rate_ok": _round_opt(retry_structs / n_ok) if n_ok else None,
            "gfnff_incomplete_count": gfnff_inc,
            "gfnff_incomplete_rate_all": _round_opt(gfnff_inc / n_total),
            "extreme_outlier_count": len(outliers),
            "extreme_outliers": outliers[:20],
        }
    )

    if has_eform:
        raw_abs: list[float] = []
        raw_signed: list[float] = []
        clean_abs: list[float] = []
        clean_signed: list[float] = []
        for t, r in zip(tasks, results, strict=True):
            if r["ok"] and r["eform"] is not None and r["abs_err"] is not None:
                ae = float(r["abs_err"])
                se = float(r["eform"]) - float(t["dft_eform"])
                raw_abs.append(ae)
                raw_signed.append(se)
                if (
                    not r.get("extreme_outlier")
                    and math.isfinite(ae)
                    and ae <= OUTLIER_ABS_ERR_THRESHOLD
                ):
                    clean_abs.append(ae)
                    clean_signed.append(se)
        payload["eform_error_ev_per_atom"] = _aggregate_eform_block(raw_abs, raw_signed, n_total)
        payload["eform_error_finite_reasonable_ev_per_atom"] = {
            "threshold_ev_per_atom": OUTLIER_ABS_ERR_THRESHOLD,
            "excluded_outlier_count": len(raw_abs) - len(clean_abs),
            **_aggregate_eform_block(clean_abs, clean_signed, n_total),
        }

    payload["relax_steps"] = {
        "mean": _round_opt(statistics.mean(steps_ok) if steps_ok else None, 3),
        "median": _round_opt(statistics.median(steps_ok) if steps_ok else None, 3),
        "p90": _round_opt(_percentile(steps_ok, 90.0), 3),
        "p95": _round_opt(_percentile(steps_ok, 95.0), 3),
        "max": int(max(steps_ok)) if steps_ok else None,
        "total": int(sum(steps_ok)) if steps_ok else 0,
    }
    payload["timing_seconds"] = {
        "mean_s": _round_opt(statistics.mean(secs_all), 4),
        "median_s": _round_opt(statistics.median(secs_all), 4),
        "p90_s": _round_opt(_percentile(secs_all, 90.0), 4),
        "p95_s": _round_opt(_percentile(secs_all, 95.0), 4),
        "p99_s": _round_opt(_percentile(secs_all, 99.0), 4),
        "max_s": _round_opt(max(secs_all), 4),
        "sum_s": _round_opt(sum(secs_all), 2),
    }
    payload["stage_timings_seconds"] = _aggregate_stage_timings(
        results, include_encode=include_encode
    )
    payload["failure_taxonomy"] = failure_taxonomy
    return payload


def _breakdown_by_crystal_system(
    tasks: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    has_eform: bool,
) -> dict[str, Any]:
    """Summarize reconstruction and energy metrics stratified by crystal system."""
    present = {str(t.get("crystal_system", "")).lower() for t in tasks if t.get("crystal_system")}
    ordered_cs = [cs for cs in CRYSTAL_SYSTEM_ORDER if cs in present] + sorted(
        present - set(CRYSTAL_SYSTEM_ORDER)
    )
    out: dict[str, Any] = {}
    for cs in ordered_cs:
        pairs = [
            (t, r)
            for t, r in zip(tasks, results, strict=True)
            if str(t.get("crystal_system", "")).lower() == cs
        ]
        agg = _aggregate_subset(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            has_eform=has_eform,
            include_encode=False,
            include_roundtrip_canon=False,
        )
        entry: dict[str, Any] = {
            "total_count": agg["total_count"],
            "ok_count": agg["ok_count"],
            "ok_rate": agg["ok_rate"],
            "match_strict_count": agg["match_strict_count"],
            "match_strict_rate_all": agg["match_strict_rate_all"],
            "match_loose_count": agg["match_loose_count"],
            "match_loose_rate_all": agg["match_loose_rate_all"],
            "sg_match_count": agg["sg_match_count"],
            "sg_match_rate_all": agg["sg_match_rate_all"],
            "mean_seconds": agg["timing_seconds"]["mean_s"],
        }
        if has_eform:
            entry["eform_mae"] = agg["eform_error_ev_per_atom"]["mae"]
            entry["eform_median_ae"] = agg["eform_error_ev_per_atom"]["median_ae"]
            entry["eform_finite_reasonable_mae"] = agg[
                "eform_error_finite_reasonable_ev_per_atom"
            ]["mae"]
        out[cs] = entry
    return out


def _breakdown_by_atom_bins(
    tasks: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    has_eform: bool,
) -> dict[str, Any]:
    """Summarize metrics across 21..40 atom-count bins."""
    out: dict[str, Any] = {}
    for label, lo, hi in ATOM_COUNT_BINS:
        pairs = [
            (t, r)
            for t, r in zip(tasks, results, strict=True)
            if lo <= int(t["n_atoms"]) <= hi
        ]
        if not pairs:
            continue
        agg = _aggregate_subset(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            has_eform=has_eform,
            include_encode=False,
            include_roundtrip_canon=False,
        )
        entry: dict[str, Any] = {
            "atom_range": f"{lo}..{hi}",
            "total_count": agg["total_count"],
            "ok_count": agg["ok_count"],
            "ok_rate": agg["ok_rate"],
            "match_strict_count": agg["match_strict_count"],
            "match_strict_rate_all": agg["match_strict_rate_all"],
            "match_loose_count": agg["match_loose_count"],
            "match_loose_rate_all": agg["match_loose_rate_all"],
            "sg_match_rate_all": agg["sg_match_rate_all"],
            "mean_seconds": agg["timing_seconds"]["mean_s"],
            "mean_relax_steps": agg["relax_steps"]["mean"],
        }
        if has_eform:
            entry["eform_mae"] = agg["eform_error_ev_per_atom"]["mae"]
            entry["eform_median_ae"] = agg["eform_error_ev_per_atom"]["median_ae"]
        out[label] = entry
    return out


def _paired_comparison_from_results(
    tasks: list[dict[str, Any]],
    base_name: str,
    cand_name: str,
    base_wall_s: float,
    cand_wall_s: float,
    base_res: list[dict[str, Any]],
    cand_res: list[dict[str, Any]],
    *,
    has_eform: bool,
) -> dict[str, Any]:
    """Compute paired McNemar and Wilcoxon comparisons between two passes."""
    n_total = len(tasks)
    bool_keys = ["ok", "match_strict", "match_loose", "sg_match", "struct_valid"]
    transitions: dict[str, Any] = {}
    for key in bool_keys:
        both_true = 0
        both_false = 0
        gained: list[str] = []
        lost: list[str] = []
        for t, rb, rc in zip(tasks, base_res, cand_res, strict=True):
            vb = bool(rb.get(key) is True)
            vc = bool(rc.get(key) is True)
            ident = t.get("material_id") or t.get("qmof_id") or f"row_{t['row_index']}"
            if vb and vc:
                both_true += 1
            elif (not vb) and vc:
                gained.append(str(ident))
            elif vb and (not vc):
                lost.append(str(ident))
            else:
                both_false += 1
        b_true = both_true + len(lost)
        c_true = both_true + len(gained)
        transitions[key] = {
            "base_true_count": b_true,
            "cand_true_count": c_true,
            "base_rate_all": _round_opt(b_true / n_total if n_total else None),
            "cand_rate_all": _round_opt(c_true / n_total if n_total else None),
            "both_true": both_true,
            "gained_count": len(gained),
            "lost_count": len(lost),
            "both_false": both_false,
            "net_delta": len(gained) - len(lost),
            "rate_delta_pp": _round_opt(
                ((c_true - b_true) / n_total) * 100.0 if n_total else None, 4
            ),
            "mcnemar_two_sided_p": _round_opt(_mcnemar_exact_pvalue(len(gained), len(lost)), 8),
            "gained_ids_sample": gained[:25],
            "lost_ids_sample": lost[:25],
        }

    sec_deltas = [
        float(rc["seconds"]) - float(rb["seconds"])
        for rb, rc in zip(base_res, cand_res, strict=True)
    ]
    step_deltas = [
        float(rc["relax_steps"]) - float(rb["relax_steps"])
        for rb, rc in zip(base_res, cand_res, strict=True)
        if rb["ok"] and rc["ok"]
    ]

    result: dict[str, Any] = {
        "baseline": base_name,
        "candidate": cand_name,
        "wall_clock": {
            "base_wall_s": _round_opt(base_wall_s, 3),
            "cand_wall_s": _round_opt(cand_wall_s, 3),
            "wall_delta_s": _round_opt(cand_wall_s - base_wall_s, 3),
            "wall_speedup_x": _round_opt(
                base_wall_s / cand_wall_s if cand_wall_s > 0 else None, 4
            ),
        },
        "paired_boolean_transitions": transitions,
        "paired_timing_and_steps": {
            "seconds_delta_mean_s": _round_opt(
                statistics.mean(sec_deltas) if sec_deltas else None, 4
            ),
            "seconds_delta_median_s": _round_opt(
                statistics.median(sec_deltas) if sec_deltas else None, 4
            ),
            "seconds_wilcoxon_two_sided_p": _round_opt(
                _wilcoxon_two_sided_pvalue(sec_deltas), 8
            ),
            "shared_ok_relax_steps_delta_mean": _round_opt(
                statistics.mean(step_deltas) if step_deltas else None, 3
            ),
            "shared_ok_relax_steps_wilcoxon_two_sided_p": _round_opt(
                _wilcoxon_two_sided_pvalue(step_deltas), 8
            ),
        },
    }

    if has_eform:
        raw_err_deltas: list[float] = []
        clean_err_deltas: list[float] = []
        eform_shifts: list[float] = []
        p005: list[tuple[str, bool, bool]] = []
        p010: list[tuple[str, bool, bool]] = []
        for t, rb, rc in zip(tasks, base_res, cand_res, strict=True):
            ident = str(t.get("material_id") or f"row_{t['row_index']}")
            b_err = float(rb["abs_err"]) if (rb["ok"] and rb["abs_err"] is not None) else None
            c_err = float(rc["abs_err"]) if (rc["ok"] and rc["abs_err"] is not None) else None
            p005.append(
                (
                    ident,
                    bool(b_err is not None and b_err <= 0.05),
                    bool(c_err is not None and c_err <= 0.05),
                )
            )
            p010.append(
                (
                    ident,
                    bool(b_err is not None and b_err <= 0.10),
                    bool(c_err is not None and c_err <= 0.10),
                )
            )
            if (
                rb["ok"]
                and rc["ok"]
                and rb["eform"] is not None
                and rc["eform"] is not None
                and b_err is not None
                and c_err is not None
            ):
                d_err = c_err - b_err
                raw_err_deltas.append(d_err)
                shift = abs(float(rc["eform"]) - float(rb["eform"]))
                eform_shifts.append(shift)
                if (
                    math.isfinite(b_err)
                    and math.isfinite(c_err)
                    and b_err <= OUTLIER_ABS_ERR_THRESHOLD
                    and c_err <= OUTLIER_ABS_ERR_THRESHOLD
                ):
                    clean_err_deltas.append(d_err)

        def _thresh_block(pairs: list[tuple[str, bool, bool]]) -> dict[str, Any]:
            bt = sum(1 for _, vb, vc in pairs if vb and vc)
            gain = [i for i, vb, vc in pairs if (not vb) and vc]
            lose = [i for i, vb, vc in pairs if vb and (not vc)]
            bf = sum(1 for _, vb, vc in pairs if (not vb) and (not vc))
            return {
                "base_true_count": bt + len(lose),
                "cand_true_count": bt + len(gain),
                "both_true": bt,
                "gained_count": len(gain),
                "lost_count": len(lose),
                "both_false": bf,
                "net_delta": len(gain) - len(lose),
                "mcnemar_two_sided_p": _round_opt(
                    _mcnemar_exact_pvalue(len(gain), len(lose)), 8
                ),
            }

        result["paired_eform"] = {
            "shared_ok_count": len(raw_err_deltas),
            "shared_finite_reasonable_count": len(clean_err_deltas),
            "abs_eform_shift_median_ev": _round_opt(
                statistics.median(eform_shifts) if eform_shifts else None, 8
            ),
            "abs_eform_shift_p95_ev": _round_opt(
                _percentile([x for x in eform_shifts if math.isfinite(x)], 95.0), 8
            ),
            "abs_err_delta_mean_finite_reasonable": _round_opt(
                statistics.mean(clean_err_deltas) if clean_err_deltas else None, 6
            ),
            "abs_err_delta_median_finite_reasonable": _round_opt(
                statistics.median(clean_err_deltas) if clean_err_deltas else None, 6
            ),
            "wilcoxon_abs_err_raw_two_sided_p": _round_opt(
                _wilcoxon_two_sided_pvalue(raw_err_deltas), 8
            ),
            "wilcoxon_abs_err_finite_reasonable_two_sided_p": _round_opt(
                _wilcoxon_two_sided_pvalue(clean_err_deltas), 8
            ),
            "within_0_05_ev_all": _thresh_block(p005),
            "within_0_10_ev_all": _thresh_block(p010),
        }

    return result


# === Dataset Preparation & Deterministic Stratified Sampling ===


def _load_mp20_reference_cifs(
    mp20_dir: Path,
    needed_keys: set[tuple[str, str, str]],
    needed_round_keys: set[tuple[float, float, str]],
) -> tuple[
    dict[tuple[str, str, str], dict[str, str]],
    dict[tuple[float, float, str], dict[str, str]],
]:
    """Index matching MP-20 reference CIF rows across ``train/val/test.csv``."""
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


def _prepare_mp20_tasks(
    csv_path: Path,
    mp20_dir: Path,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load the 2,383 MP-20 entries and join 1-to-1 with reference CIFs."""
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
                "n_atoms": n_atoms,
                "crystal_system": str(row.get("crystal_system", "")).lower(),
                "ref_sg": ref_sg,
                "dft_eform": float(ef_str),
                "dft_band_gap": float(bg_str),
                "canon_in": canon_in,
                "ekey": ekey,
                "rkey": rkey,
            }
        )

    exact_map, round_map = _load_mp20_reference_cifs(mp20_dir, needed_exact, needed_round)

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


def _hamilton_quotas(counts_by_group: dict[str, int], target_n: int) -> dict[str, int]:
    """Allocate integer stratum sample sizes summing to ``target_n`` proportionally."""
    total = sum(counts_by_group.values())
    if target_n >= total:
        return dict(counts_by_group)
    groups = sorted(counts_by_group)
    exact = {g: target_n * counts_by_group[g] / total for g in groups}
    quotas = {g: int(exact[g]) for g in groups}
    remainder = target_n - sum(quotas.values())
    ranked = sorted(groups, key=lambda g: (-(exact[g] - quotas[g]), g))
    for g in ranked[:remainder]:
        quotas[g] += 1
    return quotas


def _stratified_sample_deterministic(
    items: list[dict[str, Any]],
    target_n: int,
    seed: int,
    id_key: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Draw a version-independent SHA256/RNG stratified sample by ``crystal_system``."""
    by_cs: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for item in items:
        cs = str(item.get("crystal_system", "unknown")).lower()
        by_cs[cs].append(item)

    counts = {cs: len(rows) for cs, rows in by_cs.items()}
    quotas = _hamilton_quotas(counts, min(target_n, len(items)))

    selected: list[dict[str, Any]] = []
    for cs in sorted(quotas):
        q = quotas[cs]
        if q <= 0:
            continue
        group_sorted = sorted(
            by_cs[cs],
            key=lambda r: hashlib.sha256(
                f"{seed}:{cs}:{r[id_key]}".encode()
            ).hexdigest(),
        )
        selected.extend(group_sorted[:q])

    # Keep deterministic ordering by original dataset row order.
    selected.sort(key=lambda r: int(r["source_index"]))
    return selected, quotas


def _prepare_qmof_tasks(
    qmof_json: Path,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Load all 339 QMOF-21-40 CIF entries and precompute reference symmetry/POSCAR."""
    from pymatgen.core.structure import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    with qmof_json.open(encoding="utf-8") as fh:
        raw_items: list[dict[str, str]] = json.load(fh)
    if limit is not None:
        raw_items = raw_items[:limit]

    tasks: list[dict[str, Any]] = []
    for idx, item in enumerate(raw_items):
        qmof_id = item["qmof_id"]
        cif_str = item["cif"]
        with contextlib.redirect_stdout(io.StringIO()):
            ori = Structure.from_str(cif_str, "cif")
        formula = ori.composition.formula.replace(" ", "")
        n_atoms = len(ori)
        ref_sg: int | None = None
        crystal_system = "unknown"
        with contextlib.suppress(Exception):
            sga = SpacegroupAnalyzer(ori)
            ref_sg = int(sga.get_space_group_number())
            crystal_system = str(sga.get_crystal_system()).lower()
        tasks.append(
            {
                "row_index": idx,
                "qmof_id": qmof_id,
                "formula": formula,
                "n_atoms": n_atoms,
                "crystal_system": crystal_system,
                "ref_sg": ref_sg,
                "ori_cif": cif_str,
                "ori_poscar": ori.to(fmt="poscar"),
            }
        )
    return tasks


def _prepare_mp21_40_tasks(
    mp21_40_dir: Path,
    sample_size: int,
    seed: int,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Join MP-21-40 filtered/raw test splits and draw a stratified sample."""
    from pymatgen.core.structure import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    from slices.core import SLICES

    filtered_csv = mp21_40_dir / "filtered" / "test.csv"
    raw_csv = mp21_40_dir / "raw" / "test.csv"
    if not filtered_csv.is_file() or not raw_csv.is_file():
        raise FileNotFoundError(
            f"Expected MP-21-40 CSVs under {mp21_40_dir} "
            "(filtered/test.csv and raw/test.csv)."
        )

    csv.field_size_limit(10**9)
    with filtered_csv.open(encoding="utf-8") as fh:
        filt_rows = list(csv.DictReader(fh))
    with raw_csv.open(encoding="utf-8") as fh:
        raw_map = {row["material_id"]: row for row in csv.DictReader(fh)}

    joined_pool: list[dict[str, Any]] = []
    full_cs_counts: collections.Counter[str] = collections.Counter()
    for src_idx, frow in enumerate(filt_rows):
        mid = frow["material_id"]
        rrow = raw_map.get(mid)
        if rrow is None:
            continue
        cs_norm = str(frow.get("crystal_system") or rrow.get("crystal_system") or "").lower()
        full_cs_counts[cs_norm] += 1
        joined_pool.append(
            {
                "source_index": src_idx,
                "material_id": mid,
                "crystal_system": cs_norm,
                "dft_eform": float(frow["formation_energy_per_atom"]),
                "dft_band_gap": float(frow["band_gap"]),
                "ori_cif": rrow["cif"],
            }
        )

    sampled_rows, quotas = _stratified_sample_deterministic(
        joined_pool,
        target_n=sample_size,
        seed=seed,
        id_key="material_id",
    )
    if limit is not None:
        sampled_rows = sampled_rows[:limit]

    tasks: list[dict[str, Any]] = []
    for idx, item in enumerate(sampled_rows):
        with contextlib.redirect_stdout(io.StringIO()):
            raw_struct = Structure.from_str(item["ori_cif"], "cif")
            ori_prim = SLICES.to_primitive_if_smaller(raw_struct)
        formula = ori_prim.composition.formula.replace(" ", "")
        n_atoms = len(ori_prim)
        ref_sg: int | None = None
        with contextlib.suppress(Exception):
            ref_sg = int(SpacegroupAnalyzer(ori_prim).get_space_group_number())
        tasks.append(
            {
                "row_index": idx,
                "source_index": int(item["source_index"]),
                "material_id": item["material_id"],
                "formula": formula,
                "n_atoms": n_atoms,
                "crystal_system": item["crystal_system"],
                "ref_sg": ref_sg,
                "dft_eform": item["dft_eform"],
                "dft_band_gap": item["dft_band_gap"],
                "ori_cif": item["ori_cif"],
                "ori_poscar": ori_prim.to(fmt="poscar"),
            }
        )

    sample_meta = {
        "full_filtered_test_rows": len(filt_rows),
        "joined_raw_cif_rows": len(joined_pool),
        "requested_sample_size": sample_size,
        "evaluated_rows": len(tasks),
        "sampling_method": "proportional_hamilton_crystal_system_sha256",
        "seed": seed,
        "full_pool_crystal_system_counts": dict(sorted(full_cs_counts.items())),
        "sample_crystal_system_quotas": quotas,
        "sampled_material_ids": [t["material_id"] for t in tasks],
    }
    return tasks, sample_meta


# === CSV & Checkpoint Serialization ===


def _fmt_bool_int(val: bool | None) -> str:
    """Format an optional boolean as ``'1'``, ``'0'``, or ``''``."""
    if val is None:
        return ""
    return "1" if val else "0"


def _save_checkpoint(work_dir: Path, filename: str, payload: dict[str, Any]) -> None:
    """Write a JSON checkpoint atomically inside ``work_dir``."""
    work_dir.mkdir(parents=True, exist_ok=True)
    target = work_dir / filename
    tmp = work_dir / f".tmp_{os.getpid()}_{filename}"
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    tmp.replace(target)


def _load_checkpoint(work_dir: Path | None, filename: str) -> dict[str, Any] | None:
    """Load an existing JSON checkpoint from ``work_dir`` if present."""
    if work_dir is None:
        return None
    target = work_dir / filename
    if not target.is_file():
        return None
    with target.open(encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def _write_mp20_csv(
    out_csv: Path,
    tasks: list[dict[str, Any]],
    model_order: list[str],
    results_by_model: dict[str, list[dict[str, Any]]],
) -> None:
    """Write compact wide-format ``gpu_mp20_per_structure.csv``."""
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
    suffixes = [
        "ok",
        "eform",
        "abs_err",
        "extreme_outlier",
        "match_strict",
        "match_loose",
        "struct_valid",
        "pred_sg",
        "sg_match",
        "roundtrip_canonical_match",
        "preoptimized",
        "retry",
        "relax_steps",
        "relax_s",
        "seconds",
        "error_type",
    ]
    fieldnames = list(meta_cols)
    for mname in model_order:
        prefix = mname.replace("+", "_plus_").replace("-", "_")
        fieldnames.extend(f"{prefix}_{sfx}" for sfx in suffixes)

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
            for mname in model_order:
                prefix = mname.replace("+", "_plus_").replace("-", "_")
                r = results_by_model[mname][idx]
                row_dict[f"{prefix}_ok"] = "1" if r["ok"] else "0"
                row_dict[f"{prefix}_eform"] = (
                    f"{r['eform']:.17g}" if r["eform"] is not None else ""
                )
                row_dict[f"{prefix}_abs_err"] = (
                    f"{r['abs_err']:.8g}" if r["abs_err"] is not None else ""
                )
                row_dict[f"{prefix}_extreme_outlier"] = "1" if r.get("extreme_outlier") else "0"
                row_dict[f"{prefix}_match_strict"] = _fmt_bool_int(r["match_strict"])
                row_dict[f"{prefix}_match_loose"] = _fmt_bool_int(r["match_loose"])
                row_dict[f"{prefix}_struct_valid"] = _fmt_bool_int(r["struct_valid"])
                row_dict[f"{prefix}_pred_sg"] = r["pred_sg"] if r["pred_sg"] is not None else ""
                row_dict[f"{prefix}_sg_match"] = _fmt_bool_int(r["sg_match"])
                row_dict[f"{prefix}_roundtrip_canonical_match"] = _fmt_bool_int(
                    r.get("roundtrip_canonical_match")
                )
                row_dict[f"{prefix}_preoptimized"] = "1" if r["preoptimized"] else "0"
                row_dict[f"{prefix}_retry"] = r["retry"]
                row_dict[f"{prefix}_relax_steps"] = r["relax_steps"]
                row_dict[f"{prefix}_relax_s"] = f"{float(r['relax_s']):.4f}"
                row_dict[f"{prefix}_seconds"] = f"{float(r['seconds']):.4f}"
                row_dict[f"{prefix}_error_type"] = r["error_type"]
            writer.writerow(row_dict)


def _write_roundtrip_csv(
    out_csv: Path,
    tasks: list[dict[str, Any]],
    pass_order: list[str],
    results_by_pass: dict[str, list[dict[str, Any]]],
    *,
    id_col: str,
    has_eform: bool,
    include_source_index: bool = False,
) -> None:
    """Write wide-format per-structure CSV for QMOF-21-40 or MP-21-40."""
    meta_cols = ["row_index"]
    if include_source_index:
        meta_cols.append("source_index")
    meta_cols.extend([id_col, "formula", "n_atoms", "crystal_system", "ref_sg"])
    if has_eform:
        meta_cols.extend(["dft_eform", "dft_band_gap"])

    suffixes = ["encoded", "decoded", "ok"]
    if has_eform:
        suffixes.extend(["eform", "abs_err"])
    else:
        suffixes.append("energy_per_atom")
    suffixes.extend(
        [
            "match_strict",
            "match_loose",
            "struct_valid",
            "pred_sg",
            "sg_match",
            "preoptimized",
            "retry",
            "relax_steps",
            "encode_s",
            "gfnff_s",
            "zl_s",
            "relax_s",
            "seconds",
            "error_type",
        ]
    )

    fieldnames = list(meta_cols)
    for pname in pass_order:
        fieldnames.extend(f"{pname}_{sfx}" for sfx in suffixes)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for idx, task in enumerate(tasks):
            row_dict: dict[str, Any] = {
                "row_index": task["row_index"],
                id_col: task[id_col],
                "formula": task["formula"],
                "n_atoms": task["n_atoms"],
                "crystal_system": task["crystal_system"],
                "ref_sg": task["ref_sg"] if task["ref_sg"] is not None else "",
            }
            if include_source_index:
                row_dict["source_index"] = task["source_index"]
            if has_eform:
                row_dict["dft_eform"] = f"{task['dft_eform']:.17g}"
                row_dict["dft_band_gap"] = f"{task['dft_band_gap']:.8g}"

            for pname in pass_order:
                r = results_by_pass[pname][idx]
                row_dict[f"{pname}_encoded"] = "1" if r.get("encoded", True) else "0"
                row_dict[f"{pname}_decoded"] = "1" if r["decoded"] else "0"
                row_dict[f"{pname}_ok"] = "1" if r["ok"] else "0"
                if has_eform:
                    row_dict[f"{pname}_eform"] = (
                        f"{r['eform']:.17g}" if r["eform"] is not None else ""
                    )
                    row_dict[f"{pname}_abs_err"] = (
                        f"{r['abs_err']:.8g}" if r["abs_err"] is not None else ""
                    )
                else:
                    row_dict[f"{pname}_energy_per_atom"] = (
                        f"{r['energy_per_atom']:.8g}"
                        if r.get("energy_per_atom") is not None
                        else ""
                    )
                row_dict[f"{pname}_match_strict"] = _fmt_bool_int(r["match_strict"])
                row_dict[f"{pname}_match_loose"] = _fmt_bool_int(r["match_loose"])
                row_dict[f"{pname}_struct_valid"] = _fmt_bool_int(r["struct_valid"])
                row_dict[f"{pname}_pred_sg"] = r["pred_sg"] if r["pred_sg"] is not None else ""
                row_dict[f"{pname}_sg_match"] = _fmt_bool_int(r["sg_match"])
                row_dict[f"{pname}_preoptimized"] = "1" if r["preoptimized"] else "0"
                row_dict[f"{pname}_retry"] = r["retry"]
                row_dict[f"{pname}_relax_steps"] = r["relax_steps"]
                row_dict[f"{pname}_encode_s"] = f"{float(r['encode_s']):.4f}"
                row_dict[f"{pname}_gfnff_s"] = f"{float(r['gfnff_s']):.4f}"
                row_dict[f"{pname}_zl_s"] = f"{float(r['zl_s']):.4f}"
                row_dict[f"{pname}_relax_s"] = f"{float(r['relax_s']):.4f}"
                row_dict[f"{pname}_seconds"] = f"{float(r['seconds']):.4f}"
                row_dict[f"{pname}_error_type"] = r["error_type"]
            writer.writerow(row_dict)


# === Suite 1: MP-20 Multi-Model GPU + Stage Breakdown ===


def _load_cpu_v41_baseline(
    cpu_baseline_dir: Path,
    limit: int | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]] | None]:
    """Load archived CPU v4.1 ``default`` summary and per-structure rows."""
    sum_path = cpu_baseline_dir / "summary.json"
    csv_path = cpu_baseline_dir / "per_structure_metrics.csv"
    if not sum_path.is_file() or not csv_path.is_file():
        return None, None
    with sum_path.open(encoding="utf-8") as fh:
        cpu_sum = json.load(fh)
    with csv_path.open(encoding="utf-8", newline="") as fh:
        raw_rows = list(csv.DictReader(fh))
    raw_rows.sort(key=lambda r: int(r["row_index"]))
    if limit is not None:
        raw_rows = raw_rows[:limit]

    converted: list[dict[str, Any]] = []
    for r in raw_rows:
        ok = r["default_ok"] == "1"
        ef = float(r["default_eform"]) if r["default_eform"] != "" else None
        ae = float(r["default_abs_err"]) if r["default_abs_err"] != "" else None
        converted.append(
            {
                "row_index": int(r["row_index"]),
                "ok": ok,
                "eform": ef,
                "abs_err": ae,
                "match_strict": r["default_match_strict"] == "1"
                if r["default_match_strict"] != ""
                else None,
                "match_loose": r["default_match_loose"] == "1"
                if r["default_match_loose"] != ""
                else None,
                "struct_valid": r["default_struct_valid"] == "1"
                if r["default_struct_valid"] != ""
                else None,
                "sg_match": r["default_sg_match"] == "1" if r["default_sg_match"] != "" else None,
                "relax_steps": int(r["default_relax_steps"])
                if r["default_relax_steps"] != ""
                else 0,
                "seconds": float(r["default_seconds"]) if r["default_seconds"] != "" else 0.0,
            }
        )
    return cpu_sum, converted


def _summarize_stage_breakdown_64(
    sample_tasks: list[dict[str, Any]],
    stage_entries: dict[str, dict[str, Any]],
    seed: int,
    quotas: dict[str, int],
) -> dict[str, Any]:
    """Assemble ``stage_breakdown_64`` summary including CPU vs CUDA relax speedups."""
    cpu_ref = stage_entries.get("cpu:nequip-s+l")
    cpu_mean_relax = None
    cpu_mean_total = None
    if cpu_ref is not None:
        cpu_res = cpu_ref["results"]
        cpu_mean_relax = statistics.mean(float(r["relax_s"]) for r in cpu_res)
        cpu_mean_total = statistics.mean(float(r["decode_s"]) for r in cpu_res)

    configs_out: dict[str, Any] = {}
    ordered_keys = [k for k in STAGE_CONFIG_ORDER if k in stage_entries] + [
        k for k in stage_entries if k not in STAGE_CONFIG_ORDER
    ]
    for cfg_key in ordered_keys:
        entry = stage_entries[cfg_key]
        res_list = entry["results"]
        gfnff_vals = [float(r["gfnff_s"]) for r in res_list]
        zl_vals = [float(r["zl_s"]) for r in res_list]
        relax_vals = [float(r["relax_s"]) for r in res_list]
        topo_vals = [float(r["topo_s"]) for r in res_list]
        total_vals = [float(r["decode_s"]) for r in res_list]

        mean_gfnff = statistics.mean(gfnff_vals)
        mean_zl = statistics.mean(zl_vals)
        mean_relax = statistics.mean(relax_vals)
        mean_topo = statistics.mean(topo_vals)
        mean_total = statistics.mean(total_vals)
        denom = mean_total if mean_total > 0 else 1.0

        ok_cnt = sum(1 for r in res_list if r["ok"])
        strict_cnt = sum(1 for r in res_list if r["match_strict"] is True)
        loose_cnt = sum(1 for r in res_list if r["match_loose"] is True)

        configs_out[cfg_key] = {
            "device": entry["spec"]["device"],
            "relax_model": entry["spec"]["relax_model"],
            "resolved_relax_model": entry["run_meta"]["resolved_relax_model"],
            "relaxer_description": entry["run_meta"]["relaxer_description"],
            "workers": 1,
            "wall_seconds": _round_opt(entry["wall_seconds"], 3),
            "ok_count": ok_cnt,
            "match_strict_count": strict_cnt,
            "match_loose_count": loose_cnt,
            "mean_stage_seconds": {
                "gfnff_s": _round_opt(mean_gfnff, 4),
                "zl_s": _round_opt(mean_zl, 4),
                "relax_s": _round_opt(mean_relax, 4),
                "topo_s": _round_opt(mean_topo, 4),
                "total_s": _round_opt(mean_total, 4),
            },
            "median_stage_seconds": {
                "gfnff_s": _round_opt(statistics.median(gfnff_vals), 4),
                "zl_s": _round_opt(statistics.median(zl_vals), 4),
                "relax_s": _round_opt(statistics.median(relax_vals), 4),
                "topo_s": _round_opt(statistics.median(topo_vals), 4),
                "total_s": _round_opt(statistics.median(total_vals), 4),
            },
            "stage_share_pct": {
                "gfnff_pct": _round_opt((mean_gfnff / denom) * 100.0, 2),
                "zl_pct": _round_opt((mean_zl / denom) * 100.0, 2),
                "relax_pct": _round_opt((mean_relax / denom) * 100.0, 2),
                "topo_pct": _round_opt((mean_topo / denom) * 100.0, 2),
            },
            "speedup_vs_cpu_nequip_s_plus_l": {
                "relax_speedup_x": _round_opt(
                    cpu_mean_relax / mean_relax
                    if (cpu_mean_relax is not None and mean_relax > 0)
                    else None,
                    3,
                ),
                "total_decode_speedup_x": _round_opt(
                    cpu_mean_total / mean_total
                    if (cpu_mean_total is not None and mean_total > 0)
                    else None,
                    3,
                ),
            },
            "vram_telemetry": entry["run_meta"]["vram_telemetry"],
        }

    return {
        "sample_size": len(sample_tasks),
        "seed": seed,
        "sampling_method": "proportional_hamilton_crystal_system_sha256",
        "crystal_system_quotas": quotas,
        "mean_atoms": _round_opt(
            statistics.mean(int(t["n_atoms"]) for t in sample_tasks) if sample_tasks else None, 3
        ),
        "sample_row_indices": [int(t["row_index"]) for t in sample_tasks],
        "sample_material_ids": [str(t["material_id"]) for t in sample_tasks],
        "configs": configs_out,
    }


def run_mp20_suite(args: argparse.Namespace) -> None:
    """Execute requested MP-20 GPU model passes + stage breakdown and archive outputs."""
    t_suite0 = time.perf_counter()
    with args.chem_pot.open(encoding="utf-8") as fh:
        chem_pot: dict[str, float] = json.load(fh)

    print("Preparing MP-20 tasks and joining reference CIFs...", flush=True)
    tasks = _prepare_mp20_tasks(args.mp20_csv, args.mp20_dir, limit=args.limit)
    n_cif = sum(1 for t in tasks if t["ori_poscar"] is not None)
    print(f"Loaded {len(tasks)} MP-20 structures (reference CIFs matched: {n_cif}/{len(tasks)}).")

    model_entries: dict[str, dict[str, Any]] = {}
    if args.work_dir is not None:
        for mname in MP20_MODEL_ORDER:
            ckpt = _load_checkpoint(args.work_dir, f"mp20_full_{mname}.json")
            if ckpt is not None and len(ckpt.get("results", [])) == len(tasks):
                model_entries[mname] = ckpt

    requested_models = list(dict.fromkeys(args.models))
    for mname in requested_models:
        spec = RunSpec(
            name=mname,
            mode="decode_slices",
            device="cuda",
            relax_model=mname,
            graph_method="econnn",
            lj_mixing="legacy",
            workers=args.mp20_workers,
            n_gpus=args.n_gpus,
            compute_roundtrip_canon=True,
        )
        res_list, wall_s, run_meta = _run_pool_pass(spec, tasks, chem_pot)
        entry = {
            "spec": asdict(spec),
            "wall_seconds": wall_s,
            "run_meta": run_meta,
            "results": res_list,
        }
        model_entries[mname] = entry
        if args.work_dir is not None:
            _save_checkpoint(args.work_dir, f"mp20_full_{mname}.json", entry)

        agg = _aggregate_subset(
            tasks,
            res_list,
            has_eform=True,
            include_encode=False,
            include_roundtrip_canon=True,
        )
        ef_raw = agg["eform_error_ev_per_atom"]
        ef_clean = agg["eform_error_finite_reasonable_ev_per_atom"]
        s_pct = (agg["match_strict_rate_all"] or 0.0) * 100.0
        l_pct = (agg["match_loose_rate_all"] or 0.0) * 100.0
        print(
            f"[{mname}] DONE in {wall_s:.2f}s | ok {agg['ok_count']}/{agg['total_count']} "
            f"| strict {agg['match_strict_count']} ({s_pct:.2f}%) "
            f"| loose {agg['match_loose_count']} ({l_pct:.2f}%) "
            f"| SG {agg['sg_match_count']} | raw MAE {ef_raw['mae']} "
            f"| clean MAE {ef_clean['mae']} med {ef_clean['median_ae']}\n",
            flush=True,
        )

    # Stratified N=64 single-worker stage breakdown.
    pool_for_64 = [
        {**t, "source_index": int(t["row_index"])}
        for t in tasks
    ]
    sample_64, quotas_64 = _stratified_sample_deterministic(
        pool_for_64,
        target_n=min(args.stage_sample_size, len(tasks)),
        seed=args.seed,
        id_key="row_index",
    )
    stage_tasks: list[dict[str, Any]] = []
    for s_idx, item in enumerate(sample_64):
        copied = dict(item)
        copied["orig_row_index"] = int(item["row_index"])
        copied["row_index"] = s_idx
        stage_tasks.append(copied)

    stage_entries: dict[str, dict[str, Any]] = {}
    if args.work_dir is not None:
        for scfg in STAGE_CONFIG_ORDER:
            safe_key = scfg.replace(":", "_")
            ckpt = _load_checkpoint(args.work_dir, f"mp20_stage64_{safe_key}.json")
            if ckpt is not None and len(ckpt.get("results", [])) == len(stage_tasks):
                stage_entries[scfg] = ckpt

    if not args.skip_stage_breakdown:
        if args.stage_configs is not None:
            wanted_stage_cfgs = list(dict.fromkeys(args.stage_configs))
        else:
            auto_cfgs: list[str] = []
            if "nequip-s+l" in requested_models:
                auto_cfgs.append("cpu:nequip-s+l")
            auto_cfgs.extend(f"cuda:{m}" for m in requested_models)
            wanted_stage_cfgs = auto_cfgs

        for scfg in wanted_stage_cfgs:
            dev_str, mod_str = scfg.split(":", 1)
            stage_spec = RunSpec(
                name=f"stage64_{scfg}",
                mode="decode_slices",
                device=dev_str,
                relax_model=mod_str,
                graph_method="econnn",
                lj_mixing="legacy",
                workers=1,
                n_gpus=args.n_gpus,
                compute_roundtrip_canon=False,
            )
            s_res, s_wall, s_meta = _run_pool_pass(stage_spec, stage_tasks, chem_pot)
            s_entry = {
                "spec": asdict(stage_spec),
                "wall_seconds": s_wall,
                "run_meta": s_meta,
                "results": s_res,
            }
            stage_entries[scfg] = s_entry
            if args.work_dir is not None:
                safe_key = scfg.replace(":", "_")
                _save_checkpoint(args.work_dir, f"mp20_stage64_{safe_key}.json", s_entry)

    ordered_models = [m for m in MP20_MODEL_ORDER if m in model_entries] + [
        m for m in model_entries if m not in MP20_MODEL_ORDER
    ]
    results_by_model = {m: model_entries[m]["results"] for m in ordered_models}

    models_summary: dict[str, Any] = {}
    environments_by_model: dict[str, Any] = {}
    for mname in ordered_models:
        entry = model_entries[mname]
        wall_s = float(entry["wall_seconds"])
        res_list = entry["results"]
        run_meta = entry["run_meta"]
        environments_by_model[mname] = run_meta["runtime_env"]
        models_summary[mname] = {
            "config": {
                "name": mname,
                "device": entry["spec"]["device"],
                "relax_model": entry["spec"]["relax_model"],
                "resolved_relax_model": run_meta["resolved_relax_model"],
                "relaxer_description": run_meta["relaxer_description"],
                "graph_method": entry["spec"]["graph_method"],
                "lj_mixing": entry["spec"]["lj_mixing"],
                "decode_method": "SLICES2structure()",
                "workers": entry["spec"]["workers"],
                "n_gpus": entry["spec"]["n_gpus"],
            },
            "wall_seconds": _round_opt(wall_s, 3),
            "throughput_structures_per_sec": _round_opt(
                len(res_list) / wall_s if wall_s > 0 else None, 4
            ),
            "vram_telemetry": run_meta["vram_telemetry"],
            "all_structures": _aggregate_subset(
                tasks,
                res_list,
                has_eform=True,
                include_encode=False,
                include_roundtrip_canon=True,
            ),
            "by_crystal_system": _breakdown_by_crystal_system(
                tasks, res_list, has_eform=True
            ),
        }

    cpu_sum, cpu_rows = _load_cpu_v41_baseline(args.cpu_baseline_dir, limit=args.limit)
    vs_cpu_v41: dict[str, Any] = {}
    if cpu_sum is not None and cpu_rows is not None and len(cpu_rows) == len(tasks):
        cpu_wall = float(cpu_sum["passes"]["default"]["wall_seconds"])
        for mname in ordered_models:
            vs_cpu_v41[f"cuda_{mname}_vs_cpu_v4_1_nequip_s_plus_l"] = (
                _paired_comparison_from_results(
                    tasks=tasks,
                    base_name="cpu_v4.1:nequip-s+l",
                    cand_name=f"cuda_v4.1:{mname}",
                    base_wall_s=cpu_wall,
                    cand_wall_s=float(model_entries[mname]["wall_seconds"]),
                    base_res=cpu_rows,
                    cand_res=results_by_model[mname],
                    has_eform=True,
                )
            )

    vs_cuda_default: dict[str, Any] = {}
    if "nequip-s+l" in results_by_model:
        base_wall = float(model_entries["nequip-s+l"]["wall_seconds"])
        for mname in ordered_models:
            if mname == "nequip-s+l":
                continue
            vs_cuda_default[f"{mname}_vs_nequip_s_plus_l"] = _paired_comparison_from_results(
                tasks=tasks,
                base_name="cuda:nequip-s+l",
                cand_name=f"cuda:{mname}",
                base_wall_s=base_wall,
                cand_wall_s=float(model_entries[mname]["wall_seconds"]),
                base_res=results_by_model["nequip-s+l"],
                cand_res=results_by_model[mname],
                has_eform=True,
            )

    cpu_ref_meta: dict[str, Any] | None = None
    if cpu_sum is not None:
        cpu_def = cpu_sum["passes"]["default"]
        cpu_all = cpu_def["all_structures"]
        cpu_ref_meta = {
            "archive_dir": _clean_path_label(args.cpu_baseline_dir),
            "wall_seconds": cpu_def["wall_seconds"],
            "workers": cpu_sum["benchmark_metadata"]["environment"]["workers"],
            "ok_count": cpu_all["ok_count"],
            "match_strict_count": cpu_all["match_strict_count"],
            "match_strict_rate_all": cpu_all["match_strict_rate_all"],
            "match_loose_count": cpu_all["match_loose_count"],
            "match_loose_rate_all": cpu_all["match_loose_rate_all"],
            "sg_match_count": cpu_all["sg_match_count"],
            "eform_mae": cpu_all["eform_error_ev_per_atom"]["mae"],
            "eform_median_ae": cpu_all["eform_error_ev_per_atom"]["median_ae"],
        }

    total_full_wall = sum(float(model_entries[m]["wall_seconds"]) for m in ordered_models)
    summary_payload: dict[str, Any] = {
        "benchmark_metadata": {
            "suite": "v4.1-extended-mp20-gpu",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "dataset_csv": _clean_path_label(args.mp20_csv),
            "chem_pot_json": _clean_path_label(args.chem_pot),
            "reference_cif_source": f"{_clean_path_label(args.mp20_dir)}/{{train,val,test}}.csv",
            "total_rows": len(tasks),
            "cif_matched_rows": n_cif,
            "workers": args.mp20_workers,
            "n_gpus": args.n_gpus,
            "gpu_pinning": "CUDA_VISIBLE_DEVICES = worker_id % n_gpus",
            "models_evaluated": ordered_models,
            "sum_full_pass_wall_seconds": _round_opt(total_full_wall, 3),
            "invocation_wall_seconds": _round_opt(time.perf_counter() - t_suite0, 3),
            "cpu_v4_1_reference": cpu_ref_meta,
            "environments_by_model": environments_by_model,
        },
        "models": models_summary,
        "comparisons_vs_cpu_v4_1": vs_cpu_v41,
        "comparisons_vs_cuda_nequip_s_plus_l": vs_cuda_default,
        "stage_breakdown_64": _summarize_stage_breakdown_64(
            sample_64, stage_entries, args.seed, quotas_64
        ),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "gpu_mp20_summary.json"
    out_csv = args.out_dir / "gpu_mp20_per_structure.csv"
    _write_mp20_csv(out_csv, tasks, ordered_models, results_by_model)
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)
        fh.write("\n")

    print(
        f"Saved MP-20 archive: {out_json.name} ({out_json.stat().st_size} B), "
        f"{out_csv.name} ({out_csv.stat().st_size} B).",
        flush=True,
    )


# === Suite 2: Full QMOF-21-40 Benchmark ===


def run_qmof_suite(args: argparse.Namespace) -> None:
    """Execute the 339-MOF QMOF-21-40 GPU benchmark across ``default`` and ``lorentz``."""
    t_suite0 = time.perf_counter()
    print("Preparing QMOF-21-40 tasks...", flush=True)
    tasks = _prepare_qmof_tasks(args.qmof_json, limit=args.limit)
    print(f"Loaded {len(tasks)} QMOF-21-40 structures.")

    pass_order = list(dict.fromkeys(args.passes))
    lj_map = {"default": "legacy", "lorentz": "lorentz"}
    results_by_pass: dict[str, list[dict[str, Any]]] = {}
    passes_summary: dict[str, Any] = {}
    env_info: dict[str, Any] = {}

    for pname in pass_order:
        spec = RunSpec(
            name=pname,
            mode="cif_roundtrip",
            device="cuda",
            relax_model="nequip-s+l",
            graph_method="econnn",
            lj_mixing=lj_map[pname],
            workers=args.qmof_workers,
            n_gpus=args.n_gpus,
            compute_roundtrip_canon=False,
        )
        res_list, wall_s, run_meta = _run_pool_pass(spec, tasks, chem_pot=None)
        results_by_pass[pname] = res_list
        env_info = run_meta["runtime_env"]
        agg = _aggregate_subset(
            tasks,
            res_list,
            has_eform=False,
            include_encode=True,
            include_roundtrip_canon=False,
        )
        strict_rate = agg["match_strict_rate_all"] or 0.0
        loose_rate = agg["match_loose_rate_all"] or 0.0
        passes_summary[pname] = {
            "config": {
                "name": pname,
                "protocol": "CIF -> structure2SLICES(strategy=4, econnn) -> SLICES2structure()",
                "device": spec.device,
                "relax_model": spec.relax_model,
                "resolved_relax_model": run_meta["resolved_relax_model"],
                "relaxer_description": run_meta["relaxer_description"],
                "graph_method": spec.graph_method,
                "lj_mixing": spec.lj_mixing,
                "relax_method": "relax_large_cell1 (21..40 atoms)",
                "workers": spec.workers,
                "n_gpus": spec.n_gpus,
            },
            "wall_seconds": _round_opt(wall_s, 3),
            "throughput_structures_per_sec": _round_opt(
                len(res_list) / wall_s if wall_s > 0 else None, 4
            ),
            "vram_telemetry": run_meta["vram_telemetry"],
            "all_structures": agg,
            "by_crystal_system": _breakdown_by_crystal_system(
                tasks, res_list, has_eform=False
            ),
            "by_atom_count_bin": _breakdown_by_atom_bins(tasks, res_list, has_eform=False),
            "vs_upstream_table_s1": {
                "upstream_strict_rate": UPSTREAM_TABLE_S1_QMOF["strict_rate"],
                "upstream_loose_rate": UPSTREAM_TABLE_S1_QMOF["loose_rate"],
                "strict_rate_delta_pp": _round_opt(
                    (strict_rate - UPSTREAM_TABLE_S1_QMOF["strict_rate"]) * 100.0, 2
                ),
                "loose_rate_delta_pp": _round_opt(
                    (loose_rate - UPSTREAM_TABLE_S1_QMOF["loose_rate"]) * 100.0, 2
                ),
                "strict_fold_improvement_x": _round_opt(
                    strict_rate / UPSTREAM_TABLE_S1_QMOF["strict_rate"]
                    if UPSTREAM_TABLE_S1_QMOF["strict_rate"] > 0
                    else None,
                    3,
                ),
                "loose_fold_improvement_x": _round_opt(
                    loose_rate / UPSTREAM_TABLE_S1_QMOF["loose_rate"]
                    if UPSTREAM_TABLE_S1_QMOF["loose_rate"] > 0
                    else None,
                    3,
                ),
            },
        }
        print(
            f"[qmof:{pname}] DONE in {wall_s:.2f}s | ok {agg['ok_count']}/{agg['total_count']} "
            f"| strict {agg['match_strict_count']} ({strict_rate*100:.2f}%) "
            f"| loose {agg['match_loose_count']} ({loose_rate*100:.2f}%) "
            f"| SG {agg['sg_match_count']}\n",
            flush=True,
        )

    paired: dict[str, Any] = {}
    if "default" in results_by_pass and "lorentz" in results_by_pass:
        paired["lorentz_vs_default"] = _paired_comparison_from_results(
            tasks=tasks,
            base_name="default",
            cand_name="lorentz",
            base_wall_s=float(passes_summary["default"]["wall_seconds"]),
            cand_wall_s=float(passes_summary["lorentz"]["wall_seconds"]),
            base_res=results_by_pass["default"],
            cand_res=results_by_pass["lorentz"],
            has_eform=False,
        )

    atom_counts = [int(t["n_atoms"]) for t in tasks]
    summary_payload: dict[str, Any] = {
        "benchmark_metadata": {
            "suite": "v4.1-extended-qmof-21-40",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "dataset_json": _clean_path_label(args.qmof_json),
            "total_rows": len(tasks),
            "atom_count_min": min(atom_counts) if atom_counts else None,
            "atom_count_max": max(atom_counts) if atom_counts else None,
            "atom_count_mean": _round_opt(
                statistics.mean(atom_counts) if atom_counts else None, 3
            ),
            "graph_method": "econnn",
            "workers": args.qmof_workers,
            "n_gpus": args.n_gpus,
            "gpu_pinning": "CUDA_VISIBLE_DEVICES = worker_id % n_gpus",
            "total_wall_seconds": _round_opt(time.perf_counter() - t_suite0, 3),
            "upstream_table_s1_baseline": UPSTREAM_TABLE_S1_QMOF,
            "environment": env_info,
        },
        "passes": passes_summary,
        "paired_comparisons": paired,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "qmof_21_40_summary.json"
    out_csv = args.out_dir / "qmof_21_40_per_structure.csv"
    _write_roundtrip_csv(
        out_csv,
        tasks,
        pass_order,
        results_by_pass,
        id_col="qmof_id",
        has_eform=False,
        include_source_index=False,
    )
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)
        fh.write("\n")

    print(
        f"Saved QMOF-21-40 archive: {out_json.name} ({out_json.stat().st_size} B), "
        f"{out_csv.name} ({out_csv.stat().st_size} B).",
        flush=True,
    )


# === Suite 3: Stratified MP-21-40 Benchmark ===


def run_mp21_40_suite(args: argparse.Namespace) -> None:
    """Execute the stratified 1,000-crystal MP-21-40 GPU benchmark."""
    t_suite0 = time.perf_counter()
    with args.chem_pot.open(encoding="utf-8") as fh:
        chem_pot: dict[str, float] = json.load(fh)

    print("Preparing stratified MP-21-40 tasks...", flush=True)
    tasks, sample_meta = _prepare_mp21_40_tasks(
        args.mp21_40_dir,
        sample_size=args.mp21_40_sample_size,
        seed=args.seed,
        limit=args.limit,
    )
    print(
        f"Selected {len(tasks)} stratified MP-21-40 crystals "
        f"from {sample_meta['joined_raw_cif_rows']} held-out test entries "
        f"(quotas={sample_meta['sample_crystal_system_quotas']}).",
        flush=True,
    )

    pass_order = list(dict.fromkeys(args.passes))
    lj_map = {"default": "legacy", "lorentz": "lorentz"}
    results_by_pass: dict[str, list[dict[str, Any]]] = {}
    passes_summary: dict[str, Any] = {}
    env_info: dict[str, Any] = {}

    for pname in pass_order:
        spec = RunSpec(
            name=pname,
            mode="cif_roundtrip",
            device="cuda",
            relax_model="nequip-s+l",
            graph_method="crystalnn",
            lj_mixing=lj_map[pname],
            workers=args.mp21_40_workers,
            n_gpus=args.n_gpus,
            compute_roundtrip_canon=False,
        )
        res_list, wall_s, run_meta = _run_pool_pass(spec, tasks, chem_pot=chem_pot)
        results_by_pass[pname] = res_list
        env_info = run_meta["runtime_env"]
        agg = _aggregate_subset(
            tasks,
            res_list,
            has_eform=True,
            include_encode=True,
            include_roundtrip_canon=False,
        )
        strict_rate = agg["match_strict_rate_all"] or 0.0
        loose_rate = agg["match_loose_rate_all"] or 0.0
        ef_agg = agg["eform_error_ev_per_atom"]
        passes_summary[pname] = {
            "config": {
                "name": pname,
                "protocol": "CIF -> structure2SLICES(strategy=4, crystalnn) -> SLICES2structure()",
                "device": spec.device,
                "relax_model": spec.relax_model,
                "resolved_relax_model": run_meta["resolved_relax_model"],
                "relaxer_description": run_meta["relaxer_description"],
                "graph_method": spec.graph_method,
                "lj_mixing": spec.lj_mixing,
                "relax_method": "relax_large_cell1 (21..40 atoms)",
                "workers": spec.workers,
                "n_gpus": spec.n_gpus,
            },
            "wall_seconds": _round_opt(wall_s, 3),
            "throughput_structures_per_sec": _round_opt(
                len(res_list) / wall_s if wall_s > 0 else None, 4
            ),
            "vram_telemetry": run_meta["vram_telemetry"],
            "all_structures": agg,
            "by_crystal_system": _breakdown_by_crystal_system(
                tasks, res_list, has_eform=True
            ),
            "by_atom_count_bin": _breakdown_by_atom_bins(tasks, res_list, has_eform=True),
            "vs_upstream_table_s1": {
                "upstream_strict_rate": UPSTREAM_TABLE_S1_MP21_40["strict_rate"],
                "upstream_loose_rate": UPSTREAM_TABLE_S1_MP21_40["loose_rate"],
                "strict_rate_delta_pp": _round_opt(
                    (strict_rate - UPSTREAM_TABLE_S1_MP21_40["strict_rate"]) * 100.0, 2
                ),
                "loose_rate_delta_pp": _round_opt(
                    (loose_rate - UPSTREAM_TABLE_S1_MP21_40["loose_rate"]) * 100.0, 2
                ),
            },
        }
        print(
            f"[mp21-40:{pname}] DONE in {wall_s:.2f}s | ok {agg['ok_count']}/{agg['total_count']} "
            f"| strict {agg['match_strict_count']} ({strict_rate*100:.2f}%) "
            f"| loose {agg['match_loose_count']} ({loose_rate*100:.2f}%) "
            f"| SG {agg['sg_match_count']} | MAE {ef_agg['mae']} med {ef_agg['median_ae']}\n",
            flush=True,
        )

    paired: dict[str, Any] = {}
    if "default" in results_by_pass and "lorentz" in results_by_pass:
        paired["lorentz_vs_default"] = _paired_comparison_from_results(
            tasks=tasks,
            base_name="default",
            cand_name="lorentz",
            base_wall_s=float(passes_summary["default"]["wall_seconds"]),
            cand_wall_s=float(passes_summary["lorentz"]["wall_seconds"]),
            base_res=results_by_pass["default"],
            cand_res=results_by_pass["lorentz"],
            has_eform=True,
        )

    atom_counts = [int(t["n_atoms"]) for t in tasks]
    dir_label = _clean_path_label(args.mp21_40_dir)
    summary_payload: dict[str, Any] = {
        "benchmark_metadata": {
            "suite": "v4.1-extended-mp-21-40",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "filtered_test_csv": f"{dir_label}/filtered/test.csv",
            "raw_test_csv": f"{dir_label}/raw/test.csv",
            "chem_pot_json": _clean_path_label(args.chem_pot),
            "total_rows": len(tasks),
            "atom_count_min": min(atom_counts) if atom_counts else None,
            "atom_count_max": max(atom_counts) if atom_counts else None,
            "atom_count_mean": _round_opt(
                statistics.mean(atom_counts) if atom_counts else None, 3
            ),
            "graph_method": "crystalnn",
            "workers": args.mp21_40_workers,
            "n_gpus": args.n_gpus,
            "gpu_pinning": "CUDA_VISIBLE_DEVICES = worker_id % n_gpus",
            "total_wall_seconds": _round_opt(time.perf_counter() - t_suite0, 3),
            "upstream_table_s1_baseline": UPSTREAM_TABLE_S1_MP21_40,
            "sampling": sample_meta,
            "environment": env_info,
        },
        "passes": passes_summary,
        "paired_comparisons": paired,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_json = args.out_dir / "mp21_40_summary.json"
    out_csv = args.out_dir / "mp21_40_per_structure.csv"
    _write_roundtrip_csv(
        out_csv,
        tasks,
        pass_order,
        results_by_pass,
        id_col="material_id",
        has_eform=True,
        include_source_index=True,
    )
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(summary_payload, fh, indent=2)
        fh.write("\n")

    print(
        f"Saved MP-21-40 archive: {out_json.name} ({out_json.stat().st_size} B), "
        f"{out_csv.name} ({out_csv.stat().st_size} B).",
        flush=True,
    )


# === CLI Entrypoint ===


def build_parser() -> argparse.ArgumentParser:
    """Construct the command-line parser for all three GPU benchmark suites."""
    parser = argparse.ArgumentParser(
        description=(
            "Run SLICES v4.1 extended GPU benchmarks on MP-20, QMOF-21-40, and MP-21-40."
        )
    )
    parser.add_argument(
        "--suite",
        choices=("mp20", "qmof", "mp21-40", "all"),
        default="all",
        help="benchmark suite to execute (default: all)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="output directory for summary JSON and per-structure CSV files",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="optional scratch checkpoint directory for multi-env MP-20 model merging",
    )
    parser.add_argument(
        "--mp20-csv",
        type=Path,
        default=DEFAULT_MP20_CSV,
        help="path to mp20_v4_benchmark_2383.csv",
    )
    parser.add_argument(
        "--mp20-dir",
        type=Path,
        default=DEFAULT_MP20_DIR,
        help="directory containing MP-20 train/val/test.csv reference CIFs",
    )
    parser.add_argument(
        "--chem-pot",
        type=Path,
        default=DEFAULT_CHEM_POT,
        help="path to chemPotMP.json elemental chemical potentials",
    )
    parser.add_argument(
        "--cpu-baseline-dir",
        type=Path,
        default=DEFAULT_CPU_BASELINE_DIR,
        help="directory containing archived CPU v4.1 summary.json and per_structure_metrics.csv",
    )
    parser.add_argument(
        "--qmof-json",
        type=Path,
        default=DEFAULT_QMOF_JSON,
        help="path to QMOF-21-40 cifs_filtered.json (339 MOFs)",
    )
    parser.add_argument(
        "--mp21-40-dir",
        type=Path,
        default=DEFAULT_MP21_40_DIR,
        help="directory containing MP-21-40 filtered/test.csv and raw/test.csv",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(MP20_MODEL_ORDER),
        help="MP-20 GPU models to run in this invocation",
    )
    parser.add_argument(
        "--stage-configs",
        nargs="*",
        default=None,
        help="optional explicit stage_breakdown_64 specs (e.g. cpu:nequip-s+l cuda:nequip-s+l)",
    )
    parser.add_argument(
        "--skip-stage-breakdown",
        action="store_true",
        help="skip the single-worker MP-20 stage breakdown pass",
    )
    parser.add_argument(
        "--stage-sample-size",
        type=int,
        default=64,
        help="stratified sample size for MP-20 stage breakdown (default: 64)",
    )
    parser.add_argument(
        "--mp21-40-sample-size",
        type=int,
        default=1000,
        help="stratified sample size for MP-21-40 test split (default: 1000)",
    )
    parser.add_argument(
        "--passes",
        nargs="+",
        choices=PAIRED_PASS_ORDER,
        default=list(PAIRED_PASS_ORDER),
        help="paired LJ-mixing passes for QMOF-21-40 and MP-21-40 (default: default lorentz)",
    )
    parser.add_argument(
        "--mp20-workers",
        type=int,
        default=24,
        help="worker count for MP-20 GPU runs (default: 24)",
    )
    parser.add_argument(
        "--qmof-workers",
        type=int,
        default=24,
        help="worker count for QMOF-21-40 GPU runs (default: 24)",
    )
    parser.add_argument(
        "--mp21-40-workers",
        type=int,
        default=28,
        help="worker count for MP-21-40 GPU runs (default: 28)",
    )
    parser.add_argument(
        "--n-gpus",
        type=int,
        default=2,
        help="number of CUDA GPUs for worker_id %% n_gpus assignment (default: 2)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="deterministic seed for stratified sampling (default: 0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="optional row limit for smoke validation",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments and run the selected extended benchmark suite(s).

    Args:
        argv: Optional sequence of CLI arguments.

    Returns:
        Exit code ``0`` on completion.
    """
    _ = random.Random(0)  # Keep deterministic stdlib import active if needed.
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_single_thread_env()

    if args.suite in ("mp20", "all"):
        run_mp20_suite(args)
    if args.suite in ("qmof", "all"):
        run_qmof_suite(args)
    if args.suite in ("mp21-40", "all"):
        run_mp21_40_suite(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
