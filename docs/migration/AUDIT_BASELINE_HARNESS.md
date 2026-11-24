# Stage 2C Audit Report: Golden Baseline Equivalence Harness & Test Suite Design

**Date:** 2026-11-25  
**Auditor:** `baseline` (Slice 2C — Golden Baseline & Test Audit Engineer)  
**Target Working Branch:** `slices-4-personal` (`94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`)  
**Immutable Reference Worktree:** `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`, detached, locked, read-only)  
**Audited Personal Test Branch:** `backup/v3-personal` (`301c75fcdfb2d553b616c30178ccc7b0161b1fe7`)  
**Governing Plan:** [PLAN.md](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md) (Sections 2.3, 4, and 5 Slice 2C)

---

## 1. Executive Summary & Empirical Determinism Results

To enforce the Strict Math/Algorithm Freeze Boundary ([PLAN.md Section 4](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L140-L166)) across Stages 3–7, candidate crystal structures and SLICES strings from [examples/](file:///home/ordillo/tests/SLICES-upstream-baseline/examples), [data/mp20_nonmetal/](file:///home/ordillo/tests/SLICES-upstream-baseline/data/mp20_nonmetal), [data/mp20/test.csv](file:///home/ordillo/tests/SLICES-upstream-baseline/data/mp20/test.csv) (the upstream CIF source of `data/mp20_nonmetal/`), and [gfnff_helper.py](file:///home/ordillo/tests/SLICES-upstream-baseline/src/slices/gfnff_helper.py) were empirically probed and benchmarked on `/home/ordillo/tests/.venv-upstream` (`CPython 3.10.22`, `torch==2.9.1+cpu`, `nequip==0.17.1`, `pymatgen==2025.10.7`, `ase==3.29.0`, `scipy==1.15.3`, `numpy==2.2.6`, `spglib==2.7.0`, `OMP_NUM_THREADS=1`).

### Key Empirical Results
1. **Stratified 19-Entry Golden Reference Corpus (`G01`–`G19`) + 2 Synthetic Safety Fixtures (`S01`–`S02`) + 11 Invalid/Edge-Case SLICES Strings (`E01`–`E11`):**
   - Covers all **7 crystal systems** (`triclinic`, `monoclinic`, `orthorhombic`, `tetragonal`, `trigonal`, `hexagonal`, `cubic`) and all **6 centering letters** (`P`, `I`, `F`, `C`, `A`, `R`) present in [utils_wyckoff.py](file:///home/ordillo/tests/SLICES-upstream-baseline/src/slices/utils_wyckoff.py).
   - Exercises every critical upstream v4.0.2 code branch: single-atom primitive cell (`cocycle_rep is None`), conventional-to-primitive reduction (`16 -> 8` and `8 -> 4` atoms), high supercell coordination (`20 -> 19` and `24 -> 19` neighbor truncation in `get_nbf_blist`), CIF oxidation-state species (`Nd2+`, `Si4-`, `Ru2+`), heavy `Z <= 86` (`Nd`, `Yb`, `Ir`, `Pb`, `Bi`, `Rn`) vs `Z >= 87` (`Fr`, `Th`) element boundaries, natural and synthetic `preoptimize` (`closest_pair_ratio < 0.5`), `unstable_graph == True` (`inner_p_std_diag <= 0.0001`), and `gfnff_helper` stored reference targets.
2. **Zero CPU Repeat Variance (`0.000e+00`) & Fast Wall-Clock Runtime (`~30 s`):**
   - Two independent cold-process CPU passes (`relax_model="auto"` -> `nequip-s+l`) completed in **`30.52 s`** (Pass 1) and **`30.05 s`** (Pass 2) total wall-clock time across all 19 corpus structures, 11 edge-case strings, element checks, and synthetic `preoptimize` relaxation.
   - Maximum absolute numerical repeat difference across all floating-point outputs (`inner_p_target`, `colattice_weights`, `[std, opt, opt2]` lattice matrices and fractional coordinates, `final_energy_per_atom`, and `preoptimize` trajectories) was **`0.000e+00`** (exact IEEE-754 bit-for-bit reproducibility on CPU).
   - All `16 / 16` (`100%`) CIF-backed structures (`G01`–`G16`) achieved both strict and loose `match_check3` reconstruction matches (`'1'`).
3. **Critical Cross-Process Determinism Catch (`PYTHONHASHSEED=0`):**
   - Dual-subprocess probing uncovered that `SLICES.structure2randomSLICES` ([core.py](file:///home/ordillo/tests/SLICES-upstream-baseline/src/slices/core.py#L741-L845)) deduplicates strings in a Python `set()` before calling `list(SLICES_set)` and `random.shuffle()`. Under default randomized string hashing, `list(SLICES_set)` iteration order varies across processes even with `random.seed(42)` (`16/16` list-order mismatches across unseeded-hash processes, while `set(...)` membership matched `100%`). Setting `PYTHONHASHSEED=0` restored **100% exact list-order equality** across subprocesses.
4. **Complete Triage of `backup/v3-personal` Test Suite (25 Test/Tool Files Audited):**
   - Classified every file in `backup/v3-personal:{pytest.ini, .github/workflows/tests.yml, tests/**, tools/tests/**, tools/validate_installation.py, tools/benchmarks/test_*.py}` and identified **9 concrete bugs** inside the legacy fork tests (including passing a string instead of a `Structure` to `check_structural_validity`, an undefined variable `NameError` in `test_round_trip_batch.py`, invalid `graph_method='econ'`, `strategy=2` `from_SLICES` crash, missing `ElementComparator` on `NdSiRu.cif`, and non-frozen `LatticeBasisError` expectations on `Net`).
5. **7 Net-New Core/Algorithm Quirks (`DEF-BC-01`–`DEF-BC-07`):**
   - Cataloged in **Section 5** for consolidation into [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) starting at `DEF-021` (deduplicated against `DEF-001`–`DEF-020`), highlighted by `check_SLICES()` silently returning `True` when `Net.get_lattice_basis()` fails with `-1` (`DEF-BC-01`, empirically reproduced on quasi-1D `TiBr3` `mp-28214`).

---

## 2. Stratified Golden Reference Corpus & Edge-Case Suite

### 2.1 Dataset Provenance Note
Inspection of [data/mp20_nonmetal/1_run.py](file:///home/ordillo/tests/SLICES-upstream-baseline/data/mp20_nonmetal/1_run.py) verified that `data/mp20_nonmetal/{mp20_eform_bandgap_nonmetal.csv, test_data_reduce_zero.csv, train_data_reduce_zero.csv}` store pre-encoded SLICES strings (`['SLICES', 'eform', 'bandgap']` without CIF columns or strategy-4 space-group prefixes), generated directly from the full CIF tables in [data/mp20/test.csv](file:///home/ordillo/tests/SLICES-upstream-baseline/data/mp20/test.csv), `val.csv`, and `train.csv` (all retained in repo scope per [PLAN.md Section 1](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L28)). Accordingly, `G01`–`G16` draw CIF-backed crystals from `examples/` (`G01`–`G02`) and nonmetal/edge-case rows of `data/mp20/test.csv` (`G03`–`G16`) so full CIF->SLICES->Structure round-trips and `match_check*` are tested end-to-end, while `G17`–`G19` draw SLICES-native entries directly from `data/mp20_nonmetal/test_data_reduce_zero.csv` and `src/slices/gfnff_helper.py`.

### 2.2 Verified 19-Structure Golden Reference Corpus (`G01`–`G19`)

All values below were measured empirically on `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`) with CPU `relax_model="auto"` (`nequip-s+l`, `optimizer="BFGS"`, `fmax=0.2`, `steps=100`):

| ID | Formula | Source (`row` / `material_id`) | Atoms (`in -> prim`) | Edges | Crystal System | Ctr | Space Group (`in -> std`) | `check_element` | `opt` `cpr` | `unstable` | Supercell CN (`raw -> nbf`) | CPU `E` (`eV/atom`) | `match_check3` Strict Tuple | Time (`s`) | Primary Coverage Target |
|---|---|---|---:|---:|---|---|---|---:|---:|---:|---|---:|---|---:|---|
| `G01` | `NdSiRu` | `examples/NdSiRu.cif` | `6 -> 6` | 32 | Tetragonal | `P` | `P4/nmm (129) -> 129` | `True` | `0.7336` | `False` | `12 -> 12` | `-7.26759387` | `('1','0','0','0.0','0.25','0.25')` | `2.10` | CIF ox-states (`Nd2+/Si4-/Ru2+`), lanthanide `Z=60`, `+` token in SG `129` |
| `G02` | `Sr3Ru2O7` | `examples/Sr3Ru2O7.cif` | `12 -> 12` | 42 | Tetragonal | `I` | `I4/mmm (139) -> 139` | `True` | `0.9254` | `False` | `12 -> 12` | `-6.79135010` | `('1','1','0','0.0','0.5','0.33333333333333337')` | `3.47` | Example fixture #2, body-centered `I`, 12-atom cell |
| `G03` | `Si3P3Ir` | `data/mp20/test.csv` (`r=473`, `mp-1219249`) | `7 -> 7` | 15 | Triclinic | `P` | `P1 (1) -> 1` | `True` | `1.0323` | `False` | `6 -> 6` | `-6.19029275` | `('1','1','1','0.0','0.0','0.0')` | `0.69` | Triclinic `P1` (`o z o`), `lattice_type=3` (`a!=b!=c`), 5d `Ir` `Z=77` |
| `G04` | `VO` | `data/mp20/test.csv` (`r=930`, `mp-1287184`) | **`8 -> 4`** | 12 | Triclinic | `P` | `P-1 (2) -> 225` | `True` | `0.9591` | `False` | `6 -> 6` | `-7.80904841` | `('1','1','1','0.0','0.0','0.0')` | `0.50` | Centrosymmetric triclinic `P-1` (`+ z o`) + `8 -> 4` `to_primitive_if_smaller` |
| `G05` | `CdPb2(ClO)2` | `data/mp20/test.csv` (`r=59`, `mp-1077904`) | `7 -> 7` | 30 | Monoclinic | `C` | `C2/m (12) -> 12` | `True` | **`0.4024`** | `False` | `11 -> 11` | `-4.31523966` | `('1','0','0','0.0','0.375','0.2857142857142857')` | `1.39` | Monoclinic `C`-centering, heavy `Pb` (`Z=82`), **triggers `preoptimize` (`<0.5`)** |
| `G06` | `LiMnO2` | `data/mp20/test.csv` (`r=5`, `mp-1002572`) | **`16 -> 8`** | 28 | Orthorhombic | `P` | `P2_12_12 (18) -> 58` | `True` | `0.9341` | `False` | `8 -> 8` | `-6.57223321` | `('1','1','1','0.33333333333333337','0.33333333333333337','0.0')` | `1.40` | Orthorhombic `P` + **`16 -> 8` conventional-to-primitive reduction** |
| `G07` | `Cs3LiCl4` | `data/mp20/test.csv` (`r=154`, `mp-606711`) | `8 -> 8` | 31 | Orthorhombic | `A` | `Amm2 (38) -> 38` | `True` | `0.8033` | `False` | `9 -> 9` | `-3.35429967` | `('1','1','0','0.0','0.0','0.0')` | `1.17` | Orthorhombic **`A`-centering** (`o w a ODD b OOO j OOO o`) |
| `G08` | `BaZnSO` | `data/mp20/test.csv` (`r=146`, `mp-548469`) | `8 -> 8` | 28 | Orthorhombic | `C` | `Cmcm (63) -> 63` | `True` | `0.9841` | `False` | `10 -> 10` | `-4.83758489` | `('1','1','0','0.0','0.0','0.16666666666666663')` | `1.15` | Orthorhombic **`C`-centering** (`+ w a DDO b OOD c OOD o`) |
| `G09` | `K4ZnAs2` | `data/mp20/test.csv` (`r=119`, `mp-571461`) | `7 -> 7` | 31 | Trigonal | `R` | `R-3m (166) -> 166` | `True` | `0.9506` | `False` | `10 -> 10` | `-2.59167800` | `('1','1','1','0.0','0.0','0.0')` | `1.16` | Trigonal rhombohedral **`R`-centering** (`+ w a ECC n OOO e OOO o`) |
| `G10` | `BaSn2` | `data/mp20/test.csv` (`r=77`, `mp-567510`) | `3 -> 3` | 9 | Trigonal | `P` | `P-3m1 (164) -> 164` | `True` | `0.9099` | `False` | `6 -> 6` | `-3.75244451` | `('1','1','1','0.0','0.0','0.0')` | `0.34` | Trigonal `P`-centering (`+ x n OOO e OOO o`), compact 3-atom cell (`to_4structures`) |
| `G11` | `K2NaAs` | `data/mp20/test.csv` (`r=63`, `mp-34127`) | `8 -> 8` | 42 | Hexagonal | `P` | `P6_3/mmc (194) -> 194` | `True` | `0.8677` | `False` | `11 -> 11` | `-2.39722710` | `('1','1','1','0.0','0.0','0.0')` | `2.06` | Hexagonal (`+ w n OOO b OOD e OOO o`) |
| `G12` | `NbCoSn` | `data/mp20/test.csv` (`r=233`, `mp-1094088`) | `3 -> 3` | 14 | Cubic | `F` | `F-43m (216) -> 216` | `True` | `0.8622` | `False` | `10 -> 10` | `-7.35838148` | `('1','1','1','0.0','0.0','0.0')` | `0.50` | Face-centered cubic **`F`**, `lattice_type=1` (`a=b=c`), `to_4structures` |
| `G13` | `CsYbBr3` | `data/mp20/test.csv` (`r=38`, `mp-568005`) | `5 -> 5` | 18 | Cubic | `P` | `Pm-3m (221) -> 221` | `True` | `0.8200` | `False` | `12 -> 12` | `-3.49149623` | `('1','1','1','0.0','0.0','0.0')` | `0.79` | Primitive cubic `P`, heavy lanthanide `Yb` (`Z=70`) |
| `G14` | `Na` | `data/mp20/test.csv` (`r=1667`, `mp-127`) | **`1 -> 1`** | 7 | Cubic | `I` | `Im-3m (229) -> 229` | `True` | `N/A` | `False` | `14 -> 14` | `-1.30426465` | `('1','1','1','0.0','0.0','0.0')` | `0.24` | **Single-atom primitive cell (`cocycle_rep is None`, `num_nodes == 1`)** |
| `G15` | `PrBi2IO4` | `data/mp20/test.csv` (`r=262`, `mp-545728`) | `8 -> 8` | 42 | Tetragonal | `P` | `P4/mmm (123) -> 123` | `True` | `0.7074` | `False` | **`20 -> 19`** | `-6.10059145` | `('1','0','0','0.0','0.5','0.375')` | `1.98` | **High coordination (`>19` neighbors truncated in `get_nbf_blist`)** + `Bi` (`Z=83`) |
| `G16` | `SmThCN` | `data/mp20/test.csv` (`r=1`, `mp-1218989`) | `4 -> 4` | 12 | Trigonal | `R` | `R3m (160) -> 160` | **`False`** | `0.9324` | `False` | `6 -> 6` | `-8.27481782` | `('1','1','1','0.0','0.0','0.0')` | `0.41` | **Actinide `Th` (`Z=90 >= 87`):** `check_element=False` + GFN-FF `modern` fallback |
| `G17` | `ZrTi(PbO3)2` | `data/mp20_nonmetal/test_data_reduce_zero.csv` (`r=1249`) | `— -> 10` | 18 | SLICES-only | — | `None -> 160` | — | **`0.2715`** | `False` | `6 -> 6` | `-7.71096293` | — | `1.21` | **Natural `mp20_nonmetal` `preoptimize` trigger (`0.2715 < 0.5`)**, `space_group_num=None` |
| `G18` | `YHO2` | `data/mp20_nonmetal/test_data_reduce_zero.csv` (`r=394`) | `— -> 8` | 16 | SLICES-only | — | `None -> 63` | — | `0.6526` | **`True`** | `7 -> 7` | `-7.52021918` | — | `1.32` | **Triggers `self.unstable_graph = True` (`inner_p_std_diag <= 0.0001`)** |
| `G19` | `Na3MnCoNiO6` | `src/slices/gfnff_helper.py:120` | `— -> 12` | 36 | SLICES-only | `C` | `8 -> 8` | — | `0.8921` | `False` | `6 -> 6` | `-5.44468347` | — | `1.75` | `gfnff_helper` self-test reference (`trace=178.74144`, `126` inds, `sum(w)=61.23`) |

> [!NOTE]
> **Supplementary High-Coordination Topology Fixture (`G15b`):** In `data/mp20_nonmetal/test_data_reduce_zero.csv` row `1205` (`Cs2LiCoC6N6`, 16 atoms), supercell coordination reaches **`24 -> 19`** (`>19` cap in `get_nbf_blist`). `test_golden_equivalence.py` also snapshots `get_nbf_blist()` and `get_inner_p_target()` on `G15b` (`< 20 ms`, no NequIP needed) so both 8-atom CIF round-trip (`G15`, `CN=20`) and 24-neighbor `mp20_nonmetal` (`G15b`, `CN=24`) are covered.

### 2.3 Synthetic Safety & Element Boundary Fixtures (`S01`–`S03`)

| Fixture ID | Input Construction | Target Function(s) | Verified Upstream v4.0.2 Behavior |
|---|---|---|---|
| `S01_overlap_preopt` | `Structure(Lattice.cubic(3.6), ["Na", "Cl"], [[0,0,0], [0.12,0.12,0.12]])` | `closest_pair_ratio`, `remove_overlaps(seed=0)`, `preoptimize`, `NequIPRelaxer.relax` | `applied=True`, `ratio_before=0.279162 < 0.5`, `ratio_after=0.720994 >= 0.7`, `relax` returns `preoptimized=True`, `retry=0`, `E_tot = -6.527042 eV` (`0.0` repeat variance) |
| `S02_collapse_retry` | Mocked primary calculator shrinking volume `< COLLAPSE_VOLUME` (`2.0 A^3/atom`) on step 1 | `_collapse_guard`, `CellCollapse`, `NequIPRelaxer.relax` fallback (`NequIP-OAM-S + FIRE`) | Primary `_optimize` raises `CellCollapse`; `NequIPRelaxer.relax` catches once, retries from initial post-`preoptimize` structure with `NequIP-OAM-S + FIRE(maxstep=0.1, steps=2*steps)`, and sets `res["retry"] == 1` |
| `S03_element_boundary` | `Rn` (`Z=86`), `Fr` (`Z=87`), `Si+Fr` (`Z=[14, 87]`) | `SLICES.check_element` | `Rn (Z=86) -> True`, `Fr (Z=87) -> False`, `Si+Fr -> False` |

### 2.4 Invalid, Rank-Deficient & Edge-Case SLICES Corpus (`E01`–`E11`)

Every edge-case string below was verified against upstream v4.0.2 (`94ef8e0`):

| Edge ID | SLICES Input (`strategy=4`) | `from_SLICES(..., fix_duplicate_edge=False)` | `check_SLICES` (default: `dupli=False, rank=True`) | `check_SLICES(dupli_check=True)` | `check_SLICES(graph_rank_check=False)` | `check_SLICES_basic` | Code Branch Exercised |
|---|---|---|---|---|---|---|---|
| `E01_empty` | `""` | Raises `Exception("Error: no valid element symbols found")` | `False` | `False` | `False` | `False` | `_first_element_index` returns `None` (`core.py:276-278`) |
| `E02_no_elem` | `"foo bar baz"` | Raises `Exception("Error: no valid element symbols found")` | `False` | `False` | `False` | `False` | Non-element tokens rejected before edge parsing |
| `E03_bad_sg_prefix` | `"q q q Si O 0 1 ooo"` | Raises `Exception("Error: space_group_num = None")` | `False` | `False` | `False` | `False` | Invalid Wyckoff header rejected (`core.py:283-287`; guards against `DEF-016`) |
| `E04_oob_node_idx` | `"Si O 0 5 ooo"` | Raises `Exception("Error: wrong edge indices")` | `False` | `False` | `False` | `False` | Out-of-bounds vertex index `5 > num_atoms - 1` (`core.py:306-307`) |
| `E05_bad_jimage_label` | `"Si O 0 1 oox"` | Raises `Exception("Error: wrong edge label")` | `False` | `False` | `False` | `False` | Invalid periodic image character `'x'` (`core.py:315-316`) |
| `E06_rank_h1_lt_3_1d` | `"Si O 0 1 ooo 0 1 +oo"` | `ok` (`2` edges) | `False` | `False` | `False` | `True` | First Betti number `b = H1(X,Z) = 1 < 3` (`core.py:502-504`); fails `edge_index_covered` when `rank=False` |
| `E07_rank_h1_lt_3_2d` | `"Si O 0 1 ooo 0 1 +oo 0 1 o+o"` | `ok` (`3` edges) | `False` | `False` | `False` | `True` | `b = H1(X,Z) = 2 < 3` (2D net rejected for 3D reconstruction, accepted by `check_SLICES_basic`) |
| `E08_unconnected_atom` | `"Si O C 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+"` | `ok` (`3` atoms, atom `2` isolated) | `False` | `False` | `False` | `False` | `len(set(nodes_covered)) != len(self.atom_types)` (`core.py:510-511, 579-580`) |
| `E09_duplicate_flipped_edge` | `"Si O 0 1 ooo 1 0 ooo 0 1 +oo 0 1 o+o 0 1 oo+"` | `ok` (`5` raw edges; `4` after `fix_duplicate_edge=True`) | **`True`** | **`False`** | `True` | `True` | Inverted duplicate `0->1 ooo` vs `1->0 ooo` deduplicated when `dupli_check=False`, rejected when `dupli_check=True` (`core.py:318-329, 522-536`) |
| `E10_collinear_labels` | `"Si O 0 1 ooo 0 1 +oo 0 1 -oo 0 1 ++o"` | `ok` (`H1 = 3`) | `False` | `False` | `False` | `True` | `H1 >= 3` satisfied, but `edge_index_covered[2]` (z-axis) is empty (`core.py:518-520`) |
| `E11_quasi1d_lattice_basis_neg1` | `"+ z o Ti Ti Br Br Br Br Br Br 0 2 oo+ ..."` (`mp-28214`, `data/mp20/test.csv` `r=464`) | `ok` (`check_3D == False`) | **`True`** | **`True`** | **`True`** | `True` | Frozen baseline quirk (`DEF-BC-01`): `Net.get_lattice_basis()` returns `-1` without raising, so `check_SLICES` returns `True` while `SLICES2space_group_number` returns `None` |

---

## 3. Golden Equivalence Harness Specification (`tests/baseline/`)

### 3.1 File Layout & Storage Footprint

All golden baseline artifacts reside under `tests/baseline/` with a total footprint of **< 250 KB** (zero large files written to `/`):

```text
tests/baseline/
├── __init__.py
├── corpus_manifest.json        # Immutable source coordinates (file/row/material_id/SLICES) for G01..G19, G15b, S01, S03, E01..E11
├── golden_metadata.json        # Provenance + exact discrete expectations (strings, bools, ints, tuples)
├── golden_arrays.npz           # Compressed exact IEEE-754 float64/int64 arrays (zero text-rounding loss)
├── generate_golden.py          # Deterministic fixture generator run against SLICES-upstream-baseline (94ef8e0)
└── test_golden_equivalence.py  # Pytest golden snapshot assertions + dual-tree subprocess runner
```

### 3.2 Schema of `golden_metadata.json` and `golden_arrays.npz`

1. **`golden_metadata.json`:**
   ```json
   {
     "schema_version": "1.0.0",
     "upstream_baseline": {
       "worktree": "/home/ordillo/tests/SLICES-upstream-baseline",
       "git_commit": "94ef8e079b69c37138159805e3c701b8df87a5d7",
       "git_tree": "<git rev-parse HEAD^{tree}>",
       "python": "3.10.22",
       "packages": {
         "torch": "2.9.1+cpu", "nequip": "0.17.1", "pymatgen": "2025.10.7",
         "ase": "3.29.0", "scipy": "1.15.3", "numpy": "2.2.6", "spglib": "2.7.0"
       },
       "env": {"OMP_NUM_THREADS": "1", "PYTHONHASHSEED": "0", "SLICES_TORCH_THREADS": "1"}
     },
     "constants_sha256": {
       "config_OFFSET": "<sha256>",
       "config_LJ_PARAMS_LIST": "<sha256>",
       "config_PERIODIC_DATA_csv": "<sha256>",
       "wyckoff_sg_encoding_json": "<sha256>"
     },
     "corpus": {
       "G01": {
         "kind": "cif_file",
         "natoms_in": 6, "natoms_prim": 6,
         "sg_num_in": 129, "sg_sym_in": "P4/nmm",
         "check_element": true, "check_3D": true, "check_2D": false, "dim": 3,
         "slices_by_strategy": {"1": "...", "2": "...", "3": "...", "4": "..."},
         "random_slices_seed42_hashseed0": ["...", "...", "...", "...", "..."],
         "check_SLICES": {"default": true, "dupli_true": true, "basic": true},
         "canonical_s4": "...",
         "formula": "Nd2Ru2Si2",
         "sg_recreated": 129,
         "parsed_sg_num": 129,
         "nbf": "...",
         "colattice_inds": [[...], [...]],
         "unstable_graph": false,
         "num_returned_structs": 3,
         "energy_per_atom_hex": "<float.hex() exact IEEE-754>",
         "energy_per_atom": -7.26759387,
         "opt_closest_pair_ratio": 0.733608,
         "match_check_strict": ["0", "0", "0.25", "0.25"],
         "match_check3_strict": ["1", "0", "0", "0.0", "0.25", "0.25"],
         "match_check3_loose": ["1", "0", "0", "0.0", "0.25", "0.25"]
       }
     },
     "synthetic": {"S01_overlap_preopt": {...}, "S03_element_boundary": {...}},
     "edges": {"E01_empty": {...}, "...": {...}}
   }
   ```
2. **`golden_arrays.npz` (`np.savez_compressed`):**
   Keyed deterministically by `<ID>__<field>` with exact `int64` and `float64` dtypes:
   - `<ID>__atom_types` (`int64`, `(N,)`), `<ID>__edge_indices` (`int64`, `(E, 2)`), `<ID>__to_jimages` (`int64`, `(E, 3)`), `<ID>__blist` (`int64`, `(E, 2)`).
   - `<ID>__inner_p_target` (`float64`, `(E, E)`), `<ID>__colattice_weights` (`float64`, `(K,)`).
   - `<ID>__std_lattice` (`float64`, `(3, 3)`), `<ID>__std_frac` (`float64`, `(N, 3)`).
   - `<ID>__opt_lattice` (`float64`, `(3, 3)`), `<ID>__opt_frac` (`float64`, `(N, 3)`).
   - `<ID>__opt2_lattice` (`float64`, `(3, 3)`), `<ID>__opt2_frac` (`float64`, `(N, 3)`), `<ID>__energy_per_atom` (`float64`, scalar).
   - For `G10` and `G12` (`to_4structures` coverage): `<ID>__std2_lattice`, `<ID>__std2_frac`, plus `match_check4_strict` in `golden_metadata.json`.
   - `S01__final_lattice`, `S01__final_frac`, `S01__ratios_and_energy` (`float64`).

### 3.3 Design of `tests/baseline/generate_golden.py`

- **CLI Interface:** `python tests/baseline/generate_golden.py [--baseline-src /home/ordillo/tests/SLICES-upstream-baseline/src] [--verify-determinism]`
- **Self-Re-Exec Enforcement for Hash & Thread Determinism:** If `os.environ.get("PYTHONHASHSEED") != "0"` or `os.environ.get("OMP_NUM_THREADS") != "1"`, `generate_golden.py` re-executes itself in a clean `subprocess.run` with `PYTHONHASHSEED="0"`, `OMP_NUM_THREADS="1"`, `SLICES_TORCH_THREADS="1"`, `PYTHONDONTWRITEBYTECODE="1"`, and `PYTHONPATH=args.baseline_src` prepended ahead of all site-packages.
- **Worktree Integrity Verification:** Before generating fixtures, verifies `git -C /home/ordillo/tests/SLICES-upstream-baseline rev-parse HEAD` equals `94ef8e079b69c37138159805e3c701b8df87a5d7` and `git status --porcelain` is empty; verifies `slices.__file__` resolves inside `/home/ordillo/tests/SLICES-upstream-baseline/src/slices/`.
- **Instance Isolation Rule:** Instantiates a fresh `SLICES(relax_model="auto")` per corpus entry (`G01`–`G19`) and resets `np.random.seed(0)` before each `to_structures()` call. Because `relax_backends._CALCULATORS` caches compiled `(size, device)` NequIP calculators at module scope, creating a fresh `SLICES` instance takes `< 0.2 ms` while preventing stale instance attributes (`self.unstable_graph`, `self.space_group_num`, `self.atom_types` — see `DEF-BC-03`) from leaking across entries.

### 3.4 Design of `tests/baseline/test_golden_equivalence.py`

Marked with `@pytest.mark.baseline`, `test_golden_equivalence.py` enforces three strict assertion tiers plus a live dual-tree comparison mode:

#### Tier 1: Exact Discrete Invariance (`==` and `np.array_equal`)
- **Frozen Constants & Bijections:**
  - Exact SHA-256 and value equality on `config.OFFSET` (`(27, 3)`, `OFFSET[13] == [0,0,0]`), `config.LJ_PARAMS_LIST` (`118` rows), and `config.PERIODIC_DATA`.
  - Exhaustive 230-space-group round-trip `get_space_group_num_from_letter_enc("".join(get_tokenized_enc(n).split())) == n` for `n in 1..230`, plus exact `sg_encoding` dictionary match.
- **Encoding, Parsing, Validation & Canonicalization (`G01`–`G19`, `G15b`, `S03`, `E01`–`E11`):**
  - `structure2SLICES(ori, strategy=k) == golden["slices_by_strategy"][str(k)]` for `k in (1, 2, 3, 4)` (also asserting `from_cif` produces identical `atom_types`, `edge_indices`, `to_jimages`, `space_group_num` as `structure2crystal_graph_rep`).
  - `np.array_equal` on `from_SLICES` outputs (`atom_types`, `edge_indices`, `to_jimages`) and `==` on `space_group_num`.
  - Exact `bool` equality on `check_element`, `check_2D`, `check_3D`, `check_SLICES` (`dupli_check ∈ {False, True}`, `graph_rank_check ∈ {True, False}`), `check_SLICES_basic`, and `int` equality on `get_dim` and `SLICES2space_group_number`.
  - Exact `str` equality on `get_canonical_SLICES(s4, strategy=4)`, `SLICES2formula(s4)`, and `get_nbf_blist()` `nbf` text; `np.array_equal` on `blist` (`int64`) and `==` on `colattice_inds` and `unstable_graph`.
  - **Augmentation (`structure2randomSLICES`):** Asserts `set(res) == set(golden["random_slices_seed42_hashseed0"])` in-process (when `PYTHONHASHSEED` may be random under `pytest`) AND spawns a 1-second `PYTHONHASHSEED=0` subprocess check asserting exact list-order equality `res == golden["random_slices_seed42_hashseed0"]` across representative `G01` and `G06`.

#### Tier 2: Tight Numerical Invariance (`rtol=0.0, atol=1e-12` on CPU)
- Asserts `np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-12)` on:
  - `get_inner_p_target()` -> `inner_p_target` and `colattice_weights` (plus `get_inner_p_target_debug()` parity inside `tmp_path`).
  - `to_structures()` -> `std.lattice.matrix`, `std.frac_coords`, `opt.lattice.matrix`, `opt.frac_coords`, `opt2.lattice.matrix`, `opt2.frac_coords`, and `final_energy_per_atom` across all `G01`–`G19`.
  - `to_4structures()` -> `[std, std2, opt, opt2]` matrices, coordinates, and `final_energy_per_atom` on `G10` (`BaSn2`) and `G12` (`NbCoSn`).
  - `S01_overlap_preopt` -> `ratio_before`, `ratio_after`, `final_structure.lattice.matrix`, `final_structure.frac_coords`, and `trajectory.energies[-1]`.

#### Tier 3: Oxidation-State Normalization & `ElementComparator` Matching
- **Why Required:** `G01` (`examples/NdSiRu.cif`) defines oxidation-decorated site species (`Nd2+`, `Si4-`, `Ru2+`), whereas `SLICES` reconstructs neutral `Element` sites (`Nd`, `Si`, `Ru`). Calling `StructureMatcher().fit(ori, opt2)` with pymatgen's default `SpeciesComparator` returns **`False`**, whereas `SLICES.match_check*` ([core.py](file:///home/ordillo/tests/SLICES-upstream-baseline/src/slices/core.py#L2021-L2085)) normalizes via POSCAR (`Structure.from_str(s.to(fmt="poscar"), "poscar")`) and passes `comparator=ElementComparator()`, returning `'1'`.
- **Assertions:**
  1. On `G01` (`NdSiRu.cif`), explicitly assert both behaviors: default `StructureMatcher().fit(ori, opt2) is False` (documenting oxidation-state species inequality) AND `StructureMatcher(ltol=0.2, stol=0.3, angle_tol=5, primitive_cell=True, scale=True, attempt_supercell=False, comparator=ElementComparator()).fit(ori, opt2) is True`.
  2. On all `G01`–`G16`, assert exact equality on discrete match flags `match_check3_strict[:3] == golden[:3]` and `np.allclose(..., rtol=0.0, atol=1e-12)` on parsed topological Jaccard distances `[float(x) for x in match_check3_strict[3:]]`.

#### Live Dual-Tree Subprocess Runner (`test_live_dual_tree_equivalence`)
- Executes a compact shared probe helper in **two fresh subprocesses** (`PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`):
  - **Subprocess A (Reference):** `PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src`
  - **Subprocess B (Candidate):** `PYTHONPATH=/home/ordillo/tests/SLICES/src`
- Runs stratified subset `{G01, G06, G14, G15, G16, G17, G18, S01, E01..E11}` (~`8 s` per tree, `~16 s` total) by default during `pytest tests/baseline/`, and supports `--dual-tree-full` (all `G01`–`G19`, `~60 s` total) as the mandatory Stage 3, Stage 4, Stage 5, and Stage 7 sign-off gate. Asserts `assert actual_module_path.startswith(expected_tree)` in each subprocess so `egg-info` or path shadowing can never cause a false-positive self-comparison.

---

## 4. File-by-File Triage of `backup/v3-personal` Tests & New v4.0.2 Test Specifications

### 4.1 Audit of All 27 Test, Runner & CI Files in `backup/v3-personal`

Every test, configuration, and verification script in `backup/v3-personal` was inspected line by line:

| File in `backup/v3-personal` | Lines | Disposition | Bugs / Legacy Couplings Identified & Exact Stage 5 Adaptation |
|---|---:|---|---|
| `pytest.ini` | 22 | **PORT -> `pyproject.toml`** | Merge into `[tool.pytest.ini_options]` in `pyproject.toml`: keep `unit`, `integration`, `regression`, `slow`, `mlip`, `network` markers; **replace** `xtb` marker with `gfnff` and **add** `baseline` marker. Move `--cov` flags out of default `addopts` so quick `pytest -k` runs stay fast, enabling `--cov=src/slices` explicitly in CI/gate runs. |
| `.github/workflows/tests.yml` | 44 | **PORT (Rewrite in Stage 7)** | Currently commented out (`# on:`), targets Python `3.9`, uses `pip install -e ".[dev]"`, and sets `continue-on-error: true` (commits `01ee0dc..3162c99`). Update to Python `3.10+`, `uv sync --locked --extra cpu`, `ruff check src/ tests/ examples/`, and `pytest -m "not mlip"` with `continue-on-error: false`. |
| `tests/__init__.py`, `tests/{unit,integration,regression}/__init__.py` | 8 | **DIRECT PORT** | Keep package markers so `from tests.conftest import ...` or relative helpers work cleanly. |
| `tests/fixtures/structures/{NdSiRu.cif, Sr3Ru2O7.cif}` | 2 files | **DROP DUPLICATE COPIES** | Identical to kept `examples/NdSiRu.cif` and `examples/Sr3Ru2O7.cif`. Point `STRUCTURES_DIR` in `tests/conftest.py` directly to `REPO_ROOT / "examples"` (zero duplicate CIF files). |
| `tests/conftest.py` | 102 | **PORT (Adapt to v4.0.2)** | **3 fixes required:** (1) Remove top-level `TF_USE_LEGACY_KERAS="1"` env mutation (`L10-12`); (2) split `slices_backend` into `slices_no_relax` (`SLICES(relax_model=None)`, instant for encoding/validation/topology unit tests) and session/function `slices_nequip` (`SLICES(relax_model="auto")` instead of `'m3gnet'` at `L68`); (3) replace invalid placeholder `known_slices_string = "Nd Si Ru 0 1 2 0 0 0 ..."` (`L87`, unparseable in Strategy 4!) with verified `NdSiRu` Strategy-4 string from `G01`. |
| `tests/unit/test_core_encoding.py` | 202 | **DIRECT PORT (Fix 2 bugs)** | Uses `SLICES(relax_model=None)` instead of `'m3gnet'` / `'chgnet'`. **Fix Bug 1 (`L38, 41`):** `graph_methods` listed `'econ'` (not a valid `graph_method`; valid set is `['econnn', 'crystalnn', 'brunnernn', 'mininn']`, causing `UnboundLocalError` in `structure2structure_graph`) and hardcoded `relax_model='chgnet'`. **Fix Bug 2 (`L70-85`):** `test_encode_unsupported_element` assumed `structure2SLICES` calls `check_element` on `Fr` (`Z=87`); in upstream `structure2SLICES` encodes `Fr` while `check_element(s)` returns `False` — assert both explicitly. Also add test for `structure2SLICESAug_atom_order`. |
| `tests/unit/test_core_decoding.py` | 168 | **DIRECT PORT (Adapt to NequIP/GFN-FF)** | Replace `SLICES(relax_model='m3gnet')` with `slices_nequip` (`relax_model="auto"`) for full decode tests and `slices_no_relax` for `from_SLICES` parser tests. Convert `@pytest.mark.xtb` (`test_decode_requires_xtb`, `test_xtb_timeout_handling`) into `gfnff_helper` / `to_structures` tests; update exception assertions so upstream `Exception` on malformed `from_SLICES` strings matches frozen `core.py` contract (`DEF-016`). |
| `tests/unit/test_core_validation.py` | 160 | **DIRECT PORT (Fix critical bug at `L134`)** | **Bug caught at `L132-137`:** `test_check_structural_validity` passed a SLICES string `"Si O 0 1 ooo"` to `SLICES.check_structural_validity(str1)`, which expects a `pymatgen.core.Structure` and crashes with `AttributeError: 'str' object has no attribute 'lattice'` on upstream v4.0.2! Fix to test both a valid `Structure` (`min_dist > 0.5 Å -> True`) and an overlapping `Structure` (`min_dist <= 0.5 Å -> False`). Use `slices_no_relax` for instant execution. |
| `tests/unit/test_encoding_only.py` | 234 | **OBSOLETE / DROP** | Marked `@pytest.mark.skip(reason="This is a standalone script, not a pytest test")`, hardcodes `SLICES(relax_model="chgnet")`, and duplicates `test_mp20_samples.py` + `tools/benchmarks/`. Drop from `tests/unit/`. |
| `tests/unit/test_mlip_relaxer.py` | 74 | **`@pytest.mark.mlip` + MOCKED UNIT PORT** | Rewrite to test the unified Slice 2A `mlip_relaxer.py` contract **without requiring heavy downloads in default CI**: (1) mocked ASE calculator unit tests verifying `CHGNetRelaxer`, `MatterSimRelaxer`, `ORBv3Relaxer`, `MACERelaxer`, and `M3GNetRelaxer` return exact `{"final_structure", "trajectory": SimpleNamespace(energies=[total_e]), "steps", "preoptimized", "retry"}` and set `.name`, `.device`, `.optimizer`, `.description`; (2) `ImportError` actionable install-hint tests when `find_spec` returns `None`; (3) live `@pytest.mark.mlip` smoke tests skipped cleanly via `pytest.importorskip` when optional packages are absent. |
| `tests/unit/test_tobascco_net.py` | 229 | **DIRECT PORT (Align with Frozen `Net`)** | **Important freeze alignment (`L97, 107, 124, 218`):** Fork tests expected `net.get_lattice_basis()` to raise `LatticeBasisError` (`DEF-003` / `FC-01`), whereas frozen upstream `Net.get_lattice_basis()` returns `1` on success and `-1` (`net.lattice_basis is None`) on failure! Update those 4 tests to assert `res == 1` vs `res == -1` on frozen `Net`, keep `TestClearCache` (`Net.clear_cache()`) and `Net.nodes_iter(data=True)` NetworkX 3.x test (`self._graph.nodes[node]`), and move `LatticeBasisError`/`CocycleBasisError` class tests to `test_exceptions.py`. |
| `tests/unit/test_utils.py` | 35 | **SPLIT & EXPAND (`test_utils.py` + `test_utils_wyckoff.py`)** | Currently a 35-line placeholder testing only Wyckoff functions with `try/except: pass`! Move Wyckoff tests into dedicated `tests/unit/test_utils_wyckoff.py` and rewrite `tests/unit/test_utils.py` to test `slices.utils`: `temporaryWorkingDirectory`, `split_list`, `is_slurm_available`, `splitRun_local` / `collect_json` / `collect_csv` in `tmp_path` (`shutil` file ops), `_SUBMITTED_SLURM_JOBS` & `_SUBMITTED_LOCAL_PIDS` scoped job cancellation (verifying `pgrep -f python` is NEVER called!), and `adaptive_dynamic_binning`. |
| `tests/integration/test_graph_topology.py` | 93 | **DIRECT PORT (Fix `'e0'` 0-based bug)** | **Bug caught at `L37, 54, 77`:** Built `x_dat` with 0-based labels `f"e{idx}"` (`'e0'`, `'e1'`), whereas `Net.get_index` computes `int(edge[2][1:]) - 1` (expecting 1-based `'e1'`, `'e2'` as produced by `SLICES.convert_graph()`!), causing `'e0'` to wrap around to index `-1`! Fix to use `SLICES.convert_graph()` (1-based `'e1'..`), use `slices_no_relax`, and assert frozen `get_lattice_basis() == 1` on `G01`. |
| `tests/integration/test_mlip_integration.py` | 189 | **`@pytest.mark.mlip` ADAPTED PORT** | Split into: (1) default-enabled v4.0.2 NequIP integration tests (`relax_model="auto"`, `"nequip-s+l"`, `None`, `relax`, `relax_large_cell1`, and verifying `SLICES(relax_model="invalid")` raises `ValueError` instead of fork's dropped silent fallback to `'m3gnet'` at `L134-147`!); and (2) `@pytest.mark.mlip` parametrized tests over `("chgnet", "mattersim", "orbv3", "mace", "m3gnet")` skipped cleanly when uninstalled. |
| `tests/integration/test_round_trip.py` | 173 | **DIRECT PORT (Fix 3 bugs, use `nequip-s+l`)** | Replace `'m3gnet'` fixture with `slices_nequip` (`relax_model="auto"`). **Fix 3 bugs:** (1) `L41`: use `StructureMatcher(comparator=ElementComparator())` + POSCAR normalization (or `backend.match_check3`) instead of bare `StructureMatcher()` + weak `or len == len` fallback; (2) `L55`: test round-trip decoding over `strategy in [1, 3, 4]` (since `from_SLICES` has no `strategy=2` parser — `DEF-BC-04`) and explicitly test `to_SLICES(strategy=2)` encoding separately; (3) `L130`: compare `len(reconstructed)` against `len(SLICES.to_primitive_if_smaller(orig))` for conventional cells. Also add `robust_SLICES2structure` opt-in integration test. |
| `tests/integration/test_round_trip_batch.py` | 508 | **OBSOLETE / DROP** | Standalone CLI script inside `tests/integration/` with `@pytest.mark.skip` functions, TensorFlow `clear_session()` boilerplate, **and a fatal `NameError` at `L217`** (`test_round_trip(slices_backend, ...)` inside `process_structure_batch(backend, ...)` where `slices_backend` is undefined!). Superseded by upstream [examples/3.benchmark_relax_models.py](file:///home/ordillo/tests/SLICES-upstream-baseline/examples/3.benchmark_relax_models.py) and `test_golden_equivalence.py`. |
| `tests/integration/test_xtb_integration.py` | 70 | **OBSOLETE / DROP (Replaced by `test_gfnff_helper.py`)** | Imports deleted `from slices.core import xtb_custom` and tests external `xtb` binary workflow. Replaced completely in v4.0.2 by `tests/unit/test_gfnff_helper.py` (testing bundled `libgfnff.so.0.1.1` + optional mocked non-Linux `xtb` fallback). |
| `tests/regression/test_backward_compatibility.py` | 148 | **DIRECT PORT (Update v4.0.2 defaults)** | Keep signature and return-type checks (`SLICES.__init__`, `structure2SLICES`, `SLICES2structure`, `Net.__init__`). **Fix 2 assertions:** (1) `L62-63`: `SLICES().relax_model == "nequip-s+l"` on CPU (`relax_model="auto"` resolution) instead of `'m3gnet'`; (2) `L82-83`: `SLICES().relaxer.optimizer == "BFGS"` (upstream `SLICES` stores `optimizer` on `self.relaxer`, not `self.optimizer`). Add signature checks for `make_relaxer`, `resolve_relax_model`, `run_gfnff_helper`, and `slices` package exports (`__version__ == "4.0.2"`). |
| `tests/regression/test_known_structures.py` | 179 | **DIRECT PORT (Strengthen with `ElementComparator`)** | Replace `'m3gnet'` fixture with `slices_nequip`, point `structures_dir` to `examples/`, replace weak `assert is_match or len(reconstructed) == len(original)` (`L124`) with strict `backend.match_check3(...)` == `'1'`, and compare atom counts against `SLICES.to_primitive_if_smaller(original)`. |
| `tests/regression/test_mp20_samples.py` | 98 | **DIRECT PORT (Use `relax_model="auto"` & deterministic rows)** | Replace `SLICES(relax_model='chgnet')` (`L36, 73`) with `SLICES(relax_model=None)` for `test_encode_mp20_samples` and `SLICES(relax_model="auto")` for `test_round_trip_mp20_samples`, selecting deterministic 3D nonmetal rows (`band_gap > 0`, `check_element == True`, `check_3D == True`) instead of blind `nrows=3` (row 1 of `data/mp20/test.csv` is `SmThCN` with `Z=90`, and row 0 `GaTe` is 2D layered!) and asserting `success_count >= 3` instead of skipping when `0`. |
| `tools/tests/run_tests.py` | 83 | **PORT (Harden in `tools/run_tests.py`)** | Replace `subprocess.run(cmd, shell=True)` (`L20`) with explicit argument list `[sys.executable, "-m", "pytest", ...]`, and add `--baseline` (`tests/baseline/`), `--fast` (`-m "not slow and not mlip"`), and `--dual-tree` flags. |
| `tools/tests/verify_baseline.py` | 73 | **OBSOLETE / DROP** | Invokes nonexistent `test_slices_functions.py` with `--models chgnet`. Superseded by `tests/baseline/test_golden_equivalence.py`. |
| `tools/tests/run_comparison_test.py` | 418 | **PORT TO `tools/benchmarks/` (Adapt to `auto`)** | Useful A/B benchmark script comparing `SLICES2structure` vs opt-in `robust_SLICES2structure`; change default `--dataset` to `data/mp20_nonmetal/test_data_reduce_zero.csv`, default `--model` from `'orbv3'` to `'auto'`, and write outputs only to user-specified `--output-dir` (never dirtying tracked files by default). |
| `tools/tests/{test_failed_structures.py, test_improved_decoding.py, test_known_failures.py}` | 623 (3 files) | **OBSOLETE / DROP** | One-off ad-hoc scripts coupled to deleted fork logs (`docs/benchmarks/encode_decode_orbv3.log`, `train_encoded_decoded_orbv3.csv`), hardcoded `relax_model="orbv3"`, and dead code (`backend_standard.from_file` at `test_failed_structures.py:75`). Fully covered by `run_comparison_test.py` + `test_decoding_strategies.py`. |
| `tools/validate_installation.py` | 78 | **PORT (Update to v4.0.2)** | Update core checks to verify Python `>=3.10`, `numpy`, `scipy`, `pymatgen`, `networkx`, `sympy`, `ase`, `matscipy`, `slices._vendor.gfnff` (`gfnff_helper`), and `torch` + `nequip` (`SLICES(relax_model="auto")`), while listing `chgnet`, `mattersim`, `orb_models`, `mace`, `m3gnet` strictly as optional add-ons without failing exit status when optional MLIPs are absent. |
| `tools/benchmarks/{test_all_mlips.py, test_mlip_encoding_decoding.py}` | 484 (2 files) | **CONSOLIDATE / DROP DUPLICATE** | Upstream [examples/3.benchmark_relax_models.py](file:///home/ordillo/tests/SLICES-upstream-baseline/examples/3.benchmark_relax_models.py) already benchmarks any list of `--models` cleanly against MP-20 DFT formation energies! Drop `test_mlip_encoding_decoding.py` (broken POSCAR column assumption on CIF CSV at `L100-115`), and optionally adapt `test_all_mlips.py` only if standard-vs-robust multi-MLIP comparison is desired alongside `run_comparison_test.py`. |

### 4.2 Detailed Specification of New Unit Test Modules Needed for v4.0.2

In Stage 5 (`Refine`), create the following **six** fast, deterministic unit test modules under `tests/unit/` (all running in `< 5 s` total without network access):

#### 1. `tests/unit/test_relax_backends.py`
- **`resolve_relax_model` & `choose_device`:**
  - `None` and `"none"` -> `("none", None)`.
  - `"auto"` -> `"nequip-s+l"` on CPU; respects `SLICES_RELAX_MODEL` override via `monkeypatch.setenv`.
  - `SLICES_DEVICE` validation (`"cpu"`, `"cuda"` fallback to `"cpu"` when `torch.cuda.is_available()` is mocked `False`, `ValueError` on `"tpu"`).
  - Unknown model name raises `ValueError` listing both upstream `RELAX_MODELS` and optional `OPTIONAL_MLIP_MODELS`.
  - Optional MLIP names (`"chgnet"`, `"mattersim"`, `"orbv3"`, `"orb-v3"`, `"mace"`, `"mace-mp"`, `"m3gnet"`) dispatch cleanly to `mlip_relaxer` without touching `NEQUIP_PLANS`.
- **Geometry & Safety Primitives (`closest_pair_ratio`, `remove_overlaps`, `preoptimize`, `_collapse_guard`):**
  - `closest_pair_ratio`: exact value on non-overlapping cubic `NaCl` (`>= 0.5`) vs overlapping `S01` (`0.279162 < 0.5`).
  - `remove_overlaps`: verifies deterministic `seed=0` push-apart even for coincident atoms (`d == 0.0`, `tiny < 1e-3` random normal branch at `L496-499`) and `2%` lattice expansion every 20 iterations (`max_expand=1.5`) without mutating global `np.random`.
  - `preoptimize`: leaves `ratio >= 0.5` structure object untouched (`s_out is s_in`, `applied=False`); applies Niggli reduction + `remove_overlaps` when `ratio < 0.5` (and survives degenerate cells where Niggli raises).
  - `_collapse_guard`: verifies `CellCollapse` (`issubclass(CellCollapse, (RelaxBackendError, SLICESError, RuntimeError))`) on (a) volume `< min(2.0, 0.5 * V0 / N)`, (b) aspect ratio `max(lengths) > 20 * min(lengths)`, and (c) cell angle `< 5.0°`, while restoring `calc.calculate` in `__exit__` even on exception.
- **Optimizer & Collapse-Retry Execution (`_optimize`, `NequIPRelaxer.relax`):**
  - Tests all 4 `OPTIMIZERS` (`"BFGS"`, `"LBFGS"`, `"FIRE"`, `"FIRE+BFGS"` with `FIRE_PRESTEPS=10` step budget accounting) using a fast harmonic/LJ ASE dummy calculator; verifies unsupported optimizer raises `ValueError`.
  - Monkeypatches `self.relax_calc` to trigger `CellCollapse` on initial attempt and verifies `NequIPRelaxer.relax` retries once with `NequIP-OAM-S + FIRE` (`res["retry"] == 1`) and propagates `CellCollapse` if the second attempt also collapses.
- **Cache Naming, Error Formatting & CLI:**
  - Tests `_compiled_name` (`torchscript` `.nequip.pth` vs `aotinductor` `.nequip.pt2`, `-oeq`, `tf32` tags), `_short_error` truncation, and `_main()` (`--relax-model none`).

#### 2. `tests/unit/test_gfnff_helper.py`
- **`parse_nbf_text`:** Valid 22-line NBF parsing into `(int32 Z array, (20, nat) int32 nbf)`; raises `ValueError` on `< 22` non-empty lines, mismatched symbol count vs `nat`, and wrong row width.
- **`_selected_params` & `_env_default`:** Default/`"legacy86"`/`"legacy86_overlay"` resolves existing `param_gfnff_legacy86.xtb`; `"modern"`/`"internal"`/`"none"` returns `("modern", "")`; invalid `SLICES_VENDOR_GFNFF_PARAM_MODE` raises `ValueError`; nonexistent `SLICES_VENDOR_GFNFF_PARAM_FILE` raises `FileNotFoundError`; `_env_default` restores prior/unset env state upon exit or exception.
- **`run_gfnff_helper` & `write_debug_files`:**
  - Methane topology self-test (`4` sorted bonds `(2,1)..(5,1)`, `6` angles, `metadata["param_mode"] == "legacy86_overlay"`).
  - `Na3MnCoNiO6` (`G19`) target verification matching `(178.74144, 178.74144, 126, 61.23)` to `rtol=1e-6`.
  - Actinide NBF (`Th`, `Z=90`) evaluating finitely without crashing (`Z=87..103` fallback).
  - `write_debug_files(nbf, data, directory=tmp_path)` writes valid `testBonds_cut.top` and `gfnff_lists.json`.
  - Cross-platform fallback unit test (Stage 4): monkeypatches `slices._vendor.gfnff` import to raise `OSError` and verifies clean `GFNFFExecutionError` when no external `xtb` binary is configured, vs subprocess fallback when a mock `SLICES_XTB_PATH` script is provided.

#### 3. `tests/unit/test_utils_wyckoff.py`
- **Exhaustive 230-Space-Group Bijection:** Iterates `sg_num in range(1, 231)` asserting `tok = get_tokenized_enc(sg_num)` is non-empty, space-delimited, contains **zero tokens accepted by `pymatgen.core.Element(t)`** (critical invariant ensuring `SLICES._first_element_index` never mistakes a space-group token for an element symbol!), and satisfies `get_space_group_num_from_letter_enc("".join(tok.split())) == sg_num`.
- **Symbol Table & Error Paths:** Verifies every entry in `sg_encoding` has `1 <= int_number <= 230` and `get_space_group_num(props["enc"]) == props["int_number"]`; verifies `get_tokenized_enc(0)`, `get_tokenized_enc(231)`, `get_space_group_num("INVALID")`, and `get_space_group_num_from_letter_enc("qqq")` raise `ValueError`.

#### 4. `tests/unit/test_exceptions.py`
- **Hierarchy & Dual-Inheritance Contract:**
  - Verifies `issubclass(cls, SLICESError)` for `SLICESEncodingError`, `SLICESDecodingError`, `GraphTopologyError`, `LatticeBasisError`, `CocycleBasisError`, `GFNFFExecutionError`, `XTBExecutionError`, `MLIPRelaxationError`, `TimeoutException`, `RelaxBackendError`, and `ModelDownloadError`.
  - Verifies `issubclass(LatticeBasisError, GraphTopologyError)` and `issubclass(CocycleBasisError, GraphTopologyError)`.
  - Verifies `XTBExecutionError is GFNFFExecutionError`.
  - Verifies `issubclass(RelaxBackendError, RuntimeError)`, `issubclass(ModelDownloadError, RuntimeError)`, and `not issubclass(ModelDownloadError, RelaxBackendError)` (preserving `relax_backends.py:194` invariant that network failures are never cached as `.failed` compilation markers!).
- **Re-exports & `function_timeout`:**
  - Verifies top-level `from slices import SLICES, __version__, SLICESError, ...` (`__version__ == "4.0.2"`).
  - Verifies `@function_timeout(seconds=1)` on POSIX main thread raises `TimeoutException` (fixing upstream `F821` `NameError` `DEF-007`) and clears `signal.alarm(0)` in `finally:`; verifies non-main-thread execution runs cleanly without `ValueError: signal only works in main thread`.

#### 5. `tests/unit/test_cli.py`
- **Subcommands via `slices.cli.main(argv)` using `tmp_path`:**
  - `encode`: encodes `examples/NdSiRu.cif` to `tmp_path / "out.slices"` and stdout; monkeypatches `make_relaxer` to assert `relax_model=None` is passed (zero NequIP load overhead).
  - `validate`: returns exit code `0` (`VALID`) on `G01` SLICES and exit code `1` (`INVALID`) on `E03_bad_sg_prefix` and `E06_rank_h1_lt_3_1d` (fixing fork exit-code `0` bug!).
  - `canonicalize`: writes canonical SLICES matching `get_canonical_SLICES` with `relax_model=None`.
  - `decode`: tests `--model none` / `--model auto` (`G14` 1-atom `Na` in `0.24s`), `--output out.cif`, `--robust` dispatch, and exit code `1` on missing file / malformed SLICES without unhandled tracebacks unless `--verbose` is set.

#### 6. `tests/unit/test_decoding_strategies.py`
- **Strict Freeze Isolation Guard:** Monkeypatches `slices.decoding_strategies` with a sentinel spy and executes `SLICES(relax_model=None).to_structures()` and `SLICES(relax_model="auto").SLICES2structure(G10)` to prove **zero** functions from `decoding_strategies` are imported or called during default decoding.
- **Unit Verification of All 5 Fixed Fork Bugs (from [AUDIT_FORK_DIFF.md Section 5.2](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md#L228-L246)):**
  1. `MultiStartOptimizer.optimize`: runs cleanly on `scipy==1.15.3` (no `iprint`/`disp`), deterministic under `seed=0`, and leaves global `np.random.get_state()` unchanged.
  2. `CycleBasisOptimizer.is_approximately_integral`: returns `True` on mixed-sign near-integer vector `np.array([1.0 + 1e-8, 2.0 - 1e-8])` (which failed fork's non-elementwise `np.all(...) or np.all(...)`) and returns `False` on near-zero `[1e-9, -1e-9]`.
  3. `find_lattice_basis_with_retries`: deterministic `seed=0` search without mutating `tobascco_net.Net`.
  4. `BondParameterFallback`: correctly maps 1-based `3x3x3` supercell indices (`blist_original[i] > n_atom`) without `IndexError`.
  5. `robust_SLICES2structure`: restores `backend.fmax` and `backend.steps` after `ProgressiveRelaxer` even if relaxation raises, and never calls `from_SLICES(..., strategy=2)`.

---

## 5. Deferred Core / Algorithm Candidates (Slice 2C Additions for `DEFERRED_CORE_REGISTER.md`)

All 20 existing entries in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) (`DEF-001`–`DEF-020`) were cross-checked to avoid duplication. Empirical probing and code audit in Slice 2C identified **7 net-new core/algorithmic quirks** in upstream v4.0.2 (`94ef8e0`), ready for `@scribe` to ingest sequentially as **`DEF-021`–`DEF-027`**:

### `DEF-BC-01` (Proposed `DEF-021`) — `check_SLICES()` Silently Returns `True` When `Net.get_lattice_basis()` Returns `-1` or `Net.get_cocycle_basis()` Fails
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L549-L559) (`SLICES.check_SLICES`) & [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L233-L235), [L536-L541](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L536-L541) (`Net.get_cocycle_basis`, `Net.get_lattice_basis`; cross-ref `DEF-003`)
- **Category:** `Graph`, `Math`, `Compatibility`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** At the end of `check_SLICES()`, lines `554-556` execute:
  ```python
  net.simple_cycle_basis()
  net.get_lattice_basis()
  net.get_cocycle_basis()
  ```
  inside a `try ... except: return False` block, assuming failure raises an exception. However, in upstream `tobascco_net.py`, `Net.get_lattice_basis()` logs `"Could not obtain the lattice basis from the cycle vectors!"` and **returns `-1` without raising** (leaving `net.lattice_basis = None`), and `Net.get_cocycle_basis()` prints `"ERROR - could not find a linearly independent cocycle basis!"` without raising when `count != size`. Consequently, `check_SLICES()` **returns `True`** on graphs that have no valid 3D lattice basis! When `to_structures()` or `SLICES2space_group_number()` is subsequently called on that "valid" SLICES string, `net.get_metric_tensor()` crashes with `TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'`. Empirically reproduced on quasi-1D/2D MP-20 crystals (`TiBr3` `mp-28214` row `464`, `MnBr2` `mp-569843` row `199`, and `GaTe` `mp-10009` row `0` in `data/mp20/test.csv`; captured as edge case `E11`).
- **Why Deferred under Baseline Freeze:** Checking `if net.get_lattice_basis() == -1: return False` in `check_SLICES()` changes boolean validity results relative to upstream v4.0.2 across generative-model validity benchmarks (`benchmark/Validity_rate_ucRNN__Success_rate_cRNN/`). Must remain frozen during migration and be locked down by `E11` in `test_golden_equivalence.py`.
- **Proposed Post-Baseline Investigation / Fix:** Quantify how many generated SLICES strings in the RNN/MatterGPT benchmarks pass `check_SLICES()` solely due to ignored `get_lattice_basis() == -1` / `count != size`, then make `check_SLICES()` explicitly check `if net.get_lattice_basis() == -1: return False` (and `net.cocycle` rank) and raise `LatticeBasisError` in `to_structures()` instead of `NoneType * float` `TypeError`.
- **Impact Risk:** **High** — directly changes `check_SLICES()` boolean acceptance rate on borderline/low-dimensional periodic graphs.

---

### `DEF-BC-02` (Proposed `DEF-022`) — `structure2randomSLICES()` Output Order Depends on Process-Global `PYTHONHASHSEED`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L741-L845) (`SLICES.structure2randomSLICES`, lines `741` and `843-845`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** `structure2randomSLICES()` accumulates unique augmented strings in `SLICES_set = set()` (`L741`), then converts `SLICES_list = list(SLICES_set)` (`L843`) before calling `random.shuffle(SLICES_list)` (`L844`) and slicing `SLICES_list[:num]`. Because CPython randomizes string `hash()` salts at interpreter startup unless `PYTHONHASHSEED` is set, `list(SLICES_set)` produces a different pre-shuffle ordering in every new Python process even when the caller seeds `random.seed(42)` immediately beforehand (empirically verified: `16/16` corpus structures differed in list order across two unseeded-hash processes, and `16/16` matched identically once `PYTHONHASHSEED=0` was set).
- **Why Deferred under Baseline Freeze:** Replacing `list(SLICES_set)` with `sorted(SLICES_set)` (or preserving insertion order via `dict.fromkeys`) would alter the exact permutation returned under `PYTHONHASHSEED=0` relative to upstream v4.0.2.
- **Proposed Post-Baseline Investigation / Fix:** Replace `SLICES_set = set()` with an insertion-ordered `dict` (or `sorted(SLICES_set)` before `rng.shuffle` using an explicit `seed: int | None = None` parameter and isolated `random.Random(seed)`) so augmentation is 100% deterministic across processes regardless of `PYTHONHASHSEED`.
- **Impact Risk:** **Low–Medium** — affects only ordering/subset selection when `len(SLICES_set) > num` or across processes with distinct `PYTHONHASHSEED`.

---

### `DEF-BC-03` (Proposed `DEF-023`) — `SLICES2space_group_number()` Reads Stale `self.unstable_graph` Flag from Prior `to_structures()` Calls
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L110), [L1332-L1335](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1332-L1335), [L1746-L1750](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1746-L1750) (`SLICES.SLICES2space_group_number`)
- **Category:** `Graph`, `Runtime`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** `self.unstable_graph` is initialized to `False` in `SLICES.__init__` and updated *only* inside `get_rescaled_lattice_vectors()` (`core.py:1332-1335`) when `np.diag(inner_p_std)` has entries `<= 0.0001`. `SLICES2space_group_number()` bypasses `get_inner_p_target()` and `get_rescaled_lattice_vectors()`, yet checks `if self.unstable_graph:` at line `1746` (`net.cocycle_rep = np.zeros((net.order-1, net.ndim)) + .5`). Thus: (a) on a fresh `SLICES` instance, `self.unstable_graph` is *always* `False` inside `SLICES2space_group_number()` even if the current graph has zero-length barycentric edges; and (b) if the same `SLICES` instance previously decoded an unstable graph (`G18` `YHO2`) via `to_structures()`, `self.unstable_graph` remains `True` and contaminates subsequent `SLICES2space_group_number()` calls!
- **Why Deferred under Baseline Freeze:** Computing `inner_p_std` locally inside `SLICES2space_group_number()` to set `unstable_graph` per call would change `SLICES2space_group_number()` outputs on unstable graphs (`G18`) relative to fresh-instance v4.0.2 behavior.
- **Proposed Post-Baseline Investigation / Fix:** Compute `inner_p_std = np.dot(np.dot(net.lattice_arcs, net.metric_tensor), net.lattice_arcs.T)` locally inside `SLICES2space_group_number()` (without mutating `self.unstable_graph`), and reset all per-decode transient attributes cleanly at the start of `from_SLICES()`.
- **Impact Risk:** **Medium** — causes instance-reuse state leakage and inconsistent space-group prediction on barycentrically degenerate nets.

---

### `DEF-BC-04` (Proposed `DEF-024`) — `from_SLICES()` Missing Strategy-2 Parser & Unvalidated Token/Index Boundaries
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L202-L332) (`SLICES.from_SLICES`) vs [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L372-L386) (`SLICES.get_slices2`; cross-ref `DEF-016`, `DEF-019`)
- **Category:** `Compatibility`, `Runtime`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** Four input-validation gaps exist in `from_SLICES()`:
  1. **No `strategy == 2` branch or `else:` guard:** `to_SLICES(strategy=2)` / `get_slices2` encodes compact fixed-width strings (`'Si_O_0001ooo'`), but `from_SLICES` only implements `if strategy==3:`, `if strategy==1:`, and `if strategy == 4:`. Calling `from_SLICES(s, strategy=2)` (or `strategy=99`) falls through to `self.edge_indices = edge_indices` at `L330` and raises `UnboundLocalError: local variable 'edge_indices' referenced before assignment` (which crashed both fork's `robust_SLICES2structure` and `test_round_trip.py:55`).
  2. **Zero-edge strings (`"Si O"`):** In `strategy == 3` (`L219-223`) and `strategy == 4` (`L290-296`), if no token satisfies `.isnumeric()`, `num_atoms` is never assigned, raising `UnboundLocalError`.
  3. **Silent truncation of trailing tokens & extra label chars:** `int((len(tokens) - start_idx) / 3)` (and `/5`, `/7`) silently discards 1–2 trailing tokens when token count is not a multiple of edge width, and `for j in range(3): edge[2][j]` silently ignores extra characters in `len(edge[2]) > 3` (e.g., `'oooo'`).
  4. **Negative node indices:** `edge_indices[i,0] > num_atoms - 1` (`L231, 259, 306`) does not check `< 0`, allowing `"-1"` in subsequent edges to pass `int("-1")` and wrap around negative indices.
- **Why Deferred under Baseline Freeze:** Tightening token-length or edge-label checks in `from_SLICES` could reject noisy LLM/RNN-generated strings that currently parse (via truncation) in `benchmark/` scripts.
- **Proposed Post-Baseline Investigation / Fix:** Implement `strategy == 2` parsing (or raise an explicit `ValueError("strategy=2 is encode-only")`), validate `strategy in {1, 2, 3, 4}`, initialize `num_atoms = None` with a clean `SLICESDecodingError` if missing, check `0 <= idx < num_atoms`, and require exact edge-tuple multiples and `len(edge[2]) == 3` (optionally gated by `strict: bool = False` if lenient LLM parsing is desired).
- **Impact Risk:** **Medium** — affects error types and malformed-string rejection on generated SLICES inputs.

---

### `DEF-BC-05` (Proposed `DEF-025`) — `check_structural_validity()` Always Returns `True` on Single-Atom Cells Regardless of Lattice Collapse
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L449-L470) (`SLICES.check_structural_validity`; cross-ref `DEF-019`)
- **Category:** `Math`, `Compatibility`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** `check_structural_validity(str1)` computes `distance_matrix = str1.lattice.get_all_distances(str1.frac_coords, str1.frac_coords)` and scans strictly upper-triangular site pairs `for i in range(rows): for j in range(i+1, cols):`. When `len(str1) == 1` (single-atom primitive cell, e.g., `G14` `Na` or elemental metals), `rows == 1`, the inner loop executes zero times, `min_value` stays at `10000000`, and the method returns `True` even if a lattice vector length `min(str1.lattice.abc) <= 0.5 Å` places periodic self-images `< 0.5 Å` apart! (For multi-atom cells, periodic self-image distances `< 0.5 Å` along short lattice vectors are likewise ignored because diagonal self-image distances are `0.0` in `get_all_distances`.)
- **Why Deferred under Baseline Freeze:** `check_structural_validity` is used directly in historical validity-rate benchmarks; altering its distance check changes structural validity counts on 1-atom or short-axis cells.
- **Proposed Post-Baseline Investigation / Fix:** Also check `min(str1.lattice.abc) > 0.5` (or use `str1.get_neighbor_list(r=0.5)` excluding `[0,0,0]` self-site) so collapsed 1-atom and short-axis cells are detected accurately.
- **Impact Risk:** **Low–Medium** — affects only degenerate cells with lattice vector length `<= 0.5 Å`.

---

### `DEF-BC-06` (Proposed `DEF-026`) — Invalid `graph_method` Prints Error Message Instead of Raising `ValueError`, Then Crashes with `UnboundLocalError`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L186-L200) (`SLICES.structure2structure_graph`) and [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L856-L867) (`SLICES.get_dim`)
- **Category:** `Runtime`, `Compatibility`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** When `SLICES(graph_method=...)` is given an unrecognized method name (e.g., `'econ'` in `backup/v3-personal:tests/unit/test_core_encoding.py:38`), `SLICES.__init__` accepts it without validation, and both `structure2structure_graph` (`L199`) and `get_dim` (`L865`) execute `else: print("ERROR - graph_method not implemented")` and immediately reference unassigned local variable `structure_graph` / `bonded_structure`, raising `UnboundLocalError`!
- **Why Deferred under Baseline Freeze:** Stage 3 Review can decide whether validating `graph_method in {"econnn", "crystalnn", "brunnernn", "mininn"}` (raising `ValueError` in `structure2structure_graph` / `get_dim` or `__init__`) is an approved non-math cleanup (like `DEF-007`) or deferred. Zero impact on valid `graph_method` values.
- **Proposed Post-Baseline Investigation / Fix:** Validate `graph_method` against `VALID_GRAPH_METHODS = ("econnn", "crystalnn", "brunnernn", "mininn")` and raise `ValueError(f"Unknown graph_method {self.graph_method!r}; choose from {VALID_GRAPH_METHODS}")`.
- **Impact Risk:** **Low** — zero impact on valid inputs; replaces broken `print` + `UnboundLocalError` on invalid `graph_method`.

---

### `DEF-BC-07` (Proposed `DEF-027`) — Debug Objective `func_check()` Lacks the `epsilon2` / `r_temp` Zero-Distance Guards Added to `func()`
- **Source / Location:** `upstream/main` (`94ef8e0`), [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1611-L1672) (`SLICES.func_check`, lines `1660` and `1669-1670`) vs [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1588-L1607) (`SLICES.func`, commit `2635bcc`)
- **Category:** `Math`, `Runtime`
- **Status:** `Frozen — Deferred`
- **Observed Behavior:** Upstream commit `2635bcc` hardened `func()` against `ZeroDivisionError` / `NaN` during L-BFGS-B line searches by clamping `np.sqrt(max(inner_p[i][j], 1e-10))` (`L1593`) and `if r_temp < 1e-8: r_temp = 1e-8` (`L1604-1605`). However, `func_check()` (invoked at `to_structures()` `L1897` when `self.check_results=True`) was not updated and still computes `np.sqrt(inner_p[i][j])` (`L1660`) and `(uncovered_pair_lj[i][1] / r_temp) ** 12` (`L1670`) unclamped, risking `ZeroDivisionError` or `RuntimeWarning: invalid value encountered in sqrt` when `check_results=True` is enabled on degenerate geometries.
- **Why Deferred under Baseline Freeze:** `func_check()` is inside frozen `core.py`; leave untouched during baseline migration unless approved in Stage 3 Review, and synchronize `func_check()` clamping with `func()` post-baseline.
- **Impact Risk:** **Low** — affects only `check_results=True` diagnostic mode on zero-distance edge/pair geometries.

---

## 6. Stage 3 & Stage 5 Execution Checklist for Golden Baseline & Test Suite

1. **Stage 3 (`Review` — Pre-Refactor Baseline Lock):**
   - Implement `tests/baseline/corpus_manifest.json`, `tests/baseline/generate_golden.py`, and `tests/baseline/test_golden_equivalence.py` per **Section 3**.
   - Run `generate_golden.py` against `/home/ordillo/tests/SLICES-upstream-baseline/src` (`94ef8e0`) to write `golden_metadata.json` and `golden_arrays.npz`.
   - Verify `pytest tests/baseline/test_golden_equivalence.py --dual-tree-full` passes **100%** (`0` discrete mismatches, `atol=1e-12` numerical invariance, `~60 s` dual-tree runtime) *before* any edit is made to `src/slices/` in Stage 4.
2. **Stage 4 (`Refactor` — Continuous Equivalence Gate):**
   - Run `pytest tests/baseline/test_golden_equivalence.py` after every refactor batch (`MatterGPT/` pruning, CJK translation, `exceptions.py` + `mlip_relaxer.py` + `decoding_strategies.py` + `cli.py` + `utils.py` merge) to verify zero behavioral drift on the frozen core.
3. **Stage 5 (`Refine` — Full Unit/Integration/Regression Suite):**
   - Port the triaged `tests/{conftest.py, unit/, integration/, regression/}` files with all **9 legacy test bugs fixed** (Section 4.1) and implement all **6 new unit test modules** (`test_relax_backends.py`, `test_gfnff_helper.py`, `test_utils_wyckoff.py`, `test_exceptions.py`, `test_cli.py`, `test_decoding_strategies.py`) per Section 4.2.
   - Verify `pytest -m "not mlip"` passes 100% with zero skipped-by-accident regressions and `ruff check src/ tests/ examples/` reports zero diagnostics.
