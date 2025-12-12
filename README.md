# SLICES: Simplified Line-Input Crystal-Encoding System

**An invertible crystal structure representation system for materials science**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Quick Start

### Installation

**Step 1: Install Python and dependencies**

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

**Step 2: Install XTB Binary (Required for Decoding)**

SLICES uses a custom XTB binary for bond parameter calculations during decoding. **The codebase automatically detects which XTB binary to use** based on your operating system and available binaries.

**Automatic Detection Logic:**

1. **First Priority**: Custom binary in `src/slices/` directory
   - Linux: `xtb_noring_nooutput_nostdout_noCN`
   - Windows: `xtb_noring_nooutput_nostdout_noCN.exe`
   - macOS: `xtb_noring_nooutput_nostdout_noCN` (native macOS binary)

2. **Second Priority**: System XTB from PATH (fallback)
   - Automatically detected if custom binary not found
   - Warning will be displayed: "Using system XTB instead of custom binary"

3. **macOS Special Handling**: 
   - If a Linux binary is detected on macOS, the system will:
     - Try to use system XTB if available
     - Otherwise warn about potential compatibility issues

The detection happens automatically when you import SLICES. No manual configuration needed!

#### Linux (x86-64)

The repository includes a pre-built Linux binary:
- Location: `src/slices/xtb_noring_nooutput_nostdout_noCN`
- Automatically detected and used
- No additional steps required

#### macOS

**Option 1: Build from source (Recommended)**
```bash
# Clone the custom XTB repository
git clone https://github.com/xiaohang007/xtb.git
cd xtb

# Build for macOS
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Copy binary to SLICES directory
cp xtb_noring_nooutput_nostdout_noCN ../../SLICES/src/slices/
```

**Option 2: Use system XTB (Fallback)**
- If the custom binary is not found, SLICES will attempt to use system XTB
- Install via Homebrew: `brew install xtb`
- Note: System XTB may not have the required flags (noring, nooutput, nostdout, noCN), which may cause decoding failures

**Option 3: Linux binary on macOS (Not Recommended)**
- SLICES will detect a Linux binary on macOS and warn you
- Decoding may fail due to binary incompatibility
- Build from source for best compatibility

#### Windows

**Option 1: Build Windows binary (Recommended)**
```bash
# Clone the custom XTB repository
git clone https://github.com/xiaohang007/xtb.git
cd xtb

# Build for Windows (requires Visual Studio or MinGW)
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -G "Visual Studio 17 2022"
cmake --build . --config Release

# Copy binary to SLICES directory
copy Release\xtb_noring_nooutput_nostdout_noCN.exe ..\..\SLICES\src\slices\
```

**Option 2: Use WSL2 (Alternative)**
- Install WSL2 and use Linux binary
- Follow Linux installation instructions within WSL2

**Option 3: Use system XTB (Fallback)**
- If the custom binary is not found, SLICES will attempt to use system XTB from PATH
- Note: System XTB may not have the required flags, which may cause decoding failures

#### Verification

After installation, verify XTB binary is automatically detected:

```bash
python scripts/utilities/validate_installation.py
```

The validation script will check:
- XTB binary presence and compatibility (automatic detection)
- All required Python packages
- MLIP model availability

You can also check which XTB is being used:

```python
from slices.core import SLICES
import os
print("XTB path:", os.environ.get("XTB_MOD_PATH"))
```

**Step 3: Test installation**

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

### Basic Usage

```python
from slices.core import SLICES
from pymatgen.core.structure import Structure

# Load a crystal structure
structure = Structure.from_file('examples/NdSiRu.cif')

# Initialize SLICES
backend = SLICES(relax_model='chgnet')

# Encode structure to SLICES string
slices_string = backend.structure2SLICES(structure)
print(f"SLICES: {slices_string}")

# Decode SLICES string back to structure
reconstructed, energy = backend.SLICES2structure(slices_string)
print(f"Energy: {energy:.4f} eV/atom")
```

