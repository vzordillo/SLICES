# Codebase Structure

This document describes the organized structure of the SLICES codebase.

## Root Directory

The root directory contains only essential files:

- **`README.md`** - Main comprehensive documentation (single source of truth)
- **`LICENSE`** - License file
- **`pyproject.toml`** - Python package configuration
- **`pytest.ini`** - Pytest configuration

## Directory Structure

```
SLICES/
├── src/slices/              # Core SLICES package
│   ├── core.py              # Main SLICES class
│   ├── decoding_improvements.py  # Enhanced decoding algorithms
│   ├── mlip_relaxer.py      # MLIP model adapters
│   ├── tobascco_net.py      # Graph theory implementation
│   └── ...
│
├── scripts/                  # Utility scripts
│   ├── benchmarks/           # Benchmarking scripts
│   ├── tests/               # Testing scripts
│   └── ...
│
├── tests/                    # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── ...
│
├── docs/                     # Documentation
│   ├── README.md            # Documentation index
│   ├── guides/              # User guides
│   ├── development/         # Developer documentation
│   ├── improvements/        # Improvements documentation
│   ├── benchmarks/          # Benchmark results
│   └── ...
│
├── config/                   # Configuration files
│   ├── entrypoint_*.sh      # Docker entrypoint scripts
│   ├── slurm.conf           # SLURM configuration
│   └── ...
│
├── data/                     # Datasets
│   └── mp20/                # MP-20 dataset
│
├── examples/                 # Example scripts and structures
│   ├── basic/               # Basic examples
│   ├── advanced/            # Advanced examples
│   └── *.cif                # Example structures
│
├── benchmark/                # Benchmark workflows
│   └── ...
│
├── MatterGPT/               # MatterGPT with flash-attention
│   └── ...
│
├── MatterGPT_no_flash/       # MatterGPT without flash-attention
│   └── ...
│
└── HTS/                      # High-Throughput Screening
    └── ...
```

## File Organization Principles

1. **Single README**: Only `README.md` in root; all other docs in `docs/`
2. **Scripts**: All scripts in `scripts/` with subdirectories by purpose
3. **Config**: All configuration files in `config/`
4. **Data**: All datasets in `data/`
5. **Tests**: All tests in `tests/` with proper structure
6. **Documentation**: All docs in `docs/` with clear organization

## Naming Conventions

- **Directories**: lowercase_with_underscores
- **Python files**: lowercase_with_underscores.py
- **Scripts**: lowercase_with_underscores.py
- **Config files**: lowercase_with_underscores.ext
- **Documentation**: UPPERCASE_WITH_UNDERSCORES.md (for key docs) or lowercase_with_underscores.md

