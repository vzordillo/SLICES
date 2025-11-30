# Advanced Usage Guide

## Custom MLIP Models

You can use different MLIP models for relaxation:

```python
from slices.core import SLICES

# Use CHGNet (recommended alternative to M3GNet)
backend = SLICES(relax_model='chgnet')

# Use MatGL
backend = SLICES(relax_model='matgl')

# Use MatterSim
backend = SLICES(relax_model='mattersim')
```

## Performance Tuning

### Optimizer Selection

```python
# Use FIRE optimizer (faster, less stable)
backend = SLICES(relax_model='chgnet', optimizer='FIRE')

# Use BFGS optimizer (default, more stable)
backend = SLICES(relax_model='chgnet', optimizer='BFGS')
```

### Convergence Parameters

```python
# Stricter convergence (slower, more accurate)
backend = SLICES(relax_model='chgnet', fmax=0.1, steps=200)

# Faster convergence (less accurate)
backend = SLICES(relax_model='chgnet', fmax=0.5, steps=50)
```

## Batch Processing

For processing multiple structures:

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

backend = SLICES(relax_model='chgnet')

structures = [Structure.from_file(f) for f in structure_files]
slices_strings = []

for structure in structures:
    slices = backend.structure2SLICES(structure)
    slices_strings.append(slices)
```

## Memory Optimization

For large-scale processing:

```python
import gc
import tensorflow as tf

backend = SLICES(relax_model='chgnet')

for structure in large_structure_list:
    slices = backend.structure2SLICES(structure)
    # Clear memory periodically
    tf.keras.backend.clear_session()
    gc.collect()
```

## Encoding Strategies

Different encoding strategies have different characteristics:

- **Strategy 1**: Human-readable, verbose
- **Strategy 2**: Compact, element symbols truncated
- **Strategy 3**: Balanced
- **Strategy 4**: Includes space group info (recommended)

```python
# Use strategy 4 (recommended)
slices = backend.structure2SLICES(structure, strategy=4)
```

