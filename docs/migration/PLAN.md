# Stage 1 Migration Plan: Personal SLICES Improvements onto Upstream SLICES v4.0.2

**Date:** 2026-11-25  
**Target Branch:** `slices-4-personal` (forked from `upstream/main` at `94ef8e0`, tag `v4.0.2`)  
**Reference Personal Branch:** `backup/v3-personal` (`origin/main` at `301c75f`)  
**Immutable Baseline Worktree:** `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`, detached, locked, `chmod -R a-w`)  
**Remote Policy:** **LOCAL-ONLY — NEVER PUSH TO ANY GITHUB REMOTE** (`git config push.default nothing`)

---

## 1. Executive Overview & Pipeline Architecture

This plan governs the 7-stage migration of personal software-engineering, multi-MLIP, cross-platform, CLI, testing, and documentation improvements from `backup/v3-personal` (`vzordillo/SLICES`) onto the upstream **SLICES v4.0.2** codebase (`xiaohang007/SLICES` at `94ef8e0`).

```mermaid
flowchart LR
    S1["1. Plan & Env Setup"] --> S2["2. Parallel Audit (3 Slices)"]
    S2 --> S3["3. Review & Freeze Sign-Off"]
    S3 --> S4["4. Refactor & Additive Port"]
    S4 --> S5["5. Refine, Types & Tests"]
    S5 --> S6["6. Document (100% English)"]
    S6 --> S7["7. Systematize & Final Gate"]
```

### Governing Non-Negotiables
1. **Local-Only Execution:** Never push branches, tags, or commits to `origin` or `upstream`.
2. **Repository Scope:**
   - **Keep:** `src/slices/`, CLI, `tests/`, `docs/`, `configs/` / Docker scripts, `examples/`, `data/`, `benchmark/`, and `HTS/`.
   - **Remove (in Stage 4 Refactor only, NOT earlier):** `MatterGPT/` (`MatterGPT_no_flash/` was already removed upstream between `142298b` and `94ef8e0`; `MatterGPT/` is `8.9 MB` on `94ef8e0` and will be cleanly decoupled and removed in Stage 4).
3. **Default Relaxation & Topology Baseline:** Upstream v4.0.2 NequIP (`src/slices/relax_backends.py`, `relax_model="auto"` resolving to CPU `nequip-s+l`) + Linux-bundled GFN-FF (`src/slices/gfnff_helper.py`, `src/slices/_vendor/gfnff*`) remain the **untouched default baseline**. Personal `mlip_relaxer`, cross-platform binary/GFN-FF fallbacks, and `decoding_strategies` are ported strictly as **optional, opt-in additive modules**.
4. **Strict Math/Algorithm Freeze:** Core mathematical, crystallographic, graph-theoretic, topological, GFN-FF target-building, ZL* optimization, and default NequIP relaxation logic **MUST NOT be altered**. Candidate bug fixes or algorithmic improvements discovered in either upstream or `backup/v3-personal` are logged in a **Deferred Core/Algorithm Register** (`docs/migration/DEFERRED_CORE_REGISTER.md`) for post-migration evaluation.
5. **Style & Scientific Rigor:** Merge coding conventions from `backup/v3-personal` with the **Google Python Style Guide**: 100% English-only codebase and docs (zero CJK characters in kept scope), Google-style docstrings, Python 3.10+ type annotations, clean modularity, structured exceptions, and lab-log verification discipline.

---

## 2. Repository Setup Verification & Toolchain / Environment Report

### 2.1 Git Remotes, Branches, Fork-Base Equivalence & Worktrees

| Artifact | Path / Ref | Verified Commit / Tree SHA | Notes |
|---|---|---|---|
| Working Repository | `/home/ordillo/tests/SLICES` | HEAD on `slices-4-personal` (`94ef8e0`) | Clean working tree (`push.default=nothing`) |
| Baseline Worktree | `/home/ordillo/tests/SLICES-upstream-baseline` | Detached HEAD `94ef8e0` | `git worktree lock` + `chmod -R a-w` (read-only) |
| Remote `origin` | `https://github.com/vzordillo/SLICES.git` | `origin/main` = `301c75fcdfb2d553b616c30178ccc7b0161b1fe7` | Personal rewritten-history fork |
| Remote `upstream` | `https://github.com/xiaohang007/SLICES.git` | `upstream/main` = `94ef8e079b69c37138159805e3c701b8df87a5d7` | Tagged `v4.0.2` |
| Branch `backup/v3-personal` | `origin/main` | `301c75fcdfb2d553b616c30178ccc7b0161b1fe7` | 30 commits ahead of `cea17da` |
| Branch `slices-4-personal` | Checked out in `/home/ordillo/tests/SLICES` | `94ef8e079b69c37138159805e3c701b8df87a5d7` | 23 commits ahead of `142298b` |
| Upstream Fork-Base | `142298be4f83ab161d51298c82e74e94c3319891` | Tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9` | Exact tree match with `cea17da` (`git diff` empty) |
| Personal Fork-Base | `cea17da95be2cd9d17f6c71765895dbb5cb64958` | Tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9` | Verified bit-identical tree to `142298b` |

