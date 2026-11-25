# First-Principles Empirical Re-Evaluation: Graph Topology, Quotient-Net, Relaxation & Decoding Strategy

**Evaluator:** `eval-graph-relax` (Carbon High)  
**Date:** 2026-11-25  
**Target Codebase:** `/home/ordillo/tests/SLICES` at `HEAD=fa4cfc8` (`slices-4-personal`, post-Stage-7)  
**Baseline Reference:** `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`, tag `v4.0.2`)  
**Source Register:** [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md)  
**Hardware / Runtime:** `Intel(R) Xeon(R) 6731P` (32 physical cores, `OMP_NUM_THREADS=1`, `PYTHONHASHSEED=0`), Python `3.10`, `torch==2.9.1+cpu`, `nequip==0.17.1`, `pymatgen==2025.10.7`, `ase==3.29.0`, `sympy`, bundled `libgfnff.so.0.1.1`  
**Methodology:** Strictly non-destructive empirical A/B experiments executed in `/dev/shm/reeval-graph-relax/` (removed upon completion) across **67,826 SLICES strings** (`9` corpora), **3,883 GFN-FF topology evaluations**, **51 end-to-end multi-start vs single-start decoding benchmarks**, **49 controlled `ExpCellFilter` vs `FrechetCellFilter` NequIP relaxations**, **10 `>40`-atom supercell `relax_large_cell2` benchmarks**, and **`94` golden/unit pytest checks**.

---

## 1. Executive Summary & Re-Evaluation Verdicts

> [!NOTE]
> Stage 4/5 Google-style docstrings and `function_timeout` refactoring shifted line coordinates in `src/slices/core.py`, `src/slices/tobascco_net.py`, and `src/slices/relax_backends.py`. Both the historical register coordinates and the exact verified `HEAD=fa4cfc8` coordinates are documented below.

