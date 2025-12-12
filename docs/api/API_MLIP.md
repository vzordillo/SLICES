# MLIP Relaxer API Documentation

Complete reference for the `slices.mlip_relaxer` module, which provides a unified interface for multiple Machine Learning Interatomic Potential (MLIP) models.

## Table of Contents

1. [MLIPRelaxer Base Class](#mliprelaxer-base-class)
2. [M3GNetRelaxer](#m3gnetrelaxer)
3. [CHGNetRelaxer](#chgnetrelaxer)
4. [MatterSimRelaxer](#mattersimrelaxer)
5. [ORBv3Relaxer](#orbv3relaxer)
6. [Factory Function](#factory-function)

---

## MLIPRelaxer Base Class

Abstract base class defining the interface for all MLIP relaxers.

### `relax(structure, fmax=0.2, steps=100)`

Performs structure relaxation using the MLIP model.

**Parameters:**
- `structure` (Structure): pymatgen Structure object to relax
- `fmax` (float, optional): Maximum force convergence criterion in eV/Å. Optimization stops when all atomic forces are below this value. Defaults to 0.2.
- `steps` (int, optional): Maximum number of optimization steps. Defaults to 100.

**Returns:**
- `dict`: Dictionary containing:
  - `'final_structure'` (Structure): Optimized Structure object
  - `'trajectory'` (object): Trajectory object with `'energies'` attribute (list of energies at each optimization step)

**Example:**
```python
from slices.mlip_relaxer import MLIPRelaxer
from pymatgen.core.structure import Structure

# This is abstract - use concrete implementations
# relaxer = MLIPRelaxer()  # This will raise an error
```

---

## M3GNetRelaxer

Adapter for M3GNet (Materials Project 3D Graph Network) MLIP model.

### Initialization

```python
M3GNetRelaxer(optimizer="BFGS")
```

**Parameters:**
- `optimizer` (str, optional): Optimizer algorithm. Options: `"BFGS"`. Defaults to `"BFGS"`.

**Raises:**
- `ImportError`: If M3GNet is not installed
- `RuntimeError`: If Keras 3 compatibility issues occur

**Example:**
```python
from slices.mlip_relaxer import M3GNetRelaxer

relaxer = M3GNetRelaxer(optimizer="BFGS")
```

**Notes:**
- Requires TensorFlow and M3GNet packages
- Uses Keras 2 compatibility mode (TF_USE_LEGACY_KERAS=1)
- May require `tf_keras` package for full compatibility

### `relax(structure, fmax=0.2, steps=100)`

Relaxes structure using M3GNet model.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `fmax` (float, optional): Maximum force convergence criterion (eV/Å). Defaults to 0.2.
- `steps` (int, optional): Maximum optimization steps. Defaults to 100.

**Returns:**
- `dict`: Dictionary with `'final_structure'` and `'trajectory'` keys

**Example:**
```python
from pymatgen.core.structure import Structure
from slices.mlip_relaxer import M3GNetRelaxer

relaxer = M3GNetRelaxer()
structure = Structure.from_file('example.cif')

result = relaxer.relax(structure, fmax=0.2, steps=100)
relaxed_structure = result['final_structure']
energies = result['trajectory'].energies
```

---

## CHGNetRelaxer

Adapter for CHGNet (Charge-informed Graph Neural Network) MLIP model.

### Initialization

```python
CHGNetRelaxer()
```

**Raises:**
- `ImportError`: If CHGNet is not installed

**Example:**
```python
from slices.mlip_relaxer import CHGNetRelaxer

relaxer = CHGNetRelaxer()
```

**Notes:**
- Uses PyTorch framework
- Automatically selects device (CPU, CUDA, or MPS)
- No optimizer parameter (uses internal optimizer)

### `relax(structure, fmax=0.2, steps=100)`

Relaxes structure using CHGNet model.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `fmax` (float, optional): Maximum force convergence criterion (eV/Å). Defaults to 0.2.
- `steps` (int, optional): Maximum optimization steps. Defaults to 100.

**Returns:**
- `dict`: Dictionary with `'final_structure'` and `'trajectory'` keys

**Example:**
```python
from slices.mlip_relaxer import CHGNetRelaxer

relaxer = CHGNetRelaxer()
result = relaxer.relax(structure, fmax=0.1, steps=200)
```

---

## MatterSimRelaxer

Adapter for MatterSim MLIP model from Microsoft.

### Initialization

```python
MatterSimRelaxer(device="cpu")
```

**Parameters:**
- `device` (str, optional): Computing device. Options: `"cpu"`, `"cuda"`, `"mps"`. Defaults to `"cpu"`.

**Raises:**
- `ImportError`: If MatterSim is not installed

**Example:**
```python
from slices.mlip_relaxer import MatterSimRelaxer

# CPU
relaxer = MatterSimRelaxer(device="cpu")

# GPU (if available)
relaxer = MatterSimRelaxer(device="cuda")
```

**Notes:**
- Uses ASE interface for optimization
- Automatically downloads pretrained model on first use
- Uses BFGS optimizer internally

### `relax(structure, fmax=0.2, steps=100)`

Relaxes structure using MatterSim model.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `fmax` (float, optional): Maximum force convergence criterion (eV/Å). Defaults to 0.2.
- `steps` (int, optional): Maximum optimization steps. Defaults to 100.

**Returns:**
- `dict`: Dictionary with `'final_structure'` and `'trajectory'` keys

**Example:**
```python
from slices.mlip_relaxer import MatterSimRelaxer

relaxer = MatterSimRelaxer(device="cpu")
result = relaxer.relax(structure)
```

---

## ORBv3Relaxer

Adapter for ORBv3 (Orbital Materials) MLIP model.

### Initialization

```python
ORBv3Relaxer(model_name="orb-v3-direct-inf-mpa", device="cpu")
```

**Parameters:**
- `model_name` (str, optional): Model variant name. Defaults to `"orb-v3-direct-inf-mpa"`.
- `device` (str, optional): Computing device. Options: `"cpu"`, `"cuda"`, `"mps"`. Defaults to `"cpu"`.

**Raises:**
- `ImportError`: If ORBv3 is not installed
- `ValueError`: If model_name is not found

**Example:**
```python
from slices.mlip_relaxer import ORBv3Relaxer

relaxer = ORBv3Relaxer(model_name="orb-v3-direct-inf-mpa", device="cpu")
```

**Notes:**
- Uses ASE interface for optimization
- Multiple model variants available
- Uses BFGS optimizer internally

### `relax(structure, fmax=0.2, steps=100)`

Relaxes structure using ORBv3 model.

**Parameters:**
- `structure` (Structure): pymatgen Structure object
- `fmax` (float, optional): Maximum force convergence criterion (eV/Å). Defaults to 0.2.
- `steps` (int, optional): Maximum optimization steps. Defaults to 100.

**Returns:**
- `dict`: Dictionary with `'final_structure'` and `'trajectory'` keys

**Example:**
```python
from slices.mlip_relaxer import ORBv3Relaxer

relaxer = ORBv3Relaxer()
result = relaxer.relax(structure)
```

---

## Factory Function

### `get_relaxer(model_name="m3gnet", **kwargs)`

Factory function to create the appropriate MLIP relaxer instance.

**Parameters:**
- `model_name` (str, optional): Name of the MLIP model. Options:
  - `'m3gnet'`: M3GNet (Materials Project, default)
  - `'chgnet'`: CHGNet (charge-informed GNN)
  - `'mattersim'`: MatterSim (Microsoft)
  - `'orbv3'`: ORBv3 (Orbital Materials)
  Defaults to `"m3gnet"`.
- `**kwargs`: Additional arguments passed to the relaxer constructor:
  - `optimizer` (str): Optimizer algorithm ("BFGS", "FIRE", etc.) - for M3GNet
  - `device` (str): Computing device ("cpu", "cuda", "mps", etc.) - for MatterSim, ORBv3
  - `model_name` (str): Specific model variant name - for ORBv3

**Returns:**
- `MLIPRelaxer`: Instance of the appropriate relaxer class

**Raises:**
- `ValueError`: If model_name is not in the list of supported models
- `ImportError`: If the required package for the model is not installed
- `RuntimeError`: If model initialization fails (e.g., Keras compatibility issues)

**Example:**
```python
from slices.mlip_relaxer import get_relaxer

# Get M3GNet relaxer (default)
relaxer = get_relaxer('m3gnet', optimizer='BFGS')

# Get CHGNet relaxer
relaxer = get_relaxer('chgnet')

# Get MatterSim relaxer with GPU
relaxer = get_relaxer('mattersim', device='cuda')

# Get ORBv3 relaxer with specific model
relaxer = get_relaxer('orbv3', model_name='orb-v3-direct-inf-mpa', device='cpu')
```

**Usage in SLICES:**
```python
from slices.core import SLICES

# M3GNet (default)
backend = SLICES(relax_model='m3gnet')

# CHGNet
backend = SLICES(relax_model='chgnet')

# MatterSim
backend = SLICES(relax_model='mattersim')
```

---

## Model Comparison

| Model | Framework | Optimizer | Device Support | Notes |
|-------|-----------|-----------|----------------|-------|
| M3GNet | TensorFlow | BFGS | CPU | Default, requires Keras 2 compatibility |
| CHGNet | PyTorch | Internal | CPU/CUDA/MPS | Fast, good accuracy |
| MatterSim | PyTorch | BFGS | CPU/CUDA/MPS | Microsoft model, auto-downloads |
| ORBv3 | PyTorch | BFGS | CPU/CUDA/MPS | Multiple model variants |

---

## Error Handling

### Common Errors

**ImportError:**
```python
try:
    relaxer = get_relaxer('m3gnet')
except ImportError as e:
    print(f"Model not installed: {e}")
    # Install with: pip install m3gnet
```

**RuntimeError (Keras compatibility):**
```python
try:
    relaxer = get_relaxer('m3gnet')
except RuntimeError as e:
    if "Keras 3" in str(e):
        # Install tf_keras: pip install tf_keras
        pass
```

**ValueError (Invalid model):**
```python
try:
    relaxer = get_relaxer('invalid_model')
except ValueError as e:
    print(f"Invalid model: {e}")
```

---

## Usage Examples

### Basic Usage
```python
from slices.mlip_relaxer import get_relaxer
from pymatgen.core.structure import Structure

# Get relaxer
relaxer = get_relaxer('chgnet')

# Load structure
structure = Structure.from_file('example.cif')

# Relax
result = relaxer.relax(structure, fmax=0.2, steps=100)
relaxed = result['final_structure']
energies = result['trajectory'].energies
```

### Comparing Models
```python
from slices.mlip_relaxer import get_relaxer

models = ['m3gnet', 'chgnet', 'mattersim']
results = {}

for model_name in models:
    try:
        relaxer = get_relaxer(model_name)
        result = relaxer.relax(structure, fmax=0.2, steps=50)
        results[model_name] = result['trajectory'].energies[-1]
    except Exception as e:
        print(f"{model_name} failed: {e}")

print("Final energies:", results)
```

### Using with SLICES
```python
from slices.core import SLICES

# Use different models for decoding
for model in ['m3gnet', 'chgnet', 'mattersim']:
    backend = SLICES(relax_model=model)
    reconstructed, energy = backend.SLICES2structure(slices_string)
    print(f"{model}: {energy:.4f} eV/atom")
```

