# Changelog

All notable changes to SLICES are documented in this file. Commit hashes reference the local `slices-4-personal` branch (rebased onto upstream `v4.0.2`, commit `94ef8e0`) and upstream `xiaohang007/SLICES` tags.

---

## [Unreleased — Wave 1 (`SAFE_NOW`)] — 2026-11-25 — Zero-Drift Bugfixes & Memory-Safety Guards

Post-migration empirical re-evaluation across `125,174` SLICES strings, `18,093` MP-20 CIFs, `3,883` GFN-FF topology evaluations, and controlled CPU `NequIP-OAM-S/L` A/B benchmarks ([REEVAL_SYNTHESIS.md](docs/migration/reeval/REEVAL_SYNTHESIS.md)), followed by **15 zero-drift (`0.0` ULP, `89/89` golden baseline parity at `atol=1e-12`) Wave 1 fixes** across `src/slices/{exceptions,core,gfnff_helper,tobascco_net,relax_backends}.py`:

### Fixed

- **Critical Fortran Memory-Safety Guard (`DEF-028`, `src/slices/gfnff_helper.py`):** Enforced `1 <= Z <= 103` (`H..Lr`) in `parse_nbf_text` prior to calling bundled `libgfnff.so.0.1.1` or external `xtb`, raising `GFNFFExecutionError` naming unsupported trans-lawrencium elements (`Rf..Og`) instead of performing unguarded out-of-bounds Fortran parameter-table reads.
- **Instance-Reuse Space-Group Corruption (`DEF-023`, `src/slices/core.py`):** Removed the stale `if self.unstable_graph:` branch inside `SLICES.SLICES2space_group_number` and reset `self.unstable_graph = False` at `from_SLICES` entry, eliminating instance-reuse space-group collapse (`91.62% -> 4.68%` on MP-20) while preserving `100%` fresh-instance parity.
- **NumPy 2.x/3.x Matrix Removal & Rectangular Bounds (`DEF-011`, `DEF-034`, `src/slices/tobascco_net.py`):** Replaced all `np.matrix(...).I` calls in `Net.{eon_projection,projection,cycle_cocycle_I}` with `np.linalg.inv(...)` (`0.000e+00` ULP diff across `2,374` MP-20 crystals, `0` remaining `np.matrix` occurrences), and migrated `Net.linear_independent_vectors` to `np.atleast_2d(np.asarray(...))` with `r == 0` and `counter < r - 1` bounds guards against `IndexError`.
- **Global RNG Purity & Stateless `Net` Defaults (`DEF-004`, `DEF-010`, `src/slices/tobascco_net.py`):** Removed dead `np.random.choice` / `np.random.shuffle` calls in `Net.{simple_cycle_basis,get_lattice_basis}` (`0` remaining `np.random` mutations) and replaced mutable `[]` / `{}` default arguments in `Net.{iter_cycles,vertex_positions}` with `None` guards.
- **Import-Time Environment & Warning Hygiene (`DEF-005`, `DEF-009`, `src/slices/core.py`, `src/slices/relax_backends.py`):** Replaced unconditional overrides in `core.py` with `os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")` and `os.environ.setdefault("OMP_NUM_THREADS", "1")`, removed `PYTHONWARNINGS="ignore"` and blanket filters, scoped `DeprecationWarning` suppression strictly to `spglib`, imported `BrunnerNNReciprocal` first, and locally suppressed ASE's `ExpCellFilter` `DeprecationWarning` in `_cell_filter` while keeping empirically superior `ExpCellFilter` (`93.48%` vs `89.13%` strict match over `FrechetCellFilter`) as default.
- **Strategy 1–4 Formula Extraction (`DEF-012`, `src/slices/core.py`):** Replaced fragile regex matching in `SLICES.SLICES2formula` with grammar-aware Strategy 1/2/3/4 token extraction (fixing silent wrong Strategy 1 formulas, Strategy 2 underscore failures, and digit-free `AttributeError`s; returning `None` cleanly on malformed strings).
- **Parser Validation & Structured Exceptions (`DEF-024` Gaps 1/2/3b/4, `DEF-018`, `DEF-026`, `src/slices/exceptions.py`, `src/slices/core.py`):**
  - Updated `SLICESEncodingError(SLICESError, ValueError)` and `SLICESDecodingError(SLICESError, ValueError)` to dual-inherit from `ValueError`.
  - Exported `VALID_GRAPH_METHODS = ("econnn", "crystalnn", "brunnernn", "mininn")` and raised `ValueError` on invalid `graph_method` in `SLICES.__init__`, `structure2structure_graph`, and `get_dim`.
  - Guarded 0-site `Structure` inputs with `SLICESEncodingError` in `check_element`, `structure2structure_graph`, and `to_primitive_if_smaller`.
  - Raised `SLICESDecodingError` in `from_SLICES` for unsupported strategies (including encode-only `strategy=2`) and zero-edge strings, enforced `0 <= idx < num_atoms` and 3-character Strategy-4 edge labels while preserving golden `E01`–`E05` exception contracts and lenient trailing-token parsing.
