"""Force fields for the final relaxation step of SLICES crystal decoding.

``SLICES(relax_model=...)`` accepts the default NequIP plans:

* ``"auto"`` (default): ``"nequip-s+l"`` on every machine (or ``SLICES_RELAX_MODEL`` if set).
* ``"nequip-s+l"`` / ``"nequip-m+l"``: relax with NequIP-OAM-S / -M, energy from NequIP-OAM-L.
* ``"nequip-l"``: relax with NequIP-OAM-L (practical primarily on a GPU).
* ``None`` or ``"none"``: no relaxer.

Additional optional MLIP adapters (``"chgnet"``, ``"mattersim"``, ``"orbv3"``, ``"mace"``,
``"m3gnet"``) are delegated lazily to ``slices.mlip_relaxer`` when explicitly requested.

All NequIP variants report the NequIP-OAM-L energy. Models run on the CPU unless
``SLICES_DEVICE=cuda``. On the 2,383 MP-20 benchmark structures (CPU), ``nequip-s+l``
reproduced 93.8% of the reference structures (legacy M3GNet pipeline: 88.7%);
``nequip-m+l`` reached 94.8% at roughly twice the CPU time. Because most decode time is
spent on CPU-side GFN-FF and ZL* lattice optimization, GPU decoding is opt-in.

Environment variables:

* ``SLICES_RELAX_MODEL``: used when ``relax_model="auto"``, e.g. ``nequip-m+l``.
* ``SLICES_DEVICE``: ``cpu`` (default) or ``cuda``. GPU runs compile models with
  AOTInductor when ``CUDA_HOME`` is available; without it they fall back to TorchScript.
  ``uv sync --extra oeq`` enables optional OpenEquivariance GPU kernels.
* ``SLICES_MODEL_CACHE``: directory for compiled NequIP models (default ``~/.cache/slices/nequip``).
* ``SLICES_TORCH_THREADS``: PyTorch CPU threads per process (default ``OMP_NUM_THREADS`` or ``1``).
* ``SLICES_NEQUIP_TF32``: ``1`` compiles GPU models with TF32.
* ``SLICES_NEQUIP_MODEL_S`` / ``_M`` / ``_L``: pre-compiled model file (``.nequip.pth`` or
  ``.nequip.pt2``) or local ``.nequip.zip`` archive to compile instead of downloading.

Run ``python -m slices.relax_backends --prepare`` once before launching parallel workers.
"""

from __future__ import annotations

import contextlib
import importlib.util
import os
import re
import subprocess
import sys
import time
import types
import warnings
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

from slices.exceptions import ModelDownloadError, RelaxBackendError

if TYPE_CHECKING:
    import numpy as np
    from ase import Atoms
    from pymatgen.core import Structure

__all__ = [
    "COLLAPSE_VOLUME",
    "DOWNLOAD_RETRY_WAITS",
    "DOWNLOAD_TIMEOUT",
    "FIRE_PRESTEPS",
    "NEQUIP_MODEL_IDS",
    "NEQUIP_OAM_ATOMIC_NUMBERS",
    "NEQUIP_PLANS",
    "OPTIMIZERS",
    "OVERLAP_TARGET",
    "OVERLAP_TRIGGER",
    "RELAX_MODELS",
    "CellCollapse",
    "ModelDownloadError",
    "NequIPRelaxer",
    "RelaxBackendError",
    "choose_device",
    "closest_pair_ratio",
    "get_calculator",
    "make_relaxer",
    "nequip_available",
    "preoptimize",
    "remove_overlaps",
    "resolve_relax_model",
]

NEQUIP_MODEL_IDS: dict[str, str] = {
    "S": "mir-group/NequIP-OAM-S:0.1",
    "M": "mir-group/NequIP-OAM-M:0.1",
    "L": "mir-group/NequIP-OAM-L:0.1",
}
# Exact 89-element OAM vocabulary {1..83, 89..94} (H-Bi and Ac-Pu; excludes Po-Ra and Am-Og).
NEQUIP_OAM_ATOMIC_NUMBERS: frozenset[int] = frozenset(range(1, 84)) | frozenset(range(89, 95))
# relax_model -> (model used for relaxation, model used for the final energy or None)
NEQUIP_PLANS: dict[str, tuple[str, str | None]] = {
    "nequip-l": ("L", None),
    "nequip-s+l": ("S", "L"),
    "nequip-m+l": ("M", "L"),
}
RELAX_MODELS: tuple[str, ...] = ("auto", "none", *NEQUIP_PLANS)
OPTIMIZERS: tuple[str, ...] = ("BFGS", "LBFGS", "FIRE", "FIRE+BFGS")
FIRE_PRESTEPS: int = 10  # FIRE steps before switching to BFGS in "FIRE+BFGS"

