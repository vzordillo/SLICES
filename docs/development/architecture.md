# SLICES Architecture

## System Overview

SLICES (Simplified Line-Input Crystal-Encoding System) is an invertible crystal structure representation system.

## Component Architecture

### Core Components

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

## Data Flow

### Encoding Workflow

```
Structure → StructureGraph → Net → Cycle/Cocycle Basis → SLICES String
```

1. Convert structure to graph using local environment analysis
2. Extract cycle and cocycle basis
3. Compute lattice basis
4. Encode to SLICES string format

### Decoding Workflow

```
SLICES String → Parse → Graph Reconstruction → Barycentric Embedding → 
ZL* Optimization → MLIP Relaxation → Structure
```

1. Parse SLICES string to extract graph topology
2. Reconstruct graph structure
3. Compute initial coordinates (barycentric embedding)
4. Optimize using ZL* algorithm
5. Relax using MLIP model

## Extension Points

### Adding New MLIP Models

1. Create a new relaxer class inheriting from `MLIPRelaxer`
2. Implement the `relax()` method
3. Register in `get_relaxer()` factory function

### Adding New Graph Methods

1. Add method to `structure2structure_graph()`
2. Update `graph_method` parameter validation
3. Test with known structures

## Dependencies

- **pymatgen**: Structure manipulation and analysis
- **networkx**: Graph operations
- **numpy/scipy**: Numerical computations
- **MLIP models**: Structure relaxation (M3GNet, CHGNet, etc.)
- **XTB**: Bond/angle parameter calculation