## How It Works

### Encoding Process

1. **Build Graph**: Convert crystal structure to a graph where atoms are nodes and bonds are edges
2. **Find Cycles**: Identify independent cycles in the graph (loops)
3. **Compute Lattice**: Calculate lattice vectors from cycle information
4. **Generate String**: Convert graph to compact text format

### Decoding Process

1. **Parse String**: Extract atom types, bonds, and periodic boundary conditions
2. **Rebuild Graph**: Reconstruct the graph structure
3. **Calculate Parameters**: Use XTB to predict bond lengths and angles
4. **Generate Coordinates**: Create initial atomic positions
5. **Optimize Structure**: Use machine learning models to refine the structure

### Theory

**Graph Representation**: A crystal structure is represented as a labeled quotient graph:
- **Nodes** = atoms
- **Edges** = bonds between atoms
- **Edge labels** = periodic boundary conditions (how atoms connect across unit cells)

**Cycle Basis**: Independent cycles in the graph determine the lattice vectors. We need at least 3 independent cycles for a 3D structure.

**Lattice Basis**: Computed from cycle vectors using linear algebra (nullspace computation).

**Barycentric Embedding**: Initial atomic coordinates are generated from the graph structure.

**ZL* Optimization**: Coordinates are optimized to match predicted bond lengths and angles.

**MLIP Relaxation**: Final structure is refined using machine learning interatomic potentials.

## Configuration

### MLIP Model Selection

```python
# Use M3GNet (default)
backend = SLICES(relax_model='m3gnet', fmax=0.2, steps=100)

# Use CHGNet
backend = SLICES(relax_model='chgnet', fmax=0.2, steps=100)

# Use MatterSim
backend = SLICES(relax_model='mattersim', fmax=0.2, steps=100)

# Use ORBv3
backend = SLICES(relax_model='orbv3', fmax=0.2, steps=100)
```

**Available Models:**
- `m3gnet`: Default model (Materials Project)
- `chgnet`: Charge-informed GNN
- `mattersim`: Microsoft's deep learning potential
- `orbv3`: Orbital Materials potential

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `relax_model` | `"m3gnet"` | MLIP model to use |
| `fmax` | `0.2` | Force convergence (eV/Å). Lower = stricter |
| `steps` | `100` | Maximum optimization steps |
| `optimizer` | `"BFGS"` | Optimizer algorithm |
| `graph_method` | `"econnn"` | Graph construction method |

## Testing

### Run All Tests

```bash
# Install pytest if needed
pip install pytest pytest-cov

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/slices --cov-report=html
```

### Test Specific Components

```bash
# Test encoding/decoding
pytest tests/unit/test_core_encoding.py
pytest tests/unit/test_core_decoding.py

# Test MLIP integration
pytest tests/integration/test_mlip_integration.py

# Test round-trip (encode then decode)
pytest tests/integration/test_round_trip.py
```

### Validate Installation

   ```bash
python scripts/utilities/validate_installation.py
```

## Code Structure

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
└── docs/               # Documentation
```

## How to Apply Changes

### Making Code Changes

1. **Create a branch**
```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Edit code files
   - Add tests for new features
   - Update documentation if needed

3. **Test your changes**
```bash
   pytest tests/
   python scripts/utilities/validate_installation.py
   ```

