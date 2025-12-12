# SLICES Core API Documentation

Complete reference for the `slices.core` module, which contains the main `SLICES` class and all encoding/decoding functionality.

## Table of Contents

1. [Exception Classes](#exception-classes)
2. [SLICES Class](#slices-class)
   - [Initialization](#initialization)
   - [Encoding Methods](#encoding-methods)
   - [Decoding Methods](#decoding-methods)
   - [Validation Methods](#validation-methods)
   - [Utility Methods](#utility-methods)
   - [XTB Integration Methods](#xtb-integration-methods)
   - [Structure Relaxation Methods](#structure-relaxation-methods)

---

## Exception Classes

### `SLICESError`
Base exception class for all SLICES-related errors.

**Usage:**
```python
try:
    # SLICES operation
except SLICESError as e:
    print(f"SLICES error: {e}")
```

### `SLICESEncodingError(SLICESError)`
Raised when encoding a structure to SLICES fails.

**Common causes:**
- Invalid structure (e.g., 2D structure, unsupported elements)
- Graph construction failure
- Missing required structure properties

### `SLICESDecodingError(SLICESError)`
Raised when decoding a SLICES string to structure fails.

**Common causes:**
- Invalid SLICES string syntax
- Graph topology incompatible for 3D embedding
- Lattice basis computation failure

### `GraphTopologyError(SLICESError)`
Raised when graph topology is incompatible for SLICES operations.

**Common causes:**
- Graph rank H1(X,Z) < 3 (cannot create 3D embedding)
- Missing required cycles or cocycles
- Incompatible periodic boundary conditions

### `LatticeBasisError(GraphTopologyError)`
Raised when lattice basis cannot be computed from cycle vectors.

**Common causes:**
- Insufficient independent cycles
- Cycle vectors not forming valid lattice basis
- Numerical precision issues

### `XTBExecutionError(SLICESError)`
Raised when XTB binary execution fails.

**Common causes:**
- XTB binary not found or not executable
- XTB execution timeout
- XTB calculation failure for structure

### `MLIPRelaxationError(SLICESError)`
Raised when MLIP relaxation fails.

**Common causes:**
- MLIP model not installed
- Structure convergence failure
- Memory or computational resource issues

### `TimeoutException(Exception)`
Raised when a function execution exceeds the timeout limit.

---

## SLICES Class

Main class for encoding crystal structures to SLICES strings and decoding SLICES strings back to structures.

### Initialization

```python
SLICES(atom_types=None, edge_indices=None, to_jimages=None, 
       graph_method='econnn', check_results=False, 
       optimizer="BFGS", fmax=0.2, steps=100, relax_model="m3gnet")
```

**Parameters:**

- `atom_types` (np.array, optional): Atomic numbers of atoms. Used when initializing from existing graph data. Defaults to None.
- `edge_indices` (np.array, optional): Edge indices connecting atoms. Used when initializing from existing graph data. Defaults to None.
- `to_jimages` (np.array, optional): Periodic boundary condition labels for edges. Used when initializing from existing graph data. Defaults to None.
- `graph_method` (str, optional): Method for analyzing local chemical environments to generate labeled quotient graphs.
  - Options: `'econnn'` (default), `'crystalnn'`, `'brunnernn'`, `'mininn'`
  - `'econnn'`: EconNN - Economic coordination number method
  - `'crystalnn'`: CrystalNN - Crystal coordination number method
  - `'brunnernn'`: BrunnerNN - Reciprocal space method
  - `'mininn'`: MinimumDistanceNN - Minimum distance method
- `check_results` (bool, optional): If True, outputs intermediate results to files for debugging. Defaults to False.
- `optimizer` (str, optional): Optimizer algorithm for MLIP relaxation. Options: `"BFGS"`, `"FIRE"`. Defaults to `"BFGS"`.
- `fmax` (float, optional): Maximum force convergence criterion in eV/Å. Lower values require stricter convergence. Defaults to 0.2.
- `steps` (int, optional): Maximum number of optimization steps during MLIP relaxation. Defaults to 100.
- `relax_model` (str, optional): Machine learning interatomic potential model for structure relaxation.
  - Options: `'m3gnet'` (default), `'chgnet'`, `'mattersim'`, `'orbv3'`
  - Defaults to `"m3gnet"`.

**Example:**
```python
from slices.core import SLICES

# Default initialization
backend = SLICES()

# Custom initialization
backend = SLICES(
    graph_method='crystalnn',
    relax_model='chgnet',
    fmax=0.1,
    steps=200
)
```

---

## Encoding Methods

### `structure2SLICES(structure, strategy=4)`

Encodes a crystal structure to a SLICES string.

**Parameters:**
- `structure` (Structure): pymatgen Structure object to encode
- `strategy` (int, optional): Encoding strategy. Options: 1, 2, 3, 4. Defaults to 4.
  - Strategy 1: Edge-based format with atom symbols per edge
  - Strategy 2: Compact format with padded indices
  - Strategy 3: Space-separated format
  - Strategy 4: Tokenized space group + space-separated format

**Returns:**
- `str`: SLICES string representation

**Example:**
```python
from pymatgen.core.structure import Structure

structure = Structure.from_file('example.cif')
backend = SLICES()

# Encode with default strategy (4)
slices_string = backend.structure2SLICES(structure)
print(slices_string)

# Encode with specific strategy
slices_string = backend.structure2SLICES(structure, strategy=3)
```

**Raises:**
- `SLICESEncodingError`: If encoding fails

---

### `structure2crystal_graph_rep(structure)`

Converts a structure to crystal graph representation without encoding to string.

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `tuple`: (atom_types, edge_indices, to_jimages, space_group_number)
  - `atom_types` (np.array): Atomic numbers
  - `edge_indices` (np.array): Edge indices [atom1_idx, atom2_idx]
  - `to_jimages` (np.array): Periodic boundary labels [i, j, k]
  - `space_group_number` (int or None): Space group number

**Example:**
```python
atom_types, edge_indices, to_jimages, sg = backend.structure2crystal_graph_rep(structure)
print(f"Atoms: {len(atom_types)}, Edges: {len(edge_indices)}")
```

---

### `structure2randomSLICES(structure, strategy=4, num=50, shuffle_atom_order=True, shuffle_bond_order=True, flip_bonds=True, batch_multiplier=10)`

Generates multiple randomly augmented SLICES strings from a structure.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `strategy` (int, optional): Encoding strategy. Defaults to 4.
- `num` (int, optional): Number of unique SLICES strings to generate. Defaults to 50.
- `shuffle_atom_order` (bool, optional): Randomly shuffle atom order. Defaults to True.
- `shuffle_bond_order` (bool, optional): Randomly shuffle bond order. Defaults to True.
- `flip_bonds` (bool, optional): Randomly flip bond directions. Defaults to True.
- `batch_multiplier` (int, optional): Multiplier for generating candidates to ensure uniqueness. Defaults to 10.

**Returns:**
- `list`: List of unique SLICES strings (includes original)

**Example:**
```python
# Generate 100 augmented SLICES strings
slices_list = backend.structure2randomSLICES(structure, num=100)
print(f"Generated {len(slices_list)} unique SLICES strings")
```

---

## Decoding Methods

### `SLICES2structure(SLICES, strategy=4, fix_duplicate_edge=True)`

Decodes a SLICES string back to a crystal structure.

**Parameters:**
- `SLICES` (str): SLICES string to decode
- `strategy` (int, optional): Encoding strategy used (must match encoding strategy). Defaults to 4.
- `fix_duplicate_edge` (bool, optional): If True, removes duplicate edges that may occur due to RNN generation errors. Defaults to True.

**Returns:**
- `tuple`: (Structure, float)
  - `Structure`: Reconstructed pymatgen Structure object (MLIP-relaxed)
  - `float`: Energy per atom in eV/atom predicted by the MLIP model

**Example:**
```python
slices_string = "Nd Si Ru 0 1 2 0 0 0 1 2 0 0 0 2 0 0 0 0"
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
print(f"Formula: {reconstructed.formula}")
```

**Raises:**
- `SLICESDecodingError`: If decoding fails at any stage
- `LatticeBasisError`: If lattice basis cannot be computed
- `XTBExecutionError`: If XTB bond parameter calculation fails
- `MLIPRelaxationError`: If MLIP relaxation fails

---

### `robust_SLICES2structure(SLICES, strategy=4, fix_duplicate_edge=True, max_attempts=3)`

Robust decoding with multiple fallback strategies.

**Parameters:**
- `SLICES` (str): SLICES string to decode
- `strategy` (int, optional): Encoding strategy. Defaults to 4.
- `fix_duplicate_edge` (bool, optional): Fix duplicate edges if present. Defaults to True.
- `max_attempts` (int, optional): Maximum number of alternative strategy attempts. Defaults to 3.

**Returns:**
- `tuple`: (Structure, float) - Reconstructed structure and energy per atom. If MLIP relaxation fails, returns ZL*-optimized structure with energy 0.0.

**Example:**
```python
# Use robust decoding
reconstructed, energy = backend.robust_SLICES2structure(slices_string)
```

**Fallback strategies:**
1. Standard decoding
2. Alternative encoding strategies
3. Fallback bond parameters (if XTB fails)
4. Progressive relaxation (multiple convergence criteria)
5. Return structure without MLIP relaxation if all else fails

---

### `to_structures(bond_scaling=1.05, delta_theta=0.005, delta_x=0.45, lattice_shrink=1, lattice_expand=1.25, angle_weight=0.5, vbond_param_ave_covered=0.00, vbond_param_ave=0.01, repul=True)`

Converts graph representation to crystal structures (internal method used by decoding).

**Parameters:**
- `bond_scaling` (float, optional): Empirical scaling factor applied to XTB bond lengths. Defaults to 1.05.
- `delta_theta` (float, optional): Angle change limit (deprecated). Defaults to 0.005.
- `delta_x` (float, optional): Maximum allowed change in cocycle representation. Defaults to 0.45.
- `lattice_shrink` (float, optional): Maximum lattice shrinkage factor. Defaults to 1.0.
- `lattice_expand` (float, optional): Maximum lattice expansion factor. Defaults to 1.25.
- `angle_weight` (float, optional): Weight of angular constraint terms in ZL* objective. Defaults to 0.5.
- `vbond_param_ave_covered` (float, optional): Repulsive potential for bonded pairs. Defaults to 0.00.
- `vbond_param_ave` (float, optional): Repulsive potential for non-bonded pairs. Defaults to 0.01.
- `repul` (bool, optional): Include Lennard-Jones repulsive potential. Defaults to True.

**Returns:**
- `tuple`: (list, float)
  - `list`: List of Structure objects [barycentric, ZL*-optimized, MLIP-relaxed]
  - `float`: Energy per atom (0.0 if MLIP relaxation failed)

**Note:** This is an internal method. Use `SLICES2structure()` for decoding.

---

## Validation Methods

### `check_SLICES(SLICES, strategy=4, dupli_check=False, graph_rank_check=True)`

Validates if a SLICES string conforms to proper syntax and graph topology.

**Parameters:**
- `SLICES` (str): SLICES string to validate
- `strategy` (int, optional): Encoding strategy. Defaults to 4.
- `dupli_check` (bool, optional): Check for duplicate edges. Defaults to False.
- `graph_rank_check` (bool, optional): Verify graph rank H1(X,Z) >= 3 for 3D embedding. Defaults to True.

**Returns:**
- `bool`: True if SLICES is valid, False otherwise

**Example:**
```python
is_valid = backend.check_SLICES(slices_string)
if not is_valid:
    print("Invalid SLICES string")
```

**Validation checks:**
1. Syntax validation (parsing)
2. All nodes covered by edges
3. Graph rank H1(X,Z) >= 3 (if `graph_rank_check=True`)
4. Edge labels cover 3 dimensions
5. Duplicate edge check (if `dupli_check=True`)
6. Lattice basis computation test

---

### `check_SLICES_basic(SLICES, strategy=4)`

Basic syntax validation (faster than full validation).

**Parameters:**
- `SLICES` (str): SLICES string to validate
- `strategy` (int, optional): Encoding strategy. Defaults to 4.

**Returns:**
- `bool`: True if basic syntax is valid, False otherwise

**Example:**
```python
# Quick syntax check
if backend.check_SLICES_basic(slices_string):
    # Proceed with full validation
    if backend.check_SLICES(slices_string):
        # Decode
        structure, energy = backend.SLICES2structure(slices_string)
```

---

### `check_element(structure)`

Checks if all atoms have atomic numbers < 87 (XTB limitation).

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `bool`: True if all atoms have Z < 87, False otherwise

**Example:**
```python
if not backend.check_element(structure):
    print("Structure contains unsupported elements (Z >= 87)")
```

---

### `check_2D(structure)`

Checks if structure is 2-dimensional.

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `bool`: True if all components are 2D, False otherwise

---

### `check_3D(structure)`

Checks if structure is 3-dimensional (single 3D component).

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `bool`: True if structure has exactly one 3D component, False otherwise

---

### `check_structural_validity(str1)`

Checks structural validity with minimum distance > 0.5 Å.

**Parameters:**
- `str1` (Structure): pymatgen Structure object

**Returns:**
- `bool`: True if minimum interatomic distance > 0.5 Å, False otherwise

---

## Utility Methods

### `get_canonical_SLICES(SLICES, strategy=4)`

Converts a SLICES string to its canonical form.

**Parameters:**
- `SLICES` (str): SLICES string
- `strategy` (int, optional): Encoding strategy. Defaults to 4.

**Returns:**
- `str`: Canonical SLICES string

**Example:**
```python
canonical = backend.get_canonical_SLICES(slices_string)
```

**Canonical form:**
- Atoms sorted by atomic number
- Edges sorted by indices
- Edge labels sorted consistently

---

### `SLICES2formula(SLICES)`

Extracts chemical formula from SLICES string.

**Parameters:**
- `SLICES` (str): SLICES string

**Returns:**
- `str`: Chemical formula (e.g., "Si2O4")

**Example:**
```python
formula = backend.SLICES2formula(slices_string)
print(f"Composition: {formula}")
```

---

### `SLICES2space_group_number(SLICES, strategy=4, fix_duplicate_edge=True)`

Determines space group number from SLICES string using standard placement.

**Parameters:**
- `SLICES` (str): SLICES string
- `strategy` (int, optional): Encoding strategy. Defaults to 4.
- `fix_duplicate_edge` (bool, optional): Fix duplicate edges. Defaults to True.

**Returns:**
- `int`: Space group number (1-230) or None if determination fails

**Example:**
```python
sg_num = backend.SLICES2space_group_number(slices_string)
if sg_num:
    print(f"Space group: {sg_num}")
```

---

## XTB Integration Methods

### `get_nbf_blist()`

Generates neighbor list (nbf) and bond list (blist) for XTB calculation.

**Returns:**
- `tuple`: (nbf, blist)
  - `nbf` (str): Neighbor list string in XTB format
  - `blist` (np.array): Array of bond indices [atom1_idx, atom2_idx] in central cell

**Note:** Internal method used by `get_inner_p_target()`.

---

### `get_inner_p_target(bond_scaling=1.05)`

Computes inner product target matrix from XTB GFN-FF calculation.

**Parameters:**
- `bond_scaling` (float, optional): Empirical scaling factor applied to XTB bond lengths. Defaults to 1.05.

**Returns:**
- `tuple`: (inner_p_target, colattice_inds, colattice_weights)
  - `inner_p_target` (np.array): Inner product matrix (n_bonds x n_bonds)
  - `colattice_inds` (list): List of [i, j] pairs for off-diagonal elements
  - `colattice_weights` (list): Weights for each constraint (normalized)

**Raises:**
- `XTBExecutionError`: If XTB execution fails and fallback estimation is unavailable

**Note:** Uses fallback bond parameter estimation if XTB fails.

---

### `get_inner_p_target_debug(bond_scaling=1.05)`

Same as `get_inner_p_target()` but outputs intermediate files for debugging.

**Parameters:**
- `bond_scaling` (float, optional): Empirical scaling factor. Defaults to 1.05.

**Returns:**
- `tuple`: Same as `get_inner_p_target()`

**Output files (if `check_results=True`):**
- `testBonds_cut.top`: XTB topology file
- `gfnff_lists.json`: XTB output
- `inner_p_target.json`: Inner product matrix

---

## Structure Relaxation Methods

### `relax(structure)`

Relaxes a structure using MLIP model (for structures ≤20 atoms).

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `tuple`: (Structure, float) - Relaxed structure and energy per atom

**Example:**
```python
relaxed, energy = backend.relax(structure)
```

---

### `relax_large_cell1(structure)`

Relaxes a structure using MLIP model (for structures 21-40 atoms).

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `tuple`: (Structure, float) - Relaxed structure and energy per atom

---

### `relax_large_cell2(structure)`

Relaxes a structure using MLIP model (for structures >40 atoms).

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `tuple`: (Structure, float) - Relaxed structure and energy per atom

---

## Graph Construction Methods

### `structure2structure_graph(structure)`

Converts a Structure to a StructureGraph using the configured graph method.

**Parameters:**
- `structure` (Structure): pymatgen Structure object

**Returns:**
- `StructureGraph`: Pymatgen StructureGraph object with nodes (atoms) and edges (bonds)

---

### `cif2structure_graph(string)`

Converts a CIF file string to a StructureGraph.

**Parameters:**
- `string` (str): String content of a CIF file

**Returns:**
- `tuple`: (StructureGraph, Structure) - Pymatgen StructureGraph and Structure objects

---

## Internal Methods

### `from_SLICES(SLICES, strategy=4, fix_duplicate_edge=True)`

Extracts edge_indices, to_jimages, and atom_types from a SLICES string.

**Parameters:**
- `SLICES` (str): SLICES string
- `strategy` (int, optional): Encoding strategy. Defaults to 4.
- `fix_duplicate_edge` (bool, optional): Fix duplicate edges. Defaults to True.

**Note:** Internal method. Sets `self.atom_types`, `self.edge_indices`, `self.to_jimages`.

---

### `to_SLICES(strategy=4)`

Outputs a SLICES string based on stored atom_types, edge_indices, and to_jimages.

**Parameters:**
- `strategy` (int, optional): Encoding strategy. Defaults to 4.

**Returns:**
- `str`: SLICES string

**Note:** Requires `from_SLICES()` to be called first.

---

### `convert_graph()`

Converts edge_indices and to_jimages to networkx format.

**Returns:**
- `tuple`: (x_dat, net_voltage)
  - `x_dat` (list): NetworkX graph data
  - `net_voltage` (np.array): Edge labels

---

## Static Methods

### `get_index_list_allow_duplicates(ori, mod)`

Maps elements from original list to indices in modified list, allowing duplicates.

**Parameters:**
- `ori`: Original list of elements
- `mod`: Modified list to search for matching elements

**Returns:**
- `list`: List of indices mapping ori elements to their positions in mod

---

## Usage Examples

### Basic Encoding/Decoding
```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Initialize
backend = SLICES(relax_model='m3gnet')

# Load structure
structure = Structure.from_file('example.cif')

# Encode
slices_string = backend.structure2SLICES(structure)
print(f"SLICES: {slices_string}")

# Decode
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
```

### Validation Before Decoding
```python
# Validate SLICES string before decoding
if backend.check_SLICES(slices_string):
    reconstructed, energy = backend.SLICES2structure(slices_string)
else:
    print("Invalid SLICES string")
```

### Using Different Graph Methods
```python
# Use CrystalNN for graph construction
backend = SLICES(graph_method='crystalnn')
slices_string = backend.structure2SLICES(structure)
```

### Batch Processing with Augmentation
```python
# Generate multiple augmented SLICES strings
slices_list = backend.structure2randomSLICES(structure, num=100)
for slices_str in slices_list:
    # Process each variant
    pass
```

### Error Handling
```python
from slices.core import SLICES, SLICESDecodingError, LatticeBasisError

try:
    reconstructed, energy = backend.SLICES2structure(slices_string)
except LatticeBasisError as e:
    print(f"Graph topology issue: {e}")
except SLICESDecodingError as e:
    print(f"Decoding failed: {e}")
```

