# Deferred Core / Algorithm Register

**Project:** SLICES v4.0.2 Migration (`slices-4-personal`)  
**Governing Policy:** Strict Math / Algorithm Freeze Boundary ([PLAN.md Section 4](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L140-L166))  
**Baseline Reference:** `/home/ordillo/tests/SLICES-upstream-baseline` (`upstream/main` @ `94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`)  
**Last Updated:** 2026-11-25 07:58 JST (Stage 5 Gate Verified at `HEAD=8d9314b` — **27 verified entries**: 2 Resolved in Stage 4 & Verified in Stage 5 [`DEF-007`, `DEF-013`], 3 Blocked [`DEF-016`, `DEF-017`, `DEF-020`], 22 Frozen — Deferred [Baseline Preserved])

---

## Purpose & Governance Rules

During Stages 1–7 of this migration, all core mathematical, crystallographic, graph-theoretic, topological, GFN-FF target-construction, ZL* L-BFGS-B optimization, and default NequIP relaxation code paths are **strictly frozen** to guarantee exact / numerically invariant (`atol=1e-12` on CPU) equivalence against upstream SLICES v4.0.2 (`94ef8e0`).

Every genuine defect, numerical quirk, global-state side effect, or candidate algorithmic improvement discovered in either upstream `v4.0.2` or `backup/v3-personal` (`301c75f`) that touches a frozen path **must not be silently modified during the migration**. Instead, it is formally registered here with verified source coordinates, behavioral analysis, deferral rationale, post-baseline evaluation plan, and risk rating so it can be benchmarked and resolved in a dedicated post-migration scientific experiment cycle.

### Schema Definition

| Field | Allowed Values / Format |
|---|---|
| **ID** | Sequential immutable identifier (`DEF-001`, `DEF-002`, ...) |
| **Source / Location** | Branch/ref, file path, exact verified line numbers, symbol name(s), and relevant commit SHA(s) |
| **Category** | One or more of: `Math`, `Graph`, `Optimization`, `Relaxation`, `Runtime`, `Compatibility` |
| **Status** | `Frozen — Deferred (Baseline Preserved)`, `Frozen — Deferred (Baseline Preserved; RUL-03)`, `Resolved in Stage 4 (commit 49237f6; verified in Stage 5)`, `Resolved Upstream — Do Not Regress`, or `Blocked — Do Not Port` |
| **Provenance** | Stage/slice and source tag (`Stage 1 Seed`, `Stage 2A / FC-*`, `Stage 2B / DEF-UP-*`, `Stage 2C / DEF-BC-*`, `Stage 3 / RUL-*`) |
| **Observed Behavior** | Factual description of current code behavior verified from source |
| **Why Deferred under Baseline Freeze** | Concrete explanation of how changing it breaks or risks upstream v4.0.2 parity |
| **Proposed Post-Baseline Investigation / Fix** | Controlled ablation/benchmark experiment and concrete remediation proposal |
| **Impact Risk** | `High` / `Medium` / `Low` — expected behavioral divergence on reconstruction rate, energies, or caller parity if changed |

---

## Summary Index

