# SLICES

**Simplified Line-Input Crystal-Encoding System**

SLICES is an invertible crystal structure representation system that converts 3D crystal structures into compact text strings and reconstructs them back to atomic coordinates. It uses graph theory to encode crystal topology, machine learning interatomic potentials (MLIPs) for structure relaxation, and XTB quantum chemistry for bond parameter prediction.

**What it does:**
- **Input**: Crystal structure (CIF, POSCAR, or pymatgen Structure object)
- **Process**: Encodes structure → SLICES string → Decodes back to structure
- **Output**: SLICES string (encoding) or relaxed Structure with energy (decoding)

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

### System Requirements

- **Operating System**: Linux (x86-64), macOS (Intel/ARM), or Windows
- **Python**: 3.9 or higher
- **Package Manager**: Conda (recommended) or pip
- **Memory**: Minimum 4GB RAM (8GB+ recommended for MLIP models)
- **Disk Space**: ~2GB for dependencies and models

### Prerequisites

- Python 3.9 or higher
- Conda (recommended) or pip
- Git
- CMake (for building XTB from source, if needed)

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

SLICES requires a custom XTB binary for decoding. **The codebase automatically detects and uses the correct binary** for your operating system.

#### Automatic Detection

The system checks in this order:
1. **Pre-compiled binary** in `src/slices/` directory (platform-specific, if available)
2. **System XTB** from PATH (fallback with warning)

Detection happens automatically on import—no configuration needed.

#### Pre-compiled Binaries (Recommended)

Pre-compiled XTB binaries for different operating systems are included in the repository and organized in platform-specific directories. The system automatically detects and uses the appropriate binary based on your operating system.

**Binary Organization:**
Binaries are stored in platform-specific subdirectories:
- **Linux**: `src/slices/bin/linux/xtb_noring_nooutput_nostdout_noCN`
- **macOS**: `src/slices/bin/macos/xtb_noring_nooutput_nostdout_noCN`
- **Windows**: `src/slices/bin/windows/xtb_noring_nooutput_nostdout_noCN.exe`

**Binary Detection Logic:**
The system checks in this order:
1. **Platform-specific directory**: `src/slices/bin/{platform}/xtb_noring_nooutput_nostdout_noCN[.exe]`
   - Detects your OS using `platform.system()` (Linux, Darwin for macOS, or Windows)
   - Looks for the binary in the appropriate platform subdirectory
2. **Legacy location** (backward compatibility): `src/slices/xtb_noring_nooutput_nostdout_noCN[.exe]`
   - Falls back to old location if platform-specific binary not found
3. **System XTB** (fallback): Uses system XTB from PATH if no custom binary found

**macOS Compatibility Check:**
On macOS, the system verifies the binary is actually a macOS binary (not a Linux binary) using the `file` command. If a Linux binary is detected, it warns and attempts to use system XTB as fallback.

