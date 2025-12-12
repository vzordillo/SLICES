# Graph Theory API Documentation

Complete reference for the `slices.tobascco_net` module, which provides graph theory operations for periodic crystal structures.

## Table of Contents

1. [Exception Classes](#exception-classes)
2. [Net Class](#net-class)
3. [SystreDB Class](#systredb-class)

---

## Exception Classes

### `NetError`
Base exception class for Net-related errors.

### `LatticeBasisError(NetError)`
Raised when lattice basis cannot be computed from cycle vectors.

**Common causes:**
- Insufficient independent cycles
- Cycle vectors not forming valid lattice basis
- Numerical precision issues

### `CocycleBasisError(NetError)`
Raised when cocycle basis cannot be computed.

**Common causes:**
- Graph topology incompatible for cocycle computation
- Missing required graph properties

---

## Net Class

Represents a periodic graph (net) for crystal structure analysis.

### Initialization

```python
Net(graph=None, dim=3, options=None)
```

**Parameters:**
- `graph` (list, optional): List of tuples representing edges. Format: `[(v1, v2, {'label': 'e1'}), ...]`. Defaults to None.
- `dim` (int, optional): Dimensionality of the net. Defaults to 3.
- `options` (Any, optional): Additional options. Defaults to None.

**Example:**
```python
from slices.tobascco_net import Net

# Create from edge list
x_dat = [('1', '2', {'label': 'e1'}), ('2', '3', {'label': 'e2'})]
net = Net(x_dat, dim=3)
net.voltage = np.array([[1, 0, 0], [0, 1, 0]])  # Edge labels
```

### Key Methods

#### `simple_cycle_basis()`

Computes cycle basis using a minimum spanning tree.

**Returns:**
- `None`: Modifies `self.cycle` and `self.cycle_rep` in place

**Algorithm:**
1. Finds minimum spanning tree of the graph
2. For each edge not in the tree, finds the cycle it completes
3. Builds basis vectors from these cycles

**Example:**
```python
net.simple_cycle_basis()
print(f"Found {len(net.cycle)} cycles")
```

---

#### `get_lattice_basis()`

Computes lattice basis vectors from cycle representation.

**Returns:**
- `None`: Modifies `self.lattice_basis` in place

**Raises:**
- `LatticeBasisError`: If lattice basis cannot be computed

**Algorithm:**
1. Uses SymPy for nullspace computation
2. Finds integral lattice vectors from cycle representation
3. Attempts multiple cycle orderings if cycle basis optimization is available

**Example:**
```python
net.simple_cycle_basis()
net.get_lattice_basis()
print(f"Lattice basis:\n{net.lattice_basis}")
```

**Note:** Requires `simple_cycle_basis()` to be called first.

---

#### `get_cocycle_basis()`

Computes the cocycle basis for the graph.

**Returns:**
- `None`: Modifies `self.cocycle` and `self.cocycle_rep` in place

**Raises:**
- `CocycleBasisError`: If cocycle basis cannot be computed

**Example:**
```python
net.get_cocycle_basis()
print(f"Found {len(net.cocycle)} cocycles")
```

---

#### `get_metric_tensor()`

Computes the metric tensor describing unit cell geometry.

**Returns:**
- `None`: Modifies `self.metric_tensor` in place

**Example:**
```python
net.get_metric_tensor()
print(f"Metric tensor:\n{net.metric_tensor}")
```

---

#### `clear_cache()`

Clears cached properties and large arrays to free memory.

**Returns:**
- `None`

**Use case:** Call when Net object is no longer needed to prevent memory accumulation during batch processing.

**Example:**
```python
# After processing
net.clear_cache()
```

---

### Properties

After calling the methods above, the following properties are available:

- `lattice_basis` (np.array): Lattice basis vectors
- `metric_tensor` (np.array): Metric tensor describing unit cell geometry
- `cycle` (np.array): Cycle basis vectors
- `cycle_rep` (np.array): Cycle representation
- `cocycle` (np.array): Cocycle basis vectors
- `cocycle_rep` (np.array): Cocycle representation
- `periodic_rep` (np.array): Periodic representation (alpha(B))
- `lattice_arcs` (np.array): Lattice arcs (edge vectors in lattice coordinates)

---

## SystreDB Class

Reads network topology files from Systre database format.

### Initialization

```python
SystreDB(filename=None)
```

**Parameters:**
- `filename` (str, optional): Path to Systre database file. Defaults to None.

**Example:**
```python
from slices.tobascco_net import SystreDB

db = SystreDB('systre_database.arc')
# Access networks by name
net_graph = db['network_name']
voltages = db.voltages['network_name']
```

### Methods

#### `read_store_file(file=None)`

Reads and stores networks from a Systre database file.

**Parameters:**
- `file` (str, optional): Path to Systre database file. Defaults to None.

**Note:** File format is specific to systre.arc files and may change with Systre updates.

---

## Usage Examples

### Basic Net Operations

```python
from slices.tobascco_net import Net
import numpy as np

# Create net from edge list
x_dat = [
    ('1', '2', {'label': 'e1'}),
    ('2', '3', {'label': 'e2'}),
    ('3', '1', {'label': 'e3'})
]
net = Net(x_dat, dim=3)

# Set edge labels (periodic boundary conditions)
net.voltage = np.array([
    [1, 0, 0],  # e1
    [0, 1, 0],  # e2
    [0, 0, 1]   # e3
])

# Compute cycle basis
net.simple_cycle_basis()

# Compute lattice basis
try:
    net.get_lattice_basis()
    print("Lattice basis computed successfully")
    print(net.lattice_basis)
except LatticeBasisError as e:
    print(f"Failed to compute lattice basis: {e}")

# Compute cocycle basis
try:
    net.get_cocycle_basis()
    print("Cocycle basis computed successfully")
except CocycleBasisError as e:
    print(f"Failed to compute cocycle basis: {e}")

# Get metric tensor
net.get_metric_tensor()
print(f"Metric tensor:\n{net.metric_tensor}")
```

### Error Handling

```python
from slices.tobascco_net import Net, LatticeBasisError, CocycleBasisError

net = Net(x_dat, dim=3)
net.voltage = voltage_array

try:
    net.simple_cycle_basis()
    net.get_lattice_basis()
    net.get_cocycle_basis()
except LatticeBasisError as e:
    print(f"Lattice basis computation failed: {e}")
    # Handle error - may indicate incompatible graph topology
except CocycleBasisError as e:
    print(f"Cocycle basis computation failed: {e}")
    # Handle error
```

### Memory Management

```python
# Process multiple structures
nets = []
for structure_data in structures:
    net = Net(edge_list, dim=3)
    net.simple_cycle_basis()
    net.get_lattice_basis()
    # ... process net ...
    nets.append(net)

# Clear cache when done
for net in nets:
    net.clear_cache()
```

---

## Integration with SLICES

The Net class is used internally by SLICES for graph operations:

```python
from slices.core import SLICES

backend = SLICES()
# Net operations happen automatically during encoding/decoding
slices_string = backend.structure2SLICES(structure)
# Net is created and used internally in to_structures()
```

---

## Mathematical Background

### Cycle Basis
A cycle basis is a set of independent cycles in a graph. For a 3D periodic structure, at least 3 independent cycles are needed to determine the lattice basis.

### Cocycle Basis
A cocycle basis represents the cutsets of the graph, complementary to the cycle basis.

### Lattice Basis
The lattice basis vectors are computed from the nullspace of the cycle representation matrix, using the constraint that they must be integral (or approximately integral within tolerance).

### Metric Tensor
The metric tensor describes the geometry of the unit cell, encoding lengths and angles of lattice vectors.

