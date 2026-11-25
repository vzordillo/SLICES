# First-Principles Empirical Re-Evaluation: Core Math & Numerical Optimization

**Evaluator:** `eval-math`  
**Target Commit:** `HEAD=fa4cfc8` (`slices-4-personal`, clean working tree; upstream baseline `v4.0.2` @ `94ef8e0`)  
**Source Register:** [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md)  
**Scope:** Independent mathematical audit and non-destructive runtime A/B experimentation (`/dev/shm/reeval-math/`, `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, CPU `NequIP-OAM-S/L 0.1` + bundled `libgfnff 0.1.1`) across **`DEF-001`**, **`DEF-014`**, **`DEF-011`**, **`DEF-025`**, **`DEF-027`**, and **`DEF-006`**.

---

## 1. Executive Summary & Re-Evaluation Verdicts

| ID | Refactored Coordinates (`HEAD=fa4cfc8`) | Pre-Stage-4 Register Lines | Empirical Finding Summary | Baseline Golden Drift (`89/89`) | Re-Evaluation Verdict |
|---|---|---|---|---|---|
| [`DEF-011`](#2-def-011--pending-deprecated-npmatrixi-in-tobascco_netpy) | [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L433), [L832](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L832), [L842](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L842), [L875](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L875) | `L478, 954, 964, 993` | `np.linalg.inv` is **bit-identical (`0.000e+00` max abs diff, `0` ULP)** across `2,374/2,374` MP-20 crystals and `19/19` Golden crystals (`0` `DEF-014` flips). Conversely, `np.linalg.pinv` drifts up to `6.50e-11` and flips `DEF-014` on `231/2,366` (`9.76%`) crystals. | **`0.0` (`0` ULP)** | **`SAFE_NOW`** *(using `np.linalg.inv`, never `pinv`)* |
| [`DEF-027`](#3-def-027--func_check-missing-func-zero-distance-clamping-guards) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1911-L2036) vs [L1845-L1909](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1845-L1909) | `L1611-1672` vs `L1588-1609` | Zero calls when `check_results=False`. On real Golden `G18` (`YHO2`) at `cocycle=0`, `func()` returns finite `18.30266` while `func_check()` emits `0.0 * inf -> nan` (`L1958, L1976`) and `0.0 / 0.0 -> nan` (`L1993`). | **`0.0` (`0` ULP)** | **`SAFE_NOW`** |
| [`DEF-025`](#4-def-025--check_structural_validity-periodic-self-image-blind-spot) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L620-L636) | `L449-470` | Fails (`True`) on 1-atom short cells (`a=0.3 Å`), 2-atom short-axis cells, and **sheared cells where `min(abc) > 0.5 Å` but `\|a - b\| <= 0.5 Å`** (`niggli_min=0.296 Å`). `get_neighbor_list(r=0.5+1e-9)` fixes all cases (`91.5 µs`/call) with `0/59` Golden and `0/18,093` MP-20 CIF changes. | **`0.0` (`0` flips)** | **`SAFE_NOW`** *(must use `get_neighbor_list`, not `min(abc)`)* |
| [`DEF-014`](#5-def-014--exact-ieee-754-float-set-lattice_type-classifier) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2220-L2233) | `L1868-1877` | **`1,734 / 2,366` (`73.29%`)** of MP-20 crystals (`98.1%` of cubic, `94.3%` of hexagonal, `87.0%` of tetragonal) lose symmetry constraints due to `1.6e-16..1.0e-13` rounding noise, separated from real anisotropy by a **7-decade empty gap (`0` pairs in `(1e-13, 1e-9]`)**. `isclose(1e-9)` cuts runtime `-11.7%` with `0` match flips and `max \|dE\| = 0.27 meV/atom`. | Shifts `5/48` flipped `opt_lat` by `3.9e-8..2.8e-5 Å` (`> 1e-12`) | **`HIGH_VALUE_AB`** |
| [`DEF-006`](#6-def-006--check_element-z--87-vs-gfn-ff--nequip-oam-element-coverage) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L246-L260), [gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py#L105-L135), [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L454-L462) | `core.py:138-151` | True v4.0.2 support is **3-tiered**: `check_element` (`1..86`), `libgfnff` (`1..103`; **`Z >= 104` reads out-of-bounds Fortran memory!**), and `NequIP-OAM-S/L` (**89 elements `{1..83, 89..94}`** — crashes with `KeyError` on `Po, At, Rn` `84..86` and `Am..Lr` `95..103`, while `6/6` real MP-20 `Ac..Pu` actinide crystals decode at `100%` strict match!). | Breaks `G16` & `S03` golden assertions if default altered | **`VERSIONED_OPT_IN`** *(+ **`SAFE_NOW`** `Z <= 103` guard in `gfnff_helper`)* |
| [`DEF-001`](#7-def-001--heteronuclear-lj-i0-twice-indexing-in-corepy) | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1550-L1595) (`L1569-1572, L1589-1592`) & [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L557-L558) | `core.py:1293-1294, 1312-1313` | **Column 1 of `LJ_PARAMS_LIST` is $\sigma$ (Å), NOT $\varepsilon$!** Both columns are lengths `[4*sigma, sigma]`, so arithmetic mean on both columns **is** exact Lorentz–Berthelot mixing. Across `68` crystals (`19` Golden + `49` stratified MP-20), fixing `DEF-001` restores atom-permutation invariance and cuts mean `f(x0)` `11.5×`, but is **neutral on `match_check3` recovery (`62/68` strict, `63/68` loose; `0` flips; `median \|dE\| = 5.1e-7 eV/atom`)**. | Shifts `opt` on `52/68` (`14/19` Golden) up to `0.110` frac | **`VERSIONED_OPT_IN`** *(preserve v4.0.2 default; use arithmetic Lorentz only)* |

---

## 2. `DEF-011` — Pending-Deprecated `np.matrix(...).I` in `tobascco_net.py`

### 2.1 Verified Source Coordinates at `HEAD=fa4cfc8`
- [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L431-L454): `Net.linear_independent_vectors` (`L433`: `mat = np.matrix(r_mat)`)
- [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L828-L835): `Net.eon_projection` (`L832`: `d_inv = np.array(np.matrix(d).I)`)
- [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L838-L843): `Net.projection` (`L842`: `d_inv = np.array(np.matrix(d).I)`)
- [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py#L870-L876): `Net.cycle_cocycle_I` (`L875`: `self._cycle_cocycle_I = np.array(np.matrix(self.cycle_cocycle).I)`)

### 2.2 First-Principles Algebraic & NumPy Dispatch Analysis
In NumPy (`numpy/matrixlib/defmatrix.py`), `matrix.I` (`getI`) is implemented as:
```python
func = inv if self._shape[0] == self._shape[1] else pinv
return asmatrix(func(self))
```
Every matrix inverted by `Net` is **strictly square**:
1. `self.cycle_cocycle`: stacked fundamental cycle basis $(E - V + 1) \times E$ and cocycle basis $(V - 1) \times E$, giving shape $E \times E$ (invertible for every connected quotient graph).
2. `d = np.dot(self.kernel, self.kernel.T)` in `eon_projection`: Gram matrix of the $(E - 3) \times E$ kernel basis, shape $(E - 3) \times (E - 3)$.
3. `d = np.dot(la.T, la)` in `projection`: Gram matrix of fractional edge displacements $L_a \in \mathbb{R}^{E \times 3}$, shape $3 \times 3$.

Because `np.matrix(A)` wraps a C-contiguous `float64` `ndarray` without altering memory layout and `getI()` calls `np.linalg.inv` (LAPACK `dgesv`) on that exact buffer before `np.array(...)` strips the `matrix` wrapper, replacing `np.array(np.matrix(A).I)` with `np.linalg.inv(A)` executes the **identical LAPACK instruction stream**. Conversely, replacing `.I` with SVD-based `np.linalg.pinv(A)` changes the factorization from LU (`dgesv`) to SVD (`dgesdd`), injecting `10^-15..10^-11` rounding differences.

### 2.3 Empirical Benchmark (`19` Golden + `2,383` MP-20 Benchmark Crystals)
Evaluated across all `19` Golden Corpus entries (`18` with `cocycle_rep is not None`) and all `2,383` rows of [mp20_v4_benchmark_2383.csv](file:///home/ordillo/tests/SLICES/data/mp20_nonmetal/mp20_v4_benchmark_2383.csv) (`2,374` valid Net + GFN-FF embeddings, `2,366` with `cocycle_rep is not None`; 16 worker processes, `159.29 s` total wall clock including `DEF-014` sweep):

| Replacement Candidate | Quantity | MP-20 `max_abs_diff` (`n=2,374`) | MP-20 Nonzero Diffs | MP-20 `DEF-014` Exact Flips (`n=2,366`) | Golden 19 `max_abs_diff` (`std` & `opt`) | Golden 19 `DEF-014` Flips |
|---|---|---|---|---|---|---|
| **`np.linalg.inv`** | `cycle_cocycle_I` | **`0.000e+00`** | **`0 / 2,374`** | — | `0.000e+00` | — |
| **`np.linalg.inv`** | `eon_projection` | **`0.000e+00`** | **`0 / 2,374`** | — | `0.000e+00` | — |
| **`np.linalg.inv`** | `projection` | **`0.000e+00`** | **`0 / 2,374`** | — | `0.000e+00` | — |
| **`np.linalg.inv`** | `net.metric_tensor` | **`0.000e+00`** | **`0 / 2,374`** | — | `0.000e+00` | — |
| **`np.linalg.inv`** | `metric_tensor_std` | **`0.000e+00`** | **`0 / 2,374`** | **`0 / 2,366` (`0.00%`)** | **`0.000e+00`** (`opt_lat`: `0.000e+00`) | **`0 / 18`** |
| `np.linalg.pinv` *(unsafe)* | `cycle_cocycle_I` | `5.732e-15` | `2,366 / 2,374` | — | — | — |
| `np.linalg.pinv` *(unsafe)* | `eon_projection` | `1.399e-14` | `2,364 / 2,374` | — | — | — |
| `np.linalg.pinv` *(unsafe)* | `projection` | `2.698e-14` | `2,373 / 2,374` | — | — | — |
| `np.linalg.pinv` *(unsafe)* | `net.metric_tensor` | `1.333e-13` | `2,355 / 2,374` | — | — | — |
| `np.linalg.pinv` *(unsafe)* | `metric_tensor_std` | **`6.497e-11`** | `2,371 / 2,374` | **`231 / 2,366` (`9.76%`)** | `2.444e-12` | **`2 / 18` (`G12`, `G16`)** |

**Additional Audit Finding on `Net.linear_independent_vectors` (`L431-L454`):**
- Repo-wide scan across `src/`, `tests/`, `examples/`, `tools/`, `benchmark/`, and `HTS/` confirms **zero callers** (`0` invocations; dead inherited `tobascco` helper).
- Replacing `mat = np.matrix(r_mat)` with `mat = np.atleast_2d(np.asarray(r_mat))` and `float(np.dot(mat[:, i], mat[:, j]))` gives `max_abs_diff = 0.000e+00` on square full-rank inputs. (Note: upstream `linear_independent_vectors` also has a latent `IndexError` on rank-deficient rectangular matrices such as shape `(3, 4)` of rank `2` because `index = np.zeros(r)` overflows when `counter` increments across `> r` non-collinear adjacent column pairs.)

### 2.4 Verdict: **`SAFE_NOW`**
Contrary to the conservative Stage 2 assumption that `DEF-011` had to wait on `DEF-014`, migrating `np.array(np.matrix(...).I)` to `np.linalg.inv(...)` (never `pinv`) and `np.matrix(r_mat)` to `np.atleast_2d(np.asarray(r_mat))` produces **zero ULP drift (`0.000e+00`)** across all 2,374 MP-20 crystals and all 19 Golden Corpus structures (`89/89` golden tests pass bit-for-bit) while eliminating NumPy's `PendingDeprecationWarning` ahead of NumPy's `matrix` removal.

---

## 3. `DEF-027` — `func_check` Missing `func` Zero-Distance Clamping Guards

### 3.1 Verified Source Coordinates & Exact Divergence at `HEAD=fa4cfc8`
- `SLICES.func`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1845-L1909) (hardened in upstream commit `2635bcc`)
- `SLICES.func_check`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1911-L2036) (invoked exclusively at [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2297-L2324) under `if self.check_results:`)

Exact line-by-line mathematical divergence at `HEAD=fa4cfc8`:

| Term | `SLICES.func()` (`L1881-L1908`) | `SLICES.func_check()` (`L1954-L2035`) | Failure Mode in `func_check()` |
|---|---|---|---|
| Covered bond $r^{-12}$ (`square_diff`) | `covered_pair_lj[i][1] / np.sqrt(max(inner_p[i][j], 1e-10))` (`L1890`) | `covered_pair_lj[i][1] / np.sqrt(inner_p[i][j])` (`L1958`) | When `inner_p[i][i] == 0.0` and default `vbond_param_ave_covered == 0.0`, computes `4 * 0.0 * inf = nan`, **poisoning the returned objective to `NaN`!** When `inner_p[i][i] < 0` (`~ -1e-18` float noise), `np.sqrt` yields `nan`. |
| Covered bond $r^{-12}$ (`print`) | *(not printed)* | `round(4 * vbond_param_ave_covered * (covered_pair_lj[i][1] / np.sqrt(inner_p[i][j])) ** 12, 5)` (`L1973-L1978`) | Emits `RuntimeWarning: divide by zero` + `invalid value encountered in scalar multiply` and prints `nan`. |
| Off-diagonal angle $\cos\theta$ (`print`) | *(uses `inner_p[i][j] - mat_target[i][j]` only, `L1894`)* | `inner_p[i][j] / np.sqrt(inner_p[i][i]) / np.sqrt(inner_p[j][j])` (`L1993`) | When `inner_p[i][i] == 0.0`, computes `0.0 / 0.0 = nan` (`RuntimeWarning: invalid value encountered in scalar divide`). |
| Uncovered pair $r^{-12}$ (`square_diff` & `print`) | `r_temp = max(r_temp, 1e-8)` (`L1905`) before `(uncovered_pair_lj[i][1] / r_temp) ** 12` | Unclamped `(uncovered_pair_lj[i][1] / r_temp) ** 12` (`L2020`, `L2031`) | When two non-bonded atoms coincide (`r_temp == 0.0`), yields `inf` (`np.float64`) or raises `ZeroDivisionError` (Python `float`), or `nan` if `vbond_param_ave == 0.0`. |

### 3.2 Empirical Reproduction on Real Golden Corpus Entry `G18` (`YHO2`)
Golden Corpus entry `G18` (`YHO2`, barycentrically degenerate `unstable_graph=True`) has exact zero-length barycentric edges (`min(diag(inner_p_std)) == 0.000e+00`) at zero cocycle (`cocycle_rep = 0`):
- **Case 1 (`G18` at `cocycle=0`, `repul=True`, default `vbond_param_ave_covered=0.0`):**
  - `s.func(x_zero, ...)` -> **`18.302660`** (clean finite `float`, zero warnings)
  - `s.func_check(x_zero, ...)` -> **`nan`** (emits 5 NumPy `RuntimeWarning`s at `core.py:1956, 1958, 1974, 1976, 1993` because `0.0 * (sigma / 0.0)**12 == nan`)
- **Case 2 (`G18` at `cocycle=0`, `repul=False`, `vbond_param_ave_covered=0.0`):**
  - `s.func(x_zero, ...)` -> **`11.728273`** vs `s.func_check(x_zero, ...)` -> **`nan`**
- **Case 3 (Default decoding invariance & converged `x_opt` parity across `G01, G03, G12, G17, G18`):**
  - Repo-wide call audit confirms `func_check` appears at only **2 lines** in the entire repository (`core.py:1911` definition and `core.py:2300` inside `if self.check_results:`).
  - Runtime spy verification confirmed `called_when_check_results_False == False` (`0` calls) across all tested structures, and at converged `x_opt` with `check_results=True`, `|func(x_opt) - func_check(x_opt)| == 0.000e+00` on all 5 structures (`G01`: `315.321744844560`, `G03`: `8.271139509302`, `G12`: `2.974125162310`, `G17`: `162.771655587597`, `G18`: `2.546354319383`).

### 3.3 Verdict: **`SAFE_NOW`**
Synchronizing `func_check()` with `func()` (`denom_ii = np.sqrt(max(inner_p[i][i], 1e-10))`, `denom_jj = np.sqrt(max(inner_p[j][j], 1e-10))`, and `r_temp = max(r_temp, 1e-8)`) has **strictly `0.0` impact** on default decoding (`check_results=False`) and `0.0` drift on non-degenerate `check_results=True` runs, while eliminating genuine `NaN` / `ZeroDivisionError` failures in diagnostic mode.

---

## 4. `DEF-025` — `check_structural_validity` Periodic Self-Image Blind Spot

### 4.1 Verified Source Coordinates & Newly Discovered Sheared-Cell Blind Spot
- `SLICES.check_structural_validity`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L620-L636)

`check_structural_validity(str1)` currently loops over `0 <= i < j < len(str1)` of `str1.lattice.get_all_distances(str1.frac_coords, str1.frac_coords)`. This creates **three distinct failure modes**:
1. **1-atom primitive cells (`len(str1) == 1`):** The upper-triangular loop executes `0` iterations, leaving `min_value = 10000000` and unconditionally returning `True` even if $a = 0.3$ Å.
2. **Multi-atom cells with short basis vectors (`min(abc) <= 0.5 Å`):** Minimum-image distances between distinct sites (`i < j`) can exceed `0.5 Å` (e.g., $d_{12} = \sqrt{2^2 + 2^2} = 2.828$ Å in a $0.3 \times 4.0 \times 4.0$ Å cell) while every atom collides with its own periodic image `0.3 Å` away along $\mathbf{a}$.
3. **Newly discovered sheared-cell blind spot (defeats naive `min(str1.lattice.abc) > 0.5`!):** In a skewed triclinic/monoclinic cell with $a = 1.0$ Å, $b = 1.0$ Å, $c = 5.0$ Å, $\alpha = \beta = 90^\circ, \gamma = 17.0^\circ$, all three basis lengths satisfy `min(lattice.abc) = 1.0000 Å > 0.5 Å`, **yet the lattice diagonal translation $\mathbf{a} - \mathbf{b}$ has length $\|\mathbf{a} - \mathbf{b}\| = 2 \sin(8.5^\circ) = 0.2956\text{ Å} \le 0.5\text{ Å}$**! Thus a naive `min(str1.lattice.abc) > 0.5` guard **still returns a false `True`**, whereas `get_neighbor_list(r=0.5 + 1e-9)` (or Niggli reduction) detects the `0.2956 Å` periodic self-image collision.
4. **0-atom `Structure` edge case:** `Structure(Lattice.cubic(5.0), [], [])` currently crashes inside `get_all_distances` with `ValueError: shapes (1,0) and (3,3) not aligned`.

### 4.2 Empirical Evaluation (Synthetic Edge Suite + Golden Corpus + `18,093` MP-20 CIFs)

| Test Case | Geometry | `min(abc)` (Å) | Niggli `min(abc)` (Å) | v4.0.2 Baseline | Naive `min(abc) > 0.5` + Dist | Exact `get_neighbor_list(r=0.5+1e-9)` |
|---|---|---|---|---|---|---|
| `D1_1atom_short_a0.3` | Cubic `Na`, $a=0.3$ | `0.3000` | `0.3000` | `True` *(bug)* | `False` | **`False`** |
| `D2_1atom_boundary_a0.5` | Cubic `Na`, $a=0.5$ | `0.5000` | `0.5000` | `True` *(bug)* | `False` | **`False`** |
| `D3_1atom_valid_a0.5001` | Cubic `Na`, $a=0.5001$ | `0.5001` | `0.5001` | `True` | `True` | **`True`** |
| `D4_2atom_short_a0.3_d12_2.83` | Ortho `NaCl`, $0.3\times 4\times 4$, $d_{12}=2.83$ | `0.3000` | `0.3000` | `True` *(bug)* | `False` | **`False`** |
| `D5_1atom_sheared_diag0.30` | `Na`, $1\times 1\times 5$, $\gamma=17^\circ$ | `1.0000` | `0.2956` | `True` *(bug)* | `True` *(bug!)* | **`False`** |
| `D6_2atom_sheared_diag0.30` | `NaCl`, $1\times 1\times 5$, $\gamma=17^\circ$, $d_{12}=2.50$ | `1.0000` | `0.2956` | `True` *(bug)* | `True` *(bug!)* | **`False`** |
| `D7_2atom_distinct_d0.4` | Cubic `NaCl`, $a=4.0$, $d_{12}=0.4$ | `4.0000` | `4.0000` | `False` | `False` | **`False`** |
| `D8_2atom_distinct_d0.5` | Cubic `NaCl`, $a=4.0$, $d_{12}=0.5$ | `4.0000` | `4.0000` | `False` | `False` | **`False`** |

**Dataset Prevalence & Runtime Overhead:**
- **Golden Reference Corpus (`59` decoded structures across `std, opt, opt2, std2` of `G01`–`G19`, including 1-atom `G14` `Na`):** **`0 / 59` mismatches** (`34.2 ms` total).
- **MP-20 Real Crystal Scan (`18,093` CIFs across `data/mp20/test.csv` + `val.csv`, `34.83 s`):** Minimum observed lattice length is **`2.2598 Å`**; **`0 / 18,093`** have `min(abc) <= 0.5 Å` and **`0 / 18,093`** differ between baseline and `get_neighbor_list(r=0.5 + 1e-9)`.
- **Micro-benchmark (500 calls on 12-atom `G02` `Sr3Ru2O7`):** Baseline `43.9 µs/call` vs `get_neighbor_list(r=0.5 + 1e-9)` `91.5 µs/call` (`+47.6 µs/call`, i.e., `< 0.05 s` per 1,000 structures).

### 4.3 Recommended Exact Fix & Verdict: **`SAFE_NOW`**
```python
@staticmethod
def check_structural_validity(str1: Structure) -> bool:
    if len(str1) == 0:
        return False
    i, j, img, d = str1.get_neighbor_list(r=0.5 + 1e-9)
    non_self = (i != j) | np.any(img != 0, axis=1)
    return bool(not np.any(d[non_self] <= 0.5))
```
Preserves `100%` (`89/89`) Golden parity and `100%` (`18,093/18,093`) MP-20 parity while catching all 1-atom, short-axis, and sheared-lattice periodic self-image collisions (`<= 0.5 Å` strict inequality preserved).

---

## 5. `DEF-014` — Exact IEEE-754 Float `set`/`==` `lattice_type` Classifier

### 5.1 Verified Source Coordinates at `HEAD=fa4cfc8`
- `SLICES.to_structures`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L2220-L2233)
- Downstream consumers: `SLICES.initialize_x_bounds` ([core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1745-L1827)) and `SLICES.convert_params` ([core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1683-L1742))

### 5.2 Empirical Noise Distribution Across All `2,383` MP-20 Benchmark Crystals
Across all `2,366` active (`cocycle_rep is not None`) structures in `mp20_v4_benchmark_2383.csv` (`7,098` diagonal pairs $(g_{ii}, g_{jj})$ of `metric_tensor_std`), the relative difference $|g_{ii} - g_{jj}| / \max(g_{ii}, g_{jj})$ exhibits a **razor-sharp bimodal distribution with a 7-order-of-magnitude spectral gap**:

| Relative Diagonal Difference Band `\|g_ii - g_jj\| / max(g_ii, g_jj)` | Pair Count (`N = 7,098`) | Share | Physical / Numerical Origin |
|---|---:|---:|---|
| Exact `0.0` | `216` | `3.04%` | Small integer-symmetric nets with zero rounding residual |
| `(0.0, 1e-16]` | `0` | `0.00%` | Below float64 machine epsilon |
| `(1e-16, 1e-15]` | `1,189` | `16.75%` | **IEEE-754 rounding in `eon_projection` / `cholesky` / rescaling** |
| `(1e-15, 1e-14]` | `1,836` | `25.87%` | **IEEE-754 rounding in `eon_projection` / `cholesky` / rescaling** |
| `(1e-14, 1e-13]` | `168` | `2.37%` | **IEEE-754 rounding on larger multi-atom quotient graphs** |
| **`(1e-13, 1e-12]`** | **`0`** | **`0.00%`** | **Empty spectral gap (zero borderline pairs)** |
| **`(1e-12, 1e-09]`** | **`0`** | **`0.00%`** | **Empty spectral gap (100% tolerance-insensitive across `[1e-12, 1e-9]`)** |
| `(1e-09, 1e-06]` | `1` | `0.01%` | Near-degenerate pseudo-symmetric GFN-FF bond scaling |
| `(1e-06, 1e-03]` | `96` | `1.35%` | Genuine slight crystallographic / GFN-FF anisotropy |
| `(1e-03, 1e-01]` | `736` | `10.37%` | Moderate lattice anisotropy |
| `(1e-01, 10.0]` | `2,856` | `40.24%` | Strong lattice anisotropy |

**Per-Crystal-System Symmetry Loss Rate under Exact `set`/`==` (`n = 2,366` active MP-20 crystals):**

| Ground-Truth `crystal_system` | `n` | Baseline Exact `==` `lattice_type` Counts | Tolerant `isclose(rel_tol=1e-9)` Counts | Crystals Flipping (`1e-12` == `1e-9`) | Flip Rate |
|---|---:|---|---|---:|---:|
| **`cubic`** | `576` | `{3: 523, 22: 17, 21: 14, 1: 11, 23: 11}` | **`{1: 573, 21: 2, 3: 1}`** | **`563 / 576`** | **`97.7%`** *(98.1% missed `lt=1`!)* |
| **`hexagonal`** | `229` | `{3: 216, 23: 12, 21: 1}` | **`{23: 222, 21: 7}`** | **`216 / 229`** | **`94.3%`** |
| **`trigonal`** | `237` | `{3: 198, 23: 14, 21: 13, 22: 8, 1: 4}` | **`{1: 155, 23: 75, 3: 6, 21: 1}`** | **`224 / 237`** | **`94.5%`** |
| **`tetragonal`** | `378` | `{3: 329, 23: 43, 21: 5, 22: 1}` | **`{23: 328, 1: 37, 21: 9, 3: 4}`** | **`334 / 378`** | **`88.4%`** |
| `monoclinic` *(C-centered prim)* | `359` | `{3: 342, 23: 15, 21: 1, 22: 1}` | `{23: 185, 3: 141, 21: 15, 1: 13, 22: 5}` | `202 / 359` | `56.3%` *(primitive $\|a_p\|=\|b_p\|$)* |
| `orthorhombic` *(C/I/F prim)* | `476` | `{3: 467, 23: 7, 1: 1, 21: 1}` | `{3: 290, 23: 164, 21: 16, 1: 5, 22: 1}` | `178 / 476` | `37.4%` *(centered primitive cells)* |
| `triclinic` | `111` | `{3: 107, 23: 4}` | `{3: 91, 23: 11, 1: 5, 21: 4}` | `17 / 111` | `15.3%` *(topological net symmetry)* |
| **Total Active MP-20** | **`2,366`** | **`2,182` (`92.2%`) assigned `lt=3`** | **`533` (`22.5%`) assigned `lt=3`** | **`1,734 / 2,366`** | **`73.29%`** |

Even in the 19-structure Golden Corpus, **`15 / 18`** active (`cocycle_rep != None`) structures flip under `isclose(1e-9)`, including `G12` (`NbCoSn`, Cubic `F-43m`, whose fixture note assumed `lattice_type=1` yet actually ran at `lattice_type=3` because `r = (3.93e-16, 9.83e-16, 5.90e-16)`!) and `G13` (`CsYbBr3`, Cubic `Pm-3m`, `r = (9.81e-16, 2.80e-16, 7.00e-16)`).

### 5.3 Controlled End-to-End ZL\* + `nequip-s+l` A/B Experiment (`68` Crystals)
We ran a controlled A/B experiment comparing exact `set`/`==` vs transitive `math.isclose(rel_tol=1e-9, abs_tol=1e-12)` across all `19` Golden Corpus structures + `49` stratified multi-element MP-20 structures (`7` per crystal system; `49.43 s` wall clock across 8 workers):

| Subset | `lattice_type` Flips | Mean ZL\* `nit` (`base -> isclose`) | ZL\* `strict_opt` (`base -> isclose`) | Relaxed `strict_opt2` (`base -> isclose`) | Relaxed `loose_opt2` (`base -> isclose`) | Summed Worker CPU Time (`base -> isclose`) |
|---|---:|---|---|---|---|---|
| Golden Corpus (`19`) | `15 / 19` | `29.7 -> 30.0` | `14/19 -> 14/19` | `18/19 -> 18/19` | `18/19 -> 18/19` | `20.2 s -> 13.2 s` |
| Stratified MP-20 (`49`) | `33 / 49` | `46.2 -> 45.9` | `34/49 -> 34/49` | `44/49 -> 44/49` | `45/49 -> 45/49` | `100.7 s -> 93.6 s` |
| **Combined (`68`)** | **`48 / 68` (`70.6%`)** | **`41.7 -> 41.6`** | **`48/68 -> 48/68`** | **`62/68 -> 62/68`** | **`63/68 -> 63/68`** | **`121.0 s -> 106.8 s` (`-11.7%`)** |

- **Why `match_check3` stays invariant (`0` losses, `0` wins) while runtime improves by `-11.7%`:** When `metric_tensor_std` and `inner_p_target` are symmetric up to `1e-15`, the unconstrained `lattice_type=3` objective is also symmetric, so `fmin_l_bfgs_b` keeps `mt[0,0] ≈ mt[1,1]` up to `epsilon=1e-8` finite-difference noise: **`43 / 48`** flipped crystals agree to `< 1e-12 Å` on `opt_lat`, and only **`5 / 48`** shift `opt_lat` by `3.89e-8 .. 2.75e-5 Å` (e.g., `M_hexa_162` `Zn2O2`: `lt 3->23`, `nvars 12->11`, `nit 18->16`, `opt_lat_diff = 2.75e-5 Å`, `dE = 0.000000 eV/atom`). Across all `48` flipped crystals, **`0 / 48` have `|dE| > 1 meV/atom`** (`max |dE| = 0.274 meV/atom`, `median |dE| = 2.56e-7 eV/atom`), while dropping 1–2 redundant parameters from `approx_grad=True` finite-difference L-BFGS-B trims ~`11.7%` wall-clock time and **eliminates cross-platform / multi-thread BLAS branching sensitivity (`DEF-005`)**.

### 5.4 Verdict: **`HIGH_VALUE_AB`**
Fixing `DEF-014` via transitive `math.isclose(rel_tol=1e-9, abs_tol=1e-12)` restores the intended symmetry-constrained parameterization on `73.3%` of MP-20 crystals (`98%` of cubic, `94%` of hexagonal), speeds up decoding by `~11.7%`, and hardens SLICES against OpenMP/CPU architecture rounding differences (`DEF-005`) with zero reconstruction regressions. Because `~10%` of flipped crystals shift `opt_lat` by `1e-8..3e-5 Å` (exceeding frozen v4.0.2 `atol=1e-12` golden tolerances), it should be landed in a post-baseline `v4.1` branch (or gated behind an opt-in flag in `v4.0.x`) with refreshed golden fixtures.

---

## 6. `DEF-006` — `check_element` `Z < 87` vs GFN-FF & NequIP-OAM Element Coverage

### 6.1 Verified Source Coordinates at `HEAD=fa4cfc8`
- `SLICES.check_element`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L246-L260) (`return bool(atom_types.max() < 87)`)
- `parse_nbf_text` & `run_gfnff_helper`: [gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py#L105-L135), [L223-L249](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py#L223-L249)
- `NequIPCalculator.from_compiled_model`: [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py#L454-L462)
- `LJ_PARAMS_LIST` & `PERIODIC_DATA`: [config.py](file:///home/ordillo/tests/SLICES/src/slices/config.py#L49-L296) (`Z = 1..118`)

### 6.2 Empirical Discovery: Three-Tier Element Support Matrix & `libgfnff` `Z >= 104` Memory Safety Bug
Direct inspection of `model/config.yaml` inside both cached `NequIP-OAM-S:0.1` and `NequIP-OAM-L:0.1` Zenodo archives (`/home/ordillo/tests/.cache/nequip_raw/*.nequip.zip`) plus live execution across `Z = 1..118` revealed **two critical surprises**:

1. **NequIP-OAM-S and NequIP-OAM-L support exactly `89` elements — NOT a contiguous `Z <= Z_max` prefix!**
   Both models are trained on the Materials Project / OAM 89-element pseudopotential set:
   $$Z_{\text{NequIP-OAM}} = \{1..83\ (\text{H..Bi})\} \cup \{89..94\ (\text{Ac, Th, Pa, U, Np, Pu})\}$$
   - **`Z ∈ {84, 85, 86}` (`Po, At, Rn`)**: `SLICES.check_element()` returns **`True`** (false positive!), `libgfnff` succeeds, and **`NequIP-OAM-S/L` crashes with `KeyError: "Got an atomic number as input for ..."`**!
   - **`Z ∈ {87, 88}` (`Fr, Ra`)**: `check_element()` returns `False`, `libgfnff` succeeds, `NequIP-OAM-S/L` raises `KeyError`.
   - **`Z ∈ {89..94}` (`Ac, Th, Pa, U, Np, Pu`)**: `check_element()` returns **`False`** (false negative!), **yet BOTH `libgfnff` AND `NequIP-OAM-S/L` succeed cleanly!**
   - **`Z ∈ {95..103}` (`Am..Lr`)**: `check_element()` returns `False`, `libgfnff` succeeds cleanly (`r0_XO = 4.02..4.24 Bohr`), `NequIP-OAM-S/L` raises `KeyError` (usable with `relax_model=None` or custom relaxers).
2. **Newly Discovered `libgfnff` Out-of-Bounds Fortran Read on `Z >= 104` (`Rf..Og`):**
   Passing `Z = 104..118` (`Rf..Og`, all valid in `pymatgen.Element` and `config.py`) into `run_gfnff_helper()` does **not** raise an error in C/Fortran `libgfnff.so.0.1.1`; instead, it indexes past the 103-element Fortran parameter arrays and returns **non-deterministic uninitialized memory garbage**:
   - `Z = 103 (Lr)`: `r0_XO = 4.02140 Bohr (2.1280 Å), k = -0.16575` *(valid)*
   - `Z = 104 (Rf)`: `r0_XO = 3.31502..3.33328 Bohr, k = -0.00000, nangl = 0` *(corrupted)*
   - `Z = 105 (Db)`: `r0_XO = 67.08101 Bohr (35.4977 Å)` on run 1 vs `1.90346 Bohr` on run 2 *(non-deterministic out-of-bounds heap read!)*
   - `Z = 107 (Bh)`: `r0_XO = 6932.21447 Bohr (3,668.37 Å)!`

### 6.3 End-to-End Actinide Crystal Reconstruction on Real MP-20 Data
Scanning all `45,229` structures in `data/mp20/{train,val,test}.csv` shows **every single `Z >= 84` occurrence (`2,271` total) belongs to `Z ∈ {89..94}`**: `Ac` (`235`), `Th` (`574`), `Pa` (`204`), `U` (`931`), `Np` (`140`), `Pu` (`187`), with **`0`** occurrences of `Po..Ra` (`84..88`) or `Am..Og` (`>= 95`). Every tested MP-20 actinide crystal reconstructed with **`100%` strict and loose `match_check3` accuracy** under `nequip-s+l`:

| Atomic Number | MP-20 ID | Formula | `check_element` (v4.0.2) | `check_3D` | Decoded Structs | NequIP-OAM-L Energy (eV/atom) | `match_check3` Strict `(opt2, opt, std)` | `match_check3` Loose | Decode Time |
|---:|---|---|---|---|---:|---:|---|---|---:|
| `89` (`Ac`) | `mp-1183241` | `AcPm3` | `False` | `True` | `3` | `-4.5563` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `0.47 s` |
| `90` (`Th`) | `mp-1218989` (`G16`) | `SmThCN` | `False` | `True` | `3` | `-8.2748` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `0.24 s` |
| `91` (`Pa`) | `mp-977444` | `PaAgAu2` | `False` | `True` | `3` | `-5.0103` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `0.51 s` |
| `92` (`U`) | `mp-13018` | `UCo4Sn` | `False` | `True` | `3` | `-7.3914` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `0.90 s` |
| `93` (`Np`) | `mp-1186110` | `NpAlO3` | `False` | `True` | `3` | `-9.0994` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `0.91 s` |
| `94` (`Pu`) | `mp-7751` | `PuPt5` | `False` | `True` | `3` | `-7.9593` | **`('1', '1', '1')`** | **`('1', '1', '1')`** | `1.61 s` |

### 6.4 Verdict: **`VERSIONED_OPT_IN`** *(+ **`SAFE_NOW`** `1 <= Z <= 103` bounds guard in `gfnff_helper.py`)*
1. **Preserve default `check_element(structure)` (`Z <= 86`)** to maintain 100% Golden parity (`G16`, `S03`) and historical dataset-filter reproducibility, while adding an optional `mode: Literal["legacy86", "nequip_oam", "gfnff103"] = "legacy86"` parameter:
   - `"legacy86"` (default): `Z <= 86`
   - `"nequip_oam"`: exact 89-element set `Z in {1..83, 89..94}` (prevents `Po/At/Rn` `KeyError` crashes AND unlocks `Ac..Pu` actinides!)
   - `"gfnff103"`: `Z <= 103` (for unrelaxed ZL\* `relax_model=None` or transplutonium-capable relaxers).
2. **`SAFE_NOW` memory-safety guard:** Immediately enforce `if np.any((z_arr < 1) | (z_arr > 103)): raise GFNFFExecutionError(...)` in `gfnff_helper.parse_nbf_text()` (`gfnff_helper.py:134`) so `Z >= 104` never triggers out-of-bounds Fortran reads in `libgfnff.so`.

---

## 7. `DEF-001` — Heteronuclear LJ `i[0]`-Twice Indexing in `core.py`

### 7.1 Verified Source Coordinates & First-Principles Physics/Units Correction
- `SLICES.get_uncovered_pair_lj`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1550-L1575) (`L1569-L1572`)
- `SLICES.get_covered_pair_lj`: [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1577-L1595) (`L1589-L1592`)
- Also invoked in: [decoding_strategies.py](file:///home/ordillo/tests/SLICES/src/slices/decoding_strategies.py#L557-L558)
- Parameter table: `LJ_PARAMS_LIST` in [config.py](file:///home/ordillo/tests/SLICES/src/slices/config.py#L49-L168) (`Z = 1..118`)

> [!IMPORTANT]
> **Critical Correction to Prior Register Assumptions (`LJ_PARAMS_LIST` Units):**  
> Prior notes in `DEFERRED_CORE_REGISTER.md` assumed `lj_param[Z] = [col_0, col_1]` stored `[r0, eps]` (radius and well depth) and proposed testing geometric Berthelot mixing `sqrt(col_1_i * col_1_j)` on column 1. **First-principles inspection of `config.py` and `core.py:1888-1908` proves BOTH columns are lengths in Ångströms:**
> $$\text{col\_1}(Z) = \sigma(Z) = \frac{2\,r_{\text{cov}}(Z)}{2^{1/6}}\ [\text{\AA}], \qquad \text{col\_0}(Z) = r_{\text{cut}}(Z) = 4\,\sigma(Z)\ [\text{\AA}]$$
> verified across all `118` elements (`max |col_0 - 4 * col_1| = 6.0e-5 Å`; `95/96` of `Z=1..96` match `ase.data.covalent_radii` Cordero 2008 to `< 1e-4 Å`, with `B = 0.85 Å` and `Z = 97..118` matching Pyykkö & Atsumi 2009 single-bond covalent radii).
>
> In `SLICES.func()` ([core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py#L1888-L1908)):
> $$V_{\text{cov}} = 4\,w_{\text{cov}} \left(\frac{\sigma_{ij}}{r_{ij}}\right)^{12}, \qquad V_{\text{uncov}} = 4\,w_{\text{uncov}} \left(\frac{\sigma_{ij}}{r_{ij}}\right)^{12} \mathbf{1}[r_{ij} < r_{\text{cut}, ij}]$$
> 1. Well depth $\varepsilon$ is the uniform scalar `vbond_param_ave = 0.01` (`vbond_param_ave_covered = 0.00` across `core.py` and all `14/14` `.ini` files in `HTS/` and `benchmark/`, making `get_covered_pair_lj()` a **100% mathematical no-op** under default parameters!).
> 2. Because $\varepsilon_i = \varepsilon_j = w_{\text{uncov}}$, **Arm (b) arithmetic mean on both columns `[(r_cut_i + r_cut_j)/2, (sigma_i + sigma_j)/2]` IS the exact physical Lorentz–Berthelot mixing law!**
> 3. Conversely, **Arm (c) `[(r_cut_i + r_cut_j)/2, sqrt(sigma_i * sigma_j)]`** mistakenly takes the geometric mean of collision diameters $\sqrt{\sigma_i \sigma_j} \le (\sigma_i + \sigma_j)/2$, artificially shrinking $\sigma_{ij}$ for heteronuclear pairs (e.g., for `Y`–`H`, $\sqrt{3.385 \times 0.552} = 1.367$ Å vs arithmetic $1.969$ Å -> $(1.367/1.969)^{12} = 0.0125$, weakening repulsion **80×**).
> 4. **Atom-order permutation symmetry violation in Baseline (a):** Because `get_uncovered_pair` enumerates upper-triangular pairs `i[0] < i[1]`, `i[0]`-twice assigns the **first-listed atom's** homonuclear $\sigma_{i_0}^{12}$ to pair `(i[0], i[1])`. On `G18` (`YHO2`) with `fix_duplicate_edge=True`, reversing atom order in the SLICES string changes $\sum \sigma_{ij}^{12}$ by **5.00×** (`11,332,410.03` vs `2,266,557.56`) under Baseline (a), whereas Arm (b) is **100% permutation-invariant** (`2,280,090.76 == 2,280,090.76`). *(Side finding: when `fix_duplicate_edge=False`, `get_uncovered_pair` at `core.py:1533-1547` checks `i not in unique_covered_pair_int` without symmetrizing directed edges `u > v`, misclassifying reversed bonds as uncovered; `from_cif()` is unaffected (`0/50` MP-20 CIFs had `u > v` unresolved) because `StructureGraph` emits both or canonical directions.)*

### 7.2 Controlled 3-Arm A/B Experiment (`19` Golden + `49` Stratified Multi-Element MP-20 = `68` Crystals)
Executed in-memory via `SLICES` subclassing across all `19` Golden Corpus structures (`19/19` matched to exact ground-truth `ori` CIFs, plus reporting the `16` native CIF-backed Golden entries separately) and `49` deterministically stratified multi-element crystals (`7` per crystal system from `mp20_v4_benchmark_2383.csv`, `49/49` multi-species, `38/49` having $\ge 1$ heteronuclear uncovered pair; `68` total crystals, `52/68` with heteronuclear uncovered pairs; `8` worker processes, `98.8 s` wall clock):

#### A. ZL\*-Only Mode (`relax_model=None`)

| Dataset (`n`) | Arm | Mean `f(x0)` | Mean `f(x*)` (Median) | Mean L-BFGS-B `nit` | Overlap `cpr_opt < 0.5` (`min cpr`) | `opt` Changed (`> 1e-12`) | `max_opt_lat_diff` (Å) | `max_opt_frac_diff` | `match_opt` Strict / Loose |
|---|---|---:|---|---:|---|---|---:|---:|---|
| **Golden 19** (`14` het-uncov) | `(a) baseline` | `94,645.97` | `120.2388` (`94.4062`) | `29.7` | `2 / 19` (`0.2715`) | — | — | — | `14/19` / `17/19` |
| **Golden 19** | `(b) arith_both` | `94,642.49` | `120.1543` (`94.2958`) | `36.4` | `2 / 19` (`0.2744`) | `14 / 19` | `3.30e-05` | `2.58e-02` | `14/19` / `17/19` |
| **Golden 19** | `(c) geom_col1` | `94,642.40` | `120.1521` (`94.2925`) | `39.6` | `2 / 19` (`0.2746`) | `14 / 19` | `3.39e-05` | `1.11e-01` | `14/19` / `17/19` |
| **MP-20 Strat 49** (`38` het-uncov) | `(a) baseline` | `4,229,393.42` | `101.6064` (`66.7612`) | `46.2` | `0 / 49` (`0.5990`) | — | — | — | `34/49` / `40/49` |
| **MP-20 Strat 49** | `(b) arith_both` | **`368,285.27`** | `101.4118` (`66.7474`) | **`43.8`** | `0 / 49` (`0.5974`) | `38 / 49` | `4.20e-04` | `1.10e-01` | `34/49` / `40/49` |
| **MP-20 Strat 49** | `(c) geom_col1` | `269,226.67` | `101.3926` (`66.7472`) | `44.3` | `0 / 49` (`0.5839`) | `38 / 49` | `4.48e-04` | `1.10e-01` | `34/49` / `40/49` |
| **Combined 68** (`52` het-uncov) | `(a) baseline` | `3,118,565.75` | `106.6121` (`76.5404`) | `41.7` | `2 / 68` (`0.2715`) | — | — | — | **`48/68` / `57/68`** |
| **Combined 68** | `(b) arith_both` | **`294,769.30`** | **`106.4471`** (`76.5387`) | `41.9` | `2 / 68` (`0.2744`) | **`52 / 68`** | `4.20e-04` | `1.10e-01` | **`48/68` / `57/68`** |
| **Combined 68** | `(c) geom_col1` | `222,323.43` | `106.4325` (`76.5386`) | `43.0` | `2 / 68` (`0.2746`) | **`52 / 68`** | `4.48e-04` | `1.11e-01` | **`48/68` / `57/68`** |

#### B. Full CPU `nequip-s+l` Mode (`NequIP-OAM-S` BFGS relaxation + `NequIP-OAM-L` energy)

| Dataset (`n`) | Arm | `match_check3` Strict `opt2` | `match_check3` Loose `opt2` | Mean `E` (eV/atom) | Median `\|dE\|` vs Base (eV/atom) | Max `\|dE\|` (eV/atom) | Crystals with `\|dE\| > 1 meV/at` | Summed Worker Time |
|---|---|---|---|---:|---:|---:|---:|---:|
| **Golden 19** *(Golden 16 native)* | `(a) baseline` | **`18/19`** *(`16/16`)* | **`18/19`** *(`16/16`)* | `-5.42550` | — | — | — | `20.0 s` |
| **Golden 19** *(Golden 16 native)* | `(b) arith_both` | **`18/19`** *(`16/16`)* | **`18/19`** *(`16/16`)* | `-5.42535` | `2.79e-07` | `0.00335` (`G18`) | `1 / 19` | `13.7 s` |
| **Golden 19** *(Golden 16 native)* | `(c) geom_col1` | **`18/19`** *(`16/16`)* | **`18/19`** *(`16/16`)* | `-5.42524` | `4.33e-07` | `0.00545` (`G18`) | `1 / 19` | `13.0 s` |
| **MP-20 Strat 49** | `(a) baseline` | **`44/49` (`89.8%`)** | **`45/49` (`91.8%`)** | `-6.30926` | — | — | — | `101.1 s` |
| **MP-20 Strat 49** | `(b) arith_both` | **`44/49` (`89.8%`)** | **`45/49` (`91.8%`)** | `-6.30927` | `5.68e-07` | `0.00181` | `2 / 49` | `97.7 s` |
| **MP-20 Strat 49** | `(c) geom_col1` | **`44/49` (`89.8%`)** | **`45/49` (`91.8%`)** | `-6.30920` | `5.64e-07` | `0.00672` | `2 / 49` | `99.4 s` |
| **Combined 68** | `(a) baseline` | **`62/68` (`91.2%`)** | **`63/68` (`92.6%`)** | `-6.06233` | — | — | — | `121.1 s` |
| **Combined 68** | `(b) arith_both` | **`62/68` (`91.2%`)** | **`63/68` (`92.6%`)** | `-6.06229` | **`5.06e-07`** | **`0.00335`** | **`3 / 68`** | **`111.4 s`** |
| **Combined 68** | `(c) geom_col1` | **`62/68` (`91.2%`)** | **`63/68` (`92.6%`)** | `-6.06221` | `5.47e-07` | `0.00672` | `3 / 68` | `112.4 s` |

### 7.3 Mechanistic Interpretation & Verdict: **`VERSIONED_OPT_IN`**
1. **Helps, hurts, or neutral?** Empirically **strictly neutral on crystal recovery (`0` match wins, `0` match losses across all `68` crystals on both `opt` and `opt2`, and `0` change in `closest_pair_ratio < 0.5` overlap count `2/68`)**, while **helping mathematical consistency**: Arm `(b) arith_both` restores exact atom-index permutation invariance, slashes initial barycentric repulsive spikes `f(x0)` by **`11.5×`** on multi-element MP-20 crystals (`4.23e6 -> 3.68e5`), reduces MP-20 mean L-BFGS-B iterations (`46.2 -> 43.8`), and produces half the worst-case energy drift of `(c) geom_col1` (`3.35 meV/atom` vs `6.72 meV/atom`).
2. **Why recovery is insensitive despite `100%` (`52/52`) ZL\* trajectory perturbation:** `get_covered_pair_lj()` is multiplied by `vbond_param_ave_covered = 0.0`, and `get_uncovered_pair_lj()` carries small prefactor `4 * 0.01 = 0.04` acting purely as a short-range steric wall; once non-bonded atoms separate beyond $\sim 1.2\sigma$, GFN-FF bond/angle quadratic terms govern the ZL\* minimum, and `NequIP-OAM-S` BFGS relaxation funnels `0.01..0.11` fractional shifts into the identical physical minimum (`median |dE| = 5.06e-7 eV/atom`).
3. **Recommendation:** Keep `lj_mixing="legacy"` as the frozen v4.0.2 default in `to_structures()` (`14/19` Golden fixtures shift if changed), expose `lj_mixing: Literal["legacy", "lorentz"] = "legacy"` using **Arm (b) arithmetic mean on both `[4*sigma, sigma]` columns** (never Arm (c)), and adopt `"lorentz"` inside opt-in `decoding_strategies.py` / future `v4.1`.

---

## 8. Summary of Newly Discovered Edge Cases Across Audit

1. **`libgfnff.so` out-of-bounds Fortran read on `Z >= 104` (`Rf..Og`) (`DEF-006`):** `gfnff_helper.parse_nbf_text` allows `Z = 104..118`, causing unguarded out-of-bounds reads in `libgfnff` (`r0 = 3,668.4 Å` on `Bh`, non-deterministic `35.50 Å` vs `1.01 Å` on `Db`). Guard `1 <= Z <= 103` immediately (`SAFE_NOW`).
2. **`NequIP-OAM-S/L` `KeyError` on `Z = 84..86` (`Po, At, Rn`) (`DEF-006`):** Accepted by `check_element()` (`Z < 87`) but absent from NequIP-OAM's 89-element vocabulary `{1..83, 89..94}`.
3. **`LJ_PARAMS_LIST` column-1 physical identity (`DEF-001`):** Column 1 is $\sigma = 2^{-1/6}(2 r_{\text{cov}})$ in Å (`col_0 == 4 * col_1`), not $\varepsilon$; geometric mixing on column 1 violates Lorentz additivity of radii.
4. **Sheared-lattice periodic collision blind spot (`DEF-025`):** `min(str1.lattice.abc) > 0.5` misses acute/obtuse sheared cells where $\|\mathbf{a} \pm \mathbf{b}\| \le 0.5$ Å (`D5`/`D6`); `str1.get_neighbor_list(r=0.5 + 1e-9)` resolves all periodic images exactly.
5. **Directed-edge `u > v` blind spot in `get_uncovered_pair` (`core.py:1533-1547`):** When `from_SLICES(..., fix_duplicate_edge=False)` or direct `__init__` supplies an edge `[u, v]` with `u > v`, `get_uncovered_pair` fails to match `[v, u]` against `unique_covered_pair_int` and applies non-bonded LJ repulsion across a bonded edge.
6. **Rank-deficient rectangular `IndexError` in dead `Net.linear_independent_vectors` (`tobascco_net.py:446`):** Overflows `index = np.zeros(r)` when `mat.shape[1] > r` has $> r$ non-collinear adjacent column transitions.