_CALCULATORS: dict[tuple[str, str], tuple[Any, str]] = {}
_ANNOUNCED: set[str] = set()


def _log(msg: str) -> None:
    """Write a status message prefixed with ``[SLICES relax]`` to stderr."""
    print(f"[SLICES relax] {msg}", file=sys.stderr, flush=True)


def _announce(msg: str) -> None:
    """Emit ``msg`` to stderr at most once per process."""
    if msg not in _ANNOUNCED:
        _ANNOUNCED.add(msg)
        _log(msg)


def nequip_available() -> bool:
    """Return ``True`` if both ``torch`` and ``nequip`` are importable."""
    return (
        importlib.util.find_spec("torch") is not None
        and importlib.util.find_spec("nequip") is not None
    )


def _nequip_install_hint() -> str:
    """Return user-facing installation hint for missing NequIP dependencies."""
    return "set up the environment with `uv sync --extra cpu` (or cu126 / cu128), see README"


def choose_device() -> str:
    """Resolve ``SLICES_DEVICE`` (``cpu`` or ``cuda``), defaulting to ``cpu``.

    Returns:
        Resolved device string (``"cpu"`` or ``"cuda"``).

    Raises:
        ValueError: If ``SLICES_DEVICE`` is set to an unsupported value.
    """
    device = os.environ.get("SLICES_DEVICE", "").strip().lower() or "cpu"
    if device not in ("cpu", "cuda"):
        raise ValueError(f"SLICES_DEVICE must be 'cpu' or 'cuda', got {device!r}")
    if device == "cuda":
        import torch

        if not torch.cuda.is_available():
            _announce("SLICES_DEVICE=cuda but torch sees no CUDA GPU; using the CPU")
            return "cpu"
    return device


def resolve_relax_model(relax_model: str | None) -> tuple[str, str | None]:
    """Resolve ``relax_model`` into ``(canonical_name, device)``.

    Args:
        relax_model: Requested relaxer identifier (e.g., ``"auto"``, ``"nequip-s+l"``,
            ``None``, ``"none"``, or an optional MLIP name such as ``"chgnet"``).

    Returns:
        Tuple ``(name, device)`` where ``device`` is ``None`` when ``name == "none"``.

    Raises:
        ValueError: If ``relax_model`` is unknown.
        ImportError: If the required force-field package is not installed.
    """
    if relax_model is None:
        return "none", None
    name = str(relax_model).strip().lower()
    if name == "auto":
        name = os.environ.get("SLICES_RELAX_MODEL", "auto").strip().lower() or "auto"
    if name not in RELAX_MODELS:
        try:
            from slices.mlip_relaxer import resolve_optional_mlip
        except ModuleNotFoundError:
            raise ValueError(
                f"Unknown relax_model {relax_model!r}; choose from {RELAX_MODELS}"
            ) from None
        return resolve_optional_mlip(name)
    if name == "auto":
        name = "nequip-s+l"
    if name in NEQUIP_PLANS:
        if not nequip_available():
            raise ImportError(
                f"relax_model={name!r} needs torch and nequip ({_nequip_install_hint()})"
            )
        return name, choose_device()
    return name, None


def make_relaxer(
    relax_model: str | None = "auto",
    optimizer: str = "BFGS",
) -> tuple[Any, str]:
    """Instantiate the structure relaxer for ``relax_model``.

    Args:
        relax_model: Requested force-field model identifier or ``None``.
        optimizer: Local optimizer name (default ``"BFGS"``).

    Returns:
        Tuple ``(relaxer_or_none, resolved_model_name)``.
    """
    name, device = resolve_relax_model(relax_model)
    if name == "none":
        return None, "none"
    if name not in NEQUIP_PLANS:
        from slices.mlip_relaxer import make_optional_relaxer

        relaxer = make_optional_relaxer(name, device=device, optimizer=optimizer)
        _announce(f"relax_model={name} on {relaxer.device} ({relaxer.description})")
        return relaxer, name
    assert device is not None
    try:
        relaxer = NequIPRelaxer(name, device, optimizer)
    except Exception as exc:
        if device != "cuda":
            raise
        _announce(
            f"GPU setup failed ({type(exc).__name__}: {exc}); falling back to CPU nequip-s+l"
        )
        name, device = "nequip-s+l", "cpu"
        relaxer = NequIPRelaxer(name, device, optimizer)
    _announce(f"relax_model={name} on {device} ({relaxer.description})")
    return relaxer, name


