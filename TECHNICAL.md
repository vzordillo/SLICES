# Technical Documentation

This document contains all technical documentation for SLICES: API reference, system architecture, and algorithm enhancements.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [API Reference](#api-reference)
   - [Core Module](#core-module)
   - [MLIP Relaxer](#mlip-relaxer)
   - [Tobascco Net](#tobascco-net)
3. [Decoding Enhancements](#decoding-enhancements)

---

## System Architecture

SLICES (Simplified Line-Input Crystal-Encoding System) is an invertible crystal structure representation system.

### Component Architecture

#### Core Components

1. **SLICES Class** (`src/slices/core.py`)
   - Main encoding/decoding interface
   - Graph construction and analysis
   - MLIP integration
   - XTB integration

2. **Net Class** (`src/slices/tobascco_net.py`)
   - Graph theory operations
   - Cycle/cocycle basis computation
   - Lattice basis determination

3. **MLIP Relaxer** (`src/slices/mlip_relaxer.py`)
   - Unified interface for MLIP models
   - Model-specific adapters
   - Fallback mechanisms

### Data Flow

#### Encoding Workflow

```
Structure → StructureGraph → Net → Cycle/Cocycle Basis → SLICES String
```

1. Convert structure to graph using local environment analysis
2. Extract cycle and cocycle basis
3. Compute lattice basis
4. Encode to SLICES string format

#### Decoding Workflow

```
SLICES String → Parse → Graph Reconstruction → Barycentric Embedding → 
ZL* Optimization → MLIP Relaxation → Structure
```

1. Parse SLICES string to extract graph topology
2. Reconstruct graph structure
3. Compute initial coordinates (barycentric embedding)
4. Optimize using ZL* algorithm
5. Relax using MLIP model

### Extension Points

#### Adding New MLIP Models

1. Create a new relaxer class inheriting from `MLIPRelaxer`
2. Implement the `relax()` method
3. Register in `get_relaxer()` factory function

#### Adding New Graph Methods

1. Add method to `structure2structure_graph()`
2. Update `graph_method` parameter validation
3. Test with known structures

### Dependencies

- **pymatgen**: Structure manipulation and analysis
- **networkx**: Graph operations
- **numpy/scipy**: Numerical computations
- **MLIP models**: Structure relaxation (M3GNet, CHGNet, MatterSim, ORBv3)
- **XTB**: Bond/angle parameter calculation

---

## API Reference

### Core Module

#### SLICES Class

Main class for encoding and decoding crystal structures to/from SLICES strings.

**Initialization:**
```python
SLICES(atom_types=None, edge_indices=None, to_jimages=None, 
       graph_method='econnn', check_results=False, 
       optimizer="BFGS", fmax=0.2, steps=100, relax_model="m3gnet")
```

**Parameters:**
- `atom_types` (np.array, optional): Atom types in a SLICES string
- `edge_indices` (np.array, optional): Edge indices in a SLICES string
- `to_jimages` (np.array, optional): Edge labels in a SLICES string
- `graph_method` (str): Graph method ('econnn', 'crystalnn', 'brunnernn', 'econ')
- `check_results` (bool): Output intermediate results for debugging
- `optimizer` (str): Optimizer for MLIP relaxation ("BFGS", "FIRE")
- `fmax` (float): Maximum force convergence criterion (default: 0.2)
- `steps` (int): Maximum optimization steps (default: 100)
- `relax_model` (str): MLIP model ('m3gnet', 'chgnet', 'mattersim', 'orbv3')

**Main Methods:**

**`structure2SLICES(structure, strategy=4)`**
- Encode a crystal structure to SLICES string
- Parameters: `structure` (Structure), `strategy` (int: 1, 2, 3, or 4)
- Returns: `str` - SLICES string representation

**`SLICES2structure(SLICES, strategy=4, fix_duplicate_edge=True)`**
- Decode a SLICES string to crystal structure
- Parameters: `SLICES` (str), `strategy` (int), `fix_duplicate_edge` (bool)
- Returns: `tuple` - (Structure, float) - Reconstructed structure and energy per atom

**Validation Methods:**
- `check_SLICES(SLICES, strategy=4, dupli_check=False, graph_rank_check=True)`: Validate SLICES string
- `check_SLICES_basic(SLICES, strategy=4)`: Basic validation
- `check_element(structure)`: Check if elements are supported (Z < 87)
- `check_2D(structure)`: Check if structure is 2D
- `check_3D(structure)`: Check if structure is 3D

**Error Handling:**
- `SLICESError`: Base exception class
- `SLICESEncodingError`: Encoding failures
- `SLICESDecodingError`: Decoding failures
- `GraphTopologyError`: Incompatible graph topology
- `LatticeBasisError`: Lattice basis computation failures
- `XTBExecutionError`: XTB binary execution failures
- `MLIPRelaxationError`: MLIP relaxation failures

### MLIP Relaxer

#### MLIPRelaxer Base Class

Abstract base class defining the relaxation interface.

**Methods:**
- `relax(structure, fmax=0.2, steps=100)`: Perform structure relaxation
  - Returns: Dictionary with 'final_structure' and 'trajectory'

#### Available Relaxers

**M3GNetRelaxer**
- Model: M3GNet (Materials Project)
- Framework: TensorFlow
- Optimizer: BFGS only
- Notes: Requires Keras 2 compatibility mode

**CHGNetRelaxer**
- Model: CHGNet (charge-informed GNN)
- Framework: PyTorch
- Optimizer: BFGS only

**MatterSimRelaxer**
- Model: MatterSim (Microsoft)
- Framework: PyTorch
- Optimizer: Auto-selected
- Notes: Auto-downloads models

**ORBv3Relaxer**
- Model: ORBv3 (Orbital Materials)
- Framework: PyTorch
- Optimizer: Auto-selected
- Notes: Multiple model variants available

#### Factory Function

**`get_relaxer(model_name, optimizer="BFGS")`**
- Returns appropriate relaxer instance based on model name
- Handles model initialization and error handling
- Falls back to M3GNet if model unavailable

### Tobascco Net

#### Net Class

Represents periodic graphs (nets) for crystal structures.

**Initialization:**
```python
Net(x_dat, dim=3)
```

**Key Methods:**

**`get_lattice_basis()`**
- Compute lattice basis vectors from cycle representation
- Returns: List of 3 lattice basis vectors or -1 if computation fails
- Uses SymPy for nullspace computation
- Includes cycle basis optimization option

**`is_integral(vect, tolerance=1e-6)`**
- Check if vector components are approximately integral
- Parameters: `vect` (np.array), `tolerance` (float)
- Returns: `bool`

**`clear_cache()`**
- Clear cached computations to free memory

**Error Classes:**
- `NetError`: Base exception
- `LatticeBasisError`: Lattice basis computation failures
- `CocycleBasisError`: Cocycle basis computation failures

#### SystreDB Class

Reads network topology files from Systre database format.

---

## Decoding Enhancements

This section describes the decoding algorithm enhancements implemented in SLICES.

### Overview

The codebase includes several enhancements to the decoding process, implemented in `src/slices/decoding_strategies.py` and integrated into the core decoding workflow.

### Implemented Enhancements

#### 1. Cycle Basis Selection

**Implementation**: `CycleBasisOptimizer.select_optimal_cycle_basis()` tries multiple random orderings and selects the one with highest linear independence rank.

**Purpose**: Selects cycle orderings with higher linear independence rank for lattice basis computation.

**Reference**: Boyd & Woo (2016) - Graph theory methods for crystal structures

#### 2. Relaxed Integrality Constraint

**Implementation**: `is_integral()` accepts tolerance parameter (default: 1e-6) for approximate integrality checking.

**Purpose**: Handles numerical precision issues in floating-point computations.

#### 3. Fallback Bond Parameter Estimation

**Implementation**: `BondParameterFallback` uses covalent radii (Pauling, 1960) to estimate bond lengths when XTB fails.

**Purpose**: Provides bond parameter estimates when XTB calculation fails or times out.

**Reference**: Pauling, L. (1960). The nature of the chemical bond.

#### 4. Adaptive XTB Timeout

**Implementation**: `calculate_xtb_timeout()` scales timeout based on structure complexity: `30 + 0.5*atoms + 0.1*bonds` (capped at 120s).

**Purpose**: Adjusts timeout duration based on structure size to prevent premature termination.

#### 5. Multi-Start Optimization

**Implementation**: `MultiStartOptimizer` runs ZL* optimization from multiple starting points and selects the result with lowest objective function value.

**Purpose**: Attempts to escape local minima in optimization.

**Reference**: Nocedal & Wright (2006). Numerical optimization.

#### 6. Adaptive Convergence Criteria

**Implementation**: `AdaptiveConvergence` adjusts `fmax` and `steps` based on structure size.

**Purpose**: Adapts convergence parameters for different structure sizes.

#### 7. Progressive MLIP Relaxation

**Implementation**: `ProgressiveRelaxer` tries multiple relaxation strategies (tight → loose) with fallback.

**Purpose**: Attempts multiple relaxation approaches if initial attempt fails.

#### 8. Error Recovery

**Implementation**: `robust_SLICES2structure()` implements fallback pipeline with multiple recovery strategies.

**Purpose**: Provides alternative decoding paths when standard decoding fails.

### Implementation Details

All enhancements are implemented in `src/slices/decoding_strategies.py` and integrated into `src/slices/core.py` and `src/slices/tobascco_net.py`.

**Backward Compatibility**: All enhancements are backward compatible:
- Original `SLICES2structure()` method unchanged
- Enhancements automatically used when available
- Graceful fallback if improvements module cannot be imported
- No breaking changes to existing code

### Benchmark Results

Based on test results from `docs/benchmarks/decoding_comparison_report_20251204_184955.txt`:
- Standard decoding (`SLICES2structure`): 98.82% success rate (24,214/24,502 structures)
- Robust decoding (`robust_SLICES2structure`): 99.49% success rate (24,377/24,502 structures)
- Improvement: +0.67% absolute improvement, 163 additional successful decodings

### Scientific References

1. Boyd, P. M., & Woo, T. K. (2016). A generalized method for constructing hypothetical nanoporous materials of any net topology from graph theory. *CrystEngComm*, 18(21), 3777-3792.

2. Lenstra, A. K., Lenstra, H. W., & Lovász, L. (1982). Factoring polynomials with rational coefficients. *Mathematische Annalen*, 261(4), 515-534.

3. Nocedal, J., & Wright, S. (2006). *Numerical optimization*. Springer Science & Business Media.

4. Pauling, L. (1960). *The nature of the chemical bond*. Cornell University Press.