- **Periodic Self-Image & Sheared-Cell Validity (`DEF-025`, `DEF-019` Part 2, `src/slices/core.py`):** Updated `SLICES.check_structural_validity` to require `isinstance(str1, IStructure)` (`TypeError`), return `False` on 0-site structures, and check all non-trivial site and periodic image distances via `get_neighbor_list(r=0.5 + 1e-9)` (catching collapsed 1-atom and sheared short-image cells with `0/18,093` MP-20 flips).
- **Decoding Diagnostics, Clamps & `>40`-Atom Relaxation (`DEF-008`, `DEF-021` Wave 1, `DEF-027`, `DEF-030`, `DEF-032`, `src/slices/core.py`):**
  - Forwarded `fmax=self.fmax, steps=self.steps` in both branches of `relax_large_cell2` (`>40` atoms).
  - Raised `LatticeBasisError` and `CocycleBasisError` in `to_structures()` on invalid 3D lattice or multi-vertex cocycle bases instead of crashing with `NoneType * float` `TypeError`.
  - Guarded non-finite `vangl` entries with `np.isfinite` in `get_inner_p_target*`, canonicalized bonded pairs as `(min(u, v), max(u, v))` in `get_uncovered_pair`, and mirrored `func()`'s `1e-10`/`1e-8` distance clamps in `func_check()`.

### Documentation

- Added four empirical re-evaluation reports under `docs/migration/reeval/` ([REEVAL_SYNTHESIS.md](docs/migration/reeval/REEVAL_SYNTHESIS.md), [REEVAL_MATH_OPT.md](docs/migration/reeval/REEVAL_MATH_OPT.md), [REEVAL_GRAPH_RELAX.md](docs/migration/reeval/REEVAL_GRAPH_RELAX.md), [REEVAL_RUNTIME_PARSE.md](docs/migration/reeval/REEVAL_RUNTIME_PARSE.md)), expanded [DEFERRED_CORE_REGISTER.md](docs/migration/DEFERRED_CORE_REGISTER.md) to 34 entries (`DEF-001`–`DEF-034`), and synchronized Wave 1 API notes in `docs/api/API_{CORE,GRAPH,CONFIG}.md`.

---

## [4.0.2-personal] — 2026-11-25 (`slices-4-personal`)

Clean scientific-engineering migration of personal enhancements onto upstream **SLICES v4.0.2** (`94ef8e0`), maintaining **100% baseline numerical parity (`89/89` golden equivalence tests at `atol=1e-12`)** against immutable upstream v4.0.2 while removing unrelated generative-model bloat, eliminating host-safety hazards, and adding opt-in capabilities, CLI tooling, Google-style linting, and a unified test suite.

### Added