# === NequIP Compilation & Caching ===


def _cache_dir() -> str:
    """Return (and create if needed) the compiled NequIP model cache directory."""
    path = os.environ.get("SLICES_MODEL_CACHE") or os.path.join(
        os.path.expanduser("~"), ".cache", "slices", "nequip"
    )
    os.makedirs(path, exist_ok=True)
    return path


def _tf32() -> bool:
    """Return ``True`` if ``SLICES_NEQUIP_TF32`` is enabled."""
    return os.environ.get("SLICES_NEQUIP_TF32", "").strip().lower() in ("1", "true", "yes")


def _compile_tiers(device: str) -> list[tuple[str, bool]]:
    """Return ordered ``(mode, use_openequivariance)`` compilation attempts for ``device``."""
    if device == "cpu":
        # On CPU, TorchScript was 3-4x faster than AOTInductor in workstation benchmarks.
        return [("torchscript", False)]
    tiers: list[tuple[str, bool]] = []
    if importlib.util.find_spec("openequivariance") is not None:
        tiers.append(("aotinductor", True))
    tiers += [("aotinductor", False), ("torchscript", False)]
    return tiers


def _compiled_name(size: str, device: str, mode: str, oeq: bool) -> str:
    """Build hardware- and version-tagged cache filename for a compiled NequIP model."""
    import nequip
    import torch

    parts = [f"NequIP-OAM-{size}-0.1", mode + ("-oeq" if oeq else ""), device]
    if device == "cuda":
        gpu = re.sub(r"[^A-Za-z0-9]+", "-", torch.cuda.get_device_name(0)).strip("-")
        major, minor = torch.cuda.get_device_capability(0)
        parts += [gpu, f"sm{major}{minor}", f"cu{torch.version.cuda}"] + (
            ["tf32"] if _tf32() else []
        )
    parts += [f"torch{torch.__version__.split('+')[0]}", f"nequip{nequip.__version__}"]
    ext = ".nequip.pth" if mode == "torchscript" else ".nequip.pt2"
    return "__".join(parts) + ext


def _model_source(size: str) -> str:
    """Return local archive path or remote identifier for ``NequIP-OAM-<size>``."""
    override = os.environ.get(f"SLICES_NEQUIP_MODEL_{size}")
    if override:
        return override
    try:
        return _download_model(size)
    except ImportError:  # nequip internals moved: let nequip-compile fetch the model itself
        return "nequip.net:" + NEQUIP_MODEL_IDS[size]


# Waits (s) before the 2nd, 3rd and 4th download attempt. The weights come from nequip.net
# (which redirects to Zenodo); international connections can stall mid-download.
DOWNLOAD_RETRY_WAITS: tuple[int, ...] = (5, 15, 30)
DOWNLOAD_TIMEOUT: tuple[int, int] = (30, 120)  # (connect, read) seconds


