# SLICES v4.1 Extended GPU & Multi-Dataset Benchmark Report

**Software & Commit:** SLICES `v4.1.0` (`0bde1191e0f47f670fc523d8609bdab3c33f120c`)  
**Hardware:** `2x NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition` (`97,887 MiB` VRAM each, `sm_120`), `32`-core CPU host (`CUDA_VISIBLE_DEVICES = worker_id % 2`)  
**Environments:**
- **NequIP Suites (`nequip-s+l`, `nequip-m+l`, `nequip-l`, `QMOF-21-40`, `MP-21-40`):** Python `3.10.22`, PyTorch `2.9.1+cu128` (`CUDA 12.8`), `nequip 0.17.1`, `openequivariance 0.8.0` (`aotinductor-oeq`), `pymatgen 2025.10.7`, `ase 3.29.0`, `numpy 2.2.6`, `scipy 1.15.3`.
- **Optional MLIP Models (`chgnet`, `mace`):** Python `3.11.15`, PyTorch `2.12.0+cu130` (`CUDA 13.0`), `chgnet 0.4.2`, `mace 0.3.16` (`MACE-MP (medium)`), `pymatgen 2026.5.18`, `ase 3.28.0`, `numpy 2.4.6`, `scipy 1.17.1`.

**Primary Archives:**
- Suite 1 (`MP-20`, `N = 2,383`): [`gpu_mp20_summary.json`](gpu_mp20_summary.json) (`135,151` B) | [`gpu_mp20_per_structure.csv`](gpu_mp20_per_structure.csv) (`1,001,153` B)
- Suite 2 (`QMOF-21-40`, `N = 339`): [`qmof_21_40_summary.json`](qmof_21_40_summary.json) (`24,044` B) | [`qmof_21_40_per_structure.csv`](qmof_21_40_per_structure.csv) (`65,326` B)
- Suite 3 (`MP-21-40`, `N = 1,000`): [`mp21_40_summary.json`](mp21_40_summary.json) (`53,461` B) | [`mp21_40_per_structure.csv`](mp21_40_per_structure.csv) (`257,025` B)
- Runner & CPU Baseline: [`tools/benchmarks/run_gpu_extended_benchmarks.py`](../../tools/benchmarks/run_gpu_extended_benchmarks.py) | [`AB_COMPARISON_REPORT.md`](../v4_1_experimental/AB_COMPARISON_REPORT.md)

---

## Executive Summary

We executed three uncontended multi-GPU benchmark suites sequentially on dual Blackwell GPUs to quantify SLICES `v4.1.0` reconstruction accuracy, force-field scaling, stage-level bottlenecks, and `lj_mixing="lorentz"` behavior beyond small-cell CPU evaluation:

1. **Exact CPU/CUDA Parity (`0 / 0` Match Discrepancies) with `4.96x` Faster Relaxation:** On full `MP-20` (`N = 2,383`), CUDA `nequip-s+l` (`aotinductor-oeq`) reproduces CPU `v4.1` (`torchscript`) identically on decode (`2,381`), strict match (`2,241`, `94.04%`), loose match (`2,293`, `96.22%`), and space-group (SG) match (`1,494`, `62.69%`) with `0 / 0` strict/loose flips and `5.0e-7 eV/atom` median `|Delta eform|`, while accelerating single-crystal relaxation **`4.96x`** (`0.0662 s` vs `0.3285 s`).
2. **Upgrading to `nequip-m+l` on GPU Is Practically Free and Statistically Superior:** Because GPU relaxation shrinks to **`4.7%–6.1%`** of single-structure decode time (while CPU GFN-FF + ZL\* consume `78.5%–93.2%`), **`nequip-m+l`** completes all `2,383` MP-20 crystals in **`180.61 s`** (`13.19/s`, faster than CPU `nequip-s+l`'s `193.57 s`) while raising strict match to **`95.09%`** (`2,266`, `+25` net, McNemar `p = 0.00263`), loose match to **`96.43%`** (`2,298`), and SG match to **`64.16%`** (`1,529`, `+35` net, `p = 6.41e-4`). **`nequip-l`** (`182.58 s`) reaches `94.88%` strict (`2,261`, `p = 0.0135`), the highest NequIP SG match (**`64.54%`**, `1,538`, `p = 2.30e-5`), and lowest NequIP median AE (`0.0211 eV/atom`).
3. **CHGNet Delivers Lowest Formation-Energy Error (`0.0521 eV/atom` MAE, `0` Outliers):** CUDA `chgnet` (`0.4.2`) achieves `94.17%` strict / `96.35%` loose recovery with **`0.0521 eV/atom` MAE**, **`0.0186 eV/atom` median AE**, and `79.65%` of crystals within `<= 0.05 eV/atom` because its MPtrj PBE+U energy scale aligns directly with `chemPotMP.json` (whereas NequIP-OAM and MACE-MP reflect OMat24+sAlex+MPtrj OAM DFT offsets).
4. **Full `QMOF-21-40` (`N = 339` MOFs, `econnn`) Outperforms Published Table S1:** `v4.1` reaches **`3.54%` strict (`1.20x` vs Table S1 `2.95%`)** and **`7.96%` loose (`1.29x` vs `6.19%`)** under `default`, rising to **`8.26%` loose (`1.33x`)** and **`9.73%` SG match** under `lorentz` (`304 / 339` decoded, `100%` structurally valid).
5. **Stratified `MP-21-40` (`N = 1,000 / 4,454` Test Crystals, `crystalnn`) Beats Table S1 by `> 4 pp`:** `v4.1 default` achieves `99.40%` ok, **`90.10%` strict (`+4.03 pp` vs Table S1 `86.07%`)**, **`93.70%` loose (`+4.73 pp` vs `88.97%`)**, and `47.60%` SG match; `lorentz` preserves `90.10%` strict (`93.40%` loose) while raising SG match to **`48.80%`** (`+12` net, `+1.20 pp`, McNemar `p = 0.0576`).

---

## 1. Suite 1: Full `MP-20` Multi-Model GPU Benchmark (`N = 2,383`)

All five GPU models were evaluated on `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` (`w = 24` workers = `12 / GPU`, `graph_method="econnn"`, `lj_mixing="legacy"`, `SLICES2structure()`) and paired against the archived CPU `v4.1` `nequip-s+l` reference (`benchmark/v4_1_experimental/`, `w = 24`).

### 1.1 Five-Model GPU vs CPU `v4.1` Comparison (`N = 2,383`)

| Model (Device / Backend) | Wall (s) | Thruput (`/s`) | OK | Strict (`%`) | Loose (`%`) | SG (`%`) | Raw MAE (eV/at) | Clean MAE (eV/at) | Med AE (eV/at) | `<=0.05` / `<=0.10` | Peak GPU VRAM (`MiB`) | McNemar Strict vs CPU (`+g/-l`, `p`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| **CPU `v4.1` `nequip-s+l`** (`torchscript`, ref) | `193.57` | `12.31` | `2,381` | `2,241` (`94.04%`) | `2,293` (`96.22%`) | `1,494` (`62.69%`) | `0.2005` | `0.2005` | `0.0255` | `1,312 / 1,386` | — | baseline |
| **CUDA `nequip-s+l`** (`aotinductor-oeq`) | `181.54` | `13.13` | `2,381` | `2,241` (`94.04%`) | `2,293` (`96.22%`) | `1,494` (`62.69%`) | `0.2008` | `0.2008` | `0.0255` | `1,312 / 1,387` | `10,664` | `+0 / -0` (`p = 1.0`) |
| **CUDA `nequip-m+l`** (`aotinductor-oeq`) | **`180.61`** | **`13.19`** | `2,381` | **`2,266` (`95.09%`)** | **`2,298` (`96.43%`)** | `1,529` (`64.16%`) | `0.3610`* | **`0.1948`** | `0.0217` | `1,331 / 1,402` | `10,796` | **`+45 / -20` (`p = 0.00263`)** |
| **CUDA `nequip-l`** (`aotinductor-oeq`) | `182.58` | `13.05` | `2,381` | `2,261` (`94.88%`) | `2,292` (`96.18%`) | **`1,538` (`64.54%`)** | `4.59e11`* | `0.1954` | `0.0211` | `1,331 / 1,404` | `11,388` | **`+40 / -20` (`p = 0.0135`)** |
| **CUDA `chgnet`** (`0.4.2`, `cu130`) | `203.07` | `11.73` | `2,381` | `2,244` (`94.17%`) | `2,296` (`96.35%`) | `1,448` (`60.76%`) | **`0.0521`** | **`0.0521`** | **`0.0186`** | **`1,898 / 2,093`** | `23,426` | `+37 / -34` (`p = 0.813`) |
| **CUDA `mace`** (`0.3.16` `MACE-MP med`) | `200.02` | `11.91` | `2,375` | `2,242` (`94.08%`) | `2,281` (`95.72%`) | `1,498` (`62.86%`)† | `804.92`* | `0.1975` | `0.0312`‡ | `1,306 / 1,390` | `16,104` | `+38 / -37` (`p = 1.0`) |

*\*Clean MAE excludes extreme outliers (`|eform - DFT| > 10 eV/atom` or `vol/atom < 2.0 A^3`): `1` for `nequip-m+l` / `nequip-l`, `6` for `mace`, `0` for `nequip-s+l` and `chgnet` (see Section 1.3).*  
*†For `mace`, `all_structures` counts `1,498` SG matches and `2,373` valid structures over the `2,375` relaxed `ok` crystals (`6` crystals fell back to unrelaxed ZL\* structures via `RelaxFallback:MLIPRelaxationError`).*  
*‡`mace` median AE is `0.0313 eV/atom` raw (`N = 2,375`) and `0.0312 eV/atom` clean (`N = 2,369`).*

- **Paired Space-Group & Canonical Round-Trip Gains:** Relative to CPU `nequip-s+l`, `nequip-m+l` gains **`+35` net SG matches** (`+68 / -33`, McNemar `p = 6.41e-4`) and improves triclinic strict recovery from `80.53% -> 85.84%` (`91 -> 97 / 113`) and trigonal from `93.31% -> 95.40%`; `nequip-l` gains **`+44` net SG matches** (`+75 / -31`, `p = 2.30e-5`) and reaches the highest canonical round-trip rate (`294 / 2,383 = 12.34%`, vs `282` for `nequip-m+l` and `251` for CUDA `nequip-s+l`). By contrast, `chgnet` loses `-46` SG matches (`+38 / -84`, `p = 3.79e-5`) despite matching `nequip-s+l` on strict/loose recovery.

### 1.2 Single-Worker Stage Breakdown (`stage_breakdown_64`, Stratified `N = 64`, `seed = 0`)

To eliminate multi-process contention and quantify Amdahl's Law limits, all six backends were timed sequentially on a crystal-system-stratified `N = 64` sample (`16` cubic, `13` orthorhombic, `10` monoclinic, `10` tetragonal, `6` hexagonal, `6` trigonal, `3` triclinic; mean `9.72` atoms):

| Config (`w = 1`) | Total Mean (`s`) | GFN-FF (`s`, `%`) | ZL\* (`s`, `%`) | Relax (`s`, `%`) | Topo (`s`, `%`) | Relax Speedup | Total Speedup | Strict / Loose (`ok`) | Peak VRAM (`MiB`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **`cpu:nequip-s+l`** | `1.661` | `0.773` (`46.5%`) | `0.531` (`31.9%`) | `0.329` (`19.8%`) | `0.029` (`1.8%`) | `1.00x` | `1.00x` | `61 / 64` (`64`) | — |
| **`cuda:nequip-s+l`** | `1.417` | `0.789` (`55.7%`) | `0.531` (`37.5%`) | **`0.066` (`4.7%`)** | `0.031` (`2.2%`) | **`4.96x`** | `1.17x` | `61 / 64` (`64`) | `905` |
| **`cuda:nequip-m+l`** | `1.419` | `0.781` (`55.1%`) | `0.534` (`37.6%`) | **`0.075` (`5.3%`)** | `0.028` (`2.0%`) | **`4.36x`** | `1.17x` | **`63 / 64`** (`64`) | `917` |
| **`cuda:nequip-l`** | `1.420` | `0.766` (`54.0%`) | `0.539` (`37.9%`) | **`0.086` (`6.1%`)** | `0.029` (`2.0%`) | **`3.82x`** | `1.17x` | `62 / 64` (`64`) | `937` |
| **`cuda:chgnet`** | `1.540` | `0.773` (`50.2%`) | `0.455` (`29.6%`) | `0.284` (`18.4%`) | `0.028` (`1.8%`) | `1.16x` | `1.08x` | `63 / 64` (`64`) | `1,737` |
| **`cuda:mace`** | `1.514` | `0.758` (`50.1%`) | `0.460` (`30.4%`) | `0.269` (`17.8%`) | `0.027` (`1.8%`) | `1.22x` | `1.10x` | `61 / 63` (`63`) | `1,129` |

- **Why `nequip-m+l` and `nequip-l` Have Near-Zero Wall-Clock Cost on GPU:** On CPU, GFN-FF (`46.5%`) + ZL\* (`31.9%`) already account for `78.5%` of decode time, capping theoretical full-pipeline speedup for an infinitely fast relaxer at `1.27x`. With `aotinductor-oeq` on Blackwell, GPU relaxation drops to `66–86 ms/crystal` (`4.7%–6.1%` of decode time), so stepping up from `nequip-s+l` to `nequip-m+l` adds only `+9.2 ms/crystal` (`+0.6%`) while achieving the best overall wall-clock (`180.61 s` at `w = 24`) and highest strict/loose match rates across all 5 models.

### 1.3 Formation-Energy Scale Alignment & Transparent Outlier Audit

- **Why CHGNet Achieves `0.0521 eV/atom` MAE:** `chemPotMP.json` defines elemental reference energies on the Materials Project PBE+U energy scale, which directly matches CHGNet's MPtrj training set (`mean_signed_error = -0.0223 eV/atom`, `1,898 / 2,383` [`79.65%`] within `<= 0.05 eV/atom`, `2,093 / 2,383` [`87.83%`] within `<= 0.10 eV/atom`). By contrast, `NequIP-OAM` (`mean_signed_error = +0.189..+0.196 eV/atom`) and `MACE-MP` (`+0.1886 eV/atom`) carry systematic OMat24+sAlex+MPtrj DFT compatibility offsets on transition-metal oxides and chalcogenides, producing clean MAE `~0.195–0.201 eV/atom` while maintaining tight median AE (`0.0211–0.0255 eV/atom`).
- **Complete Outlier & Failure Accounting (`N = 2,383`):**
  - **Shared Topological Failures (`2` crystals, all 5 models):** `CocycleBasisError: 1` (`mp-643814`) and `LatticeBasisError: 1` (`mp-29816`, proper sublattice `SNF = (1, 1, 3)`).
  - **`nequip-s+l` & `chgnet`:** **`0` extreme outliers**, `0` relaxation fallbacks.
  - **`nequip-m+l` & `nequip-l` (`1` outlier each):** `row 207: mp-754382` (`He1`, 1-atom primitive cell where `cocycle_rep is None` bypasses ZL\*). Without a repulsive multi-atom lattice target, `ExpCellFilter` collapses the noble-gas cell to `0.558 A^3/atom` (`eform = -395.81 eV/atom`) under `nequip-m+l` and `0.836 A^3/atom` (`eform = +1.09e15 eV/atom`) under `nequip-l`. Excluding this single 1-atom crystal brings clean MAE to `0.1948` (`nequip-m+l`) and `0.1954 eV/atom` (`nequip-l`).
  - **`mace` (`6` extreme outliers + `6` relaxation fallbacks):** Six Bi/Tl oxyhalides/halides produce extreme energies (`row 390: mp-549709` `Er1Bi2Cl1O4`, `row 606: mp-1216585` `Tl4Br3Cl1`, `row 655: mp-552008` `Dy1Bi2Cl1O4`, `row 1743: mp-561808` `Yb1Bi2Cl1O4`, `row 2009: mp-1205991` `La1Bi2Cl1O4`, `row 2066: mp-753360` `Bi4O4F4`), and six additional structures hit `RelaxFallback:MLIPRelaxationError` (`mp-1597`, `mp-625477`, `mp-753853`, `mp-27689`, `mp-549695`, `mp-753581`, McNemar `ok` `p = 0.03125`).

---

## 2. Suite 2: Full `QMOF-21-40` GPU Benchmark (`N = 339` MOFs)

All **339 / 339** metal-organic frameworks in `benchmark/Match_rate_QMOF-21-40/0_get_json/cifs_filtered.json` (`21–40` atoms, mean `33.01` atoms) were evaluated end-to-end (`CIF -> structure2SLICES(strategy=4, econnn) -> SLICES2structure()`, CUDA `nequip-s+l`, `relax_large_cell1`, `w = 24`) across paired `default` (`legacy`) and `lorentz` passes (`837.24 s` combined wall-clock).

### 2.1 Aggregate Results vs Upstream Table S1 (`N = 339`)

| Pass (`lj_mixing`) | Wall (s) | OK / 339 (`%`) | Strict (`%` vs `2.95%` S1) | Loose (`%` vs `6.19%` S1) | SG Match (`%`) | Valid (`%` ok) | Preopt / Retry | Mean BFGS Steps | Peak VRAM (`MiB`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Upstream Table S1 (M3GNet)** | — | — | `2.95%` | `6.19%` | — | — | — | — | — |
| **`v4.1 default` (`legacy`)** | `415.48` | `304` (`89.68%`) | **`12` (`3.54%`, `1.20x`)** | **`27` (`7.96%`, `1.29x`)** | `30` (`8.85%`) | `304` (`100%`) | `142 / 47` | `100.67` | `11,392` |
| **`v4.1 lorentz`** | `414.81` | `304` (`89.68%`) | **`12` (`3.54%`, `1.20x`)** | **`28` (`8.26%`, `1.33x`)** | **`33` (`9.73%`)** | `304` (`100%`) | `136 / 51` | `101.82` | `11,316` |

- **Paired `lorentz` vs `default`:** Identical `ok` (`304 == 304`), strict `+2 / -2` (`net 0`, McNemar `p = 1.0`), loose `+4 / -3` (`net +1`, `+0.30 pp`, `p = 1.0`), and SG `+4 / -1` (`net +3`, `+0.89 pp`, `p = 0.375`).
- **Failure Taxonomy (`35 / 339 = 10.32%`, identical across passes):** `CocycleBasisError: 33` (dominant bottleneck on porous multi-component MOF topologies), `LatticeBasisError: 1`, and `RelaxFallback:CellCollapse: 1`.
- **Stage Timings (mean s/MOF, `default` / `lorentz`):** Encode `0.065 / 0.066 s`, **GFN-FF `4.95 / 4.95 s` (`26.8%`)**, **ZL\* `11.29 / 11.32 s` (`61.3%`)**, CUDA Relax `2.10 / 2.12 s` (`11.4%`, median `0.69 s`), Topo `0.030 / 0.030 s`, Total `18.43 / 18.49 s`.
- **Atom-Count Scaling (`default` -> `lorentz`):** `21..25` atoms (`N = 34`, `7.79 s`): `5.88% -> 8.82%` strict, `8.82% -> 11.76%` loose; `26..30` (`N = 83`, `11.72 s`): `7.23% -> 6.02%` strict, `12.05%` loose; `31..35` (`N = 81`, `20.09 s`): `1.23%` strict, `6.17%` loose; `36..40` (`N = 141`, `24.00 s`): `2.13%` strict, `6.38%` loose.

---

## 3. Suite 3: Stratified `MP-21-40` GPU Benchmark (`N = 1,000 / 4,454`)

We drew a deterministic crystal-system-stratified sample (`seed = 0`, proportional Hamilton quotas with SHA-256 tie-breaking; all `1,000` `sampled_material_ids` archived in [`mp21_40_summary.json`](mp21_40_summary.json)) of **`1,000`** held-out test crystals from the `4,454`-crystal filtered `MP-21-40` test split (`6–40` primitive atoms, mean `29.69` atoms: `969` with `21–40` atoms plus `31` reduced to `6–20` atoms). Both `default` and `lorentz` passes ran end-to-end (`CIF -> structure2SLICES(strategy=4, crystalnn) -> SLICES2structure()`, CUDA `nequip-s+l`, `w = 28` = `14 / GPU`, `1,282.29 s` combined wall-clock).

### 3.1 Aggregate Results vs Upstream Table S1 (`N = 1,000`)

| Pass (`lj_mixing`) | Wall (s) | OK / 1,000 | Strict (`%` vs `86.07%` S1) | Loose (`%` vs `88.97%` S1) | SG Match (`%`) | Valid (`%` ok) | `\|eform - DFT\|` MAE / Med AE (eV/at) | `<=0.05` / `<=0.10` | Peak VRAM (`MiB`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Upstream Table S1 (M3GNet, `23.6k`)** | — | — | `86.07%` | `88.97%` | — | — | — | — | — |
| **`v4.1 default` (`legacy`)** | `635.71` | `994` (`99.40%`) | **`901` (`90.10%`, `+4.03 pp`)** | **`937` (`93.70%`, `+4.73 pp`)** | `476` (`47.60%`) | `994` (`100%`) | `0.4174 / 0.4024` | `183 / 219` | `13,827` |
| **`v4.1 lorentz`** | **`629.94`** | `994` (`99.40%`) | **`901` (`90.10%`, `+4.03 pp`)** | `934` (`93.40%`, `+4.43 pp`) | **`488` (`48.80%`)** | `994` (`100%`) | `0.4177 / 0.4022` | `183 / 218` | `13,831` |

- **Paired `lorentz` vs `default`:** Strict `+4 / -4` (`net 0`, McNemar `p = 1.0`), Loose `+1 / -4` (`net -3`, `p = 0.375`), **SG `+23 / -11` (`net +12`, `+1.20 pp`, McNemar `p = 0.0576`)**, formation-energy error neutral (Wilcoxon `p = 0.551`, median `|Delta eform| = 3.32e-5 eV/atom`), and slightly faster (`-5.78 s` wall-clock, `-0.139 s/crystal` mean, Wilcoxon `p = 1.0e-8`, `preoptimized` `21 -> 18`).
- **Failure Taxonomy (`6 / 1,000 = 0.60%`, identical across passes):** `RelaxFallback:CellCollapse: 3`, `CocycleBasisError: 2`, `NodeNotFound: 1`, and **`0` `LatticeBasisError`** (exact SNF fallback eliminates every unimodular basis obstruction across all 1,000 held-out large cells).
- **Stage Timings (mean s/crystal, `default` / `lorentz`):** Encode `0.233 / 0.235 s` (`1.4%`), **GFN-FF `5.204 / 5.196 s` (`31.4%`)**, **ZL\* `10.789 / 10.656 s` (`65.1%`)**, **CUDA Relax `0.210 / 0.211 s` (`1.3%`)**, Topo `0.127 / 0.128 s` (`0.8%`), Total `16.56 / 16.42 s` (`mean BFGS steps = 28.64`). On `21–40`-atom inorganic crystals, CPU ZL\* + GFN-FF account for **`96.5%`** of round-trip time while GPU relaxation takes just **`1.3%`**.

### 3.2 Seven-System Breakdown (`MP-21-40`, `N = 1,000`)

| Crystal System | Quota (`N`) | `ok` (`%`) | `default` Strict (`%`) | `default` Loose (`%`) | `default` SG (`%`) | `lorentz` SG (`%`) | `default` MAE / Med AE (eV/at) | Mean Time (`s`) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **Cubic** | `68` | `100.0%` | **`95.59%`** (`65`) | **`97.06%`** (`66`) | `50.00%` (`34`) | `51.47%` (`35`) | `0.1991 / 0.0309` | `14.19` |
| **Hexagonal** | `66` | `100.0%` | **`95.45%`** (`63`) | `95.45%` (`63`) | `50.00%` (`33`) | `48.48%` (`32`) | `0.2345 / 0.1156` | `16.11` |
| **Tetragonal** | `67` | `100.0%` | `94.03%` (`63`) | `95.52%` (`64`) | `37.31%` (`25`) | `38.81%` (`26`) | `0.3034 / 0.2525` | `17.27` |
| **Orthorhombic** | `249` | `99.60%` | `91.16%` (`227`) | `92.77%` (`231`) | `40.96%` (`102`) | `40.96%` (`102`) | `0.3471 / 0.3573` | `15.54` |
| **Trigonal** | `81` | `95.06%` | `90.12%` (`73`) | `91.36%` (`74`) | `48.15%` (`39`) | `48.15%` (`39`) | `0.5645 / 0.5644` | `19.25` |
| **Monoclinic** | `303` | `99.67%` | `88.45%` (`268`) | `94.06%` (`285`) | `36.96%` (`112`) | **`40.26%`** (`122`) | `0.4842 / 0.4571` | `17.57` |
| **Triclinic** | `166` | `100.0%` | `85.54%` (`142`) | `92.77%` (`154`) | `78.92%` (`131`) | `79.52%` (`132`) | `0.5410 / 0.5500` | `15.83` |
| **All Systems** | **`1,000`** | **`99.40%`** | **`90.10%` (`901`)** | **`93.70%` (`937`)** | **`47.60%` (`476`)** | **`48.80%` (`488`)** | **`0.4174 / 0.4024`** | **`16.56`** |

*(Atom-count scaling on `default`, `21..40` bins: `21..25` [`N=270`, `7.29 s`] `89.63% / 92.59%`; `26..30` [`N=286`, `12.44 s`] `92.31% / 94.06%`; `31..35` [`N=143`, `18.66 s`] `88.81% / 94.41%`; `36..40` [`N=270`, `30.76 s`] `88.52% / 93.70%`.)*

---

## 4. Practical Guidance & CLI Reproduction

### Recommended Backend Selection (`v4.1`)

| Workload | Recommended Configuration | Rationale |
|---|---|---|
| **CPU Workstation (Default)** | `SLICES(relax_model="auto")` (`nequip-s+l`) + opt-in `lj_mixing="lorentz"` | `94.04%` strict / `96.22%` loose (`65.55%` SG with `lorentz`), `0` outliers, reproducible CPU determinism. |
| **NVIDIA GPU (Best Structural Accuracy)** | `SLICES_DEVICE=cuda`, `relax_model="nequip-m+l"` (with `--extra oeq`) | Pareto-optimal: **`95.09%`** strict, **`96.43%`** loose, `64.16%` SG in `180.61 s` (`5.3%` GPU relax share). Use `nequip-l` when maximizing SG match (`64.54%`). |
| **MPtrj PBE+U Formation-Energy Parity** | `SLICES_DEVICE=cuda`, `relax_model="chgnet"` (`chgnet >= 0.4.2`) | **`0.0521 eV/atom` MAE**, `0.0186 eV/atom` median AE, `0` outliers against `chemPotMP.json`. |

### Exact Reproduction Commands

Run from the repository root with a CUDA-enabled NequIP environment (`--extra cu128 --extra oeq` after `python -m slices.relax_backends --prepare`). Use `--work-dir` to checkpoint and merge models from a separate `chgnet`/`mace` environment if needed:

```bash
# Suite 1A: MP-20 NequIP GPU models + CPU/CUDA 64-crystal stage breakdown
PYTHONPATH=src python tools/benchmarks/run_gpu_extended_benchmarks.py \
  --suite mp20 \
  --models nequip-s+l nequip-m+l nequip-l \
  --stage-configs cpu:nequip-s+l cuda:nequip-s+l cuda:nequip-m+l cuda:nequip-l \
  --mp20-workers 24 --n-gpus 2 --seed 0 \
  --work-dir /tmp/slices-mp20-ckpt \
  --out-dir benchmark/v4_1_extended

# Suite 1B (optional MLIP env with chgnet & mace installed): merge into unified MP-20 archive
PYTHONPATH=src python tools/benchmarks/run_gpu_extended_benchmarks.py \
  --suite mp20 \
  --models chgnet mace \
  --stage-configs cuda:chgnet cuda:mace \
  --mp20-workers 24 --n-gpus 2 --seed 0 \
  --work-dir /tmp/slices-mp20-ckpt \
  --out-dir benchmark/v4_1_extended

# Suite 2: Full QMOF-21-40 (339 MOFs, econnn, default + lorentz)
PYTHONPATH=src python tools/benchmarks/run_gpu_extended_benchmarks.py \
  --suite qmof \
  --qmof-workers 24 --n-gpus 2 --passes default lorentz \
  --out-dir benchmark/v4_1_extended

# Suite 3: Stratified MP-21-40 (1,000 / 4,454 test crystals, crystalnn, default + lorentz)
PYTHONPATH=src python tools/benchmarks/run_gpu_extended_benchmarks.py \
  --suite mp21-40 \
  --mp21-40-dir <path/to/mp-21-40> \
  --mp21-40-sample-size 1000 --mp21-40-workers 28 --n-gpus 2 --seed 0 \
  --passes default lorentz \
  --out-dir benchmark/v4_1_extended
```