### 2.2 Local Hardware, OS, GPU & Storage Constraints

| Resource | Specification / Status | Operational Impact |
|---|---|---|
| OS / Kernel | Ubuntu 24.04.3 LTS (`Linux sage 6.8.0-87-generic x86_64`) | Compatible with `manylinux2014_x86_64` bundled `libgfnff.so.0.1.1` |
| CPU | Intel(R) Xeon(R) 6731P (32 physical cores, 1 thread/core) | High parallel throughput for CPU `nequip-s+l` + `pytest` |
| System RAM | 503 GiB total (~488 GiB available) | Ample memory for multi-worker tests and `/dev/shm` scratch |
| GPUs | 2× NVIDIA RTX PRO 6000 Blackwell (97,887 MiB VRAM each) | Driver `580.95.05` (CUDA 13.0); Blackwell `sm_120` needs `cu128` if GPU opt-in is tested; no system `nvcc` on `PATH` |
| **Root Disk (`/`)** | **`/dev/nvme0n1p2` (894 GB total, 884 GB used, ~9.7 GB free, 99%)** | **CRITICAL CONSTRAINT:** Never install duplicate CUDA PyTorch wheels (~3.5 GB) onto `/` |
| `/data1`, `/data2` | 7.0 TB NVMe drives (`drwxr-xr-x root:root`) | Non-writable by user `ordillo`; cannot store artifacts there |
| `/dev/shm` | `tmpfs` (252 GiB total, ~23 MiB used) | Ideal ephemeral scratch for `UV_CACHE_DIR` and temporary test outputs |
| System Compilers | `gcc`, `g++`, `gfortran`, `cmake`, `git` (`/usr/bin/*`) | Present; `xtb` binary not on system `PATH` (not needed on Linux v4.0.2) |

> [!WARNING]
> **Disk Discipline Rule (Mandatory for Stages 2–7):** Root `/` has **~9.7 GB free**. All agents MUST reuse `/home/ordillo/tests/.venv-upstream` and `/home/ordillo/tests/.cache`, set `UV_CACHE_DIR=/dev/shm/ordillo-uv-cache` (cleaning `/dev/shm/ordillo-uv-cache` after package installs), write large transient benchmark/test scratch files under `tmp_path` or `/dev/shm`, and never modify `/home/ordillo/miniconda3` environments. If GPU (`--extra cu128`) verification is ever run, place that ephemeral virtualenv in `/dev/shm/venv-cu128`.

### 2.3 Verified Workspace Toolchain & Upstream Python 3.10 Environment

Without modifying any files outside `/home/ordillo/tests` or dirtying tracked git files, the complete upstream environment was provisioned and smoke-tested inside `/home/ordillo/tests/`:

- **Standalone Tools (`/home/ordillo/tests/.tools`, 146 MB):**
  - `uv 0.13.9`: `/home/ordillo/tests/.tools/bin/uv`
  - `ruff 0.17.6`: `/home/ordillo/tests/.tools/bin/ruff`
  - Managed CPython `3.10.22`: `/home/ordillo/tests/.tools/python`
- **Locked Upstream Virtualenv (`/home/ordillo/tests/.venv-upstream`, 1.2 GB):**
  - Created via `uv sync --directory /home/ordillo/tests/SLICES --locked --extra cpu --no-install-project` plus `pytest==9.2.0` and `pytest-cov==7.1.0`.
  - Key locked versions: `torch==2.9.1+cpu`, `nequip==0.17.1`, `pymatgen==2025.10.7`, `ase==3.29.0`, `matscipy==1.3.1`, `numpy==2.2.6`, `scipy==1.15.3`, `networkx==3.4.2`, `spglib==2.7.0`, `e3nn==0.6.0`, `einops==0.8.2`.
  - `--no-install-project` deliberately avoids generating `src/slices.egg-info` in either worktree, enabling side-by-side execution against either `PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src` or `PYTHONPATH=/home/ordillo/tests/SLICES/src` under identical package versions.
- **Pre-Compiled NequIP Model Cache (`/home/ordillo/tests/.cache`, 121 MB):**
  - Raw weights (`NEQUIP_CACHE_DIR=/home/ordillo/tests/.cache/nequip_raw`): `NequIP-OAM-S` (5.64 MB) and `NequIP-OAM-L` (78.5 MB) downloaded cleanly from Zenodo via `nequip.net`.
  - Compiled CPU TorchScript models (`SLICES_MODEL_CACHE=/home/ordillo/tests/.cache/slices/nequip`):
    - `NequIP-OAM-S-0.1__torchscript__cpu__torch2.9.1__nequip0.17.1.nequip.pth`
    - `NequIP-OAM-L-0.1__torchscript__cpu__torch2.9.1__nequip0.17.1.nequip.pth`
- **Network Findings:**
  - `https://pypi.org/simple/` responds in `0.64s` vs `3.28s` for upstream's default `https://pypi.tuna.tsinghua.edu.cn/simple/` in `pyproject.toml`. Use `--index-url https://pypi.org/simple` (or `UV_DEFAULT_INDEX=https://pypi.org/simple` when unlocked) for ad-hoc installs.