| ID | Category | Source / Symbol | Short Description | Provenance | Impact Risk | Status |
|---|---|---|---|---|---|---|
| [`DEF-001`](#def-001) | `Math`, `Optimization` | `src/slices/core.py:1293-1294,1312-1313` (`get_uncovered_pair_lj`, `get_covered_pair_lj`) | Heteronuclear LJ mixing averages `atom_types[i[0]]` with itself instead of `i[0]` and `i[1]` | Stage 1 Seed | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-002`](#def-002) | `Optimization`, `Relaxation` | `backup/v3-personal:src/slices/core.py:2459-2566` (`to_structures`) | Auto-injection of `MultiStartOptimizer`, `AdaptiveConvergence`, and `ProgressiveRelaxer` (overriding `fmax=0.2` with `0.1`) into default decoding | Stage 1 Seed; Stage 2A (`FC-04`, `FC-05`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-003`](#def-003) | `Graph`, `Math` | `backup/v3-personal:src/slices/tobascco_net.py:500-704,985-1006` (`iter_cycles`, `get_lattice_basis`, `is_integral`) | Personal `Net` algorithm changes (`CycleBasisOptimizer` + `LatticeBasisError`, `is_integral` float tolerance, BFS `iter_cycles`) | Stage 1 Seed; Stage 2A (`FC-01`, `FC-02`, `FC-03`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-004`](#def-004) | `Graph`, `Runtime` | `src/slices/tobascco_net.py:359,514` (`simple_cycle_basis`, `get_lattice_basis`) | Dead `np.random.choice` / `np.random.shuffle` calls mutate global NumPy RNG state without affecting graph results | Stage 1 Seed; Stage 3 (`RUL-03`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved; RUL-03) |
| [`DEF-005`](#def-005) | `Runtime`, `Compatibility` | `src/slices/core.py:5-9` (module import header) | Import-time process-global mutations of `OMP_NUM_THREADS="1"`, `PYTHONWARNINGS="ignore"`, `TF_CPP_MIN_LOG_LEVEL="3"`, and `warnings` filters | Stage 1 Seed; Stage 3 (`RUL-03`, `CA-08`) | **Medium** | Frozen — Deferred (Baseline Preserved; RUL-03) |
| [`DEF-006`](#def-006) | `Compatibility`, `Math` | `src/slices/core.py:138-151` (`check_element`) vs `src/slices/gfnff_helper.py:11-15` | `check_element` hard-rejects `Z >= 87` while v4.0.2 bundled GFN-FF supports `Z = 87..103` | Stage 1 Seed | **Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-007`](#def-007) | `Runtime`, `Compatibility` | `src/slices/core.py:60` (`function_timeout` -> `signal_handler`) | Undefined `TimeoutException` (`F821`, deleted in `119afaf`) causes `NameError` when any timeout triggers | Stage 2B (`DEF-UP-001`); Stage 3 (`RUL-01`) | **Low** (non-math) | **Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_exceptions.py)** |
| [`DEF-008`](#def-008) | `Relaxation`, `Compatibility` | `src/slices/core.py:2007,2010` (`relax_large_cell2`) | Omits `fmax=self.fmax, steps=self.steps`, silently using `NequIPRelaxer.relax` defaults (`fmax=0.1, steps=500`) for `>40` atoms | Stage 2B (`DEF-UP-002`); Stage 2A (`FC-08`) | **Medium–High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-009`](#def-009) | `Relaxation`, `Optimization`, `Compatibility` | `src/slices/relax_backends.py:367-372` (`_cell_filter`) | Uses deprecated `ase.filters.ExpCellFilter` instead of `FrechetCellFilter` on `ase>=3.23` | Stage 2B (`DEF-UP-003`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-010`](#def-010) | `Graph`, `Runtime` | `src/slices/tobascco_net.py:413-422,767` (`iter_cycles`, `vertex_positions`) | Mutable default arguments (`[]`, `{}`) persist across direct calls lacking explicit containers (cross-ref `DEF-003`) | Stage 2B (`DEF-UP-004`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-011`](#def-011) | `Math`, `Compatibility` | `src/slices/tobascco_net.py:478,954,964,993` (`linear_independent_vectors`, `eon_projection`, `projection`, `cycle_cocycle_I`) | Pending-deprecated `np.matrix(...).I` usage in NumPy 2.x (cross-ref `DEF-014`) | Stage 2B (`DEF-UP-005`) | **Medium–High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-012`](#def-012) | `Compatibility`, `Runtime` | `src/slices/core.py:652-663` (`SLICES2formula`) | Regex/composition fragility on Strategy 1/2 strings and digit-free invalid strings (`AttributeError` outside `try`) | Stage 2B (`DEF-UP-006`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-013`](#def-013) | `Relaxation`, `Runtime` | `src/slices/core.py:1900-1910,1944-1949` (`to_structures`, `to_4structures`) | `relax_model=None` triggers `AttributeError` on `self.relaxer.relax`, prints error to stdout, then returns `[std, opt], 0` | Stage 2B (`DEF-UP-007`); Stage 3 (`RUL-02`, `CA-06`) | **Low** | **Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_decoding.py)** |
| [`DEF-014`](#def-014) | `Math`, `Optimization` | `src/slices/core.py:1868-1877` (`to_structures` `lattice_type` classifier) | Exact IEEE-754 float `set`/`==` on `metric_tensor_std` diagonals can flip symmetry class & optimizer dimensionality on `~1e-16` rounding (cross-ref `DEF-005`, `DEF-011`) | Stage 2B (`DEF-UP-008`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-015`](#def-015) | `Optimization`, `Graph` | `backup/v3-personal:src/slices/core.py:1685-1705,1758-1769,2393-2395` (`get_inner_p_target`) | Inline `BondParameterFallback` on unmatched supercell bonds (1-based `IndexError` bug) and failure return changed from `None` to `(None, None, None)` | Stage 2A (`FC-06`; cross-ref `DEF-002`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-016`](#def-016) | `Compatibility`, `Graph` | `backup/v3-personal:src/slices/core.py:595-635` vs `src/slices/core.py:280-294` (`from_SLICES`) | Fork swallowed invalid strategy-4 space-group header errors (`space_group_num=None`), accepting malformed strings upstream rejects | Stage 2A (`FC-07`) | **High** | Blocked — Do Not Port |
| [`DEF-017`](#def-017) | `Compatibility` | `backup/v3-personal:src/slices/core.py:483-540` vs `src/slices/core.py:165-200` (`cif2structure_graph`, `structure2structure_graph`) | Fork kept deprecated `StructureGraph.with_local_env_strategy` and duplicated dispatch; superseded upstream by `2635bcc` | Stage 2A (`FC-09`) | **High** | Resolved Upstream — Do Not Regress |
| [`DEF-018`](#def-018) | `Compatibility`, `Runtime` | `backup/v3-personal:src/slices/core.py:1044-1071` vs `src/slices/core.py:666-722` (`structure2SLICES`) | Fork added explicit empty-`Structure` `ValueError` guard on pre-v4.0 path lacking upstream `to_primitive_if_smaller` fallback | Stage 2A (`FC-10`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-019`](#def-019) | `Compatibility`, `Runtime` | `backup/v3-personal:src/slices/core.py:698-759,806-829` vs `src/slices/core.py:345-402,449-470` (`get_slices1..3`, `check_structural_validity`) | Fork dropped `space_group_num=None` 4th arg on `get_slices1..3` (breaking 4-arg dispatch) and added `TypeError` check in `check_structural_validity` | Stage 2A (`FC-11`) | **Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-020`](#def-020) | `Runtime`, `Compatibility` | `backup/v3-personal:src/slices/core.py:10-43,164-232` & `mlip_relaxer.py:22-35` (module import headers) | Fork set global root logger to `CRITICAL` and injected import-time `TF_USE_LEGACY_KERAS="1"` / `sys.modules["keras"] = tf_keras` / TF GPU probe (cross-ref `DEF-005`) | Stage 2A (`FC-12`) | **High** | Blocked — Do Not Port |
| [`DEF-021`](#def-021) | `Graph`, `Math`, `Compatibility` | `src/slices/core.py:549-559` (`check_SLICES`) & `src/slices/tobascco_net.py:233-235,536-541` (`get_lattice_basis`, `get_cocycle_basis`) | `check_SLICES()` ignores `get_lattice_basis() == -1` and cocycle rank failure, silently returning `True` on graphs with no valid 3D lattice basis (reproduced on `E11` `TiBr3`; cross-ref `DEF-003`) | Stage 2C (`DEF-BC-01`) | **High** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-022`](#def-022) | `Runtime`, `Compatibility` | `src/slices/core.py:741,843-845` (`structure2randomSLICES`) | Converts Python `set()` to `list()` before `random.shuffle()`, making cross-process list order dependent on `PYTHONHASHSEED` even with `random.seed(42)` | Stage 2C (`DEF-BC-02`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-023`](#def-023) | `Graph`, `Runtime` | `src/slices/core.py:110,1332-1335,1746-1750` (`SLICES2space_group_number`) | Reads stale `self.unstable_graph` from prior `to_structures()` calls instead of computing per-call `inner_p_std` degeneracy | Stage 2C (`DEF-BC-03`) | **Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-024`](#def-024) | `Compatibility`, `Runtime` | `src/slices/core.py:202-332` (`from_SLICES`) vs `L372-386` (`get_slices2`) | Missing `strategy == 2` branch (`UnboundLocalError`), missing `num_atoms` guard on zero-edge strings, silent token/label truncation, and missing `< 0` node-index check (cross-ref `DEF-016`, `DEF-019`) | Stage 2C (`DEF-BC-04`) | **Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-025`](#def-025) | `Math`, `Compatibility` | `src/slices/core.py:449-470` (`check_structural_validity`) | Always returns `True` on 1-atom cells and ignores periodic self-image distances `<= 0.5 Å` along short lattice vectors (cross-ref `DEF-019`) | Stage 2C (`DEF-BC-05`) | **Low–Medium** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-026`](#def-026) | `Runtime`, `Compatibility` | `src/slices/core.py:186-200,856-867` (`structure2structure_graph`, `get_dim`) | Invalid `graph_method` prints error message and crashes with `UnboundLocalError` instead of raising `ValueError` | Stage 2C (`DEF-BC-06`); Stage 3 Sign-Off | **Low** | Frozen — Deferred (Baseline Preserved) |
| [`DEF-027`](#def-027) | `Math`, `Runtime` | `src/slices/core.py:1611-1672` (`func_check`) vs `L1588-1609` (`func`) | Debug objective `func_check()` lacks the `np.sqrt(max(..., 1e-10))` and `r_temp < 1e-8` clamping guards added to `func()` in commit `2635bcc` | Stage 2C (`DEF-BC-07`) | **Low** | Frozen — Deferred (Baseline Preserved) |

---

## Detailed Register Entries

### DEF-001
- **ID:** `DEF-001`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1275-L1314) — `SLICES.get_uncovered_pair_lj` (lines `1293-1294`) and `SLICES.get_covered_pair_lj` (lines `1312-1313`)
- **Category:** `Math`, `Optimization`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L160)); line numbers verified in Stage 2 initialization.
- **Observed Behavior:** For heteronuclear atom pairs (`i[0] != i[1]`), both `get_uncovered_pair_lj` and `get_covered_pair_lj` compute the Lorentz–Berthelot arithmetic average using `self.atom_types[i[0]]` twice instead of `self.atom_types[i[0]]` and `self.atom_types[i[1]]`:
  ```python
  lj_param[self.atom_types[i[0]]][0]/2 + lj_param[self.atom_types[i[0]]][0]/2,
  lj_param[self.atom_types[i[0]]][1]/2 + lj_param[self.atom_types[i[0]]][1]/2
  ```
  Consequently, heteronuclear pairs receive atom `i[0]`'s homonuclear Lennard-Jones radius (`r0`) and well depth (`eps`) rather than the arithmetic/geometric mix of species `i[0]` and `i[1]`.
- **Why Deferred under Baseline Freeze:** Both lists feed directly into `SLICES.func()` repulsive potential terms during ZL* `fmin_l_bfgs_b` optimization (`core.py:1879-1884`). Correcting the indexing changes gradient evaluations, shifts `structure_recreated_opt` coordinates and lattices for every multi-element crystal, and alters downstream NequIP relaxation trajectories, violating golden equivalence against upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** After Stage 7 sign-off, run an A/B reconstruction benchmark on the MP-20 nonmetal dataset (`data/mp20_nonmetal/`) comparing (a) baseline `i[0]` self-averaging, (b) Lorentz arithmetic mean for both `r0` and `eps` (`(p[i[0]] + p[i[1]]) / 2`), and (c) standard Lorentz–Berthelot mixing (`(r0_i + r0_j)/2`, `sqrt(eps_i * eps_j)`). Measure strict/loose `match_check3` recovery rates, closest-pair overlap frequency, and wall-clock L-BFGS-B iterations before deciding whether to adopt as a versioned/opt-in change or upstream PR.
- **Impact Risk:** **High** — directly alters ZL* objective values and optimized coordinates for all multi-species crystals.

---

### DEF-002
- **ID:** `DEF-002` (Slice 2A Source Tags: `FC-04`, `FC-05`; cross-ref [`DEF-015`](#def-015))
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `57c23ff` & `75ddf8b`), `backup/v3-personal:src/slices/core.py:2459-2566` vs frozen upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1770-L1924) (`SLICES.to_structures`, `SLICES.SLICES2structure`)
- **Category:** `Optimization`, `Relaxation`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L161)); expanded and deduplicated with Stage 2A `FC-04` & `FC-05` ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L258-L259)).
- **Observed Behavior:** In `backup/v3-personal`, `SLICES.to_structures()` automatically attempted to import and execute `slices.decoding_strategies` whenever importable:
  1. **`FC-04` (`core.py:2459-2501`):** Invoked `AdaptiveConvergence.get_convergence_params(num_nodes)` (loosening L-BFGS-B `factr`/`pgtol` for `>10`-atom cells) and `MultiStartOptimizer.optimize(..., n_starts=3)` with unseeded global `np.random.normal(0, 0.1)` perturbations and `scipy>=1.15`-deprecated `iprint=-1, disp=None` kwargs.
  2. **`FC-05` (`core.py:2518-2566`):** Invoked `ProgressiveRelaxer` (`tight: fmax=0.1, steps=200` -> `standard: 0.2/100` -> `loose: 0.3/80` -> `very_loose: 0.5/50`), silently overriding caller-configured `SLICES(fmax=0.2, steps=100)` with `fmax=0.1, steps=200` even on the first relaxation attempt.
  In contrast, upstream v4.0.2 `core.py:1879-1910` runs a single deterministic `fmin_l_bfgs_b` optimization (`m=10`, `factr=1e7`, `pgtol=1e-5`, `maxfun=15000`, `maxiter=15000`) followed by a single-call NequIP relaxation (`relax`, `relax_large_cell1`, or `relax_large_cell2` with built-in overlap pre-optimization and collapse guard in `relax_backends.py`). *(See [`DEF-015`](#def-015) / `FC-06` for the separate `get_inner_p_target` `BondParameterFallback` change.)*
- **Why Deferred under Baseline Freeze:** Auto-injecting multi-start random restarts, loosened tolerances, or tighter/multi-stage relaxation schedules into default `to_structures()` / `SLICES2structure()` breaks CPU determinism, ~3×'s ZL* compute cost, silently overrides `self.fmax`/`self.steps`, and diverges from upstream v4.0.2 `[std, opt, opt2]` structures and energies. During this migration, `decoding_strategies.py` will be ported strictly as an **explicit opt-in API** (`robust_SLICES2structure()`), with all fork bugs fixed and zero calls from default `to_structures()`.
- **Proposed Post-Baseline Investigation / Fix:** Benchmark the opt-in `decoding_strategies` pipeline (using seeded `np.random.default_rng`) against v4.0.2's NequIP `FIRE+BFGS` + collapse-guard relaxer on failing MP-20 SLICES cases to quantify whether multi-start ZL* yields statistically significant net recovery gain over v4.0.2's GFN-FF + NequIP pipeline.
- **Impact Risk:** **High** — fundamentally changes default decoding trajectories, RNG usage, runtime cost, and relaxation outputs.

---

### DEF-003
- **ID:** `DEF-003` (Slice 2A Source Tags: `FC-01`, `FC-02`, `FC-03`; cross-ref [`DEF-010`](#def-010))
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `54fd2c1`, `b59d31b`, `57c23ff`, `75ddf8b`), `backup/v3-personal:src/slices/tobascco_net.py:500-704,985-1006` vs frozen upstream [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L413-L475), [L511-L541](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L511-L541), [L814-L815](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L814-L815)
- **Category:** `Graph`, `Math`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L162)); expanded and deduplicated with Stage 2A `FC-01`, `FC-02`, `FC-03` ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L255-L257)).
- **Observed Behavior:** `backup/v3-personal` introduced three behavioral changes to `Net`:
  1. **`FC-01` — `get_lattice_basis()` (`backup/v3-personal:627-704`):** Reorders `self.cycle_rep` and `self.cycle` via `CycleBasisOptimizer.select_optimal_cycle_basis(..., max_attempts=50)` (or random shuffle fallback) before SymPy nullspace computation, raises `LatticeBasisError` on failure instead of returning `-1`, and returns `None` instead of `1` on success. Slice 2A additionally proved that `select_optimal_cycle_basis` had a row-rank permutation-invariance no-op bug (`np.linalg.matrix_rank(cycle_rep[inds])` is invariant under row permutation, so only `attempt == 0` ever won while still consuming 50 global `np.random` draws).
  2. **`FC-02` — `is_integral(vect, tolerance=1e-6)` (`backup/v3-personal:985-1006`):** Adds a floating-point tolerance fallback after `np.mod(vect, 1) == 0`. Notably, `np.all(fractional_parts < tolerance) or np.all(fractional_parts > 1 - tolerance)` still rejects mixed near-zero and near-one vectors (e.g., `[1e-9, 1 - 1e-9]`), where per-element `(fractional_parts < tol) | (fractional_parts > 1 - tol)` is required.
  3. **`FC-03` — `iter_cycles()` (`backup/v3-personal:500-591`):** Rewrote recursive DFS into an iterative `deque.append` + `deque.popleft()` BFS traversal with `max_depth=100`, changing cycle enumeration order in `get_cycle_basis()` and truncating cycles deeper than 100 edges. *(See also [`DEF-010`](#def-010) / `DEF-UP-004` regarding upstream's mutable default arguments in `iter_cycles` and `vertex_positions`.)*
- **Why Deferred under Baseline Freeze:** Reordering `cycle_rep` alters the SymPy nullspace basis vectors selected for `self.lattice_basis`, changing `self.metric_tensor`, Cholesky `lattice_vectors_std`, and `lattice_arcs`, and changing `1`/`-1` returns to `None`/`LatticeBasisError` breaks callers checking `get_lattice_basis() == -1`. Modifying `is_integral` or `iter_cycles` traversal order alters edge-case topology behavior relative to v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Keep fixed, seeded `find_lattice_basis_with_retries` standalone inside opt-in `decoding_strategies.py`. Post-migration, test (a) whether exact SymPy rational arithmetic in `get_lattice_basis` ever yields non-exact floats needing an element-wise integrality tolerance, (b) whether multi-order SymPy nullspace retries recover failed topologies without regressing valid crystals, and (c) replacing `iter_cycles` with an iterative DFS (`pop()` LIFO) and `None`-guarded defaults (`DEF-010`).
- **Impact Risk:** **High** — modifies fundamental periodic quotient-graph lattice basis selection, metric tensors, and failure control flow.

---

### DEF-004
- **ID:** `DEF-004`
- **Source / Location:** `upstream/main` (`94ef8e0`), [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L352-L365) (`Net.simple_cycle_basis`, line `359`) and [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L511-L517) (`Net.get_lattice_basis`, line `514`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved; RUL-03)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L163)); strict freeze confirmed in Stage 3 `RUL-03` ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L67-L71)).
- **Observed Behavior:**
  - Line `359` (`simple_cycle_basis`): executes `st_vtx = np.random.choice(range(self.graph.order()))`, a leftover from commented-out SageMath code (`# mspt = ... min_spanning_tree(starting_vertex=st_vtx)`). The NetworkX replacement on line `363` (`nx.minimum_spanning_tree(...)`) never reads `st_vtx`.
  - Line `514` (`get_lattice_basis`): creates `inds = list(range(self.cycle_rep.shape[0]))` and calls `np.random.shuffle(inds)`, but lines `515-516` copy `self.cycle_rep.copy()` and `self.cycle.copy()` without indexing by `inds`.
  Both statements are dead code with respect to `Net` calculations, yet silently advance the global NumPy legacy random generator (`np.random`) on every decode call.
