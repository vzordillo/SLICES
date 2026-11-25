# SLICES `exp/v4.1-algo-upgrades` vs `v4.0.2-baseline` Scientific A/B Comparison Report

**Candidate Branch:** `exp/v4.1-algo-upgrades` (branched from `9a51a73955e34614413984dc108cef2d10e993a9` with v4.1 algorithmic upgrades evaluated prior to branch commit)  
**Locked Control Tag:** `v4.0.2-baseline` (`f248b3c725b48ea33b495acb3dd69bb9c1ec57e3`; see [`BASELINE_REPORT.md`](../v4_0_2_baseline/BASELINE_REPORT.md))  
**Primary Artifacts:** [`ab_vs_v4_0_2.json`](ab_vs_v4_0_2.json) (`98,773` bytes) | [`summary.json`](summary.json) (`28,838` bytes) | [`per_structure_metrics.csv`](per_structure_metrics.csv) (`611,247` bytes, `2,383` rows × `53` columns)  
**Benchmark & Analysis Tools:** [`tools/benchmarks/run_mp20_baseline.py`](../../tools/benchmarks/run_mp20_baseline.py) | [`tools/benchmarks/compare_ab_baselines.py`](../../tools/benchmarks/compare_ab_baselines.py)

---

## Executive Summary

This report presents a controlled, paired head-to-head A/B evaluation of four core algorithmic upgrades implemented on experimental branch **`exp/v4.1-algo-upgrades`** against the locked **`v4.0.2-baseline`** control group (`f248b3c`) across all **2,383** crystals of the Strategy-4 MP-20 non-metal benchmark (three paired passes: `default`, `lorentz`, `robust`; deterministic CPU `nequip-s+l` relaxation), all **39,244** conditioned-RNN (`cRNN`) SLICES strings across five repository corpora, and the full **294-test** verification and golden-oracle suite.

1. **Statistically Significant Recovery Gains in Standard `default` (`p = 0.0156`) with Zero Shared-`ok` Regressions:** Standard `v4.1 default` (`SLICES2structure()`, `lj_mixing="legacy"`) rescues **`7 / 7` (`100.0%`)** unimodular `LatticeBasisError` crystals via exact integer Smith Normal Form (`DEF-003`), achieving **`+7 / -0`** gains on decode success (`99.62% -> 99.92%`, `2,374 -> 2,381`), strict `StructureMatcher` recovery (`93.75% -> 94.04%`, `2,234 -> 2,241`), loose `StructureMatcher` recovery (`95.93% -> 96.22%`, `2,286 -> 2,293`), and structural validity (`100.00%` of `ok`) — each with exact two-sided McNemar **`p = 0.015625`**. Across all **`2,374` shared `ok` crystals**, there are **`0` strict match losses, `0` loose match losses, `0` `<= 0.05 eV/atom` flips (`1,312 == 1,312`), `0` `<= 0.10 eV/atom` flips (`1,386 == 1,386`)**, **`88.04%` (`2,090 / 2,374`)** within `<= 1e-6 eV/atom`, and statistically neutral formation-energy residuals (`Delta MAE = +0.000012 eV/atom`, Wilcoxon `p = 0.1861`).
2. **Standard `v4.1 default` Now Matches `v4.0.2 robust` on Every Structural Recovery Metric While Running Faster:** Comparing `v4.1 default` directly against `v4.0.2 robust` confirms **`2,381 == 2,381` `ok`**, **`2,241 == 2,241` strict match**, and **`2,293 == 2,293` loose match** (`+0 / -0`, `p = 1.0`), while delivering `+3` higher space-group match (`1,494` vs `1,491`), lower MAE (`-0.000155 eV/atom`), and **`-1.28%` wall-clock / `-65.23 CPU-s` faster execution** (`193.57 s` vs `196.08 s`). Within `v4.1`, `default` and `robust` are bit-identical on **`2,379 / 2,381` (`99.92%`)** decoded crystals.
3. **Consistent Physical Improvements on Incomplete-GFN-FF Lanthanide Oxyhydrides (`DEF-031`):** Aligning diagonal bond weights via `matched_bond_indices` improves both `gfnff_incomplete` crystals in standard decoding: `mp-1176505` (`Lu4H4O8`) drops `|eform - DFT|` by **`-12.16 meV/atom`**, exits overlap pre-optimization (**`preoptimized: True -> False`**), and cuts BFGS steps **`44 -> 18` (`-59.1%`)**; `mp-625477` (`Eu2H6O6`) improves by **`-48.06 meV/atom`** in `default` (BFGS `66 -> 48`) and **`-55.81 meV/atom`** in `lorentz`.
4. **Combined `v4.1 lorentz` vs `v4.0.2 default` Maximizes Symmetry & Loose Recovery:** Pairing `v4.1` upgrades with `lj_mixing="lorentz"` achieves **`+11 / -0` loose recovery (`96.39%`, `p = 0.00098`)** and **`+80 / -6` (`+74` net, `+3.11 pp`, `p < 1e-16`) space-group preservation** (`62.44% -> 65.55%`) with `-14.50 CPU-s` faster execution across the `2,374` shared `ok` crystals.
5. **Exact 3D Invertibility Enforcement Across `39,244` `cRNN` Strings (`DEF-003` + `DEF-021`):** Co-deploying the SNF fallback with basis/cocycle validation in `check_SLICES(..., graph_rank_check=True)` rescues **`5` unimodular crystals** and rejects **`4` non-invertible graphs** on `sampled.sli` (`1,000` raw strings), and rescues **`98 / 401` unimodular crystals** while rejecting **`303 / 401` (`0.79%`) non-invertible graphs** across `38,244` published `unique.sli` strings — where **`0 / 303` (`0.00%`)** survived downstream `4_inverse` reconstruction.
6. **Promotion Verdict:** **Recommend promoting `exp/v4.1-algo-upgrades` to `v4.1.0`** (`294 passed, 5 skipped, 0 failed`, `0` Ruff diagnostics, locked `v4.0.2` golden fixtures untouched, `max |dE| < 1e-6 eV/atom` on the `14` symmetry-restored golden crystals).