def _download_model(size: str) -> str:
    """Download ``NequIP-OAM-<size>`` into nequip's cache with timeouts and retries.

    Uses the same cache directory as ``nequip`` (``~/.nequip/model_cache`` or
    ``NEQUIP_CACHE_DIR``) with completeness verification and exponential retry waits.

    Args:
        size: Model size key (``"S"``, ``"M"``, or ``"L"``).

    Returns:
        Filesystem path to the cached ``.nequip.zip`` model package.

    Raises:
        ModelDownloadError: If all download attempts fail due to network errors.
    """
    import functools

    import lightning.fabric.utilities.rank_zero  # noqa: F401
    import requests
    from nequip.utils.model_cache import cache_model, get_cached_model
    from nequip.utils.model_repository import ModelNotFoundError, NequIPNetAPIClient
    from tqdm import tqdm

    model_id = NEQUIP_MODEL_IDS[size]

    def fetch(target: str | os.PathLike[str]) -> None:
        assert url is not None
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            with (
                open(target, "wb") as fh,
                tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc=f"Downloading NequIP-OAM-{size}",
                ) as bar,
            ):
                for chunk in response.iter_content(chunk_size=1 << 16):
                    fh.write(chunk)
                    bar.update(len(chunk))
        if total and os.path.getsize(target) != total:
            raise requests.exceptions.ConnectionError(
                f"download ended early ({os.path.getsize(target)} of {total} bytes)"
            )

    url: str | None = None
    last_error: Exception | None = None
    for attempt in range(len(DOWNLOAD_RETRY_WAITS) + 1):
        if attempt:
            wait = DOWNLOAD_RETRY_WAITS[attempt - 1]
            _log(
                f"downloading NequIP-OAM-{size} failed ({_short_error(last_error)}); "
                f"retry {attempt}/{len(DOWNLOAD_RETRY_WAITS)} in {wait} s"
            )
            time.sleep(wait)
        try:
            with NequIPNetAPIClient() as client:
                client.session.get = functools.partial(
                    client.session.get, timeout=DOWNLOAD_TIMEOUT
                )
                url = client.get_model_download_info(model_id).artifact.download_url
            cached = get_cached_model(model_id, url)
            return str(cached if cached is not None else cache_model(model_id, url, fetch))
        except ModelNotFoundError:
            raise
        except requests.exceptions.RequestException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and 400 <= status < 500 and status != 429:
                raise  # e.g. 404: retrying cannot help
            last_error = exc
    where = url or f"https://nequip.net (model {model_id})"
    raise ModelDownloadError(
        f"Could not download the NequIP-OAM-{size} weights after "
        f"{len(DOWNLOAD_RETRY_WAITS) + 1} attempts "
        f"(network problem: {_short_error(last_error)}).\n"
        "Please verify network connectivity and re-run (automatic retry is enabled), "
        f"or download {where} in a browser and set "
        f"SLICES_NEQUIP_MODEL_{size}=/path/to/that/file.zip"
    )


def _short_error(exc: Exception | None) -> str:
    """Format a single-line summary for a nested ``requests`` / ``urllib3`` exception."""
    if exc is None:
        return "unknown error"
    name, text = type(exc).__name__, str(exc)
    for marker in (
        "SSLError",
        "ConnectTimeout",
        "ReadTimeout",
        "NewConnectionError",
        "RemoteDisconnected",
    ):
        if marker in text:
            return name if marker == name else f"{name}: {marker}"
    return f"{name}: {text.splitlines()[0][:120]}" if text else name