- **Why Deferred under Baseline Freeze:** Confirmed under Stage 3 `RUL-03`: although neither value is read inside `Net`, both lines remain verbatim in Stage 4 (using `# noqa: F841` on `st_vtx` for `ruff`) so global legacy `np.random` state advances identically to upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Verify no downstream workflow or `remove_overlaps` call depends on global `np.random` (note `relax_backends.remove_overlaps` uses an isolated `np.random.default_rng(seed)`), then remove both dead RNG calls cleanly and add a regression test asserting that `Net.simple_cycle_basis()` and `Net.get_lattice_basis()` leave `np.random.get_state()` unchanged.
- **Impact Risk:** **Low–Medium** — zero impact on `Net` mathematical outputs; affects only external callers sharing NumPy's legacy global RNG state.

---

### DEF-005
- **ID:** `DEF-005`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L5-L9) (module import side effects)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved; RUL-03)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L164)); strict freeze confirmed in Stage 3 `RUL-03` & `CA-08` ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L67-L71)).
- **Observed Behavior:** Importing `slices.core` unconditionally mutates process-wide environment variables and Python's warning registry:
  ```python
  os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
  warnings.filterwarnings("ignore", category=DeprecationWarning)
  warnings.filterwarnings("ignore", category=FutureWarning)
  os.environ["OMP_NUM_THREADS"] = "1"
  os.environ["PYTHONWARNINGS"] = "ignore"
  ```
  This suppresses warnings across host applications embedding `slices` and overrides any user-configured `OMP_NUM_THREADS` before PyTorch/OpenMP/BLAS thread pools initialize.
- **Why Deferred under Baseline Freeze:** Confirmed under Stage 3 `RUL-03` & `CA-08`: lines 5–9 remain verbatim **above** all scientific imports (with `[tool.ruff.lint.per-file-ignores] "src/slices/core.py" = ["E402"]` in `pyproject.toml`), preventing OpenMP/BLAS thread-pool drift in `np.linalg.cholesky` / `fmin_l_bfgs_b` that could flip `DEF-014` `lattice_type` float equality on 32-core hardware. Meanwhile, `CA-05`/`RUL-07` isolates `python -m slices.relax_backends` from triggering `core.py` via PEP 562 lazy `__getattr__` in `src/slices/__init__.py`.
- **Proposed Post-Baseline Investigation / Fix:** Empirically test CPU determinism and throughput across `OMP_NUM_THREADS ∈ {1, 4, 8, unset}` on the Golden Reference Corpus (both `numpy`/`scipy` ZL* and CPU `nequip-s+l`). Replace unconditional `os.environ[...] = ...` with `os.environ.setdefault(...)` or explicit CLI/context-manager configuration, and replace global `warnings.filterwarnings` with scoped `warnings.catch_warnings()` blocks around noisy third-party calls.
- **Impact Risk:** **Medium** — changing `OMP_NUM_THREADS` can alter floating-point summation order and CPU parallelism; scoping warnings affects only stderr diagnostics.

