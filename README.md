# SLICES

**Simplified Line-Input Crystal-Encoding System**

An invertible crystal structure representation system for materials science.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPL--2.1-blue.svg)](LICENSE)

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Testing](#testing)
- [Benchmarks](#benchmarks)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Installation

### Prerequisites

- Python 3.9 or higher
- Conda (recommended) or pip
- Git

### Step 1: Python Environment

```bash
# Create conda environment
conda create --name slices python=3.9 -y
conda activate slices

# Install core dependencies
pip install tensorflow-cpu==2.13.0
pip install --no-deps m3gnet
pip install smact==2.5.5 ase==3.22.1 pymatgen==2024.8.9
pip install scipy==1.13.0 scikit-learn==1.3.1 numpy==1.26.4
pip install torch torchvision

# Install SLICES
git clone https://github.com/xiaohang007/SLICES.git
cd SLICES
pip install -e .

# Install MLIP models (optional)
pip install chgnet mattersim orb-models
```

### Step 2: XTB Binary

SLICES requires a custom XTB binary for decoding. **The codebase automatically detects the correct binary** for your operating system.

#### Automatic Detection

The system checks in this order:
1. Custom binary in `src/slices/` directory (platform-specific)
2. System XTB from PATH (fallback with warning)

Detection happens automatically on import—no configuration needed.

#### Platform-Specific Setup

<details>
<summary><b>Linux (x86-64)</b> - Click to expand</summary>

The repository includes a pre-built Linux binary:
- Location: `src/slices/xtb_noring_nooutput_nostdout_noCN`
- Automatically detected and used
- No additional steps required

</details>

<details>
<summary><b>macOS</b> - Click to expand</summary>

**Option 1: Build from source (Recommended)**

```bash
git clone https://github.com/xiaohang007/xtb.git
cd xtb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
cp xtb_noring_nooutput_nostdout_noCN ../../SLICES/src/slices/
```

**Option 2: Use system XTB (Fallback)**
- Install: `brew install xtb`
- Note: May lack required flags, causing decoding failures

**Option 3: Linux binary on macOS (Not Recommended)**
- System will warn about compatibility issues
- Build from source for best results

</details>

<details>
<summary><b>Windows</b> - Click to expand</summary>

**Option 1: Build Windows binary (Recommended)**

```bash
git clone https://github.com/xiaohang007/xtb.git
cd xtb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -G "Visual Studio 17 2022"
cmake --build . --config Release
copy Release\xtb_noring_nooutput_nostdout_noCN.exe ..\..\SLICES\src\slices\
```

**Option 2: Use WSL2**
- Install WSL2 and use Linux binary
- Follow Linux installation instructions within WSL2

**Option 3: Use system XTB (Fallback)**
- System XTB from PATH (may lack required flags)

</details>

### Step 3: Verification

```bash
python scripts/utilities/validate_installation.py
```

**Expected Output:**
```
✓ All required packages installed
✓ XTB binary found and compatible
✓ MLIP models available
✓ Installation validation passed!
```

Check which XTB is being used:
```python
from slices.core import SLICES
import os
print("XTB path:", os.environ.get("XTB_MOD_PATH"))
```

---

## Quick Start

### Basic Example

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load a crystal structure
structure = Structure.from_file('examples/NdSiRu.cif')

# Initialize SLICES (M3GNet is default)
backend = SLICES(relax_model='m3gnet')

# Encode structure to SLICES string
slices_string = backend.structure2SLICES(structure)
print(f"SLICES: {slices_string}")

# Decode SLICES string back to structure
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
```

### What Happens

1. **Encoding**: Structure → Graph → Cycles → SLICES String
2. **Decoding**: SLICES String → Graph → Coordinates → MLIP Relaxation → Structure

### Augment and Canonicalize SLICES

The same crystal structure can be represented by multiple SLICES strings due to different atom orderings. Augmentation generates multiple representations, and canonicalization reduces them to a unique form.

**Why This Matters:**
- **Data Augmentation**: Generate multiple training examples from one structure
- **Uniqueness**: Canonical form ensures identical structures have identical SLICES strings
- **Comparison**: Compare structures by comparing canonical SLICES strings

**Example:**
```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load crystal structure
structure = Structure.from_file('examples/Sr3Ru2O7.cif')
backend = SLICES(graph_method='econnn')

# Generate augmented SLICES (50 variations with random atom order)
slices_list = backend.structure2SLICESAug_atom_order(
    structure=structure, 
    strategy=4, 
    num=50
)

# Remove duplicates
slices_list_unique = list(set(slices_list))
print(f"Generated {len(slices_list)} SLICES, {len(slices_list_unique)} unique")

# Convert all to canonical form
canonical_slices_list = []
for slices_str in slices_list_unique:
    canonical = backend.get_canonical_SLICES(slices_str, strategy=4)
    canonical_slices_list.append(canonical)

# All canonical forms should be identical
canonical_set = set(canonical_slices_list)
print(f"Canonical forms: {len(canonical_set)} unique")
# Output: All augmented SLICES reduce to 1 canonical SLICES
```

**How It Works:**
- **Augmentation**: Randomly permutes atom order while preserving structure topology
- **Canonicalization**: Sorts atoms by atomic number, edges by indices, and edge labels consistently

---

## How It Works

### Encoding Process

```
Structure → Graph → Cycles → Lattice → SLICES String
```

1. **Build Graph**: Convert structure to labeled quotient graph (atoms = nodes, bonds = edges)
2. **Find Cycles**: Identify independent cycles in the graph
3. **Compute Lattice**: Calculate lattice vectors from cycle information
4. **Generate String**: Convert graph to compact text format

### Decoding Process

```
SLICES String → Graph → XTB Parameters → Coordinates → MLIP Relaxation → Structure
```

1. **Parse String**: Extract atom types, bonds, and periodic boundary conditions
2. **Rebuild Graph**: Reconstruct the graph structure
3. **Calculate Parameters**: Use XTB to predict bond lengths and angles
4. **Generate Coordinates**: Create initial atomic positions
5. **Optimize Structure**: Use MLIP models to refine the structure

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Graph Representation** | Crystal structure as labeled quotient graph (nodes=atoms, edges=bonds, labels=periodic boundaries) |
| **Cycle Basis** | Independent cycles determine lattice vectors (3D requires ≥3 cycles) |
| **Lattice Basis** | Computed from cycle vectors using nullspace computation |
| **Barycentric Embedding** | Initial atomic coordinates from graph structure |
| **ZL* Optimization** | Coordinates optimized to match XTB-predicted bond lengths/angles |
| **MLIP Relaxation** | Final structure refinement using machine learning potentials |

---

## Configuration

### MLIP Model Selection

```python
# M3GNet (default)
backend = SLICES(relax_model='m3gnet', fmax=0.2, steps=100)

# CHGNet
backend = SLICES(relax_model='chgnet', fmax=0.2, steps=100)

# MatterSim
backend = SLICES(relax_model='mattersim', fmax=0.2, steps=100)

# ORBv3
backend = SLICES(relax_model='orbv3', fmax=0.2, steps=100)
```

### Available Models

| Model | Description |
|-------|-------------|
| `m3gnet` | Default model (Materials Project) |
| `chgnet` | Charge-informed GNN |
| `mattersim` | Microsoft's deep learning potential |
| `orbv3` | Orbital Materials potential |

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `relax_model` | `"m3gnet"` | MLIP model to use |
| `fmax` | `0.2` | Force convergence (eV/Å). Lower = stricter |
| `steps` | `100` | Maximum optimization steps |
| `optimizer` | `"BFGS"` | Optimizer algorithm |
| `graph_method` | `"econnn"` | Graph construction method |

---

## Testing

### Run All Tests

```bash
pip install pytest pytest-cov
pytest tests/
pytest tests/ --cov=src/slices --cov-report=html
```

### Test Specific Components

```bash
# Encoding/decoding
pytest tests/unit/test_core_encoding.py
pytest tests/unit/test_core_decoding.py

# MLIP integration
pytest tests/integration/test_mlip_integration.py

# Round-trip (encode then decode)
pytest tests/integration/test_round_trip.py
```

### Validate Installation

```bash
python scripts/utilities/validate_installation.py
```

---

## Benchmarks

### Benchmark Dataset

Location: `docs/benchmarks/train_encoded_decoded_orbv3.csv`

- Encoded/decoded structures with ORBv3 energy calculations
- Used for testing and validation
- Format: CSV with SLICES strings, structures, energies, space group, formula, POSCAR

### Running Benchmarks

#### Compare Standard vs Robust Decoding

**Standard decoding** (`SLICES2structure`): Basic workflow with single attempt

**Robust decoding** (`robust_SLICES2structure`): Multiple fallback strategies:
1. Standard decoding
2. Alternative encoding strategies
3. Fallback bond parameters (if XTB fails)
4. Progressive relaxation (tight → loose convergence)
5. Graceful degradation (returns ZL*-optimized structure if MLIP fails)

**Usage:**
```bash
conda activate slices
python scripts/tests/run_comparison_test.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 500
```

**Output:**
- `decoding_comparison_report_*.txt` and `.json` files
- Success rates, error breakdown, performance metrics
- Generated in current working directory with timestamp

**Test Robust Decoding Only:**
```bash
python scripts/tests/test_improved_decoding.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 1000 \
    --use-robust
```

#### Encode/Decode Benchmark Workflow

Encode structures to SLICES, decode back, and calculate formation energies.

```bash
# Quick test (5 samples)
python scripts/benchmarks/encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded.csv \
    --threads 8 \
    --max_samples 5

# Full dataset
python scripts/benchmarks/encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded.csv \
    --threads 8
```

**Note:** Script uses ORBv3 by default. Modify script or use SLICES API for other models.

**Output CSV Format:**
- `slices` - SLICES string representation
- `energy_per_atom_<model>` - Energy per atom (eV/atom)
- `formation_energy_per_atom_<model>` - Formation energy per atom (eV/atom)
- `space_group` - Space group number
- `formula` - Chemical formula
- `poscar` - Structure in POSCAR format

---

## Documentation

### API Reference

Complete API documentation in `docs/api/`:

- [`API_CORE.md`](docs/api/API_CORE.md) - Core SLICES class and methods
- [`API_MLIP.md`](docs/api/API_MLIP.md) - MLIP relaxer interfaces
- [`API_GRAPH.md`](docs/api/API_GRAPH.md) - Graph theory operations
- [`API_UTILITIES.md`](docs/api/API_UTILITIES.md) - Utility functions
- [`API_DECODING_STRATEGIES.md`](docs/api/API_DECODING_STRATEGIES.md) - Decoding strategies
- [`API_CONFIG.md`](docs/api/API_CONFIG.md) - Configuration constants

### Technical Documentation

- [`TECHNICAL.md`](TECHNICAL.md) - System architecture and algorithm details
- [`CHANGELOG.md`](CHANGELOG.md) - Version history

### Codebase Structure

```
SLICES/
├── src/slices/          # Core package
│   ├── core.py         # Main SLICES class
│   ├── mlip_relaxer.py # MLIP model adapters
│   ├── tobascco_net.py # Graph theory operations
│   └── ...
├── tests/              # Test suite
├── examples/           # Example scripts
├── scripts/            # Utility scripts
│   ├── tests/         # Test scripts
│   ├── benchmarks/    # Benchmark scripts
│   └── utilities/     # Utility scripts
└── docs/               # Documentation
    ├── api/           # API reference
    └── benchmarks/    # Benchmark data
```

---

## Troubleshooting

### Import Errors

- Ensure conda environment is activated: `conda activate slices`
- Reinstall: `pip install -e .`

### MLIP Model Errors

- Install required package: `pip install chgnet` (or other model)
- Check model is supported: see [Configuration](#configuration) section

### XTB Errors

**Binary not found:**
- Ensure XTB binary is in `src/slices/` directory
- Binary name must match your OS (see [Installation](#step-2-xtb-binary))
- Check file permissions (Linux/macOS): `chmod +x src/slices/xtb_noring_nooutput_nostdout_noCN`

**macOS-specific:**
- If you see "Linux-only XTB binary on macOS" warning:
  - Build from source: https://github.com/xiaohang007/xtb
  - Or install system XTB: `brew install xtb` (may have limited functionality)
- ARM64 (Apple Silicon) users must build from source

**Windows-specific:**
- Binary must be `.exe` extension
- If using WSL2, use Linux binary instead
- Ensure binary is in PATH or in `src/slices/` directory

**Binary compatibility:**
- Custom XTB binary has specific flags: `noring`, `nooutput`, `nostdout`, `noCN`
- System XTB may not have these flags, causing decoding failures
- Always use custom binary from https://github.com/xiaohang007/xtb when possible

### Decoding Failures

- Some structures may fail due to incompatible graph topology
- Try different MLIP models
- Check structure is 3D (not 2D or 1D)

---

## Adding New MLIP Models

1. Create a new class in `src/slices/mlip_relaxer.py`:

```python
class YourModelRelaxer(MLIPRelaxer):
    def __init__(self, **kwargs):
        # Initialize your model
        
    def relax(self, structure, fmax=0.2, steps=100):
        # Implement relaxation
        return {'final_structure': ..., 'trajectory': ...}
```

2. Register in `get_relaxer()` function
3. Add tests in `tests/unit/test_mlip_relaxer.py`

---

## License

LGPL-2.1 License - see [LICENSE](LICENSE) file for details