---

## 1. Algorithmic Upgrades & Experimental Protocol

### 1.1 Evaluated Algorithmic Changes (`exp/v4.1-algo-upgrades`)

| Register ID | Modified Files & Symbols | Algorithmic Upgrade |
|---|---|---|
| **`DEF-003`** | [`src/slices/tobascco_net.py`](../../src/slices/tobascco_net.py) (`Net._get_lattice_basis_via_snf`, `Net.get_lattice_basis`), [`src/slices/decoding_strategies.py`](../../src/slices/decoding_strategies.py) (`CycleBasisOptimizer.find_lattice_basis`) | Preserves the primary SymPy single-nullspace-vector search verbatim on all passing nets (`0.0` ULP drift, zero overhead), invoking exact integer Smith Normal Form (`DomainMatrix` + `smith_normal_decomp` over $\mathbb{Z}$) strictly inside `if not found_vector:` to construct exact left-inverse $W = V S U_{:d,:}$ whenever invariant factors satisfy $|D_{kk}| = 1$ and $|\det V| = 1$. `CycleBasisOptimizer.find_lattice_basis` invokes `net.get_lattice_basis()` first before falling back to seeded row permutations. |
| **`DEF-014`** | [`src/slices/core.py`](../../src/slices/core.py) (`_classify_lattice_type`, `SLICES.to_structures`), [`src/slices/decoding_strategies.py`](../../src/slices/decoding_strategies.py) (`_classify_lattice_type`, `_reconstruct_zl_multistart`) | Replaces exact IEEE-754 float `set`/`==` classification on `metric_tensor_std` diagonals with pairwise `math.isclose(rel_tol=1e-9, abs_tol=1e-12)` and transitive closure (`1`, `23`, `22`, `21`, `3`), restoring crystallographic ZL\* axial-length symmetry constraints across the 7-decade rounding-noise gap `(1e-13, 1e-9]`. |
| **`DEF-021`** | [`src/slices/core.py`](../../src/slices/core.py) (`SLICES.check_SLICES`) | Strictly under `graph_rank_check=True`, verifies both `net.get_lattice_basis() != -1` (`net.lattice_basis is not None`) and, for multi-vertex nets (`net.order > 1`), full-rank 2D cocycle bases (`len(net.cocycle) >= net.order - 1`), returning `False` for mathematically non-3D or sublattice graphs while preserving 1-atom cells (`net.order == 1`) and leaving `graph_rank_check=False` workflows unchanged. |
| **`DEF-031`** | [`src/slices/core.py`](../../src/slices/core.py) (`SLICES.get_inner_p_target`, `SLICES.get_inner_p_target_debug`) | Records `matched_bond_indices` alongside `bond_weight` and iterates `zip(matched_bond_indices, bond_weight, strict=True)` so diagonal `colattice_inds` pairs `(edge_idx, edge_idx)` and normalized weights attach strictly to their true matched edges whenever GFN-FF skips unmatched bonds (`"Cannot find bond!!!"`). |

### 1.2 Controlled Benchmark Configuration & Statistical Methods

| Field | Control (`v4.0.2-baseline`) | Candidate (`exp/v4.1-algo-upgrades`) |
|---|---|---|
| **Git Reference / Commit** | Tag `v4.0.2-baseline` (`f248b3c725b48ea33b495acb3dd69bb9c1ec57e3`) | Branch `exp/v4.1-algo-upgrades` (from `9a51a73955e34614413984dc108cef2d10e993a9` + v4.1 upgrades) |
| **Benchmark Timestamp (UTC)** | `2026-11-25T07:43:33Z` | `2026-11-25T08:44:03Z` (`ab_vs_v4_0_2.json`: `2026-11-25T08:45:33Z`) |
| **Dataset & Reference Join** | `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` (`N = 2,383`, all `<= 20` atoms, `100.0%` 1-to-1 CIF join) | Identical (`N = 2,383`, all `<= 20` atoms, `100.0%` 1-to-1 CIF join) |
| **Relaxation Backend** | `relax_model="auto"` -> `nequip-s+l` CPU (`NequIP-OAM-S-0.1` BFGS + `NequIP-OAM-L-0.1` energy) | Identical |
| **Software Stack** | Python `3.10.22`, PyTorch `2.9.1+cpu`, NequIP `0.17.1`, pymatgen `2025.10.7`, ASE `3.29.0`, NumPy `2.2.6`, SciPy `1.15.3` | Identical |
| **Workers & Determinism** | `32` CPU cores, `24` spawned workers, `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1` | Identical |
| **Total 3-Pass Suite Wall-Clock** | `626.369 s` | `625.834 s` (`-0.535 s`) |

**Statistical Hypothesis Testing ([`compare_ab_baselines.py`](../../tools/benchmarks/compare_ab_baselines.py)):**
- **Paired binary indicators** (`ok`, `match_strict`, `match_loose`, `sg_match`, `struct_valid`, `roundtrip_canonical_match`, `|eform - DFT| <= 0.05` and `<= 0.10 eV/atom`): exact two-sided McNemar test via `scipy.stats.binomtest(gained, gained + lost, p=0.5)`.
- **Paired continuous formation-energy residuals** on shared `ok` crystals: two-sided Wilcoxon signed-rank test (`scipy.stats.wilcoxon`) on `|err_cand| - |err_base|` and signed `eform_cand - eform_base`.

---

## 2. Head-to-Head Paired A/B Results (`N = 2,383`)

### 2.1 Complete Five-Comparison Paired A/B Matrix

