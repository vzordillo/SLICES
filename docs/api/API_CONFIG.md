# Configuration API Documentation

Reference for configuration constants and data structures used in SLICES.

## Table of Contents

1. [OFFSET](#offset)
2. [LJ_PARAMS_LIST](#lj_params_list)
3. [PERIODIC_DATA](#periodic_data)

---

## OFFSET

Array defining offsets for 3x3x3 supercell construction.

**Type:** `np.array`

**Shape:** (27, 3)

**Description:** Contains all combinations of [-1, 0, 1] in 3D, representing the 27 unit cells in a 3x3x3 supercell.

**Usage:**
```python
from slices.config import OFFSET

# OFFSET[i] gives the (i, j, k) offset for unit cell i in the supercell
# For example:
# OFFSET[0] = [-1, -1, -1]  # Bottom-left-back cell
# OFFSET[13] = [0, 0, 0]    # Center cell
# OFFSET[26] = [1, 1, 1]    # Top-right-front cell
```

**Example:**
```python
from slices.config import OFFSET

# Get offset for center cell (index 13)
center_offset = OFFSET[13]  # [0, 0, 0]

# Iterate over all 27 cells
for i, offset in enumerate(OFFSET):
    print(f"Cell {i}: offset = {offset}")
```

---

## LJ_PARAMS_LIST

Lennard-Jones parameters for different atomic numbers.

**Type:** `list`

**Format:** List of tuples `(atomic_number, sigma, epsilon)`
- `atomic_number` (int): Atomic number (Z)
- `sigma` (float): LJ sigma parameter (Å)
- `epsilon` (float): LJ epsilon parameter (eV)

**Usage:**
```python
from slices.config import LJ_PARAMS_LIST

# Find LJ parameters for silicon (Z=14)
for z, sigma, epsilon in LJ_PARAMS_LIST:
    if z == 14:
        print(f"Si: sigma={sigma} Å, epsilon={epsilon} eV")
        break
```

**Purpose:** Used for repulsive potential calculations in ZL* optimization to prevent atom collisions.

**Example:**
```python
from slices.config import LJ_PARAMS_LIST

# Create lookup dictionary
lj_params = {z: (sigma, epsilon) for z, sigma, epsilon in LJ_PARAMS_LIST}

# Get parameters for multiple elements
elements = [6, 8, 14]  # C, O, Si
for z in elements:
    if z in lj_params:
        sigma, epsilon = lj_params[z]
        print(f"Z={z}: sigma={sigma:.3f} Å, epsilon={epsilon:.4f} eV")
```

---

## PERIODIC_DATA

Periodic table data as pandas DataFrame.

**Type:** `pandas.DataFrame`

**Columns:**
- Atomic number (Z)
- Element symbol
- Other periodic table properties

**Usage:**
```python
from slices.config import PERIODIC_DATA

# Get atomic number for element symbol
si_z = PERIODIC_DATA.loc[PERIODIC_DATA["symbol"] == "Si"]["atomic_number"].values[0]
print(f"Silicon atomic number: {si_z}")

# Get element symbol for atomic number
element = PERIODIC_DATA.loc[PERIODIC_DATA["atomic_number"] == 14]["symbol"].values[0]
print(f"Z=14 is {element}")
```

**Example:**
```python
from slices.config import PERIODIC_DATA

# Convert atomic numbers to symbols
atomic_numbers = [6, 8, 14]  # C, O, Si
symbols = []
for z in atomic_numbers:
    symbol = PERIODIC_DATA.loc[PERIODIC_DATA["atomic_number"] == z]["symbol"].values[0]
    symbols.append(symbol)
print(f"Symbols: {symbols}")  # ['C', 'O', 'Si']

# Convert symbols to atomic numbers
symbols = ['Si', 'O', 'Al']
atomic_numbers = []
for symbol in symbols:
    z = PERIODIC_DATA.loc[PERIODIC_DATA["symbol"] == symbol]["atomic_number"].values[0]
    atomic_numbers.append(z)
print(f"Atomic numbers: {atomic_numbers}")  # [14, 8, 13]
```

---

## Usage Examples

### Working with OFFSET

```python
from slices.config import OFFSET
import numpy as np

# Create supercell mapping
supercell_map = {}
for i, offset in enumerate(OFFSET):
    supercell_map[tuple(offset)] = i

# Find index for specific offset
offset = (0, 0, 0)  # Center cell
if offset in supercell_map:
    idx = supercell_map[offset]
    print(f"Center cell index: {idx}")  # 13
```

### Working with LJ Parameters

```python
from slices.config import LJ_PARAMS_LIST

# Create parameter dictionary
lj_dict = {}
for z, sigma, epsilon in LJ_PARAMS_LIST:
    lj_dict[z] = {'sigma': sigma, 'epsilon': epsilon}

# Get parameters for common elements
common_elements = {1: 'H', 6: 'C', 8: 'O', 14: 'Si', 26: 'Fe'}
for z, symbol in common_elements.items():
    if z in lj_dict:
        params = lj_dict[z]
        print(f"{symbol} (Z={z}): σ={params['sigma']:.3f} Å, ε={params['epsilon']:.4f} eV")
```

### Working with Periodic Data

```python
from slices.config import PERIODIC_DATA

# Get all element symbols
all_symbols = PERIODIC_DATA["symbol"].tolist()
print(f"Total elements: {len(all_symbols)}")

# Filter by atomic number range
light_elements = PERIODIC_DATA[PERIODIC_DATA["atomic_number"] < 20]
print(f"Light elements (Z<20): {light_elements['symbol'].tolist()}")
```

---

## Integration with SLICES

These configuration constants are used internally by SLICES:

```python
from slices.core import SLICES

# OFFSET is used in get_nbf_blist() for supercell construction
# LJ_PARAMS_LIST is used in get_uncovered_pair_lj() and get_covered_pair_lj()
# PERIODIC_DATA is used in from_SLICES() for atomic number conversion

backend = SLICES()
# Configuration is used automatically during encoding/decoding
```

---

## Notes

- **OFFSET**: Fixed 27-element array representing 3x3x3 supercell offsets
- **LJ_PARAMS_LIST**: Empirical parameters for repulsive potential calculations
- **PERIODIC_DATA**: Standard periodic table data for element lookups

All configuration data is loaded at module import time and is read-only.