---

### DEF-006
- **ID:** `DEF-006`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L138-L151) (`SLICES.check_element`) vs [gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py#L11-L22) and [config.py](file:///home/ordillo/tests/SLICES/src/slices/config.py) (`LJ_PARAMS_LIST`, `Z=1..118`)
- **Category:** `Compatibility`, `Math`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 1 Seed ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L165)); verified directly in upstream `core.py` and `gfnff_helper.py`.
- **Observed Behavior:** `SLICES.check_element(structure)` returns `True` iff `np.array(structure.atomic_numbers).max() < 87` (i.e., `Z <= 86`, Rn and lighter), with the legacy docstring noting *"due to GFN-FF's limitation"*. However, upstream v4.0.2 replaced the legacy `xtb` binary with the bundled `pprcht/gfnff` library (`gfnff_helper.py`), which supports `Z = 1..86` under `param_gfnff_legacy86.xtb` overlay and `Z = 87..103` (Fr through Lr, including actinides Th, U, Np, Pu) via the library's internal modern parameter table, and `config.py` provides `LJ_PARAMS_LIST` up to `Z = 118`.
- **Why Deferred under Baseline Freeze:** `check_element()` is part of the frozen validation API tested by the Golden Reference Corpus (including explicit `Z >= 87` rejection cases) and used by `HTS/` and `benchmark/` filtering scripts to match historical Materials Project / xtb-era element coverage. Changing the threshold from `87` to `104` (or `95` to match NequIP-OAM training support) would silently change boolean outputs of `check_element()`.
- **Proposed Post-Baseline Investigation / Fix:** During Stage 5/6 documentation, document the exact `Z <= 86` historical behavior of `check_element()` accurately in its docstring without altering the threshold. Post-migration, verify element coverage of `NequIP-OAM-S/L` and `pprcht/gfnff` across actinides (`Z = 87..103`), and consider adding an optional parameter `max_z: int = 86` to `check_element(structure, max_z=86)` so existing callers preserve `Z <= 86` while actinide workflows can explicitly opt into higher `Z`.
- **Impact Risk:** **Medium** — changes validation acceptance sets for actinide-bearing crystals (`Z >= 87`) and downstream dataset filters.

---

### DEF-007
- **ID:** `DEF-007` (Slice 2B Source Tag: `DEF-UP-001`; Stage 3 Ruling: `RUL-01`)
- **Source / Location:** `upstream/main` (`94ef8e0`, defect introduced in commit `119afaf`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L44-L72) — `function_timeout` -> `signal_handler` (line `60`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_exceptions.py)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L233-L235)); **MODIFY & APPROVE** in Stage 3 `RUL-01` ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L51-L55)); implemented in Stage 4 Wave 4A-2 (commit `49237f6`) and verified in Stage 5 (`tests/unit/test_exceptions.py` & `tests/unit/test_decoding.py`, commit `8d9314b`).
- **Observed Behavior:** `signal_handler` inside `function_timeout` executes `raise TimeoutException("Timed out!")`, but upstream commit `119afaf` deleted the definition/import of `TimeoutException` (`ruff` `F821`). Consequently, any decorated call (`relax`, `relax_large_cell1`, `relax_large_cell2`) that hits its 360/720/2000 s `SIGALRM` deadline raises `NameError: name 'TimeoutException' is not defined` rather than a structured timeout exception (which still gets caught by `except Exception as e:` in `to_structures`, printing the `NameError`).
- **Stage 3 Ruling & Rationale (`RUL-01`):** Approved for Stage 4 Wave 4A-2 (`refactor-core`) because `signal_handler` is never invoked on non-timed-out paths, guaranteeing 100.0% numerical, RNG, and timing invariance. Define `class TimeoutException(SLICESError): pass` in `src/slices/exceptions.py`, import it in `core.py`, and guard `SIGALRM` with `hasattr(signal, "SIGALRM") and threading.current_thread() is threading.main_thread()` (yielding directly off-main-thread/Windows; explicitly rejecting fork's broken `threading.Timer` callback).
- **Proposed Post-Baseline Investigation / Fix:** Implemented in Stage 4 Wave 4A-2 and verified by Stage 5 `tests/unit/test_exceptions.py`.
- **Impact Risk:** **Low** — zero impact on non-timed-out numerical trajectories; restores intended exception type on timeout.

---

### DEF-008
- **ID:** `DEF-008` (Slice 2B Source Tag: `DEF-UP-002`; Slice 2A Source Tag: `FC-08`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1993-L2013) — `SLICES.relax_large_cell2` (lines `2007` and `2010`); independently altered in `backup/v3-personal:src/slices/core.py:2763-2782` (commit `665b042`)
- **Category:** `Relaxation`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L236-L238)) & Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L262)); verified directly in `src/slices/core.py:1951-2013`.
- **Observed Behavior:** Whereas `relax` (`<=20` atoms, `L1964,1967`) and `relax_large_cell1` (`21..40` atoms, `L1985,1988`) forward `fmax=self.fmax, steps=self.steps` (defaults `0.2`, `100`) to `self.relaxer.relax(...)`, `relax_large_cell2` (`>40` atoms, `L2007,2010`) invokes `self.relaxer.relax(struc)` with no keyword arguments. Under `NequIPRelaxer.relax`, this silently applies the backend's own defaults (`fmax=0.1, steps=500`) and ignores caller-configured `SLICES(fmax=..., steps=...)`.
- **Why Deferred under Baseline Freeze:** Passing `fmax=self.fmax, steps=self.steps` in `relax_large_cell2` would alter relaxation step counts, force convergence criteria, final geometries, and energies for all structures with `>40` atoms relative to upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** During Stage 5/6, document the exact `>40`-atom behavior explicitly in the `relax_large_cell2` Google docstring without altering runtime kwargs. Post-migration, benchmark `>40`-atom crystals under `(fmax=0.2, steps=100)` vs `(fmax=0.1, steps=500)` and evaluate forwarding `self.fmax`/`self.steps` consistently across all three cell-size branches.
- **Impact Risk:** **Medium–High** — directly changes force convergence and trajectory length for all `>40`-atom relaxations.

---

### DEF-009
- **ID:** `DEF-009` (Slice 2B Source Tag: `DEF-UP-003`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L367-L372) — `_cell_filter`
- **Category:** `Relaxation`, `Optimization`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L239-L241)); verified directly in `src/slices/relax_backends.py:367-372`.
- **Observed Behavior:** `_cell_filter(atoms)` imports and instantiates `ase.filters.ExpCellFilter(atoms)` (with fallback to `ase.constraints.ExpCellFilter` for `ase < 3.23`). Under locked `ase==3.29.0`, ASE emits `DeprecationWarning: Use FrechetCellFilter for better convergence w.r.t. cell variables`.
- **Why Deferred under Baseline Freeze:** `ExpCellFilter` and `FrechetCellFilter` define different strain parameterizations and cell-gradient Jacobians (`dE/dF` vs exponential map), which changes every BFGS/LBFGS/FIRE relaxation step, final lattice parameters, and energy in `NequIPRelaxer.relax`, breaking CPU parity (`atol=1e-12`) against `SLICES-upstream-baseline`.
- **Proposed Post-Baseline Investigation / Fix:** Keep `ExpCellFilter` frozen as long as `ase` retains it. Post-migration (or ahead of an ASE major release removing `ExpCellFilter`), run a full MP-20 benchmark comparing `ExpCellFilter` vs `FrechetCellFilter` on match rate, energy distribution, convergence steps, and collapse-guard trigger frequency.
- **Impact Risk:** **High** — alters every NequIP variable-cell relaxation trajectory and final geometry/energy.

---

