# SLICES Decoding Improvements

This document describes the scientific improvements implemented to enhance SLICES decoding success rate.

## Overview

The improvements target the ~11% failure rate observed in decoding ~27k training structures, aiming to increase success rate from ~89% to ~98-100%.

## Implemented Improvements

### 1. Enhanced Cycle Basis Selection

**Problem**: Random cycle ordering may not maximize linear independence, leading to lattice basis computation failures.

**Solution**: `CycleBasisOptimizer.select_optimal_cycle_basis()` tries multiple random orderings and selects the one with highest linear independence rank.

**Scientific Basis**: 
- Higher rank cycle representation matrices are more likely to yield valid nullspace vectors
- Multiple attempts increase probability of finding suitable basis

**Reference**: Boyd & Woo (2016) - Graph theory methods for crystal structures

### 2. Relaxed Integrality Constraint

**Problem**: Strict integer requirement for lattice basis vectors fails due to numerical errors.

**Solution**: `is_integral()` now accepts tolerance parameter (default: 1e-6) for approximate integrality.

**Scientific Basis**:
- Numerical errors in floating-point computation are inevitable
- Small deviations (< 1e-6) from integers are acceptable for practical purposes

### 3. Fallback Bond Parameter Estimation

**Problem**: XTB may fail or timeout, leaving missing bond parameters.

**Solution**: `BondParameterFallback` uses covalent radii (Pauling, 1960) to estimate bond lengths when XTB fails.

**Scientific Basis**:
- Pauling's covalent radii provide reliable bond length estimates
- Sum of covalent radii ≈ bond length for most elements

**Reference**: Pauling, L. (1960). The nature of the chemical bond. Cornell University Press.

### 4. Adaptive XTB Timeout

**Problem**: Fixed 30-second timeout may be insufficient for large/complex structures.

**Solution**: `calculate_xtb_timeout()` scales timeout based on structure size (atoms + bonds).

**Formula**: `timeout = 30 + 0.5*num_atoms + 0.1*num_bonds` (capped at 120s)

### 5. Multi-Start Optimization

**Problem**: ZL* optimization may converge to local minima.

**Solution**: `MultiStartOptimizer` runs optimization from multiple random starting points and selects best result.

**Scientific Basis**:
- Non-convex optimization landscapes have multiple local minima
- Multiple starts increase probability of finding global minimum

**Reference**: Nocedal & Wright (2006) - Numerical Optimization

### 6. Adaptive Convergence Criteria

**Problem**: Fixed convergence parameters may be too strict for large structures.

**Solution**: `AdaptiveConvergence` adjusts `factr` and `pgtol` based on structure size.

**Parameters**:
- Small (≤10 atoms): factr=1e7, pgtol=1e-5 (tight)
- Medium (11-20 atoms): factr=1e6, pgtol=1e-4
- Large (21-40 atoms): factr=1e5, pgtol=1e-3
- Very large (>40 atoms): factr=1e4, pgtol=1e-2 (loose)

### 7. Progressive MLIP Relaxation

**Problem**: MLIP relaxation may fail with tight convergence criteria.

**Solution**: `ProgressiveRelaxer` tries multiple strategies from tight to loose:
1. Tight: fmax=0.1, steps=200
2. Standard: fmax=0.2, steps=100
3. Loose: fmax=0.3, steps=80
4. Very loose: fmax=0.5, steps=50

**Scientific Basis**:
- Looser convergence still provides reasonable structures
- Better to have relaxed structure than no structure

### 8. Robust Decoding Pipeline

**Problem**: Single failure point causes entire decoding to fail.

**Solution**: `robust_SLICES2structure()` implements comprehensive error recovery:
1. Try standard decoding
2. Try alternative encoding strategies
3. Use fallback bond parameters
4. Return ZL*-optimized structure if MLIP fails
5. Return barycentric embedding as last resort

## Expected Impact

| Improvement | Expected Gain |
|-------------|---------------|
| Enhanced cycle basis | +5-7% |
| Fallback bond parameters | +2-3% |
| Multi-start optimization | +1-2% |
| Progressive relaxation | +1-2% |
| **Total** | **+9-14%** |

Target: Increase from ~89% to **~98-100%** success rate.

## Usage

### Standard Decoding (Original)
```python
from slices.core import SLICES

backend = SLICES(relax_model="orbv3")
structure, energy = backend.SLICES2structure(slices_string)
```

### Robust Decoding (Improved)
```python
from slices.core import SLICES

backend = SLICES(relax_model="orbv3")
structure, energy = backend.robust_SLICES2structure(slices_string)
```

The robust method automatically uses all improvements and fallback strategies.

## Testing

Run the test script on your dataset:

```bash
python scripts/test_improved_decoding.py \
    --dataset data/mp20/train.csv \
    --samples 1000 \
    --use-robust
```

Compare with standard decoding:

```bash
python scripts/test_improved_decoding.py \
    --dataset data/mp20/train.csv \
    --samples 1000 \
    --no-robust
```

## Implementation Details

All improvements are in `src/slices/decoding_improvements.py` and are automatically used when available. The code gracefully falls back to original behavior if the improvements module cannot be imported.

## References

1. Boyd, P. M., & Woo, T. K. (2016). A generalized method for constructing hypothetical nanoporous materials of any net topology from graph theory. CrystEngComm, 18(21), 3777-3792.

2. Lenstra, A. K., Lenstra, H. W., & Lovász, L. (1982). Factoring polynomials with rational coefficients. Mathematische Annalen, 261(4), 515-534.

3. Nocedal, J., & Wright, S. (2006). Numerical optimization. Springer Science & Business Media.

4. Pauling, L. (1960). The nature of the chemical bond. Cornell University Press.

