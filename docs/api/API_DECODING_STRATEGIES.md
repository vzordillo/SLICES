# API Reference: Opt-In Decoding Recovery Strategies (`slices.decoding_strategies`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/decoding_strategies.py`](../../src/slices/decoding_strategies.py), [`src/slices/core.py`](../../src/slices/core.py) (`SLICES.robust_SLICES2structure`)

---

## 1. Freeze Isolation Policy

`slices.decoding_strategies` is **strictly opt-in**. Default `SLICES.to_structures()`, `SLICES.SLICES2structure()`, and `Net.get_lattice_basis()` remain frozen (`DEF-002`) and **never import or invoke** any function from this module. Wave 3 (`DEF-001`, `DEF-015`, `DEF-031`) upgraded the opt-in Stage 1 -> Stage 2 handoff and Stage 2 Lorentz-Berthelot pair mixing strictly within this module.

To use multi-stage recovery decoding, callers must explicitly invoke either:
- `slices_inst.robust_SLICES2structure(slices_str, ...)` on a `SLICES` instance,
- `slices.decoding_strategies.robust_decode(slices_inst, ...)`, or
- `slices decode --robust ...` via the CLI.

All randomized operations in this module use isolated `numpy.random.default_rng(seed)` generators and never mutate NumPy's global `np.random` state.

---

## 2. Public Exports (`slices.decoding_strategies.__all__`)

`AdaptiveConvergence`, `BondParameterFallback`, `CycleBasisOptimizer`, `MultiStartOptimizer`, `ProgressiveRelaxer`, `calculate_topology_timeout`, `calculate_xtb_timeout`, `is_approximately_integral`, `robust_decode`.

---

## 3. Primary Entry Points

### `robust_decode`

```python
def robust_decode(
    slices_inst: SLICES,
    slices_str: str,
    strategy: int = 4,
    fix_duplicate_edge: bool = True,
    n_starts: int = 3,
    seed: int = 0,
) -> tuple[Structure, float]
```

Decodes `slices_str` using a three-stage fallback cascade:

1. **Stage 1 (Exact v4.0.2 Fast Path & Incomplete-GFN-FF Detection):** Validates `strategy in (1, 3, 4)` (raising `SLICESDecodingError` on encode-only `strategy=2` or unknown strategies), parses via `slices_inst.from_SLICES(...)`, and executes untouched `slices_inst.to_structures()`. Checks `gfnff_incomplete = bool(getattr(slices_inst, "_last_gfnff_incomplete", False))` (`DEF-015`, `DEF-031`):
   - When `(slices_inst.relaxer is None or len(structures) == 3)` **and** `not gfnff_incomplete`, returns `(structures[-1], float(energy))` immediately with `0%` overhead and bit-for-bit v4.0.2 output.
   - When `gfnff_incomplete` is `True` (indicating `"Cannot find bond!!!"`, a non-positive diagonal in `inner_p_target`, or a GFN-FF target error during Stage 1), saves `(structures[-1], float(energy))` as `stage1_result` and automatically advances into Stage 2/3 recovery rather than stopping on Stage 1's incomplete-GFN-FF geometry.
