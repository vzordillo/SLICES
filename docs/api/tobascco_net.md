# tobascco_net API Documentation

## Net Class

Represents a periodic graph (net) for crystal structures.

### Initialization

```python
Net(graph=None, dim=3, options=None)
```

**Parameters:**
- `graph`: NetworkX graph or edge list
- `dim` (int): Dimension (default: 3)
- `options`: Additional options

### Key Methods

#### `simple_cycle_basis()`

Compute a simple cycle basis for the graph.

**Returns:** None (sets `self.cycle` attribute)

#### `get_lattice_basis()`

Compute lattice basis from cycle vectors.

**Raises:**
- `LatticeBasisError`: If lattice basis cannot be computed

**Returns:** None (sets `self.lattice_basis` attribute)

#### `get_cocycle_basis()`

Compute cocycle basis (complementary to cycles).

**Raises:**
- `CocycleBasisError`: If cocycle basis cannot be computed

**Returns:** None (sets `self.cocycle` attribute)

#### `clear_cache()`

Clear cached properties to free memory.

**Returns:** None

### Properties

- `graph`: NetworkX MultiDiGraph
- `cycle`: Cycle basis (numpy array)
- `cocycle`: Cocycle basis (numpy array)
- `lattice_basis`: Lattice basis vectors
- `cycle_rep`: Cycle representation
- `cocycle_rep`: Cocycle representation

### Error Handling

Custom exceptions:
- `NetError`: Base exception
- `LatticeBasisError`: Lattice basis computation failures
- `CocycleBasisError`: Cocycle basis computation failures

