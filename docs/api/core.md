# SLICES Core API Documentation

## SLICES Class

Main class for encoding and decoding crystal structures to/from SLICES strings.

### Initialization

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
- `relax_model` (str): MLIP model ('m3gnet', 'chgnet', 'matgl', 'mattersim', 'orbv3')

### Main Methods

#### `structure2SLICES(structure, strategy=4)`

Encode a crystal structure to SLICES string.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `strategy` (int): Encoding strategy (1, 2, 3, or 4)

**Returns:**
- `str`: SLICES string representation

#### `SLICES2structure(SLICES, strategy=4, fix_duplicate_edge=True)`

Decode a SLICES string to crystal structure.

**Parameters:**
- `SLICES` (str): SLICES string
- `strategy` (int): Encoding strategy used
- `fix_duplicate_edge` (bool): Fix duplicate edges if present

**Returns:**
- `tuple`: (Structure, float) - Reconstructed structure and energy per atom

### Validation Methods

- `check_SLICES(SLICES, strategy=4, dupli_check=False, graph_rank_check=True)`: Validate SLICES string
- `check_SLICES_basic(SLICES, strategy=4)`: Basic validation
- `check_element(structure)`: Check if elements are supported (Z < 87)
- `check_2D(structure)`: Check if structure is 2D
- `check_3D(structure)`: Check if structure is 3D

### Error Handling

Custom exceptions:
- `SLICESError`: Base exception
- `SLICESEncodingError`: Encoding failures
- `SLICESDecodingError`: Decoding failures
- `GraphTopologyError`: Incompatible graph topologies
- `XTBExecutionError`: XTB binary execution failures
- `MLIPRelaxationError`: MLIP relaxation failures

