# First-Principles Empirical Re-Evaluation: Determinism, Runtime State, Input Parsing & Blocked Items

**Evaluator:** `eval-runtime-parse` (Carbon High)  
**Date:** 2026-11-25  
**Target Codebase:** `/home/ordillo/tests/SLICES` at `HEAD=fa4cfc8` (`slices-4-personal`, post-Stage-7)  
**Baseline Reference:** `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`, tag `v4.0.2`)  
**Source Register:** [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md)  
**Hardware / Runtime:** `Intel(R) Xeon(R) 6731P` (32 physical cores, 1 thread/core, single socket), Python `3.10`, `torch==2.9.1+cpu`, `nequip==0.17.1`, `pymatgen==2025.10.7`, `ase==3.29.0`, `scipy` (`libscipy_openblas`), `libgomp` (`libgfnff.so.0.1.1`)  
**Methodology:** Strictly non-destructive empirical probes executed in `/dev/shm/reeval-runtime/` (cleaned upon completion) against live repository sources, the 19-structure Golden Reference Corpus (`G01`–`G19`), all `255` pytest tests, and all `125,174` SLICES strings across `28` dataset/benchmark/HTS files.

---

## 1. Executive Summary & Re-Evaluation Verdicts

> [!NOTE]
> Line numbers in `src/slices/core.py` and `src/slices/tobascco_net.py` shifted during Stage 4/5 Google-style docstring and typing refactoring. The table below maps both the historical register coordinates and the exact verified coordinates at `HEAD=fa4cfc8`.