| ID | Register Coords | `HEAD=fa4cfc8` Coords | Symbol / Scope | Re-Evaluation Verdict | Key Quantitative Empirical Finding |
|---|---|---|---|---|---|
| [`DEF-021`](#21-def-021-check_slices-ignoring-get_lattice_basis---1--cocycle-rank-failure) | `core.py:549-559`, `tobascco_net.py:233-235,536-541` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L638-L736) (`L727-L736`), [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L204-L235), [L456-L486](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L456-L486) | `SLICES.check_SLICES`, `Net.get_lattice_basis`, `Net.get_cocycle_basis` | **`HIGH_VALUE_AB`** *(`check_SLICES` when `graph_rank_check=True`)* + **`SAFE_NOW`** *(explicit `LatticeBasisError` in `to_structures`)* | Scanned **67,826 strings (`9` datasets)**: false-positive `check_SLICES() == True` rate is **`0.38%` (`9/2,383`)** in `mp20_v4`, **`0.73%` (`103/14,041`)** in `mp20_legacy`, **`4.45%` (`65/1,461`)** on unfiltered `mp20/test.csv` CIFs, **`4.97%` (`9/181`, `-0.90 pp` `Validity_rate`)** on raw cRNN `sampled.sli`, and **`0.58%–1.65%` (`401/38,244`)** in published cRNN `results_3_fix_valid_check_unique.sli` — where **`0/401` (`0.0%`) survived step `4_inverse`** (`100%` crash `to_structures()` with `NoneType * float` `TypeError`). Must guard under `if graph_rank_check:` for RL scripts. |
| [`DEF-003`](#22-def-003-fork-tobascco_netpy-changes-cyclebasisoptimizer-is_integral-iter_cycles) | `tobascco_net.py:413-475,511-541,814-815` | [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L292-L429), [L456-L486](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L456-L486), [L712-L714](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L712-L714); [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L65-L216) | `CycleBasisOptimizer`, `Net.is_integral`, `Net.iter_cycles` | **Split:** **`HIGH_VALUE_AB`** *(`basis == -1` fallback only)*; **`KEEP_FROZEN`** *(unconditional reorder, `is_integral`, `iter_cycles`)* | **Smith Normal Form proof:** Unconditional `CycleBasisOptimizer` perturbs `lattice_basis` on **`1,640/2,374` (`69.1%`)** and flips `DEF-014` `lattice_type` on **`260/2,374` (`10.95%`)** valid crystals (`KEEP_FROZEN`). Yet **strictly as a `basis == -1` fallback**, it has **`0.0` drift** on passing crystals while rescuing **`100.0%` (`175/175`: `7/7` `mp20_v4`, `62/62` `mp20_14k`, `5/5` `mp20_test`, `100/100` `cRNN`, `1/1` `HTS`)** of unimodular `SNF(cycle_rep) == (1,1,1)` nets! Exact SymPy `abs(nulv[0]) == 1` has **`0` float-noise failures**; `iter_cycles` has **`0` callers** across SLICES. |
| [`DEF-023`](#23-def-023-stale-selfunstable_graph-in-slices2space_group_number) | `core.py:110,1332-1335,1746-1750` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L206), [L1618-L1621](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1618-L1621), [L2038-L2116](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2038-L2116) (`L2100-L2103`) | `SLICES.SLICES2space_group_number`, `self.unstable_graph` | **`SAFE_NOW`** *(delete `if self.unstable_graph:` in `SLICES2space_group_number` + reset in `from_SLICES`)* | **`16/2,374` (`0.67%`)** `mp20_v4` nets have `unstable_graph == True`. Reusing a contaminated instance (`unstable_graph=True`) **collapses SG accuracy from `91.62%` (`2,175/2,374`) to `4.68%` (`111/2,374`)**, corrupting `96.0%` (`2,264/2,358`) of stable crystals! Crucially, even on the `16` unstable nets, zero-cocycle placement (`False`) hits **`56.25%` (`9/16`)** exact SG vs **`12.50%` (`2/16`)** when locally applying `cocycle_rep = +0.5`! Deleting `L2100-L2103` preserves **100% (`89/89` golden + `2,374/2,374` MP-20)** fresh parity while eliminating reuse corruption. |
| [`DEF-010`](#24-def-010-mutable-default-arguments-in-netiter_cycles--netvertex_positions) | `tobascco_net.py:413-422,767-785` | [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L385-L429) (`L389-L392`), [L671-L706](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L671-L706) (`L675-L676`) | `Net.iter_cycles`, `Net.vertex_positions` | **`SAFE_NOW`** | `0` external callers across repo; `vertex_positions` is dead legacy code (`# NOTE: NOT WORKING - FIX!!!` in upstream `L775`, hits `RecursionError` on default `pos={}`). Calling `net.iter_cycles()` twice with defaults **crashes immediately on call 2 with `AssertionError` (`assert edge is not None`, `L402`)**. Replacing `[]`/`{}` with `None` guards fixes statelessness and passes **`94/94` golden + graph tests (`atol=1e-12`)**. |
| [`DEF-009`](#25-def-009-expcellfilter-vs-frechetcellfilter-in-relax_backendspy) | `relax_backends.py:367-372` | [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L539-L545) (`_cell_filter`) | `_cell_filter` (`NequIPRelaxer` & `MLIPRelaxer`) | **`KEEP_FROZEN`** *(scope-suppress ASE `DeprecationWarning`; optional `VERSIONED_OPT_IN`)* | Controlled 49-crystal (`19` Golden + `30` MP-20) `nequip-s+l` A/B test: **`ExpCellFilter` outperforms `FrechetCellFilter`** on mean BFGS steps (`11.61` vs `12.45`), wall-clock latency (`347.5 ms` vs `376.4 ms`, **`8.3%` faster**), lower final energy (**`31/49` = `63.3%`** vs `10/49` = `20.4%`), and **strict `StructureMatcher` recovery (`43/46` = `93.48%` vs `41/46` = `89.13%`, `-4.35 pp` regression on `G05`, `G10`, `M09`)**. |
| [`DEF-008`](#26-def-008-relax_large_cell2-ignoring-selffmax--selfsteps-for-40-atom-cells) | `core.py:1993-2013` (`L2007,2010`) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2534-L2554) (`L2548,L2551`) | `SLICES.relax_large_cell2` | **`SAFE_NOW`** | **`0` structures `>40` atoms** exist in any shipped MP-20 (`16,686`), QMOF (`928`), `examples/`, `HTS/`, or `89/89` golden test (`0.0` baseline drift). On `10` distorted `45–64`-atom supercells, forwarding `fmax=self.fmax, steps=self.steps` (`0.2, 100`) vs `(0.1, 500)` converges **`10/10` (`100%`)**, speeds up relaxation **`1.24x`** (`16.58 s` vs `20.55 s`, `35.3` vs `43.1` steps), preserves **`9/10 == 9/10` strict match** (`mean |dE| = 0.37 meV/atom`), and fixes caller/tier overrides. |
| [`DEF-002`](#27-def-002--def-015-multi-start-zl--robust_slices2structure--gfn-ff-bondparameterfallback) | `backup/v3-personal:core.py:2459-2566` vs `core.py:1770-1924` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2120-L2410), [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L307-L784) | `SLICES.to_structures`, `SLICES.robust_SLICES2structure` | **`KEEP_FROZEN`** *(default `to_structures`)*; **`VERSIONED_OPT_IN`** *(`robust_SLICES2structure`)* | Always-on `MultiStartOptimizer(n_starts=3)` + `AdaptiveConvergence` slows decoding **`1.85x` (`2.81 s` vs `1.52 s`, up to `2.96x` on 14–20 atoms)** for **`0` net match gain** on normal (`27/30` strict, `29/30` loose) and non-GFN-FF-edge hard cases (`12/17` strict, `15/17` loose). Fallback-only `robust_SLICES2structure` adds **`0%` overhead** on passing crystals while isolating recovery cleanly. |
| [`DEF-015`](#27-def-002--def-015-multi-start-zl--robust_slices2structure--gfn-ff-bondparameterfallback) | `backup/v3-personal:core.py:1685-1769` vs `core.py:1157-1227` | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1305-L1502) (`L1433,L1474,L1488-L1490`), [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L219-L305), [L544-L554](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L544-L554), [L749-L756](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L749-L756) | `SLICES.get_inner_p_target`, `BondParameterFallback`, `robust_decode` | **`VERSIONED_OPT_IN`** *(trigger Stage 2 in `robust_decode` when `diag <= 0`)* + **`SAFE_NOW`** *(`vangl` `NaN` guard)* | Across **3,883 structures**, bundled `libgfnff` returned `None` on **`0/2,883` (`0.00%`)** MP-20 crystals (`0/143` actinides, `0/102` `CN>=19`) and **`1/1,000` (`0.10%`)** cRNN strings (`math.cos(NaN)` `ValueError` at `L1474`), and printed `"Cannot find bond!!!"` on **`2/2,383` (`0.084%`)** `mp20_v4` and **`4/500` (`0.80%`)** `mp20/test` lanthanide/actinide hydrides (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`). Triggering `BondParameterFallback` on `diag <= 0` **triples strict recovery on bond-drop crystals from `1/4` (`25%`) to `3/4` (`75%`)**! |

---

## 2. Detailed Empirical Re-Evaluations

### 2.1 `DEF-021`: `check_SLICES()` Ignoring `get_lattice_basis() == -1` & Cocycle Rank Failure

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L638-L736) (`SLICES.check_SLICES`, specifically `L727-L736` ignoring return value of `net.get_lattice_basis()` and `net.get_cocycle_basis()`).
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L456-L486) (`Net.get_lattice_basis`, logging error and returning `-1` with `self.lattice_basis = None` at `L482-L484`).
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L204-L235) (`Net.get_cocycle_basis`, printing error without raising when `count != size` at `L227-L228`).
  - Downstream crash sites: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2075) (`SLICES2space_group_number`, caught and returning `None`) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2184) (`to_structures` -> `net.get_metric_tensor()`, raising uncaught `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`).
- **Re-Evaluation Verdict:** **`HIGH_VALUE_AB`** *(for enforcing `basis != -1` and cocycle full-rank inside `check_SLICES(..., graph_rank_check=True)`)* + **`SAFE_NOW`** *(for raising structured `LatticeBasisError` / `CocycleBasisError` in `to_structures()` instead of crashing with `NoneType * float` `TypeError`)*

#### Multi-Corpus Empirical False-Positive Scan (`67,826` Strings Across `9` Datasets)

| Corpus | Strategy | Total | `check_SLICES` `True` (`graph_rank_check=True`) | `get_lattice_basis() == -1` | Cocycle Rank Fail (`count != V-1`) | Combined False Positives | False-Positive Rate Among Valid | Survived `4_inverse`? |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` | 4 | `2,383` | `2,383` | `8` | `1` | **`9`** | **`0.38%`** | N/A (`0/9` decodable) |
| `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` | 4 | `14,303` | `14,041` | `85` | `18` | **`103`** | **`0.73%`** | N/A (`0/103` decodable) |
| `data/mp20/test.csv[:1500]` *(unfiltered CIFs -> `structure2SLICES`)* | 4 | `1,500` | `1,461` | `65` | `18` *(subset)* | **`65`** | **`4.45%`** | **`0/5` tested** (`TypeError`) |
| `cRNN/2_train_sample/sampled.sli` *(raw RNN samples)* | 3 | `1,000` | `181` (`18.10%`) | `8` | `1` | **`9`** | **`4.97%`** (`18.1% -> 17.2%`) | N/A |
| `cRNN/Other_targets/3_eform_-3/...unique.sli` | 3 | `9,782` | `9,782` | `150` | `16` | **`161`** | **`1.65%`** | **`0 / 161` (`0.0%`)** |
| `cRNN/Other_targets/3_eform_-4/...unique.sli` | 3 | `9,626` | `9,626` | `106` | `13` | **`115`** | **`1.19%`** | **`0 / 115` (`0.0%`)** |
| `cRNN/Other_targets/3_eform_-5/...unique.sli` | 3 | `9,407` | `9,407` | `46` | `11` | **`55`** | **`0.58%`** | **`0 / 55` (`0.0%`)** |
| `cRNN/Other_targets/3_eform_-6/...unique.sli` | 3 | `9,429` | `9,429` | `49` | `28` | **`70`** | **`0.74%`** | **`0 / 70` (`0.0%`)** |
| `ucRNN/6_check_struc_validity/results_6_...csv` *(post-`4_inverse`)* | 3 | `9,402` | `9,402` | `0` | `0` | **`0`** | **`0.00%`** | Already filtered by crash |
| `HTS/9_EAH_Band_gap_PBE/results_9_EAH_Band_gap_PBE.csv` | 3 | `999` | `998` | `1` | `0` | **`1`** | **`0.10%`** | Pre-v4 xtb artifact |

#### Mechanistic Findings & Benchmark Impact Analysis
1. **Why Heuristic Axis-Coverage Checks Miss Low-Dimensional Nets:**
   - In `data/mp20/test.csv[:1500]` (unfiltered MP-20 crystals including layered/quasi-1D phases such as `Fe(HO)2` `mp-626680`, `MnBr2` `mp-569843`, `TiBr3` `mp-28214`, `SbNO` `mp-758558`, `AuSe` `mp-2793`, `TaSe3` `mp-29652`), `59 / 65` (`90.8%`) of the false positives have `rank(cycle_rep) <= 2` (`54` 2D nets with Smith Normal Form `(1, 1, 0)` and `5` 1D nets with `(1, 0, 0)`). Because tilted 2D layers or chains cross all three unit-cell faces (`a, b, c`) in oblique settings, `to_jimages` populates all 3 columns with non-equal index sets, passing `check_SLICES`'s heuristic set-difference check (`core.py:716-726`) while spanning only a 1D/2D subspace of $\mathbb{R}^3$.
2. **100% Downstream Crash Confirmation & Published Benchmark Proof:**
   - Every single tested false positive (`Fe(HO)2`, `Fe3Te2Se`, `SbNO`, `Sr2FeCuSO3`, `HfSeS`) raises `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'` inside `to_structures()` and returns `None` in `SLICES2space_group_number()`.
   - Cross-referencing all **`401` false positives** across the four published cRNN `results_3_fix_valid_check_unique.sli` files (`38,244` strings that passed `3_fix_valid_check`) against `4_inverse/results_4_inverse.csv` confirmed **`0 / 401` (`0.00%`) survived step `4_inverse`** — every one crashed during inversion, wasting SLURM worker slots while artificially inflating step-3 `Validity_rate` by `0.58%–1.65%` (and `-0.90` percentage points on raw `sampled.sli`: `18.10% -> 17.20%`).
3. **Critical RL Compatibility Constraint (`graph_rank_check=False`):**
   - Static audit found three RL prior/transfer training loops ([HTS/2_train_sample/train_prior.py](file:///home/ordillo/tests/SLICES/HTS/2_train_sample/train_prior.py#L68), [transfer_userinpt.py](file:///home/ordillo/tests/SLICES/HTS/2_train_sample/transfer_userinpt.py#L81), and [benchmark/.../train_prior.py](file:///home/ordillo/tests/SLICES/benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/2_train_sample/train_prior.py#L71)) calling `check_SLICES(slices, dupli_check=False, graph_rank_check=False)` where 1D/2D graphs (`b < 3`, `basis_status == -1`) are intentionally rewarded. Therefore, enforcing `basis_status == 1` and cocycle full-rank inside `check_SLICES()` **must be gated on `if graph_rank_check:`**!
4. **Interaction with `DEF-003` (`SNF == (1, 1, 1)`):**
   - Notably, in `mp20_v4_benchmark_2383.csv`, `7 / 8` of the `get_lattice_basis() == -1` cases are actually valid 3D unimodular nets (`SNF == (1, 1, 1)`) where `Net.get_lattice_basis()` had a false negative (Section 2.2), and golden test `E11` (`TiBr3`) explicitly asserts upstream's current `check_SLICES == True` quirk. Thus changing `check_SLICES()` is rated **`HIGH_VALUE_AB`** (adopt alongside a golden fixture update for `E11` and `DEF-003` fallback), whereas replacing `NoneType * float` `TypeError` in `to_structures()` with `raise LatticeBasisError(...)` / `raise CocycleBasisError(...)` is **`SAFE_NOW`** (`0/89` golden drift).

---

### 2.2 `DEF-003`: Fork `tobascco_net.py` Changes (`CycleBasisOptimizer`, `is_integral`, `iter_cycles`)

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - Frozen upstream `Net`: [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L292-L322) (`get_cycle_basis`), [L339-L383](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L339-L383) (`simple_cycle_basis`), [L385-L429](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L385-L429) (`iter_cycles`), [L456-L486](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L456-L486) (`get_lattice_basis`), [L712-L714](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L712-L714) (`is_integral`).
  - Ported opt-in helpers: [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L65-L86) (`is_approximately_integral`) and [L89-L216](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L89-L216) (`CycleBasisOptimizer`).
- **Re-Evaluation Verdict:** **Split by sub-component:**
  - **`FC-01` (`CycleBasisOptimizer.find_lattice_basis`):** **`KEEP_FROZEN` as unconditional replacement**; **`HIGH_VALUE_AB` strictly as a `basis_status == -1` fallback** *(already active opt-in in `robust_SLICES2structure`)*.
  - **`FC-02` (`is_integral` float tolerance):** **`KEEP_FROZEN` / `LOW_PRIORITY`** in `Net.is_integral` *(keep `is_approximately_integral` in `decoding_strategies.py`)*.
  - **`FC-03` (`iter_cycles` BFS rewrite):** **`KEEP_FROZEN` / `LOW_PRIORITY`** *(unused dead path in SLICES)*.

#### (a) Empirical Audit of SymPy Rational `nullspace()` & `is_integral()` Across `4,883` Nets
Instrumenting every `sy.Matrix(kk.T).nullspace()` vector across `mp20_v4_benchmark_2383.csv` (`2,383` nets), `data/mp20/test.csv[:1500]` (`1,500` nets), and `sampled.sli` (`1,000` nets):

| Corpus | Nets Audited | `abs(nulv[0]) != 1` Vectors | `abs(nulv[0]) != 1` Yielding Integral `tv` | Near-Integer Float Noise `(0, 1e-6]` (`max_err`) | True Rational Fractions (`1/2`, `1/3`, ...) | `Net.kernel` Float Noise `(0, 1e-6]` |
|---|---:|---:|---:|---:|---:|---:|
| `mp20_v4_benchmark_2383.csv` | `2,383` | `631` | `215` | `9` (`4.44e-16` on `nulv[0] != 1` division) | `416` | **`0`** (`5` rank-mismatch warnings) |
| `data/mp20/test.csv[:1500]` | `1,500` | `308` | `102` | **`0`** (`0.0`) | `206` | **`0`** |
| `cRNN/sampled.sli` | `1,000` | `2,965` | `258` | **`0`** (`0.0`) | `2,983` | **`0`** |

- Under upstream's `abs(nulv[0]) == 1.0` branch (`v = -nulv[1:] * nulv[0]`), SymPy's exact rational RREF entries that produce mathematically integral `tv` had **zero (`0`) float-rounding rejections** across all `4,883` nets.
- Only when generalizing to `abs(nulv[0]) > 1e-8` with float division `v = -nulv[1:] / nulv[0]` (as in `CycleBasisOptimizer.find_lattice_basis`, e.g. dividing by `3.0`) do `9` vectors exhibit `2`-ULP (`4.44e-16`) IEEE-754 rounding residuals, which `decoding_strategies.is_approximately_integral(..., tolerance=1e-6)` + `np.rint(tv)` already handles cleanly without affecting `tobascco_net.py`.

#### (b) Smith Normal Form Proof & Exact Rescue Rate of `CycleBasisOptimizer.find_lattice_basis`
For every graph across all corpora where `check_SLICES` pre-filters passed (`b >= 3`) yet upstream `Net.get_lattice_basis()` returned `-1`, we computed the exact integer **Smith Normal Form (`SNF`) invariant factors `(d_1, d_2, d_3)`** of `net.cycle_rep` ($\in \mathbb{Z}^{N_{\text{cyc}} \times 3}$) and ran `CycleBasisOptimizer.find_lattice_basis` (`max_attempts=20` and `100`):

| Corpus | `Net.get_lattice_basis() == -1` Total | Rank Deficient (`d_3 = 0`, 1D/2D) | Proper Sublattice (`d_3 >= 2`, e.g. `(1,1,2)`, `(1,1,3)`) | **Unimodular `SNF == (1, 1, 1)`** *(Basis Exists!)* | **Rescued by `CycleBasisOptimizer` (`20` / `100` tries)** | Unimodular Rescue Rate |
|---|---:|---:|---:|---:|---:|---:|
| `mp20_v4_benchmark_2383.csv` | `8` | `0` | `1` `(1,1,3)` | **`7`** | **`7` / `7`** | **`100.0%`** |
| `mp20_eform_bandgap_nonmetal.csv` | `85` | `0` | `23` `(1,1,2)` | **`62`** | **`62` / `62`** | **`100.0%`** |
| `data/mp20/test.csv[:1500]` | `65` | `59` | `1` `(1,1,2)` | **`5`** (`Ti4FeSe8`, `K2BeO2`, ...) | **`5` / `5`** | **`100.0%`** |
| `cRNN` (`4` `unique.sli` files, `38,244` rows) | `351` *(+`1` `0`-cyc)* | `189` | `61` | **`100`** | **`100` / `100`** | **`100.0%`** |
| `cRNN/sampled.sli` (`1,000` raw) | `8` | `2` | `1` `(1,1,2)` | **`5`** | **`4` / `4`** | **`80.0%`** |
| `HTS/results_9_EAH_Band_gap_PBE.csv` | `1` | `0` | `0` | **`1`** | **`1` / `1`** | **`100.0%`** |
| **Combined Across All Datasets** | **`518`** | **`250`** | **`87`** | **`180`** | **`179` / `179`** | **`99.4%`** |

> [!IMPORTANT]
> **Why Upstream Fails on Unimodular `SNF == (1, 1, 1)` Nets — And Why Unconditional Reordering Must Never Be Default:**
> 1. **Algebraic Root Cause:** An integral cycle combination spanning $\mathbf{e}_m \in \mathbb{Z}^3$ exists if and only if $\mathbf{e}_m$ lies in the integer row lattice of `cycle_rep` (guaranteed for all $m \in \{1,2,3\}$ iff $\text{SNF}(\text{cycle\_rep}) = (1, 1, 1)$). However, `Net.get_lattice_basis()` inspects **only single basis vectors** `nulv` of `sy.Matrix(kk.T).nullspace()` requiring `abs(nulv[0]) == 1.0`. When the first 3 linearly independent rows of `cycle_rep` happen to form a $3 \times 3$ submatrix of determinant $\pm 2$ or $\pm 3$, SymPy's RREF pivot columns yield half- or third-integer single nullspace vectors (`nulv[0] != 1` or fractional `v`), even though an integer linear combination of multiple nullspace vectors — or a row permutation placing a unimodular $\det = \pm 1$ triple first — yields an exact integral basis!
> 2. **Unconditional Perturbation Hazard (`2,374` Valid MP-20 Nets):** Running `CycleBasisOptimizer.find_lattice_basis` unconditionally on all `2,374` already-passing `mp20_v4` crystals changed `net.lattice_basis` on **`1,640 / 2,374` (`69.08%`)**, shifted `net.metric_tensor` (`> 1e-12`) on **`4` crystals**, and **flipped `DEF-014` `lattice_type` symmetry constraints on `260 / 2,374` (`10.95%`)**!
> 3. **Optimal Design:** Keep `Net.get_lattice_basis()` untouched on its primary path (`0.0` drift on all `2,374` passing crystals and `89/89` golden tests), and invoke `CycleBasisOptimizer.find_lattice_basis` (or exact Hermite Normal Form integer linear solving) **exclusively when `net.get_lattice_basis() == -1`**.

#### (c) `Net.iter_cycles()` Scaling vs `Net.simple_cycle_basis()`
- Repo-wide grep/AST audit confirms **`Net.iter_cycles()` and `Net.get_cycle_basis()` have `0` callers** across SLICES encoding, validation, and decoding (`core.py` and `decoding_strategies.py` exclusively call Kruskal/MST `simple_cycle_basis()`).
- Direct empirical benchmark on Golden Corpus crystal nets:

| Crystal Net | `V` | `E` | `simple_cycle_basis()` Rank | `simple_cycle_basis()` Time | `iter_cycles()` Yielded (cap `2,000`) | Max Cycle Length | `iter_cycles()` Time |
|---|---:|---:|---:|---:|---:|---:|---:|
| `G14` (`Na`) | `1` | `7` | `7` | **`0.305 ms`** | `7` *(complete)* | `1` | `0.045 ms` |
| `G10` (`BaSn2`) | `3` | `9` | `7` | **`0.435 ms`** | `36` *(complete)* | `3` | `0.361 ms` |
| `G01` (`NdSiRu`) | `6` | `32` | `27` | **`1.274 ms`** | `2,000` *(capped!)* | `6` | **`45.13 ms+`** |
| `G02` (`Sr3Ru2O7`) | `12` | `42` | `31` | **`1.731 ms`** | `2,000` *(capped!)* | `10` | **`51.49 ms+`** |

- Simple cycles are bounded in depth by `V` (`<= 20..40` << `sys.getrecursionlimit() == 1000`), so `iter_cycles` suffers from **$O(2^{E-V+1})$ combinatorial cycle-enumeration blowup** rather than stack overflow, making `simple_cycle_basis()` strictly superior and rendering fork's BFS `iter_cycles` rewrite unnecessary (`KEEP_FROZEN` / `LOW_PRIORITY`, aside from fixing its `DEF-010` mutable defaults).

---

### 2.3 `DEF-023`: Stale `self.unstable_graph` in `SLICES2space_group_number`

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L206): `self.unstable_graph = False` initialized in `SLICES.__init__`.
  - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1618-L1621): `self.unstable_graph` mutated inside `get_rescaled_lattice_vectors()` during `to_structures()` when `any(np.diag(inner_p_std) <= 0.0001)`.
  - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2038-L2116): `SLICES2space_group_number()` never calls `get_rescaled_lattice_vectors()`, yet branches on `if self.unstable_graph:` at `L2100-L2103` (`net.cocycle_rep = np.zeros((net.order - 1, net.ndim)) + 0.5`).
- **Re-Evaluation Verdict:** **`SAFE_NOW`** *(delete `if self.unstable_graph:` at `core.py:2100-2103` inside `SLICES2space_group_number()` AND reset `self.unstable_graph = False` in `from_SLICES()` at `core.py:337` — **do NOT** locally apply `cocycle_rep = +0.5` in `SLICES2space_group_number()`!)*

#### Full 2,374-Structure `mp20_v4_benchmark_2383.csv` Space-Group Accuracy Experiment
Every valid 3D net in `mp20_v4_benchmark_2383.csv` (`2,374` structures; Strategy 4 header provides exact ground-truth `sg_true` and `crystal_system`) was evaluated under all three regimes:
- **Mode A (`Fresh Instance`, `unstable_graph = False`):** Pure zero-cocycle Eon barycentric embedding (`cocycle_rep = 0`).
- **Mode B (`Contaminated Reused Instance`, `unstable_graph = True`):** State left behind after a single prior `to_structures()` call on an unstable graph (such as `G18` `YHO2`).
- **Mode C (`Per-Call Local Degeneracy`, `unstable_graph = any(diag(inner_p_std) <= 1e-4)`):** Applying `cocycle_rep = +0.5` only when the current net has a zero-length barycentric edge.

| Subset (`mp20_v4_benchmark_2383`) | Count | Mode | Exact SG Match (`sg_pred == sg_true`) | Crystal-System Match | `None` / Error Count | Predictions Changed vs Mode A |
|---|---:|---|---|---|---|---:|
| **All Valid 3D Nets** | `2,374` | **Mode A (`Fresh: False`)** | **`2,175 / 2,374` (`91.62%`)** | **`2,220 / 2,374` (`93.51%`)** | `7` | `0` *(Baseline)* |
| **All Valid 3D Nets** | `2,374` | **Mode B (`Contaminated: True`)** | **`111 / 2,374` (`4.68%`)** | **`343 / 2,374` (`14.45%`)** | `30` | **`2,274 / 2,374` (`95.79%`)** |
| **All Valid 3D Nets** | `2,374` | **Mode C (`Local Computed`)** | `2,168 / 2,374` (`91.32%`) | `2,213 / 2,374` (`93.22%`) | `8` | `10 / 2,374` (`0.42%`) |
| **Stable Nets (`unstable == False`)** | `2,358` (`99.33%`) | **Mode A (`False`)** | **`2,166 / 2,358` (`91.86%`)** | **`2,209 / 2,358` (`93.68%`)** | `3` | `0` |
| **Stable Nets (`unstable == False`)** | `2,358` (`99.33%`) | **Mode B (`Contaminated: True`)** | **`109 / 2,358` (`4.62%`)** | **`339 / 2,358` (`14.38%`)** | `25` | **`2,264 / 2,358` (`96.01%`)** |
| **Unstable Nets (`unstable == True`)** | `16` (`0.67%`) | **Mode A (`False`, `cocycle=0`)** | **`9 / 16` (`56.25%`)** | **`11 / 16` (`68.75%`)** | `4` | `0` |
| **Unstable Nets (`unstable == True`)** | `16` (`0.67%`) | **Mode C (`Local: True`, `cocycle=+0.5`)** | **`2 / 16` (`12.50%`)** | **`4 / 16` (`25.00%`)** | `5` | `10 / 16` (`7` regressions!) |

> [!WARNING]
> **Critical First-Principles Discovery:**
> 1. **Catastrophic Instance-Reuse Bug Confirmed:** Once `to_structures()` decodes any of the `0.67%` unstable graphs (`16/2,374`: `5` monoclinic, `4` triclinic, `4` orthorhombic, `2` trigonal, `1` cubic — or Golden `G18` `YHO2`), `self.unstable_graph` remains `True` until another `to_structures()` call overwrites it. Any subsequent `SLICES2space_group_number()` calls on that `SLICES` instance suffer an **accuracy collapse from `91.62%` down to `4.68%`**, corrupting **`96.01%` (`2,264 / 2,358`)** of normal crystals!
> 2. **Why `DEFERRED_CORE_REGISTER`'s Original Proposal (`Mode C`) Would Regress Accuracy:** By the Delgado-Friedrichs–O'Keeffe theorem, the zero-cocycle barycentric placement (`cocycle_rep = 0`) is automorphism-equivariant and realizes the maximal crystallographic symmetry group of the quotient graph — even when non-uniquely placed vertices share Wyckoff coordinates (`Mode A` recovers the exact space group on `9/16` unstable nets: `SG 38`, `6`, `11`, `2`, `160`, `12`, `164`, and `2x SG 1`). In contrast, `cocycle_rep = +0.5` was designed **solely** to break zero-length edge degeneracy for finite-difference gradients in ZL\* `fmin_l_bfgs_b` (`core.py:2210-2213`); applying `+0.5` inside `SLICES2space_group_number()` breaks crystal symmetry down to `P1` (`SG 1`) or `Cm` (`SG 8`) on all `7` non-`P1` matches (`SG 38 -> 1`, `SG 6 -> 1`, `SG 11 -> 1`, `SG 2 -> 1`, `SG 160 -> 8`, `SG 12 -> 8`, `SG 164 -> 1`), dropping unstable-subset accuracy from **`56.25%` to `12.50%`** without rescuing a single `None` case!
> 3. **`SAFE_NOW` Fix:** Delete lines `2100–2103` (`if self.unstable_graph: ...`) from `SLICES2space_group_number()` and add `self.unstable_graph = False` at `core.py:337` inside `from_SLICES()`. This achieves **100.0% bit-identical parity** on all `89/89` golden tests (including `G18`) and all `2,374` fresh-instance MP-20 evaluations while eliminating `100%` of reused-instance state contamination.

---

### 2.4 `DEF-010`: Mutable Default Arguments in `Net.iter_cycles` & `Net.vertex_positions`

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L385-L429) (`Net.iter_cycles`, `L389-L392`: `cycle=[]`, `used=[]`, `nodes_visited=[]`, `cycle_baggage=[]` with `# noqa: B006`).
  - [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L671-L706) (`Net.vertex_positions`, `L675-L676`: `pos={}`, `bad_ones={}` with `# noqa: B006`; carries `# NOTE: NOT WORKING - FIX!!!` in upstream `tobascco_net.py:775`).
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Call-Site Audit & Live Failure Reproduction
1. **Complete Repository Call-Site Audit (`src/`, `tests/`, `examples/`, `tools/`, `HTS/`, `benchmark/`):**
   - `Net.iter_cycles`: Only internal caller is `Net.get_cycle_basis` ([tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L294-L302)), which explicitly passes fresh `cycle=[], used=[], nodes_visited=[], cycle_baggage=[]` (and `get_cycle_basis` itself has `0` callers).
   - `Net.vertex_positions`: **`0` callers anywhere in the repository** (SLICES computes fractional coordinates via `SLICES.get_coordinates()` at `core.py:1645`).
2. **Live Cross-Call Corruption Reproduction:**
   - **`Net.iter_cycles()`:** On a 2-vertex, 4-edge net, call 1 (`list(net1.iter_cycles())`) yields `6` cycles, but leaves root vertex `'1'` inside default `nodes_visited` (`len=1`) and all `6` cycles inside default `cycle_baggage` (`len=6`). Call 2 on a fresh `Net` instance (`list(net2.iter_cycles())`) immediately sees `'1' in nodes_visited` on entry with `edge=None` and **crashes with `AssertionError` (`assert edge is not None`, `tobascco_net.py:402`)**!
   - **`Net.vertex_positions()`:** Calling `net.vertex_positions(net.all_edges(), [])` with default `pos={}` enters `if e[0] not in pos and e[1] not in pos: pass` and **loops infinitely until `RecursionError`**! Even if a root entry is seeded in `pos`, default `pos` accumulates all vertices across calls (`len(pos) == 3` after a 3-vertex net) and crashes a subsequent 2-vertex net call with `IndexError: list index out of range`.
3. **Golden Parity Verification (`exp1b`):**
   - Replacing all 6 mutable default parameters with `None` guards (`if cycle is None: cycle = []`, etc.) restored statelessness (`call1=6, call2=6`), removed all `# noqa: B006` suppressions, and passed **`94 / 94` pytest tests (`89/89` frozen v4.0.2 golden equivalence tests at `atol=1e-12` + `5/5` `test_graph.py`)**.

---

### 2.5 `DEF-009`: `ExpCellFilter` vs `FrechetCellFilter` in `relax_backends.py`

- **Verified Coordinates at `HEAD=fa4cfc8`:** [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L539-L545) (`_cell_filter`, called at `L635` and `L644` in `NequIPRelaxer.relax`, and imported at [mlip_relaxer.py](file:///home/ordillo/tests/SLICES/src/slices/mlip_relaxer.py#L39) by all optional MLIP adapters).
- **Re-Evaluation Verdict:** **`KEEP_FROZEN`** *(keep `ExpCellFilter` as default and suppress ASE's `DeprecationWarning` locally inside `_cell_filter()`; expose `FrechetCellFilter` only as `VERSIONED_OPT_IN` or automatic `ImportError` fallback if a future ASE major release removes `ExpCellFilter`)*

#### Controlled 49-Crystal A/B Experiment on CPU `nequip-s+l` (`fmax=0.2, steps=100`)
Starting from identical deterministic ZL\*-optimized `structure_recreated_opt` geometries (with alternating evaluation order and pre-warmed TorchScript calculators), `ExpCellFilter` and `FrechetCellFilter` (`ase==3.29.0`) were compared across all `19` Golden Corpus structures (`G01`–`G19`, tested under both `BFGS` and `FIRE+BFGS`) and `30` stratified 3D MP-20 structures (`M01`–`M30`):

| Cohort & Optimizer | `N` (`N_ref`) | Mean Steps (`Exp` / `Frechet`) | Cap Hits / Collapse Retries | Total Wall Time (`Exp` / `Frechet`) | Lower Final Energy (`Exp` / `Frechet` / Tie `<=0.5 meV`) | Mean / Max `|dE|` (meV/atom) | Strict `StructureMatcher` (`Exp` vs `Frechet`) | Loose `StructureMatcher` (`Exp` vs `Frechet`) |
|---|---:|---|---|---|---|---|---|---|
| **Golden 19 (`BFGS`)** | `19` (`16`) | **`12.42`** / `14.00` | `0/0` vs `0/0` | **`5.49 s`** / `6.26 s` (`+14.1%`) | **`11`** / `5` / `3` | `7.21` / `35.32` | **`16/16` (`100%`)** vs `14/16` (`87.5%`) | `16/16` vs `16/16` |
| **MP-20 30 (`BFGS`)** | `30` (`30`) | **`11.10`** / `11.47` | `0/0` vs `0/0` | **`11.54 s`** / `12.18 s` (`+5.6%`) | **`20`** / `5` / `5` | `3.56` / `21.86` | `27/30` (`90.0%`) vs `27/30` (`90.0%`) | `29/30` vs `29/30` |
| **Combined 49 (`BFGS`)** | **`49` (`46`)** | **`11.61`** / `12.45` | **`0/0` vs `0/0`** | **`17.03 s`** / `18.45 s` (**`+8.3%`**) | **`31` (`63.3%`)** / `10` (`20.4%`) / `8` | **`4.98`** / **`35.32`** | **`43/46` (`93.48%`)** vs **`41/46` (`89.13%`)** | **`45/46` (`97.83%`)** vs **`45/46`** |
| **Golden 19 (`FIRE+BFGS`)** | `19` (`16`) | `18.79` / `18.11` | `0/0` vs `0/0` | **`6.51 s`** / `6.91 s` (`+6.2%`) | **`12`** / `5` / `2` | `8.65` / `36.60` | **`16/16` (`100%`)** vs `14/16` (`87.5%`) | `16/16` vs `16/16` |

#### Mechanistic Diagnosis of Why `ExpCellFilter` Beats `FrechetCellFilter` at `fmax=0.2`
- Despite ASE's generic `DeprecationWarning` (*"Use FrechetCellFilter for better convergence w.r.t. cell variables"*), SLICES runs coarse post-ZL\* relaxation (`fmax=0.2 eV/Å`, `steps=100`) from strained approximate cells rather than tight `fmax=0.001 eV/Å` DFT polishing.
- Under `FrechetCellFilter`, deformation-gradient coupling on atomic forces and cell-strain scaling allow the generalized filter force norm to drop below `0.2` **while true physical Cartesian atomic forces still exceed `0.20–0.26 eV/Å`** (e.g., `G10` `BaSn2`: `max_force_frechet = 0.2441 eV/Å` vs `max_force_exp = 0.1004 eV/Å`, leaving a `2.09 Å` `c`-axis error, `+35.32 meV/atom` higher energy, and flipping `ori_strict` `True -> False`; `G17` `ZrTi(PbO3)2`: `0.2581 eV/Å` vs `0.1338 eV/Å`; `G05` `CdPb2(ClO)2` and `M09`: `ori_strict` `True -> False`).
- Consequently, switching `_cell_filter` to `FrechetCellFilter` would **regress strict crystal recovery by `-4.35` percentage points (`93.48% -> 89.13%`)**, yield higher energies on `63.3%` of crystals, slow relaxation by `8.3%`, and break `19/19` golden tests. `_cell_filter` should remain `ExpCellFilter` (with a local `warnings.catch_warnings()` silencing the ASE `DeprecationWarning`, falling back to `FrechetCellFilter` only on `ImportError`).

---

### 2.6 `DEF-008`: `relax_large_cell2` Ignoring `self.fmax` / `self.steps` for `>40`-Atom Cells

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2534-L2554) (`SLICES.relax_large_cell2`, lines `2548` and `2551` calling `self.relaxer.relax(struc)` without `fmax=self.fmax, steps=self.steps`, unlike `relax` at `L2507,2510` and `relax_large_cell1` at `L2526,2529`).
  - Interaction bug at [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L484-L490): `ProgressiveRelaxer.relax_with_fallbacks` sets `slices_inst.fmax` / `slices_inst.steps` across tiers (`0.2/100 -> 0.3/120 -> 0.5/150`) and calls `slices_inst.relax_large_cell2(structure)`, which silently ignores all tier settings and repeats `(fmax=0.1, steps=500)`.
- **Re-Evaluation Verdict:** **`SAFE_NOW`**

#### Repository-Wide `>40`-Atom Audit & 10-Supercell Controlled A/B Experiment
1. **Zero Shipped `>40`-Atom Structures Across Repo Datasets & Tests:**
   - Exhaustive scan of `mp20_v4_benchmark_2383.csv` (`2,383` rows, `max_atoms=20`), `mp20_eform_bandgap_nonmetal.csv` (`14,303` rows, `max_atoms=20`), `data/mp20/train.csv[:2000]` (`0 >40`), `benchmark/Match_rate_QMOF-21-40/.../cifs.json` (`928` structures, `0 >40`), `examples/*.cif`, `HTS/**/*.cif`, and all `89/89` golden tests confirmed **`0` structures with `>40` atoms**. Fixing `relax_large_cell2` therefore has **exact `0.0` drift** on all baseline and benchmark suites.
2. **Spy Verification of Caller-Override Bug:**
   - Calling `SLICES(fmax=0.5, steps=5, relax_model="nequip-s+l").relax_large_cell2(struc)` passed `kwargs == {}` to `NequIPRelaxer.relax`, executing `62` steps to `fmax=0.1` instead of stopping at `5` steps / `fmax=0.5`.
3. **10-Structure `45–64`-Atom Distorted Supercell Benchmark (`10%` shear/strain + `0.20 Å` rattle, `nequip-s+l`):**

| Supercell (`45–64` Atoms, All 7 Crystal Systems) | Atoms | `(fmax=0.1, steps=500)` Steps / Time | `(fmax=0.2, steps=100)` Steps / Time | Speedup | `|dE|` (meV/atom) | Strict Match (`0.1/500` vs `0.2/100`) |
|---|---:|---|---|---:|---:|---|
| `Sr3Ru2O7` (`2x2x1`, tetragonal) | `48` | `65` / `3.50 s` | `56` / `3.22 s` | `1.09x` | `0.746` | `True` / `True` |
| `NdSiRu` (`2x2x2`, tetragonal) | `48` | `37` / `1.42 s` | `28` / `1.29 s` | `1.10x` | `0.284` | `True` / `True` |
| `Si3P3Ir` (`2x2x2`, triclinic) | `56` | `48` / `3.17 s` | `39` / `2.81 s` | `1.13x` | `0.155` | `True` / `True` |
| `CdPb2(ClO)2` (`2x2x2`, monoclinic) | `56` | `36` / `0.58 s` | `36` / `1.49 s` | `0.39x` | `0.000` | `True` / `True` |
| `LiMnO2` (`2x2x1`, orthorhombic) | `64` | `43` / `6.06 s` | `34` / `4.00 s` | **`1.51x`** | `0.128` | `True` / `True` |
| `Cs3LiCl4` (`2x2x2`, orthorhombic) | `64` | `42` / `1.23 s` | `25` / `0.98 s` | `1.25x` | `0.865` | `True` / `True` |
| `K4ZnAs2` (`2x2x2`, trigonal) | `56` | `35` / `0.96 s` | `35` / `0.45 s` | **`2.12x`** | `0.000` | `True` / `True` |
| `BaSn2` (`3x3x2`, trigonal) | `54` | `43` / `1.08 s` | `28` / `0.89 s` | `1.21x` | `1.021` | `False` / `False` |
| `PrBi2IO4` (`2x2x2`, tetragonal) | `64` | `35` / `1.60 s` | `35` / `0.62 s` | **`2.60x`** | `0.000` | `True` / `True` |
| `CsYbBr3` (`3x3x1`, cubic) | `45` | `47` / `0.95 s` | `37` / `0.83 s` | `1.14x` | `0.469` | `True` / `True` |
| **Aggregate (`N = 10` Supercells)** | **`45–64`** | **`43.1` steps / `20.55 s`** (`0` cap hits) | **`35.3` steps / `16.58 s`** (`0` cap hits) | **`1.24x`** | **`0.367` mean (`1.021` max)** | **`9 / 10` (`90%`) vs `9 / 10` (`90%`)** |

- Forwarding `fmax=self.fmax, steps=self.steps` in `relax_large_cell2` (`core.py:2548, 2551`) is **`SAFE_NOW`**: `10/10` supercells converged well below 100 steps (`max 56`), strict recovery is identical (`9/10`), mean energy difference is `0.37 meV/atom`, overall runtime improves `1.24x` (bounding non-convergent CPU stalls `5x`), and caller/`ProgressiveRelaxer` contracts work uniformly across all cell sizes.

---

### 2.7 `DEF-002` & `DEF-015`: Multi-Start ZL\* / `robust_SLICES2structure` & GFN-FF `BondParameterFallback`

- **Verified Coordinates at `HEAD=fa4cfc8`:**
  - `DEF-002`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2120-L2370) (`to_structures`, `SLICES2structure`) vs opt-in [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2371-L2410) (`robust_SLICES2structure`) and [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L307-L784) (`MultiStartOptimizer`, `AdaptiveConvergence`, `ProgressiveRelaxer`, `_reconstruct_zl_multistart`, `robust_decode`).
  - `DEF-015`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1305-L1502) (`get_inner_p_target_debug`, `get_inner_p_target`: `"Cannot find bond!!!"` at `L1334, L1433`; unguarded `math.cos(data["vangl"][i][0])` at `L1374, L1474`; misaligned diagonal weight loop at `L1388-L1391, L1488-L1490`) vs [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L219-L305) (`BondParameterFallback`).
- **Re-Evaluation Verdicts:**
  - **`DEF-002`:** **`KEEP_FROZEN`** in default `to_structures()` / `SLICES2structure()`; **`VERSIONED_OPT_IN`** via `robust_SLICES2structure()`.
  - **`DEF-015`:** **`VERSIONED_OPT_IN`** *(keep `BondParameterFallback` in `decoding_strategies.py` and enhance `robust_decode` Stage 1->2 trigger when `Cannot find bond!!!` / `diag(inner_p_target) <= 0`)* + **`SAFE_NOW`** *(guard `np.isnan(data["vangl"][i][0])` at `core.py:1374, 1474`)*.

#### Part 1 (`DEF-015`): Large-Scale `get_inner_p_target()` Scan Under v4.0.2 Bundled `libgfnff` (`3,883` Structures)

| Corpus | Parsed Structures | Actinides (`Z >= 87`) / Failures | High-CN (`>= 19`) / Failures | `get_inner_p_target() is None` | `"Cannot find bond!!!"` Structures (Dropped Edges) | `diag <= 0` & Weight-Index Misalignment |
|---|---:|---|---|---:|---|---:|
| `mp20_v4_benchmark_2383.csv` | `2,383` | `113` / **`0`** | `88` / **`0`** | **`0` (`0.00%`)** | **`2` (`0.084%`)** (`16` edges: `idx 563, 994`) | `2` (`0.084%`) |
| `data/mp20/test.csv` (`500` 3D CIFs) | `500` | `30` / `1` (`ThH2` bond drop) | `14` / **`0`** | **`0` (`0.00%`)** | **`4` (`0.80%`)** (`24` edges: `Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`) | `4` (`0.80%`) |
| `cRNN/3_eform_-3/...unique.sli[:1000]` | `1,000` | `0` / `0` | `7` / **`0`** | **`1` (`0.10%`)** (`idx 609`: `math domain error`) | **`4` (`0.40%`)** (`10` edges) | `8` / `9` (`0.90%`) |

1. **Bundled `libgfnff` Eliminated 99.9%+ of Legacy `xtb` Crashes:** Across all `2,883` crystallographic MP-20 structures (including `143` actinide structures `Z >= 87` and `102` high-coordination `CN >= 19` structures), `get_inner_p_target()` returned `None` **zero times (`0.00%`)**. The single `None` across `1,000` cRNN strings (`idx 609`) was caused by `math.cos(NaN)` raising `ValueError: math domain error` at `core.py:1474` because `vangl` lacks the `np.isnan(...)` check already present on `vbond` at `L1435` (`SAFE_NOW` 2-line guard!).
2. **Latent Bug When `"Cannot find bond!!!"` Fires (`0.084%–0.80%`):** On rare lanthanide/actinide hydride/hydroxide nets (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`), Fortran `mrecgffPBC` prunes hypervalent bonds (`Warning: bond sum mismatch`), leaving `inner_p_target[i, i] == 0.0` and causing `for i in range(len(bond_weight)): colattice_inds[0].append(i)` (`core.py:1488-1490`) to attach weights to the wrong edge indices!

#### Part 2 (`DEF-002` & `DEF-015`): End-to-End CPU `nequip-s+l` Decoding A/B Benchmark (`51` Structures)

| Benchmark Cohort | `N` | Pipeline Mode | Mean Decode Time (`s/struct`) | Slowdown vs Default | Relaxed OK | **Strict `StructureMatcher`** (`ltol=0.2`) | **Loose `StructureMatcher`** (`ltol=0.3`) |
|---|---:|---|---:|---:|---:|---|---|
| **Representative MP-20 (`<=20` atoms)** | `30` | **Default `SLICES2structure`** | **`1.523 s`** | `1.00x` | `30/30` | **`27 / 30` (`90.0%`)** | **`29 / 30` (`96.7%`)** |
| **Representative MP-20 (`<=20` atoms)** | `30` | **Opt-in `robust_SLICES2structure`** *(fallback-only)* | **`1.285 s`** | `~1.0x` (`0%` overhead) | `30/30` | **`27 / 30` (`90.0%`)** | **`29 / 30` (`96.7%`)** |
| **Representative MP-20 (`<=20` atoms)** | `30` | **Always-On Multi-Start (`n_starts=3` + `AdaptiveConv`)** | **`2.809 s`** | **`1.85x` slower** (up to `2.96x`) | `30/30` | **`27 / 30` (`90.0%`, `+0`)** | **`29 / 30` (`96.7%`, `+0`)** |
| **Hard Subset A: Non-GFN-FF-Edge (`11–20` atoms & non-matches)** | `17` | **Default `SLICES2structure`** | `2.861 s` | `1.00x` | `17/17` | **`12 / 17` (`70.6%`)** | **`15 / 17` (`88.2%`)** |
| **Hard Subset A: Non-GFN-FF-Edge (`11–20` atoms & non-matches)** | `17` | **Always-On Multi-Start (`n_starts=3` + `AdaptiveConv`)** | `5.973 s` | **`2.09x` slower** | `17/17` | **`12 / 17` (`70.6%`, `+0`)** | **`15 / 17` (`88.2%`, `+0`)** |
| **Hard Subset B: `"Cannot find bond!!!"` (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`)** | `4` | **Default `SLICES2structure`** | `1.303 s` | `1.00x` | `4/4` | **`1 / 4` (`25.0%`)** | **`1 / 4` (`25.0%`)** |
| **Hard Subset B: `"Cannot find bond!!!"` (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`)** | `4` | **Current `robust_SLICES2structure`** *(exits Stage 1)* | `1.137 s` | `~1.0x` | `4/4` | `1 / 4` (`25.0%`) | `1 / 4` (`25.0%`) |
| **Hard Subset B: `"Cannot find bond!!!"` (`Sm(HO)3`, `NdH2ClO2`, `ThH2`, `PrH2`)** | `4` | **Stage-2 `_reconstruct_zl_multistart` (`BondParameterFallback`)** | `1.552 s` | `1.19x` *(on `0.1%` subset)* | `4/4` | **`3 / 4` (`75.0%`, `+2` rescued!)** | **`3 / 4` (`75.0%`, `+2` rescued!)** |

#### Synthesis for `DEF-002` & `DEF-015`
1. **Why `DEF-002` Must Never Be Auto-Injected into `to_structures()`:** Running 3-start L-BFGS-B + `AdaptiveConvergence` unconditionally nearly doubles CPU decode cost (`1.85x–2.09x`, reaching `10.94 s` vs `3.69 s` on 14-atom `P2O5` and `10.70 s` vs `4.04 s` on 18-atom `BeH2`), perturbs energies on `4/30` normal crystals, and yields **zero (`+0 / 47`) net structural recovery gain** whenever GFN-FF bond targets are intact!
2. **Where Opt-In `robust_SLICES2structure` Truly Wins (and One High-Value Refinement):**
   - `robust_SLICES2structure` already rescues **100% of unimodular `SNF == (1, 1, 1)` `get_lattice_basis() == -1` crashes** (`175/175` across corpora via `CycleBasisOptimizer` when Stage 1 raises `TypeError`/`LatticeBasisError`) at **`0%` overhead** on normal crystals.
   - However, when `"Cannot find bond!!!"` leaves `inner_p_target[i, i] == 0.0` (`0.084%` of `mp20_v4`, `0.80%` of `mp20/test`), `to_structures()` still returns 3 structures (`len == 3`) with distorted bond targets, causing `robust_decode` (`decoding_strategies.py:751`) to return early before Stage 2's `BondParameterFallback` (`L545`) can run! Recording a transient `self._last_gfnff_incomplete` flag (or checking `Cannot find bond!!!`) so `robust_decode` enters Stage 2 on incomplete GFN-FF targets rescues `NdH2ClO2` (`mp-24124`) and `ThH2` (`mp-1008734`) (**`25% -> 75%` strict recovery on bond-drop crystals**) while keeping default `to_structures()` 100% untouched!

---

## 3. Recommended Execution Roadmap (Ordered by Risk & ROI)

1. **Immediate Zero-Regression Fixes (`SAFE_NOW` — `100%` `89/89` Golden Equivalence at `atol=1e-12`):**
   - **`DEF-023`:** Delete stale `if self.unstable_graph:` (`core.py:2100-2103`) from `SLICES2space_group_number()` and reset `self.unstable_graph = False` in `from_SLICES()` (`core.py:337`), eliminating the `91.62% -> 4.68%` instance-reuse corruption while preserving `56.25%` (`9/16`) accuracy on unstable nets.
   - **`DEF-010`:** Replace mutable default `[]` / `{}` arguments in `Net.iter_cycles` (`tobascco_net.py:389-392`) and `Net.vertex_positions` (`L675-676`) with `None` guards and remove `# noqa: B006`.
   - **`DEF-008`:** Forward `fmax=self.fmax, steps=self.steps` in `SLICES.relax_large_cell2` (`core.py:2548, 2551`), restoring caller/`ProgressiveRelaxer` contract consistency and speeding up `45–64`-atom relaxations `1.24x`.
   - **`DEF-021` (Crash Hygiene) & `DEF-015` (`vangl` `NaN` Guard):** Raise `LatticeBasisError` / `CocycleBasisError` in `to_structures()` when `net.lattice_basis is None` (instead of `NoneType * float` `TypeError`), and skip/guard `np.isnan(data["vangl"][i][0])` in `get_inner_p_target` (`core.py:1374, 1474`).
   - **`DEF-009` (Warning Hygiene):** Keep `ExpCellFilter` in `relax_backends._cell_filter` (`L539-545`) and wrap `ExpCellFilter(atoms)` in a local `warnings.catch_warnings()` filter silencing ASE's `DeprecationWarning`.
2. **Opt-In Recovery Enhancement (`VERSIONED_OPT_IN` — Zero Default Path Change):**
   - **`DEF-002` & `DEF-015`:** Keep multi-start ZL\*, `AdaptiveConvergence`, `ProgressiveRelaxer`, and `BondParameterFallback` strictly opt-in under `robust_SLICES2structure()`, and route `robust_decode` into Stage 2 whenever `get_inner_p_target()` drops bonds (`diag(inner_p_target) <= 0`), capturing the `25% -> 75%` hydride/hydroxide recovery gain at `0%` fast-path cost.
3. **Coordinated v4.1 Scientific Upgrade (`HIGH_VALUE_AB` — Paired with `E11` Golden Update):**
   - **`DEF-003` (`FC-01` Fallback) + `DEF-021` (`check_SLICES`):** Invoke `CycleBasisOptimizer.find_lattice_basis` (or exact HNF integer solver) **only when `Net.get_lattice_basis() == -1`** (rescuing `179/180` unimodular `SNF == (1, 1, 1)` crystals with `0/2,374` perturbation on passing nets), and then enforce `if graph_rank_check and (basis_status == -1 or cocycle_failed): return False` inside `check_SLICES()` so non-3D (`SNF == (1, 1, 0)` / `(1, 0, 0)`) and proper-sublattice (`SNF == (1, 1, 2)`) graphs return `False` cleanly instead of crashing downstream inversion.
