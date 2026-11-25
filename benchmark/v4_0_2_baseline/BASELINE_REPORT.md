# SLICES `v4.0.2-baseline` Quantitative MP-20 Benchmark Report

**Locked Reference Tag:** `v4.0.2-baseline` (`f248b3c725b48ea33b495acb3dd69bb9c1ec57e3`)  
**Benchmark Dataset:** `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` (`N = 2,383` Strategy-4 MP-20 non-metal structures)  
**Primary Artifacts:** [`summary.json`](summary.json) (`29,471` bytes) | [`per_structure_metrics.csv`](per_structure_metrics.csv) (`611,007` bytes, `2,383` rows × `53` columns)  
**Benchmark Runner:** [`tools/benchmarks/run_mp20_baseline.py`](../../tools/benchmarks/run_mp20_baseline.py)

---

## Executive Summary

This report establishes the locked quantitative control group for **SLICES v4.0.2** on git tag `v4.0.2-baseline` (`f248b3c`) across all **2,383** crystal structures of the Strategy-4 MP-20 non-metal benchmark under deterministic CPU `nequip-s+l` relaxation (`24` spawned workers, `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, `PYTHONHASHSEED=0`). Every structure (`2,383 / 2,383`) is joined 1-to-1 to its Materials Project reference CIF in `data/mp20/train.csv` to measure exact `StructureMatcher` recovery alongside DFT formation-energy accuracy, structural validity, space-group preservation, canonical round-trip consistency, and relaxation telemetry across three paired passes:

1. **`default` (locked control group — `lj_mixing="legacy"`, `SLICES2structure()`):** `2,374 / 2,383` (`99.62%`) decode success, `100.0%` structural validity among decoded crystals, **`93.75%`** (`2,234 / 2,383`) strict and **`95.93%`** (`2,286 / 2,383`) loose `StructureMatcher` recovery, `62.44%` (`1,488 / 2,383`) space-group match, and `0.199109 eV/atom` MAE (`0.025299 eV/atom` median AE) in `192.59 s` wall-clock (`12.37 struct/s`). Cross-checked against single-process [`examples/3.benchmark_relax_models.py`](../../examples/3.benchmark_relax_models.py) at **`0.000e+00` (`0` ULP)** max absolute formation-energy difference.
2. **`lorentz` (paired A/B — `lj_mixing="lorentz"`, `SLICES2structure()`):** Identical runtime (`192.54 s`, `0.9997x`), **`+70` (`+2.94 pp`) net space-group preservation gain** (`1,488 -> 1,558`, `+75` gained / `-5` lost) with gains across all 7 crystal systems led by **cubic (`74.10% -> 80.96%`, `+40` gained / `0` lost)**, **`+4 / -0` loose recovery gain** (`95.93% -> 96.10%`), **`+9` canonical round-trip gain**, and effectively neutral strict recovery (`-2` net, `+4 / -6`, with all `6` strict losses remaining loose matches) and MAE (`+0.000140 eV/atom`).
3. **`robust` (paired A/B — `lj_mixing="legacy"`, `robust_SLICES2structure(n_starts=3, seed=0)`):** Rescues **`7 / 8` (`87.5%`) `LatticeBasisError` failures** at **`+1.81%`** total wall-clock overhead (`196.08 s`, `1.0181x`), with **`7 / 7` (`100%`) rescued structures passing both strict and loose `StructureMatcher`** (`ok` `99.62% -> 99.92%`, strict `93.75% -> 94.04%`, loose `95.93% -> 96.22%`, SG match `+3 / -0`). Across the `2,374` crystals decoded by `default`, **`2,372 / 2,374` (`99.92%`) are bit-identical (`0.0` `eform` shift)**; only the `2` `gfnff_incomplete` lanthanide oxyhydrides (`Lu4H4O8`, `Eu2H6O6`) entered automatic Stage 2 fallback.

---

## 1. Study Metadata, Dataset & Verification Protocol

| Field | Verified Value |
|---|---|
| **Git Tag / Full SHA** | `v4.0.2-baseline` / `f248b3c725b48ea33b495acb3dd69bb9c1ec57e3` |
| **Package Version / UTC Timestamp** | SLICES `4.0.2` / `2026-11-25T07:43:33Z` |
| **Benchmark Dataset** | [`data/mp20_nonmetal/mp20_v4_benchmark_2383.csv`](../../data/mp20_nonmetal/mp20_v4_benchmark_2383.csv) (`2,383` rows; `1 <= n_atoms <= 20`, median `10`, mean `10.32`; `2,383` rows `<= 20` atoms, `0` rows `> 20` atoms) |
| **Chemical Potentials** | [`data/mp20_nonmetal/chemPotMP.json`](../../data/mp20_nonmetal/chemPotMP.json) |
| **Reference CIF Join** | `2,383 / 2,383` (`100.0%`, `0` missing, `0` ambiguous) 1-to-1 join against [`data/mp20/train.csv`](../../data/mp20/train.csv) (searched across `data/mp20/{train,val,test}.csv`) via `(formation_energy_per_atom, band_gap, reduced_formula)`, normalized with `SLICES.to_primitive_if_smaller` |
| **Relaxation Model** | `relax_model="auto"` -> `nequip-s+l` on CPU (`NequIP-OAM-S-0.1` TorchScript relaxation, `NequIP-OAM-L-0.1` TorchScript single-point energy, ASE `BFGS`) |
| **Software Stack** | Python `3.10.22`, PyTorch `2.9.1+cpu`, NequIP `0.17.1`, pymatgen `2025.10.7`, ASE `3.29.0`, NumPy `2.2.6`, SciPy `1.15.3` |
| **Parallelism & Determinism** | `32`-core CPU host (`cpu_count=32`); `24` spawned worker processes (`ProcessPoolExecutor` with `spawn` context, 1 cached `SLICES` instance + non-invasive `_RelaxTelemetryProxy` per worker); `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, `PYTHONHASHSEED=0`, `PYTHONDONTWRITEBYTECODE=1` |
| **Total Suite Wall-Clock** | `626.369 s` (task preparation, CIF join, all 3 full passes, and JSON/CSV archival) |
| **Single-Process Determinism Check** | `examples/3.benchmark_relax_models.py --n 10 --seed 0 --models auto`: **`0.000e+00` (`0` ULP)** max absolute `eform` difference across all `10 / 10` sampled structures vs Pass 1 (`default_eform`) |

### Evaluation Definitions

- **Structural Recovery (`StructureMatcher`):** Evaluated on POSCAR-normalized reference and relaxed structures (matching `SLICES.match_check3` conventions: `ElementComparator()`, `primitive_cell=True`, `scale=True`, `attempt_supercell=False`):
  - **Strict:** `ltol=0.2`, `stol=0.3`, `angle_tol=5`.
  - **Loose:** `ltol=0.3`, `stol=0.5`, `angle_tol=10`.
- **Formation Energy (`|eform - DFT|`):** Uses the verbatim `formation_energy()` helper from [`examples/3.benchmark_relax_models.py`](../../examples/3.benchmark_relax_models.py) (`SpacegroupAnalyzer.get_primitive_standard_structure()` composition minus elemental `chemPotMP.json` references), ensuring exact cross-script comparability.
- **Structural Validity:** `SLICES.check_structural_validity(structure)` requiring minimum interatomic distance `d > 0.5 Å` across all distinct sites and non-trivial periodic images.
- **Space-Group Match & Canonical Round-Trip:** `SpacegroupAnalyzer(structure).get_space_group_number() == ref_sg` and `get_canonical_SLICES(structure2SLICES(prim_std, strategy=4), strategy=4) == canon_in`.
- **Atom-Count Subsets:** Because all `2,383` structures satisfy `1 <= n_atoms <= 20`, the `all_structures` and `subset_le_20_atoms` blocks in [`summary.json`](summary.json) are identical.

---

## 2. Three-Pass Quantitative Summary (`N = 2,383`)

| Metric | Pass 1: `default` (`legacy` + `SLICES2structure`) | Pass 2: `lorentz` (`lorentz` + `SLICES2structure`) | Pass 3: `robust` (`legacy` + `robust_SLICES2structure(3, 0)`) |
|---|---:|---:|---:|
| **Decoded & Relaxed (`ok` / `2,383`)** | **2,374 (99.62%)** | **2,374 (99.62%)** | **2,381 (99.92%)** |
| **Failures (`failed` / unrelaxed fallback)** | 9 / 0 | 9 / 0 | 2 / 0 |
| **Failure Taxonomy** | `8` `LatticeBasisError`, `1` `CocycleBasisError` | `8` `LatticeBasisError`, `1` `CocycleBasisError` | `2` `SLICESDecodingError` |
| **`StructureMatcher` Strict (`all` / `ok`)** | **2,234 (93.75% / 94.10%)** | **2,232 (93.66% / 94.02%)** | **2,241 (94.04% / 94.12%)** |
| **`StructureMatcher` Loose (`all` / `ok`)** | **2,286 (95.93% / 96.29%)** | **2,290 (96.10% / 96.46%)** | **2,293 (96.22% / 96.30%)** |
| **Structural Validity (`all` / `ok`)** | 2,374 (99.62% / 100.00%) | 2,374 (99.62% / 100.00%) | 2,381 (99.92% / 100.00%) |
| **Space-Group Match (`all` / `ok`)** | 1,488 (62.44% / 62.68%) | **1,558 (65.38% / 65.63%)** | 1,491 (62.57% / 62.62%) |
| **Canonical SLICES Round-Trip (`all` / `ok`)** | 271 (11.37% / 11.42%) | 280 (11.75% / 11.79%) | 271 (11.37% / 11.38%) |
| **`\|eform - DFT\|` MAE (eV/atom)** | **0.199109** | 0.199249 | 0.200619 |
| **`\|eform - DFT\|` Median AE (eV/atom)** | **0.025299** | 0.025488 | 0.025486 |
| **`\|eform - DFT\|` RMSE / Std AE (eV/atom)** | 0.342007 / 0.278072 | 0.342120 / 0.278112 | 0.343856 / 0.279265 |
| **`\|eform - DFT\|` P90 / P95 / Max (eV/atom)** | 0.623470 / 0.847180 / 1.620774 | 0.626548 / 0.847119 / 1.620774 | 0.629667 / 0.848342 / 1.620774 |
| **Mean Signed Error `eform - DFT` (eV/atom)** | +0.194767 | +0.194846 | +0.196290 |
| **`\|eform - DFT\| <= 0.05 eV/atom` (`ok` / `all`)** | 1,312 (55.27% / 55.06%) | 1,311 (55.22% / 55.01%) | 1,312 (55.10% / 55.06%) |
| **`\|eform - DFT\| <= 0.10 eV/atom` (`ok` / `all`)** | 1,386 (58.38% / 58.16%) | 1,386 (58.38% / 58.16%) | 1,386 (58.21% / 58.16%) |
| **Relax `preoptimized` (`ok`)** | 40 (1.68%) | 40 (1.68%) | 38 (1.60%) |
| **Relax `retry` (structs / total / `% ok`)** | 0 / 0 / 0.00% | 1 / 1 / 0.04% | 0 / 0 / 0.00% |
| **Relax Steps (`mean` / `med` / `P90` / `P95` / `max`)** | 11.854 / 9.0 / 23.0 / 29.35 / 100 | 11.864 / 9.0 / 22.7 / 29.0 / 200 | 11.887 / 9.0 / 23.0 / 29.0 / 100 |
| **Total Relax Steps (`sum`)** | 28,142 | 28,165 | 28,303 |
| **`gfnff_incomplete` Count (`all`)** | 2 (0.084%) | 2 (0.084%) | 2 (0.084%) |
| **Wall-Clock (`24` workers) / Throughput** | **192.588 s** (`12.3736/s`) | **192.536 s** (`12.3769/s`) | **196.083 s** (`12.1530/s`) |
| **Per-Structure Latency `mean` / `med` (s)** | 1.7445 / 1.1666 | 1.7408 / 1.1553 | 1.7802 / 1.1762 |
| **Per-Structure Latency `P90` / `P95` / `P99` / `max` (s)** | 4.1209 / 5.0781 / 7.0855 / 12.5618 | 4.1629 / 5.0372 / 6.8992 / 12.6258 | 4.1795 / 5.1964 / 7.4518 / 15.8573 |
| **Total Worker CPU Time (`sum_cpu_s`)** | 4,157.15 s | 4,148.23 s | 4,242.15 s |

> **Formation-Energy Error Profile:** Across all three passes, the median absolute error is low (`0.0253–0.0255 eV/atom`, with `55.1–55.3%` within `0.05 eV/atom`), whereas MAE (`~0.199 eV/atom`) closely tracks the systematic positive mean signed bias (`+0.1948 eV/atom` in `default`, where `1,920 / 2,374 = 80.88%` of residuals are positive). This offset reflects DFT/GGA+U reference-energy compatibility shifts relative to OAM-trained NequIP potentials on transition-metal oxides and halides rather than geometric failure; `StructureMatcher` strict/loose recovery therefore serves as the primary geometric fidelity metric alongside formation-energy percentiles.

---

## 3. Crystal-System Breakdown

Rates below are expressed over all `N` structures in each crystal system (`*_rate_all` in [`summary.json`](summary.json)), ordered from highest to lowest lattice symmetry:

| Crystal System | `N` | `default` `ok` | `default` Strict / Loose | `default` SG Match | `default` MAE (eV/at) | `lorentz` Strict / Loose | `lorentz` SG Match (`Delta`) | `robust` `ok` (`Delta`) | `robust` Strict / Loose (`Delta` Strict) | `robust` SG Match (`Delta`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Cubic** | 583 | 100.00% | 99.66% / 99.66% | 74.10% (432) | 0.095072 | 99.66% / 99.66% | **80.96% (472, +40)** | 100.00% (+0) | 99.66% / 99.66% (+0) | 74.10% (+0) |
| **Hexagonal** | 230 | 100.00% | 98.70% / 99.57% | 79.13% (182) | 0.071291 | 98.70% / 99.57% | 79.57% (183, +1) | 100.00% (+0) | 98.70% / 99.57% (+0) | 79.13% (+0) |
| **Trigonal** | 239 | 99.16% | 92.47% / 94.98% | 64.44% (154) | 0.242714 | 92.47% / 95.40% | 65.69% (157, +3) | **100.00% (+2)** | **93.31%** / 95.82% (+2) | 64.44% (+0) |
| **Tetragonal** | 379 | 99.74% | 95.78% / 97.36% | 56.73% (215) | 0.173566 | 95.78% / 97.36% | 58.84% (223, +8) | 99.74% (+0) | 95.78% / 97.36% (+0) | 56.73% (+0) |
| **Orthorhombic** | 477 | 99.79% | 93.50% / 96.23% | 60.38% (288) | 0.168664 | 93.29% / 96.44% | 62.26% (297, +9) | 99.79% (+0) | 93.50% / 96.23% (+0) | 60.38% (+0) |
| **Monoclinic** | 362 | 99.17% | 84.81% / 89.50% | 43.09% (156) | 0.388485 | 84.81% / 90.06% | 44.48% (161, +5) | **100.00% (+3)** | **85.64%** / 90.33% (+3) | 43.65% (+2) |
| **Triclinic** | 113 | 98.23% | 78.76% / 85.84% | 53.98% (61) | 0.522339 | 77.88% / 85.84% | 57.52% (65, +4) | **100.00% (+2)** | **80.53%** / 87.61% (+2) | 54.87% (+1) |
| **All Systems** | **2,383** | **99.62%** | **93.75% / 95.93%** | **62.44% (1,488)** | **0.199109** | **93.66% / 96.10%** | **65.38% (1,558, +70)** | **99.92% (+7)** | **94.04% / 96.22% (+7)** | **62.57% (+3)** |

### Key Crystal-System Observations

- **Cubic Space-Group Preservation Jump (`lorentz`):** Replacing asymmetric legacy heteronuclear Lennard-Jones parameters with exact Lorentz-Berthelot arithmetic mixing improves space-group preservation in **all 7 crystal systems** (`+75` gained / `-5` lost = `+70` net), with the largest single improvement in **cubic crystals (`74.10% -> 80.96%`, `+6.86 pp`, `+40` gained / `0` lost)**, followed by orthorhombic (`+9`), tetragonal (`+8`), monoclinic (`+5`), triclinic (`+4`), trigonal (`+3`), and hexagonal (`+1`). Eliminating atom-order-dependent steric bias prevents asymmetric ZL\* lattice shear prior to NequIP relaxation.
- **Low-Symmetry Decoding Recovery (`robust`):** `default` decode failures concentrate in lower-symmetry lattices (`3` monoclinic, `2` triclinic, `2` trigonal, `1` orthorhombic, `1` tetragonal; `0` cubic/hexagonal). `robust` raises decode success to **`100.00%`** in **monoclinic** (`+3`), **triclinic** (`+2`), and **trigonal** (`+2`) systems, converting every rescued structure into a strict `StructureMatcher` hit (`monoclinic` `84.81% -> 85.64%`, `triclinic` `78.76% -> 80.53%`, `trigonal` `92.47% -> 93.31%`).

---

## 4. Failure Taxonomy, Rescued Crystals & Incomplete GFN-FF Cases

### 4.1 Complete Inventory of the 9 `default` / `lorentz` Failures and `robust` Outcomes

Both `default` and `lorentz` fail on the exact same `9` structures (`8` `LatticeBasisError` + `1` `CocycleBasisError`). Under `robust`, `7 / 8` (`87.5%`) `LatticeBasisError` cases are rescued with **`7 / 7` (`100%`) strict and loose `StructureMatcher` recovery** and `100%` structural validity; `2` structures remain `SLICESDecodingError`:

| Row | Material ID | Formula | Atoms | System | Ref SG | `default` / `lorentz` Error | `robust` Outcome | Strict / Loose | Pred SG (Match) | `robust` `\|eform - DFT\|` (eV/at) | Steps / Time (s) |
|---:|---|---|---:|---|---:|---|---|---|---:|---:|---:|
| 45 | `mp-643814` | `Zn4Si2H4O10` | 20 | orthorhombic | 44 | `CocycleBasisError` | **Failed** (`SLICESDecodingError`) | — | — | — | 0 / 1.5682 |
| 74 | `mp-1207855` | `V5Te8` | 13 | monoclinic | 12 | `LatticeBasisError` | **Rescued** | **1 / 1** | 12 (**Yes**) | 0.306796 | 26 / 2.0226 |
| 214 | `mp-1177618` | `Li3Mn1Cr3O8` | 15 | trigonal | 166 | `LatticeBasisError` | **Rescued** | **1 / 1** | 1 (No) | 0.880551 | 10 / 8.0535 |
| 976 | `mp-23456` | `Cr4Bi4O12` | 20 | monoclinic | 15 | `LatticeBasisError` | **Rescued** | **1 / 1** | 9 (No) | 0.829729 | 20 / 10.3262 |
| 1377 | `mp-1104659` | `Dy4Mn2Ni2O12` | 20 | monoclinic | 14 | `LatticeBasisError` | **Rescued** | **1 / 1** | 7 (No) | 0.847969 | 16 / 9.1729 |
| 1394 | `mp-675310` | `Na3V5Se10` | 18 | triclinic | 1 | `LatticeBasisError` | **Rescued** | **1 / 1** | 1 (**Yes**) | 0.277489 | 19 / 15.8573 |
| 1417 | `mp-25407` | `Li2Fe2P2O8F2` | 16 | triclinic | 2 | `LatticeBasisError` | **Rescued** | **1 / 1** | 1 (No) | 0.623335 | 21 / 5.9076 |
| 1695 | `mp-756871` | `Li4Ni3Te1O8` | 16 | trigonal | 166 | `LatticeBasisError` | **Rescued** | **1 / 1** | 1 (No) | 0.824346 | 10 / 12.3956 |
| 2178 | `mp-29816` | `Ag8Hg4O8` | 20 | tetragonal | 96 | `LatticeBasisError` | **Failed** (`SLICESDecodingError`) | — | — | — | 0 / 0.0565 |

### 4.2 Incomplete GFN-FF Bond-Target Cases (`2 / 2,383`, `0.084%`)

Exactly two monoclinic lanthanide oxyhydrides trigger `_last_gfnff_incomplete = True` across all three passes (dropped bond targets during GFN-FF topology generation). Under `robust`, these are the **only two** crystals among the `2,374` shared-`ok` structures that enter automatic Stage 2 recovery (`BondParameterFallback` + Lorentz-Berthelot multi-start ZL\* + `ProgressiveRelaxer`):

| Row | Material ID | Formula | Atoms | Ref SG | Pass | `eform` (eV/at) | `\|eform - DFT\|` (eV/at) | Strict / Loose | Pred SG (Match) | `preopt` | Steps / Time (s) |
|---:|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|
| 563 | `mp-1176505` | `Lu4H4O8` | 16 | 14 | `default` | -2.706289 | 0.341293 | 0 / 0 | 1 (No) | 1 | 44 / 3.8085 |
| 563 | `mp-1176505` | `Lu4H4O8` | 16 | 14 | `lorentz` | -2.706901 | 0.340680 | 0 / 0 | 1 (No) | 1 | 44 / 4.3807 |
| 563 | `mp-1176505` | `Lu4H4O8` | 16 | 14 | `robust` | -2.724169 | **0.323413** (`-17.88 meV`) | 0 / 0 | **14 (Yes)** | **0** | 71 / 14.6028 |
| 994 | `mp-625477` | `Eu2H6O6` | 14 | 11 | `default` | -1.598311 | 0.306835 | 0 / 0 | 1 (No) | 1 | 66 / 2.4264 |
| 994 | `mp-625477` | `Eu2H6O6` | 14 | 11 | `lorentz` | -1.600099 | 0.305047 | 0 / 0 | 1 (No) | 1 | 74 / 2.5675 |
| 994 | `mp-625477` | `Eu2H6O6` | 14 | 11 | `robust` | -1.182224 | 0.722922 (`+416.09 meV`) | 0 / 0 | 194 (No) | **0** | 78 / 6.3982 |

- Both oxyhydrides exit overlap pre-optimization (`preoptimized: 1 -> 0`) under Stage 2 fallback, accounting for the full `40 -> 38` reduction in `preoptimized` count between `default` and `robust`.
- On `mp-1176505` (`Lu4H4O8`), Stage 2 lowers energy by `17.88 meV/atom` and recovers reference space group `14`; on `mp-625477` (`Eu2H6O6`), Stage 2 converges to a higher-energy hexagonal-like basin (`SG 194`, `+416.09 meV/atom`), demonstrating that comparing Stage 1 vs Stage 2 candidate energies before accepting Stage 2 is a concrete target for future robust-decoding refinement.

---

## 5. Paired A/B Analysis (`lorentz` vs `default` and `robust` vs `default`)

| Paired Metric | `lorentz` vs `default` | `robust` vs `default` |
|---|---:|---:|
| **`Delta ok` (`both_true` / `gained` / `lost` / `both_false`)** | **0** (`2,374` / `+0` / `-0` / `9`) | **+7** (`2,374` / **`+7`** / `-0` / `2`) |
| **`Delta match_strict` (`both_true` / `gained` / `lost` / `both_false`)** | **-2** (`2,228` / `+4` / `-6` / `145`) | **+7** (`2,234` / **`+7`** / `-0` / `142`) |
| **`Delta match_loose` (`both_true` / `gained` / `lost` / `both_false`)** | **+4** (`2,286` / **`+4`** / `-0` / `93`) | **+7** (`2,286` / **`+7`** / `-0` / `90`) |
| **`Delta sg_match` (`both_true` / `gained` / `lost` / `both_false`)** | **+70** (`1,483` / **`+75`** / `-5` / `820`) | **+3** (`1,488` / **`+3`** / `-0` / `892`) |
| **`Delta roundtrip_canonical_match`** | **+9** (`271 -> 280`) | **0** (`271 -> 271`) |
| **Shared `ok` Count / Bit-Identical `eform` Count** | `2,374` / `807` (`33.99%`) | `2,374` / **`2,372` (`99.92%`)** |
| **Shared `ok` `\|eform_cand - eform_base\|` (`mean` / `med` / `P90` / `P95` / `max`)** | `0.000474` / `0.0` / `0.000172` / `0.000692` / `0.135226` | `0.000183` / `0.0` / `0.0` / `0.0` / `0.416087` |
| **Shared `ok` `Delta \|err\|` (`mean` / `med` / improved `>1 meV` / worsened `>1 meV`)** | `+0.000140` / `0.0` / `38` / `47` | `+0.000168` / `0.0` / `1` / `1` |
| **Aggregate `Delta` MAE / Median AE / RMSE (eV/atom)** | `+0.000140` / `+0.000189` / `+0.000113` | `+0.001510` / `+0.000187` / `+0.001849` |
| **Per-Structure Seconds Delta (`mean` / `med` / `P90` / `P95`)** | `-0.0037` / `-0.0014` / `+0.0971` / `+0.1727` | `+0.0357` / `0.0000` / `+0.0755` / `+0.1242` |
| **Wall-Clock Ratio (`cand / default`)** | **`0.9997x`** (`-0.03%`) | **`1.0181x`** (`+1.81%`) |

### Paired Interpretation

- **`lorentz` vs `default`:** Switching `lj_mixing` to `"lorentz"` incurs zero wall-clock overhead (`0.9997x`) and delivers substantial symmetry preservation (`+70` SG matches, `+2.94 pp`) alongside `+4 / -0` loose recovery (`mp-1189965`, `mp-568864`, `mp-1219514`, `mp-556375`) and `+9` canonical round-trip hits. On strict matching, `4` crystals are gained (`mp-546757`, `mp-568864`, `mp-556375`, `mp-753360`) and `6` are lost (`mp-1190287`, `mp-1188869`, `mp-3879`, `mp-755188`, `mp-1210350`, `mp-1188309`), with **all `6 / 6` strict losses remaining loose matches**. One monoclinic structure (`row 1753`, `mp-753510`, `Sb6O8F2`) triggered a cell-collapse retry (`retry=1`, `200` total steps vs `100` in `default`; unmatched in both passes).
- **`robust` vs `default`:** Opt-in multi-start decoding adds only `+1.81%` wall-clock cost (`0.0000 s` median per-structure delta) while yielding strictly monotonic structural improvements (`+7 / -0` on decode success, strict match, loose match, and structural validity; `+3 / -0` on space-group match). Its `0.001510 eV/atom` higher aggregate MAE is fully explained by (1) denominator expansion from the `7` newly rescued transition-metal/lanthanide oxide and chalcogenide crystals (mean `|eform - DFT| = 0.655745 eV/atom`, all `7/7` strictly matched to reference CIFs) and (2) the `+0.416087 eV/atom` Stage 2 shift on `mp-625477` (`Eu2H6O6`). Across the `2,372` complete-GFN-FF shared crystals, `robust` and `default` agree to `0.0` ULP.

---

## 6. Reproduction & Control-Group Protocol for Future Experiments

### Exact Reproduction Command

Run from the repository root after preparing NequIP-OAM weights (`python -m slices.relax_backends --prepare`):

```bash
OMP_NUM_THREADS=1 \
SLICES_TORCH_THREADS=1 \
PYTHONHASHSEED=0 \
PYTHONDONTWRITEBYTECODE=1 \
python tools/benchmarks/run_mp20_baseline.py \
  --csv data/mp20_nonmetal/mp20_v4_benchmark_2383.csv \
  --chem-pot data/mp20_nonmetal/chemPotMP.json \
  --mp20-dir data/mp20 \
  --out-dir benchmark/v4_0_2_baseline \
  --workers 24 \
  --passes default lorentz robust \
  --relax-model auto \
  --robust-starts 3 \
  --robust-seed 0
```

All flags above match the script defaults (an optional `--limit N` flag supports quick smoke runs). To verify single-process determinism against Pass 1 (`default_eform`), run:

```bash
OMP_NUM_THREADS=1 \
SLICES_TORCH_THREADS=1 \
PYTHONHASHSEED=0 \
PYTHONDONTWRITEBYTECODE=1 \
python examples/3.benchmark_relax_models.py \
  --n 10 --seed 0 --models auto --out ref10.json
```

### Using `per_structure_metrics.csv` as the Locked Control Group

[`per_structure_metrics.csv`](per_structure_metrics.csv) stores one row per structure (`2,383` rows, `53` columns) with lossless float64 formation energies (`%.17g`):

- **Metadata columns (`8`):** `row_index`, `material_id`, `formula`, `n_atoms`, `crystal_system`, `ref_sg`, `dft_eform`, `dft_band_gap`.
- **Per-pass columns (`15` × `3` passes prefixed by `default_`, `lorentz_`, `robust_`):** `ok`, `eform`, `abs_err`, `match_strict`, `match_loose`, `struct_valid`, `pred_sg`, `sg_match`, `roundtrip_canonical_match`, `preoptimized`, `retry`, `relax_steps`, `gfnff_incomplete`, `seconds`, `error_type`.

When testing a candidate algorithmic change on a new branch, run `tools/benchmarks/run_mp20_baseline.py --out-dir <experiment_dir> --passes default` and join directly on `row_index` (or `material_id`) against `benchmark/v4_0_2_baseline/per_structure_metrics.csv` to compute exact paired gains/losses, crystal-system stratification, and energy drift:

```python
import csv

with open("benchmark/v4_0_2_baseline/per_structure_metrics.csv", newline="") as f:
    ctrl = {int(r["row_index"]): r for r in csv.DictReader(f)}
with open("experiment_out/per_structure_metrics.csv", newline="") as f:
    cand = {int(r["row_index"]): r for r in csv.DictReader(f)}

strict_gained = [
    ctrl[i]["material_id"]
    for i in ctrl
    if ctrl[i]["default_match_strict"] != "1" and cand[i]["default_match_strict"] == "1"
]
strict_lost = [
    ctrl[i]["material_id"]
    for i in ctrl
    if ctrl[i]["default_match_strict"] == "1" and cand[i]["default_match_strict"] != "1"
]
print(f"Paired strict delta: +{len(strict_gained)} / -{len(strict_lost)}")
```