4. **Commit and push**
```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

### Adding New MLIP Models

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

## Troubleshooting

### Common Issues

**Import errors**
- Make sure conda environment is activated: `conda activate slices`
- Reinstall: `pip install -e .`

**MLIP model errors**
- Install required package: `pip install chgnet` (or other model)
- Check model is supported: see Configuration section

**XTB errors**

*Binary not found:*
- Ensure XTB binary is in `src/slices/` directory
- Binary name must match your OS:
  - Linux/macOS: `xtb_noring_nooutput_nostdout_noCN`
  - Windows: `xtb_noring_nooutput_nostdout_noCN.exe`
- Check file permissions (Linux/macOS): `chmod +x src/slices/xtb_noring_nooutput_nostdout_noCN`

*macOS-specific issues:*
- If you see "Linux-only XTB binary on macOS" warning:
  - Build from source: https://github.com/xiaohang007/xtb
  - Or install system XTB: `brew install xtb` (may have limited functionality)
- ARM64 (Apple Silicon) users must build from source

*Windows-specific issues:*
- Binary must be `.exe` extension
- If using WSL2, use Linux binary instead
- Ensure binary is in PATH or in `src/slices/` directory

*Binary compatibility:*
- The custom XTB binary has specific flags: `noring`, `nooutput`, `nostdout`, `noCN`
- System XTB may not have these flags, causing decoding failures
- Always use the custom binary from https://github.com/xiaohang007/xtb when possible

**Decoding failures**
- Some structures may fail due to incompatible graph topology
- Try different MLIP models
- Check structure is 3D (not 2D or 1D)

## Examples

See `examples/` directory for:
- Basic encoding/decoding
- Advanced usage
- Batch processing

## Benchmarks

### Benchmark Dataset

The benchmark dataset is located at `docs/benchmarks/train_encoded_decoded_orbv3.csv`:
- Contains 1.3M+ encoded/decoded structures
- Used for testing and validation
- Format: CSV with columns for SLICES strings, structures, energies, etc.

### Running Benchmarks

**Compare Standard vs Robust Decoding:**
```bash
conda activate slices
python scripts/tests/run_comparison_test.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 500
```

**Test Robust Decoding:**
```bash
conda activate slices
python scripts/tests/test_improved_decoding.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 1000 \
    --use-robust
```

**Note**: Robust decoding uses additional fallback strategies. See `TECHNICAL.md` for details on the enhancements.

**Output Files:**
- `decoding_comparison_report_*.txt/json` - Test comparison results
- `baseline_test_results.txt` - Baseline performance metrics
- `formation_energy_comparison.png` - Visualization of results

### ORBv3 Benchmark Workflow

**Encode/Decode Training Dataset:**
  ```bash
# Quick test (5 samples)
python scripts/benchmarks/encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded_orbv3.csv \
    --threads 8 \
    --max_samples 5

# Full dataset
python scripts/benchmarks/encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded_orbv3.csv \
    --threads 8
```

**Benchmark MatterGPT Generated Structures:**
```bash
python scripts/benchmarks/encode_decode_orbv3_benchmark.py \
    --skip_encode_decode \
    --benchmark_csv path/to/mattergpt_generated_slices.csv
