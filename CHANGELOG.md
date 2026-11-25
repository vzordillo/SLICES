# Changelog

All notable changes to SLICES are documented in this file. Commit hashes reference the local `slices-4-personal` branch (rebased onto upstream `v4.0.2`, commit `94ef8e0`) and upstream `xiaohang007/SLICES` tags.

---

## [4.1.0] — 2026-11-25

Promoted `exp/v4.1-algo-upgrades` (`d922032`..`9df6d8a`, branched from `9a51a73`) onto `main` via linear fast-forward merge and bumped the package version to `4.1.0`, delivering four core mathematical and topological upgrades verified against the locked `v4.0.2-baseline` (`f248b3c`) control group (`294 passed, 5 skipped, 0 failed` pytest + full `2,383`-crystal MP-20 & `39,244`-string `cRNN` paired A/B evaluation).

### Changed & Fixed

- **Exact Integer Smith Normal Form Lattice-Basis Fallback (`DEF-003`, `src/slices/tobascco_net.py`, `src/slices/decoding_strategies.py`):**
  - Added `Net._get_lattice_basis_via_snf()` using exact `sympy` `DomainMatrix` + `smith_normal_decomp` over $\mathbb{Z}$, invoked strictly inside `Net.get_lattice_basis()` when the primary single-nullspace-vector search fails (`basis == -1`) so already-passing nets remain bit-identical (`0.0` ULP drift, zero overhead).
  - Updated `CycleBasisOptimizer.find_lattice_basis()` to invoke `net.get_lattice_basis()` first so unimodular 3D nets are solved deterministically without RNG, retaining seeded row-permutation search only when `get_lattice_basis()` still returns `-1`.
- **3D Lattice & Cocycle Basis Enforcement in `check_SLICES` (`DEF-021`, `src/slices/core.py`):**
  - Updated `SLICES.check_SLICES(..., graph_rank_check=True)` to return `False` when `net.get_lattice_basis() == -1` (`net.lattice_basis is None`) or when a multi-vertex graph (`net.order > 1`) lacks a full-rank 2D cocycle basis (`len(net.cocycle) < net.order - 1`), preserving 1-atom primitive cells (`net.order == 1`) and `graph_rank_check=False` workflows.
- **Transitive `math.isclose` Lattice Symmetry Classification (`DEF-014`, `src/slices/core.py`, `src/slices/decoding_strategies.py`):**
  - Added `_classify_lattice_type(metric_tensor_std, rel_tol=1e-9, abs_tol=1e-12)` with pairwise `math.isclose` and transitive closure (`1`, `23`, `22`, `21`, `3`) and replaced exact float `set`/`==` classification in `SLICES.to_structures()` and `_reconstruct_zl_multistart()`, restoring symmetry-constrained ZL\* parameterizations perturbed by IEEE-754 rounding noise.
- **Matched Bond-Index Alignment in Incomplete GFN-FF Targets (`DEF-031`, `src/slices/core.py`):**
  - Tracked `matched_bond_indices` alongside `bond_weight` in `SLICES.get_inner_p_target()` and `SLICES.get_inner_p_target_debug()` so diagonal `colattice_inds` pairs `(edge_idx, edge_idx)` and normalized weights attach strictly to their true matched edges whenever GFN-FF skips unmatched bonds (`"Cannot find bond!!!"`).

### Tests & Benchmarks

- **Test Suite (`294 passed, 5 skipped, 0 failed`):** Added `tests/regression/test_v41_algo_upgrades.py` (`20` parametrized regression tests), aligned `E11` and `mininn` expectations in `tests/regression/test_wave1_fixes.py` and `tests/unit/test_encoding.py`, and enforced bounded symmetry-restored tolerances in `tests/baseline/test_golden_equivalence.py` (`max |dE| < 1e-6 eV/atom`, `0` match regressions) while keeping frozen `v4.0.2` fixtures in `tests/baseline/fixtures/` untouched.
- **Full MP-20 & `cRNN` Paired A/B Evaluation ([`AB_COMPARISON_REPORT.md`](benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md), [`tools/benchmarks/compare_ab_baselines.py`](tools/benchmarks/compare_ab_baselines.py)):**
  - **`v4.1 default` vs `v4.0.2 default` (`N = 2,383`):** Rescued `7 / 7` unimodular `LatticeBasisError` crystals (`+7 / -0` `ok` `99.92%`, strict `94.04%`, loose `96.22%`, McNemar `p = 0.0156`), matching `v4.0.2 robust` on every recovery metric at `-1.28%` lower wall-clock (`-65.23 CPU-s`) with `0` regressions across `2,374` shared `ok` crystals (`88.04%` within `<= 1e-6 eV/atom`, Wilcoxon `p = 0.1861`).
  - **Incomplete-GFN-FF Oxyhydrides (`DEF-031`):** Improved `mp-1176505` (`Lu4H4O8`) by `-12.16 meV/atom` (`preoptimized: True -> False`, BFGS `44 -> 18`) and `mp-625477` (`Eu2H6O6`) by `-48.06 meV/atom` in `default` (`-55.81 meV/atom` in `lorentz`).
  - **`cRNN` Scan (`39,244` strings):** Rescued `5` and rejected `4` on `sampled.sli`; rescued `98 / 401` unimodular crystals and rejected `303 / 401` non-invertible graphs across `38,244` published `unique.sli` strings (`0 / 303` survived `4_inverse`).