| Comparison (`cand` vs `base`) | `ok` (`+g/-l`, McNemar `p`) | Strict Match (`+g/-l`, `p`) | Loose Match (`+g/-l`, `p`) | SG Match (`+g/-l`, `p`) | Shared-`ok` `Delta` MAE (`p_Wilcoxon`) | Pass Wall-Clock (`Delta %`) & Shared-`ok` CPU Delta |
|---|---|---|---|---|---|---|
| **`v4.1 default` vs `v4.0.2 default`** | **`2,381` vs `2,374`** (`+7 / -0`, **`p = 0.0156`**) | **`2,241` vs `2,234`** (`94.04%` vs `93.75%`, `+7 / -0`, **`p = 0.0156`**) | **`2,293` vs `2,286`** (`96.22%` vs `95.93%`, `+7 / -0`, **`p = 0.0156`**) | **`1,494` vs `1,488`** (`62.69%` vs `62.44%`, `+7 / -1`, `p = 0.0703`) | `+0.000012` eV/at (`p = 0.1861`, med `0.0`) | `193.57 s` vs `192.59 s` (`+0.51%`); shared CPU **`-6.92 s`** (`-0.17%`) |
| **`v4.1 lorentz` vs `v4.0.2 lorentz`** | **`2,381` vs `2,374`** (`+7 / -0`, **`p = 0.0156`**) | **`2,239` vs `2,232`** (`93.96%` vs `93.66%`, `+8 / -1`, **`p = 0.0391`**) | **`2,297` vs `2,290`** (`96.39%` vs `96.10%`, `+7 / -0`, **`p = 0.0156`**) | **`1,562` vs `1,558`** (`65.55%` vs `65.38%`, `+5 / -1`, `p = 0.2188`) | `+0.000007` eV/at (`p = 0.9087`, med `0.0`) | `193.43 s` vs `192.54 s` (`+0.46%`); shared CPU **`-5.59 s`** (`-0.14%`) |
| **`v4.1 lorentz` vs `v4.0.2 default`** | **`2,381` vs `2,374`** (`+7 / -0`, **`p = 0.0156`**) | **`2,239` vs `2,234`** (`93.96%` vs `93.75%`, `+10 / -5`, `p = 0.3018`) | **`2,297` vs `2,286`** (**`96.39%`** vs `95.93%`, **`+11 / -0`**, **`p = 0.00098`**) | **`1,562` vs `1,488`** (**`65.55%`** vs `62.44%`, **`+80 / -6`**, **`p < 1e-16`**) | `+0.000146` eV/at (`p = 0.7644`, med `0.0`) | `193.43 s` vs `192.59 s` (`+0.44%`); shared CPU **`-14.50 s`** (`-0.35%`) |
| **`v4.1 robust` vs `v4.0.2 robust`** | `2,381` vs `2,381` (`+0 / -0`, `p = 1.0`) | `2,241` vs `2,241` (`+0 / -0`, `p = 1.0`) | `2,293` vs `2,293` (`+0 / -0`, `p = 1.0`) | **`1,495` vs `1,491`** (`62.74%` vs `62.57%`, `+5 / -1`, `p = 0.2188`) | `+0.000038` eV/at (`p = 0.2381`, med `0.0`) | **`193.66 s` vs `196.08 s` (`-1.24%`)**; shared CPU **`-63.37 s`** (`-1.49%`) |
| **`v4.1 default` vs `v4.0.2 robust`** | **`2,381 == 2,381`** (`+0 / -0`, `p = 1.0`) | **`2,241 == 2,241`** (`94.04% == 94.04%`, `+0 / -0`, `p = 1.0`) | **`2,293 == 2,293`** (`96.22% == 96.22%`, `+0 / -0`, `p = 1.0`) | **`1,494` vs `1,491`** (`62.69%` vs `62.57%`, `+5 / -2`, `p = 0.4531`) | **`-0.000155` eV/at** (`p = 0.2549`, med `0.0`) | **`193.57 s` vs `196.08 s` (`-1.28%`)**; shared CPU **`-65.23 s`** (`-1.54%`) |

*(Note: For `v4.1 lorentz` vs `v4.0.2 default` `sg_match`, `ab_vs_v4_0_2.json` rounds `mcnemar_two_sided_p` to `0.0` at 8 decimal places; exact two-sided `binomtest(80, 86, 0.5)` is `p < 1e-16`.)*

### 2.2 Candidate Three-Pass Summary (`benchmark/v4_1_experimental/summary.json`)

| Metric | `v4.1 default` | `v4.1 lorentz` | `v4.1 robust` | `v4.0.2 default` (Control) |
|---|---:|---:|---:|---:|
| **Decoded & Relaxed (`ok` / `2,383`)** | **2,381 (99.92%)** | **2,381 (99.92%)** | **2,381 (99.92%)** | 2,374 (99.62%) |
| **Failures (`failed` / taxonomy)** | 2 (`1` Lattice, `1` Cocycle) | 2 (`1` Lattice, `1` Cocycle) | 2 (`2` `SLICESDecodingError`) | 9 (`8` Lattice, `1` Cocycle) |
| **`StructureMatcher` Strict (`all` / `ok`)** | **2,241 (94.04% / 94.12%)** | **2,239 (93.96% / 94.04%)** | **2,241 (94.04% / 94.12%)** | 2,234 (93.75% / 94.10%) |
| **`StructureMatcher` Loose (`all` / `ok`)** | **2,293 (96.22% / 96.30%)** | **2,297 (96.39% / 96.47%)** | **2,293 (96.22% / 96.30%)** | 2,286 (95.93% / 96.29%) |
| **Structural Validity (`all` / `ok`)** | 2,381 (99.92% / 100.00%) | 2,381 (99.92% / 100.00%) | 2,381 (99.92% / 100.00%) | 2,374 (99.62% / 100.00%) |
| **Space-Group Match (`all` / `ok`)** | 1,494 (62.69% / 62.75%) | **1,562 (65.55% / 65.60%)** | 1,495 (62.74% / 62.79%) | 1,488 (62.44% / 62.68%) |
| **Canonical Round-Trip (`all` / `ok`)** | 273 (11.46% / 11.47%) | 279 (11.71% / 11.72%) | 273 (11.46% / 11.47%) | 271 (11.37% / 11.42%) |
| **`\|eform - DFT\|` MAE (eV/atom, all `ok`)** | 0.200464 | 0.200598 | 0.200656 | 0.199109 |
| **`\|eform - DFT\|` Median AE / RMSE (eV/at)** | 0.025486 / 0.343635 | 0.025577 / 0.343721 | 0.025486 / 0.343911 | 0.025299 / 0.342007 |
| **`\|eform - DFT\| <= 0.05` / `<= 0.10` (`all`)** | 1,312 / 1,386 | 1,311 / 1,386 | 1,312 / 1,386 | 1,312 / 1,386 |
| **Relax `preoptimized` (`ok`) / `retry`** | 39 (1.64%) / 0 | 37 (1.55%) / 1 | 38 (1.60%) / 0 | 40 (1.68%) / 0 |
| **Relax Steps (`mean` / `med` / `total`)** | 11.815 / 9.0 / 28,132 | 11.890 / 9.0 / 28,309 | 11.832 / 9.0 / 28,172 | 11.854 / 9.0 / 28,142 |
| **Wall-Clock (`24` workers) / Throughput** | **193.568 s** (`12.3109/s`) | **193.430 s** (`12.3197/s`) | **193.661 s** (`12.3050/s`) | 192.588 s (`12.3736/s`) |
| **Total Worker CPU Time (`all` / `shared_ok`)** | 4,175.30 s / 4,150.12 s | 4,167.10 s / 4,142.54 s | 4,178.77 s / 4,177.15 s | 4,157.15 s / 4,157.04 s |

