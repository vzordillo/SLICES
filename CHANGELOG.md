# Changelog

All notable changes to SLICES are documented in this file. Commit hashes reference the local `slices-4-personal` branch (rebased onto upstream `v4.0.2`, commit `94ef8e0`) and upstream `xiaohang007/SLICES` tags.

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
