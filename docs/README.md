# SLICES Code Documentation

Complete code documentation for the SLICES (Simplified Line-Input Crystal-Encoding System) codebase.

## Documentation Structure

This directory contains API documentation organized by module:

### API Reference (`api/`)

1. **[api/API_CORE.md](api/API_CORE.md)** - Core SLICES class and encoding/decoding functionality
2. **[api/API_MLIP.md](api/API_MLIP.md)** - Machine Learning Interatomic Potential (MLIP) relaxers
3. **[api/API_GRAPH.md](api/API_GRAPH.md)** - Graph theory operations (Net class, SystreDB)
4. **[api/API_UTILITIES.md](api/API_UTILITIES.md)** - Utility functions for file operations, parallel processing, space groups
5. **[api/API_DECODING_STRATEGIES.md](api/API_DECODING_STRATEGIES.md)** - Decoding strategies
6. **[api/API_CONFIG.md](api/API_CONFIG.md)** - Configuration constants and data structures

### Benchmark Data (`benchmarks/`)

Contains benchmark results, comparison reports, and datasets used for testing and evaluation.

## Quick Navigation

### Main Classes

- **SLICES** ([api/API_CORE.md](api/API_CORE.md#slices-class)) - Main encoding/decoding class
- **MLIPRelaxer** ([api/API_MLIP.md](api/API_MLIP.md#mliprelaxer-base-class)) - Base class for MLIP models
- **Net** ([api/API_GRAPH.md](api/API_GRAPH.md#net-class)) - Periodic graph representation
- **SystreDB** ([api/API_GRAPH.md](api/API_GRAPH.md#systredb-class)) - Systre database reader

### Key Functions

- **Encoding**: `structure2SLICES()` - Convert structure to SLICES string
- **Decoding**: `SLICES2structure()` - Convert SLICES string to structure
- **Validation**: `check_SLICES()` - Validate SLICES string
- **MLIP Factory**: `get_relaxer()` - Get MLIP relaxer instance

## Usage Examples

### Basic Encoding/Decoding

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Initialize
backend = SLICES(relax_model='m3gnet')

# Load and encode
structure = Structure.from_file('example.cif')
slices_string = backend.structure2SLICES(structure)

# Decode
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
```

### Using Different MLIP Models

```python
from slices.mlip_relaxer import get_relaxer

# Get different relaxers
m3gnet = get_relaxer('m3gnet')
chgnet = get_relaxer('chgnet')
mattersim = get_relaxer('mattersim', device='cuda')
```

### Graph Operations

```python
from slices.tobascco_net import Net
import numpy as np

# Create and analyze net
x_dat = [('1', '2', {'label': 'e1'}), ('2', '3', {'label': 'e2'})]
net = Net(x_dat, dim=3)
net.voltage = np.array([[1, 0, 0], [0, 1, 0]])

net.simple_cycle_basis()
net.get_lattice_basis()
```

## Module Overview

### `slices.core`
Main module containing the SLICES class and all encoding/decoding functionality.

**Key components:**
- SLICES class
- Exception classes
- XTB integration
- MLIP integration
- Graph construction

### `slices.mlip_relaxer`
Unified interface for MLIP models.

**Key components:**
- MLIPRelaxer base class
- M3GNetRelaxer, CHGNetRelaxer, MatterSimRelaxer, ORBv3Relaxer
- get_relaxer() factory function

### `slices.tobascco_net`
Graph theory operations for periodic structures.

**Key components:**
- Net class for periodic graphs
- Cycle/cocycle basis computation
- Lattice basis determination
- SystreDB for reading network files

### `slices.utils`
Utility functions for file operations and parallel processing.

**Key components:**
- File collection functions
- Parallel processing
- SLURM job management
- Statistical functions

### `slices.utils_wyckoff`
Space group encoding/decoding utilities.

**Key components:**
- Tokenized encoding
- Space group number conversion

### `slices.decoding_strategies`
Decoding strategies.

**Key components:**
- Cycle basis optimization
- Bond parameter fallback
- Multi-start optimization
- Progressive relaxation

### `slices.config`
Configuration constants.

**Key components:**
- OFFSET array (supercell offsets)
- LJ_PARAMS_LIST (Lennard-Jones parameters)
- PERIODIC_DATA (periodic table data)

## Finding Documentation

- **Looking for a specific function?** Use your editor's search across all files in `api/` directory
- **Need usage examples?** Each API file contains usage examples for its functions
- **Want to understand the architecture?** See [TECHNICAL.md](../TECHNICAL.md) in the root directory

## Contributing

When adding new functions or classes:
1. Add docstrings following the existing format
2. Update the relevant file in `api/` directory
3. Include usage examples
4. Keep documentation factual and in plain language