- **Empirical Smoke & Determinism Verification Results (against read-only `SLICES-upstream-baseline`):**
  1. `python -m slices.relax_backends --prepare`: Passed (`CsCl-type NaCl` relaxation in `1.65 s`, `E = -3.2291 eV/atom`, `a = 3.452 Å`).
  2. `python -m slices.gfnff_helper`: Passed (`methane`: 4 bonds, 6 angles in `legacy86_overlay` mode; `Na3MnCoNiO6` inner-product target tuple `(178.74144, 178.74144, 126, 61.23)` matched reference to `rtol=1e-6`).
  3. **Repeatability & Oxidation-State Finding:**
     - `NdSiRu.cif` (6 atoms): `E = -7.26759387 eV/atom`, repeated CPU runs yielded **exact `0.00e+00` difference** in lattice matrix, fractional coordinates, and energy; `match_check3` strict = `('1', '0', '0', '0.0', '0.25', '0.25')`. *(Note: `NdSiRu.cif` carries oxidation states in CIF site species, whereas reconstructed `Structure` uses neutral `Element` symbols; therefore direct `StructureMatcher()` without `ElementComparator()` or POSCAR round-trip returns `False`, while `SLICES.match_check*` uses POSCAR normalization + `ElementComparator()` and returns `'1'`. The Stage 2 baseline harness MUST test both exact array equality and `ElementComparator()` matching.)*
     - `Sr3Ru2O7.cif` (24 atoms conventional -> reduced to 12-atom primitive cell): `E = -6.79135010 eV/atom`, repeated CPU runs yielded **exact `0.00e+00` difference** in lattice, fractional coordinates, and energy; `match_check3` strict = `('1', '1', '0', '0.0', '0.5', '0.33333333333333337')`.
- **Standard Activation Snippet for All Subsequent Stages:**
  ```bash
  export PATH="/home/ordillo/tests/.tools/bin:/home/ordillo/tests/.venv-upstream/bin:$PATH"
  export PYTHONDONTWRITEBYTECODE=1
  export NEQUIP_CACHE_DIR="/home/ordillo/tests/.cache/nequip_raw"
  export SLICES_MODEL_CACHE="/home/ordillo/tests/.cache/slices/nequip"
  export UV_CACHE_DIR="/dev/shm/ordillo-uv-cache"
  export UV_LINK_MODE="copy"
  ```

---

## 3. Coding Style & Engineering Standards (`backup/v3-personal` + Google Python Style Guide)

Analysis of the 30 commits in `cea17da..backup/v3-personal` (`src/slices/core.py`, `mlip_relaxer.py`, `decoding_strategies.py`, `tobascco_net.py`, `utils.py`, `slices_cli.py`, `tests/`, `docs/api/`, `TECHNICAL.md`, `CHANGELOG.md`) merged with the **Google Python Style Guide** establishes the target standards for `slices-4-personal`:

### 3.1 Language & Prose Discipline
- **100% English-Only:** Zero Chinese/CJK characters anywhere in kept files, filenames, comments, docstrings, exception messages, CLI help, shell scripts, or documentation. (Preliminary scan found **59 CJK file/content hits** in `upstream/main`, including 34 lines in `src/slices/core.py`, 1 line in `src/slices/relax_backends.py`, 182 lines in `src/slices/utils.py`, 70 lines in `README.md`, 67 lines in `HANDOFF_workstation.md`, 2 CJK filenames in `docs/`, plus hits in `HTS/`, `benchmark/`, `data/`, `Dockerfile/`, `rundocker.sh`, and `MatterGPT/`.)
- **Factual Scientific Tone:** Follow commit `fbfb536` (*"Ensure consistent factual language across codebase"*): concise, objective technical descriptions; avoid marketing superlatives, exclamation-mark debug prints (`Cannot find bond!!!`), or informal slang in comments/docstrings.

### 3.2 Module Layout, Imports & Naming
- **Module Header & Docstring:** Every Python module begins with a concise Google-style module docstring describing its responsibility, key classes/functions, and relevant environment variables.
- **Imports (Google Style):**
  - One `import` per line (eliminate comma-joined imports such as `import os,sys,glob,json,io` and duplicate imports in `utils.py`/`core.py`).
  - Grouped in three blocks separated by a blank line: (1) Standard library, (2) Third-party (`numpy`, `scipy`, `pandas`, `networkx`, `sympy`, `pymatgen`, `ase`), (3) Local `slices.*` absolute imports.
  - Keep heavy optional MLIP imports (`torch`, `nequip`, `chgnet`, `mattersim`, `orb_models`, `mace`, `m3gnet`) **lazy inside adapter constructors/functions** so `SLICES(relax_model=None)` and encoding-only workflows import rapidly without loading deep-learning runtimes.
