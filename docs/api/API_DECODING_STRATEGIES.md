# API Reference: Opt-In Decoding Recovery Strategies (`slices.decoding_strategies`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/decoding_strategies.py`](../../src/slices/decoding_strategies.py), [`src/slices/core.py`](../../src/slices/core.py) (`SLICES.robust_SLICES2structure`)

---

## 1. Freeze Isolation Policy

`slices.decoding_strategies` is **strictly opt-in**. Under the Stage 3 Math/Algorithm Freeze (`DEF-002`, `DEF-003`, `DEF-015`), default `SLICES.to_structures()`, `SLICES.SLICES2structure()`, and `Net.get_lattice_basis()` **never import or invoke** any function from this module.

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

1. **Stage 1 (Exact v4.0.2 Fast Path):** Validates `strategy in (1, 3, 4)` (raising `SLICESDecodingError` on encode-only `strategy=2` or unknown strategies) and executes standard `slices_inst.SLICES2structure(slices_str, strategy=strategy, fix_duplicate_edge=fix_duplicate_edge)`. If relaxation succeeds (`len(structures) == 3`) or `slices_inst.relaxer is None`, returns immediately with bit-identical v4.0.2 output.
2. **Stage 2 (Opt-In Recovery):** Reconstructs `(std, opt)` using `CycleBasisOptimizer.find_lattice_basis`, `BondParameterFallback` (if GFN-FF target generation fails), `AdaptiveConvergence`, and seeded `MultiStartOptimizer` (`n_starts`, `seed`), then attempts `ProgressiveRelaxer.relax_with_fallbacks`.
3. **Stage 3 (Unrelaxed Fallback):** If force-field relaxation still fails, returns `(opt_structure, 0.0)` rather than crashing; raises `SLICESDecodingError` only if parsing or graph embedding itself is unrecoverable.

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

Covalent-radius bond-target fallback when GFN-FF bond parameters are unavailable:

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
