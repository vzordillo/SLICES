# API Reference: Physical Constants, Environment Variables, and Tooling Configuration (`slices.config`, `pyproject.toml`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/config.py`](../../src/slices/config.py), [`pyproject.toml`](../../pyproject.toml)

---

## 1. Frozen Physical & Crystallographic Constants (`slices.config`)

All three module-level constants in `slices.config` are **strictly frozen** bit-for-bit against upstream SLICES v4.0.2 (`94ef8e0`) and verified by SHA-256 hash checks in `tests/baseline/test_golden_equivalence.py`.

### Public Exports (`slices.config.__all__`)

| Symbol | Type & Shape | Description |
|---|---|---|
| `OFFSET` | `np.ndarray` (`int64`, shape `(27, 3)`) | Ordered integer lattice offsets of the `3x3x3` supercell spanning `{-1, 0, +1}^3`. Index `13` is `[0, 0, 0]` (central unit cell). Used by `SLICES.get_nbf_blist`. |
| `LJ_PARAMS_LIST` | `list[list[float | int]]` (`118` rows × `3` columns) | Element-indexed `[atomic_number, cutoff_angstrom, sigma_angstrom]` Lennard-Jones repulsive potential parameters for `Z = 1..118`, consumed by `get_uncovered_pair_lj` and `get_covered_pair_lj`. |
| `PERIODIC_DATA` | `pd.DataFrame` (`118` rows × `12` columns) | Periodic table reference parsed from embedded CSV with columns: `atomic_number`, `symbol`, `name`, `atomic_mass`, `electron_configuration`, `phase`, `category`, `period`, `group`, `mass_number`, `radioactive`, `valence_electrons`. |

---

## 2. Complete Environment Variable Reference

Every environment variable read or set across `src/slices/*.py` is documented below.

### 2.1 Force-Field & Relaxation Variables (`slices.relax_backends`, `slices.mlip_relaxer`)

| Variable | Module(s) | Default | Valid Values & Behavior |
|---|---|---|---|
| `SLICES_RELAX_MODEL` | `relax_backends.py` | Unset (`"nequip-s+l"` via `"auto"`) | Overrides `relax_model="auto"` (e.g., `"nequip-l"`, `"nequip-m+l"`, `"nequip-s+l"`, `"none"`, or an optional MLIP name). |
| `SLICES_DEVICE` | `relax_backends.py`, `mlip_relaxer.py` | `"cpu"` | Compute device for NequIP (`"cpu"`, `"cuda"`) and optional PyTorch MLIPs (`"cpu"`, `"cuda"`, `"mps"`). Falls back to `"cpu"` if requested accelerator is unavailable. |
| `SLICES_MODEL_CACHE` | `relax_backends.py` | `~/.cache/slices/nequip` | Directory storing compiled TorchScript (`.nequip.pth`) and AOTInductor (`.nequip.pt2`) NequIP models. |
| `NEQUIP_CACHE_DIR` | `nequip` (via `_download_model`) | `~/.nequip/model_cache` | Directory storing downloaded raw NequIP Zenodo `.nequip.zip` archives and metadata. |
| `SLICES_NEQUIP_MODEL_S` / `_M` / `_L` | `relax_backends.py` | Unset (Zenodo download) | Local path to a pre-downloaded `.nequip.zip` package for `NequIP-OAM-S`, `-M`, or `-L` (bypasses network download). |
| `SLICES_NEQUIP_TF32` | `relax_backends.py` | Unset (`False`) | Set to `"1"`, `"true"`, or `"yes"` to enable TF32 matmul/cuDNN on CUDA GPUs (reflected in compiled cache filename tag `tf32`). |
| `SLICES_TORCH_THREADS` | `relax_backends.py` | `OMP_NUM_THREADS` or CPU count | Overrides PyTorch intra-op CPU thread count (`torch.set_num_threads`) once per process (`1` recommended for bit-exact CPU reproducibility). |
| `SLICES_MATTERSIM_MODEL` | `mlip_relaxer.py` | Unset (package default) | Optional checkpoint path or model name passed to `MatterSimCalculator`. |
| `SLICES_ORBV3_MODEL` | `mlip_relaxer.py` | `"orb-v3-conservative-inf-omat"` (fallback `"orb-v3-direct-inf-mpa"`) | Pretrained ORBv3 model identifier loaded by `ORBv3Relaxer`. |
| `SLICES_MACE_MODEL` | `mlip_relaxer.py` | `"medium"` | MACE-MP model size or checkpoint path passed to `mace_mp`. |
| `TF_USE_LEGACY_KERAS` | `mlip_relaxer.py` | Set to `"1"` **only** inside `M3GNetRelaxer.__init__` | Enables `tf_keras` (Keras 2) compatibility for opt-in legacy `relax_model="m3gnet"` without affecting non-M3GNet imports. |

### 2.2 GFN-FF Topology & Non-Linux Fallback Variables (`slices.gfnff_helper`)