**Current Status:**
- ✅ Linux binary: Included in `src/slices/bin/linux/`
- ✅ macOS binary: Included in `src/slices/bin/macos/`
- ⚠️ Windows binary: Placeholder in `src/slices/bin/windows/` (replace with actual binary from https://github.com/xiaohang007/xtb)

If the pre-compiled binary for your OS is not available, you can build from source (see below).

#### Building from Source (If Pre-compiled Binary Unavailable)

<details>
<summary><b>Linux (x86-64)</b> - Click to expand</summary>

Pre-compiled binary is included in `src/slices/bin/linux/`. If you need to rebuild:

```bash
git clone https://github.com/xiaohang007/xtb.git
cd xtb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
cp xtb_noring_nooutput_nostdout_noCN ../../SLICES/src/slices/bin/linux/
```

</details>

<details>
<summary><b>macOS</b> - Click to expand</summary>

**Option 1: Use Pre-compiled Binary (If Available)**
- Pre-compiled binary is included in `src/slices/bin/macos/`
- Automatically detected and used

**Option 2: Build from Source (If binary unavailable or for different architecture)**

```bash
git clone https://github.com/xiaohang007/xtb.git
cd xtb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(sysctl -n hw.ncpu)
cp xtb_noring_nooutput_nostdout_noCN ../../SLICES/src/slices/bin/macos/
```

**Option 3: Use system XTB (Fallback)**
- Install: `brew install xtb`
- Note: May lack required flags, causing decoding failures

</details>

<details>
<summary><b>Windows</b> - Click to expand</summary>

**Option 1: Use Pre-compiled Binary (If Available)**
- Currently, only a placeholder exists in `src/slices/bin/windows/`
- Replace the placeholder with actual Windows binary from https://github.com/xiaohang007/xtb
- Once replaced, it will be automatically detected and used

**Option 2: Build Windows binary (If binary unavailable)**

```bash
git clone https://github.com/xiaohang007/xtb.git
cd xtb
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -G "Visual Studio 17 2022"
cmake --build . --config Release
copy Release\xtb_noring_nooutput_nostdout_noCN.exe ..\..\SLICES\src\slices\bin\windows\
```

**Option 3: Use WSL2**
- Install WSL2 and use Linux binary
- Follow Linux installation instructions within WSL2

**Option 4: Use system XTB (Fallback)**
- System XTB from PATH (may lack required flags)

</details>

### Step 3: Verification

```bash
python tools/validate_installation.py
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

<details>
<summary>Click to see example output</summary>

```
XTB path: /Users/zielle/Dissertation/SLICES/src/slices/bin/macos/xtb_noring_nooutput_nostdout_noCN
```

</details>

---

## Quick Start

### Basic Example

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load a crystal structure (input: CIF file, POSCAR, or Structure object)
structure = Structure.from_file('tutorial/NdSiRu.cif')

# Initialize SLICES (M3GNet is default MLIP model)
backend = SLICES(relax_model='m3gnet')

# Encode structure to SLICES string (output: text string)
slices_string = backend.structure2SLICES(structure)
print(f"SLICES: {slices_string}")

# Decode SLICES string back to structure (output: Structure + energy)
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
print(f"Formula: {reconstructed.formula}")
```

<details>
<summary>Click to see example output</summary>

```
SLICES:  o v b OOO g DDO c DDO h DDO + YBO Nd Nd Si Si Ru Ru 0 3 -oo 0 3 -+o 0 3 ooo 0 3 o+o 0 5 -oo 0 5 ooo 0 4 ooo 0 4 o+o 0 2 oo- 0 2 ooo 1 2 o-o 1 2 ooo 1 2 +-o 1 2 +oo 1 4 oo+ 1 4 +o+ 1 5 o-+ 1 5 oo+ 1 3 ooo 1 3 oo+ 2 5 -o+ 2 5 oo+ 2 4 oo+ 2 4 o++ 3 4 ooo 3 4 +oo 3 5 o-o 3 5 ooo 4 5 --o 4 5 -oo 4 5 o-o 4 5 ooo 

Energy: -7.2728 eV/atom
Formula: Nd2 Si2 Ru2
```

</details>

### What Happens

1. **Encoding**: Structure → Graph → Cycles → SLICES String
   - **Input**: Crystal structure
   - **Output**: SLICES text string (compact representation)

2. **Decoding**: SLICES String → Graph → Coordinates → MLIP Relaxation → Structure
   - **Input**: SLICES text string
   - **Output**: Relaxed crystal structure + energy per atom

### Augment and Canonicalize SLICES

The same crystal structure can be represented by multiple SLICES strings due to different atom orderings. Augmentation generates multiple representations, and canonicalization reduces them to a unique form.

**Why This Matters:**
- **Data Augmentation**: Generate multiple training examples from one structure by permuting atom order
- **Uniqueness**: Canonical form ensures identical structures always produce the same SLICES string, regardless of atom ordering
- **Structure Comparison**: Determine if two structures are identical by comparing their canonical SLICES strings (faster than geometric comparison)

**Example:**
```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load crystal structure
structure = Structure.from_file('tutorial/Sr3Ru2O7.cif')
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

<details>
<summary>Click to see example output</summary>

```
Generated 50 SLICES, 50 unique
Canonical forms: 1 unique
```

</details>

**How It Works:**
- **Augmentation**: Randomly permutes atom order while preserving structure topology
- **Canonicalization**: Sorts atoms by atomic number, edges by indices, and edge labels consistently

---

## How It Works

### Process Workflow

**Encoding (Structure → SLICES String):**
- **Input**: Crystal structure (CIF file, POSCAR, or pymatgen Structure object)
- **Process**: 
  1. Convert structure to labeled quotient graph (atoms = nodes, bonds = edges, labels = periodic boundaries)
  2. Find independent cycles in the graph
  3. Compute lattice vectors from cycle information
  4. Generate compact text string representation
- **Output**: SLICES string (text format, typically 100-500 characters)

**Decoding (SLICES String → Structure):**
- **Input**: SLICES string
- **Process**:
  1. Parse string to extract atom types, bonds, and periodic boundary conditions
  2. Reconstruct labeled quotient graph
  3. Calculate bond lengths and angles using XTB quantum chemistry
  4. Generate initial atomic coordinates using barycentric embedding
  5. Optimize coordinates using ZL* algorithm to match XTB predictions
  6. Relax structure using MLIP model (M3GNet, CHGNet, etc.)
- **Output**: Relaxed crystal structure (pymatgen Structure) and energy per atom (eV/atom)

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

<details>
<summary>Click to see example output</summary>

All models initialize successfully when installed:

```
✓ M3GNET: Initialized successfully
✓ CHGNET: Initialized successfully
✓ MATTERSIM: Initialized successfully
✓ ORBV3: Initialized successfully
```

</details>

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

### Prerequisites

```bash
pip install pytest pytest-cov
```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with coverage report
pytest tests/ --cov=src/slices --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

<details>
<summary>Click to see example output</summary>

```
============================= test session starts ==============================
collected 199 items

tests/unit/test_core_encoding.py::TestStructure2SLICES::test_encode_basic PASSED
tests/unit/test_mlip_relaxer.py::TestMLIPRelaxer::test_get_relaxer_factory PASSED
tests/integration/test_round_trip.py::TestRoundTrip::test_round_trip_basic PASSED
...

============================= 88 passed, 11 failed, 4 errors in 231.71s ==============================
```

</details>

### Test Specific Components

```bash
# Encoding only
pytest tests/unit/test_encoding_only.py

# Decoding only
pytest tests/unit/test_core_decoding.py

# MLIP integration
pytest tests/integration/test_mlip_integration.py

# Round-trip (encode then decode)
pytest tests/integration/test_round_trip.py

# Batch processing
pytest tests/integration/test_round_trip_batch.py

# Backward compatibility
pytest tests/regression/test_backward_compatibility.py
```

<details>
<summary>Click to see example output</summary>

```
tests/unit/test_mlip_relaxer.py::TestMLIPRelaxer::test_get_relaxer_factory PASSED
tests/integration/test_round_trip.py::TestRoundTrip::test_round_trip_basic PASSED
tests/integration/test_mlip_integration.py::TestMLIPModelInitialization::test_get_relaxer_factory PASSED
...
```

</details>

### Validate Installation

   ```bash
python tools/validate_installation.py
```

**Expected Output:**
```
✓ All required packages installed
✓ XTB binary found and compatible
✓ MLIP models available
✓ Installation validation passed!
```

### Test Benchmarks

```bash
# Compare standard vs robust decoding (20 samples, all MLIP models)
conda activate slices
python tools/benchmarks/test_all_mlips.py
```

---

## Benchmarks

### Benchmark Dataset

Location: `benchmark/results/data/train_encoded_decoded_orbv3.csv`

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
python tools/tests/run_comparison_test.py \
    --dataset benchmark/results/data/train_encoded_decoded_orbv3.csv \
    --samples 500
```

**Output:**
- `decoding_comparison_report_*.txt` and `.json` files
- Success rates, error breakdown, performance metrics
- Generated in current working directory with timestamp

**Test Robust Decoding Only:**
```bash
python tools/tests/test_improved_decoding.py \
    --dataset benchmark/results/data/train_encoded_decoded_orbv3.csv \
    --samples 1000 \
    --use-robust
```

#### MLIP Model Comparison Benchmark

Compare all available MLIP models with standard and robust decoding on the same set of structures.

```bash
# Run benchmark (20 samples, all MLIP models)
conda activate slices
python tools/benchmarks/test_all_mlips.py
```

**What it tests:**
- 20 random structures (same samples across all models)
- 4 MLIP models: M3GNet, CHGNet, MatterSim, ORBv3
- 2 SLICES variants: Default and Canonical
- 2 decoding methods: Standard and Robust

**Output:**
- Results saved to `benchmark/mlip_benchmark_YYYYMMDD_HHMMSS.json`
- Terminal output with success rates, timing, and error breakdowns
- Comparison between standard and robust decoding performance

**Benchmark Results:**

**Large-Scale Comparison (24,502 structures):**

Results from testing 24,502 structures.  
**Input:** `benchmark/results/data/train_encoded_decoded_orbv3.csv`  
**Output:** `benchmark/results/reports/decoding_comparison_report_20251204_184955.json`

| Decoding Method | Success Rate | Failed | Avg Time (s) |
|----------------|--------------|--------|--------------|
| Standard (`SLICES2structure`) | 98.82% (24,214/24,502) | 288 (1.18%) | 3.67 |
| Robust (`robust_SLICES2structure`) | 99.49% (24,377/24,502) | 125 (0.51%) | 3.66 |

**Improvement:** Robust decoding achieves +0.67% success rate improvement, successfully decoding 163 additional structures that standard decoding failed on.

**MLIP Model Comparison (20 samples):**

Results from testing 20 random structures (same samples across all models).  
**Input:** `data/mp20/train.csv`  
**Output:** `benchmark/results/reports/mlip_benchmark_YYYYMMDD_HHMMSS.json`

| Model | Default SLICES (Standard) | Default SLICES (Robust) | Canonical SLICES (Standard) | Canonical SLICES (Robust) | Overall (Standard) | Overall (Robust) |
|-------|---------------------------|-------------------------|-----------------------------|---------------------------|-------------------|------------------|
| M3GNet | 19/20 (95%) | 19/20 (95%) | 17/20 (85%) | 18/20 (90%) | 36/40 (90%) | 37/40 (92%) |
| CHGNet | 19/20 (95%) | 19/20 (95%) | 18/20 (90%) | 18/20 (90%) | 37/40 (92%) | 37/40 (92%) |
| MatterSim | 18/20 (90%) | 19/20 (95%) | 19/20 (95%) | 19/20 (95%) | 37/40 (92%) | 38/40 (95%) |
| ORBv3 | 19/20 (95%) | 19/20 (95%) | 18/20 (90%) | 19/20 (95%) | 37/40 (92%) | 38/40 (95%) |

**Average Processing Times (Default SLICES):**
- M3GNet: Standard 3.27s, Robust 2.82s
- CHGNet: Standard 6.20s, Robust 4.30s
- MatterSim: Standard 2.17s, Robust 2.79s
- ORBv3: Standard 4.77s, Robust 4.20s

**Key Findings:**
- Robust decoding shows improvement for M3GNet (+2%), MatterSim (+3%), and ORBv3 (+3%)
- MatterSim and ORBv3 achieve highest overall success rate (95%) with robust decoding
- One structure (Th2 Ni4 P4) failed across all models due to XTB computation issues

*Results generated on 2025-12-13. Input: `data/mp20/train.csv`. Output: `benchmark/results/reports/mlip_benchmark_20251213_035724.json`. To regenerate: `conda activate slices && python tools/benchmarks/test_all_mlips.py`*

#### Encode/Decode Benchmark Workflow

Generic benchmark script supports any MLIP model with all combinations of SLICES types and decoding strategies.

**Run Comprehensive Benchmark (All Combinations):**

```bash
# Generic benchmark script works with any MLIP model
conda activate slices
python tools/benchmarks/run_encode_decode_benchmark.py --model m3gnet

# Other models
python tools/benchmarks/run_encode_decode_benchmark.py --model chgnet
python tools/benchmarks/run_encode_decode_benchmark.py --model mattersim
python tools/benchmarks/run_encode_decode_benchmark.py --model orbv3
```

**What it tests:**
- Combines `data/mp20/train.csv`, `val.csv`, `test.csv` into single dataset
- Tests 4 combinations:
  - Default SLICES + Standard decoding
  - Default SLICES + Robust decoding
  - Canonical SLICES + Standard decoding
  - Canonical SLICES + Robust decoding
- Generates formation energy comparison plot

**Monitor Progress:**
The script prints progress every 100 structures. For background execution:
```bash
nohup python tools/benchmarks/run_encode_decode_benchmark.py --model m3gnet > benchmark.log 2>&1 &
tail -f benchmark.log  # Monitor progress
```

<details>
<summary>Click to see example progress output</summary>

```
======================================================================
Encode/Decode Benchmark - M3GNET
======================================================================

Step 1: Combining datasets...
Combined dataset: 45229 structures

Step 2: Running all combinations...

======================================================================
Running: DEFAULT_STANDARD with M3GNET
======================================================================
Processing 45229 structures...
Processed 100/45229 structures (successful: 90, failed: 10)
Processed 200/45229 structures (successful: 180, failed: 20)
...
```

</details>

**Single Combination Benchmark:**

```bash
# Quick test (5 samples, default SLICES, standard decoding)
python tools/benchmarks/encode_decode_benchmark.py \
    --train_csv data/mp20/train.csv \
    --val_csv data/mp20/val.csv \
    --test_csv data/mp20/test.csv \
    --output_csv train_encoded_decoded.csv \
    --model m3gnet \
    --max_samples 5

# Full dataset with specific combination
python tools/benchmarks/encode_decode_benchmark.py \
    --train_csv data/mp20/train.csv \
    --val_csv data/mp20/val.csv \
    --test_csv data/mp20/test.csv \
    --output_csv train_encoded_decoded.csv \
    --model m3gnet \
    --use_canonical  # Use canonical SLICES
    --use_robust     # Use robust decoding
```

**Output CSV Format (Essential Columns Only):**
- `slices` - SLICES string representation
- `energy_per_atom_<model>` - Energy per atom (eV/atom)
- `formation_energy_per_atom_<model>` - Formation energy per atom (eV/atom)
- `formation_energy_per_atom` - Original formation energy (for comparison)
- `space_group` - Space group number
- `formula` - Chemical formula
- `slices_type` - "default" or "canonical"
- `decoding_type` - "standard" or "robust"

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
├── tutorial/           # Tutorial and example scripts
├── tools/              # Utility scripts
│   ├── benchmarks/     # Benchmark scripts
│   ├── tests/          # Test scripts
│   └── validate_installation.py # Installation validation
├── configs/            # Configuration files
├── checkpoints/        # Saved model checkpoints
├── logs/               # Log files
└── docs/               # Documentation
    └── api/            # API reference
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
- Ensure XTB binary is in the platform-specific directory: `src/slices/bin/{platform}/`
- Binary name must match your OS (see [Installation](#step-2-xtb-binary))
- Check file permissions (Linux/macOS): `chmod +x src/slices/bin/{platform}/xtb_noring_nooutput_nostdout_noCN`
- The system also checks the legacy location `src/slices/` for backward compatibility

**macOS-specific:**
- If you see "Linux-only XTB binary on macOS" warning:
  - Build from source: https://github.com/xiaohang007/xtb
  - Or install system XTB: `brew install xtb` (may have limited functionality)
- ARM64 (Apple Silicon) users must build from source

**Windows-specific:**
- Binary must be `.exe` extension
- If using WSL2, use Linux binary instead (WSL2 will use Linux binary from `src/slices/bin/linux/`)
- Ensure binary is in `src/slices/bin/windows/` directory

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

<details>
<summary>Click to see example implementation</summary>

After implementing your relaxer class, register it in `get_relaxer()`:

```python
def get_relaxer(model_name: str = "m3gnet", **kwargs):
    if model_name.lower() == "yourmodel":
        return YourModelRelaxer(**kwargs)
    # ... existing models ...
```

Then add tests:

```python
def test_your_model_relaxer():
    relaxer = get_relaxer("yourmodel")
    assert isinstance(relaxer, YourModelRelaxer)
```

</details>

---

## License

LGPL-2.1 License - see [LICENSE](LICENSE) file for details