- **Section Dividers:** In large core modules (`core.py`), use clean `# === Section Name ===` headers (as in `backup/v3-personal`) to separate logical groups (Exceptions, Initialization, Graph Construction, String Serialization, Validation & Canonicalization, GFN-FF Target Generation, ZL* Optimization, Relaxation & Matching) without altering method names.
- **Public Package Exports (`src/slices/__init__.py`):** Export `SLICES`, `__version__ = "4.0.2"`, and public exception classes in `__all__` (upstream `__init__.py` is currently a 1-line empty file).
- **Naming:** Preserve all existing public method/parameter names on `SLICES`, `Net`, `SystreDB`, `utils`, `utils_wyckoff`, `gfnff_helper`, and `relax_backends` (e.g., `structure2SLICES`, `SLICES2structure`, `splitRun`) for 100% backward compatibility with `HTS/`, `benchmark/`, `data/`, and external callers. New modules/functions follow strict `snake_case` functions/variables, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants.

### 3.3 Docstrings & Type Annotations
- **Google-Style Docstrings:** Mandatory on all public classes, methods, and functions using standard sections (`Args:`, `Returns:`, `Raises:`, `Attributes:`, `Examples:`, `References:`). Fix stale docstring defaults found in upstream (e.g., `core.py` docstrings saying `strategy` defaults to `3` when signature is `strategy=4`, `dupli_check` saying `Defaults to True` when signature is `False`, `relax()` docstring saying `60 seconds` when decorator is `360`).
- **Type Annotations (Python 3.10+):**
  - Full PEP 484 / PEP 604 (`X | None`) annotations on all newly ported/created modules (`exceptions.py`, `mlip_relaxer.py`, `decoding_strategies.py`, `cli.py`, `tests/`).
  - Add accurate parameter and return type annotations (`from __future__ import annotations` + `TYPE_CHECKING` guards where helpful) to `src/slices/` modules without changing runtime coercion or default values.

### 3.4 Exceptions, Logging, Subprocesses & Cross-Platform Safety
- **Structured Exception Hierarchy (`src/slices/exceptions.py`, re-exported in `slices.core` and `slices`):**
  - `SLICESError(Exception)` -> `SLICESEncodingError`, `SLICESDecodingError`, `GraphTopologyError` -> `LatticeBasisError`, `CocycleBasisError`, `GFNFFExecutionError` (alias `XTBExecutionError`), `MLIPRelaxationError`, `TimeoutException`.
  - `RelaxBackendError(SLICESError, RuntimeError)` and `ModelDownloadError(SLICESError, RuntimeError)` inherit both `SLICESError` and `RuntimeError` so both upstream `RuntimeError` catches and personal `SLICESError` catches succeed.
  - **Contract Rule:** Do NOT change methods that return `bool` or `None` on failure (`check_SLICES`, `check_SLICES_basic`, `SLICES2space_group_number`, `get_inner_p_target`, `to_structures` relaxation fallback returning `[std, opt], 0`) to raise uncaught exceptions.