| Variable | Module(s) | Default | Valid Values & Behavior |
|---|---|---|---|
| `SLICES_VENDOR_GFNFF_PARAM_MODE` | `gfnff_helper.py` | `"legacy86_overlay"` | `"legacy86_overlay"` (`""`, `"default"`, `"legacy86"`) uses `param_gfnff_legacy86.xtb` for `Z=1..86` and modern parameters for `Z=87..103`; `"modern"` (`"internal"`, `"none"`) uses library-internal parameters for all elements. |
| `SLICES_VENDOR_GFNFF_PARAM_FILE` | `gfnff_helper.py` | `LEGACY86_PARAM_FILE` | Custom xtb-style parameter table path when in `legacy86_overlay` mode. |
| `SLICES_VENDOR_GFNFF_RAB_MODE` | `gfnff_helper.py` | Matches `param_mode` | Internal environment variable temporarily defaulted for the patched `libgfnff` C/Fortran library during `from_nbf`, restored on exit. |
| `SLICES_XTB_PATH` | `gfnff_helper.py` | Unset | Primary path override for an external modified `xtb` binary used **only** when bundled `libgfnff.so` fails to load on non-Linux platforms. |
| `XTB_MOD_PATH` | `gfnff_helper.py` | Unset | Legacy alias for `SLICES_XTB_PATH` checked second before falling back to `shutil.which("xtb_noring_nooutput_nostdout_noCN")`. |

### 2.3 Job Execution, Determinism & Runtime Variables (`slices.core`, `slices.utils`)

| Variable | Module(s) | Default | Valid Values & Behavior |
|---|---|---|---|
| `SLICES_FORCE_LOCAL` | `utils.py` | Unset (`False`) | Set to `"1"`, `"true"`, or `"yes"` to force `is_slurm_available()` to return `False` and execute `splitRun*` shards locally even on a SLURM login node. |
| `OMP_NUM_THREADS` | `core.py`, `relax_backends.py`, `utils.py` | Set to `"1"` on `slices.core` import (`DEF-005`) | Enforces single-threaded OpenMP/BLAS execution for deterministic CPU Cholesky, L-BFGS-B, and `multiprocessing.Pool` workers (alongside `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS` in `utils._init_single_thread_worker`). |
| `PYTHONHASHSEED` | Python runtime (recommended `"0"`) | Random per process | Set `PYTHONHASHSEED=0` when exact cross-process list order is required from `SLICES.structure2randomSLICES` (`DEF-022`) and when running `tests/baseline/test_golden_equivalence.py`. |
| `PYTHONWARNINGS` | `core.py` | Set to `"ignore"` on `slices.core` import (`DEF-005`) | Frozen upstream import-time warning suppression. |
| `TF_CPP_MIN_LOG_LEVEL` | `core.py` | Set to `"3"` on `slices.core` import (`DEF-005`) | Frozen upstream TensorFlow C++ log-level setting. |

---

## 3. Packaging, Linting & Testing Configuration (`pyproject.toml`)

### Package Metadata, Extras & Dependency Groups

- **Build Backend:** `setuptools>=77` (`setuptools.build_meta`), Python `>=3.10`, version `4.0.2`.
- **Console Entry Point:** `[project.scripts] slices = "slices.cli:main"`.
- **PyTorch Extras (Mutually Exclusive in `[tool.uv]`):** `cpu`, `cu126`, `cu128` (mapped to explicit PyTorch wheel indexes `pytorch-cpu`, `pytorch-cu126`, `pytorch-cu128`), plus optional GPU acceleration extra `oeq = ["openequivariance"]`.
- **PEP 735 Dev Group (`[dependency-groups]`):** `dev = ["pytest>=8.0", "pytest-cov>=5.0", "ruff>=0.9"]`.
- **Locked Index Policy (`CA-02`):** Retains `[[tool.uv.index]] name = "tuna"` (`default = true`) so `uv.lock` resolves identically across all core scientific packages (`torch 2.9.1`, `nequip 0.17.1`, `pymatgen 2025.10.7`, `ase 3.29.0`, `scipy 1.15.3`, `numpy 2.2.6`, `networkx 3.4.2`, `spglib 2.7.0`, `matscipy 1.3.1`, `e3nn 0.6.0`). Outside China, ad-hoc unlocked installs can pass `UV_DEFAULT_INDEX=https://pypi.org/simple`.

### Ruff Google Python Style Configuration (`[tool.ruff]`)

- `target-version = "py310"`, `line-length = 100`.
- `select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF", "D"]` with `[tool.ruff.lint.pydocstyle] convention = "google"`.
- `extend-exclude = ["src/slices/_vendor", "HTS", "benchmark", "data", "docs"]`.
- Minimal documented `per-file-ignores`:
  - `"src/slices/core.py" = ["E402"]` (`DEF-005` frozen top-of-file env setup).
  - `"src/slices/utils_wyckoff.py" = ["E501"]` (frozen 250-entry `sg_encoding` literal).
  - `"examples/3.benchmark_relax_models.py" = ["E402"]` (standalone `OMP_NUM_THREADS="1"` before imports).
  - `"tests/**/*.py" = ["B017", "D100", "D101", "D102", "D103", "D104", "D107", "E501", "RUF100"]`.

### Pytest Configuration (`[tool.pytest.ini_options]`)

- `testpaths = ["tests"]`; excludes `.git`, `.venv`, `build`, `dist`, `src/slices/_vendor`, `HTS`, `benchmark`, `data`, `docs`.
- Registered markers: `baseline`, `unit`, `integration`, `regression`, `slow`, `mlip`, `gfnff`, `network`.
- Recommended reproducible test command:
  ```bash
  PYTHONHASHSEED=0 OMP_NUM_THREADS=1 pytest tests/
  # Or via the bundled runner:
  python tools/run_tests.py --lint
  ```