2. **Stage 2 (Opt-In Recovery with Covalent-Radius Fallback & Lorentz-Berthelot Multi-Start ZL\*):** Runs `_reconstruct_zl_multistart(slices_inst, n_starts=n_starts, seed=seed)`:
   - Retries lattice-basis discovery via `CycleBasisOptimizer.find_lattice_basis` when needed.
   - Switches to `BondParameterFallback.build_inner_p_target(...)` whenever `get_inner_p_target()` returns `None`, `gfnff_incomplete` is `True` (before or after `get_inner_p_target`), or `np.any(np.diag(target_res[0]) <= 0.0)`.
   - Evaluates uncovered and covered pair Lennard-Jones `[4*sigma, sigma]` parameters using **exact Lorentz-Berthelot arithmetic mixing** (`_evaluate_lorentz_lj_pairs` / `_compute_lorentz_pair_lj`, temporarily setting `slices_inst.lj_mixing = "lorentz"` inside a `try ... finally` block so the caller's original `lj_mixing` setting is always restored, even on exceptions; `DEF-001`).
   - Runs `AdaptiveConvergence` and seeded `MultiStartOptimizer` (`n_starts`, `seed`).
   - If Stage 2 raises an exception and `stage1_result` is available, cleanly returns `stage1_result` so Stage 2 never regresses a valid Stage 1 structure.
3. **Stage 3 (Progressive Relaxation & Graceful Fallback):** When `slices_inst.relaxer is not None`, attempts `ProgressiveRelaxer.relax_with_fallbacks` across `(opt_struct, std_struct)`. If relaxation fails across all candidates, returns `stage1_result` when available, otherwise returns `(opt_struct, 0.0)` rather than crashing; raises `SLICESDecodingError` only if parsing or all reconstruction stages fail without any fallback structure.

### `SLICES.robust_SLICES2structure`

```python
def robust_SLICES2structure(
    self,
    SLICES: str,
    strategy: int = 4,
    fix_duplicate_edge: bool = True,
    n_starts: int = 3,
    seed: int = 0,
) -> tuple[Structure, float]
```

Thin lazy-importing wrapper on `slices.core.SLICES` that forwards all arguments to `slices.decoding_strategies.robust_decode`.

---

## 4. Helper Functions & Classes

### `is_approximately_integral`

```python
def is_approximately_integral(vect: np.ndarray, tolerance: float = 1e-6) -> bool
```

Returns `True` iff `vect` is non-empty, not all-zero (within `tolerance`), and **every individual entry** satisfies `frac < tolerance or frac > 1.0 - tolerance` where `frac = np.mod(np.abs(vect), 1.0)`. Correctly handles vectors mixing positive and negative near-integer residuals (e.g., `[1.0 + 1e-8, 2.0 - 1e-8]`).

### `CycleBasisOptimizer`

Opt-in cycle-ordering and lattice-basis retry utilities (never mutates `tobascco_net.Net` defaults):

- `is_approximately_integral(vect: np.ndarray, tolerance: float = 1e-6) -> bool` (`@staticmethod`): Delegates to module-level `is_approximately_integral`.
- `select_optimal_cycle_basis(cycle_rep: np.ndarray, max_attempts: int = 50, seed: int | None = 0) -> np.ndarray` (`@staticmethod`): Samples seeded row permutations via `np.random.default_rng(seed)` and scores leading spanning subsets by SVD conditioning (`s_min / s_max`) rather than permutation-invariant matrix rank.
- `find_lattice_basis(cls, net: Net, max_attempts: int = 20, tolerance: float = 1e-6, seed: int | None = 0) -> bool` (`@classmethod`): Attempts to populate `net.lattice_basis` via SymPy nullspace search across seeded cycle-row permutations using `is_approximately_integral(..., tolerance=tolerance)`.

### `BondParameterFallback`

Covalent-radius bond-target fallback when GFN-FF bond parameters are unavailable or incomplete (`_last_gfnff_incomplete=True` or `diag(inner_p_target) <= 0.0`):

- `estimate_bond_length(cls, atom1_symbol: str, atom2_symbol: str) -> float` (`@classmethod`): Estimates equilibrium bond length in **Bohr** from `pymatgen` covalent radii (`(r1 + r2) / 0.529177`).
- `estimate_bond_energy(cls, atom1_symbol: str, atom2_symbol: str, bond_length_bohr: float) -> float` (`@classmethod`): Returns positive empirical bond-stretching weight inversely scaled by bond length.
- `build_inner_p_target(cls, atom_types: np.ndarray, edge_indices: np.ndarray, bond_scaling: float = 1.05) -> tuple[np.ndarray, list[list[int]], list[float]]` (`@classmethod`): Builds a diagonal `(E, E)` inner-product target matrix using modulo-safe 0-based `atom_types` lookup.

### `MultiStartOptimizer`

```python
class MultiStartOptimizer:
    @staticmethod
    def optimize(
        func: Callable[..., float],
        x0: np.ndarray,
        bounds: list[tuple[float, float]],
        n_starts: int = 3,
        seed: int | None = 0,
        perturbation_scale: float = 0.1,
        **kwargs: Any,
    ) -> tuple[np.ndarray, float, dict[str, Any]]
```

Runs `scipy.optimize.fmin_l_bfgs_b` from `x0` and `n_starts - 1` seeded clipped Gaussian perturbations (`np.random.default_rng(seed)`), automatically stripping `scipy >= 1.15`-deprecated `iprint`/`disp` kwargs and defaulting `approx_grad=True` when `fprime` is omitted. Returns `(best_x, best_f, best_info)`.

### `AdaptiveConvergence`

- `get_convergence_params(num_atoms: int) -> dict[str, float]` (`@staticmethod`): Returns `{"factr": ..., "pgtol": ...}` scaled by cell size (`<= 10` atoms: `1e7` / `1e-5`; `11..20`: `1e8` / `5e-5`; `> 20`: `1e9` / `1e-4`).

### `ProgressiveRelaxer`

- `get_relaxation_strategies(base_fmax: float = 0.2, base_steps: int = 100) -> list[dict[str, Any]]` (`@staticmethod`): Returns ordered relaxation tiers starting from the caller's `(base_fmax, base_steps)` before relaxing tolerances.
- `calculate_timeout(num_atoms: int) -> int` (`@staticmethod`): Returns atom-count-scaled wall-clock timeout in seconds, capped at `3000`.
- `relax_with_fallbacks(cls, slices_inst: SLICES, structure: Structure) -> tuple[Structure, float] | None` (`@classmethod`): Iterates progressive tiers and unconditionally restores `slices_inst.fmax` and `slices_inst.steps` in a `finally:` block.

### `calculate_topology_timeout` (alias: `calculate_xtb_timeout`)

```python
def calculate_topology_timeout(num_atoms: int, num_bonds: int) -> int
```

Computes an adaptive external topology-helper timeout in seconds (`min(120, ...)`). `calculate_xtb_timeout` is preserved as an alias.

### Stage 2 Reconstruction & Lorentz-Berthelot Internals

`_reconstruct_zl_multistart(slices_inst, n_starts=3, seed=0, ...)` orchestrates Stage 2 reconstruction and uses two internal helpers for exact Lorentz-Berthelot pair mixing (`DEF-001`):

- `_compute_lorentz_pair_lj(atom_types, pairs) -> list[list[float]]`: Computes exact arithmetic-mean `[(p0[0] + p1[0]) / 2.0, (p0[1] + p1[1]) / 2.0]` on `LJ_PARAMS_LIST` `[4*sigma, sigma]` length columns in Angstrom.
- `_evaluate_lorentz_lj_pairs(slices_inst, uncovered_pair) -> tuple[list[list[float]], list[list[float]]]`: When `hasattr(slices_inst, "lj_mixing")`, temporarily sets `slices_inst.lj_mixing = "lorentz"` inside a `try ... finally` block around `get_uncovered_pair_lj` / `get_covered_pair_lj` and unconditionally restores the original `slices_inst.lj_mixing`; otherwise falls back directly to `_compute_lorentz_pair_lj`.

### Example

```python
from slices import SLICES

decoder = SLICES(relax_model="auto")
structure, energy_per_atom = decoder.robust_SLICES2structure(
    slices_str,
    strategy=4,
    n_starts=3,
    seed=0,
)
```
