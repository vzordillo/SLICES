# Scripts Directory

This directory contains utility scripts organized by category.

## Directory Structure

### `tests/`
Test scripts for validation and verification:
- `test_failed_structures.py` - Test structures that previously failed
- `test_improved_decoding.py` - Test decoding strategies
- `test_known_failures.py` - Test known failure cases
- `run_tests.py` - Run test suite
- `run_comparison_test.py` - Run comparison tests
- `verify_baseline.py` - Verify baseline results

### `benchmarks/`
Benchmark scripts for performance evaluation:
- `benchmark.py` - General benchmarking script
- `encode_decode_orbv3_benchmark.py` - ORBv3 encoding/decoding benchmark
- `plot_formation_energy_comparison.py` - Plot formation energy comparisons

### `utilities/`
Utility scripts for setup and maintenance:
- `validate_installation.py` - Validate SLICES installation
- `git_checkpoint.sh` - Git checkpoint utility

## Usage

### Running Tests
```bash
# Run all tests
python scripts/tests/run_tests.py

# Run specific test
python scripts/tests/test_improved_decoding.py
```

### Running Benchmarks
```bash
# Run benchmark
python scripts/benchmarks/benchmark.py

# Run ORBv3 benchmark
python scripts/benchmarks/encode_decode_orbv3_benchmark.py
```

### Utilities
```bash
# Validate installation
python scripts/utilities/validate_installation.py
```