### DEF-010
- **ID:** `DEF-010` (Slice 2B Source Tag: `DEF-UP-004`; cross-ref [`DEF-003`](#def-003))
- **Source / Location:** `upstream/main` (`94ef8e0`), [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L413-L422) (`Net.iter_cycles`) and [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L767-L785) (`Net.vertex_positions`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L242-L244)); verified directly in `src/slices/tobascco_net.py`.
- **Observed Behavior:** Both methods define mutable default arguments (`cycle=[]`, `used=[]`, `nodes_visited=[]`, `cycle_baggage=[]` in `iter_cycles`; `pos={}`, `bad_ones={}` in `vertex_positions`; `ruff` `B006`). Calling either method directly without passing fresh containers mutates the function-level defaults across subsequent invocations. (`Net.get_cycle_basis` passes explicit empty lists at `L307-310`, masking the bug on that internal call path, and `vertex_positions` itself carries an upstream `# NOTE: NOT WORKING - FIX!!!` comment at `L775`.)
- **Why Deferred under Baseline Freeze:** Both methods reside inside the frozen `Net` class. While distinct from `backup/v3-personal`'s algorithmic BFS rewrite logged in `DEF-003`, altering frozen `Net` method signatures/bodies is deferred until post-baseline verification confirms zero external callers rely on shared default behavior.
- **Proposed Post-Baseline Investigation / Fix:** Audit all call sites of `iter_cycles` and `vertex_positions` across `src/slices/`, `HTS/`, and `benchmark/`; replace mutable defaults with `None` guards (`if cycle is None: cycle = []`) and add unit tests verifying repeated calls are stateless.
- **Impact Risk:** **Low–Medium** — no effect on `SLICES.to_structures()` (which uses `simple_cycle_basis`), but changes repeated direct invocations of `iter_cycles()`/`vertex_positions()`.

---

### DEF-011
- **ID:** `DEF-011` (Slice 2B Source Tag: `DEF-UP-005`; cross-ref [`DEF-014`](#def-014))
- **Source / Location:** `upstream/main` (`94ef8e0`), [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L478) (`linear_independent_vectors`), [L954](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L954) (`eon_projection`), [L964](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L964) (`projection`), and [L993](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L993) (`cycle_cocycle_I`)
- **Category:** `Math`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L245-L247)); verified directly in `src/slices/tobascco_net.py`.
- **Observed Behavior:** `Net` relies on `np.matrix(d).I` (which dispatches internally to `np.linalg.inv` or `pinv` through NumPy's pending-deprecated `numpy.matrix` subclass) for `eon_projection`, `projection`, and `cycle_cocycle_I`, plus `np.matrix(R)` in `linear_independent_vectors`.
- **Why Deferred under Baseline Freeze:** Replacing `np.matrix(d).I` with `np.linalg.inv(d)` / `np.linalg.pinv(d)` can introduce `~1e-16` floating-point differences in `metric_tensor` and `lattice_arcs`. Because `core.py:1868-1877` (`DEF-014`) classifies `lattice_type` using exact IEEE-754 float `set` equality and `fmin_l_bfgs_b` uses finite-difference gradients (`epsilon=1e-8`), even a 1-ULP change in `metric_tensor_std` can flip optimizer dimensionality and cause macroscopic trajectory divergence.
- **Proposed Post-Baseline Investigation / Fix:** Once `DEF-014` (tolerant `lattice_type` classification) is evaluated, benchmark migrating `np.matrix(...).I` to `np.linalg.inv` (and `np.asarray` in `linear_independent_vectors`) on the Golden Reference Corpus and MP-20 dataset to confirm NumPy 3.x readiness without numerical regression.
- **Impact Risk:** **Medium–High** — negligible algebraic difference alone, but amplified to discrete branching changes by `DEF-014`.

---

### DEF-012
- **ID:** `DEF-012` (Slice 2B Source Tag: `DEF-UP-006`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L652-L663) — `SLICES.SLICES2formula`
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L248-L250)); verified directly in `src/slices/core.py:652-663`.
- **Observed Behavior:** After stripping strategy-4 space-group tokens via `_first_element_index`, `SLICES2formula` runs `match = re.search(r'^(.*?)(\d+)', SLICES)` and immediately calls `match.group(1)` **outside** the `try`/`except` block. Two edge cases fail inconsistently:
  1. For Strategy 2 strings (e.g., underscore-delimited tokens `Si_O_0001...`), underscores remain in `extracted_string` and cause `Composition(extracted_string)` to fail (printing to stdout and returning `None`).
  2. For malformed or digit-free strings, `match` is `None`, raising an uncaught `AttributeError: 'NoneType' object has no attribute 'group'` instead of returning `None` or raising a structured `SLICESEncodingError`/`ValueError`.
- **Why Deferred under Baseline Freeze:** `SLICES2formula` is in the frozen parsing/validation surface; altering its return/exception behavior for invalid or legacy-strategy inputs could diverge from v4.0.2 parity checks.
- **Proposed Post-Baseline Investigation / Fix:** Document Strategy 3/4 input expectations clearly in Stage 5/6 docstrings. Post-migration, guard `if match is None:` cleanly, decide on a consistent error/return contract, and evaluate direct token-based formula extraction (supporting Strategies 1–4 uniformly).
- **Impact Risk:** **Low–Medium** — affects only Strategy 1/2 strings and malformed digit-free inputs.

---