def _compile(source: str, out_path: str, device: str, mode: str, oeq: bool) -> None:
    """Compile a NequIP model package to ``out_path`` atomically via subprocess."""
    tmp = os.path.join(
        os.path.dirname(out_path), f".tmp{os.getpid()}-{os.path.basename(out_path)}"
    )
    cmd = [
        sys.executable,
        "-m",
        "nequip.scripts.compile",
        source,
        tmp,
        "--mode",
        mode,
        "--device",
        device,
    ]
    if mode == "aotinductor":
        # Default shape bounds start at 2 atoms; primitive elemental cells can have 1.
        cmd += ["--target", "ase", "--num-nodes", "1,inf"]
    if oeq:
        cmd += ["--modifiers", "enable_OpenEquivariance"]
    if device == "cuda" and _tf32():
        cmd += ["--tf32"]
    t0 = time.time()
    proc = subprocess.run(
        cmd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0 or not os.path.exists(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RelaxBackendError(
            f"nequip-compile failed ({mode}{', OpenEquivariance' if oeq else ''}):\n"
            + proc.stdout[-3000:]
        )
    os.replace(tmp, out_path)
    _log(f"compiled {os.path.basename(out_path)} in {time.time() - t0:.0f} s")


def _self_test(calc: Any) -> None:
    """Run a single-point diamond-Si sanity check on a compiled ASE calculator."""
    import math

    from ase.build import bulk

    atoms = bulk("Si", "diamond", a=5.43)
    atoms.calc = calc
    energy = atoms.get_potential_energy()
    atoms.get_forces()
    atoms.get_stress()
    if math.isnan(float(energy)):
        raise RelaxBackendError("model returned NaN energy in self-test")


def _set_cpu_threads() -> None:
    """Configure PyTorch intra-op and inter-op CPU thread counts once per process."""
    import torch

    if getattr(_set_cpu_threads, "_done", False):
        return
    threads = int(
        os.environ.get("SLICES_TORCH_THREADS") or os.environ.get("OMP_NUM_THREADS") or 1
    )
    torch.set_num_threads(max(1, threads))
    with contextlib.suppress(RuntimeError):
        torch.set_num_interop_threads(1)
    _set_cpu_threads._done = True  # type: ignore[attr-defined]


def _load_calculator(path: str, device: str) -> Any:
    """Load a compiled NequIP ASE calculator from ``path`` onto ``device``."""
    from nequip.integrations.ase import NequIPCalculator

    if "aotinductor-oeq" in os.path.basename(path):
        import openequivariance  # noqa: F401
    return NequIPCalculator.from_compiled_model(
        path, device=device, chemical_species_to_atom_type_map=True
    )


def get_calculator(size: str, device: str) -> tuple[Any, str]:
    """Return ``(ase_calculator, filename)`` for ``NequIP-OAM-<size>`` on ``device``.

    Compiles and caches the model on first use, using an exclusive ``fcntl`` file lock
    so concurrent worker processes wait for a single compilation rather than racing.

    Args:
        size: Model size identifier (``"S"``, ``"M"``, or ``"L"``).
        device: Target compute device (``"cpu"`` or ``"cuda"``).

    Returns:
        Tuple ``(calculator, compiled_model_basename)``.

    Raises:
        RelaxBackendError: If all compilation/loading tiers fail on ``device``.
    """
    key = (size, device)
    if key in _CALCULATORS:
        return _CALCULATORS[key]
    if device == "cpu":
        _set_cpu_threads()
    override = os.environ.get(f"SLICES_NEQUIP_MODEL_{size}", "")
    if override.endswith((".nequip.pth", ".nequip.pt2")):
        calc = _load_calculator(override, device)
        _self_test(calc)
        _CALCULATORS[key] = (calc, os.path.basename(override))
        return _CALCULATORS[key]

    import fcntl

    cache = _cache_dir()
    errors: list[str] = []
    for mode, oeq in _compile_tiers(device):
        path = os.path.join(cache, _compiled_name(size, device, mode, oeq))
        failed_marker = path + ".failed"
        with open(path + ".lock", "w", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if os.path.exists(failed_marker):
                errors.append(f"{os.path.basename(path)}: failed earlier, see {failed_marker}")
                continue
            if not os.path.exists(path):
                _log(
                    f"compiling NequIP-OAM-{size} for {device} "
                    f"({mode}{', OpenEquivariance' if oeq else ''}); "
                    "first use on this machine can take several minutes"
                )
                try:
                    _compile(_model_source(size), path, device, mode, oeq)
                except RelaxBackendError as exc:
                    with open(failed_marker, "w", encoding="utf-8") as fh:
                        fh.write(str(exc))
                    errors.append(str(exc).splitlines()[0])
                    _log(
                        f"{exc.args[0].splitlines()[0]} -> trying the next option "
                        f"(delete {failed_marker} to retry)"
                    )
                    continue
        try:
            calc = _load_calculator(path, device)
            _self_test(calc)
        except Exception as exc:
            errors.append(f"{os.path.basename(path)}: {type(exc).__name__}: {exc}")
            _log(
                f"could not use {os.path.basename(path)} "
                f"({type(exc).__name__}: {exc}); trying the next option"
            )
            continue
        _CALCULATORS[key] = (calc, os.path.basename(path))
        return _CALCULATORS[key]
    raise RelaxBackendError(
        f"no usable NequIP-OAM-{size} model for {device}:\n  " + "\n  ".join(errors)
    )


def _cell_filter(atoms: Any) -> Any:
    """Wrap ``atoms`` in ASE ``ExpCellFilter`` for variable-cell relaxation."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            from ase.filters import ExpCellFilter
        except ImportError:  # ase < 3.23
            from ase.constraints import ExpCellFilter
        return ExpCellFilter(atoms)


def _optimize(target: Any, optimizer: str, fmax: float, steps: int) -> int:
    """Run ASE force minimization on ``target`` and return total steps executed."""
    from ase.optimize import BFGS, FIRE, LBFGS

    classes = {"BFGS": BFGS, "LBFGS": LBFGS, "FIRE": FIRE}
    if optimizer == "FIRE+BFGS":
        plan = [(FIRE, min(FIRE_PRESTEPS, steps)), (BFGS, steps)]
    else:
        plan = [(classes[optimizer], steps)]
    used = 0
    for cls, nmax in plan:
        nmax = min(nmax, steps - used)
        if nmax <= 0:
            break
        opt = cls(target, logfile=None)
        converged = opt.run(fmax=fmax, steps=nmax)
        used += opt.nsteps
        if converged:
            break
    return int(used)


def _validate_nequip_elements(atoms: Atoms) -> None:
    """Validate that all atomic numbers in ``atoms`` belong to NequIP-OAM's 89-element set.

    Args:
        atoms: Input ASE ``Atoms`` structure prior to relaxation.

    Raises:
        RelaxBackendError: If ``atoms`` contains any element outside
            ``NEQUIP_OAM_ATOMIC_NUMBERS`` (``{1..83, 89..94}``).
    """
    z_nums = atoms.get_atomic_numbers()
    if all(int(z) in NEQUIP_OAM_ATOMIC_NUMBERS for z in z_nums):
        return
    unsupported: dict[int, str] = {}
    for symbol, z_raw in zip(atoms.get_chemical_symbols(), z_nums, strict=False):
        z = int(z_raw)
        if z not in NEQUIP_OAM_ATOMIC_NUMBERS and z not in unsupported:
            unsupported[z] = str(symbol)
    formatted = ", ".join(f"{unsupported[z]} (Z={z})" for z in sorted(unsupported))
    raise RelaxBackendError(
        f"Unsupported element(s) for NequIP-OAM relaxation: {formatted}. "
        "Supported 89-element NequIP-OAM atomic numbers are {1..83, 89..94} "
        "(H-Bi and Ac-Pu; Po-Ra [84-88] and Am-Og [95-118] are not in the model vocabulary)."
    )


class NequIPRelaxer:
    """NequIP-OAM crystal relaxer matching the ``SLICES.relax`` dictionary interface.

    ``relax()`` returns ``final_structure`` and a ``trajectory`` namespace whose
    ``energies[-1]`` holds the total potential energy (in eV) of ``final_structure``.
    """

    def __init__(self, name: str, device: str, optimizer: str = "BFGS") -> None:
        """Initialize NequIP relaxation and single-point calculators.

        Args:
            name: NequIP plan name (``"nequip-s+l"``, ``"nequip-m+l"``, or ``"nequip-l"``).
            device: Compute device (``"cpu"`` or ``"cuda"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.

        Raises:
            ValueError: If ``optimizer`` is not in ``OPTIMIZERS``.
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported with NequIP; choose from {OPTIMIZERS}"
            )
        relax_size, energy_size = NEQUIP_PLANS[name]
        self.name, self.device, self.optimizer = name, device, optimizer
        self.relax_calc, relax_file = get_calculator(relax_size, device)
        self.energy_calc, energy_file = (
            get_calculator(energy_size, device) if energy_size else (None, None)
        )
        self.description = (
            f"relax {relax_file}"
            + (f", energy {energy_file}" if energy_file else "")
            + f", optimizer {optimizer}"
        )

    def relax(
        self,
        structure: Structure,
        fmax: float = 0.1,
        steps: int = 500,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Relax ``structure`` with overlap pre-optimization and cell-collapse recovery.

        Validates that all site elements belong to ``NEQUIP_OAM_ATOMIC_NUMBERS``,
        removes severe atomic overlaps prior to relaxation, guards against unphysical
        cell collapse during optimization, and retries once with ``NequIP-OAM-S + FIRE``
        if a collapse is detected. Reports final energy using the plan's energy model.

        Args:
            structure: Input ``pymatgen`` ``Structure`` to relax.
            fmax: Maximum atomic force convergence threshold in eV/Angstrom.
            steps: Maximum number of optimizer steps.
            **kwargs: Unused extra keyword arguments for interface compatibility.

        Returns:
            Dictionary containing ``final_structure``, ``trajectory`` (with ``energies``
            in total eV), ``steps``, ``preoptimized``, and ``retry``.

        Raises:
            RelaxBackendError: If ``structure`` contains elements outside
                ``NEQUIP_OAM_ATOMIC_NUMBERS`` or if cell collapse persists.
        """
        from pymatgen.io.ase import AseAtomsAdaptor

        atoms = AseAtomsAdaptor.get_atoms(structure)
        _validate_nequip_elements(atoms)
        orig_structure = structure
        structure, pre = preoptimize(structure)
        if structure is not orig_structure:
            atoms = AseAtomsAdaptor.get_atoms(structure)
        retry = 0
        try:
            with _collapse_guard(self.relax_calc, atoms):
                atoms.calc = self.relax_calc
                n_steps = _optimize(_cell_filter(atoms), self.optimizer, fmax, steps)
        except CellCollapse as exc:
            from ase.optimize import FIRE

            retry = 1
            s_calc, _ = get_calculator("S", self.device)
            atoms = AseAtomsAdaptor.get_atoms(structure)
            with _collapse_guard(s_calc, atoms):
                atoms.calc = s_calc
                opt = FIRE(_cell_filter(atoms), logfile=None, maxstep=0.1)
                opt.run(fmax=fmax, steps=2 * steps)
                n_steps = int(opt.nsteps)
            _log(f"relaxation collapsed ({exc}); retried with NequIP-OAM-S + FIRE")
        atoms.calc = None
        final = AseAtomsAdaptor.get_structure(atoms)
        atoms.calc = self.energy_calc or self.relax_calc
        energy = float(atoms.get_potential_energy())
        return {
            "final_structure": final,
            "trajectory": types.SimpleNamespace(energies=[energy]),
            "steps": n_steps,
            "preoptimized": pre["applied"],
            "retry": retry,
        }


# === Start-Structure Safety & Cell-Collapse Guards ===
# Lattice optimization occasionally returns overlapping atoms (closest pair down to 0 A).
# Starting from such a geometry, ML force fields can collapse the cell so neighbor-list
# construction hangs in C extensions where SIGALRM cannot interrupt it.

OVERLAP_TRIGGER: float = 0.5  # pre-optimize when closest pair < trigger * (r_i + r_j)
OVERLAP_TARGET: float = 0.7  # push pairs apart to at least target * (r_i + r_j)
COLLAPSE_VOLUME: float = 2.0  # A^3 per atom; physical crystals exceed ~5 A^3/atom


class CellCollapse(RelaxBackendError):
    """Raised when the unit cell collapses or degenerates during relaxation."""


def _covalent_radii(structure: Structure) -> np.ndarray:
    """Return covalent radii (Angstrom) for all sites in ``structure``."""
    import numpy as np
    from pymatgen.analysis.local_env import CovalentRadius

    return np.array([CovalentRadius.radius.get(el.symbol, 1.5) for el in structure.species])


def closest_pair_ratio(structure: Structure) -> float:
    """Compute minimum ``d_ij / (r_i + r_j)`` across all periodic atom pairs.

    Args:
        structure: Input ``pymatgen`` ``Structure``.

    Returns:
        Smallest ratio of interatomic distance to sum of covalent radii.
    """
    import numpy as np

    rad = _covalent_radii(structure)
    d = structure.distance_matrix.copy()
    np.fill_diagonal(d, np.inf)
    return float((d / (rad[:, None] + rad[None, :])).min())


def remove_overlaps(
    structure: Structure,
    target: float = OVERLAP_TARGET,
    max_iter: int = 300,
    max_expand: float = 1.5,
    seed: int = 0,
) -> Structure:
    """Push apart atom pairs closer than ``target * (r_i + r_j)`` via pure geometry.

    Each overlapping pair separates along its displacement vector (or a seeded random
    unit vector when ``d < 1e-3``). If overlaps persist, the lattice expands by 2%
    every 20 iterations up to ``max_expand`` times its initial linear dimensions.

    Args:
        structure: Input ``pymatgen`` ``Structure``.
        target: Target minimum fraction of ``r_i + r_j``.
        max_iter: Maximum repulsive displacement iterations.
        max_expand: Maximum isotropic linear cell expansion factor.
        seed: Deterministic random seed for breaking exact atom coincidences.

    Returns:
        Overlap-resolved ``Structure``.
    """
    import numpy as np
    from pymatgen.core import Lattice, Structure

    rng = np.random.default_rng(seed)
    s = structure.copy()
    rad = _covalent_radii(s)
    scale = 1.0
    for it in range(max_iter):
        i, j, img, d = s.get_neighbor_list(target * 2 * rad.max())
        need = target * (rad[i] + rad[j])
        m = (d < need) & (i < j)
        if not m.any():
            break
        i, j, img, d, need = i[m], j[m], img[m], d[m], need[m]
        cart = s.cart_coords
        vec = cart[j] + img @ s.lattice.matrix - cart[i]
        tiny = d < 1e-3
        if tiny.any():
            rnd = rng.normal(size=(int(tiny.sum()), 3))
            vec[tiny] = rnd / np.linalg.norm(rnd, axis=1)[:, None] * 1e-3
            d = np.where(tiny, 1e-3, d)
        push = 0.525 * (need - d)[:, None] * vec / d[:, None]
        delta = np.zeros_like(cart)
        np.add.at(delta, i, -push)
        np.add.at(delta, j, push)
        cart = cart + delta
        lattice = s.lattice
        if it and it % 20 == 0 and scale * 1.02 <= max_expand:
            frac = lattice.get_fractional_coords(cart)
            lattice = Lattice(lattice.matrix * 1.02)
            cart = lattice.get_cartesian_coords(frac)
            scale *= 1.02
        s = Structure(lattice, s.species, cart, coords_are_cartesian=True)
    return s


def preoptimize(
    structure: Structure,
    trigger: float = OVERLAP_TRIGGER,
) -> tuple[Structure, dict[str, Any]]:
    """Niggli-reduce and remove overlaps when ``closest_pair_ratio < trigger``.

    Args:
        structure: Candidate ``Structure`` prior to MLIP relaxation.
        trigger: Overlap ratio threshold below which geometric repair runs.

    Returns:
        Tuple ``(structure_out, metadata_dict)``.
    """
    ratio = closest_pair_ratio(structure)
    if ratio >= trigger:
        return structure, {"applied": False, "ratio": ratio}
    s = structure
    with contextlib.suppress(Exception):
        s = s.get_reduced_structure("niggli")
    s = remove_overlaps(s)
    return s, {"applied": True, "ratio_before": ratio, "ratio": closest_pair_ratio(s)}


class _collapse_guard:
    """Context manager making an ASE calculator reject collapsed or degenerate cells."""

    def __init__(self, calc: Any, atoms: Any) -> None:
        self.calc = calc
        self.natoms = len(atoms)
        self.min_volume = min(COLLAPSE_VOLUME, 0.5 * atoms.get_volume() / len(atoms))
        self.orig: Any = None

    def __enter__(self) -> Self:
        calc, natoms, min_volume, orig = (
            self.calc,
            self.natoms,
            self.min_volume,
            self.calc.calculate,
        )
        self.orig = orig

        def calculate(atoms: Any = None, *args: Any, **kwargs: Any) -> Any:
            if atoms is not None:
                volume = atoms.get_volume() / natoms
                if not volume >= min_volume:
                    raise CellCollapse(f"cell collapsed to {volume:.2f} A^3/atom")
                lengths = atoms.cell.lengths()
                if lengths.max() > 20 * lengths.min() or min(atoms.cell.angles()) < 5:
                    raise CellCollapse("cell degenerated")
            return orig(atoms, *args, **kwargs)

        calc.calculate = calculate
        return self

    def __exit__(self, *exc: object) -> bool:
        self.calc.calculate = self.orig
        return False


# === Module CLI ===


def _main() -> None:
    """CLI entry point for ``python -m slices.relax_backends [--prepare]``."""
    import argparse

    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--relax-model",
        default="auto",
        help="relax_model to inspect or prepare (default: auto)",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="compile/cache the models and run a test relaxation",
    )
    args = parser.parse_args()

    print(f"python {sys.version.split()[0]}  nequip installed: {nequip_available()}")
    if nequip_available():
        import torch

        cuda = torch.cuda.is_available()
        print(
            f"torch {torch.__version__}  CUDA available: {cuda}"
            + (f"  GPU: {torch.cuda.get_device_name(0)}" if cuda else "")
            + f"  OpenEquivariance: {importlib.util.find_spec('openequivariance') is not None}"
        )
    name, device = resolve_relax_model(args.relax_model)
    print(f"relax_model={args.relax_model!r} resolves to {name!r} on {device}")
    if not args.prepare:
        return
    t0 = time.time()
    relaxer, name = make_relaxer(args.relax_model)
    print(
        f"ready in {time.time() - t0:.0f} s: {name}"
        + (f" ({relaxer.description})" if hasattr(relaxer, "description") else "")
    )
    if relaxer is None:
        return
    from pymatgen.core import Lattice, Structure

    struct = Structure(Lattice.cubic(4.3), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])
    t0 = time.time()
    res = relaxer.relax(struct, fmax=0.2, steps=100)
    final = res["final_structure"]
    print(
        f"test relaxation (CsCl-type NaCl): {time.time() - t0:.2f} s, "
        f"E = {res['trajectory'].energies[-1] / len(final):.4f} eV/atom, "
        f"a = {final.lattice.a:.3f} A"
    )


if __name__ == "__main__":
    _main()