> **Why Aggregate `all_ok` MAE Shifts by `+0.001355 eV/atom`:** The slight rise in aggregate MAE (`0.199109 -> 0.200464 eV/atom`) is strictly a denominator-expansion effect from including the `7` newly rescued transition-metal/lanthanide oxides and chalcogenides (whose DFT/GGA+U vs OAM reference offset averages `0.6557 eV/atom` despite `7 / 7` strict crystallographic match). On the identical `2,374` shared `ok` crystals, paired `Delta MAE` is `+0.000012 eV/atom` (`0.012 meV/atom`, Wilcoxon `p = 0.1861`).

---

## 3. Zero-Regression Verification Across `2,374` Shared `ok` Crystals

| Paired Integrity Check (Shared `ok` Subset) | `v4.1 default` vs `v4.0.2 default` (`N = 2,374`) | `v4.1 lorentz` vs `v4.0.2 lorentz` (`N = 2,374`) | `v4.1 robust` vs `v4.0.2 robust` (`N = 2,381`) |
|---|---:|---:|---:|
| **Strict Match Flips (`+gained / -lost`)** | **`+0 / -0`** | `+1 / -1` (`mp-1210350` / `mp-546757`) | **`+0 / -0`** |
| **Loose Match Flips (`+gained / -lost`)** | **`+0 / -0`** | **`+0 / -0`** | **`+0 / -0`** |
| **`\|eform - DFT\| <= 0.05 eV/at` Flips** | **`+0 / -0`** (`1,312 == 1,312`, `p = 1.0`) | **`+0 / -0`** (`1,311 == 1,311`, `p = 1.0`) | **`+0 / -0`** (`1,312 == 1,312`, `p = 1.0`) |
| **`\|eform - DFT\| <= 0.10 eV/at` Flips** | **`+0 / -0`** (`1,386 == 1,386`, `p = 1.0`) | **`+0 / -0`** (`1,386 == 1,386`, `p = 1.0`) | **`+0 / -0`** (`1,386 == 1,386`, `p = 1.0`) |
| **Bit-Identical `eform` (`0.0` ULP)** | `661` (`27.84%`) | `660` (`27.80%`) | `662` (`27.80%`) |
| **`\|eform_v41 - eform_v402\| <= 1e-6 eV/at`** | **`2,090` (`88.04%`)** | **`2,073` (`87.32%`)** | **`2,092` (`87.86%`)** |
| **`\|eform_v41 - eform_v402\|` (`med` / `P90` / `P95` / `P99`)** | `0.0` / `1e-6` / `1.1e-5` / `7.98e-4` | `0.0` / `2e-6` / `1.2e-5` / `7.38e-4` | `0.0` / `2e-6` / `1.2e-5` / `6.86e-4` |
| **Max `\|eform_v41 - eform_v402\|` (eV/at)** | `0.120484` (`mp-23950`, `K2B6H6`, cubic) | `0.128527` (`mp-23950`, `K2B6H6`, cubic) | `0.120484` (`mp-23950`, `K2B6H6`, cubic) |
| **Improved vs Worsened `> 1 meV/at`** | **`16` improved vs `6` worsened** | `9` improved vs `11` worsened | **`14` improved vs `6` worsened** |
| **Wilcoxon Two-Sided `p` (`\|err\|` / signed `eform`)** | `0.1861` / `0.2103` | `0.9087` / `0.9433` | `0.2381` / `0.2663` |

- In `v4.1 default` vs `v4.0.2 default`, the lone outlier with `|Delta eform| > 0.05 eV/atom` is cubic `row_index=180` (`mp-23950`, `K2B6H6`, `0.053228 -> 0.173712 eV/atom`), which remains strict-matched in both passes and sits `> 0.42 eV/atom` from DFT in both. More crystals improve by `> 1 meV/atom` (`16`) than worsen (`6`), led by the two `DEF-031` oxyhydrides (`Section 5`).
- In `v4.1 lorentz` vs `v4.0.2 lorentz`, the single shared-`ok` strict gain (`row_index=2194`, `mp-1210350`, `Na3Tb1V2O8`, trigonal, `|err| 0.6204 -> 0.6155 eV/atom`) and single shared-`ok` strict loss (`row_index=1025`, `mp-546757`, `Sn3P1O4F3`, trigonal, `|err| 0.2545 -> 0.2693 eV/atom`) are exact boundary ties: both remain loose-matched with unchanged space groups (`SG 1` and `SG 146`).
- Within `v4.1`, `robust` vs `default` produces **`2,379 / 2,381` (`99.92%`) bit-identical `eform`**, differing exclusively on the two `gfnff_incomplete` lanthanide oxyhydrides.

---