- **OS-Agnostic File & Process Handling:**
  - Replace shell calls (`os.system('rm -rf ...')`, `os.system('cp -r ...')`) in `utils.py` with `pathlib` / `shutil.rmtree` / `shutil.copytree` and `subprocess.run` with explicit argument lists (porting the safe patterns from `backup/v3-personal:src/slices/utils.py` while keeping upstream v4.0.2's `_SUBMITTED_SLURM_JOBS` tracking!).
  - Cross-platform `function_timeout`: use `signal.SIGALRM` on POSIX main thread (preserving exact upstream Linux behavior) and fall back cleanly when `SIGALRM` is unavailable (Windows or non-main threads).
- **Formatting & Linting (`ruff`):** Configure `[tool.ruff]` in `pyproject.toml` (`target-version = "py310"`, `line-length = 100`) and `[tool.pytest.ini_options]` (markers from `backup/v3-personal/pytest.ini` plus `baseline` and `gfnff`).

---

## 4. Explicit Math / Algorithm Freeze Boundary

> [!IMPORTANT]
> Any edit to a frozen symbol below is limited strictly to **non-behavioral** changes (docstrings, comments, English string translation of non-parsed human messages, import cleanup, type hints). Every mathematical formula, array ordering, rounding call (`round(..., 5)`, `round(..., 2)`), graph traversal order, random-number draw sequence, optimizer tolerance, and fallback branch **MUST remain numerically invariant** against `/home/ordillo/tests/SLICES-upstream-baseline`.

### 4.1 Frozen Modules, Classes, Functions & Constants

| File | Frozen Symbols / Logic | Invariance Requirement |
|---|---|---|
| [config.py](file:///home/ordillo/tests/SLICES/src/slices/config.py) | `OFFSET` (27 supercell cells; index 13 is `[0,0,0]`), `LJ_PARAMS_LIST` (Z=1..118), `PERIODIC_DATA` | Exact bit-for-bit array/DataFrame values and row order |
| [utils_wyckoff.py](file:///home/ordillo/tests/SLICES/src/slices/utils_wyckoff.py) | `sg_encoding` (all 230 space groups), `tokenize_enc`, `get_tokenized_enc`, `get_space_group_num`, `get_space_group_num_from_letter_enc` | Exact string/int bijection across all space group numbers 1–230 and symbols |
| [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py) | `SystreDB.*`, `Net.__init__`, `get_cocycle_basis`, `get_cycle_basis`, `simple_cycle_basis`, `iter_cycles`, `linear_independent_vectors`, `get_lattice_basis`, `check_linear_dependency`, `assign_ip_matrix`, `convert_params`, `get_metric_tensor`, `barycentric_embedding`, `get_2d_params`, `get_3d_params`, `vertex_positions`, `is_integral`, `kernel`, `minimal`, `eon_projection`, `projection`, `lattice_arcs`, `cycle_cocycle`, `cycle_cocycle_I` | Exact basis matrices, projections, metric tensors, and arc coordinates. *(Additive helper `Net.clear_cache()` from `backup/v3-personal` and `self._graph.nodes[node]` NX 2.x fix in unused `nodes_iter` must be audited in Stage 2 before inclusion.)* |
| [_vendor/gfnff*](file:///home/ordillo/tests/SLICES/src/slices/_vendor/gfnff/__init__.py) & [gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py) | `libgfnff.so.0.1.1`, `gfnff.libs/*`, `param_gfnff_legacy86.xtb`, `GFNFFCalculator`, `GFNFFTopology`, `parse_nbf_text`, `run_gfnff_helper`, `_selected_params` | Untouched binary & `legacy86_overlay` default output (`blist`, `vbond`, `alist`, `vangl`) |
| [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py) | `NEQUIP_MODEL_IDS`, `NEQUIP_PLANS`, `RELAX_MODELS`, `OPTIMIZERS`, `FIRE_PRESTEPS=10`, `OVERLAP_TRIGGER=0.5`, `OVERLAP_TARGET=0.7`, `COLLAPSE_VOLUME=2.0`, `choose_device`, `resolve_relax_model`, `make_relaxer`, `NequIPRelaxer.relax`, `closest_pair_ratio`, `remove_overlaps` (`seed=0`), `preoptimize`, `_collapse_guard`, `_optimize`, `_cell_filter` | Exact relaxation trajectories, energies, overlap pre-optimization, and collapse retry (`NequIP-OAM-S + FIRE`) for `auto`, `none`, `nequip-s+l`, `nequip-m+l`, `nequip-l`. *(Extension hook for optional MLIPs in `make_relaxer` / `resolve_relax_model` must ONLY dispatch when `name` is outside upstream `RELAX_MODELS`.)* |
| [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py) (Encoding & Graph) | `SLICES.__init__` defaults, `get_index_list_allow_duplicates`, `check_element`, `check_2D`, `check_3D`, `get_dim`, `cif2structure_graph`, `structure2structure_graph`, `to_primitive_if_smaller`, `_run_with_primitive_fallback`, `from_cif`, `structure2crystal_graph_rep`, `_crystal_graph_rep`, `structure2SLICES`, `structure2randomSLICES` | Exact `SLICES` strings for strategies 1–4, primitive-cell fallback behavior, and identical augmented sets under fixed `random.seed` |
| [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py) (Parsing, Validation & Canonical) | `from_SLICES`, `_first_element_index`, `get_slices_by_strategy`, `get_slices1..4`, `to_SLICES`, `check_structural_validity`, `check_SLICES`, `check_SLICES_basic`, `get_canonical_SLICES` (`custom_sort_rule`), `SLICES2formula`, `SLICES2space_group_number` | Exact boolean validity results, canonical string outputs, formulas, and space group numbers |
| [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py) (Decoding, ZL* & Matching) | `get_nbf_blist`, `get_inner_p_target`, `get_inner_p_target_debug`, `convert_graph`, `get_uncovered_pair`, `get_uncovered_pair_lj`, `get_covered_pair_lj`, `get_rescaled_lattice_vectors`, `get_coordinates`, `convert_params`, `initialize_x_bounds`, `all_distances`, `func`, `func_check`, `to_structures`, `SLICES2structure`, `to_relaxed_structure`, `to_4structures`, `relax`, `relax_large_cell1`, `relax_large_cell2`, `match_check`, `match_check3`, `match_check4` | Exact `[std, opt, opt2]` structures, `final_energy_per_atom`, and `match_check*` return tuples |

### 4.2 Preliminary Seed Items for the Deferred Core/Algorithm Register
Stage 1 inspection already identified six critical items that **MUST NOT** be silently applied to the frozen core and instead seed `docs/migration/DEFERRED_CORE_REGISTER.md` in Stage 2:
1. **`core.py:1293-1294` & `core.py:1312-1313` (`get_uncovered_pair_lj` / `get_covered_pair_lj`):** Both heteronuclear branches average `lj_param[self.atom_types[i[0]]]` with **itself** (`i[0]` twice instead of `i[0]` and `i[1]`). Fixing this would alter `func()` LJ repulsive terms and shift `fmin_l_bfgs_b` ZL* trajectories relative to v4.0.2. **Decision: Keep frozen; log in Register.**
2. **`backup/v3-personal` `to_structures()` auto-injection of `MultiStartOptimizer`, `AdaptiveConvergence`, and `ProgressiveRelaxer`:** Personal fork modified default `to_structures()` to run 3-start random L-BFGS-B perturbations and multi-stage relaxation whenever `decoding_strategies` was importable. **Decision: Do NOT wire into default `to_structures()` / `SLICES2structure()`; expose strictly via explicit opt-in (`robust_SLICES2structure()` or `decoding_strategies` API) and log core integration in Register.**
3. **`backup/v3-personal` `tobascco_net.py` changes (`is_integral` float tolerance, `CycleBasisOptimizer` in `get_lattice_basis`, iterative stack `iter_cycles` with `max_depth`):** Alter cycle/lattice basis selection on edge-case topologies. **Decision: Keep `tobascco_net.py` math frozen at v4.0.2; keep `CycleBasisOptimizer` standalone in `decoding_strategies.py` and log `Net` changes in Register.**
4. **`tobascco_net.py:359` & `514` (`np.random.choice` / `np.random.shuffle`):** Unused draws mutate global `np.random` state whenever `simple_cycle_basis()` / `get_lattice_basis()` runs. **Decision: Audit in Stage 2 whether removing dead draws affects any internal call; if any risk to global RNG parity exists, keep frozen and log in Register.**
5. **`core.py:5-9` import-time global side effects (`os.environ["OMP_NUM_THREADS"] = "1"`, `os.environ["PYTHONWARNINGS"] = "ignore"`, `warnings.filterwarnings`):** Audit in Stage 2 whether scoping or preserving `OMP_NUM_THREADS` affects multi-threaded BLAS determinism in `np.linalg.cholesky` / `fmin_l_bfgs_b`.
6. **`core.py:139` (`check_element` Z < 87 check) vs `gfnff_helper.py` (Z <= 103 support):** Upstream `gfnff_helper` supports Z=87..103 via modern fallback, while `check_element` still checks `Z < 87` (for legacy MP/xtb filtering). **Decision: Keep `check_element` frozen; document clearly in docstring and log in Register.**

---

## 5. Stage 2 Audit Plan (Three Non-Overlapping Slices)

Stage 2 (`Audit`) will fan out into **three strictly disjoint audit slices** that produce markdown audit reports under `/home/ordillo/tests/SLICES/docs/migration/` without modifying any SLICES source code.

### Slice 2A: Personal Fork Diff & Portability Audit (`cea17da..backup/v3-personal`)
- **Owner Scope:** All 30 commits and all touched/added files in `backup/v3-personal` (`src/slices/{core.py,mlip_relaxer.py,decoding_strategies.py,tobascco_net.py,utils.py,__init__.py,bin/*}`, `slices_cli.py`, `tests/**`, `tools/**`, `configs/**`, `docker/**`, `tutorial/**`, `docs/api/**`, `README.md`, `TECHNICAL.md`, `CHANGELOG.md`, `.gitignore`, `.github/workflows/tests.yml`, `pytest.ini`).
- **Tasks:**
  1. Produce a commit-by-commit and file-by-file inventory classifying every change into one of five buckets:
     - `PORT_ADDITIVE`: Safe new modules/APIs (`mlip_relaxer.py` adapted to v4.0.2 `make_relaxer` protocol, `cli.py` adapted to `relax_model="auto"` default, opt-in `decoding_strategies.py` & `robust_SLICES2structure`, `exceptions.py`, `tests/`).
     - `PORT_CROSS_PLATFORM`: Safe OS-agnostic improvements (`function_timeout` non-POSIX fallback, `shutil`/`pathlib` file ops in `utils.py`, optional non-Linux GFN-FF/xtb fallback when `libgfnff.so` cannot load on macOS/Windows — **note:** do NOT re-commit 60 MB Linux/Windows xtb binaries into git!).
     - `PORT_STYLE_DOCS`: Docstrings, type hints, `TECHNICAL.md`, `docs/api/*.md`, `CHANGELOG.md`, `.gitignore` improvements.
     - `DEFER_CORE_FREEZE`: Any modification to frozen math/graph/ZL*/default-relaxation paths (record exact file/lines, rationale, and impact in `DEFERRED_CORE_REGISTER.md`).
     - `DROP_OBSOLETE`: Tracked `__pycache__/*.pyc` binaries (`301c75f`), root `xtb` / `test.slices` scratch files, M3GNet-as-default `pyproject.toml` (`version = "2.0.12"`), and benchmark CSV deletions (`cea17da..backup/v3-personal` deleted large benchmark CSVs that must be **kept** per our scope rule!).
  2. Design the clean integration contract between upstream `relax_backends.py` (`make_relaxer(relax_model, optimizer)` returning `(relaxer, resolved_name)`) and personal `mlip_relaxer.py` (`chgnet`, `mattersim`, `orbv3`, `mace`, optional legacy `m3gnet`) so `relax_model="auto"` / `"nequip-*"` / `None` remain 100% untouched while opt-in models work seamlessly with `NequIPRelaxer`-compatible return dicts (`{"final_structure": ..., "trajectory": SimpleNamespace(energies=[total_e])}`).
- **Output File:** `/home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md`

### Slice 2B: Upstream v4.0.2 Architecture, Scope Coupling & CJK/Style Audit (`142298b..upstream/main`)
- **Owner Scope:** All 23 upstream commits (`142298b..94ef8e0`) and the full `upstream/main` directory tree (`src/slices/`, `pyproject.toml`, `setup.cfg`, `uv.lock`, `README.md`, `HANDOFF_workstation.md`, `tools/`, `examples/`, `docs/`, `Dockerfile/`, `rundocker.sh`, `entrypoint_*.sh`, `HTS/`, `benchmark/`, `data/`, and `MatterGPT/` removal impact).
- **Tasks:**
  1. **Complete CJK & Translation Ledger:** Inspect all **59 CJK hits** identified in Stage 1 (`src/slices/core.py`, `src/slices/relax_backends.py:251`, `src/slices/utils.py`, `README.md`, `HANDOFF_workstation.md`, `docs/SLICES-MatterGPT_<CJK-intro:\u4ecb\u7ecd>.pdf`, `docs/utils_<CJK-force-local:\u5f3a\u5236\u672c\u5730\u8fd0\u884c>.py`, `Dockerfile/docker-compose.yml`, `rundocker.sh`, `data/`, `HTS/`, `benchmark/`), distinguishing files to translate/rename vs files deleted with `MatterGPT/` in Stage 4, and verifying no CJK string is parsed programmatically.
  2. **`MatterGPT/` Decoupling Audit (Critical for Stage 4):** Audit every reference to `MatterGPT/` across kept files:
     - `examples/3.benchmark_relax_models.py` lines 49–50 reference `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` (which also exists under `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv`!) and `MatterGPT/2_decode/workflow/chemPotMP.json` (which also exists in `HTS/` and `benchmark/`!). Plan exact path repointing / fixture retention before `MatterGPT/` is deleted in Stage 4.
     - `tools/workstation_check.sh` & `HANDOFF_workstation.md` & `entrypoint_set_cpus_gradio.sh` & `pyproject.toml` (`description`, `einops`, `gui = ["gradio"]` extra) & `README.md` MatterGPT sections: specify exact updates needed when `MatterGPT/` is removed.
  3. **`HTS/`, `benchmark/`, and `data/` Baseline Audit:** Inventory all scripts in `HTS/` and `benchmark/` (including legacy `relax_model="m3gnet"` call sites noted in `HANDOFF_workstation.md:95`, SLURM/PBS scripts, and `from slices import check_SLICES` in `benchmark/.../train_prior.py:15` — note upstream `__init__.py` doesn't even export `check_SLICES`!). Determine what `src/slices/__init__.py` exports or compatibility notes are needed without altering historical benchmark data.
  4. **Packaging & `utils.py` Safety Audit:** Audit `pyproject.toml` (Tsinghua TUNA `default = true` index vs PyPI, optional dependencies `[dev]`, `[mlip]`, `[project.scripts]`), `setup.cfg` (`manylinux2014_x86_64` wheel tag implications), and `src/slices/utils.py` (`cancel_all_jobs` / `show_progress` `pgrep -f python` process-kill hazard).
- **Output File:** `/home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md`

### Slice 2C: Golden Baseline Equivalence Harness & Test Suite Design
- **Owner Scope:** Equivalence test architecture against `/home/ordillo/tests/SLICES-upstream-baseline`, golden fixture specification, and triage of the 16 test files in `backup/v3-personal:tests/` + `backup/v3-personal:tools/tests/`.
- **Tasks:**
  1. **Golden Reference Corpus Selection (12–20 Stratified Crystals):** Select a compact, fast, deterministic corpus from `examples/` (`NdSiRu.cif`, `Sr3Ru2O7.cif`) and `data/mp20_nonmetal/` covering:
     - All 7 crystal systems & multiple centering types (`P`, `I`, `F`, `C`, `R`) for `utils_wyckoff` / strategy-4 tokens;
     - Single-atom primitive cell (`cocycle_rep is None` branch in `to_structures`);
     - Conventional cell reducible to smaller primitive cell (`to_primitive_if_smaller` branch);
     - High-coordination structure (`>19` neighbors in `get_nbf_blist`);
     - Heavy / lanthanide / actinide elements (`Z <= 86` and `87 <= Z <= 94` if present);
     - Structure triggering `preoptimize` (`closest_pair_ratio < 0.5`) in `relax_backends.py`;
     - Invalid / rank-deficient (`H1 < 3`) / duplicate-edge SLICES strings for `check_SLICES` & `from_SLICES`.
  2. **Golden Snapshot & Dual-Tree Runner Specification:** Design `tests/baseline/generate_golden.py` and `tests/baseline/test_golden_equivalence.py` that load ground-truth outputs generated from `/home/ordillo/tests/SLICES-upstream-baseline/src` and assert:
     - **Exact equality (`==`)** on `structure2SLICES` (strategies 1–4), `from_SLICES` (`atom_types`, `edge_indices`, `to_jimages`, `space_group_num`), `check_SLICES`, `check_SLICES_basic`, `get_canonical_SLICES`, `SLICES2formula`, `SLICES2space_group_number`, `get_nbf_blist`, and `structure2randomSLICES` (with seeded `random.seed(42)`).
     - **Tight numerical invariance (`np.allclose(..., rtol=0, atol=1e-12)` on CPU)** on `get_inner_p_target` (`inner_p_target`, `colattice_inds`, `colattice_weights`), `to_structures()` intermediate structures (`std`, `opt`) and NequIP-relaxed `opt2` (`lattice.matrix`, `frac_coords`, `final_energy_per_atom`), and `match_check3` / `match_check4` tuples.
  3. **Personal Test Suite Triage:** Audit each of the 16 test files in `backup/v3-personal:tests/{unit,integration,regression}/` to map what converts directly to `nequip-s+l` / `gfnff_helper`, what becomes `@pytest.mark.mlip` optional tests, and what new unit tests are needed for v4.0.2's `relax_backends.py`, `gfnff_helper.py`, and `utils_wyckoff.py`.
  4. **Consolidate `DEFERRED_CORE_REGISTER.md`:** Merge candidate core/algorithm findings from Slices 2A, 2B, and 2C into `/home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md`.
- **Output Files:** `/home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md` and `/home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md`

---

## 6. Full 7-Stage Pipeline Acceptance & Verification Criteria

| Stage | Goal | Key Deliverables | Mandatory Verification Gate |
|---|---|---|---|
| **1. Plan** | Repo clone, remotes, branches, locked read-only baseline worktree, toolchain/env verification, migration blueprint | `/home/ordillo/tests/SLICES` (`slices-4-personal` @ `94ef8e0`), `backup/v3-personal` @ `301c75f`, `SLICES-upstream-baseline` @ `94ef8e0`, `.venv-upstream`, `docs/migration/PLAN.md` | Exact SHAs verified; `git diff upstream/main` empty (only untracked `docs/migration/PLAN.md`); `gfnff_helper` + `relax_backends --prepare` + round-trip determinism verified; `/` free space >= 9 GB |
| **2. Audit** | Exhaustive 3-slice read-only audit of personal fork, upstream v4.0.2 + CJK/scope couplings, and golden harness design | `AUDIT_FORK_DIFF.md`, `AUDIT_UPSTREAM_STYLE.md`, `AUDIT_BASELINE_HARNESS.md`, `DEFERRED_CORE_REGISTER.md` | Every personal commit (`30`) and upstream commit (`23`) accounted for; all `59` CJK locations mapped; zero edits to tracked source files |
| **3. Review** | Architectural review, conflict resolution, freeze-boundary sign-off, and execution specification for Stage 4 + golden baseline generation | `docs/migration/REVIEW_SIGNOFF.md` + frozen golden reference fixtures generated from `SLICES-upstream-baseline` & passing baseline `pytest` against untouched v4.0.2 | Golden baseline test suite passes 100% against both `SLICES-upstream-baseline` and unmodified `slices-4-personal` before a single line of `src/slices/` is edited |
| **4. Refactor** | Prune `MatterGPT/`, translate CJK in kept code, clean module structure, port additive `exceptions.py`, `mlip_relaxer.py`, `decoding_strategies.py` (opt-in), `cli.py`, cross-platform `utils.py`/helpers, repoint `examples/3.benchmark_relax_models.py` | Refactored `src/slices/`, `pyproject.toml`, `examples/`, `MatterGPT/` removed; `data/`, `benchmark/`, `HTS/` preserved | Golden baseline equivalence suite passes **100% (`atol=1e-12` on CPU)**; CLI (`slices encode/decode/validate/canonicalize`) works; no `MatterGPT` broken imports in kept examples/tools |
| **5. Refine** | Complete Google-style docstrings, Python 3.10+ type annotations, port & expand `tests/{unit,integration,regression,baseline}/`, `ruff` lint/check compliance, edge-case hardening of additive modules | Comprehensive `tests/` suite, clean `ruff` diagnostics, verified optional MLIP graceful-skip / adapter mocks | `pytest` 100% green (zero failures); `ruff check src/ tests/ examples/` passes with zero errors; zero CJK characters in `src/`, `tests/`, `examples/`; golden equivalence still 100% invariant |
| **6. Document** | Rewrite/translate `README.md`, `TECHNICAL.md`, `docs/api/*.md`, `CHANGELOG.md`, `configs/`/Docker docs, and migration lab log in 100% clear factual English | Updated `README.md`, `TECHNICAL.md`, `CHANGELOG.md`, `docs/`, `docs/migration/LAB_LOG.md`, updated `DEFERRED_CORE_REGISTER.md` | Repo-wide CJK scan across all kept files returns **0 hits**; all doc code snippets and links verified; `SLICES` v4.0.2 + optional MLIPs + CLI accurately documented |
| **7. Systematize / Organize** | Final directory hygiene, `.gitignore`, `pyproject.toml` extras/metadata polish, reproducible test/lint runner scripts, clean atomic git commit history on `slices-4-personal`, final sign-off report | Clean git history on `slices-4-personal`, `docs/migration/FINAL_REPORT.md` | Full verification suite passes in one command (`ruff`, `pytest`, golden dual-tree diff against `SLICES-upstream-baseline`, CJK=0 check, `git status` clean, `SLICES-upstream-baseline` untouched at `94ef8e0`, `/` disk >= 5 GB free, **zero remote pushes**) |