- **Golden Baseline Equivalence Harness (`e0142f8`):** Added `tests/baseline/` (`generate_golden.py`, `test_golden_equivalence.py`, frozen fixtures) verifying 89 deterministic assertions across encoding, validation, canonicalization, periodic net topology, GFN-FF targets, ZL\* optimization, and NequIP relaxation (`atol=1e-12`, `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`).
- **Structured Exception Hierarchy & Lazy Top-Level Exports (`49237f6`):**
  - Added `src/slices/exceptions.py` defining `SLICESError`, `SLICESEncodingError`, `SLICESDecodingError`, `GraphTopologyError`, `LatticeBasisError`, `CocycleBasisError`, `GFNFFExecutionError` (`XTBExecutionError` alias), `MLIPRelaxationError`, `TimeoutException`, and sibling dual-inheriting `RelaxBackendError(SLICESError, RuntimeError)` / `ModelDownloadError(SLICESError, RuntimeError)`.
  - Added PEP 562 lazy loading in `src/slices/__init__.py` exporting `__version__ = "4.0.2"`, exception classes eagerly (zero startup overhead), and lazy `SLICES` + `check_SLICES(...)`.
  - Added `SLICES.structure2SLICESAug_atom_order(...)` and lazy hook `SLICES.robust_SLICES2structure(...)` in `src/slices/core.py`.
  - Added `Net.clear_cache()` and NetworkX 3.x-compatible `Net.nodes_iter(data=...)` in `src/slices/tobascco_net.py`.
  - Added non-Linux external `xtb` fallback (`SLICES_XTB_PATH`, `XTB_MOD_PATH`, `PATH` lookup) in `src/slices/gfnff_helper.py` when bundled Linux x86\_64 `libgfnff.so` cannot load.
  - Added `SLICES_FORCE_LOCAL` override in `src/slices/utils.py`.
- **Optional Multi-MLIP Adapters, Opt-In Robust Decoding, CLI, and Tooling (`1320773`):**
  - Added `src/slices/mlip_relaxer.py` providing lazy opt-in adapters (`chgnet`, `mattersim`, `orbv3` / `orb-v3`, `mace` / `mace-mp`, legacy `m3gnet`) reusing `relax_backends` overlap pre-optimization and cell-collapse guards with zero module-level `torch`/`tensorflow`/`keras` imports.
  - Added `src/slices/decoding_strategies.py` (`robust_decode`, `CycleBasisOptimizer`, `BondParameterFallback`, `MultiStartOptimizer`, `AdaptiveConvergence`, `ProgressiveRelaxer`, `is_approximately_integral`, `calculate_topology_timeout` / `calculate_xtb_timeout`) strictly isolated from default v4.0.2 decoding and using isolated `np.random.default_rng` seeds.
  - Added `src/slices/cli.py` registered as `[project.scripts] slices = "slices.cli:main"` (`--version`, `encode`, `decode`, `validate`, `canonicalize`, stdin `"-"` support).
  - Added `tools/validate_installation.py`, `tools/run_tests.py`, and `tools/benchmarks/run_comparison_test.py`.
- **Comprehensive v4.0.2 Test Suite (`8d9314b`):** Added `tests/conftest.py`, 11 unit test modules (`tests/unit/`), end-to-end round-trip tests (`tests/integration/test_round_trip.py`), and regression edge-case tests (`tests/regression/test_edge_cases.py`), totaling `250 passed, 5 skipped, 0 failed` across the unified suite.
- **Documentation Suite (Stage 6):** Rewrote `README.md`, authored `TECHNICAL.md`, `CHANGELOG.md`, `docs/README.md`, and 6 API reference documents under `docs/api/`, removing stale Sphinx v1/v2 HTML output while preserving `docs/{SLICES_demo.png,figure_intro.png,win11_wsl2.png}` and `docs/migration/`.

### Changed

