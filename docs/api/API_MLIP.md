# API Reference: Relaxation Backends and Optional MLIPs (`slices.relax_backends`, `slices.mlip_relaxer`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/relax_backends.py`](../../src/slices/relax_backends.py), [`src/slices/mlip_relaxer.py`](../../src/slices/mlip_relaxer.py)

---

## 1. Architecture Overview

SLICES v4.0.2 separates the **frozen default NequIP-OAM relaxation backend** (`slices.relax_backends`) from **strictly optional third-party MLIP adapters** (`slices.mlip_relaxer`):

- Built-in `RELAX_MODELS` (`"auto"`, `"none"`, `"nequip-s+l"`, `"nequip-m+l"`, `"nequip-l"`) execute entirely inside `slices.relax_backends` with zero delegation to `slices.mlip_relaxer`.
- When `relax_model` is outside `RELAX_MODELS`, `resolve_relax_model` and `make_relaxer` lazily import `slices.mlip_relaxer` to resolve and instantiate optional backends (`chgnet`, `mattersim`, `orbv3`, `mace`, or legacy `m3gnet`).
- Neither module imports `torch`, `tensorflow`, `keras`, or optional MLIP libraries at module import time.

---

## 2. Default NequIP Backend (`slices.relax_backends`)

### Public Exports (`slices.relax_backends.__all__`)

`COLLAPSE_VOLUME`, `DOWNLOAD_RETRY_WAITS`, `DOWNLOAD_TIMEOUT`, `FIRE_PRESTEPS`, `NEQUIP_MODEL_IDS`, `NEQUIP_PLANS`, `OPTIMIZERS`, `OVERLAP_TARGET`, `OVERLAP_TRIGGER`, `RELAX_MODELS`, `CellCollapse`, `ModelDownloadError`, `NequIPRelaxer`, `RelaxBackendError`, `choose_device`, `closest_pair_ratio`, `get_calculator`, `make_relaxer`, `nequip_available`, `preoptimize`, `remove_overlaps`, `resolve_relax_model`.

### Constants & Plans

| Constant | Value | Purpose |
|---|---|---|
| `NEQUIP_MODEL_IDS` | `{"S": "mir-group/NequIP-OAM-S:0.1", "M": "mir-group/NequIP-OAM-M:0.1", "L": "mir-group/NequIP-OAM-L:0.1"}` | Official `nequip.net` model identifiers |
| `NEQUIP_PLANS` | `{"nequip-l": ("L", None), "nequip-s+l": ("S", "L"), "nequip-m+l": ("M", "L")}` | `(relax_size, energy_single_point_size)` pairs |
| `RELAX_MODELS` | `("auto", "none", "nequip-l", "nequip-s+l", "nequip-m+l")` | Built-in v4.0.2 model choices |
| `OPTIMIZERS` | `("BFGS", "LBFGS", "FIRE", "FIRE+BFGS")` | Supported ASE optimizers (`FIRE+BFGS` runs `min(FIRE_PRESTEPS, steps)` FIRE steps then BFGS) |
| `FIRE_PRESTEPS` | `10` | Pre-conditioning FIRE step count for `"FIRE+BFGS"` |
| `OVERLAP_TRIGGER` | `0.5` | `closest_pair_ratio` threshold triggering `preoptimize` |
| `OVERLAP_TARGET` | `0.7` | Target minimum `d_ij / (r_i + r_j)` ratio for `remove_overlaps` |
| `COLLAPSE_VOLUME` | `2.0` | Minimum volume per atom (Angstrom^3/atom) enforced by `_collapse_guard` |
| `DOWNLOAD_RETRY_WAITS` | `(5, 15, 30)` | Retry backoff delays (seconds) for Zenodo weight downloads |
| `DOWNLOAD_TIMEOUT` | `(30, 120)` | `(connect, read)` HTTP timeout tuple (seconds) |

### Exceptions

- `RelaxBackendError(SLICESError, RuntimeError)` (imported from `slices.exceptions`): Raised on model compilation, loading, or evaluation failures.
- `ModelDownloadError(SLICESError, RuntimeError)` (imported from `slices.exceptions`, **sibling** of `RelaxBackendError`): Raised on Zenodo/network download failures without writing `.failed` cache markers.
- `CellCollapse(RelaxBackendError)`: Raised by `_collapse_guard` when unit-cell volume, aspect ratio (`> 20x`), or cell angle (`< 5 deg`) degenerates during relaxation.