---

## [Unreleased — `v4.0.2-baseline` MP-20 Quantitative Benchmark] — 2026-11-25 (`f248b3c`)

Locked annotated baseline tag **`v4.0.2-baseline`** at commit `f248b3c` (verified `89/89` golden equivalence tests at `0.0` ULP drift and `274 passed, 5 skipped` across the full test suite) and archived the complete 2,383-structure MP-20 non-metal quantitative benchmark as a reproducible control group for future algorithmic work.

### Added

- **Multi-Process MP-20 Baseline Benchmark Runner ([`tools/benchmarks/run_mp20_baseline.py`](tools/benchmarks/run_mp20_baseline.py)):**
  - Evaluates all `2,383` structures of `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` across three paired passes (`default`, `lorentz`, `robust`) using `24` spawned CPU workers (`OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, `PYTHONHASHSEED=0`), 1-to-1 Materials Project reference CIF matching against `data/mp20/train.csv`, non-invasive relaxation telemetry, and exact `formation_energy()` parity with [`examples/3.benchmark_relax_models.py`](examples/3.benchmark_relax_models.py).
- **Archived `v4.0.2-baseline` Quantitative Control Group (`benchmark/v4_0_2_baseline/`):**
  - [`BASELINE_REPORT.md`](benchmark/v4_0_2_baseline/BASELINE_REPORT.md): Publication-grade baseline report covering 3-pass metrics, 7-system crystallographic breakdown, failure/rescue taxonomy, incomplete-GFN-FF oxyhydride diagnostics, paired A/B deltas, and control-group reproduction protocol.
  - [`summary.json`](benchmark/v4_0_2_baseline/summary.json) & [`per_structure_metrics.csv`](benchmark/v4_0_2_baseline/per_structure_metrics.csv) (`2,383` rows × `53` columns, lossless float64 `eform`):
    - **`default` (`legacy` + `SLICES2structure`):** `2,374 / 2,383` (`99.62%`) decoded (`9` failures: `8` `LatticeBasisError`, `1` `CocycleBasisError`), `93.75%` strict / `95.93%` loose `StructureMatcher` recovery, `62.44%` space-group match, `0.199109 eV/atom` MAE (`0.025299 eV/atom` median AE), `192.59 s` wall-clock (`0.000e+00` single-process determinism parity vs `examples/3.benchmark_relax_models.py`).
    - **`lorentz` (`lj_mixing="lorentz"`):** `0.9997x` runtime (`192.54 s`), `+70` (`+2.94 pp`) space-group preservation gain (`62.44% -> 65.38%`, cubic `74.10% -> 80.96%`), `+4 / -0` loose recovery (`96.10%`), `+9` canonical round-trip matches, neutral strict recovery (`-2`, `+4 / -6`, all `6` losses remain loose matches).
    - **`robust` (`robust_SLICES2structure(n_starts=3, seed=0)`):** `+1.81%` runtime (`196.08 s`), rescues `7 / 8` (`87.5%`) `LatticeBasisError` crystals at `100%` strict/loose match (`ok` `99.92%`, strict `94.04%`, loose `96.22%`, `2` `SLICESDecodingError` remaining) while preserving `2,372 / 2,374` (`99.92%`) fast-path bit-identity.
- **Documentation Index:** Linked the `v4.0.2-baseline` quantitative report, JSON/CSV archive, and benchmark runner from [`docs/README.md`](docs/README.md).

---

## [Unreleased — Wave 3 (`VERSIONED_OPT_IN`)] — 2026-11-25 (`e5c7f0d`, `0e51ff0`) — Opt-In Scientific & API Upgrades

Five clean opt-in upgrades across `src/slices/{core,relax_backends,decoding_strategies}.py` derived from [REEVAL_SYNTHESIS.md](docs/migration/reeval/REEVAL_SYNTHESIS.md) Section 5 Wave 3, preserving **100% default v4.0.2 numerical parity (`89/89` frozen golden baseline tests at `atol=1e-12`, `0.0` ULP drift)**:

### Added

- **Lorentz-Berthelot LJ Mixing (`DEF-001`, `src/slices/core.py`, `src/slices/decoding_strategies.py`):**
  - Exported `VALID_LJ_MIXING_MODES = ("legacy", "lorentz")` in `slices.core.__all__` and appended `lj_mixing: Literal["legacy", "lorentz"] = "legacy"` to `SLICES.__init__` (`ValueError` on invalid modes).
  - Under `lj_mixing="lorentz"`, `get_uncovered_pair_lj()` and `get_covered_pair_lj()` compute exact arithmetic Lorentz-Berthelot averages `[(r_cut_0 + r_cut_1) / 2, (sigma_0 + sigma_1) / 2]` on `[4*sigma, sigma]` length parameters, restoring atom-order permutation invariance (`5.0x` steric swing eliminated on `YHO2`) while preserving `"legacy"` bit-for-bit by default.
  - Updated opt-in `_reconstruct_zl_multistart()` to evaluate Lorentz-Berthelot pair parameters inside a `try ... finally` block that unconditionally restores `slices_inst.lj_mixing`.
- **Backend-Aware Element Validation & NequIP-OAM Pre-Check (`DEF-006`, `DEF-029`, `src/slices/core.py`, `src/slices/relax_backends.py`):**
  - Exported `VALID_ELEMENT_MODES = ("legacy86", "nequip_oam", "gfnff103")` in `slices.core.__all__` and added `mode: Literal["legacy86", "nequip_oam", "gfnff103"] = "legacy86"` to `SLICES.check_element()` (`"legacy86"`: `Z <= 86` default; `"nequip_oam"`: 89-element OAM set `{1..83, 89..94}`; `"gfnff103"`: `1 <= Z <= 103`; raises `ValueError` on invalid mode and `SLICESEncodingError` on 0-site structures).
  - Exported `NEQUIP_OAM_ATOMIC_NUMBERS: frozenset[int]` (`{1..83, 89..94}`) in `slices.relax_backends.__all__` and added a pre-relaxation element validation check in `NequIPRelaxer.relax()` (prior to `preoptimize()` and calculator execution), raising an informative `RelaxBackendError` naming unsupported symbols and atomic numbers (`Po..Ra`, `Am..Og`) instead of raw TorchScript `KeyError`.
- **Incomplete-GFN-FF Automatic Stage 2 Recovery (`DEF-015`, `DEF-031` Wave 3, `src/slices/core.py`, `src/slices/decoding_strategies.py`):**
  - Tracked transient `self._last_gfnff_incomplete` in `SLICES` whenever `get_inner_p_target()` / `get_inner_p_target_debug()` skips unmatched bonds (`"Cannot find bond!!!"`), leaves non-positive diagonal targets (`diag(inner_p_target) <= 0`), or catches a target-generation exception.
  - Updated opt-in `robust_decode()` / `SLICES.robust_SLICES2structure()` to automatically advance from Stage 1 into Stage 2 (`BondParameterFallback` + Lorentz-Berthelot multi-start ZL\* + `ProgressiveRelaxer`) when `_last_gfnff_incomplete` is `True`, cleanly falling back to Stage 1's valid structure on Stage 2/3 error while preserving `0%` fast-path overhead and bit-for-bit v4.0.2 output on complete-GFN-FF crystals.
- **Seeded `PYTHONHASHSEED`-Invariant Data Augmentation (`DEF-022`, `DEF-033`, `src/slices/core.py`):**
  - Added `seed: int | None = None` to `SLICES.structure2randomSLICES()` and `SLICES.structure2SLICESAug_atom_order()`.
  - Passing an integer `seed` uses an isolated `random.Random(seed)`, insertion-ordered `dict` deduplication, and a pre-loop `if len(seen) >= num: break` termination guard (guaranteeing `num=1` deterministically returns `[original_SLICES]`) for `100%` cross-`PYTHONHASHSEED` reproducibility with zero global `random` mutation, while `seed=None` preserves exact v4.0.2 behavior.
- **Strict Trailing-Token Parsing (`DEF-024` Gap 3a, `src/slices/core.py`):**
  - Added `strict: bool = False` to `SLICES.from_SLICES()`, `SLICES.check_SLICES()`, and `SLICES.check_SLICES_basic()`.
  - Under `strict=True`, trailing partial edge tokens that violate strategy token stride (`7` for Strategy 1, `5` for Strategy 3, `3` for Strategy 4) raise `SLICESDecodingError` (and return `False` in `check_SLICES` / `check_SLICES_basic`), while `strict=False` preserves lenient replay compatibility for historical datasets (`HTS/9_EAH_Band_gap_PBE`).

### Tests & Documentation

- Added `tests/regression/test_wave3_opt_in.py` (`0e51ff0`, `9` `@pytest.mark.regression` tests covering all 5 opt-in Wave 3 features and `13` authentic truncated HTS PBE rows; full suite `274 passed, 5 skipped`).
- Updated [DEFERRED_CORE_REGISTER.md](docs/migration/DEFERRED_CORE_REGISTER.md) (`34/34` entries synchronized), appended Post-Migration Cycle 2 to [LAB_LOG.md](docs/migration/LAB_LOG.md), and updated Wave 3 API contracts in `docs/api/API_{CORE,MLIP,DECODING_STRATEGIES}.md`.

---

## [Wave 1 (`SAFE_NOW`)] — 2026-11-25 (`a85e832`..`f9d675b`) — Zero-Drift Bugfixes & Memory-Safety Guards

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