- **Packaging & Repository Hygiene (`984416b`, `ad4446b`):**
  - Relocated MP-20 Strategy-4 benchmark fixtures to `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` and `data/mp20_nonmetal/chemPotMP.json` (preserving existing 14,303-row `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv`), then removed `MatterGPT/`, `entrypoint_set_cpus_gradio.sh`, `HANDOFF_workstation.md`, root `__init__.py`, `src/slices/README.rst`, and legacy `MatterGPT`/CJK docs assets (~15.8 MiB pruned).
  - Updated `pyproject.toml` and refreshed `uv.lock` (removed `einops` and `gui = ["gradio"]`, added `[project.scripts]` and PEP 735 `[dependency-groups] dev`, preserved exact locked versions across all 10 core scientific packages).
  - Configured strict Google-style `[tool.ruff]` linting (`E`, `F`, `W`, `I`, `B`, `UP`, `SIM`, `RUF`, `D` with `pydocstyle.convention = "google"`) and `[tool.pytest.ini_options]` markers/exclusions; achieved `0` ruff diagnostics across `src/`, `examples/`, `tools/`, and `tests/` (`ad4446b`, verified `100%` docstring-stripped AST parity).
  - Repointed `examples/3.benchmark_relax_models.py`, `src/slices/gfnff_helper.py`, and `tools/workstation_check.sh` to the relocated MP-20 benchmark fixtures (`1320773`).
- **Complete English Translation (`49237f6`, `479f0a2`):**
  - Translated all CJK comments, docstrings, and console messages across `src/slices/{core,relax_backends,utils}.py` (`49237f6`) and across 28 baseline scripts in `HTS/`, `benchmark/`, and `data/` plus `Dockerfile/{Dockerfile,docker-compose.yml}` and `rundocker.sh` (`479f0a2`) with `0` algorithmic/data drift and `0` CJK characters remaining across all code and baseline files.
  - Parameterized hardcoded personal paths in `Dockerfile/docker-compose.yml` (`${SLICES_DATA_DIR:-..}`, `${SLICES_DOCKER_DIR:-.}`) and `rundocker.sh` (`${SLICES_DATA_DIR:-${PWD}}`, `${SLICES_IMAGE}`, `${SLICES_SHM_SIZE}`) while preserving `Dockerfile/` at its upstream path.

### Fixed

- **`DEF-007` Undefined `TimeoutException` & Worker-Thread Safety (`49237f6`):** Defined `TimeoutException(SLICESError)` and guarded `signal.SIGALRM` in `core.function_timeout` to activate only on POSIX main threads, preventing `NameError` on timeouts and `ValueError` in worker threads or on Windows.
- **`DEF-013` `relax_model=None` / `"none"` Short-Circuit (`49237f6`):** Short-circuited `if self.relaxer is None:` in both `SLICES.to_structures()` and `SLICES.to_4structures()`, eliminating spurious `'NoneType' object has no attribute 'relax'` stdout messages while returning identical `[std, opt], 0` tuples.
- **Host Process-Kill Hazard & Shell Calls in `src/slices/utils.py` (`49237f6`):** Removed all `pgrep -f python` + `kill -9` calls; introduced session-scoped `_SUBMITTED_LOCAL_PROCS` alongside `_SUBMITTED_SLURM_JOBS`; replaced 11 `os.system` calls with `shutil`/`Path` and wrapped directory changes in `temporaryWorkingDirectory`.
- **Optional `m3gnet` Dispatch Unblock (`49237f6`):** Removed the hardcoded pre-check in `relax_backends.resolve_relax_model` so explicit opt-in `relax_model="m3gnet"` reaches `mlip_relaxer.resolve_optional_mlip` (raising a clear `ImportError` with v4.0.2 NequIP guidance when uninstalled).
- **Baseline Syntax Typo (`479f0a2`):** Fixed stray `* ` syntax error on line 5 of `HTS/0_get_json_mp_api/2_filter_prior_3d/1_run.py` (`benchmark/.../error.py` preserved untouched as a historical stderr artifact).

### Removed

- Removed `MatterGPT/` directory, `entrypoint_set_cpus_gradio.sh`, `HANDOFF_workstation.md`, root `__init__.py`, `src/slices/README.rst`, `einops` dependency, `gradio` extra, and stale Sphinx HTML files in `docs/`.

---