### DEF-013
- **ID:** `DEF-013` (Slice 2B Source Tag: `DEF-UP-007`; Stage 3 Ruling: `RUL-02`, `CA-06`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1900-L1910) (`SLICES.to_structures`) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1944-L1949) (`SLICES.to_4structures`)
- **Category:** `Relaxation`, `Runtime`
- **Status:** `Resolved in Stage 4 (commit 49237f6; verified in tests/unit/test_decoding.py)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L251-L253)); **APPROVE** in Stage 3 `RUL-02` & `CA-06` ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L57-L65)); implemented in Stage 4 Wave 4A-2 (commit `49237f6`) and verified with zero-stdout assertions in Stage 5 (`tests/unit/test_decoding.py`, commit `8d9314b`).
- **Observed Behavior:** `SLICES.__init__` already unifies both `relax_model=None` and `relax_model="none"` (plus `SLICES_RELAX_MODEL=none`) via `make_relaxer` to `(None, "none")`. However, when `self.relaxer is None`, `to_structures()` (`L1901-1906`) and `to_4structures()` (`L1945`) still enter `@function_timeout` `self.relax(...)`, arm `SIGALRM`, trigger `AttributeError: 'NoneType' object has no attribute 'relax'`, print the error to stdout (twice in `to_4structures`), and catch it to return `[structure_recreated_std, structure_recreated_opt], 0` (or `structures, final_energy_per_atom`).
- **Stage 3 Ruling & Rationale (`RUL-02` / `CA-06`):** Approved for Stage 4 Wave 4A-2 (`refactor-core`): insert `if self.relaxer is None: return [structure_recreated_std, structure_recreated_opt], 0` before `try:` at `core.py:1900` and `if self.relaxer is None: return structures, final_energy_per_atom` before `try:` at `core.py:1944`. Return tuples are bit-identical for both `None` and `"none"` (`to_relaxed_structure` still raises `Exception("relax failed")` when `len(structures) != 3`), while eliminating spurious stdout `AttributeError` prints and unnecessary `SIGALRM` calls.
- **Proposed Post-Baseline Investigation / Fix:** Implemented in Stage 4 Wave 4A-2 and verified in Stage 4/5 tests.
- **Impact Risk:** **Low** — return structures and energy (`0`) are bit-identical; only eliminates spurious stdout `AttributeError` message and `SIGALRM` setup when `relax_model=None` / `"none"`.

---

### DEF-014
- **ID:** `DEF-014` (Slice 2B Source Tag: `DEF-UP-008`; cross-ref [`DEF-005`](#def-005), [`DEF-011`](#def-011))
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1868-L1877) — `SLICES.to_structures` (`lattice_type` classification)
- **Category:** `Math`, `Optimization`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2B ([AUDIT_UPSTREAM_STYLE.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md#L254-L256)); verified directly in `src/slices/core.py:1868-1877`.
- **Observed Behavior:** `to_structures` classifies the lattice symmetry constraint mode passed to `initialize_x_bounds` and `func` using exact IEEE-754 floating-point `set` deduplication and `==` comparisons on the diagonal entries of `metric_tensor_std`:
  ```python
  lattice_length_list = [metric_tensor_std[0,0], metric_tensor_std[1,1], metric_tensor_std[2,2]]
  lattice_length_list_unique = list(set(lattice_length_list))
  lattice_type = len(lattice_length_list_unique)
  if lattice_type == 2:
      if metric_tensor_std[0,0] == metric_tensor_std[1,1]: lattice_type = 23
      if metric_tensor_std[0,0] == metric_tensor_std[2,2]: lattice_type = 22
      if metric_tensor_std[2,2] == metric_tensor_std[1,1]: lattice_type = 21
  ```
  A floating-point rounding drift as small as `~1e-16` between two theoretically equal diagonal components flips `lattice_type` from `1` (cubic, 1 length variable) or `21`/`22`/`23` (2 length variables) to `3` (3 independent length variables), changing the dimensionality of `x` and `bounds` in `fmin_l_bfgs_b`.
- **Why Deferred under Baseline Freeze:** This discrete branching sensitivity is the primary mechanistic reason upstream `tobascco_net.py` (`np.matrix.I`, `DEF-011`), `get_rescaled_lattice_vectors`, `np.linalg.cholesky`, and import-time `OMP_NUM_THREADS="1"` (`DEF-005`) must remain bit-for-bit untouched during the migration. Introducing a relative tolerance (e.g., `math.isclose(..., rel_tol=1e-9)`) would reclassify borderline high-symmetry crystals and alter their ZL* parameter spaces relative to v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Post-migration, audit the distribution of `|g_ii - g_jj| / max(g_ii, g_jj)` across the MP-20 dataset (all 7 crystal systems) to measure how often cubic/tetragonal/hexagonal nets miss symmetry classification due to `~1e-15` Cholesky/rescaling noise, and evaluate replacing exact `==` with `math.isclose(..., rel_tol=1e-9, abs_tol=1e-12)` alongside `DEF-011` and `DEF-005`.
- **Impact Risk:** **High** — directly alters ZL* optimization variable dimensionality (`lattice_type` ∈ `{1, 21, 22, 23, 3}`) and symmetry preservation during L-BFGS-B optimization.

---

### DEF-015
- **ID:** `DEF-015` (Slice 2A Source Tag: `FC-06`; cross-ref [`DEF-002`](#def-002))
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `57c23ff` & `75ddf8b`), `backup/v3-personal:src/slices/core.py:1685-1705,1758-1769,2393-2395` vs frozen upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1157-L1173), [L1224-L1227](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1224-L1227) (`SLICES.get_inner_p_target`)
- **Category:** `Optimization`, `Graph`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 5.2 & Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L243-L245)); upstream target lines verified in `src/slices/core.py:1157-1227`.
- **Observed Behavior:** In `backup/v3-personal`, when a bond `blist_original[i]` was absent from `blist_super` inside `get_inner_p_target()`, the fork injected `BondParameterFallback.estimate_bond_length(...)` instead of upstream's `print('Cannot find bond!!!'); continue` (`core.py:1165-1167`), and changed the `except` failure return from implicit `None` (`core.py:1225-1226`) to `(None, None, None)`. Furthermore, `blist_original[i]` holds **1-based `3×3×3` supercell indices** (`1..27*n_atom`), whereas the fork indexed `atom_symbols[blist_original[i][0]]` (length `n_atom`), triggering `IndexError` on fallback invocation.
- **Why Deferred under Baseline Freeze:** Substituting covalent-radius bond estimates alters `inner_p_target[i, i]` diagonals and `colattice_weights` normalization whenever GFN-FF drops a bond, diverging from v4.0.2 ZL* targets; changing `None` to `(None, None, None)` alters caller unpacking/error handling. Moreover, v4.0.2's bundled `libgfnff` already resolved xtb's legacy actinide/crash failures.
- **Proposed Post-Baseline Investigation / Fix:** Keep a bug-fixed `BondParameterFallback` (using proper supercell symbol lookup and `pymatgen` covalent radii) strictly inside opt-in `decoding_strategies.robust_decode` when `get_inner_p_target()` fails; post-migration, measure how often `Cannot find bond!!!` still occurs under v4.0.2 `libgfnff` on MP-20 before deciding whether core fallback logic is warranted.
- **Impact Risk:** **High** — modifies `inner_p_target` matrices, bond-weight normalization, and failure return contract.

---

### DEF-016
- **ID:** `DEF-016` (Slice 2A Source Tag: `FC-07`)
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `665b042` & `54fd2c1`), `backup/v3-personal:src/slices/core.py:595-635` vs frozen upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L275-L296) (`SLICES.from_SLICES`)
- **Category:** `Compatibility`, `Graph`
- **Status:** `Blocked — Do Not Port`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L261)); blocked in Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L135)).
- **Observed Behavior:** In upstream v4.0.2 `core.py:281-288`, when a Strategy 4 SLICES string has prefix tokens before `_first_element_index` (`first_elem_idx > 0`) that fail `get_space_group_num_from_letter_enc(letter_enc)`, `from_SLICES` raises `Exception("Error: space_group_num = None")`, causing `check_SLICES` / `check_SLICES_basic` to return `False`. In `backup/v3-personal`, the fork swallowed that failure by setting `space_group_num = None` and also inferred `num_atoms` even when no numeric edge-index token was present.
- **Why Deferred under Baseline Freeze:** Swallowing invalid space-group header errors causes `from_SLICES`, `check_SLICES`, and `check_SLICES_basic` to **accept corrupted/invalid Strategy 4 SLICES strings** that upstream v4.0.2 rejects, directly violating golden validation parity.
- **Proposed Post-Baseline Investigation / Fix:** Do not port to `core.py`. Keep upstream's strict space-group header validation intact and include corrupted Strategy 4 headers in the Stage 3/5 golden validation test suite to guard against regression.
- **Impact Risk:** **High** — silently alters boolean validity outputs of `check_SLICES` and `check_SLICES_basic` on malformed Strategy 4 strings.

---

### DEF-017
- **ID:** `DEF-017` (Slice 2A Source Tag: `FC-09`)
- **Source / Location:** `backup/v3-personal` (`301c75f`, commit `665b042`), `backup/v3-personal:src/slices/core.py:483-540` vs upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L165-L200) (`SLICES.cif2structure_graph`, `SLICES.structure2structure_graph`; fixed upstream in commit `2635bcc`)
- **Category:** `Compatibility`
- **Status:** `Resolved Upstream — Do Not Regress`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L263)) & Stage 2B commit `#21` (`2635bcc`); confirmed in Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L135)).
- **Observed Behavior:** Because `backup/v3-personal` diverged at `cea17da` (`== 142298b`), it retained the deprecated `StructureGraph.with_local_env_strategy(...)` API and duplicated `graph_method` dispatch across both `cif2structure_graph` and `structure2structure_graph`. Upstream v4.0.2 (`2635bcc`) already migrated to `StructureGraph.from_local_env_strategy(...)` (required by `pymatgen>=2025/2026`), added the `BrunnerNNReciprocal` import fallback, and deduplicated `cif2structure_graph` to delegate directly to `structure2structure_graph`.
- **Why Deferred under Baseline Freeze:** Recorded explicitly so Stage 4 refactoring preserves upstream v4.0.2's `from_local_env_strategy` implementation and never overwrites it with older `backup/v3-personal` hunks.
- **Proposed Post-Baseline Investigation / Fix:** None needed — already resolved in upstream v4.0.2 (`94ef8e0`).
- **Impact Risk:** **High** (if regressed) — breaks compatibility with locked `pymatgen==2025.10.7` and `pymatgen>=2026.3`.

---

### DEF-018
- **ID:** `DEF-018` (Slice 2A Source Tag: `FC-10`)
- **Source / Location:** `backup/v3-personal` (`301c75f`, commit `54fd2c1`), `backup/v3-personal:src/slices/core.py:1044-1071` vs frozen upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L666-L722) (`SLICES.to_primitive_if_smaller`, `_run_with_primitive_fallback`, `structure2SLICES`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L264)).
- **Observed Behavior:** `backup/v3-personal` added an explicit `if len(structure) == 0: raise ValueError(...)` guard at the entry of `structure2SLICES` (on the pre-v4.0 encoding path without primitive-cell pre-reduction). Upstream v4.0.2 (`da0d873`) routes `structure2SLICES`, `structure2randomSLICES`, and `from_cif` through `to_primitive_if_smaller` and `_run_with_primitive_fallback` without a custom empty-structure `ValueError`.
- **Why Deferred under Baseline Freeze:** All encoding entry points and primitive-cell fallback branches in `core.py:666-722` are frozen; introducing new early-exit exception paths could alter error behavior on degenerate structures relative to v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Post-migration, verify how `to_primitive_if_smaller` and `structure2SLICES` fail on 0-site `Structure` instances and evaluate adding a clean `SLICESEncodingError` / `ValueError` guard with unit tests.
- **Impact Risk:** **Low–Medium** — affects only degenerate 0-atom `Structure` inputs.

---

