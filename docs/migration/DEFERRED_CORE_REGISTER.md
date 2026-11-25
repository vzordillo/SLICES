# Deferred Core / Algorithm Register

**Project:** SLICES v4.0.2 Migration & Post-Migration Empirical Re-Evaluation (`slices-4-personal` / `main`)  
**Governing Policy:** Strict Math / Algorithm Freeze Boundary ([PLAN.md Section 4](PLAN.md#L140-L166)) -> Post-Migration Empirical Re-Evaluation ([REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md))  
**Baseline Reference:** `/home/ordillo/tests/SLICES-upstream-baseline` (`upstream/main` @ `94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`)  
**Last Updated:** 2026-11-25 18:10 JST (Post-Migration Cycle 4: `v4.0.2-baseline` locked at `f248b3c` and benchmark archive pushed to `origin/main` @ `9a51a73`; all 4 remaining Wave 2 `HIGH_VALUE_AB` items [`DEF-003` SNF fallback, `DEF-014`, `DEF-021` `check_SLICES`, `DEF-031` core `matched_bond_indices` alignment] implemented, verified, and sealed on experimental branch `exp/v4.1-algo-upgrades` in commits `d922032`, `cd76ac5`, `36fa8e5` [`294 passed, 5 skipped, 0 failed` pytest + full 2,383-crystal MP-20 & 39,244-string `cRNN` paired A/B verified] — **34 verified entries, 0 active deferred items remaining**: 2 Resolved in Stage 4 [`DEF-007`, `DEF-013`], 15 Fully Resolved in Wave 1 [`DEF-004`, `DEF-005`, `DEF-008`, `DEF-010`, `DEF-011`, `DEF-012`, `DEF-018`, `DEF-023`, `DEF-025`, `DEF-026`, `DEF-027`, `DEF-028`, `DEF-030`, `DEF-032`, `DEF-034`], 1 Split Wave 1 / Closed [`DEF-019`], 1 Fully Resolved across Wave 1 + Wave 3 [`DEF-024`], 6 Fully Resolved in Wave 3 [`DEF-001`, `DEF-006`, `DEF-015`, `DEF-022`, `DEF-029`, `DEF-033`], 4 Resolved on `exp/v4.1-algo-upgrades` [`DEF-003` (SNF fallback; non-SNF parts Keep Frozen), `DEF-014`, `DEF-021` (completing Wave 1), `DEF-031` (completing Wave 3)], 2 `KEEP_FROZEN` [`DEF-002` (default; opt-in enhanced in Wave 3), `DEF-009`], 3 `CLOSE_WONTFIX` [`DEF-016`, `DEF-017`, `DEF-020`])

---

## Purpose & Governance Rules

During Stages 1–7 of this migration, all core mathematical, crystallographic, graph-theoretic, topological, GFN-FF target-construction, ZL* L-BFGS-B optimization, and default NequIP relaxation code paths were **strictly frozen** to guarantee exact / numerically invariant (`atol=1e-12` on CPU) equivalence against upstream SLICES v4.0.2 (`94ef8e0`).

Following Stage 7 completion (`HEAD=fa4cfc8`), a 4-agent Carbon High empirical re-evaluation cycle ([REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md), [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md), [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md), [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md)) tested every deferred item against `125,174` SLICES strings, `18,093` MP-20 CIFs, `3,883` GFN-FF topology evaluations, and controlled CPU `NequIP-OAM-S/L` A/B benchmarks, discovering `7` new defects (`DEF-028`–`DEF-034`) and classifying all `34` entries into actionable waves:

- **Wave 1 (`SAFE_NOW`):** Zero-drift (`0.0` ULP, `89/89` golden parity at `atol=1e-12`) bugfixes, memory-safety guards, and hygiene cleanups sealed on `main` (`a85e832`, `954a56a`, `f9d675b`) and fast-forward pushed to `origin/main` (`f9d675b`).
- **Wave 2 (`HIGH_VALUE_AB`):** High-value scientific upgrades (`DEF-003` SNF fallback, `DEF-014`, `DEF-021` `check_SLICES`, `DEF-031` core `matched_bond_indices` alignment) implemented, verified, and sealed on `exp/v4.1-algo-upgrades` (`d922032`, `cd76ac5`, `36fa8e5`; `294 passed, 5 skipped, 0 failed` pytest + full 2,383-crystal MP-20 & 39,244 `cRNN` A/B comparison in [AB_COMPARISON_REPORT.md](../../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md)).
- **Wave 3 (`VERSIONED_OPT_IN`):** Clean opt-in APIs preserving upstream `v4.0.2` default behavior (`89/89` golden parity at `atol=1e-12`), sealed locally on `main` in commits `e5c7f0d` (`W3-a`) and `0e51ff0` (`W3-b`), Gate W3 **PASS**.
- **`KEEP_FROZEN` / `CLOSE_WONTFIX`:** Empirically proven regressions or Stage 3 architectural blocks permanently retained/closed.

### Schema Definition

| Field | Allowed Values / Format |
|---|---|
| **ID** | Sequential immutable identifier (`DEF-001`, `DEF-002`, ..., `DEF-034`) |
| **Source / Location** | Branch/ref, file path, exact verified line numbers, symbol name(s), and relevant commit SHA(s) |
| **Category** | One or more of: `Math`, `Graph`, `Optimization`, `Relaxation`, `Runtime`, `Compatibility` |
| **Status** | `Resolved in Stage 4 (...)`, `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`, `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`, `Resolved in Wave 1 + Wave 3 (...)`, `Resolved on exp/v4.1-algo-upgrades (commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified)`, `Split — ... / Keep Frozen (...)`, `Keep Frozen (...)`, or `Closed — Won't Fix (CLOSE_WONTFIX; ...)` |
| **Provenance** | Stage/slice and source tag (`Stage 1 Seed`, `Stage 2A / FC-*`, `Stage 2B / DEF-UP-*`, `Stage 2C / DEF-BC-*`, `Stage 3 / RUL-*`, `Post-Migration Re-Eval / REEVAL_*`) |
| **Observed Behavior** | Factual description of code behavior verified from primary source |
| **Why Deferred under Baseline Freeze** | Concrete explanation of how changing it affected upstream v4.0.2 parity during Stages 1–7 (or why discovered post-migration) |
| **Empirical Re-Evaluation & Disposition** | Verified quantitative evidence from `REEVAL_SYNTHESIS.md` and concrete Wave 1/Wave 3 resolution or Wave 2/Frozen/Closed disposition |
| **Impact Risk** | `Critical` / `High` / `Medium` / `Low` — behavioral or memory-safety impact rating |

---

## Summary Index

| ID | Category | Source / Symbol | Short Description | Provenance | Impact Risk | Status |
|---|---|---|---|---|---|---|
| [`DEF-001`](#def-001) | `Math`, `Optimization` | `src/slices/core.py:82,161-234,1917-1998`, `src/slices/decoding_strategies.py:518-582,629` (`VALID_LJ_MIXING_MODES`, `lj_mixing`, `get_uncovered_pair_lj`, `get_covered_pair_lj`, `_reconstruct_zl_multistart`) | Added opt-in `lj_mixing: Literal["legacy", "lorentz"] = "legacy"` with exact arithmetic Lorentz–Berthelot mixing on `[4*sigma, sigma]` (restoring atom-order symmetry) and adopted Lorentz mixing inside opt-in `_reconstruct_zl_multistart` | Stage 1 Seed; Re-Eval (`REEVAL_MATH_OPT`); Wave 3 (`#96`, `#98`) | **High** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-002`](#def-002) | `Optimization`, `Relaxation` | `backup/v3-personal:src/slices/core.py:2459-2566` vs `src/slices/core.py:2526-2835` (`to_structures`, `robust_SLICES2structure`) | Default `to_structures()` stays permanently frozen (`1.85x–2.09x` slower for `+0/47` net gain if always on); opt-in `robust_SLICES2structure()` upgraded in Wave 3 (`DEF-001`, `DEF-015`, `DEF-031`) | Stage 1 Seed; Stage 2A (`FC-04`, `FC-05`); Re-Eval (`REEVAL_GRAPH_RELAX`) | **High** | Keep Frozen (Default) / Opt-In Robust Decoding Enhanced in Wave 3 (VERSIONED_OPT_IN) |
| [`DEF-003`](#def-003) | `Graph`, `Math` | `src/slices/tobascco_net.py:469-595`, `src/slices/decoding_strategies.py:156-190` (`_get_lattice_basis_via_snf`, `get_lattice_basis`, `CycleBasisOptimizer.find_lattice_basis`) | Exact integer `smith_normal_decomp` fallback on `basis == -1` rescues `7/7` MP-20 unimodular crystals (`100%` strict/loose match, `p=0.0156`) and `98` cRNN strings (`0.0` passing-net drift); non-SNF fork changes remain `KEEP_FROZEN` | Stage 1 Seed; Stage 2A (`FC-01`–`FC-03`); Re-Eval (`REEVAL_SYNTHESIS`); v4.1 (`#118`, `#121`, `#124`) | **High** | Split — SNF fallback Resolved on exp/v4.1-algo-upgrades (commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified) / Keep Frozen (unconditional reorder, is_integral, iter_cycles) |
| [`DEF-004`](#def-004) | `Graph`, `Runtime` | `src/slices/tobascco_net.py:339-382,467-494` (`simple_cycle_basis`, `get_lattice_basis`) | Dead `np.random.choice` / `np.random.shuffle` calls mutating global NumPy RNG state removed (`0` `np.random`, `0.0` ULP drift) | Stage 1 Seed; Stage 3 (`RUL-03`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-005`](#def-005) | `Runtime`, `Compatibility` | `src/slices/core.py:17-19,53-58` (module import header) | Replaced unconditional env/warning overrides with `setdefault` (`TF_CPP_MIN_LOG_LEVEL`, `OMP_NUM_THREADS`), scoped `spglib` warning, and `BrunnerNNReciprocal` priority | Stage 1 Seed; Stage 3 (`RUL-03`, `CA-08`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-006`](#def-006) | `Compatibility`, `Math` | `src/slices/core.py:80,270-301` (`VALID_ELEMENT_MODES`, `check_element`) vs `src/slices/gfnff_helper.py:59-60,107-156` | Added opt-in `check_element(structure, mode="legacy86"\|"nequip_oam"\|"gfnff103")` preserving `Z <= 86` default while exposing NequIP-OAM `{1..83, 89..94}` (`DEF-029`) and GFN-FF `1..103` (`DEF-028`) tiers | Stage 1 Seed; Re-Eval (`REEVAL_MATH_OPT`); Wave 3 (`#98`) | **Medium** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-007`](#def-007) | `Runtime`, `Compatibility` | `src/slices/core.py:108-153` (`function_timeout`), `src/slices/exceptions.py:77-78` | Undefined `TimeoutException` (`F821`, deleted in `119afaf`) restored with POSIX main-thread `SIGALRM` guard | Stage 2B (`DEF-UP-001`); Stage 3 (`RUL-01`) | **Low** | Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_exceptions.py) |
| [`DEF-008`](#def-008) | `Relaxation`, `Compatibility` | `src/slices/core.py:2960-2976` (`relax_large_cell2`) | Forwarded `fmax=self.fmax, steps=self.steps` in both `>40`-atom relaxation branches (`1.24x` faster on `45–64`-atom supercells, `0.0` golden drift) | Stage 2B (`DEF-UP-002`); Stage 2A (`FC-08`); Re-Eval (`REEVAL_GRAPH_RELAX`) | **Medium–High** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-009`](#def-009) | `Relaxation`, `Optimization`, `Compatibility` | `src/slices/relax_backends.py:544-552` (`_cell_filter`) | `ExpCellFilter` beats `FrechetCellFilter` (`93.48%` vs `89.13%` strict match, `8.3%` faster); retained as default with scoped `DeprecationWarning` suppression | Stage 2B (`DEF-UP-003`); Re-Eval (`REEVAL_GRAPH_RELAX`, `REEVAL_SYNTHESIS`) | **High** | Keep Frozen (KEEP_FROZEN; ASE warning scoped in Wave 1) |
| [`DEF-010`](#def-010) | `Graph`, `Runtime` | `src/slices/tobascco_net.py:384-405,679-692` (`iter_cycles`, `vertex_positions`) | Replaced mutable `[]` / `{}` default arguments with `None` guards and removed `# noqa: B006` | Stage 2B (`DEF-UP-004`); Re-Eval (`REEVAL_GRAPH_RELAX`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-011`](#def-011) | `Math`, `Compatibility` | `src/slices/tobascco_net.py:438-465,840-855,882-888` (`linear_independent_vectors`, `eon_projection`, `projection`, `cycle_cocycle_I`) | Replaced `np.matrix(...).I` with `np.linalg.inv(...)` (strictly `inv`, zero `pinv`, `0.000e+00` ULP across `2,374` MP-20 crystals) | Stage 2B (`DEF-UP-005`); Re-Eval (`REEVAL_MATH_OPT`) | **Medium–High** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-012`](#def-012) | `Compatibility`, `Runtime` | `src/slices/core.py:980-1079` (`SLICES2formula`) | Replaced fragile regex with grammar-aware Strategy 1–4 token extraction (`100%` parity across Strategies 1–4 & `16,686` MP-20 rows; clean `None` on malformed strings) | Stage 2B (`DEF-UP-006`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-013`](#def-013) | `Relaxation`, `Runtime` | `src/slices/core.py:2750-2753,2912-2915` (`to_structures`, `to_4structures`) | `if self.relaxer is None:` short-circuit returns `[std, opt], 0` with zero spurious `AttributeError` stdout | Stage 2B (`DEF-UP-007`); Stage 3 (`RUL-02`, `CA-06`) | **Low** | Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_decoding.py) |
| [`DEF-014`](#def-014) | `Math`, `Optimization` | `src/slices/core.py:156-192,2702`, `src/slices/decoding_strategies.py:594-629,729` (`_classify_lattice_type`, `to_structures`, `_reconstruct_zl_multistart`) | Replaced exact float `set`/`==` with transitive `math.isclose(rel_tol=1e-9, abs_tol=1e-12)` in core and Stage 2 decoding; `0` regressions on `2,374` shared `ok` crystals (`88.04%` `<= 1e-6 eV/at`, `max \|dE\| < 1e-6` on 14 golden crystals) | Stage 2B (`DEF-UP-008`); Re-Eval (`REEVAL_MATH_OPT`); v4.1 (`#116`, `#118`, `#121`, `#124`) | **High** | Resolved on exp/v4.1-algo-upgrades (commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified) |
| [`DEF-015`](#def-015) | `Optimization`, `Graph` | `src/slices/core.py:230,400,1652-1870`, `src/slices/decoding_strategies.py:220-305,612-626,824-866` (`_last_gfnff_incomplete`, `get_inner_p_target`, `robust_decode`) | Tracked transient `_last_gfnff_incomplete` on dropped/non-positive GFN-FF bonds so opt-in `robust_decode` automatically triggers Stage 2 `BondParameterFallback` (with Stage 1 fallback on Stage 2 error; `0%` fast-path overhead) | Stage 2A (`FC-06`); Re-Eval (`REEVAL_GRAPH_RELAX`); Wave 3 (`#96`, `#98`) | **High** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-016`](#def-016) | `Compatibility`, `Graph` | `src/slices/core.py:506-515` (`from_SLICES`) | Fork swallowed invalid Strategy-4 space-group header errors; permanently blocked (`E03_bad_sg_prefix` verified intact) | Stage 2A (`FC-07`); Stage 3 Sign-Off; Re-Eval (`REEVAL_RUNTIME_PARSE`) | **High** | Closed — Won't Fix (CLOSE_WONTFIX; Blocked in Stage 3) |
| [`DEF-017`](#def-017) | `Compatibility` | `src/slices/core.py:53-58,317-367` (`cif2structure_graph`, `structure2structure_graph`) | Fork kept deprecated `with_local_env_strategy`; permanently closed (`from_local_env_strategy` + `BrunnerNNReciprocal` active) | Stage 2A (`FC-09`); Stage 2B (`2635bcc`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **High** | Closed — Won't Fix (CLOSE_WONTFIX; Resolved Upstream in 2635bcc) |
| [`DEF-018`](#def-018) | `Compatibility`, `Runtime` | `src/slices/core.py:294-295,342-345,1100-1101`, `src/slices/exceptions.py:35-41` (`check_element`, `structure2structure_graph`, `to_primitive_if_smaller`) | Added `len(structure) == 0` guards raising `SLICESEncodingError(SLICESError, ValueError)` instead of silently returning `""` / `[""]` | Stage 2A (`FC-10`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-019`](#def-019) | `Compatibility`, `Runtime` | `src/slices/core.py:630-701,758-782` (`get_slices1..3`, `check_structural_validity`) | Part 1: 4-arg `get_slices1..3(..., space_group_num=None)` permanently retained; Part 2: `isinstance(str1, IStructure)` `TypeError` guard added in Wave 1 | Stage 2A (`FC-11`); Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Medium** | Resolved in Wave 1 (Part 2 SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) / Closed — Won't Fix (Part 1 4-arg get_slices1..3) |
| [`DEF-020`](#def-020) | `Runtime`, `Compatibility` | `src/slices/core.py:17-19`, `src/slices/__init__.py`, `src/slices/mlip_relaxer.py` | Fork set root logger to `CRITICAL` and eagerly injected `TF_USE_LEGACY_KERAS`/`sys.modules["keras"]`; permanently blocked | Stage 2A (`FC-12`); Stage 3 Sign-Off; Re-Eval (`REEVAL_RUNTIME_PARSE`) | **High** | Closed — Won't Fix (CLOSE_WONTFIX; Blocked in Stage 3) |
| [`DEF-021`](#def-021) | `Graph`, `Math`, `Compatibility` | `src/slices/core.py:823-935,2637-2652` (`check_SLICES`, `to_structures`) | Wave 1: `to_structures` raises `LatticeBasisError`/`CocycleBasisError`; v4.1: `check_SLICES(..., graph_rank_check=True)` enforces lattice & multi-vertex cocycle bases, rejecting `303/401` non-invertible cRNN graphs (`0/303` survived `4_inverse`) while keeping 1-atom cells & `graph_rank_check=False` intact | Stage 2C (`DEF-BC-01`); Re-Eval (`REEVAL_GRAPH_RELAX`, `REEVAL_SYNTHESIS`); v4.1 (`#116`, `#121`, `#124`) | **High** | Resolved in Wave 1 (to_structures LatticeBasisError/CocycleBasisError; commit a85e832) + Resolved on exp/v4.1-algo-upgrades (check_SLICES; commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified) |
| [`DEF-022`](#def-022) | `Runtime`, `Compatibility` | `src/slices/core.py:1156-1429` (`structure2randomSLICES`, `structure2SLICESAug_atom_order`) | Added opt-in `seed: int \| None = None` using isolated `random.Random(seed)` + insertion-ordered `dict` for `100%` `PYTHONHASHSEED`-invariant augmentation with `0` global RNG mutation while preserving `seed=None` v4.0.2 behavior | Stage 2C (`DEF-BC-02`); Re-Eval (`REEVAL_RUNTIME_PARSE`); Wave 3 (`#98`) | **Low–Medium** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-023`](#def-023) | `Graph`, `Runtime` | `src/slices/core.py:229,399,2448-2522` (`from_SLICES`, `SLICES2space_group_number`) | Deleted stale `if self.unstable_graph:` branch in `SLICES2space_group_number` and reset `self.unstable_graph = False` in `from_SLICES` (fixes `91.62% -> 4.68%` reuse collapse) | Stage 2C (`DEF-BC-03`); Re-Eval (`REEVAL_GRAPH_RELAX`) | **Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-024`](#def-024) | `Compatibility`, `Runtime` | `src/slices/core.py:371-596,784-913` (`from_SLICES`, `_is_int_token`, `check_SLICES`, `check_SLICES_basic`) | Fully resolved across Wave 1 (Gaps 1, 2, 3b, 4 preserving `E01`–`E05`) and Wave 3 (Gap 3a `strict: bool = False` enforcing edge-token stride `7`/`5`/`3` when `strict=True` while preserving lenient `strict=False` HTS replay) | Stage 2C (`DEF-BC-04`); Re-Eval (`REEVAL_RUNTIME_PARSE`, `REEVAL_SYNTHESIS`); Wave 1 (`#86`); Wave 3 (`#98`) | **Medium** | Resolved in Wave 1 + Wave 3 (Gaps 1, 2, 3b, 4 SAFE_NOW commit a85e832 / Gap 3a strict=True VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-025`](#def-025) | `Math`, `Compatibility` | `src/slices/core.py:758-782` (`check_structural_validity`) | Replaced `i < j` distance loop with `get_neighbor_list(r=0.5 + 1e-9)` excluding `(i == j) & (img == 0)` (catches 1-atom and sheared short-image cells; `0/18,093` MP-20 flips) | Stage 2C (`DEF-BC-05`); Re-Eval (`REEVAL_MATH_OPT`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-026`](#def-026) | `Runtime`, `Compatibility` | `src/slices/core.py:81,213-216,362-366,1453-1457` (`VALID_GRAPH_METHODS`, `__init__`, `structure2structure_graph`, `get_dim`) | Exported `VALID_GRAPH_METHODS` and raised `ValueError` on invalid `graph_method` instead of printing + `UnboundLocalError` | Stage 2C (`DEF-BC-06`); Stage 3 Sign-Off; Re-Eval (`REEVAL_RUNTIME_PARSE`) | **Low** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-027`](#def-027) | `Math`, `Runtime` | `src/slices/core.py:2314-2446` (`func_check`) | Mirrored `func()`'s `np.sqrt(max(..., 1e-10))` and `r_temp = max(r_temp, 1e-8)` clamping guards in `func_check()` (`0` `NaN`/`RuntimeWarning` on `G18`) | Stage 2C (`DEF-BC-07`); Re-Eval (`REEVAL_MATH_OPT`) | **Low** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-028`](#def-028) | `Compatibility`, `Runtime` | `src/slices/gfnff_helper.py:59-60,107-156` (`parse_nbf_text`) | Critical Fortran OOB guard: enforce `1 <= Z <= 103` before `libgfnff.so.0.1.1` / `xtb`, raising `GFNFFExecutionError` on `Rf..Og` (`Z >= 104`) | Post-Migration Re-Eval (`REEVAL_MATH_OPT`, `REEVAL_SYNTHESIS`) | **Critical** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-029`](#def-029) | `Compatibility`, `Relaxation` | `src/slices/relax_backends.py:88,577-600,637-700`, `src/slices/core.py:80,270-301` (`NEQUIP_OAM_ATOMIC_NUMBERS`, `_validate_nequip_elements`, `NequIPRelaxer.relax`, `check_element`) | Exported 89-element `NEQUIP_OAM_ATOMIC_NUMBERS` (`{1..83, 89..94}`), added `RelaxBackendError` pre-check in `NequIPRelaxer.relax` (replacing raw `KeyError` on `Po..Ra`/`Am..Og`), and wired `check_element(..., mode="nequip_oam")` | Post-Migration Re-Eval (`REEVAL_MATH_OPT`, `REEVAL_SYNTHESIS`); Wave 3 (`#96`, `#98`) | **Medium** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-030`](#def-030) | `Math`, `Runtime` | `src/slices/core.py:1706-1707,1814-1817` (`get_inner_p_target_debug`, `get_inner_p_target`) | Guarded `math.cos(data["vangl"][i][0])` against non-finite `vangl` entries (`np.isfinite`), eliminating `ValueError: math domain error` (`1/1,000` cRNN strings) | Post-Migration Re-Eval (`REEVAL_GRAPH_RELAX`, `REEVAL_SYNTHESIS`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-031`](#def-031) | `Optimization`, `Graph` | `src/slices/core.py:1725,1744,1797-1802,1835,1854,1909-1914`, `src/slices/decoding_strategies.py:660-675,807-866` (`get_inner_p_target*`, `robust_decode`) | Wave 3: `robust_decode` Stage 2 trigger; v4.1: `matched_bond_indices` alignment in `core.py` improves `Lu4H4O8` `-12.16 meV/at` (`preopt True->False`, BFGS `44->18`) and `Eu2H6O6` `-48.06 meV/at` (`-55.81` lorentz) with `0.0` drift on complete-GFN-FF crystals | Post-Migration Re-Eval (`REEVAL_GRAPH_RELAX`, `REEVAL_SYNTHESIS`); Wave 3 (`#96`, `#98`); v4.1 (`#116`, `#121`, `#124`) | **Medium–High** | Resolved in Wave 3 (robust_decode Stage 2 trigger; commit e5c7f0d) + Resolved on exp/v4.1-algo-upgrades (core.py matched_bond_indices alignment; commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified) |
| [`DEF-032`](#def-032) | `Math`, `Graph` | `src/slices/core.py:1890-1915` (`get_uncovered_pair`) | Canonicalized bonded pairs as `(min(u, v), max(u, v))` so reversed `[u, v]` (`u > v`) edges are never misclassified as non-bonded LJ pairs | Post-Migration Re-Eval (`REEVAL_MATH_OPT`, `REEVAL_SYNTHESIS`) | **Low–Medium** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |
| [`DEF-033`](#def-033) | `Runtime`, `Compatibility` | `src/slices/core.py:1156-1399` (`structure2randomSLICES`, pre-loop guard `L1222-L1223`) | Added pre-loop `if len(seen) >= num: break` under `seed is not None` so `num=1` deterministically returns `[original_SLICES]` across all `PYTHONHASHSEED` values | Post-Migration Re-Eval (`REEVAL_RUNTIME_PARSE`, `REEVAL_SYNTHESIS`); Wave 3 (`#98`) | **Low–Medium** | Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity) |
| [`DEF-034`](#def-034) | `Graph`, `Runtime` | `src/slices/tobascco_net.py:438-465` (`linear_independent_vectors`) | Replaced `np.matrix(r_mat)` with `np.atleast_2d(np.asarray(r_mat))` and added `r == 0` and `counter < r - 1` bounds guards against `IndexError` on rank-deficient rectangular matrices | Post-Migration Re-Eval (`REEVAL_MATH_OPT`, `REEVAL_SYNTHESIS`) | **Low** | Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) |

---

## Detailed Register Entries

### DEF-001
- **ID:** `DEF-001`
- **Source / Location:** `upstream/main` (`94ef8e0`) -> `main`, [core.py](../../src/slices/core.py#L82), [L161-L234](../../src/slices/core.py#L161-L234), [L1917-L1998](../../src/slices/core.py#L1917-L1998) (`VALID_LJ_MIXING_MODES`, `SLICES.__init__`, `get_uncovered_pair_lj`, `get_covered_pair_lj`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L518-L582), [L629](../../src/slices/decoding_strategies.py#L629) (`_compute_lorentz_pair_lj`, `_evaluate_lorentz_lj_pairs`, `_reconstruct_zl_multistart`)
- **Category:** `Math`, `Optimization`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L160)); empirically re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); implemented in Wave 3A (`#96`, `#98`).
- **Observed Behavior:** For heteronuclear atom pairs (`i[0] != i[1]`), upstream `get_uncovered_pair_lj` and `get_covered_pair_lj` averaged `self.atom_types[i[0]]` with itself instead of `self.atom_types[i[0]]` and `self.atom_types[i[1]]`:
  ```python
  lj_param[self.atom_types[i[0]]][0]/2 + lj_param[self.atom_types[i[0]]][0]/2,
  lj_param[self.atom_types[i[0]]][1]/2 + lj_param[self.atom_types[i[0]]][1]/2
  ```
- **Why Deferred under Baseline Freeze:** Feeds directly into `SLICES.func()` repulsive terms during ZL\* `fmin_l_bfgs_b` optimization, shifting `structure_recreated_opt` fractional coordinates up to `0.110` on `14/19` Golden Corpus entries relative to upstream v4.0.2.
- **Empirical Re-Evaluation & Disposition:**
  - **Critical Units Correction:** Direct inspection of [config.py](../../src/slices/config.py#L49-L168) proved that **both columns of `LJ_PARAMS_LIST` are lengths in Angstroms (`[4*sigma, sigma]`, `max |col_0 - 4*col_1| = 6.0e-5 Å`; $\sigma = 2^{-1/6} \cdot 2 r_{\text{cov}}$)**, NOT `[r0, eps]`. The scalar well depth is `vbond_param_ave = 0.01`, and `vbond_param_ave_covered == 0.0` across `core.py` and all `.ini` configs (making `get_covered_pair_lj()` a 100% default no-op).
  - **Benchmark Result (`68` crystals, `52` heteronuclear-uncovered):** Arithmetic averaging on both columns (`[(r_cut_i + r_cut_j)/2, (sigma_i + sigma_j)/2]`) **is** exact Lorentz–Berthelot mixing, eliminates the `5.00x` $\sum \sigma^{12}$ atom-order permutation swing on `G18`, and cuts MP-20 initial `f(x0)` by `11.5x`, yet produces **`0` `match_check3` wins/losses (`62/68` strict, `63/68` loose; median `|dE| = 5.06e-7 eV/atom`)** because NequIP relaxation absorbs the `0.01..0.11` fractional shifts.
  - **Resolved in Wave 3 (`#96`, `#98`):** Exported `VALID_LJ_MIXING_MODES = ("legacy", "lorentz")` in `slices.core.__all__`; appended `lj_mixing: Literal["legacy", "lorentz"] = "legacy"` to `SLICES.__init__` (`ValueError` on unsupported modes); implemented exact arithmetic mean `[(lj_param[z0][0] + lj_param[z1][0]) / 2, (lj_param[z0][1] + lj_param[z1][1]) / 2]` in both `get_uncovered_pair_lj` and `get_covered_pair_lj` under `"lorentz"` while keeping `"legacy"` bit-for-bit identical (`89/89` golden at `atol=1e-12`); and updated `_reconstruct_zl_multistart` in `decoding_strategies.py` via `_evaluate_lorentz_lj_pairs` / `_compute_lorentz_pair_lj` to evaluate Lorentz–Berthelot mixing cleanly while unconditionally restoring `slices_inst.lj_mixing` in `try ... finally`. Verified on `G18` (`YHO2`) atom-order reversal (`"legacy"` `2,266,515.59` vs `11,332,452.00` [`5.0x`] -> `"lorentz"` `2,280,090.80 == 2,280,090.80`).
- **Impact Risk:** **High** — shifts intermediate ZL\* `opt` structures for multi-species crystals when opted in, with `0.0` drift under default `lj_mixing="legacy"`.

---

### DEF-002
- **ID:** `DEF-002` (Slice 2A Source Tags: `FC-04`, `FC-05`; cross-ref [`DEF-015`](#def-015))
- **Source / Location:** `backup/v3-personal` (`301c75f`), `backup/v3-personal:src/slices/core.py:2459-2566` vs [core.py](../../src/slices/core.py#L2526-L2835) (`SLICES.to_structures`, `SLICES.SLICES2structure`, `SLICES.robust_SLICES2structure`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L308-L866)
- **Category:** `Optimization`, `Relaxation`
- **Status:** `Keep Frozen (Default) / Opt-In Robust Decoding Enhanced in Wave 3 (VERSIONED_OPT_IN)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L161)); Stage 2A `FC-04` & `FC-05`; empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); opt-in path enhanced in Wave 3 (`#96`, `#98`).
- **Observed Behavior:** In `backup/v3-personal`, `SLICES.to_structures()` automatically injected `AdaptiveConvergence`, 3-start `MultiStartOptimizer`, and `ProgressiveRelaxer` (silently overriding `fmax=0.2` with `0.1`). In v4.0.2, `decoding_strategies.py` is strictly opt-in via `SLICES.robust_SLICES2structure()`.
- **Why Deferred under Baseline Freeze:** Auto-injecting multi-start restarts and tighter relaxation schedules breaks CPU determinism, increases runtime, and alters default `[std, opt, opt2]` outputs relative to upstream v4.0.2.
- **Empirical Re-Evaluation & Disposition:** Controlled 47-crystal (`30` normal + `17` hard) CPU `nequip-s+l` benchmarking proved that always-on `MultiStartOptimizer(n_starts=3)` + `AdaptiveConvergence` slows CPU decoding by **`1.85x–2.09x`** (up to `2.96x` on 14–20 atoms) for **`+0 / 47` net match gain** (`27/30` normal, `12/17` hard). **Default `to_structures()` / `SLICES2structure()` stays permanently frozen (`KEEP_FROZEN`)**; opt-in `robust_SLICES2structure()` remains the explicit Wave 3 recovery vehicle (upgraded in `#96`/`#98` with Lorentz–Berthelot Stage 2 mixing and `_last_gfnff_incomplete` automatic handoff at `0%` default overhead).
- **Impact Risk:** **High** — doubles default decode runtime without net accuracy gain if enabled unconditionally.

---

### DEF-003
- **ID:** `DEF-003` (Slice 2A Source Tags: `FC-01`, `FC-02`, `FC-03`; cross-ref [`DEF-010`](#def-010), [`DEF-021`](#def-021))
- **Source / Location:** `backup/v3-personal:src/slices/tobascco_net.py:500-704,985-1006` vs [tobascco_net.py](../../src/slices/tobascco_net.py#L469-L595), [L828-L830](../../src/slices/tobascco_net.py#L828-L830) (`_get_lattice_basis_via_snf`, `get_lattice_basis`, `is_integral`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L156-L190) (`CycleBasisOptimizer.find_lattice_basis`)
- **Category:** `Graph`, `Math`
- **Status:** `Split — SNF fallback Resolved on exp/v4.1-algo-upgrades (commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified) / Keep Frozen (unconditional reorder, is_integral, iter_cycles)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L162)); Stage 2A `FC-01`–`FC-03`; empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); SNF fallback implemented and A/B-verified on `exp/v4.1-algo-upgrades` (`#118`, `#121`, `#124`).
- **Observed Behavior:** `backup/v3-personal` modified `Net` in three ways: (1) reordering `cycle_rep` via `CycleBasisOptimizer` before SymPy nullspace solving, (2) adding floating-point tolerance to `is_integral`, and (3) rewriting `iter_cycles` as depth-limited BFS.
- **Why Deferred under Baseline Freeze:** Reordering `cycle_rep` alters SymPy nullspace basis vectors, metric tensors, and downstream ZL\* trajectories relative to upstream v4.0.2.
- **Empirical Re-Evaluation & Disposition:**
  - **Frozen Components (`KEEP_FROZEN`):** Unconditional `CycleBasisOptimizer` perturbs `lattice_basis` on **`69.1%` (`1,640/2,374`)** of passing MP-20 nets and flips `DEF-014` `lattice_type` on `10.95%` (`260/2,374`); exact SymPy `abs(nulv[0]) == 1` had **`0` float-noise failures** across `4,883` nets; and `iter_cycles` has **`0` callers** across SLICES.
  - **Resolved on `exp/v4.1-algo-upgrades` (`#118`, `#121`, `#124` — Exact Smith Normal Form Fallback):** Kept the primary SymPy single-nullspace-vector search in `Net.get_lattice_basis()` 100% untouched (`0.0` ULP drift and zero overhead on passing nets) and added `Net._get_lattice_basis_via_snf()` (`DomainMatrix` + `smith_normal_decomp` over `sympy.ZZ`) invoked strictly inside `if not found_vector:`; updated `CycleBasisOptimizer.find_lattice_basis()` to invoke `net.get_lattice_basis()` first before seeded row permutations. Verified `294/294` pytest pass (`5` skips) and full 2,383-crystal MP-20 + 39,244 `cRNN` A/B comparison ([AB_COMPARISON_REPORT.md](../../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md)): rescues **`7/7` (`100.0%`)** unimodular MP-20 `LatticeBasisError` crystals in `0.576–2.772 ms` at **`7/7` (`100%`) strict & loose recovery** directly in `v4.1 default` (McNemar `p = 0.0156`, matching `v4.0.2 robust` at `-1.28%` lower wall-clock and `-65.23 CPU-s`), rescues `sampled.sli idx=709` (`1.256 ms`) plus `5` `sampled.sli` and `98/401` published `unique.sli` unimodular nets, and rejects proper sublattice `mp-29816` (`SNF=(1,1,3)`) in `0.195 ms` and quasi-1D `E11` in `0.208 ms` with `0` global RNG mutation.
- **Impact Risk:** **High** — resolved cleanly via failure-path-only exact integer SNF co-deployed with `DEF-021` (`0.0` drift on all passing nets).

---

### DEF-004
- **ID:** `DEF-004`
- **Source / Location:** [tobascco_net.py](../../src/slices/tobascco_net.py#L339-L382) (`Net.simple_cycle_basis`) and [tobascco_net.py](../../src/slices/tobascco_net.py#L467-L494) (`Net.get_lattice_basis`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L163)); Stage 3 `RUL-03`; re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); implemented in Wave 1A-1 (`#85`).
- **Observed Behavior:** `simple_cycle_basis` executed unused `st_vtx = np.random.choice(...)` and `get_lattice_basis` executed unused `np.random.shuffle(inds)`, mutating global NumPy legacy RNG state without reading either result.
- **Why Deferred under Baseline Freeze:** Frozen under Stage 3 `RUL-03` during Stages 1–7 to preserve identical global `np.random` advancement prior to empirical audit.
- **Empirical Re-Evaluation & Disposition:** Re-evaluation confirmed `0` repo consumers of legacy global `np.random` and **`max_float_abs_diff = 0.0` (`0` ULP)** across `19/19` Golden Corpus entries. **Resolved in Wave 1 (`#85`):** Deleted both dead RNG calls (`0` remaining `np.random` occurrences in `tobascco_net.py`). Verified `np.random.get_state()` is 100% unchanged, `0` ruff errors, `37/37` unit tests pass, and `89/89` golden baseline tests pass (`0.0` ULP drift).
- **Impact Risk:** **Low–Medium** — zero impact on `Net` math; restores global RNG purity.

---

### DEF-005
- **ID:** `DEF-005` (cross-ref [`DEF-009`](#def-009), [`DEF-014`](#def-014), [`DEF-020`](#def-020))
- **Source / Location:** [core.py](../../src/slices/core.py#L17-L19), [L53-L58](../../src/slices/core.py#L53-L58) and [relax_backends.py](../../src/slices/relax_backends.py#L544-L552)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L164)); Stage 3 `RUL-03` & `CA-08`; re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); implemented in Wave 1A-1 (`#85`) & Wave 1A-2 (`#86`).
- **Observed Behavior:** Importing `slices.core` unconditionally overwrote `TF_CPP_MIN_LOG_LEVEL="3"`, `OMP_NUM_THREADS="1"`, `PYTHONWARNINGS="ignore"`, and installed blanket `DeprecationWarning`/`FutureWarning` filters.
- **Why Deferred under Baseline Freeze:** Frozen above imports under Stage 3 `RUL-03`/`CA-08` to prevent OpenMP/BLAS thread-pool drift during migration.
- **Empirical Re-Evaluation & Disposition:** Testing across `OMP_NUM_THREADS ∈ {1, 2, 4, 8, unset}` proved `GFN-FF`/`std`/`ZL*` have `0.0` drift and `0/19` `DEF-014` flips across `1..32` threads, `OMP=8` gives `1.41x` single-process speedup (`2.42x` in `GFN-FF`), whereas fully `unset` spawns `32` threads and slows PyTorch `2.71x`. **Resolved in Wave 1 (`#85`, `#86`):** Replaced unconditional overrides in `core.py` with `os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")` and `os.environ.setdefault("OMP_NUM_THREADS", "1")`, deleted `os.environ["PYTHONWARNINGS"] = "ignore"` and blanket filters, scoped `warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"^spglib\.")`, imported `BrunnerNNReciprocal` first (`0` `FutureWarning`s), and wrapped `ExpCellFilter` in `relax_backends._cell_filter` inside `warnings.catch_warnings()` (`DEF-009`). Preserves `0.0` default drift (`89/89` golden + `161/161` unit/int/reg green).
- **Impact Risk:** **Medium** — preserves single-thread defaults when unset while honoring explicit user `OMP_NUM_THREADS` overrides and eliminating global warning suppression.

---

### DEF-006
- **ID:** `DEF-006` (cross-ref [`DEF-028`](#def-028), [`DEF-029`](#def-029))
- **Source / Location:** [core.py](../../src/slices/core.py#L80), [L270-L301](../../src/slices/core.py#L270-L301) (`VALID_ELEMENT_MODES`, `SLICES.check_element`) vs [gfnff_helper.py](../../src/slices/gfnff_helper.py#L59-L60), [L107-L156](../../src/slices/gfnff_helper.py#L107-L156) and [config.py](../../src/slices/config.py)
- **Category:** `Compatibility`, `Math`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](PLAN.md#L165)); empirically re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); `DEF-028` floor guarded in Wave 1 (`a85e832`); opt-in modes implemented in Wave 3A (`#98`).
- **Observed Behavior:** `SLICES.check_element(structure)` previously enforced only `Z < 87` (`Z <= 86`), whereas bundled `libgfnff` supports `Z = 1..103` and `config.py` covers `Z = 1..118`.
- **Why Deferred under Baseline Freeze:** `check_element()` is locked by golden fixtures (`G16` `SmThCN` `Z=90`, `S03` `Rn`/`Fr`) and historical Materials Project filters.
- **Empirical Re-Evaluation & Disposition:** Live probing across `Z = 1..118` uncovered three distinct element tiers — `check_element` (`1..86`), `libgfnff` (`1..103`; `Z >= 104` caused Fortran OOB memory corruption -> **`DEF-028`, guarded in Wave 1 commit `a85e832`**), and `NequIP-OAM-S/L` (**non-contiguous 89-element OAM set `{1..83, 89..94}`** -> **`DEF-029`**) — with `6/6` (`100%`) real MP-20 `Ac..Pu` actinide crystals reconstructing cleanly. **Resolved in Wave 3 (`#98`):** Exported `VALID_ELEMENT_MODES = ("legacy86", "nequip_oam", "gfnff103")` in `slices.core.__all__` and extended `@staticmethod SLICES.check_element(structure, mode="legacy86")` to support `"legacy86"` (`Z < 87`, default), `"nequip_oam"` (`NEQUIP_OAM_ATOMIC_NUMBERS`, `{1..83, 89..94}`), and `"gfnff103"` (`1 <= Z <= 103`), raising `ValueError` on invalid `mode` and preserving `SLICESEncodingError` on 0-site structures (`89/89` golden parity).
- **Impact Risk:** **Medium** — changes validation acceptance sets for actinides (`Z >= 87`) and `Po/At/Rn` (`Z = 84..86`) only when callers explicitly pass `mode="nequip_oam"` or `mode="gfnff103"`.

---

### DEF-007
- **ID:** `DEF-007` (Slice 2B Source Tag: `DEF-UP-001`; Stage 3 Ruling: `RUL-01`)
- **Source / Location:** `upstream/main` (`94ef8e0`, defect introduced in `119afaf`), resolved in [core.py](../../src/slices/core.py#L108-L153) (`function_timeout`) and [exceptions.py](../../src/slices/exceptions.py#L77-L78)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_exceptions.py)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](AUDIT_UPSTREAM_STYLE.md#L233-L235)); Stage 3 `RUL-01`; implemented in Stage 4 (`49237f6`); verified in Stage 5 (`8d9314b`) and confirmed intact in [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md).
- **Observed Behavior:** `signal_handler` raised undefined `TimeoutException` (`F821`), causing `NameError` on timeouts.
- **Why Deferred under Baseline Freeze:** Approved for Stage 4 (`RUL-01`) as non-math runtime fix with zero impact on non-timed-out paths.
- **Empirical Re-Evaluation & Disposition:** `TimeoutException(SLICESError)` + POSIX main-thread `SIGALRM` guard verified intact at `HEAD=fa4cfc8` (`tests/unit/test_exceptions.py`).
- **Impact Risk:** **Low** — restores structured timeout handling without altering numerical paths.

---

### DEF-008
- **ID:** `DEF-008` (Slice 2B Source Tag: `DEF-UP-002`; Slice 2A Source Tag: `FC-08`)
- **Source / Location:** [core.py](../../src/slices/core.py#L2960-L2976) (`SLICES.relax_large_cell2`)
- **Category:** `Relaxation`, `Compatibility`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2B (`DEF-UP-002`) & Stage 2A (`FC-08`); re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** Unlike `relax` (`<=20` atoms) and `relax_large_cell1` (`21..40` atoms), `relax_large_cell2` (`>40` atoms) omitted `fmax=self.fmax, steps=self.steps`, silently running `NequIPRelaxer` defaults (`fmax=0.1, steps=500`) and breaking `ProgressiveRelaxer` tiers on large cells.
- **Why Deferred under Baseline Freeze:** Deferred in Stages 1–7 to avoid altering `>40`-atom relaxation trajectories prior to empirical verification.
- **Empirical Re-Evaluation & Disposition:** Audit confirmed **`0` structures `>40` atoms** exist in MP-20 (`16,686`), QMOF (`928`), `examples/`, `HTS/`, or `89/89` golden tests (`0.0` drift). On `10` distorted `45–64`-atom supercells, forwarding `fmax=self.fmax, steps=self.steps` converged `10/10` (`100%`), ran **`1.24x` faster** (`16.58 s` vs `20.55 s`), preserved **`9/10 == 9/10` strict match** (`mean |dE| = 0.37 meV/atom`), and fixed `ProgressiveRelaxer`. **Resolved in Wave 1 (`#86`):** Forwarded `fmax=self.fmax, steps=self.steps` in both branches of `relax_large_cell2` (`L2970`, `L2973`).
- **Impact Risk:** **Medium–High** — restores caller-configured `fmax`/`steps` for `>40`-atom cells with zero drift on shipped benchmarks.

---

### DEF-009
- **ID:** `DEF-009` (Slice 2B Source Tag: `DEF-UP-003`; cross-ref [`DEF-005`](#def-005))
- **Source / Location:** [relax_backends.py](../../src/slices/relax_backends.py#L544-L552) (`_cell_filter`)
- **Category:** `Relaxation`, `Optimization`, `Compatibility`
- **Status:** `Keep Frozen (KEEP_FROZEN; ASE warning scoped in Wave 1)`
- **Provenance:** Stage 2B (`DEF-UP-003`); empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) and stress-tested in [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); warning scoped in Wave 1A-1 (`#85`).
- **Observed Behavior:** `_cell_filter(atoms)` uses `ase.filters.ExpCellFilter(atoms)` (fallback `ase.constraints.ExpCellFilter`), which emits `DeprecationWarning: Use FrechetCellFilter` on `ase >= 3.23`.
- **Why Deferred under Baseline Freeze:** `ExpCellFilter` and `FrechetCellFilter` have distinct strain Jacobians and alter every variable-cell relaxation trajectory.
- **Empirical Re-Evaluation & Disposition:** Controlled 49-crystal (`19` Golden + `30` MP-20) CPU `nequip-s+l` A/B testing proved **`ExpCellFilter` strictly outperforms `FrechetCellFilter`** on mean BFGS steps (`11.61` vs `12.45`), wall-clock time (`347.5 ms` vs `376.4 ms`, **`8.3%` faster**), lower final energy (**`31/49` = `63.3%`** vs `10/49` = `20.4%`), and **strict `StructureMatcher` recovery (`93.48%` [`43/46`] vs `89.13%` [`41/46`], `-4.35 pp` regression)**. Verifier stress-testing identified two coarse-tolerance (`fmax=0.2 eV/Å`) `FrechetCellFilter` failure modes: premature filter-force termination on `G05` (`+8.75 meV/at` higher, `phys_fmax > 0.24 eV/Å`), and interlayer `c`-axis over-compression (`6.51 -> 4.42 Å`, `-35.32 meV/at` wrong polymorph basin) on layered `G10` (`BaSn2`). **Disposition (`KEEP_FROZEN` + Wave 1 warning scope `#85`):** Retain `ExpCellFilter` strictly as default (falling back to `FrechetCellFilter` only if a future ASE major release removes it) and suppress its `DeprecationWarning` locally inside `_cell_filter` via `warnings.catch_warnings()`.
- **Impact Risk:** **High** — switching to `FrechetCellFilter` measurably regresses crystal recovery (`-4.35 pp`).

---

### DEF-010
- **ID:** `DEF-010` (Slice 2B Source Tag: `DEF-UP-004`; cross-ref [`DEF-003`](#def-003))
- **Source / Location:** [tobascco_net.py](../../src/slices/tobascco_net.py#L384-L405) (`Net.iter_cycles`) and [tobascco_net.py](../../src/slices/tobascco_net.py#L679-L692) (`Net.vertex_positions`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2B (`DEF-UP-004`); re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md); implemented in Wave 1A-1 (`#85`).
- **Observed Behavior:** Both methods defined mutable default containers (`[]`, `{}`; `ruff` `B006`), causing repeated default calls to `iter_cycles()` to crash on call 2 with `AssertionError` and `vertex_positions()` to hit `RecursionError`.
- **Why Deferred under Baseline Freeze:** Both methods resided inside frozen `Net` pending caller audit.
- **Empirical Re-Evaluation & Disposition:** Audit confirmed `0` external callers and `0.0` drift. **Resolved in Wave 1 (`#85`):** Replaced mutable `[]` / `{}` defaults in `Net.iter_cycles` and `Net.vertex_positions` with `None` defaults + `if ... is None:` guards and removed all `# noqa: B006` suppressions. Verified stateless repeated calls (`6 == 6 == 6` cycles), `0` ruff errors, and `89/89` golden parity.
- **Impact Risk:** **Low–Medium** — eliminates stateful crash on direct calls with zero impact on `to_structures()`.

---

### DEF-011
- **ID:** `DEF-011` (Slice 2B Source Tag: `DEF-UP-005`; cross-ref [`DEF-014`](#def-014), [`DEF-034`](#def-034))
- **Source / Location:** [tobascco_net.py](../../src/slices/tobascco_net.py#L438-L465) (`linear_independent_vectors`), [L840-L855](../../src/slices/tobascco_net.py#L840-L855) (`eon_projection`, `projection`), and [L882-L888](../../src/slices/tobascco_net.py#L882-L888) (`cycle_cocycle_I`)
- **Category:** `Math`, `Compatibility`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2B (`DEF-UP-005`); empirically re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md); implemented in Wave 1A-1 (`#85`).
- **Observed Behavior:** `Net` relied on pending-deprecated `np.matrix(...).I` in `eon_projection`, `projection`, and `cycle_cocycle_I`, plus `np.matrix(r_mat)` in `linear_independent_vectors`.
- **Why Deferred under Baseline Freeze:** Stage 2 deferred removal over concern that a 1-ULP shift in `metric_tensor_std` could flip `DEF-014` `lattice_type`.
- **Empirical Re-Evaluation & Disposition:** Because all three inverted matrices are strictly square and `matrix.I` dispatches directly to `np.linalg.inv` (`dgesv`), replacing `np.array(np.matrix(...).I)` with `np.linalg.inv(...)` achieved **`max_abs_diff = 0.000e+00` (`0` ULP, `0/2,366` `DEF-014` flips)** across all `2,374` MP-20 and `19` Golden crystals (whereas `np.linalg.pinv` drifted up to `6.50e-11` and flipped `231/2,366` [`9.76%`] crystals). **Resolved in Wave 1 (`#85`):** Migrated all three inverses strictly to `np.linalg.inv(...)` (`0` `pinv`, `0` `np.matrix` remaining) and migrated `linear_independent_vectors` to `np.atleast_2d(np.asarray(r_mat))` (`DEF-034`), passing `89/89` golden tests at `0.0` ULP drift.
- **Impact Risk:** **Medium–High** (if `pinv` were misused) / **Zero** with `np.linalg.inv` — restores NumPy 3.x readiness with bit-exact parity.

---

### DEF-012
- **ID:** `DEF-012` (Slice 2B Source Tag: `DEF-UP-006`)
- **Source / Location:** [core.py](../../src/slices/core.py#L980-L1079) (`SLICES.SLICES2formula`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2B (`DEF-UP-006`); re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** Legacy `re.search(r'^(.*?)(\d+)', SLICES)` called `match.group(1)` outside `try`/`except`, silently emitting **wrong non-`None` formulas on `16/16` (`100%`) Strategy 1 strings** (`Nd2Si2Ru2 -> 'Nd1Si1'`), failing on `10/16` (`62.5%`) Strategy 2 strings, and raising uncaught `AttributeError` on digit-free strings (`"Si O"`).
- **Why Deferred under Baseline Freeze:** Deferred in Stages 1–7 to avoid changing parsing error contracts before empirical corpus verification.
- **Empirical Re-Evaluation & Disposition:** Grammar-aware Strategy 1/2/3/4 token extraction achieved **`16/16` (`100%`) across all Strategies 1–4**, **`2,383/2,383`** (`mp20_v4`), and **`14,303/14,303`** (`mp20_legacy`) with `0` `AttributeError`s. **Resolved in Wave 1 (`#86`):** Implemented full Strategy 1–4 grammar-aware `SLICES2formula` returning `None` cleanly on malformed/digit-free strings (`89/89` golden + `161/161` existing tests green).
- **Impact Risk:** **Low–Medium** — fixes silent wrong formulas on Strategy 1 and crashes on malformed inputs while preserving 100% Strategy 3/4 outputs.

---

### DEF-013
- **ID:** `DEF-013` (Slice 2B Source Tag: `DEF-UP-007`; Stage 3 Ruling: `RUL-02`, `CA-06`)
- **Source / Location:** [core.py](../../src/slices/core.py#L2750-L2753) (`SLICES.to_structures`) and [core.py](../../src/slices/core.py#L2912-L2915) (`SLICES.to_4structures`)
- **Category:** `Relaxation`, `Runtime`
- **Status:** `Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_decoding.py)`
- **Provenance:** Stage 2B (`DEF-UP-007`); Stage 3 `RUL-02` & `CA-06`; implemented in Stage 4 (`49237f6`); verified in Stage 5 (`8d9314b`) and confirmed intact in [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md).
- **Observed Behavior:** `relax_model=None` / `"none"` previously called `self.relax(...)`, raised `AttributeError`, and printed to stdout before returning `[std, opt], 0`.
- **Why Deferred under Baseline Freeze:** Approved for Stage 4 (`RUL-02`/`CA-06`) with bit-identical return values.
- **Empirical Re-Evaluation & Disposition:** `if self.relaxer is None:` short-circuit in both `to_structures` and `to_4structures` verified intact with zero stdout noise at `HEAD=fa4cfc8` (`tests/unit/test_decoding.py`).
- **Impact Risk:** **Low** — eliminates spurious stdout errors and `SIGALRM` overhead when relaxation is disabled.

---

### DEF-014
- **ID:** `DEF-014` (Slice 2B Source Tag: `DEF-UP-008`; cross-ref [`DEF-005`](#def-005), [`DEF-011`](#def-011))
- **Source / Location:** [core.py](../../src/slices/core.py#L156-L192), [L2702](../../src/slices/core.py#L2702) (`_classify_lattice_type`, `SLICES.to_structures`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L594-L629), [L729](../../src/slices/decoding_strategies.py#L729) (`_classify_lattice_type`, `_reconstruct_zl_multistart`)
- **Category:** `Math`, `Optimization`
- **Status:** `Resolved on exp/v4.1-algo-upgrades (commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified)`
- **Provenance:** Stage 2B (`DEF-UP-008`); empirically re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) and reconciled with `DEF-005` in [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); implemented and A/B-verified on `exp/v4.1-algo-upgrades` (`#116`, `#118`, `#121`, `#124`).
- **Observed Behavior:** `to_structures` and `_reconstruct_zl_multistart` classified `lattice_type` using exact IEEE-754 float `set` and `==` on the diagonal entries of `metric_tensor_std`.
- **Why Deferred under Baseline Freeze:** Replacing exact `==` with tolerant comparison shifts `lattice_type` and ZL\* optimization dimensionality relative to upstream v4.0.2 (`opt_frac`, `opt2_lattice`, `opt2_frac`, and `energy_per_atom` shift slightly above `atol=1e-12` on `14` symmetry-restored golden crystals).
- **Empirical Re-Evaluation & Disposition:** Across `2,366` active MP-20 crystals (`7,098` diagonal pairs), **`1,734 / 2,366` (`73.29%`)** lost symmetry constraints due to `1.6e-16..1.0e-13` rounding residuals across an empty 7-decade spectral gap `(1e-13, 1e-9]`. **Resolved on `exp/v4.1-algo-upgrades` (`#116`, `#118`, `#121`, `#124`):** Added pairwise `math.isclose(rel_tol=1e-9, abs_tol=1e-12)` with transitive closure (`_classify_lattice_type` returning `1`, `23`, `22`, `21`, `3`) identically in both `core.py` and `decoding_strategies.py`. Verified `294/294` pytest pass (with locked `tests/baseline/fixtures/` untouched; `max |dE| < 1e-6 eV/atom` and `0` match flips across the `14` symmetry-restored golden crystals) and full 2,383-crystal MP-20 A/B comparison ([AB_COMPARISON_REPORT.md](../../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md)): **`0` strict/loose match losses and `0` `<=0.05`/`<=0.10 eV/at` flips across all `2,374` shared `ok` crystals** (`88.04%` within `<= 1e-6 eV/at`, Wilcoxon `p = 0.1861`), with high-symmetry shared-`ok` CPU savings (`trigonal` `-1.53%`, `hexagonal` `-0.50%` mean / `-2.16%` median, `cubic` `-0.39%`; `-6.92 CPU-s` overall in `default` and `-63.37 CPU-s` in `robust`).
- **Impact Risk:** **High** — resolved and A/B-verified with zero structural or energy-threshold regressions across `2,374` shared `ok` crystals.

---

### DEF-015
- **ID:** `DEF-015` (Slice 2A Source Tag: `FC-06`; cross-ref [`DEF-002`](#def-002), [`DEF-030`](#def-030), [`DEF-031`](#def-031))
- **Source / Location:** `backup/v3-personal:src/slices/core.py:1685-1705,1758-1769,2393-2395` vs [core.py](../../src/slices/core.py#L230), [L400](../../src/slices/core.py#L400), [L1652-L1870](../../src/slices/core.py#L1652-L1870) (`_last_gfnff_incomplete`, `get_inner_p_target_debug`, `get_inner_p_target`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L220-L305), [L612-L626](../../src/slices/decoding_strategies.py#L612-L626), [L824-L866](../../src/slices/decoding_strategies.py#L824-L866) (`BondParameterFallback`, `_reconstruct_zl_multistart`, `robust_decode`)
- **Category:** `Optimization`, `Graph`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Stage 2A (`FC-06`); empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); implemented in Wave 3A (`#96`, `#98`).
- **Observed Behavior:** `backup/v3-personal` injected inline `BondParameterFallback` inside `get_inner_p_target()` (with a 1-based supercell `IndexError` bug) and changed failure return from `None` to `(None, None, None)`.
- **Why Deferred under Baseline Freeze:** Substituting covalent-radius bond estimates alters `inner_p_target` matrices and failure return contracts relative to upstream v4.0.2.
- **Empirical Re-Evaluation & Disposition:** Across `2,883` MP-20 crystals, bundled `libgfnff` returned `None` on **`0/2,883` (`0.0%`)**, while dropping hypervalent hydride/hydroxide bonds (`"Cannot find bond!!!"`) on **`0.084%–0.80%`** (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`). Routing opt-in `robust_decode` to Stage 2 `BondParameterFallback` whenever `diag(inner_p_target) <= 0` **tripled strict recovery (`25% [1/4] -> 75% [3/4]`)** at `0%` fast-path cost. **Resolved in Wave 3 (`#96`, `#98`):** Kept default `get_inner_p_target()` / `to_structures()` return contracts 100% frozen (`0.0` drift); added transient `self._last_gfnff_incomplete: bool` in `SLICES` (initialized `False`, reset on `from_SLICES`/`get_inner_p_target*`, set `True` on `"Cannot find bond!!!"`, `np.any(np.diag(inner_p_target) <= 0)`, or `get_inner_p_target` exception); and updated `robust_decode()` / `_reconstruct_zl_multistart()` to enter Stage 2 `BondParameterFallback` + Lorentz–Berthelot multi-start ZL\* + `ProgressiveRelaxer` whenever `_last_gfnff_incomplete` is `True` while preserving `stage1_result` as fallback on Stage 2/3 failure. Verified on real MP-20 bond-drop hydrides (`row=563` `Lu4H4O8`: `-7.1155 -> -7.1333 eV/atom`, `-17.88 meV/atom`; `row=994` `Eu2H6O6`) and `0.0` ULP parity on `NdSiRu.cif`.
- **Impact Risk:** **High** — modifies target matrices on dropped bonds if injected into default `core.py`; zero risk when gated inside opt-in `robust_decode`.

---

### DEF-016
- **ID:** `DEF-016` (Slice 2A Source Tag: `FC-07`)
- **Source / Location:** `backup/v3-personal:src/slices/core.py:595-635` vs [core.py](../../src/slices/core.py#L506-L515) (`SLICES.from_SLICES`)
- **Category:** `Compatibility`, `Graph`
- **Status:** `Closed — Won't Fix (CLOSE_WONTFIX; Blocked in Stage 3)`
- **Provenance:** Stage 2A (`FC-07`); Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](REVIEW_SIGNOFF.md#L135)); verified intact in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md).
- **Observed Behavior:** Fork swallowed invalid Strategy-4 space-group prefix errors (`space_group_num = None`), accepting malformed strings upstream rejects.
- **Why Deferred under Baseline Freeze:** Blocked permanently in Stage 3 (`E03_bad_sg_prefix` `"q q q Si O 0 1 ooo"` must reject).
- **Empirical Re-Evaluation & Disposition:** Re-evaluation verified Stage 3 block ruling 100% intact at `HEAD=fa4cfc8`. **Permanently closed (`CLOSE_WONTFIX`).**
- **Impact Risk:** **High** — would silently accept corrupted Strategy-4 prefixes if ported.

---

### DEF-017
- **ID:** `DEF-017` (Slice 2A Source Tag: `FC-09`)
- **Source / Location:** `backup/v3-personal:src/slices/core.py:483-540` vs [core.py](../../src/slices/core.py#L53-L58), [L317-L367](../../src/slices/core.py#L317-L367) (`cif2structure_graph`, `structure2structure_graph`; fixed upstream in `2635bcc`)
- **Category:** `Compatibility`
- **Status:** `Closed — Won't Fix (CLOSE_WONTFIX; Resolved Upstream in 2635bcc)`
- **Provenance:** Stage 2A (`FC-09`); Stage 2B commit `#21` (`2635bcc`); verified intact in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md).
- **Observed Behavior:** Fork kept deprecated `StructureGraph.with_local_env_strategy` (which emits `FutureWarning` on `pymatgen==2025.10.7` and breaks on `>=2026.3`). Upstream `2635bcc` migrated to `from_local_env_strategy` and `BrunnerNNReciprocal`.
- **Why Deferred under Baseline Freeze:** Recorded to prevent regression during Stage 4 refactoring.
- **Empirical Re-Evaluation & Disposition:** Verified `from_local_env_strategy` and `BrunnerNNReciprocal` active at `HEAD=fa4cfc8` (and Wave 1 `DEF-005` prioritized `BrunnerNNReciprocal` first to eliminate import-order `FutureWarning`). **Permanently closed (`CLOSE_WONTFIX`).**
- **Impact Risk:** **High** (if regressed) — breaks `pymatgen >= 2025/2026` compatibility.

---

### DEF-018
- **ID:** `DEF-018` (Slice 2A Source Tag: `FC-10`)
- **Source / Location:** [core.py](../../src/slices/core.py#L294-L295), [L342-L345](../../src/slices/core.py#L342-L345), [L1100-L1101](../../src/slices/core.py#L1100-L1101) (`check_element`, `structure2structure_graph`, `to_primitive_if_smaller`) and [exceptions.py](../../src/slices/exceptions.py#L35-L41)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2A (`FC-10`); re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** On a 0-site `Structure`, `to_primitive_if_smaller` swallowed Spglib's error and returned the empty structure, causing `structure2SLICES(empty)` to silently return `""` and `structure2randomSLICES(empty)` to silently return `[""]`.
- **Why Deferred under Baseline Freeze:** Encoding entry points were frozen during Stages 1–7 pending empty-input verification.
- **Empirical Re-Evaluation & Disposition:** Confirmed silent `""` / `[""]` corruption and `0` regressions across `255` tests when raising `(SLICESEncodingError, ValueError)`. **Resolved in Wave 1 (`#86`):** Updated `SLICESEncodingError(SLICESError, ValueError)` in `exceptions.py` and added `if len(structure) == 0: raise SLICESEncodingError(...)` guards in `check_element`, `structure2structure_graph`, and `to_primitive_if_smaller`.
- **Impact Risk:** **Low–Medium** — affects only degenerate 0-atom `Structure` inputs.

---

### DEF-019
- **ID:** `DEF-019` (Slice 2A Source Tag: `FC-11`; cross-ref [`DEF-025`](#def-025))
- **Source / Location:** [core.py](../../src/slices/core.py#L630-L701) (`get_slices1..3`) and [core.py](../../src/slices/core.py#L758-L782) (`check_structural_validity`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Resolved in Wave 1 (Part 2 SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity) / Closed — Won't Fix (Part 1 4-arg get_slices1..3)`
- **Provenance:** Stage 2A (`FC-11`); re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); Part 2 implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** `backup/v3-personal` (1) removed the 4th parameter `space_group_num=None` from `get_slices1..3` (breaking `get_slices_by_strategy` 4-arg dispatch) and (2) added a `TypeError` check on `check_structural_validity`.
- **Why Deferred under Baseline Freeze:** Part 1 breaks Strategy 1–3 encoding outright; Part 2 shifted `AttributeError -> TypeError` on invalid inputs.
- **Empirical Re-Evaluation & Disposition:**
  - **Part 1 (`CLOSE_WONTFIX`):** 4-arg `get_slices1..3(..., space_group_num=None)` is permanently required across 5 dispatch sites.
  - **Part 2 (`Resolved in Wave 1`, `#86`):** Unified with `DEF-025` in `check_structural_validity`: checks `if not isinstance(str1, IStructure): raise TypeError(...)` (accepting both `Structure` and `IStructure`) with `0` caller/test regressions.
- **Impact Risk:** **Medium** — Part 1 stays permanently closed; Part 2 hardens type checking on invalid callers.

---

### DEF-020
- **ID:** `DEF-020` (Slice 2A Source Tag: `FC-12`; cross-ref [`DEF-005`](#def-005))
- **Source / Location:** `backup/v3-personal:src/slices/core.py:10-43,164-232` & `mlip_relaxer.py:22-35` vs [core.py](../../src/slices/core.py#L17-L19), [__init__.py](../../src/slices/__init__.py), [mlip_relaxer.py](../../src/slices/mlip_relaxer.py)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Closed — Won't Fix (CLOSE_WONTFIX; Blocked in Stage 3)`
- **Provenance:** Stage 2A (`FC-12`); Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](REVIEW_SIGNOFF.md#L135)); verified intact in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md).
- **Observed Behavior:** Fork mutated Python's global root logger to `CRITICAL` and eagerly injected `TF_USE_LEGACY_KERAS="1"`, `sys.modules["keras"] = tf_keras`, and TF GPU probes at import time.
- **Why Deferred under Baseline Freeze:** Blocked permanently in Stage 3 to protect PyTorch-only environments and host logging.
- **Empirical Re-Evaluation & Disposition:** Verified intact at `HEAD=fa4cfc8`: root logger stays `WARNING` (`30`), `tensorflow`/`keras` absent from `sys.modules` on import, `TF_USE_LEGACY_KERAS` isolated to `M3GNetRelaxer.__init__`. **Permanently closed (`CLOSE_WONTFIX`).**
- **Impact Risk:** **High** — corrupts host logging and breaks TF-free environments if ported.

---

### DEF-021
- **ID:** `DEF-021` (Slice 2C Source Tag: `DEF-BC-01`; cross-ref [`DEF-003`](#def-003))
- **Source / Location:** [core.py](../../src/slices/core.py#L823-L935) (`SLICES.check_SLICES`), [core.py](../../src/slices/core.py#L2637-L2652) (`SLICES.to_structures`), and [tobascco_net.py](../../src/slices/tobascco_net.py#L204-L235), [L469-L595](../../src/slices/tobascco_net.py#L469-L595)
- **Category:** `Graph`, `Math`, `Compatibility`
- **Status:** `Resolved in Wave 1 (to_structures LatticeBasisError/CocycleBasisError; commit a85e832) + Resolved on exp/v4.1-algo-upgrades (check_SLICES; commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified)`
- **Provenance:** Stage 2C (`DEF-BC-01`); empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); Wave 1 crash hygiene implemented in Wave 1A-2 (`#86`); `check_SLICES` enforcement implemented and A/B-verified on `exp/v4.1-algo-upgrades` (`#116`, `#121`, `#124`).
- **Observed Behavior:** `check_SLICES()` previously ignored `net.get_lattice_basis() == -1` and cocycle rank failure, returning `True` on non-3D/rank-deficient graphs (`E11` `TiBr3`), while `to_structures()` previously crashed with `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`.
- **Why Deferred under Baseline Freeze:** Changing `check_SLICES()` alters validity rates and golden fixture `E11_quasi1d_lattice_basis_neg1`.
- **Empirical Re-Evaluation & Disposition:**
  - **Wave 1 Resolved (`#86`, commit `a85e832`):** `to_structures()` now raises `LatticeBasisError` on `basis_status == -1` / `net.lattice_basis is None` and `CocycleBasisError` on incomplete multi-vertex cocycle bases (`net.order > 1`), preserving 1-atom `G14` (`net.order == 1`).
  - **Resolved on `exp/v4.1-algo-upgrades` (`#116`, `#121`, `#124`, co-deployed with `DEF-003` SNF fallback):** Updated `check_SLICES()` strictly under `if graph_rank_check:` to return `False` on `basis_status == -1 or net.lattice_basis is None` or multi-vertex (`net.order > 1`) incomplete cocycle bases (`net.cocycle is None or net.cocycle_rep is None or net.cocycle.ndim != 2 or len(net.cocycle) < net.order - 1`), preserving 1-atom primitive cells (`G14 Na -> True`) and `graph_rank_check=False` RL workflows. Verified `294/294` pytest pass (`E11` `check_default/dupli: True -> False`, `mininn` 2D `NdSiRu -> False` / 3D `CsCl -> True`) and full `39,244`-string `cRNN` scan ([AB_COMPARISON_REPORT.md](../../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md)): rescues `5` & rejects `4` on `sampled.sli` (`18.10% -> 17.70%`), and rescues `98/401` unimodular crystals while rejecting `303/401` (`0.79%`) non-invertible graphs across `38,244` published `unique.sli` strings with **`0/303` (`0.00%`) surviving `4_inverse`**.
- **Impact Risk:** **High** — fully resolved; aligns `check_SLICES(..., graph_rank_check=True)` exactly with 3D topological invertibility.

---

### DEF-022
- **ID:** `DEF-022` (Slice 2C Source Tag: `DEF-BC-02`; cross-ref [`DEF-033`](#def-033))
- **Source / Location:** [core.py](../../src/slices/core.py#L1156-L1429) (`SLICES.structure2randomSLICES`, `SLICES.structure2SLICESAug_atom_order`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-02`); empirically re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md) and [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); implemented in Wave 3A (`#98`).
- **Observed Behavior:** `structure2randomSLICES()` converts `SLICES_set = set()` to `list()` prior to `random.shuffle()`, making cross-process list ordering dependent on `PYTHONHASHSEED` even with `random.seed(42)`.
- **Why Deferred under Baseline Freeze:** Replacing `list(SLICES_set)` with `sorted(...)` or insertion-ordered `dict` changes the exact permutation returned under `PYTHONHASHSEED=0` (`15/16` or `16/16` `random_slices_5` fixtures).
- **Empirical Re-Evaluation & Disposition:** Across `PYTHONHASHSEED ∈ {0, 1, 42, 999}`, legacy `set()` has **`0/16` (`0%`)** exact-list invariance at `num=5` and **`3/16` (`18.8%`)** set invariance at `num=1` (`DEF-033`), whereas insertion-ordered `dict` achieves **`16/16` (`100%`)** invariance. **Resolved in Wave 3 (`#98`):** Added `seed: int | None = None` to both `structure2randomSLICES` and `structure2SLICESAug_atom_order`. When `seed is None` (default), the exact v4.0.2 `random` / `set` path executes (`89/89` golden parity); when an integer `seed` is passed, an isolated `random.Random(seed)` instance, insertion-ordered `seen: dict[str, None] = {}`, pre-loop `if len(seen) >= num: break` guard (`DEF-033`), and `rng.shuffle(slices_list)` deliver `100%` identical outputs across `PYTHONHASHSEED=0` vs `PYTHONHASHSEED=999` with `0` global `random.getstate()` mutation.
- **Impact Risk:** **Low–Medium** — affects only opt-in seeded augmentation ordering and `num < len(seen)` subset selection without altering default `seed=None` behavior.

---

### DEF-023
- **ID:** `DEF-023` (Slice 2C Source Tag: `DEF-BC-03`)
- **Source / Location:** [core.py](../../src/slices/core.py#L229), [L399](../../src/slices/core.py#L399), [L2448-L2522](../../src/slices/core.py#L2448-L2522) (`SLICES.from_SLICES`, `SLICES.SLICES2space_group_number`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-03`); empirically re-evaluated in [REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** `SLICES2space_group_number()` previously branched on `if self.unstable_graph:` (`net.cocycle_rep = ... + 0.5`), reading stale instance state left over from a prior `to_structures()` call on an unstable net (`G18` `YHO2`).
- **Why Deferred under Baseline Freeze:** The initial Stage 2 proposal (computing `unstable_graph` locally and applying `+0.5`) would have altered fresh-instance predictions on degenerate nets.
- **Empirical Re-Evaluation & Disposition:** Reusing a contaminated instance (`unstable_graph=True`, occurring on `16/2,374 = 0.67%` of `mp20_v4`) **collapsed SG accuracy from `91.62%` (`2,175/2,374`) to `4.68%` (`111/2,374`)** (`13/16` Golden CIFs corrupted). Crucially, applying `+0.5` cocycle locally **regressed unstable-subset SG accuracy from `56.25%` (`9/16`) to `12.50%` (`2/16`)** because non-zero cocycle breaks automorphism-equivariant barycentric symmetry (Delgado-Friedrichs–O'Keeffe theorem). **Resolved in Wave 1 (`#86`):** Deleted `if self.unstable_graph:` inside `SLICES2space_group_number` and reset `self.unstable_graph = False` at `from_SLICES` entry (`L399`), fixing 100% of reuse corruption (`NdSiRu -> 129` after `G18`) at `0.0` fresh/golden drift.
- **Impact Risk:** **Medium** — eliminates severe instance-reuse corruption while preserving 100% fresh-instance accuracy.

---

### DEF-024
- **ID:** `DEF-024` (Slice 2C Source Tag: `DEF-BC-04`; cross-ref [`DEF-016`](#def-016), [`DEF-019`](#def-019))
- **Source / Location:** [core.py](../../src/slices/core.py#L371-L596), [L784-L913](../../src/slices/core.py#L784-L913) (`SLICES.from_SLICES`, `_is_int_token`, `check_SLICES`, `check_SLICES_basic`) vs [core.py](../../src/slices/core.py#L659-L679) (`SLICES.get_slices2`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Resolved in Wave 1 + Wave 3 (Gaps 1, 2, 3b, 4 SAFE_NOW commit a85e832 / Gap 3a strict=True VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-04`); empirically re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md) & [REEVAL_SYNTHESIS.md](reeval/REEVAL_SYNTHESIS.md); Wave 1 gaps implemented in Wave 1A-2 (`#86`); Gap 3a implemented in Wave 3A (`#98`).
- **Observed Behavior:** Four input-parsing gaps existed in `from_SLICES()`: (1) missing `strategy == 2` / invalid strategy guard (`UnboundLocalError`), (2) zero-edge strings (`"Si O"`) leaving `num_atoms` unbound, (3a/3b) silent truncation of trailing partial edge tokens and extra `len(edge[2]) > 3` label characters, and (4) unchecked negative `< 0` node indices.
- **Why Deferred under Baseline Freeze:** Tightening parser rejections could reject historical benchmark strings or alter golden exception strings (`E01`–`E05`).
- **Empirical Re-Evaluation & Disposition:** Scanning **`125,174` SLICES strings (`28` files)** showed `0` rely on `strategy=2` decode (non-injective `mod 100` collision for `>100` atoms), zero-edge strings, `len(label) > 3`, or `< 0` indices — **but `13/999` (`1.30%`) PBE-screened rows in `HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv` have RNN-truncated trailing partial edge tokens and pass `check_SLICES(strategy=3)` today**.
  - **Wave 1 Resolved (Gaps 1, 2, 3b, 4 — `#86`, commit `a85e832`):** Updated `SLICESDecodingError(SLICESError, ValueError)` in `exceptions.py`; raised `SLICESDecodingError` on `strategy not in (1, 3, 4)` (including encode-only `strategy=2`) and zero-numeric-edge / zero-complete-edge strings; added signed-integer `_is_int_token`; enforced `0 <= idx < num_atoms` via `Exception("Error: wrong edge indices")` and `len(edge[2]) == 3` in Strategy 4 via `Exception("Error: wrong edge label")`, preserving `E01`–`E05` golden exception strings verbatim (`89/89` green) and keeping trailing partial tokens lenient.
  - **Wave 3 Resolved (Gap 3a `VERSIONED_OPT_IN` — `#98`):** Added `strict: bool = False` to `from_SLICES`, `check_SLICES`, and `check_SLICES_basic`. When `strict=True`, verifies `(len(tokens) - edge_start_idx) % stride == 0` (stride `7` for Strategy 1, `5` for Strategy 3, `3` for Strategy 4) and raises `SLICESDecodingError` (causing `check_SLICES`/`check_SLICES_basic` to return `False`) on trailing partial edge tokens, while `strict=False` preserves 100% replay compatibility for `HTS/9_EAH_Band_gap_PBE` and `89/89` golden tests. **All four parsing gaps of `DEF-024` are now fully resolved.**
- **Impact Risk:** **Medium** — eliminates `UnboundLocalError`, negative-index wraparound, extra-label truncation, and (under `strict=True`) silent partial-edge truncation at `0.0` default golden/HTS drift.

---

### DEF-025
- **ID:** `DEF-025` (Slice 2C Source Tag: `DEF-BC-05`; cross-ref [`DEF-019`](#def-019))
- **Source / Location:** [core.py](../../src/slices/core.py#L758-L782) (`SLICES.check_structural_validity`)
- **Category:** `Math`, `Compatibility`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-05`); empirically re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** Checking only strictly upper-triangular `i < j` pairs returned false `True` on 1-atom collapsed cells (`a = 0.3 Å`, `a = 0.5 Å`), 2-atom short-axis cells, and sheared cells where `min(abc) = 1.0 Å > 0.5 Å` yet `|a - b| = 0.2956 Å <= 0.5 Å` (`D5`/`D6`, defeating naive `min(abc) > 0.5`), and raised `ValueError` on 0-site structures.
- **Why Deferred under Baseline Freeze:** Deferred pending empirical check across Golden and MP-20 corpora.
- **Empirical Re-Evaluation & Disposition:** `str1.get_neighbor_list(r=0.5 + 1e-9)` excluding `(i == j) & np.all(img == 0, axis=1)` caught all degenerate and sheared cases at `+47.6 us/call` with **`0/59` Golden and `0/18,093` MP-20 flips**. **Resolved in Wave 1 (`#86`):** Unified with `DEF-019` Part 2 (`isinstance(str1, IStructure)` -> `len == 0 -> False` -> `get_neighbor_list(r=0.5 + 1e-9)`), passing `89/89` golden + `161/161` tests green.
- **Impact Risk:** **Low–Medium** — catches degenerate periodic self-image collisions with zero drift on physical crystals.

---

### DEF-026
- **ID:** `DEF-026` (Slice 2C Source Tag: `DEF-BC-06`)
- **Source / Location:** [core.py](../../src/slices/core.py#L81), [L213-L216](../../src/slices/core.py#L213-L216), [L362-L366](../../src/slices/core.py#L362-L366), [L1453-L1457](../../src/slices/core.py#L1453-L1457) (`VALID_GRAPH_METHODS`, `SLICES.__init__`, `structure2structure_graph`, `get_dim`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-06`); Stage 3 Sign-Off; re-evaluated in [REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** Invalid `graph_method` strings were accepted in `__init__` and then printed to stdout before crashing with `UnboundLocalError`.
- **Why Deferred under Baseline Freeze:** Kept frozen under Stage 3 Sign-Off pending audit of all `.ini` configs and callers.
- **Empirical Re-Evaluation & Disposition:** Verified `20/20` `.ini` configs (`17` `econnn`, `3` `crystalnn`) and `100%` of callers use valid methods. **Resolved in Wave 1 (`#86`):** Defined and exported `VALID_GRAPH_METHODS = ("econnn", "crystalnn", "brunnernn", "mininn")` and raised `ValueError` in `SLICES.__init__`, `structure2structure_graph`, and `get_dim`.
- **Impact Risk:** **Low** — zero impact on valid callers; replaces `UnboundLocalError` with clear `ValueError`.

---

### DEF-027
- **ID:** `DEF-027` (Slice 2C Source Tag: `DEF-BC-07`)
- **Source / Location:** [core.py](../../src/slices/core.py#L2314-L2446) (`SLICES.func_check`) vs [core.py](../../src/slices/core.py#L2248-L2312) (`SLICES.func`)
- **Category:** `Math`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Stage 2C (`DEF-BC-07`); re-evaluated in [REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** Debug objective `func_check()` lacked `func()`'s `1e-10` and `1e-8` distance clamps, reproducing `4 * 0.0 * inf -> nan` and `0.0 / 0.0 -> nan` on real Golden `G18` (`YHO2`) at `cocycle=0`.
- **Why Deferred under Baseline Freeze:** Resided in the frozen ZL\* objective section during Stages 1–7.
- **Empirical Re-Evaluation & Disposition:** `0` calls when `check_results=False` and `0.0` diff at converged `x_opt`. **Resolved in Wave 1 (`#86`):** Mirrored `func()`'s `np.sqrt(max(..., 1e-10))` (both bond $r^{-12}$ and angle print denominators) and `r_temp = max(r_temp, 1e-8)` guards in `func_check()` (`0.0` diff vs `func()` and `0` `RuntimeWarning`s on `G18`).
- **Impact Risk:** **Low** — fixes `NaN`/`ZeroDivisionError` strictly in `check_results=True` diagnostic mode.

---

### DEF-028
- **ID:** `DEF-028` (Parent Investigation: [`DEF-006`](#def-006))
- **Source / Location:** [gfnff_helper.py](../../src/slices/gfnff_helper.py#L59-L60), [L107-L156](../../src/slices/gfnff_helper.py#L107-L156) (`parse_nbf_text`, `_MIN_GFNFF_Z`, `_MAX_GFNFF_Z`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) & live verifier probe in [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 1A-1 (`#85`).
- **Observed Behavior:** Passing any element with `Z >= 104` (`Rf..Og`, valid symbols in `pymatgen` and `config.py`) into bundled `libgfnff.so.0.1.1` indexed past the 103-element Fortran parameter tables without bounds checking, reading non-deterministic heap/BSS memory garbage (verified live: `Db` `Z=105` returned `r0 = 969.63 Bohr` on call 1 vs **`-1,648,270,880.45 Bohr`** on call 2; `Rf` `Z=104` returned subnormal `-2.095e-321`).
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 live probing of `Z = 1..118` (`DEF-006`).
- **Empirical Re-Evaluation & Disposition:** Classified as a **Critical `SAFE_NOW` memory-safety guard** required before any higher-`Z` Wave 3 opt-in (`DEF-006`). **Resolved in Wave 1 (`#85`):** Added `_MIN_GFNFF_Z = 1` and `_MAX_GFNFF_Z = 103` in `gfnff_helper.py` and enforced `1 <= Z <= 103` in `parse_nbf_text` prior to any `libgfnff.so.0.1.1` or fallback `xtb` call, raising `GFNFFExecutionError` naming unsupported symbol(s) and `Z` (e.g., `Rf (Z=104)`, `Db (Z=105)`) while preserving `ValueError` for malformed syntax or unrecognized tokens. Verified `Th (Z=90)` and `Lr (Z=103)` succeed with finite `vbond`, `Rf`/`Db`/`Og` raise `GFNFFExecutionError`, and `89/89` golden tests pass.
- **Impact Risk:** **Critical** — prevents unguarded C/Fortran out-of-bounds memory reads and non-deterministic memory corruption.

---

### DEF-029
- **ID:** `DEF-029` (Parent Investigation: [`DEF-006`](#def-006))
- **Source / Location:** [relax_backends.py](../../src/slices/relax_backends.py#L88), [L577-L600](../../src/slices/relax_backends.py#L577-L600), [L637-L700](../../src/slices/relax_backends.py#L637-L700) (`NEQUIP_OAM_ATOMIC_NUMBERS`, `_validate_nequip_elements`, `NequIPRelaxer.relax`) and [core.py](../../src/slices/core.py#L80), [L270-L301](../../src/slices/core.py#L270-L301) (`VALID_ELEMENT_MODES`, `SLICES.check_element`)
- **Category:** `Compatibility`, `Relaxation`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) & live verifier probe in [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 3A (`#96`, `#98`).
- **Observed Behavior:** `NequIP-OAM-S/L` supports the non-contiguous 89-element OAM vocabulary `{1..83, 89..94}`: `Po, At, Rn` (`Z = 84..86`) passed `check_element()` (`Z < 87`) and `libgfnff` then crashed `NequIPRelaxer` with a raw TorchScript `KeyError`, whereas `Ac..Pu` (`Z = 89..94`) were rejected by `check_element()` despite achieving `6/6` (`100%`) end-to-end strict reconstruction accuracy on real MP-20 actinide crystals.
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 live probing of `Z = 1..118`; changing default `check_element()` would break locked `Z <= 86` golden fixtures (`G16`, `S03`).
- **Empirical Re-Evaluation & Disposition:** Because NequIP-OAM's supported set is non-contiguous (`{1..83, 89..94}`), a single `max_z` threshold cannot accurately validate it. **Resolved in Wave 3 (`#96`, `#98`):** Exported `NEQUIP_OAM_ATOMIC_NUMBERS: frozenset[int] = frozenset(range(1, 84)) | frozenset(range(89, 95))` in `slices.relax_backends.__all__`, added `_validate_nequip_elements(atoms)` invoked at the start of `NequIPRelaxer.relax()` prior to `preoptimize()` and calculator evaluation (raising `RelaxBackendError` naming unsupported symbols & `Z` such as `Po (Z=84)`, `Rn (Z=86)`, `Am (Z=95)` and `{1..83, 89..94}`), and wired `SLICES.check_element(structure, mode="nequip_oam")` directly to `NEQUIP_OAM_ATOMIC_NUMBERS`. Verified `RelaxBackendError` on `Po`/`Rn`/`Am`, live relaxation success on `NdSiRu` (`-43.609947 eV`) and `Th (Z=90)` (`-2.685131 eV`), and `89/89` golden parity.
- **Impact Risk:** **Medium** — eliminates cryptic `KeyError` on unsupported elements (`Po..Ra`, `Am..Og`) and unlocks validated `Ac..Pu` actinide decoding via opt-in `mode="nequip_oam"`.

---

### DEF-030
- **ID:** `DEF-030` (Parent Investigation: [`DEF-015`](#def-015))
- **Source / Location:** [core.py](../../src/slices/core.py#L1706-L1707) (`SLICES.get_inner_p_target_debug`) and [core.py](../../src/slices/core.py#L1814-L1817) (`SLICES.get_inner_p_target`)
- **Category:** `Math`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) & [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** `math.cos(data["vangl"][i][0])` lacked the finiteness guard already applied to `vbond`, raising `ValueError: math domain error` whenever `libgfnff` emitted a `NaN` equilibrium angle (observed on `1/1,000` cRNN strings, `idx 609`).
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 large-scale `libgfnff` stress testing (`3,883` topology evaluations).
- **Empirical Re-Evaluation & Disposition:** Skipping non-finite `vangl` entries has `0.0` drift on every crystal with finite angles and prevents mid-target crashes. **Resolved in Wave 1 (`#86`):** Added `if not np.isfinite(data["vangl"][i][0]) or not np.isfinite(data["vangl"][i][1]): continue` in both `get_inner_p_target_debug` (`L1706-L1707`) and `get_inner_p_target` (`L1814-L1817`).
- **Impact Risk:** **Low–Medium** — prevents `ValueError: math domain error` on rare `NaN` GFN-FF angles with `0.0` golden drift.

---

### DEF-031
- **ID:** `DEF-031` (Parent Investigation: [`DEF-015`](#def-015))
- **Source / Location:** [core.py](../../src/slices/core.py#L1725-L1802), [L1835-L1914](../../src/slices/core.py#L1835-L1914) (`get_inner_p_target_debug`, `get_inner_p_target`) and [decoding_strategies.py](../../src/slices/decoding_strategies.py#L660-L675), [L807-L866](../../src/slices/decoding_strategies.py#L807-L866) (`_reconstruct_zl_multistart`, `robust_decode`)
- **Category:** `Optimization`, `Graph`
- **Status:** `Resolved in Wave 3 (robust_decode Stage 2 trigger; commit e5c7f0d) + Resolved on exp/v4.1-algo-upgrades (core.py matched_bond_indices alignment; commit d922032, verified in cd76ac5 & 36fa8e5; 294/294 pytest + 2,383-crystal MP-20 A/B verified)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_GRAPH_RELAX.md](reeval/REEVAL_GRAPH_RELAX.md) & [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); Stage 2 trigger implemented in Wave 3A (`#96`, `#98`); core `matched_bond_indices` alignment implemented and A/B-verified on `exp/v4.1-algo-upgrades` (`#116`, `#121`, `#124`).
- **Observed Behavior:** When `"Cannot find bond!!!"` skipped $k$ edges (`0.084%` `mp20_v4`, `0.80%` `mp20/test` hypervalent hydrides), `for i in range(len(bond_weight)): colattice_inds[0].append(i)` attached diagonal bond weights to indices `0..E-k-1` instead of the true matched edge indices, and `robust_decode` previously returned Stage 1's distorted crystal instead of entering Stage 2 `BondParameterFallback`.
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1; aligning indices in `core.py` changes `colattice_inds` on the `0.084%–0.80%` hydride subset where bonds are dropped.
- **Empirical Re-Evaluation & Disposition:**
  - **Wave 3 Resolved (`VERSIONED_OPT_IN` — `#96`, `#98`, commit `e5c7f0d`):** Tracked `self._last_gfnff_incomplete` in `SLICES.get_inner_p_target*` and updated `robust_decode()` / `_reconstruct_zl_multistart()` to enter Stage 2 `BondParameterFallback` automatically (`stage1_result` preserved as fallback).
  - **Resolved on `exp/v4.1-algo-upgrades` (`#116`, `#121`, `#124` — core `matched_bond_indices` alignment):** Added `matched_bond_indices: list[int] = []` alongside `bond_weight` in both `get_inner_p_target_debug()` and `get_inner_p_target()` and iterated `zip(matched_bond_indices, bond_weight, strict=True)` so diagonal `(edge_idx, edge_idx)` entries and normalized weights align verbatim with `np.where(np.diag(inner_p_target) > 0)[0]` (`0.0` ULP drift on all `19/19` Golden crystals). Verified `294/294` pytest pass and full 2,383-crystal MP-20 A/B comparison ([AB_COMPARISON_REPORT.md](../../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md)): improves `row=563` (`mp-1176505` `Lu4H4O8`) by **`-12.16 meV/atom`** (`default`) / `-9.53 meV/atom` (`lorentz`) with **`preoptimized: True -> False`** and BFGS steps **`44 -> 18` (`-59.1%`)**, and improves `row=994` (`mp-625477` `Eu2H6O6`) by **`-48.06 meV/atom`** (`default`, BFGS `66 -> 48`) and **`-55.81 meV/atom`** (`lorentz`).
- **Impact Risk:** **Medium–High** — fully resolved across both opt-in `robust_decode` and standard `core.py` decoding with zero drift on complete-GFN-FF crystals.

---

### DEF-032
- **ID:** `DEF-032` (Parent Investigation: [`DEF-001`](#def-001))
- **Source / Location:** [core.py](../../src/slices/core.py#L1890-L1915) (`SLICES.get_uncovered_pair`)
- **Category:** `Math`, `Graph`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) & [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 1A-2 (`#86`).
- **Observed Behavior:** When `from_SLICES(..., fix_duplicate_edge=False)` or direct `SLICES(edge_indices=...)` supplied a bonded edge `[u, v]` with `u > v`, `unique_covered_pair_int` stored `[u, v]` and failed to match upper-triangular `[v, u]` in `triu_pair`, erroneously applying non-bonded LJ repulsion across a bonded edge.
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 audit of `get_uncovered_pair` / `get_uncovered_pair_lj`.
- **Empirical Re-Evaluation & Disposition:** Canonicalizing undirected covered pairs has `0.0` drift on all canonical / `fix_duplicate_edge=True` / CIF-encoded paths while preventing spurious bonded-edge repulsion when `u > v`. **Resolved in Wave 1 (`#86`):** Canonicalized `covered_pair` entries as `(min(u, v), max(u, v))` deduplicated via `dict.fromkeys` (`L1902-L1905`).
- **Impact Risk:** **Low–Medium** — eliminates non-bonded LJ artifacts on reversed-orientation graph inputs with `0.0` golden drift.

---

### DEF-033
- **ID:** `DEF-033` (Parent Investigation: [`DEF-022`](#def-022))
- **Source / Location:** [core.py](../../src/slices/core.py#L1156-L1399) (`SLICES.structure2randomSLICES`, pre-loop guard `L1222-L1223`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Wave 3 (VERSIONED_OPT_IN; commit e5c7f0d, verified in 0e51ff0, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_RUNTIME_PARSE.md](reeval/REEVAL_RUNTIME_PARSE.md) & live verifier probe in [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 3A (`#98`).
- **Observed Behavior:** Because `if len(SLICES_set) >= num: break` executes at the *end* of loop iteration `0` after `SLICES_set.add(original_SLICES)`, calling `structure2randomSLICES(..., num=1)` inserted 2 distinct strings into `SLICES_set` and returned `list(SLICES_set)[:1]`, causing `13/16` (`81.25%`) Golden CIFs to return different single strings across `PYTHONHASHSEED` (`3` distinct outputs on `NdSiRu` across 4 hashseeds).
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 `PYTHONHASHSEED` invariance experiments (`DEF-022`); changing the default loop termination alters `PYTHONHASHSEED=0` golden outputs.
- **Empirical Re-Evaluation & Disposition:** **Resolved in Wave 3 (`#98`, paired with `DEF-022`):** Added pre-loop `if len(seen) >= num: break` (`core.py:1222-1223`) inside the opt-in `seed is not None` branch of `structure2randomSLICES`, ensuring `num=1` deterministically returns `[original_SLICES]` across all `PYTHONHASHSEED` values while preserving exact default `seed=None` behavior (`89/89` golden parity).
- **Impact Risk:** **Low–Medium** — fixes `num=1` augmentation hashseed sensitivity under opt-in `seed` with `0.0` default drift.

---

### DEF-034
- **ID:** `DEF-034` (Parent Investigation: [`DEF-011`](#def-011))
- **Source / Location:** [tobascco_net.py](../../src/slices/tobascco_net.py#L438-L465) (`Net.linear_independent_vectors`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Resolved in Wave 1 (SAFE_NOW; commit a85e832, verified in 954a56a, 89/89 golden parity)`
- **Provenance:** Post-Migration Re-Eval ([REEVAL_MATH_OPT.md](reeval/REEVAL_MATH_OPT.md) & [REEVAL_SYNTHESIS.md Section 3.2](reeval/REEVAL_SYNTHESIS.md#L86-L97)); implemented in Wave 1A-1 (`#85`).
- **Observed Behavior:** Dead legacy helper (`0` callers in SLICES) allocated `index = np.zeros(r)` and incremented `counter` without bounding `counter < r - 1`, overflowing with `IndexError` on rank-deficient rectangular matrices (e.g., shape `(3, 4)` of rank `2`) when more than `r` adjacent column pairs were non-collinear.
- **Why Deferred under Baseline Freeze:** Discovered during Post-Migration Cycle 1 `np.matrix` audit (`DEF-011`).
- **Empirical Re-Evaluation & Disposition:** **Resolved in Wave 1 (`#85`):** Replaced `np.matrix(r_mat)` with `np.atleast_2d(np.asarray(r_mat))`, added `if r == 0: return np.zeros((0, dim))` and `counter < r - 1` bounds guards, and handled rectangular row/column indexing safely without `IndexError` (`0.0` golden drift).
- **Impact Risk:** **Low** — hardens legacy helper alongside `np.matrix` removal.

---

## Register Disposition Summary (Post-Migration Cycle 4 — 34 Entries, 0 Active Deferred Items)

All **34 entries (`DEF-001`–`DEF-034`)** are accounted for with **100% Summary Index $\leftrightarrow$ Detailed Entry status parity** and **0 active deferred items remaining**:

- **Resolved in Stage 4 & Verified in Stage 5 (`2` entries):** `DEF-007` (`RUL-01`), `DEF-013` (`RUL-02`, `CA-06`).
- **Fully Resolved in Wave 1 (`SAFE_NOW`; commits `a85e832`/`954a56a`/`f9d675b`, pushed to `origin/main` @ `f9d675b`, `89/89` golden parity, `15` entries):** `DEF-004`, `DEF-005`, `DEF-008`, `DEF-010`, `DEF-011`, `DEF-012`, `DEF-018`, `DEF-023`, `DEF-025`, `DEF-026`, `DEF-027`, `DEF-028`, `DEF-030`, `DEF-032`, `DEF-034`.
- **Split Resolved in Wave 1 / Permanently Closed (`1` entry):** `DEF-019` (Part 2 `IStructure` `TypeError` resolved in Wave 1; Part 1 4-arg `get_slices1..3` closed `CLOSE_WONTFIX`).
- **Fully Resolved across Wave 1 + Wave 3 (`1` entry):** `DEF-024` (Wave 1 Gaps 1, 2, 3b, 4 preserving `E01`–`E05` in `a85e832`; Wave 3 Gap 3a `strict: bool = False` in `e5c7f0d`/`0e51ff0`).
- **Fully Resolved in Wave 3 (`VERSIONED_OPT_IN`; commits `e5c7f0d`/`0e51ff0`/`f248b3c`, pushed to `origin/main` & tagged `v4.0.2-baseline`, `6` entries):** `DEF-001`, `DEF-006`, `DEF-015`, `DEF-022`, `DEF-029`, `DEF-033`.
- **Resolved on `exp/v4.1-algo-upgrades` (commits `d922032`, `cd76ac5`, `36fa8e5`; `294 passed, 5 skipped, 0 failed` pytest + `2,383`-crystal MP-20 & `39,244`-string `cRNN` A/B verified, `4` entries):**
  - `DEF-003` (exact `smith_normal_decomp` `basis == -1` fallback + SNF-first `CycleBasisOptimizer.find_lattice_basis`; unconditional reorder, `is_integral`, and `iter_cycles` remain `KEEP_FROZEN`),
  - `DEF-014` (transitive `math.isclose(1e-9, 1e-12)` `_classify_lattice_type` in `core.py` and `decoding_strategies.py`),
  - `DEF-021` (`check_SLICES(..., graph_rank_check=True)` lattice/cocycle enforcement, completing Wave 1 `to_structures` exceptions),
  - `DEF-031` (`core.py` `matched_bond_indices` diagonal alignment, completing Wave 3 `robust_decode` Stage 2 trigger).
- **Keep Frozen (`KEEP_FROZEN`, `2` entries):** `DEF-002` (default `to_structures()` permanently frozen; opt-in `robust_SLICES2structure()` enhanced in Wave 3), `DEF-009` (`ExpCellFilter` retained as default; ASE `DeprecationWarning` scoped in Wave 1).
- **Closed — Won't Fix (`CLOSE_WONTFIX`, `3` entries):** `DEF-016` (Stage 3 block), `DEF-017` (resolved upstream `2635bcc`), `DEF-020` (Stage 3 block).

**Total Register Entries:** **34** (`DEF-001`–`DEF-034`). **Active Deferred Items Remaining:** **0**. Next sequential ID available: **`DEF-035`**.