```

**Output:** The script generates CSV files with:
- SLICES strings
- ORBv3 calculated energy per atom (eV/atom)
- Formation energy per atom (eV/atom)
- Space group number
- Chemical formula
- POSCAR format structure

**Notes:**
- Processing 1M+ structures can take several hours
- Adjust `--threads` based on available memory
- Some structures may fail due to incompatible graph topology (normal)

## Codebase Structure

### Directory Structure

```
SLICES/
├── src/                    # Source code
│   └── slices/             # Main SLICES package
│       ├── core.py        # Core SLICES class
│       ├── mlip_relaxer.py # MLIP model adapters
│       ├── tobascco_net.py # Graph theory operations
│       ├── decoding_strategies.py # Decoding strategies
│       ├── utils.py       # Utility functions
│       ├── utils_wyckoff.py # Space group utilities
│       └── config.py      # Configuration constants
│
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── regression/        # Regression tests
│   └── fixtures/          # Test fixtures
│
├── scripts/                # Utility scripts
│   ├── tests/             # Test scripts
│   ├── benchmarks/        # Benchmark scripts
│   └── utilities/         # Utility scripts
│
├── docs/                   # Documentation
│   ├── api/              # API reference documentation
│   └── benchmarks/       # Benchmark data and results
│
├── examples/               # Example scripts
│   ├── basic/            # Basic usage examples
│   └── advanced/         # Advanced usage examples
│
├── config/                 # Configuration files
│   ├── APIKEY.ini        # API keys
│   ├── slurm.conf        # SLURM configuration
│   └── *.sh              # Shell scripts
│
├── docker/                 # Docker configuration
│   ├── Dockerfile        # Docker image definition
│   └── docker-compose.yml # Docker Compose config
│
├── data/                   # Datasets
│   ├── mp20/             # MP-20 dataset
│   └── mp20_nonmetal/    # MP-20 nonmetal subset
│
├── benchmark/              # Benchmark workflows (research)
├── HTS/                    # High-throughput screening (research)
├── MatterGPT/              # MatterGPT integration (research)
├── MatterGPT_no_flash/     # MatterGPT no-flash variant (research)
│
├── README.md               # Main documentation
├── TECHNICAL.md            # Technical documentation
├── CHANGELOG.md            # Version history
├── pyproject.toml         # Python package configuration
└── pytest.ini             # Pytest configuration
```

### Key Directories

**`src/slices/`** - Main source code package containing all SLICES functionality.

**`tests/`** - Comprehensive test suite organized by test type:
- **unit/**: Tests for individual functions and classes
- **integration/**: Tests for component interactions
- **regression/**: Tests for known structures and backward compatibility

**`scripts/`** - Utility scripts organized by purpose:
- **tests/**: Test execution and validation scripts
- **benchmarks/**: Performance benchmarking scripts
- **utilities/**: Setup and maintenance scripts

**`docs/`** - Documentation organized by type:
- **api/**: Complete API reference for all modules
- **benchmarks/**: Benchmark results and comparison data

**`examples/`** - Example scripts demonstrating SLICES usage:
- **basic/**: Simple encoding/decoding examples
- **advanced/**: Advanced features and techniques

**`config/`** - Configuration files for API keys, SLURM job scheduling, and shell scripts.

**`docker/`** - Docker containerization files including Dockerfile and Docker Compose configuration.

### Research Directories

The following directories contain research-specific code and may not be part of the core SLICES functionality:
- `benchmark/`: Benchmark workflows and experiments
- `HTS/`: High-throughput screening workflows
- `MatterGPT/`: MatterGPT model integration
- `MatterGPT_no_flash/`: MatterGPT variant without flash attention

### File Naming Conventions

- **Python modules**: `snake_case.py`
- **Test files**: `test_*.py`
- **Documentation**: `*.md` (Markdown)
- **Configuration**: `*.ini`, `*.conf`, `*.toml`
- **Scripts**: `*.py`, `*.sh`

### Import Paths

All SLICES functionality is imported from `slices` package:

```python
from slices.core import SLICES
from slices.mlip_relaxer import get_relaxer
from slices.decoding_strategies import CycleBasisOptimizer
```

## Documentation

- **Code API Documentation**: See `docs/` directory for complete API reference:
  - `docs/api/API_CORE.md` - Core SLICES class and methods
  - `docs/api/API_MLIP.md` - MLIP relaxer interfaces
  - `docs/api/API_GRAPH.md` - Graph theory operations
  - `docs/api/API_UTILITIES.md` - Utility functions
  - `docs/api/API_DECODING_STRATEGIES.md` - Decoding strategies
  - `docs/api/API_CONFIG.md` - Configuration constants
- **Technical Documentation**: See `TECHNICAL.md` for system architecture and algorithm details
- **Changelog**: See `CHANGELOG.md` for version history

## Citation

If you use SLICES in your research, please cite:

```bibtex
@article{xiao2023slices,
  title={},
  author={},
  journal={},
  year={}
}
```

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: [GitHub Issues](https://github.com/xiaohang007/SLICES/issues)
- **Documentation**: [Online Docs](https://xiaohang007.github.io/SLICES/)
- **Paper**: [Nature Communications](https://www.nature.com/articles/s41467-023-42870-7)