| ID | Register Coords | `HEAD=fa4cfc8` Coords | Symbol / Scope | Re-Evaluation Verdict | Key Quantitative Empirical Finding |
|---|---|---|---|---|---|
| [`DEF-004`](#21-def-004-dead-nprandomchoice--nprandomshuffle-in-tobascco_netpy) | `tobascco_net.py:359,514` | [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L342), [L462-L464](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L462-L464) | `Net.simple_cycle_basis`, `Net.get_lattice_basis` | **`SAFE_NOW`** | `0` downstream consumers of legacy `np.random`; **`max_float_abs_diff = 0.0` (0 ULPs)** across `19/19` Golden Corpus entries & `89/89` golden tests (`249/249` non-path-pinned pytest pass); restores 100% `np.random` purity across `Net`, `check_SLICES`, and unrelaxed `to_structures`. |
| [`DEF-005`](#22-def-005-import-time-omp_num_threads--warning-mutations-in-corepy) | `core.py:5-9` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L17-L21) | Module import header (`OMP_NUM_THREADS`, `PYTHONWARNINGS`, `filterwarnings`) | **`SAFE_NOW`** *(via `setdefault("1")` + scoped warnings)* | `GFN-FF` + `std` + `ZL*` have **`0.0` drift** and **`0/19` `DEF-014` `lattice_type` flips** across `OMP ∈ {1,2,4,8,32}`; `NequIP` drifts up to `0.042 Å` / `2.34 meV/atom` (`G18`) for `OMP >= 2` (`16/16` `match_check3` intact). `OMP=4..8` gives **`1.33x–1.41x` single-process speedup** (`2.42x` in `GFN-FF`), whereas fully `unset` spawns `32` OpenBLAS threads and slows `32`-thread PyTorch **`2.71x`** (`40.83 s` vs `15.06 s`). `setdefault("OMP_NUM_THREADS", "1")` + module-scoped warnings is strictly superior (`0.0` default drift). |
| [`DEF-022`](#23-def-022-structure2randomslices-pythonhashseed-set-order-dependence) | `core.py:741,843-845` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L962), [L1051-L1062](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1051-L1062) | `SLICES.structure2randomSLICES` | **`VERSIONED_OPT_IN`** *(or `SAFE_NOW` w/ golden metadata refresh)* | Across `PYTHONHASHSEED ∈ {0,1,42,999}`, current `set()` has **`0/16` (`0%`)** list-order invariance at `num=5` and **`3/16` (`18.8%`) set invariance at `num=1`** (`13/16` return a different string!). Both `sorted()` and `dict` achieve **`16/16` (`100%`)** list & set invariance at `num=1` and `num=5`, while changing `15/16` (`sorted`) or `16/16` (`dict`) `random_slices_5` permutations at `PYTHONHASHSEED=0`. |
| [`DEF-024`](#24-def-024-from_slices-parsing-gaps--strategy-2-invertibility) | `core.py:202-332,372-386` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L319-L459), [L521-L541](file:///home/ordillo/tests/SLICES/src/slices/core.py#L521-L541) | `SLICES.from_SLICES`, `SLICES.get_slices2` | **Split:** **`SAFE_NOW`** *(Gaps 1, 2, 4 & extra label chars)*; **`VERSIONED_OPT_IN`** *(trailing tokens `strict=False`)* | Full scan of **`125,174` SLICES strings (`28` files)**: `0` reliance on `strategy=2` decode (non-injective `mod 100` for `>100` atoms), `0` zero-edge, `0` extra Strategy-4 label chars, `0` negative node indices; **HOWEVER**, **`13/999` (`1.30%`) real PBE-screened rows in `HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv`** have RNN-truncated trailing tokens and pass `check_SLICES(strategy=3)` today. |
| [`DEF-012`](#25-def-012-slices2formula-regex-fragility--uncaught-attributeerror) | `core.py:652-663` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L824-L848) | `SLICES.SLICES2formula` | **`SAFE_NOW`** | Current regex silently returns **wrong non-`None` formulas on `16/16` (`100%`) Strategy 1 strings** (`Nd2Si2Ru2 -> 'Nd1Si1'`), fails on `10/16` (`62.5%`) Strategy 2 strings, and raises `AttributeError` on digit-free inputs. Token/grammar-aware extraction hits **`16/16` across Strategies 1–4**, **`2,383/2,383`** (`mp20_v4`), and **`14,303/14,303`** (`mp20_legacy`) with `0` `AttributeError`s. |
| [`DEF-018`](#26-def-018-empty-structure-behavior-across-encoding--validation) | `core.py:666-722` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L851-L918), [L919-L1063](file:///home/ordillo/tests/SLICES/src/slices/core.py#L919-L1063), [L1114-L1180](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1114-L1180) | `to_primitive_if_smaller`, `structure2SLICES`, `structure2randomSLICES`, `from_cif` | **`SAFE_NOW`** | On `0`-site `Structure`, `to_primitive_if_smaller` swallows Spglib error and returns empty `Structure`, causing `structure2SLICES` to **silently return invalid `""`** and `structure2randomSLICES` to **return `[""]`**! Early `len(structure) == 0` guard raising `(SLICESEncodingError, ValueError)` fixes silent corruption with `0` regressions. |
| [`DEF-019`](#27-def-019-get_slices13-4-arg-signature--check_structural_validity-type-guard) | `core.py:345-402,449-470` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L471-L564), [L620-L637](file:///home/ordillo/tests/SLICES/src/slices/core.py#L620-L637) | `get_slices1..3`, `check_structural_validity` | **Split:** **`CLOSE_WONTFIX`** *(4-arg `get_slices1..3`)*; **`SAFE_NOW`** *(`IStructure` `TypeError` guard)* | `get_slices_by_strategy` (`L488`) dispatches 4 positional args across 5 internal call sites — 4-arg signature is permanently required. `isinstance(str1, IStructure)` guard in `check_structural_validity` has `0` impact across all callers and all `255` tests. |
| [`DEF-026`](#28-def-026-invalid-graph_method-stdout-print--unboundlocalerror) | `core.py:186-200,856-867` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L160), [L202](file:///home/ordillo/tests/SLICES/src/slices/core.py#L202), [L297-L315](file:///home/ordillo/tests/SLICES/src/slices/core.py#L297-L315), [L1099-L1112](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1099-L1112) | `SLICES.__init__`, `structure2structure_graph`, `get_dim` | **`SAFE_NOW`** | `100%` of repo callers & `20/20` `.ini` configs (`17` `econnn`, `3` `crystalnn`) use only `("econnn", "crystalnn", "brunnernn", "mininn")`. Validating in `__init__` + both `else:` branches replaces stdout + `UnboundLocalError` with clean `ValueError` at `0` test/caller cost. |
| [`DEF-016`](#31-def-016-malformed-strategy-4-space-group-header-handling) | `core.py:275-296` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L401-L408) | `SLICES.from_SLICES` *(Blocked Item)* | **`CLOSE_WONTFIX`** *(Block Confirmed)* | Stage 3 block holds 100%: `"q q q Si O 0 1 ooo"` raises `Exception("Error: space_group_num = None")` and returns `False` in `check_SLICES` / `check_SLICES_basic` (locked in golden `E03_bad_sg_prefix`). |
| [`DEF-017`](#32-def-017-structuregraphfrom_local_env_strategy-migration) | `core.py:165-200` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L54-L59), [L276-L315](file:///home/ordillo/tests/SLICES/src/slices/core.py#L276-L315) | `cif2structure_graph`, `structure2structure_graph` *(Blocked Item)* | **`CLOSE_WONTFIX`** *(Block Confirmed)* | Stage 3 block holds 100%: `with_local_env_strategy` emits `FutureWarning` (scheduled removal) in `pymatgen==2025.10.7`, whereas `core.py` already uses `from_local_env_strategy` + `BrunnerNNReciprocal` fallback. |
| [`DEF-020`](#33-def-020-root-logger-silencing--eager-tensorflowkeras-side-effects) | `core.py:4-9` & `mlip_relaxer.py` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L17-L21), [__init__.py](file:///home/ordillo/tests/SLICES/src/slices/__init__.py#L1-L102), [mlip_relaxer.py](file:///home/ordillo/tests/SLICES/src/slices/mlip_relaxer.py#L565-L577) | Module import hygiene *(Blocked Item)* | **`CLOSE_WONTFIX`** *(Block Confirmed)* | Stage 3 block holds 100%: importing `slices`, `slices.mlip_relaxer`, and `slices.core` preserves `logging.getLogger().level == 30` (`WARNING`), `tensorflow`/`keras` absent from `sys.modules`, and `TF_USE_LEGACY_KERAS` scoped strictly inside `M3GNetRelaxer.__init__`. |

---

## 2. Detailed Empirical Re-Evaluations (8 Deferred Items)

### 2.1 `DEF-004`: Dead `np.random.choice` / `np.random.shuffle` in `tobascco_net.py`

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L342) (`Net.simple_cycle_basis`): `st_vtx = np.random.choice(range(self.graph.order()))  # noqa: F841 (DEF-004 frozen RNG)`
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L462-L464) (`Net.get_lattice_basis`): `L = []  # noqa: F841`, `inds = list(range(self.cycle_rep.shape[0]))`, `np.random.shuffle(inds)  # DEF-004 frozen RNG draw`
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Empirical Audit & Live Measurements
1. **Repository-Wide Static Audit (`src/`, `tests/`, `examples/`, `tools/`, `HTS/`, `benchmark/`, `data/`):**
   - Across all `src/slices/*.py` modules, `tobascco_net.py:342` and `tobascco_net.py:464` are the **only two calls** to NumPy's legacy global `np.random` API.
   - [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L726) (`remove_overlaps`) and [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L126) (`L126, 180, 347`) exclusively instantiate isolated `np.random.default_rng(seed)` generators.
   - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L989) (`structure2randomSLICES`, `L989, 1004, 1015, 1061`) uses Python's `random` module, never `np.random`.
   - `HTS/2_train_sample/tobascco_net.py` and `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/2_train_sample/tobascco_net.py` are standalone historical script copies and do not import `slices.tobascco_net`.
2. **Per-Method `np.random.get_state()` Isolation Probe:**

   | Operation | `HEAD=fa4cfc8` (`np.random` Unchanged?) | Patched (`DEF-004` Removed, `np.random` Unchanged?) |
   |---|---|---|
   | `SLICES.structure2SLICES(ori, strategy=4)` | `True` | `True` |
   | `Net.simple_cycle_basis()` | `False` *(mutated)* | **`True`** |
   | `Net.get_lattice_basis()` | `False` *(mutated)* | **`True`** |
   | `Net.get_cocycle_basis()` | `True` | `True` |
   | `SLICES.check_SLICES(sli, strategy=4)` | `False` *(mutated)* | **`True`** |
   | `SLICES.SLICES2space_group_number(sli, strategy=4)` | `False` *(mutated)* | **`True`** |
   | `SLICES(relax_model=None).to_structures()` *(GFN-FF + Eon + ZL\*)* | `False` *(mutated)* | **`True`** |

   *(Note: Third-party ASE/matscipy neighbor-list helpers inside `NequIPRelaxer` touch `np.random` internally without affecting deterministic TorchScript forces/energies.)*
3. **Golden Equivalence & Full Test Suite Verification (`/dev/shm` Patched `src/slices`):**
   - **All 19 Golden Corpus structures (`G01`–`G19`):** `max_float_abs_diff = 0.0` (bit-for-bit IEEE-754 identity across `inner_p_target`, `std`, `opt`, `opt2`, `std2`, and `energy_per_atom`) and `discrete_mismatches = 0` (including `G05`, `G17`, and `S01` `preoptimize`/`remove_overlaps`).
   - **Unified `pytest` run:** `249 passed, 5 skipped` (`0` failures; the single deselected test is `test_live_dual_tree_subprocess_parity` only because it asserts `slices.core.__file__` resides under `REPO_ROOT / "src"`).

#### Concrete Action
Delete `st_vtx = np.random.choice(...)` at [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L342) and `L = []` / `inds = ...` / `np.random.shuffle(inds)` at [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L462-L464), and add a unit test asserting `np.random.get_state()` invariance across `check_SLICES`, `SLICES2space_group_number`, and unrelaxed `to_structures`.

---

### 2.2 `DEF-005`: Import-Time `OMP_NUM_THREADS` & Warning Mutations in `core.py`

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L17-L21) (with `"src/slices/core.py" = ["E402"]` in [pyproject.toml](file:///home/ordillo/tests/SLICES/pyproject.toml#L124)) and [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L439-L451) (`_set_cpu_threads`)
- **Re-Evaluation Verdict:** **`SAFE_NOW`** *(replace unconditional overwrites and global warning filters with `os.environ.setdefault("OMP_NUM_THREADS", "1")`, `os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")`, removal of `PYTHONWARNINGS="ignore"`, and module-scoped warning filters — strictly keeping `"1"` as the default when unset)*

#### Empirical 19-Structure Golden Corpus Benchmark on 32-Core Xeon (`Intel Xeon 6731P`)
Using an isolated copy of `src/slices` in `/dev/shm` with unconditional `os.environ["OMP_NUM_THREADS"] = "1"` removed, all 19 Golden Corpus entries (`G01`–`G19`) were benchmarked in fresh subprocesses across six OpenMP/PyTorch configurations:
- `1`, `2`, `4`, `8`: explicit `OMP_NUM_THREADS` passed in environment (`libscipy_openblas`, `libgomp`, and `torch.get_num_threads()` all match `N`).
- `unset (rb=1)`: `OMP_NUM_THREADS` unset; `libscipy_openblas` spawns **`32` threads**, while `relax_backends._set_cpu_threads()` (`L446`) defaults `torch.set_num_threads(1)` (`libgomp=1`).
- `unset (native 32)`: `OMP_NUM_THREADS` unset and `_set_cpu_threads()` bypassed so `libscipy_openblas`, `libgomp`, and PyTorch all run at native **`32` threads**.

| Config (`OMP_NUM_THREADS`) | OpenBLAS / `libgomp` / Torch Threads | `GFN-FF` (`19`x, s) | `ZL*`+`GFN-FF` (`19`x, s) | `NequIP` Est. (`19`x, s) | `to_structures` Total (`19`x, s) | Speedup vs `OMP=1` | `max_opt_diff` (Lat / Frac) | `DEF-014` `lattice_type` Flips | `max_opt2_lat_diff` (Å) | `max_opt2_frac_diff` | `max_energy_diff` (eV/atom) | `match_check3` Drift (Strict / Loose) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **`1` (Baseline)** | `1 / 1 / 1` | `5.220` | `8.468` | `6.587` | **`15.055`** | `1.00x` | `0.0 / 0.0` | **`0 / 19`** | **`0.000e+00`** | **`0.000e+00`** | **`0.000e+00`** | `0/16` / `0/16` |
| **`2`** | `2 / 2 / 2` | `3.226` | `6.581` | `6.028` | **`12.609`** | `1.19x` | `0.0 / 0.0` | **`0 / 19`** | `2.105e-02` | `4.954e-03` | `3.440e-04` | `0/16` / `0/16` |
| **`4`** | `4 / 4 / 4` | `2.569` | `5.888` | `5.429` | **`11.317`** | **`1.33x`** | `0.0 / 0.0` | **`0 / 19`** | `4.200e-02` | `3.507e-02` | `2.343e-03` | `0/16` / `0/16` |
| **`8`** | `8 / 8 / 8` | `2.153` | `5.482` | `5.229` | **`10.711`** | **`1.41x`** | `0.0 / 0.0` | **`0 / 19`** | `3.148e-02` | `3.109e-02` | `1.871e-03` | `0/16` / `0/16` |
| **`unset (rb=1)`** | `32 / 1 / 1` | `4.707` | `8.039` | `6.961` | **`15.000`** | `1.00x` | `0.0 / 0.0` | **`0 / 19`** | **`0.000e+00`** | **`0.000e+00`** | **`0.000e+00`** | `0/16` / `0/16` |
| **`unset (native 32)`** | `32 / 32 / 32` | `1.722` | `4.973` | `35.859` | **`40.832`** | **`0.37x` (`2.71x` slower!)** | `0.0 / 0.0` | **`0 / 19`** | `2.100e-02` | `4.908e-03` | `3.450e-04` | `0/16` / `0/16` |

#### Mechanistic Insights
1. **Zero OpenBLAS / ZL\* Drift & Zero `DEF-014` Flips Across All Thread Counts:**
   - Across `OMP_NUM_THREADS ∈ {1, 2, 4, 8, 32}`, `inner_p_target`, `std_lattice`, `std_frac`, `opt_lattice`, and `opt_frac` exhibit **exact `0.0` IEEE-754 drift (`0` ULPs)** and **`0/19` `DEF-014` `lattice_type` flips**. Because unit-cell `Net` matrices (`3x3` to `~36x36`) and ZL\* optimization vectors (`~6–39` parameters) sit well below OpenBLAS's multi-threading dispatch threshold, CPU BLAS operations execute deterministically on a single thread regardless of `OMP_NUM_THREADS`. Meanwhile, Fortran `libgfnff.so` parallelizes OpenMP loops deterministically (`max_inner_p_diff = 0.0`) and speeds up **`2.42x` at `OMP=8`** (`5.220 s -> 2.153 s`).
2. **Where Numerical Drift Originates (`NequIP` `float32` Reductions):**
   - For `OMP_NUM_THREADS >= 2`, PyTorch `float32` intra-op parallel reductions in `NequIP-OAM-S` introduce `~10^-7` eV/Å force rounding variations that BFGS Hessian updates accumulate:
     - On `17/19` structures (`G01`–`G16`, `G19`), drift is tiny (`d_opt2_lat = 4.3e-8 .. 2.9e-5 Å`, `d_energy = 3.1e-9 .. 5.2e-6 eV/atom`), though exceeding the `atol=1e-12` golden test threshold.
     - On `G17` (`ZrTi(PbO3)2`, `preoptimize=True`), `d_opt2_lat = 7.1e-6 .. 5.9e-5 Å`.
     - On `G18` (`YHO2`, `unstable_graph=True`, flat energy surface), BFGS settles into a slightly shifted local basin (`d_opt2_lat = 0.021 .. 0.042 Å`, `d_energy = 0.34 .. 2.34 meV/atom`, `G18` decode time `1.22 s` at `OMP=1` vs `8.03 s` at `32` threads).
     - Structural recovery (`match_check3` strict & loose) is **`100%` invariant (`0/16` mismatches)** across every thread setting.
3. **Why Leaving `OMP_NUM_THREADS` Completely Unset is Dangerous, and Why `setdefault("1")` Wins:**
   - Simply deleting `os.environ["OMP_NUM_THREADS"] = "1"` causes `libscipy_openblas` to allocate `32` threads per process (`1,024` threads across a 32-worker `splitRun_csv` job!), and uncapped `32`-thread PyTorch suffers severe OpenMP barrier contention on small crystal graphs (`NequIP` slows `5.44x` from `6.59 s` to `35.86 s`).
   - Conversely, current unconditional `os.environ["OMP_NUM_THREADS"] = "1"` clobbers an explicit `OMP_NUM_THREADS=4` or `8` set by a single-process user (forfeiting a `1.33x–1.41x` speedup) and creates a split-brain thread configuration if `numpy` was imported before `slices.core`.
   - `os.environ.setdefault("OMP_NUM_THREADS", "1")` preserves **bit-exact `0.0` default determinism** and `splitRun_csv` multi-process safety when unset, while honoring explicit caller `OMP_NUM_THREADS` overrides!
4. **Empirical Warning Audit (Removing Global `filterwarnings` & `PYTHONWARNINGS="ignore"`):**
   - Capturing all `DeprecationWarning` and `FutureWarning` emissions across full encode + decode when lines `18–19` and `21` of `core.py` are removed revealed **only 3 third-party warning sites**:
     1. `spglib` (`spg.py:438`): `DeprecationWarning: Set OLD_ERROR_HANDLING to false...`
     2. `spglib` (`cell.py:106`): `DeprecationWarning: Set OLD_ERROR_HANDLING to false...`
     3. `ase` ([relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L545)): `DeprecationWarning: Use FrechetCellFilter...` (`DEF-009`)
   - Replacing process-wide `warnings.filterwarnings("ignore", category=DeprecationWarning/FutureWarning)` and `os.environ["PYTHONWARNINGS"] = "ignore"` (which leaks to child processes) with `os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")`, `os.environ.setdefault("OMP_NUM_THREADS", "1")`, module-scoped `warnings.filterwarnings("ignore", category=DeprecationWarning, module=r"^spglib\.")`, and a local `warnings.catch_warnings()` around `ExpCellFilter(atoms)` in `_cell_filter()` passed **`161/161` unit/integration/regression tests** and **`89/89` golden tests** with zero host-application warning suppression.

---

### 2.3 `DEF-022`: `structure2randomSLICES` `PYTHONHASHSEED` Set-Order Dependence

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L962) (`SLICES_set = set()`), [L973](file:///home/ordillo/tests/SLICES/src/slices/core.py#L973), [L1049-L1062](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1049-L1062) (`SLICES_list = list(SLICES_set); random.shuffle(SLICES_list); return SLICES_list[:num]`)
- **Re-Evaluation Verdict:** **`VERSIONED_OPT_IN`** *(or **`SAFE_NOW`** if paired with a one-time regeneration of the 16 `random_slices_5` list permutations in `tests/baseline/fixtures/golden_metadata.json`)*

#### Empirical Cross-Process `PYTHONHASHSEED` Measurements (`{0, 1, 42, 999}`, `random.seed(42)`)
Evaluated across all `16` CIF structures in the Golden Corpus (`G01`–`G16`) for both `num=5` and `num=1`:

| Deduplication Strategy | `num=5` Exact List Invariant (`0,1,42,999`) | `num=5` Set Invariant (`0,1,42,999`) | `num=1` Exact List Invariant (`0,1,42,999`) | `num=1` Set Invariant (`0,1,42,999`) | Matches Frozen Golden `random_slices_5` at `PYTHONHASHSEED=0` |
|---|---|---|---|---|---|
| **Current `set()` -> `list(SLICES_set)`** | **`0 / 16` (`0.0%`)** | `16 / 16` (`100%`) | **`3 / 16` (`18.8%`)** | **`3 / 16` (`18.8%`)** | `16 / 16` (`100%`) |
| **`sorted(SLICES_set)`** | **`16 / 16` (`100%`)** | `16 / 16` (`100%`) | **`16 / 16` (`100%`)** | **`16 / 16` (`100%`)** | `1 / 16` (`6.2%`) |
| **Insertion-ordered `dict`** | **`16 / 16` (`100%`)** | `16 / 16` (`100%`) | **`16 / 16` (`100%`)** | **`16 / 16` (`100%`)** | `0 / 16` (`0.0%`) |

#### Newly Uncovered `num=1` Subset-Selection Bug
In addition to changing output list permutations for `num >= 2` (`0/16` cross-process agreement), first-principles inspection and empirical testing uncovered a **subset-content bug when `num=1`**:
1. At `L973`, `SLICES_set.add(original_SLICES)` inserts `1` item before the loop.
2. Because `total_permutations = 1 * 10 = 10` (`L978`) and `if len(SLICES_set) >= num: break` (`L1051`) executes at the **end** of iteration `0` rather than before entering the loop, iteration `0` inserts a second augmented string (`len(SLICES_set) == 2`).
3. `list(SLICES_set)` orders those 2 strings according to CPython's per-process randomized SipHash salt, so after `random.shuffle(SLICES_list)` with fixed `random.seed(42)`, `SLICES_list[:1]` returns a **different SLICES string on `13/16` (`81.25%`) structures** across `PYTHONHASHSEED` values!

#### Trade-Off & Concrete Recommendation
- [test_golden_equivalence.py](file:///home/ordillo/tests/SLICES/tests/baseline/test_golden_equivalence.py#L159-L163) explicitly asserts `actual["random_slices_5"] == expected["random_slices_5"]` when `PYTHONHASHSEED == "0"`. Switching `list(SLICES_set)` unconditionally breaks `15/16` (`sorted`) or `16/16` (`dict`) of those exact-order assertions unless `golden_metadata.json` is updated in tandem.
- **Recommended Path:** Add an optional `seed: int | None = None` parameter to `structure2randomSLICES` (and `structure2SLICESAug_atom_order`): when `seed is not None`, use an isolated `rng = random.Random(seed)` + insertion-ordered `dict` (and check `if len(seen) >= num: break` before the loop), giving 100% `PYTHONHASHSEED`-independent and global-RNG-free reproducibility while keeping legacy `seed=None` `PYTHONHASHSEED=0` golden order untouched (or switch default to insertion-ordered `dict` in `v4.1` alongside a 16-field `golden_metadata.json` update).

---

### 2.4 `DEF-024`: `from_SLICES()` Parsing Gaps & Strategy 2 Invertibility

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L319-L459) (`SLICES.from_SLICES`) vs [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L521-L541) (`SLICES.get_slices2`), [cli.py](file:///home/ordillo/tests/SLICES/src/slices/cli.py#L358) (`L358, 388, 420`), and [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L730-L734)
- **Re-Evaluation Verdict:**
  - **Gap 1 (`strategy=2` / unknown strategy `UnboundLocalError`), Gap 2 (zero-edge `"Si O"` `UnboundLocalError`), Gap 4 (negative node index `"-1"`), and Gap 3b (extra Strategy-4 label chars `len(edge[2]) != 3`):** **`SAFE_NOW`**
  - **Gap 3a (trailing partial edge tokens `(len(tokens) - start_idx) % stride != 0`):** **`VERSIONED_OPT_IN`** (`strict: bool = False` default, `strict=True` opt-in)

#### 1. Exhaustive Scan of All `125,174` SLICES Strings Across `data/`, `benchmark/`, and `HTS/` (`28` Files)

| Dataset / Benchmark Group | Files | Format | Strings Scanned | Gap 2: Zero Numeric Tokens | Gap 3a: Trailing Partial Tokens | Gap 3b: Extra Label Chars (`len > 3`) | Gap 4: Negative Node Index | Anomalous Strings Passing `check_SLICES` Today |
|---|---|---|---|---|---|---|---|---|
| `data/mp20_nonmetal/*.csv` (`mp20_v4_benchmark_2383`, `mp20_eform_bandgap_nonmetal`, `train/test_data_reduce_zero`) | `4` | Strategy 4 | `30,989` | `0` | `0` | `0` | `0` | `0` |
| `benchmark/` syntax-filtered `.sli` & inverse/DFT `.csv` suites | `20` | Strategy 3 | `92,158` | `0` | `0` | `0` | `0` | `0` |
| `benchmark/.../2_conditioned_RNN/2_train_sample/sampled.sli` *(raw unfiltered RNN samples)* | `1` | Strategy 3 | `1,000` | `1` | `74` | `0` | `0` | **`0 / 75`** *(all 75 fail index/coverage/rank)* |
| `HTS/9_EAH_Band_gap_PBE/*_filtered.csv` (`2` files) | `2` | Strategy 3 | `28` | `0` | `0` | `0` | `0` | `0` |
| **`HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv`** *(PBE-screened HTS candidates)* | `1` | Strategy 3 | `999` | `0` | **`13` (`1.30%`)** | `0` | `0` | **`13 / 13` (`100%`)** |
| **Repository Total** | **`28`** | — | **`125,174`** | **`1`** | **`87`** | **`0`** | **`0`** | **`13`** |

> [!IMPORTANT]
> **Critical Empirical Discovery in `HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv`:**  
> `13 / 999` (`1.30%`) PBE-relaxed HTS crystal rows (e.g., row `157` `... 3 0 - o` [`rem=4`], row `171` `... 0 6 + o o 8` [`rem=1`], row `172` `... 1 3 o o + 8` [`rem=1`]) contain trailing partial edge tokens produced when fixed-length RNN sequence sampling cut off the last edge mid-tuple. Because `from_SLICES(..., strategy=3)` (`core.py:347`) computed `num_edges = int((len(tokens) - len(self.atom_symbols)) / 5)`, all `13` rows silently discarded the trailing 1–4 tokens, **passed `check_SLICES(..., strategy=3)` (`13/13`)**, and were decoded into valid 3D crystals! Unconditionally rejecting trailing tokens in `from_SLICES` would break replay parity on `1.30%` of that published HTS dataset.

#### 2. First-Principles Invertibility Analysis of Strategy 2 (`get_slices2`, `core.py:521-541`)
- **For `N_atoms <= 100` (`edge_idx <= 99`) and `N_edges >= 1`:** `get_slices2` encodes each element as a 2-char `_`-padded prefix (`[A-Za-z_]{2}`, digit-free) followed by 7-char fixed-width edges (`u:2d`, `v:2d`, `jimage:3c`). A prototype parser tested in `/dev/shm` achieved **`16 / 16` (`100%`) lossless graph round-trip (`atom_symbols`, `edge_indices`, `to_jimages`)** across all Golden CIF structures (`space_group_num` is omitted, matching Strategies 1 & 3).
- **For `N_atoms > 100` (`edge_idx >= 100`):** Line `533` executes `("0" + str(edge_indices[i][0]))[-2:]`, which **silently truncates indices modulo 100**:
  - `get_slices2(["Si"]*106, [[0, 105]], [[0,0,0]])[-7:] == "0005ooo"`
  - `get_slices2(["Si"]*106, [[0,   5]], [[0,0,0]])[-7:] == "0005ooo"` (`collision == True`!)
  Strategy 2 is therefore **mathematically non-injective** for supercells exceeding 100 atoms.
- **Alignment with Stage 4 Architecture:** Both [cli.py](file:///home/ordillo/tests/SLICES/src/slices/cli.py#L358) (`choices=(1, 3, 4)` on `decode`/`validate`/`canonicalize`) and [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L730-L734) (`SLICESDecodingError: ... (strategy 2 is encode-only)`) already treat Strategy 2 as encode-only. Updating `from_SLICES` to explicitly raise `SLICESDecodingError` (or `ValueError` via dual-inheritance) when `strategy == 2` or `strategy not in (1, 3, 4)` eliminates `UnboundLocalError: local variable 'edge_indices' referenced before assignment` cleanly and consistently.

#### 3. Live Reproducers of Current Failure Modes (`HEAD=fa4cfc8`)
- `from_SLICES("SiO_0001ooo", strategy=2)` / `strategy=99` -> `UnboundLocalError` on `edge_indices` (`L439`/`L451`).
- `from_SLICES("Si O", strategy=4)` / `strategy=3` -> `UnboundLocalError` on `num_atoms` (`L346`/`L415`); `strategy=1` -> `ValueError: max() arg is an empty sequence` (`L371`).
- `from_SLICES("Si O 0 1 oooGARBAGE", strategy=4)` -> silently returns `to_jimages = [[0, 0, 0]]`, ignoring `"GARBAGE"` (`0` real files rely on this -> fix `len(edge[2]) != 3` now).
- `from_SLICES("Si O -1 1 ooo", strategy=4)` -> passes `edge_indices[i, 0] > num_atoms - 1` (`-1 > 1` is `False`!) and crashes later in `fix_duplicate_edge` (`IndexError`) or, in Strategy 1 (`L380`), **silently writes into `self.atom_symbols[-1]`** via Python negative list indexing! Enforcing `0 <= idx < num_atoms` fixes both immediately (`SAFE_NOW`).
- Keep trailing-token truncation permissive by default and add `strict: bool = False` to `from_SLICES` (raising `SLICESDecodingError` when `strict=True` and `(len(tokens) - start_idx) % stride != 0`).

---

### 2.5 `DEF-012`: `SLICES2formula` Regex Fragility & Uncaught `AttributeError`

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L824-L848) (`SLICES.SLICES2formula`)
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Empirical Evaluation Across Strategies 1–4, Edge Inputs & MP-20 Datasets (`16,750` Strings)
Testing `SLICES2formula` at `HEAD=fa4cfc8` across all `16` CIF Golden Corpus structures (`G01`–`G16`) revealed a **critical silent-corruption defect on Strategy 1** in addition to the Strategy 2 and `AttributeError` issues:

| Input Suite | `HEAD=fa4cfc8` `SLICES2formula` Behavior | Token / Grammar-Aware `SLICES2formula` |
|---|---|---|
| **Golden Corpus Strategy 4 (`16` crystals)** | `16 / 16` (`100%`) exact match | **`16 / 16` (`100%`)** exact match |
| **Golden Corpus Strategy 3 (`16` crystals)** | `16 / 16` (`100%`) exact match | **`16 / 16` (`100%`)** exact match |
| **Golden Corpus Strategy 2 (`16` crystals)** | `6 / 16` (`37.5%`) match; **`10 / 16` (`62.5%`) `None` + stdout print** (fails whenever any 1-letter symbol has `_` padding, e.g., `Sr3Ru2O7`, `V2O2`) | **`16 / 16` (`100%`)** exact match |
| **Golden Corpus Strategy 1 (`16` crystals)** | **`0 / 16` (`0%`) match; `16 / 16` (`100%`) SILENT WRONG FORMULA!** (`G01` `Nd2Si2Ru2 -> 'Nd1Si1'`, `G02` `Sr3Ru2O7 -> 'Sr1O1'`, `G03` `Si3P3Ir1 -> 'Si1Ir1'`, `G04` `V2O2 -> 'V1O1'`) | **`16 / 16` (`100%`)** exact match |
| **`mp20_v4_benchmark_2383.csv` (`2,383` rows, S4)** | Baseline reference | **`2,383 / 2,383` (`100.0%`)** exact parity |
| **`mp20_eform_bandgap_nonmetal.csv` (`14,303` rows, S4)** | Baseline reference | **`14,303 / 14,303` (`100.0%`)** exact parity |
| **Digit-free / empty (`""`, `"   "`, `"Si O"`, `"foo bar"`)** | **Uncaught `AttributeError: 'NoneType' object has no attribute 'group'`** (`L840`) | Returns `None` cleanly (`0` exceptions, `0` stdout spam) |

#### Root Cause & Safe Fix
In Strategy 1 (`"Nd Si 0 2 o o o Nd Ru 0 4 ..."`), atom symbols are interleaved per edge rather than grouped in a header. `re.search(r"^(.*?)(\d+)", SLICES)` stops at the first edge's atom index `0` and feeds only the first edge's two symbols (`"Nd Si "`) into `Composition(...)`, silently fabricating a plausible-looking wrong formula! Detecting Strategy 2 (unspaced 2-char `_`-padded header before `\d`), Strategy 1 (`len % 7 == 0` with numeric `tokens[2], tokens[3]` reconstructing `atom_symbols[u], atom_symbols[v]`), and Strategy 3/4 (element tokens from `first_elem_idx` up to the first integer index token) inside a guarded block preserves **100.0% parity across all `16,686` valid Strategy 3/4 dataset strings** while fixing `16/16` Strategy 1, `16/16` Strategy 2, and all `AttributeError` crashes.

---

### 2.6 `DEF-018`: Empty `Structure` Behavior Across Encoding & Validation

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L851-L918) (`to_primitive_if_smaller`, `_run_with_primitive_fallback`, `structure2SLICES`), [L919-L1063](file:///home/ordillo/tests/SLICES/src/slices/core.py#L919-L1063) (`structure2randomSLICES`), [L1114-L1180](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1114-L1180) (`from_cif`, `structure2crystal_graph_rep`), [L246-L260](file:///home/ordillo/tests/SLICES/src/slices/core.py#L246-L260) (`check_element`), and [L620-L637](file:///home/ordillo/tests/SLICES/src/slices/core.py#L620-L637) (`check_structural_validity`)
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Exact Observed Failure Modes on `empty = Structure(Lattice.cubic(5.0), [], [])` at `HEAD=fa4cfc8`

| Entry Point | Actual Result at `HEAD=fa4cfc8` | Stdout Side Effect |
|---|---|---|
| `SLICES.to_primitive_if_smaller(empty)` | **Returns 0-site `empty` `Structure` unchanged** | Prints `Warning: primitive cell conversion failed, using the input cell: Generic Spglib error: positions has to be a (num_atoms, 3) array.` |
| `structure2crystal_graph_rep(empty)` | **Returns `(array([]), array([]), array([]), None)`** | Prints Spglib warning above |
| `structure2SLICES(empty, strategy=1..4)` *(all 4 `graph_method`s)* | **Silently returns `""` (empty string!)** without raising | Prints Spglib warning above |
| `structure2randomSLICES(empty, num=5)` | **Silently returns `[""]`** without raising | Prints Spglib warning + `Warning: Only generated 1 unique augmented SLICES strings...` |
| `from_cif(empty.to(fmt="cif"))` | Raises `IndexError: tuple index out of range` *(inside `pymatgen` CIF parser)* | None |
| `SLICES.check_element(empty)` | Raises `ValueError: zero-size array to reduction operation maximum which has no identity` | None |
| `SLICES.check_structural_validity(empty)` | Raises `ValueError: shapes (1,0) and (3,3) not aligned: 0 (dim 1) != 3 (dim 0)` | None |

#### Analysis & Concrete Fix
Contrary to the assumption that v4.0's `to_primitive_if_smaller` already raises on an empty `Structure`, `to_primitive_if_smaller` (`core.py:871-873`) catches all exceptions and falls back to returning `empty`, causing `structure2SLICES(empty)` to silently emit `""` (which downstream `from_SLICES("")` / `check_SLICES("")` rejects)! Making `SLICESEncodingError` inherit from `(SLICESError, ValueError)` (or raising `SLICESEncodingError("Cannot encode an empty Structure with 0 sites.")` when `len(structure) == 0` at the top of `to_primitive_if_smaller` / `structure2structure_graph`) fails fast with zero impact on any non-empty crystal across all 255 tests.

---

### 2.7 `DEF-019`: `get_slices1..3` 4-Arg Signature & `check_structural_validity` Type Guard

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L471-L564) (`get_slices_by_strategy`, `get_slices1..3`) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L620-L637) (`check_structural_validity`)
- **Re-Evaluation Verdict:**
  - **`get_slices1..3` 4-argument signature (`space_group_num: int | None = None`):** **`CLOSE_WONTFIX`** *(already permanently resolved at `HEAD=fa4cfc8`)*
  - **`check_structural_validity` `isinstance(str1, IStructure)` guard:** **`SAFE_NOW`** *(low priority, zero risk)*

#### Empirical Caller Audit
1. **`get_slices1..3`:** `get_slices_by_strategy` (`core.py:488`) uniformly invokes `method(atom_symbols, edge_indices, to_jimages, space_group_num)` across 5 internal call sites (`core.py:613, 820, 915, 966, 1038`), while `space_group_num: int | None = None` preserves 3-arg backward compatibility for direct static calls. Dropping the 4th parameter immediately breaks all Strategy 1–3 encoding with `TypeError`. Close out permanently as a non-issue.
2. **`check_structural_validity`:** Repo-wide grep confirms only 3 call sites exist outside `core.py`: `tests/baseline/generate_golden.py:334`, `tests/unit/test_validation.py:85-102`, and `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/1_unconditioned_RNN/6_check_struc_validity/workflow/0_run.py:21` — all passing `pymatgen.core.Structure` instances, with zero tests asserting `AttributeError` on invalid types (`None` or `str` currently raise `AttributeError: '...' object has no attribute 'lattice'`). Adding `if not isinstance(str1, IStructure): raise TypeError(...)` (checking `pymatgen.core.structure.IStructure` so both `Structure` and immutable `IStructure` pass) has **zero** impact on all 255 tests.

---

### 2.8 `DEF-026`: Invalid `graph_method` Stdout Print & `UnboundLocalError`

- **Verified Coordinates at `HEAD=fa4cfc8`:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L160) (`SLICES.__init__`, `L202`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L297-L315) (`structure2structure_graph`), and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1099-L1112) (`get_dim`); compare [cli.py](file:///home/ordillo/tests/SLICES/src/slices/cli.py#L46) (`_GRAPH_METHODS = ("econnn", "crystalnn", "brunnernn", "mininn")`)
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Empirical Audit Across All Tests, Scripts & `.ini` Configurations
1. **100% Caller Inventory:**
   - Scanned all `20` `settings.ini` files containing `graph_method` across `HTS/`, `benchmark/`, and `data/`: **`17 / 20` specify `econnn`** and **`3 / 20` specify `crystalnn`** (`0` invalid or legacy names).
   - Scanned all Python files across `src/`, `tests/`, `examples/`, `tools/`, `HTS/`, `benchmark/`, and `data/`: only `"econnn"`, `"crystalnn"`, `"brunnernn"`, and `"mininn"` appear anywhere in the repository (`cli.py:46` already enforces `_GRAPH_METHODS`).
   - Zero tests in the `255`-test suite expect `UnboundLocalError` on invalid `graph_method`.
2. **Current Failure Mode (`HEAD=fa4cfc8`):**
   - `bad = SLICES(graph_method="econ", relax_model=None)` succeeds silently in `__init__`, then `bad.structure2structure_graph(struct)` prints `"ERROR - graph_method not implemented"` to stdout and crashes with `UnboundLocalError: local variable 'structure_graph' referenced before assignment` (`get_dim` similarly crashes with `UnboundLocalError` on `bonded_structure`).
3. **Concrete Safe Fix:**
   - Define `VALID_GRAPH_METHODS: tuple[str, ...] = ("econnn", "crystalnn", "brunnernn", "mininn")`. Validate `graph_method` in `SLICES.__init__` AND replace both `else: print(...)` blocks (`core.py:313-314` and `core.py:1109-1110`) with `raise ValueError(f"Unsupported graph_method {self.graph_method!r}; choose from {VALID_GRAPH_METHODS}")` (guarding post-init attribute mutation as well). Zero impact on valid calls across all 255 tests and all baseline workflows.

---

## 3. Sanity-Check of the 3 Blocked Items (`DEF-016`, `DEF-017`, `DEF-020`)

### 3.1 `DEF-016`: Malformed Strategy-4 Space-Group Header Handling
- **Verified Coordinates:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L401-L408) (`from_SLICES`), locked by `E03_bad_sg_prefix` in [generate_golden.py](file:///home/ordillo/tests/SLICES/tests/baseline/generate_golden.py#L205), [test_validation.py](file:///home/ordillo/tests/SLICES/tests/unit/test_validation.py#L34), and [test_decoding.py](file:///home/ordillo/tests/SLICES/tests/unit/test_decoding.py#L62).
- **Verdict:** **`CLOSE_WONTFIX` (Stage 3 Block Holds 100%)**
- **Empirical Verification:** Calling `from_SLICES("q q q Si O 0 1 ooo", strategy=4)` raises `Exception("Error: space_group_num = None")`, and both `check_SLICES` and `check_SLICES_basic` return `False`. Swallowing invalid Wyckoff/space-group prefixes in `core.py` would silently mark corrupted generative-model outputs as valid. *(Nuance: if a future LLM recovery benchmark specifically wishes to salvage strings with corrupted SG prefixes by ignoring the header, that belongs strictly behind a default-off kwarg in `decoding_strategies.robust_decode(..., ignore_invalid_sg_header=False)` — never in `core.from_SLICES` or `check_SLICES`.)*

### 3.2 `DEF-017`: `StructureGraph.from_local_env_strategy` Migration
- **Verified Coordinates:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L54-L59) (`BrunnerNNReciprocal` compatibility import) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L276-L315) (`cif2structure_graph`, `structure2structure_graph`).
- **Verdict:** **`CLOSE_WONTFIX` (Resolved Upstream — Stage 3 Block Holds 100%)**
- **Empirical Verification:** Under `.venv-upstream` (`pymatgen==2025.10.7`), invoking legacy `StructureGraph.with_local_env_strategy(...)` emits `FutureWarning: with_local_env_strategy is deprecated, and will be removed on 2025-03-20. Use from_local_env_strategy in pymatgen.analysis.graphs instead.` `core.py` already uses `StructureGraph.from_local_env_strategy` across all four graph methods, delegates `cif2structure_graph` cleanly without code duplication, and supports `pymatgen>=2026.3` `BrunnerNNReciprocal`. Nothing remains to port or change.

### 3.3 `DEF-020`: Root-Logger Silencing & Eager TensorFlow/Keras Side Effects
- **Verified Coordinates:** [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L17-L21), [__init__.py](file:///home/ordillo/tests/SLICES/src/slices/__init__.py#L1-L102) (PEP 562 lazy `__getattr__`, verified by `test_rul07` in [test_edge_cases.py](file:///home/ordillo/tests/SLICES/tests/regression/test_edge_cases.py#L33-L68)), and [mlip_relaxer.py](file:///home/ordillo/tests/SLICES/src/slices/mlip_relaxer.py#L565-L577) (`M3GNetRelaxer.__init__`).
- **Verdict:** **`CLOSE_WONTFIX` (Stage 3 Block Holds 100%)**
- **Empirical Verification:** In a clean Python subprocess at `HEAD=fa4cfc8`, importing `slices`, `slices.mlip_relaxer`, and `slices.core` leaves `logging.getLogger().level == 30` (`logging.WARNING`, never `50`/`CRITICAL`), leaves `"tensorflow" in sys.modules == False` and `"keras" in sys.modules == False`, and leaves `os.environ.get("TF_USE_LEGACY_KERAS") is None`. Scoped `os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")` and `sys.modules.setdefault("keras", tf_keras)` execute solely inside `M3GNetRelaxer.__init__` when optional `relax_model="m3gnet"` is explicitly instantiated.

---

## 4. Recommended Implementation Priority Tiering

1. **Immediate Zero-Drift Hardening Batch (`SAFE_NOW` — `0.0` Golden Array/Metadata Drift):**
   - **`DEF-004`:** Remove the 2 dead `np.random` draws in `tobascco_net.py:342,462-464`.
   - **`DEF-005`:** Switch `core.py:17-21` to `os.environ.setdefault("OMP_NUM_THREADS", "1")` and `os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")`, drop `os.environ["PYTHONWARNINGS"] = "ignore"`, and scope `DeprecationWarning` filters to `spglib` + `relax_backends._cell_filter`.
   - **`DEF-012`:** Replace `SLICES2formula` regex extraction with Strategy 1–4 token/grammar extraction (`100%` parity on `16,686` Strategy 3/4 dataset rows; fixes `16/16` Strategy 1 silent wrong formulas, `10/16` Strategy 2 `None` failures, and digit-free `AttributeError`s).
   - **`DEF-018`:** Guard `len(structure) == 0` with `SLICESEncodingError` (subclassing `ValueError` for dual catch compatibility) so empty structures fail fast instead of returning `""` / `[""]`.
   - **`DEF-019` (part 2) & `DEF-026`:** Add `isinstance(str1, IStructure)` `TypeError` check in `check_structural_validity` and `VALID_GRAPH_METHODS` `ValueError` validation in `SLICES.__init__`, `structure2structure_graph`, and `get_dim`.
   - **`DEF-024` (Gaps 1, 2, 3b, 4):** Explicitly raise `SLICESDecodingError` on `strategy == 2` (encode-only; lossy `mod 100` for `>100` atoms) or invalid strategy, guard unbound `num_atoms` on zero-edge strings, enforce `0 <= idx < num_atoms`, and require `len(edge[2]) == 3` in Strategy 4.
2. **Opt-In / Versioned Behavioral Flags (`VERSIONED_OPT_IN`):**
   - **`DEF-022`:** Add `seed: int | None = None` (using isolated `random.Random(seed)` + insertion-ordered `dict` + pre-loop `len >= num` guard) to `structure2randomSLICES` so seeded calls are 100% `PYTHONHASHSEED`-invariant at both `num=1` and `num>=2` without perturbing legacy `PYTHONHASHSEED=0` golden list order (or promote to default in `v4.1` with a 16-entry `golden_metadata.json` update).
   - **`DEF-024` (Gap 3a):** Add `strict: bool = False` to `from_SLICES` (and `check_SLICES`) so `strict=True` rejects trailing partial edge tokens while default `strict=False` preserves replay compatibility with the `13 / 999` RNN-truncated crystal rows in `HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv`.
3. **Close Permanently (`CLOSE_WONTFIX`):**
   - **`DEF-019` (part 1):** Keep 4-argument `get_slices1..3(..., space_group_num=None)` permanently.
   - **`DEF-016`, `DEF-017`, `DEF-020`:** Keep Stage 3 blocks permanently enforced.