### Model Resolution & Factory Functions

| Function | Signature | Behavior |
|---|---|---|
| `nequip_available` | `() -> bool` | Returns `True` iff both `torch` and `nequip` are importable. |
| `choose_device` | `() -> str` | Reads `SLICES_DEVICE` (`"cpu"` default; `"cuda"` falls back to `"cpu"` if CUDA is unavailable; raises `ValueError` for invalid values). |
| `resolve_relax_model` | `(relax_model: str | None) -> tuple[str, str | None]` | Maps `None`/`"none"` -> `("none", None)`; `"auto"` -> `SLICES_RELAX_MODEL` or `"nequip-s+l"`; built-in NequIP names -> `(name, choose_device())`; external names -> lazy `mlip_relaxer.resolve_optional_mlip(name)`. |
| `make_relaxer` | `(relax_model: str | None = "auto", optimizer: str = "BFGS") -> tuple[Any, str]` | Instantiates `(NequIPRelaxer, resolved_name)` (with CUDA-to-CPU fallback on `RelaxBackendError`), `(None, "none")`, or `(MLIPRelaxer, canonical_name)` via `make_optional_relaxer`. |
| `get_calculator` | `(size: str, device: str) -> tuple[Any, str]` | Downloads/compiles/caches (in `SLICES_MODEL_CACHE`, default `~/.cache/slices/nequip`) and returns `(ase_calculator, filename)` for `size in {"S", "M", "L"}`. Caches loaded calculators in process-level `_CALCULATORS`. |

### `NequIPRelaxer`

```python
class NequIPRelaxer:
    def __init__(self, name: str, device: str, optimizer: str = "BFGS") -> None
    def relax(
        self,
        structure: Structure,
        fmax: float = 0.1,
        steps: int = 500,
        **kwargs: Any,
    ) -> dict[str, Any]
```

- **Attributes:** `name: str`, `device: str`, `optimizer: str`, `description: str`, `relax_calc`, `energy_calc`.
- **Execution Pipeline:**
  1. Runs `preoptimize(structure)` when `closest_pair_ratio(structure) < OVERLAP_TRIGGER`.
  2. Converts to ASE `Atoms`, wraps in `_cell_filter` (`ExpCellFilter`, frozen per `DEF-009`), and minimizes under `_collapse_guard` via `_optimize`.
  3. On `CellCollapse`, retries once from the post-`preoptimize` structure using `NequIP-OAM-S` with `FIRE(maxstep=0.1)` and `2 * steps` (`retry = 1`).
  4. Evaluates final total energy (in eV) with `energy_calc` (`L` for `nequip-s+l` / `nequip-m+l`) or the relaxation calculator (`nequip-l`).
- **Return Dictionary Protocol (5 Keys):**
  ```python
  {
      "final_structure": Structure,               # Relaxed pymatgen Structure
      "trajectory": SimpleNamespace(energies=[float]),  # Total energy in eV (last entry)
      "steps": int,                               # Total optimizer steps taken
      "preoptimized": bool,                       # True if overlap pre-optimization ran
      "retry": int,                               # 0 or 1 (collapse recovery triggered)
  }
  ```

### Geometry Safety Primitives & Module CLI

| Symbol | Signature | Description |
|---|---|---|
| `closest_pair_ratio` | `(structure: Structure) -> float` | Minimum `d_ij / (r_i + r_j)` across periodic atom pairs (`inf` for 1-atom primitive cells with no near neighbors). |
| `remove_overlaps` | `(structure: Structure, target: float = 0.7, max_iter: int = 300, max_expand: float = 1.5, seed: int = 0) -> Structure` | Pure-geometry overlap push-apart using isolated `np.random.default_rng(seed)` (zero global RNG mutation), with 2% cell expansion every 20 iterations up to `max_expand`. |
| `preoptimize` | `(structure: Structure, trigger: float = 0.5) -> tuple[Structure, dict[str, Any]]` | Applies Niggli reduction and `remove_overlaps` when `closest_pair_ratio < trigger`; otherwise returns `(structure, {"applied": False, ...})` untouched. |
| `_collapse_guard` | `class _collapse_guard(calc: Any, atoms: Any)` | Context manager wrapping `calc.calculate` to raise `CellCollapse` if volume/atom `< min(COLLAPSE_VOLUME, 0.5 * V0 / N)`, cell aspect ratio `> 20`, or any cell angle `< 5 deg`; always restores `calc.calculate` in `__exit__`. |