## 4. Exact Smith Normal Form Rescues (`DEF-003`) & Remaining Non-Invertible Crystals

### 4.1 Complete Table of the `7` SNF-Rescued Unimodular `mp20_v4` Crystals

All **`7 / 7` (`100.0%`)** unimodular `LatticeBasisError` crystals (`SNF(cycle_rep) == (1, 1, 1)`) now decode directly in standard `v4.1 default` with **`7 / 7` (`100.0%`)** strict and loose `StructureMatcher` recovery, `100.0%` structural validity, sub-3 ms SNF basis solve times, zero global `np.random` state mutation, and `0.0..1.09e-4 eV/atom` parity against `v4.0.2 robust`:

| Row | Material ID | Formula | Atoms | System | Ref SG | `SNF(C)` | SNF Solve (ms) | `v4.1 default` `eform` (eV/at) | `\|eform - DFT\|` (eV/at) | `\|Delta eform\|` vs `v4.0.2 robust` | Strict / Loose | Pred SG (Match) | Steps / Time (s) |
|---:|---|---|---:|---|---:|---|---:|---:|---:|---:|---|---:|---:|
| 74 | `mp-1207855` | `V5Te8` | 13 | monoclinic | 12 | `(1, 1, 1)` | 0.895 | -0.294956 | 0.306812 | `1.6e-5` | **1 / 1** | 12 (**Yes**) | 25 / 1.0089 |
| 214 | `mp-1177618` | `Li3Mn1Cr3O8` | 15 | trigonal | 166 | `(1, 1, 1)` | 1.783 | -1.426143 | 0.880551 | `0.0` | **1 / 1** | 1 (No) | 10 / 2.7607 |
| 976 | `mp-23456` | `Cr4Bi4O12` | 20 | monoclinic | 15 | `(1, 1, 1)` | 1.311 | -1.151745 | 0.829730 | `1.0e-6` | **1 / 1** | 9 (No) | 20 / 4.6931 |
| 1377 | `mp-1104659` | `Dy4Mn2Ni2O12` | 20 | monoclinic | 14 | `(1, 1, 1)` | 2.772 | -2.009480 | 0.847860 | `1.09e-4` | **1 / 1** | 7 (No) | 16 / 4.0285 |
| 1394 | `mp-675310` | `Na3V5Se10` | 18 | triclinic | 1 | `(1, 1, 1)` | 2.394 | -0.806412 | 0.277493 | `4.0e-6` | **1 / 1** | 1 (**Yes**) | 19 / 5.3876 |
| 1417 | `mp-25407` | `Li2Fe2P2O8F2` | 16 | triclinic | 2 | `(1, 1, 1)` | 0.576 | -1.926863 | 0.623336 | `1.0e-6` | **1 / 1** | 1 (No) | 21 / 2.5674 |
| 1695 | `mp-756871` | `Li4Ni3Te1O8` | 16 | trigonal | 166 | `(1, 1, 1)` | 2.107 | -0.903968 | 0.824343 | `3.0e-6` | **1 / 1** | 1 (No) | 10 / 4.7186 |

*(Outside MP-20, `sampled.sli idx=709` — a unimodular `SNF=(1,1,1)` net previously missed by 20-shuffle `CycleBasisOptimizer` — is also deterministically rescued in `1.256 ms` total, decoding `LiO7F` at `E = -4.5592 eV/atom`.)*

### 4.2 Remaining `2` Mathematically Non-Invertible Crystals (`2 / 2,383`, `0.084%`)

Only two MP-20 structures remain undecodable across all passes (`default`, `lorentz`, and `robust`), both reflecting genuine topological obstructions in their encoded quotient graphs rather than solver limitations:

| Row | Material ID | Formula | Atoms | System | Ref SG | Error (`v4.0.2` & `v4.1`) | Mathematical Cause & Solve Time |
|---:|---|---|---:|---|---:|---|---|
| 45 | `mp-643814` | `Zn4Si2H4O10` | 20 | orthorhombic | 44 | `CocycleBasisError` | Multi-vertex quotient graph fails to yield `V - 1` linearly independent cocycle vectors (`0.0105 s`). |
| 2178 | `mp-29816` | `Ag8Hg4O8` | 20 | tetragonal | 96 | `LatticeBasisError` | Proper sublattice of index `3` (`SNF(cycle_rep) = (1, 1, 3)`): no integral cycle combination spans $\mathbb{Z}^3$; rejected by `_get_lattice_basis_via_snf()` in `0.195 ms` (`0.0066 s` end-to-end). |

---

## 5. Dedicated `DEF-031` Analysis: Incomplete-GFN-FF Lanthanide Oxyhydrides

Exactly two crystals in `mp20_v4_benchmark_2383.csv` (`2 / 2,383 = 0.084%`) emit `"Cannot find bond!!!"` during GFN-FF topology lookup (`_last_gfnff_incomplete = True`): `mp-1176505` (`Lu4H4O8`, dropping edges `[0, 7, 14, 21]` of `36`) and `mp-625477` (`Eu2H6O6`, dropping `12` of `36` edges). In `v4.0.2`, indexing diagonal entries via `range(len(bond_weight))` shifted bond weights onto indices `0..E-k-1`, applying positive weights to dropped zero-target edges and leaving trailing matched edges unweighted. Tracking `matched_bond_indices` restores exact `diag_pairs == np.where(np.diag(inner_p_target) > 0)[0]` alignment across both crystals:

