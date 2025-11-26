# Getting Started with SLICES

## Quick Start

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load a crystal structure
structure = Structure.from_file('examples/NdSiRu.cif')

# Initialize SLICES backend
backend = SLICES(relax_model='chgnet')

# Encode to SLICES string
slices_string = backend.structure2SLICES(structure)
print(f"SLICES: {slices_string}")

# Decode back to structure
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy} eV/atom")
```

## Installation Verification

Run the verification script:
```bash
python scripts/verify_baseline.py
```

## Common Issues

1. **Import errors**: Ensure conda environment is activated
2. **MLIP model errors**: Install required MLIP packages
3. **XTB errors**: Ensure XTB binary is available

