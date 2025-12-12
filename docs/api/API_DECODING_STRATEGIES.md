# Decoding Strategies API Documentation

Complete reference for the `slices.decoding_strategies` module, which provides decoding strategies.

## Table of Contents

1. [CycleBasisOptimizer](#cyclebasisoptimizer)
2. [BondParameterFallback](#bondparameterfallback)
3. [MultiStartOptimizer](#multistartoptimizer)
4. [ProgressiveRelaxer](#progressiverelaxer)
5. [AdaptiveConvergence](#adaptiveconvergence)
6. [Utility Functions](#utility-functions)

---

## CycleBasisOptimizer

Cycle basis selection for lattice basis computation.

### `select_optimal_cycle_basis(cycle_rep, max_attempts=100)`

Selects cycle basis that maximizes linear independence rank.

**Parameters:**
- `cycle_rep` (np.array): Cycle representation matrix (n_cycles x n_edges)
- `max_attempts` (int, optional): Maximum number of random shuffles to try. Defaults to 100.

**Returns:**
- `np.array`: Array of indices representing optimal cycle ordering

**Example:**
```python
from slices.decoding_strategies import CycleBasisOptimizer
import numpy as np

cycle_rep = np.array([[1, 0, 1], [0, 1, 1], [1, 1, 0]])
optimal_inds = CycleBasisOptimizer.select_optimal_cycle_basis(cycle_rep)
print(f"Optimal ordering: {optimal_inds}")
```

**Algorithm:**
- Tries multiple random orderings of cycles
- Selects ordering with highest linear independence rank
- Helps maximize probability of finding valid lattice vectors

---

### `is_approximately_integral(vect, tolerance=1e-6)`

Checks if vector is approximately integral with given tolerance.

**Parameters:**
- `vect` (np.array): Vector to check
- `tolerance` (float, optional): Maximum deviation from integer values. Defaults to 1e-6.

**Returns:**
- `bool`: True if vector is approximately integral

**Example:**
```python
from slices.decoding_strategies import CycleBasisOptimizer
import numpy as np

# Check if vector is approximately integral
vect = np.array([1.0, 2.0, 3.0000001])
is_integral = CycleBasisOptimizer.is_approximately_integral(vect, tolerance=1e-5)
print(is_integral)  # True
```

**Purpose:** Handles numerical precision issues in floating-point computations while maintaining mathematical correctness.

---

## BondParameterFallback

Fallback bond parameter estimation when XTB calculation fails.

### `estimate_bond_length(atom1_symbol, atom2_symbol)`

Estimates bond length using covalent radii (Pauling, 1960).

**Parameters:**
- `atom1_symbol` (str): Symbol of first atom (e.g., 'Si')
- `atom2_symbol` (str): Symbol of second atom (e.g., 'O')

**Returns:**
- `float`: Estimated bond length in Bohr (atomic units)

**Example:**
```python
from slices.decoding_strategies import BondParameterFallback

# Estimate Si-O bond length
bond_length_bohr = BondParameterFallback.estimate_bond_length('Si', 'O')
bond_length_angstrom = bond_length_bohr * 0.529177
print(f"Estimated Si-O bond length: {bond_length_angstrom:.3f} Å")
```

**Method:**
- Uses sum of covalent radii from Pauling (1960)
- Converts to Bohr units (1 Bohr = 0.529177 Å)

---

### `estimate_bond_energy(atom1_symbol, atom2_symbol, bond_length_bohr)`

Estimates bond energy parameter using empirical relationship.

**Parameters:**
- `atom1_symbol` (str): Symbol of first atom
- `atom2_symbol` (str): Symbol of second atom
- `bond_length_bohr` (float): Bond length in Bohr

**Returns:**
- `float`: Estimated bond energy parameter

**Note:** This is a simplified model; XTB provides more accurate values.

---

## MultiStartOptimizer

Multi-start optimization for ZL* algorithm to improve convergence.

### `optimize(func, x0, bounds, n_starts=5, **kwargs)`

Runs optimization from multiple random starting points.

**Parameters:**
- `func`: Objective function to minimize
- `x0` (np.array): Initial guess
- `bounds` (list): List of (min, max) tuples for each variable
- `n_starts` (int, optional): Number of random starting points. Defaults to 5.
- `**kwargs`: Additional arguments for `fmin_l_bfgs_b`

**Returns:**
- `tuple`: (best_x, best_value, best_info)
  - `best_x` (np.array): Best solution found
  - `best_value` (float): Best objective function value
  - `best_info` (dict): Optimization information

**Example:**
```python
from slices.decoding_strategies import MultiStartOptimizer
import numpy as np
from scipy.optimize import fmin_l_bfgs_b

def objective(x):
    return np.sum(x**2)

x0 = np.array([1.0, 2.0, 3.0])
bounds = [(-10, 10), (-10, 10), (-10, 10)]

best_x, best_value, info = MultiStartOptimizer.optimize(
    objective, x0, bounds, n_starts=5
)
print(f"Best value: {best_value}")
```

**Algorithm:**
- Runs optimization from multiple random starting points
- Selects result with lowest objective function value
- Helps escape local minima

---

## ProgressiveRelaxer

Progressive MLIP relaxation with fallback strategies.

### `get_relaxation_strategies()`

Returns list of relaxation strategies ordered from tight to loose convergence.

**Returns:**
- `list`: List of strategy dictionaries with keys:
  - `'name'` (str): Strategy name
  - `'fmax'` (float): Force convergence criterion
  - `'steps'` (int): Maximum steps

**Example:**
```python
from slices.decoding_strategies import ProgressiveRelaxer

strategies = ProgressiveRelaxer.get_relaxation_strategies()
for strategy in strategies:
    print(f"{strategy['name']}: fmax={strategy['fmax']}, steps={strategy['steps']}")
```

**Strategies:**
1. Tight: fmax=0.1, steps=200
2. Normal: fmax=0.2, steps=100
3. Loose: fmax=0.3, steps=50

---

## AdaptiveConvergence

Adaptive convergence criteria based on structure size.

### `get_convergence_params(num_atoms)`

Gets convergence parameters adjusted for structure size.

**Parameters:**
- `num_atoms` (int): Number of atoms in structure

**Returns:**
- `dict`: Dictionary with convergence parameters:
  - `'factr'` (float): Factr parameter for L-BFGS-B
  - `'pgtol'` (float): Pgtol parameter for L-BFGS-B

**Example:**
```python
from slices.decoding_strategies import AdaptiveConvergence

# Small structure
params_small = AdaptiveConvergence.get_convergence_params(10)
print(f"Small structure params: {params_small}")

# Large structure
params_large = AdaptiveConvergence.get_convergence_params(100)
print(f"Large structure params: {params_large}")
```

**Adaptation:**
- Smaller structures: Tighter convergence (lower factr, lower pgtol)
- Larger structures: Looser convergence (higher factr, higher pgtol)
- Prevents premature termination for large structures

---

## Utility Functions

### `calculate_xtb_timeout(num_atoms, num_bonds)`

Calculates adaptive timeout for XTB execution based on structure complexity.

**Parameters:**
- `num_atoms` (int): Number of atoms
- `num_bonds` (int): Number of bonds

**Returns:**
- `int`: Timeout in seconds (capped at 120s)

**Formula:**
```
timeout = 30 + 0.5 * num_atoms + 0.1 * num_bonds
timeout = min(timeout, 120)  # Cap at 120 seconds
```

**Example:**
```python
from slices.decoding_strategies import calculate_xtb_timeout

# Small structure
timeout = calculate_xtb_timeout(10, 20)
print(f"Timeout: {timeout} seconds")  # ~35 seconds

# Large structure
timeout = calculate_xtb_timeout(100, 200)
print(f"Timeout: {timeout} seconds")  # 120 seconds (capped)
```

**Purpose:**
- Prevents premature timeouts for complex structures
- Reduces wasted time for simple structures

---

## Usage Examples

### Using Cycle Basis Optimization

```python
from slices.decoding_strategies import CycleBasisOptimizer
import numpy as np

# Cycle representation matrix
cycle_rep = np.array([
    [1, 0, 1, 0],
    [0, 1, 1, 0],
    [1, 1, 0, 1]
])

# Find optimal cycle ordering
optimal_inds = CycleBasisOptimizer.select_optimal_cycle_basis(cycle_rep, max_attempts=50)
print(f"Optimal cycle ordering: {optimal_inds}")
```

### Using Bond Parameter Fallback

```python
from slices.decoding_strategies import BondParameterFallback

# Estimate bond lengths when XTB fails
bond_lengths = {}
pairs = [('Si', 'O'), ('Al', 'O'), ('Fe', 'O')]

for atom1, atom2 in pairs:
    length_bohr = BondParameterFallback.estimate_bond_length(atom1, atom2)
    length_angstrom = length_bohr * 0.529177
    bond_lengths[f"{atom1}-{atom2}"] = length_angstrom
    print(f"{atom1}-{atom2}: {length_angstrom:.3f} Å")
```

### Using Multi-Start Optimization

```python
from slices.decoding_strategies import MultiStartOptimizer
import numpy as np

def objective(x):
    # Your objective function
    return np.sum((x - target)**2)

x0 = np.random.random(10)
bounds = [(-1, 1)] * 10

best_x, best_value, info = MultiStartOptimizer.optimize(
    objective, x0, bounds, n_starts=5,
    factr=1e7, pgtol=1e-5
)
```

### Using Adaptive Timeout

```python
from slices.decoding_strategies import calculate_xtb_timeout

# Calculate timeout based on structure
num_atoms = 50
num_bonds = 100
timeout = calculate_xtb_timeout(num_atoms, num_bonds)

print(f"XTB timeout for {num_atoms} atoms, {num_bonds} bonds: {timeout}s")
```

---

## Integration with SLICES

These improvements are automatically used when available:

```python
from slices.core import SLICES

# Improvements are used automatically in robust decoding
backend = SLICES()
reconstructed, energy = backend.robust_SLICES2structure(slices_string)
```

**Automatic usage:**
- Cycle basis optimization in `get_lattice_basis()`
- Bond parameter fallback in `get_inner_p_target()`
- Multi-start optimization in `to_structures()`
- Progressive relaxation in `SLICES2structure()`
- Adaptive timeout in XTB execution

---

## Scientific References

1. Boyd, P. M., & Woo, T. K. (2016). A generalized method for constructing hypothetical nanoporous materials of any net topology from graph theory. *CrystEngComm*, 18(21), 3777-3792.

2. Lenstra, A. K., Lenstra, H. W., & Lovász, L. (1982). Factoring polynomials with rational coefficients. *Mathematische Annalen*, 261(4), 515-534.

3. Nocedal, J., & Wright, S. (2006). *Numerical optimization*. Springer Science & Business Media.

4. Pauling, L. (1960). *The nature of the chemical bond*. Cornell University Press.