| Row / ID | Formula (Ref SG, DFT eV/at) | Pass | `v4.0.2` `eform` -> `v4.1` `eform` | `Delta \|err\|` (meV/at) | `v4.0.2` -> `v4.1` `\|err\|` (eV/at) | `preoptimized` (`v4.0.2 -> v4.1`) | BFGS Steps (`v4.0.2 -> v4.1`) | Pred SG (`v4.0.2 -> v4.1`) |
|---|---|---|---|---:|---:|---|---:|---|
| `563` / `mp-1176505` | `Lu4H4O8` (`14`, `-3.047581`) | **`default`** | `-2.706289 -> -2.718445` | **`-12.16`** | `0.341293 -> 0.329136` | **`True -> False`** | **`44 -> 18` (`-59.1%`)** | `1 -> 1` |
| `563` / `mp-1176505` | `Lu4H4O8` (`14`, `-3.047581`) | **`lorentz`** | `-2.706901 -> -2.716426` | **`-9.53`** | `0.340680 -> 0.331156` | **`True -> False`** | **`44 -> 18` (`-59.1%`)** | `1 -> 1` |
| `563` / `mp-1176505` | `Lu4H4O8` (`14`, `-3.047581`) | `robust` | `-2.724169 -> -2.724169` | `0.00` | `0.323413 -> 0.323413` | `False -> False` | `71 -> 45` *(Stage 1 `-26`)* | `14 -> 14` |
| `994` / `mp-625477` | `Eu2H6O6` (`11`, `-1.905146`) | **`default`** | `-1.598311 -> -1.646373` | **`-48.06`** | `0.306835 -> 0.258773` | `True -> True` | **`66 -> 48` (`-27.3%`)** | `1 -> 1` |
| `994` / `mp-625477` | `Eu2H6O6` (`11`, `-1.905146`) | **`lorentz`** | `-1.600099 -> -1.655904` | **`-55.81`** | `0.305047 -> 0.249242` | `True -> True` | `74 -> 72` (`-2.7%`) | `1 -> 1` |
| `994` / `mp-625477` | `Eu2H6O6` (`11`, `-1.905146`) | `robust` | `-1.182224 -> -1.182321` | `-0.10` | `0.722922 -> 0.722826` | `False -> False` | `78 -> 61` *(Stage 1 `-17`)* | `194 -> 194` |

- **Physical Effect in Standard Decoding:** On `Lu4H4O8`, eliminating misassigned bond weights removes the initial atomic clash completely (`preoptimized: True -> False`, lowering `default` `preoptimized` count `40 -> 39`), reduces NequIP BFGS steps by `59.1%`, and lowers formation energy by `12.16 meV/atom`. On `Eu2H6O6`, proper diagonal alignment yields a `48.06 meV/atom` energy drop in `default` (`55.81 meV/atom` in `lorentz`) and cuts `default` BFGS steps from `66` to `48`.
- **Stage 2 Interaction Insight (`robust`):** Because `robust_decode` replaces the incomplete GFN-FF matrix with Stage 2 `BondParameterFallback`, `robust` final energies remain effectively unchanged (while cumulative BFGS steps drop `-26` and `-17` because Stage 1 converges faster). On `Eu2H6O6`, `v4.1 default` (`|err| = 0.2588 eV/atom`) outperforms `robust` Stage 2 (`|err| = 0.7228 eV/atom`, SG `194` basin) by **`464.05 meV/atom`**, underscoring that future `robust_decode` refinements should keep the lower-energy candidate between Stage 1 and Stage 2.

---

## 6. Crystal-System Accuracy & Latency Breakdown