#### Pre-Compilation & Diagnostics CLI (`python -m slices.relax_backends`)

The module entry point `_main()` inspects environment readiness and pre-compiles cached TorchScript/AOTInductor weights without needing a separate `prepare_models` function:

```bash
# Inspect resolved model and hardware status
python -m slices.relax_backends --relax-model auto

# Download, compile, cache models, and run CsCl-type NaCl verification relaxation
python -m slices.relax_backends --relax-model auto --prepare
```

---

## 3. Optional Multi-MLIP Adapters (`slices.mlip_relaxer`)

### Public Exports (`slices.mlip_relaxer.__all__`)

`OPTIONAL_MLIP_ALIASES`, `OPTIONAL_MLIP_MODELS`, `CHGNetRelaxer`, `M3GNetRelaxer`, `MACERelaxer`, `MLIPRelaxer`, `MatterSimRelaxer`, `ORBv3Relaxer`, `choose_mlip_device`, `get_relaxer`, `make_optional_relaxer`, `mlip_available`, `resolve_optional_mlip`.

### Supported Optional Models & Aliases

| Canonical Name | Accepted Aliases | Required Python Package(s) | Model Variant Env Var | Adapter Class |
|---|---|---|---|---|
| `"chgnet"` | `"chgnet"` | `chgnet` | — | `CHGNetRelaxer` |
| `"mattersim"` | `"mattersim"` | `mattersim` | `SLICES_MATTERSIM_MODEL` | `MatterSimRelaxer` |
| `"orbv3"` | `"orbv3"`, `"orb-v3"`, `"orb_v3"`, `"orb"` | `orb_models` | `SLICES_ORBV3_MODEL` | `ORBv3Relaxer` |
| `"mace"` | `"mace"`, `"mace-mp"`, `"mace_mp"` | `mace` | `SLICES_MACE_MODEL` (default `"medium"`) | `MACERelaxer` |
| `"m3gnet"` | `"m3gnet"` | `m3gnet`, `tensorflow` | — (`TF_USE_LEGACY_KERAS` scoped in `__init__`) | `M3GNetRelaxer` |

### Helper & Factory Functions

| Function | Signature | Behavior |
|---|---|---|
| `mlip_available` | `(model_name: str) -> bool` | Checks `importlib.util.find_spec` for all packages required by `model_name` without importing them. |
| `choose_mlip_device` | `(explicit_device: str | None = None) -> str` | Resolves `"cpu"`, `"cuda"`, or `"mps"` honoring `SLICES_DEVICE`, falling back safely to `"cpu"`. |
| `resolve_optional_mlip` | `(name: str) -> tuple[str, str]` | Normalizes aliases, validates installation (raising `ImportError` with an exact `pip install` hint if uninstalled, or `ValueError` if unknown), and returns `(canonical_name, device)`. |
| `make_optional_relaxer` | `(name: str, device: str | None = None, optimizer: str = "BFGS", model_variant: str | None = None) -> MLIPRelaxer` | Instantiates the concrete `MLIPRelaxer` subclass for `name`. |
| `get_relaxer` | `(model_name: str | None = "auto", **kwargs: Any) -> Any` | Unified convenience factory: delegates built-in models (`"auto"`, `"none"`, `"nequip-*"`) to `relax_backends.make_relaxer` and optional names to `make_optional_relaxer`. |

### Adapter Hierarchy & Return Contract

- **`MLIPRelaxer(ABC)`:** Defines abstract `relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100, **kwargs: Any) -> dict[str, Any]` and requires `.name`, `.device`, `.optimizer`, and `.description` attributes.
- **`_ASEMLIPRelaxer(MLIPRelaxer)`:** Shared base for `CHGNetRelaxer`, `MatterSimRelaxer`, `ORBv3Relaxer`, and `MACERelaxer`. Reuses `relax_backends.preoptimize`, `_cell_filter`, `_collapse_guard`, `_optimize`, and `FIRE` collapse retry, returning the exact 5-key `NequIPRelaxer` dictionary (`trajectory.energies[-1]` is always total potential energy in eV).
- **`M3GNetRelaxer(MLIPRelaxer)`:** Legacy opt-in wrapper that sets `TF_USE_LEGACY_KERAS="1"` and imports `tf_keras` strictly inside `__init__` (never at module scope), runs `preoptimize`, and normalizes output to the same 5-key dictionary protocol.