### DEF-019
- **ID:** `DEF-019` (Slice 2A Source Tag: `FC-11`)
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `665b042` & `54fd2c1`), `backup/v3-personal:src/slices/core.py:698-759,806-829` vs frozen upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L345-L402), [L449-L470](file:///home/ordillo/tests/SLICES/src/slices/core.py#L449-L470) (`get_slices1..3`, `check_structural_validity`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L265)); upstream signatures verified directly in `src/slices/core.py:345-470`.
- **Observed Behavior:** `backup/v3-personal` made two API-contract changes relative to upstream v4.0.2:
  1. Removed the 4th parameter `space_group_num=None` from `get_slices1`, `get_slices2`, and `get_slices3` (added upstream in commit `da0d873` so `get_slices_by_strategy` at `core.py:354` uniformly dispatches `method(atom_symbols, edge_indices, to_jimages, space_group_num)`).
  2. Added an explicit `isinstance(str1, Structure)` guard raising `TypeError` in `check_structural_validity` (whereas upstream raises `AttributeError` when accessing `str1.lattice` on a non-`Structure`).
- **Why Deferred under Baseline Freeze:** Removing `space_group_num=None` from `get_slices1..3` directly breaks `get_slices_by_strategy` (`TypeError: takes 3 positional arguments but 4 were given`) and any 4-arg callers. Deferring `check_structural_validity`'s `AttributeError` -> `TypeError` shift keeps exception-type parity with upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Never drop `space_group_num=None` from `get_slices1..3`. Post-migration, evaluate adding explicit type validation (`TypeError`) on `check_structural_validity` if desired as part of a versioned API hardening pass.
- **Impact Risk:** **Medium** — dropping the 4th argument breaks Strategy 1–3 encoding outright; `check_structural_validity` change affects only invalid non-`Structure` callers.

---

### DEF-020
- **ID:** `DEF-020` (Slice 2A Source Tag: `FC-12`; cross-ref [`DEF-005`](#def-005))
- **Source / Location:** `backup/v3-personal` (`301c75f`, commits `54fd2c1` & `58ff66c`), `backup/v3-personal:src/slices/core.py:10-43,164-232` & `backup/v3-personal:src/slices/mlip_relaxer.py:22-35` vs upstream [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L4-L9) & [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Blocked — Do Not Port`
- **Provenance:** Stage 2A ([AUDIT_FORK_DIFF.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L266)); blocked in Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L135)).
- **Observed Behavior:** In `backup/v3-personal`, importing `slices.core` or `slices.mlip_relaxer` executed process-wide side effects beyond upstream's `core.py:5-9` (`DEF-005`):
  1. Mutated Python's global root logger via `logging.getLogger().setLevel(logging.CRITICAL)`, silencing all `INFO`/`WARNING`/`ERROR` logs across any host application or test runner importing `slices`.
  2. Set `os.environ["TF_USE_LEGACY_KERAS"] = "1"`, monkey-patched `sys.modules["keras"] = tf_keras`, and probed `tf.config.list_physical_devices("GPU")` at module import time, pulling TensorFlow into every encoding-only or CPU NequIP workflow.
- **Why Deferred under Baseline Freeze:** Violates lazy-import hygiene, breaks host-application logging and PyTorch-only v4.0.2 environments (where TensorFlow is not even installed), and mutates `sys.modules` globally.
- **Proposed Post-Baseline Investigation / Fix:** Do not port to `core.py` or module-level `mlip_relaxer.py`. Isolate `TF_USE_LEGACY_KERAS` / `tf_keras` strictly inside `M3GNetRelaxer.__init__` when a user explicitly requests optional legacy `relax_model="m3gnet"`.
- **Impact Risk:** **High** — corrupts process-wide logging and breaks TensorFlow-free v4.0.2 environments if imported eagerly.

---

### DEF-021
- **ID:** `DEF-021` (Slice 2C Source Tag: `DEF-BC-01`; cross-ref [`DEF-003`](#def-003))
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L549-L559) (`SLICES.check_SLICES`) and [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L233-L235), [L536-L541](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L536-L541) (`Net.get_cocycle_basis`, `Net.get_lattice_basis`)
- **Category:** `Graph`, `Math`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L319-L332)); upstream lines verified directly in `core.py` and `tobascco_net.py`.
- **Observed Behavior:** `check_SLICES()` executes `net.simple_cycle_basis()`, `net.get_lattice_basis()`, and `net.get_cocycle_basis()` (`core.py:554-556`) inside `try ... except: return False`, assuming failure raises an exception. In upstream `tobascco_net.py`, however, `get_lattice_basis()` logs `"Could not obtain the lattice basis from the cycle vectors!"` and returns `-1` without raising (leaving `net.lattice_basis = None`), and `get_cocycle_basis()` prints `"ERROR - could not find a linearly independent cocycle basis!"` without raising when `count != size`. Consequently, `check_SLICES()` silently returns `True` on non-3D/degenerate graphs that cannot form a valid 3D lattice basis; subsequent `to_structures()` or `SLICES2space_group_number()` calls crash in `net.get_metric_tensor()` with `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`. Empirically reproduced on quasi-1D/2D MP-20 structures (`TiBr3` `mp-28214` row `464`, `MnBr2` `mp-569843` row `199`, `GaTe` `mp-10009` row `0`; locked as edge fixture `E11`).
- **Why Deferred under Baseline Freeze:** Checking `if net.get_lattice_basis() == -1: return False` (or cocycle rank failure) in `check_SLICES()` directly alters boolean validity rates across generative-model benchmarks (`benchmark/Validity_rate_ucRNN__Success_rate_cRNN/`) relative to upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Quantify how many generated SLICES strings in historical RNN/MatterGPT benchmarks pass `check_SLICES()` solely due to ignored `-1` / cocycle rank failures, then enforce explicit `if net.get_lattice_basis() == -1: return False` (and cocycle rank validation) in `check_SLICES()` and raise `LatticeBasisError` in `to_structures()` rather than `NoneType * float` `TypeError`.
- **Impact Risk:** **High** — directly changes `check_SLICES()` boolean validity results on borderline/low-dimensional periodic graphs.

---

### DEF-022
- **ID:** `DEF-022` (Slice 2C Source Tag: `DEF-BC-02`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L741), [L835-L845](file:///home/ordillo/tests/SLICES/src/slices/core.py#L835-L845) (`SLICES.structure2randomSLICES`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L336-L343)); upstream lines verified directly in `core.py:835-845`.
- **Observed Behavior:** `structure2randomSLICES()` collects unique augmented strings in `SLICES_set = set()` (`L741`), converts `SLICES_list = list(SLICES_set)` (`L843`), runs `random.shuffle(SLICES_list)` (`L844`), and returns `SLICES_list[:num]`. Because CPython randomizes string hash salts per process unless `PYTHONHASHSEED` is fixed, `list(SLICES_set)` yields different pre-shuffle ordering across processes even under `random.seed(42)` (empirically confirmed: `16/16` corpus structures had different list orders across unseeded-hash subprocesses, and `16/16` matched identically once `PYTHONHASHSEED=0` was set).
- **Why Deferred under Baseline Freeze:** Replacing `list(SLICES_set)` with `sorted(SLICES_set)` or insertion-ordered `dict.fromkeys` would change the exact permutation returned under `PYTHONHASHSEED=0` relative to upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Replace `SLICES_set = set()` with insertion-ordered deduplication or `sorted(SLICES_set)` prior to shuffling with an optional isolated `random.Random(seed)` parameter so augmentation is 100% process-independent regardless of `PYTHONHASHSEED`.
- **Impact Risk:** **Low–Medium** — affects only output ordering and subset selection when `len(SLICES_set) > num` across different `PYTHONHASHSEED` values.

---

### DEF-023
- **ID:** `DEF-023` (Slice 2C Source Tag: `DEF-BC-03`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L110), [L1332-L1335](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1332-L1335), [L1746-L1750](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1746-L1750) (`SLICES.SLICES2space_group_number`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L347-L354)); upstream lines verified directly in `core.py:1745-1755`.
- **Observed Behavior:** `self.unstable_graph` is initialized to `False` in `SLICES.__init__` (`L110`) and refreshed solely inside `get_rescaled_lattice_vectors()` (`L1332-1335`) based on `np.diag(inner_p_std) > 0.0001`. Although `SLICES2space_group_number()` never calls `get_inner_p_target()` or `get_rescaled_lattice_vectors()`, line `1746` still branches on `if self.unstable_graph:` (`net.cocycle_rep = np.zeros((net.order-1, net.ndim)) + .5`). Consequently, on a fresh instance `self.unstable_graph` is always `False` (even for degenerate nets like `G18` `YHO2`), whereas on a reused instance that previously decoded an unstable graph via `to_structures()`, stale `self.unstable_graph == True` contaminates subsequent `SLICES2space_group_number()` calls.
- **Why Deferred under Baseline Freeze:** Computing `inner_p_std` locally inside `SLICES2space_group_number()` would change space-group predictions on barycentrically degenerate nets (`G18`) compared to fresh-instance upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Compute `inner_p_std = np.dot(np.dot(net.lattice_arcs, net.metric_tensor), net.lattice_arcs.T)` locally inside `SLICES2space_group_number()` without reading/mutating stale `self.unstable_graph`, and reset per-structure transient state at the start of `from_SLICES()`.
- **Impact Risk:** **Medium** — causes instance-reuse state leakage and inconsistent space-group determination on barycentrically unstable graphs.

---

### DEF-024
- **ID:** `DEF-024` (Slice 2C Source Tag: `DEF-BC-04`; cross-ref [`DEF-016`](#def-016), [`DEF-019`](#def-019))
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L202-L332) (`SLICES.from_SLICES`) vs [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L372-L386) (`SLICES.get_slices2`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L358-L369)); upstream lines verified directly in `core.py`.
- **Observed Behavior:** Four input-parsing gaps exist in `from_SLICES()`:
  1. **No `strategy == 2` parser or `else:` guard:** `to_SLICES(strategy=2)` encodes fixed-width strings, yet `from_SLICES` handles only `strategy in {1, 3, 4}`, falling through to `UnboundLocalError` on `edge_indices` (`L330`) for `strategy=2` or invalid strategy integers.
  2. **Zero-edge strings (`"Si O"`):** When no token satisfies `.isnumeric()` in `strategy == 3` (`L219-223`) or `strategy == 4` (`L290-296`), `num_atoms` remains unbound (`UnboundLocalError`).
  3. **Silent truncation of trailing tokens and extra label characters:** `int((len(tokens) - start_idx) / 3)` (and `/5`, `/7`) silently discards trailing partial edge tuples, and `for j in range(3): edge[2][j]` ignores extra characters when `len(edge[2]) > 3`.
  4. **Unchecked negative node indices:** `edge_indices[i,0] > num_atoms - 1` (`L231, 259, 306`) omits `< 0`, allowing `"-1"` in edge tokens to parse as negative indices.
- **Why Deferred under Baseline Freeze:** Tightening token-length or edge-label validation in `from_SLICES()` could reject malformed/truncated LLM- or RNN-generated strings that currently parse in `benchmark/` scripts.
- **Proposed Post-Baseline Investigation / Fix:** Add `strategy == 2` decoding (or raise an explicit `ValueError("strategy=2 is encode-only")`), validate `strategy in {1, 2, 3, 4}`, guard `num_atoms is None` with `SLICESDecodingError`, enforce `0 <= idx < num_atoms`, and validate exact edge-tuple multiples and `len(edge[2]) == 3` (with an optional lenient mode if legacy generative benchmarks require truncation).
- **Impact Risk:** **Medium** — alters exception types and rejection behavior on malformed or Strategy-2 SLICES strings.

---

### DEF-025
- **ID:** `DEF-025` (Slice 2C Source Tag: `DEF-BC-05`; cross-ref [`DEF-019`](#def-019))
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L449-L470) (`SLICES.check_structural_validity`)
- **Category:** `Math`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L373-L380)); upstream lines verified directly in `core.py:449-470`.
- **Observed Behavior:** `check_structural_validity(str1)` inspects strictly upper-triangular pairs (`i < j`) of `str1.lattice.get_all_distances(str1.frac_coords, str1.frac_coords)`. On any 1-atom primitive cell (`len(str1) == 1`, e.g., `G14` `Na`), the loop executes zero times, leaving `min_value = 10000000` and returning `True` even if a collapsed lattice axis (`min(str1.lattice.abc) <= 0.5 Å`) places periodic self-images within `0.5 Å`. Multi-atom cells with short lattice axes (`<= 0.5 Å`) similarly ignore periodic self-image collisions because diagonal entries in `get_all_distances` are `0.0`.
- **Why Deferred under Baseline Freeze:** `check_structural_validity()` is part of frozen structural-validity benchmarks; altering it changes validity outcomes on collapsed 1-atom or short-axis structures relative to v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Include periodic self-image checks via `min(str1.lattice.abc) > 0.5` (or `str1.get_neighbor_list(r=0.5)` excluding `[0,0,0]` self-pairs) and benchmark impact on historical MP-20 / RNN validity datasets.
- **Impact Risk:** **Low–Medium** — affects only degenerate cells with lattice vector length `<= 0.5 Å`.

---

### DEF-026
- **ID:** `DEF-026` (Slice 2C Source Tag: `DEF-BC-06`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L186-L200) (`SLICES.structure2structure_graph`) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L856-L867) (`SLICES.get_dim`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L384-L391)); strict freeze confirmed in Stage 3 Sign-Off ([REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L136)).
- **Observed Behavior:** Passing an unrecognized `graph_method` (e.g., `'econ'` in legacy fork tests) to `SLICES(graph_method=...)` is accepted in `__init__`, and then `structure2structure_graph()` (`L199`) and `get_dim()` (`L865`) execute `else: print("ERROR - graph_method not implemented")` before immediately dereferencing unassigned `structure_graph` / `bonded_structure`, raising `UnboundLocalError`.
- **Why Deferred under Baseline Freeze:** Confirmed strictly frozen under Stage 3 Sign-Off (`REVIEW_SIGNOFF.md:136`) to keep upstream v4.0.2 control flow and exception semantics completely invariant during migration.
- **Proposed Post-Baseline Investigation / Fix:** Post-migration, validate `graph_method` against `VALID_GRAPH_METHODS = ("econnn", "crystalnn", "brunnernn", "mininn")` and raise `ValueError`.
- **Impact Risk:** **Low** — zero impact on valid `graph_method` inputs; replaces broken `UnboundLocalError` on invalid names.

---

### DEF-027
- **ID:** `DEF-027` (Slice 2C Source Tag: `DEF-BC-07`)
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1611-L1672) (`SLICES.func_check`, lines `1660` and `1669-1670`) vs [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1588-L1609) (`SLICES.func`, hardened in commit `2635bcc`)
- **Category:** `Math`, `Runtime`
- **Status:** `Frozen — Deferred (Baseline Preserved)`
- **Provenance:** Stage 2C ([AUDIT_BASELINE_HARNESS.md Section 5](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md#L395-L401)); upstream lines verified directly in `core.py:1588-1672`.
- **Observed Behavior:** Upstream commit `2635bcc` added numerical guards to `func()` (`np.sqrt(max(inner_p[i][j], 1e-10))` at `L1593` and `if r_temp < 1e-8: r_temp = 1e-8` at `L1604-1605`) to prevent `ZeroDivisionError`/`NaN` during ZL* optimization. The companion diagnostic method `func_check()` (invoked when `self.check_results=True` at `core.py:1897`) was not updated and still computes unclamped `np.sqrt(inner_p[i][j])` (`L1660`) and `(uncovered_pair_lj[i][1] / r_temp) ** 12` (`L1670`), risking `ZeroDivisionError` or `NaN` in debug mode on degenerate geometries.
- **Why Deferred under Baseline Freeze:** `func_check()` belongs to the frozen ZL* objective module; synchronize its clamping guards with `func()` post-baseline (or if explicitly approved in Stage 3 Review).
- **Proposed Post-Baseline Investigation / Fix:** Mirror `func()`'s `epsilon2 = 1e-10` and `r_temp = max(r_temp, 1e-8)` guards in `func_check()` (and guard `sqrt(inner_p[i][i])` in the angle print at `L1664`), adding a regression test with `check_results=True`.
- **Impact Risk:** **Low** — affects only `check_results=True` debug print mode on zero-distance edge/pair geometries.

---

## Stage 2 Audit Consolidation Status (Complete)

All three Stage 2 parallel audits have been consolidated and deduplicated with 100% traceability:
- **Stage 1 Seeds ([PLAN.md Section 4.2](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L158-L166)):** 6 entries (`DEF-001`–`DEF-006`).
- **Slice 2B (`architect` -> [AUDIT_UPSTREAM_STYLE.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md)):** 8 entries (`DEF-UP-001`..`DEF-UP-008` -> `DEF-007`–`DEF-014`; 0 duplicates).
- **Slice 2A (`auditor-fork` -> [AUDIT_FORK_DIFF.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md)):** 12 entries (`FC-01`..`FC-12` -> 6 cross-referenced merges into `DEF-002`, `DEF-003`, `DEF-008` + 6 net-new `DEF-015`–`DEF-020`).
- **Slice 2C (`baseline` -> [AUDIT_BASELINE_HARNESS.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md)):** 7 entries (`DEF-BC-01`..`DEF-BC-07` -> `DEF-021`–`DEF-027`; 0 duplicates).

**Total Active Register Entries:** **27** (`DEF-001`–`DEF-027`). Next sequential ID available for Stage 4+ discoveries: **`DEF-028`**.

---

## Stage 3–5 Execution & Verification Status

Per [REVIEW_SIGNOFF.md Section 3](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L129-L137) (`reviewer`, `#21`) and Stage 4/5 independent gates (`#34`, `#45`, `#55`, `HEAD=8d9314b`), all 27 register entries are verified as follows:
- **Resolved in Stage 4 & Verified in Stage 5 (2 entries — zero normal-path mathematical drift):**
  - `DEF-007` (`RUL-01`): `TimeoutException(SLICESError)` implemented in `src/slices/exceptions.py`, imported in `src/slices/core.py` with POSIX main-thread `SIGALRM` scoping (commit `49237f6`), verified in `tests/unit/test_exceptions.py` and `tests/unit/test_decoding.py` (commit `8d9314b`).
  - `DEF-013` (`RUL-02`, `CA-06`): `if self.relaxer is None:` short-circuit implemented in `core.py` `to_structures()` and `to_4structures()` (commit `49237f6`), verified with zero-stdout assertions in `tests/unit/test_decoding.py` (commit `8d9314b`).
- **Blocked from Porting / Regression (3 entries):** `DEF-016` (`FC-07`), `DEF-017` (`FC-09`, already fixed upstream in `2635bcc`), and `DEF-020` (`FC-12`) confirmed absent from core runtime paths (guarded by `tests/regression/test_edge_cases.py`).
- **Frozen — Deferred (Baseline Preserved, 22 entries):** `DEF-001`–`DEF-003`, `DEF-004` & `DEF-005` (`RUL-03` strict freeze), `DEF-006`, `DEF-008`–`DEF-012`, `DEF-014`–`DEF-015`, `DEF-018`–`DEF-019`, and `DEF-021`–`DEF-027` remain strictly preserved at upstream v4.0.2 (`89/89` golden equivalence tests passing at `atol=1e-12` and `250/250` active pytest tests green at `HEAD=8d9314b`).