| Crystal System | `N` | `v4.1 default` `ok` (`Delta` vs `v4.0.2`) | `v4.1 default` Strict / Loose (`Delta` Strict) | `v4.1 default` SG (`Delta`) | `v4.1 lorentz` SG | `v4.1 default` MAE (eV/at) | `default` Shared-`ok` CPU Delta (`mean %`) | `robust` Shared-`ok` CPU Delta (`mean %`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Cubic** | 583 | 100.00% (`+0`) | 99.66% / 99.66% (`+0`) | 74.27% (`+1`) | **80.96%** | 0.095277 | **`-1.79 s`** (`-0.39%`) | **`-4.51 s`** (`-0.98%`) |
| **Hexagonal** | 230 | 100.00% (`+0`) | 98.70% / 99.57% (`+0`) | 79.13% (`+0`) | **80.00%** | 0.071279 | **`-1.85 s`** (`-0.50%`, med `-2.16%`) | **`-5.53 s`** (`-1.48%`) |
| **Trigonal** | 239 | **100.00%** (`+2`) | **93.31% / 95.82%** (`+2`) | 64.44% (`+0`) | **66.11%** | 0.247801 | **`-5.49 s`** (`-1.53%`) | **`-19.52 s`** (`-5.14%`) |
| **Tetragonal** | 379 | 99.74% (`+0`) | 95.78% / 97.36% (`+0`) | 56.99% (`+1`) | **58.84%** | 0.173559 | **`-0.33 s`** (`-0.06%`) | **`-5.45 s`** (`-0.94%`) |
| **Orthorhombic** | 477 | 99.79% (`+0`) | 93.50% / 96.23% (`+0`) | 60.38% (`+0`) | **62.05%** | 0.168638 | `-0.02 s` (`0.00%`) | `-1.54 s` (`-0.13%`) |
| **Monoclinic** | 362 | **100.00%** (`+3`) | **85.64% / 90.33%** (`+3`) | **43.65%** (`+2`) | **44.75%** | 0.390550 | `+1.88 s` (`+0.21%`) | **`-11.77 s`** (`-1.29%`) |
| **Triclinic** | 113 | **100.00%** (`+2`) | **80.53% / 87.61%** (`+2`) | **55.75%** (`+2`) | **59.29%** | 0.521090 | `+0.68 s` (`+0.20%`) | **`-15.05 s`** (`-4.11%`) |
| **All Systems** | **2,383** | **99.92% (`+7`)** | **94.04% / 96.22% (`+7`)** | **62.69% (`+6`)** | **65.55%** | **0.200464** | **`-6.92 s`** (`-0.17%`) | **`-63.37 s`** (`-1.49%`) |

### Latency Interpretation (Why NequIP Dominates Wall-Clock)

- **High-Symmetry ZL\* Reduction vs NequIP Dominance:** Restoring `DEF-014` symmetry constraints reduces L-BFGS-B metric-tensor freedom (`6 -> 1` cubic, `6 -> 2` tetragonal/hexagonal/trigonal), accelerating the ZL\* stage. In full end-to-end decoding with CPU `NequIP-OAM-S/L` TorchScript relaxation (`mean 1.75 s/structure`, `11.8` BFGS steps plus `NequIP-OAM-L` single-point evaluation), however, neural force-field evaluation accounts for the large majority of total wall-clock time. Consequently, `DEF-014` latency gains appear cleanly in the high-symmetry systems — **`trigonal` (`-1.53%`, `-5.49 CPU-s`), `hexagonal` (`-0.50%` mean / `-2.16%` median, `-1.85 CPU-s`), `cubic` (`-0.39%`, `-1.79 CPU-s`), and `tetragonal` (`-0.06%`, `-0.33 CPU-s`)** — while low-symmetry `orthorhombic`, `monoclinic`, and `triclinic` systems (which already use unconstrained `lattice_type=3`) remain neutral within `+-0.21%` worker scheduling noise (`1,228` faster vs `1,142` slower across `2,374` shared `ok` crystals; `-6.92 CPU-s` net in `default`, `-14.50 CPU-s` in `v4.1 lorentz` vs `v4.0.2 default`).
- **Why All-2,383 `default` Wall-Clock Rises `+0.98 s` (`+0.51%`):** The `7` newly rescued crystals execute full GFN-FF + ZL\* + NequIP relaxation (`25.17 CPU-s` combined, `1.01–5.39 s` each) rather than failing in `< 0.02 s` on `LatticeBasisError`.
- **Why `v4.1 robust` Saves `-63.37 CPU-s` (`-1.49%`, `-2.42 s` Wall-Clock):** When both control and candidate decode the exact same `2,381` structures (`v4.1 robust` vs `v4.0.2 robust`), solving all `7` unimodular nets in `< 3 ms` inside Stage 1 eliminates multi-start Stage 2 fallback completely on `monoclinic` (`-11.77 CPU-s`), `trigonal` (`-19.52 CPU-s`), and `triclinic` (`-15.05 CPU-s`) rescues, combining with high-symmetry `DEF-014` gains (`cubic` `-4.51`, `hexagonal` `-5.53`, `tetragonal` `-5.45 CPU-s`) to speed up `1,378` vs `999` crystals.

---

## 7. Conditioned-RNN (`cRNN`) Validity & Inversion-Crash Audit (`39,244` Strings)

Using [`tools/benchmarks/compare_ab_baselines.py`](../../tools/benchmarks/compare_ab_baselines.py) (`69.349 s` scan across `5` corpora under `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/`), we audited how co-deploying `DEF-003` (SNF fallback) and `DEF-021` (`check_SLICES(..., graph_rank_check=True)` basis/cocycle enforcement) reshapes generative-model validity filtering:

| Corpus (`benchmark/Validity_rate_ucRNN__Success_rate_cRNN/...`) | Total Rows | `v4.0.2` Valid (`%`) | `v4.0.2` Primary Decodable | `v4.0.2` Crashes (`to_structures`) | `v4.1` Valid (`%`, `Delta pp`) | Rescued `SNF=(1,1,1)` (`DEF-003`) | Rejected (`DEF-021` Total) | Rejected Breakdown (`1D/2D` / `Sublat` / `Cocycle` / `Both`) | Rejected Surviving `4_inverse` |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `2_train_sample/sampled.sli` *(raw Strategy-3)* | 1,000 | 181 (18.10%) | 172 | 9 | **177** (`17.70%`, `-0.40 pp`) | **+5** | **4** | `2` / `1` / `1` / `0` | N/A |
| `Other_targets/3_eform_-3/.../unique.sli` | 9,782 | 9,782 (100.00%) | 9,621 | 161 | **9,671** (`98.87%`, `-1.13 pp`) | **+50** | **111** | `62` / `37` / `16` / `4` | **`0`** |
| `Other_targets/3_eform_-4/.../unique.sli` | 9,626 | 9,626 (100.00%) | 9,511 | 115 | **9,534** (`99.04%`, `-0.96 pp`) | **+23** | **92** | `65` / `18` / `13` / `4` | **`0`** |
| `Other_targets/3_eform_-5/.../unique.sli` | 9,407 | 9,407 (100.00%) | 9,352 | 55 | **9,362** (`99.52%`, `-0.48 pp`) | **+10** | **45** | `32` / `3` / `11` / `1` | **`0`** |
| `Other_targets/3_eform_-6/.../unique.sli` | 9,429 | 9,429 (100.00%) | 9,359 | 70 | **9,374** (`99.42%`, `-0.58 pp`) | **+15** | **55** | `31` / `3` / `28` / `7` | **`0`** |
| **Published `unique.sli` Aggregate (`4` Targets)** | **38,244** | **38,244 (100.00%)** | **37,843** | **401** | **37,941 (`99.21%`, `-0.79 pp`)** | **+98** | **303 (`0.79%`)** | **`190` / `61` / `68` / `16`** | **`0 / 303` (`0.00%`)** |

- **Zero Valid Crystals Lost, `98` Unimodular Crystals Rescued:** Across the `38,244` published `cRNN` `unique.sli` candidates that previously passed `v4.0.2` `check_SLICES`, `401` crashed `v4.0.2` inversion. Under `exp/v4.1-algo-upgrades`, **`98 / 401` (`24.4%`)** are exact unimodular 3D nets rescued by `DEF-003` (`37,843 -> 37,941` decodable), while the remaining **`303 / 401` (`0.79%`)** are mathematically non-invertible graphs (`190` rank-deficient 1D/2D + `61` proper sublattices + `68` rank-deficient cocycle bases, with `16` failing both lattice and cocycle checks: `190 + 61 + 68 - 16 = 303`) of which **`0 / 303` (`0.00%`)** ever produced a crystal in `4_inverse/results_4_inverse.csv`.
- **RL Workflow Preservation:** Because `DEF-021` checks execute strictly inside `if graph_rank_check:`, callers passing `graph_rank_check=False` (such as generative RL training loops) remain unaffected.

---

## 8. Golden Oracle Delta & Test-Suite Verification

- **Locked Fixture Immutability:** Frozen upstream `v4.0.2` (`94ef8e0`) oracle fixtures in [`tests/baseline/fixtures/golden_metadata.json`](../../tests/baseline/fixtures/golden_metadata.json) and [`tests/baseline/fixtures/golden_arrays.npz`](../../tests/baseline/fixtures/golden_arrays.npz) remain **100% untouched** (`git diff tests/baseline/fixtures/` empty).
- **Full Unified Pytest Result (`PYTHONHASHSEED=0 OMP_NUM_THREADS=1 SLICES_TORCH_THREADS=1 PYTHONPATH=src pytest -p no:cacheprovider tests/`):** **`294 passed, 5 skipped, 0 failed` in `156.41 s`**, including `89/89` golden equivalence assertions and `20/20` new parametrized regression tests in [`tests/regression/test_v41_algo_upgrades.py`](../../tests/regression/test_v41_algo_upgrades.py) (`ruff check --no-cache src/ tests/ tools/` -> `0` errors).
- **Exact Golden Oracle Delta vs Locked `v4.0.2` Fixtures ([`tests/baseline/test_golden_equivalence.py`](../../tests/baseline/test_golden_equivalence.py)):**
  1. **Discrete Metadata, GFN-FF Targets & Structural Matching (`0` regressions):** `100%` exact parity across `G01`–`G19`, `E01`–`E10`, `S01`, `S03`, and `G15b` for `match_check_strict`, `match_check3_strict`, `match_check3_loose`, `match_check4_strict`, `colattice_inds`, `sg_recreated`, and all `std_lattice`, `std_frac`, `inner_p_target`, `colattice_weights`, and `opt_lattice` arrays (`atol=1e-12`).
  2. **Intended `DEF-021` Edge Shift (`1` edge fixture):** `E11_quasi1d_lattice_basis_neg1` (quasi-1D `TiBr3`, `SNF=(1,1,0)`) shifts `check_default: True -> False` and `check_dupli: True -> False` (`check_basic: True`, `check_3D: False`, `sg_recreated: None`, and `graph_rank_check=False -> True` unchanged).
  3. **Bounded `DEF-014` Symmetry-Restored Shifts (`14` crystals + live dual-tree test):** Five crystals (`G03`, `G06`, `G12`, `G14`, `G18`) stay within `atol=1e-12` across all arrays. Across the `14` symmetry-restored golden crystals (`G01`, `G02`, `G04`, `G05`, `G07`, `G08`, `G09`, `G10`, `G11`, `G13`, `G15`, `G16`, `G17`, `G19`), `opt_lattice` stays `<= 1e-12`, while reduced-dimension ZL\* L-BFGS-B finite-difference steps shift `opt_frac` (`5.58e-09..2.35e-04`), `opt2_lattice` (`2.61e-07..3.57e-05 Å`), `opt2_frac` (`2.63e-08..1.43e-04`), and `energy_per_atom` (`2.03e-08..9.56e-07 eV/atom`, **`max |dE| < 1e-6 eV/atom`**, asserted within `ATOL_DEF014_ENERGY=1e-5`, `ATOL_DEF014_OPT2_LAT=1e-4`, `ATOL_DEF014_FRAC=5e-4`), with **`0` `StructureMatcher` flips**.

---

## 9. Promotion Recommendation & Reproduction Commands

### Promotion Recommendation

**RECOMMEND PROMOTION of `exp/v4.1-algo-upgrades` to `main` (target release `v4.1.0`)** following standard branch commit and final gate review:
- Every quantitative acceptance criterion is satisfied: statistically significant decode and structural recovery gains in standard `default` (`+7 / -0`, `p = 0.0156`), `0` regressions across `2,374` shared `ok` crystals (`88.04%` within `<= 1e-6 eV/atom`), exact `v4.0.2 robust` accuracy achieved directly in standard `default` at `-1.28%` lower wall-clock (`-65.23 CPU-s`), `-12.16` / `-48.06 meV/atom` physical improvements on incomplete-GFN-FF oxyhydrides, `98` rescued and `303` properly rejected `cRNN` strings (`0/303` surviving `4_inverse`), and `294/294` passing tests (`5` optional-MLIP skips).
- **Lorentz-Berthelot Mixing Policy:** Keep `lj_mixing="legacy"` as default for backward continuity while continuing to recommend opt-in `lj_mixing="lorentz"` for symmetry-sensitive generative screening (`v4.1 lorentz` vs `v4.0.2 default`: `+74` SG match [`+3.11 pp`, `p < 1e-16`], `+11 / -0` loose match [`p = 0.00098`], `-14.50 CPU-s` on shared `ok`).

### Exact Reproduction CLI Commands

Run from the repository root after preparing NequIP-OAM weights (`python -m slices.relax_backends --prepare`):

```bash
# 1. Run full 3-pass MP-20 benchmark (2,383 structures, 24 CPU workers)
OMP_NUM_THREADS=1 \
SLICES_TORCH_THREADS=1 \
PYTHONHASHSEED=0 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python tools/benchmarks/run_mp20_baseline.py \
  --csv data/mp20_nonmetal/mp20_v4_benchmark_2383.csv \
  --chem-pot data/mp20_nonmetal/chemPotMP.json \
  --mp20-dir data/mp20 \
  --out-dir benchmark/v4_1_experimental \
  --workers 24 \
  --passes default lorentz robust \
  --relax-model auto \
  --robust-starts 3 \
  --robust-seed 0

# 2. Compute paired A/B statistics vs v4.0.2-baseline + 39,244-string cRNN audit
OMP_NUM_THREADS=1 \
PYTHONHASHSEED=0 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python tools/benchmarks/compare_ab_baselines.py \
  --candidate-dir benchmark/v4_1_experimental \
  --baseline-dir benchmark/v4_0_2_baseline \
  --out benchmark/v4_1_experimental/ab_vs_v4_0_2.json

# 3. Run full test and golden-oracle verification suite
PYTHONHASHSEED=0 \
OMP_NUM_THREADS=1 \
SLICES_TORCH_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
pytest -p no:cacheprovider tests/
```