## [4.0.2] — 2026-11-09 (`94ef8e0`)

### Added

- Automatic download timeout (`(30, 120)` s), completeness verification, and exponential retry waits (`5, 15, 30` s) for NequIP-OAM weight downloads from `nequip.net` / Zenodo in `src/slices/relax_backends.py`, raising `ModelDownloadError` with manual override guidance (`SLICES_NEQUIP_MODEL_{S,M,L}`).

---

## [4.0.1] — 2026-11-09 (`47bbd6e`)

### Fixed

- Compatibility with `pymatgen >= 2026.3` (`StructureGraph.from_local_env_strategy` and `BrunnerNNReciprocal` import fallback) and `scipy >= 1.15` (removed deprecated `iprint` and `disp` keyword arguments from `fmin_l_bfgs_b`).

---

## [4.0.0] — 2026-11-09 (`84da90f`)

### Added

- **`uv` Environment & Python 3.10 Lockfile (`119afaf`):** Migrated packaging to `pyproject.toml`, `.python-version`, `uv.lock`, and `setup.cfg` (`manylinux2014_x86_64` wheel).
- **NequIP-OAM Default Relaxation Backend (`eb1f6c9`, `315d4f0`, `a096d91`):** Introduced `src/slices/relax_backends.py` with `relax_model="auto"` defaulting to CPU `nequip-s+l` (93.79% standard match on 2,383 MP-20 structures vs 88.67% legacy M3GNet), `nequip-m+l` (94.80%), `nequip-l`, AOTInductor/TorchScript/OpenEquivariance compilation caching, soft-sphere overlap pre-optimization (`preoptimize`, `remove_overlaps`), and `_collapse_guard` + `FIRE` retry recovery.
- **Bundled Open-Source GFN-FF Decoder (`d40c909`, `4e5a9d9`):** Added `src/slices/_vendor/gfnff/` (`libgfnff.so.0.1.1`, LGPL-3.0) and `src/slices/gfnff_helper.py` with `legacy86_overlay` / `modern` parameter modes, replacing the 60.8 MB external `xtb` binary and `/dev/shm` subprocess calls; fixed `get_nbf_blist` neighbor count cap (`<= 19`).
- **Primitive-Cell Pre-Reduction (`da0d873`):** Reduced structures to primitive standard cells prior to SLICES encoding when atom count decreases without altering reduced composition.
- **Scoped SLURM Tracking (`b600715`):** Added `_SUBMITTED_SLURM_JOBS` tracking in `src/slices/utils.py`.

### Removed

- Dropped legacy M3GNet and TensorFlow runtime dependencies from core packaging (`119afaf`) and removed the precompiled `xtb_noring_nooutput_nostdout_noCN` binary (`4e5a9d9`).

---

## [3.0.0] – [3.3.0] — 2025-01-07 to 2026-02-27 (`2cdfd3a`..`5ac90d9`)

- Added Strategy-4 space-group tokenization (`src/slices/utils_wyckoff.py`, SLICES-PLUS 230 space-group encoding).
- Improved SLURM detection and job submission helpers (`v3.0.1`).
- Added RTX 50-series CUDA support and the 2,383-structure Strategy-4 MP-20 non-metal benchmark dataset (`v3.3.0`).

---

## [2.0.0] – [2.3.0] — 2024-08-15 to 2025-01-06 (`fe955af`..`183ffe5`)

- Packaged `slices` under `src/slices/` with Strategy 3/4 support, parallel processing utilities, and memory-leak fixes in batch workflows (`v2.1.0`).

---

## [1.0] – [1.4.5] — 2023-04-27 to 2024-03-08 (`b018e7b`..`bb79b5a`)

- Initial public release accompanying *Nature Communications* 14, 7027 (2023): core SLICES encoding/decoding (Strategies 1–3), barycentric embedding (`tobascco_net`), ZL\* optimization, data augmentation, canonicalization, MP-20 / MP-21-40 / QMOF-21-40 / HTS benchmarks, and Docker/SLURM configuration scripts.
