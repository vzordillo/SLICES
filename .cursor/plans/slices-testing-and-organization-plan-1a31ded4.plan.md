<!-- 1a31ded4-1e10-46f9-8d78-c6dcd1534108 98f563c9-cfe1-48a5-8ca1-0dc03c7f3faf -->
# SLICES Testing and Organization Plan

## Overview

This plan addresses three critical areas: (1) comprehensive unit testing to prevent regressions, (2) improved file organization for better maintainability, and (3) enhanced documentation for accessibility. The goal is to make the codebase robust, readable, and accessible without breaking existing functionality.

---

## Part 1: Comprehensive Unit Testing Framework

### 1.1 Test Directory Structure

Create a proper test hierarchy:

```
tests/
├── __init__.py
├── conftest.py                    # pytest fixtures and shared utilities
├── unit/                          # Unit tests for individual components
│   ├── __init__.py
│   ├── test_core_encoding.py      # structure2SLICES tests
│   ├── test_core_decoding.py      # SLICES2structure tests
│   ├── test_core_validation.py    # check_SLICES, check_element, etc.
│   ├── test_tobascco_net.py       # Net class, cycle/cocycle basis
│   ├── test_mlip_relaxer.py      # MLIP model adapters
│   └── test_utils.py              # Utility functions
├── integration/                   # Integration tests for workflows
│   ├── __init__.py
│   ├── test_round_trip.py         # structure -> SLICES -> structure
│   ├── test_mlip_integration.py  # MLIP model workflows
│   ├── test_xtb_integration.py   # XTB binary workflows
│   └── test_graph_topology.py     # Graph theory workflows
├── regression/                    # Regression tests to prevent breaking changes
│   ├── __init__.py
│   ├── test_known_structures.py  # Known good structures (NdSiRu, Sr3Ru2O7, etc.)
│   ├── test_mp20_samples.py       # MP-20 dataset samples
│   └── test_backward_compatibility.py  # Ensure API compatibility
└── fixtures/                      # Test data and fixtures
    ├── structures/                # CIF files for testing
    │   ├── NdSiRu.cif
    │   ├── Sr3Ru2O7.cif
    │   └── simple_structures/     # Small test structures
    └── slices_strings/            # Known good SLICES strings
        └── reference_slices.txt
```

### 1.2 Core Functionality Tests

#### Test Suite: `tests/unit/test_core_encoding.py`

- Test `structure2SLICES()` with various structures
- Test all encoding strategies (1, 2, 3, 4)
- Test with different graph methods (econnn, crystalnn, etc.)
- Test edge cases (empty structures, single atom, large structures)
- Test error handling (invalid structures, unsupported elements)

#### Test Suite: `tests/unit/test_core_decoding.py`

- Test `SLICES2structure()` with valid SLICES strings
- Test `from_SLICES()` parsing for all strategies
- Test `to_structures()` internal workflow
- Test error handling (invalid SLICES, malformed strings)
- Test with different MLIP models

#### Test Suite: `tests/unit/test_tobascco_net.py`

- Test `Net` class initialization
- Test `simple_cycle_basis()` computation
- Test `get_lattice_basis()` (success and failure cases)
- Test `get_cocycle_basis()` (success and failure cases)
- Test `get_metric_tensor()` computation
- Test `iter_cycles()` iterative implementation
- Test `clear_cache()` memory management
- Test error handling (LatticeBasisError, CocycleBasisError)

#### Test Suite: `tests/integration/test_round_trip.py`

- Round-trip tests: structure -> SLICES -> structure
- Verify structure matching using StructureMatcher
- Test with multiple MLIP models
- Test with different encoding strategies
- Performance benchmarks for round-trip time

### 1.3 Regression Test Suite

#### Test Suite: `tests/regression/test_known_structures.py`

- Fixed set of known structures with expected SLICES strings
- Verify encoding produces same SLICES (or equivalent)
- Verify decoding produces structures within tolerance
- Track encoding/decoding success rates over time

#### Test Suite: `tests/regression/test_backward_compatibility.py`

- Test that public API methods maintain signatures
- Test that default parameters produce same results
- Test that error handling remains consistent

### 1.4 Test Infrastructure

#### `tests/conftest.py` - Shared Fixtures

```python
@pytest.fixture
def sample_structure():
    """Load a known test structure"""
    return Structure.from_file('tests/fixtures/structures/NdSiRu.cif')

@pytest.fixture
def slices_backend():
    """Create SLICES backend with default settings"""
    return SLICES(relax_model='chgnet')

@pytest.fixture
def simple_net():
    """Create a simple Net object for testing"""
    x_dat = [('1', '2', {'label': 'e1'})]
    return Net(x_dat, dim=3)
```

#### Test Configuration: `pytest.ini` or `pyproject.toml`

- Configure pytest settings
- Set test discovery patterns
- Configure coverage reporting
- Set up markers for test categories

### 1.5 Continuous Integration Setup

- Add GitHub Actions workflow (`.github/workflows/tests.yml`)
- Run tests on Python 3.9, 3.10, 3.11
- Run tests on multiple OS (Linux, macOS)
- Generate coverage reports
- Fail on coverage drop below threshold

---

## Part 2: File Organization Improvements

### 2.1 Current Issues

- `src/slices/core.py` is 2314 lines (too large)
- Test files scattered in root directory
- No clear separation of concerns
- Documentation files need better organization

### 2.2 Proposed Organization (Without Breaking Changes)

#### Directory Structure:

```
SLICES/
├── src/slices/                    # Source code (keep as-is)
│   ├── __init__.py
│   ├── core.py                    # Main SLICES class (keep, but document sections)
│   ├── tobascco_net.py
│   ├── mlip_relaxer.py
│   ├── config.py
│   ├── utils.py
│   └── utils_wyckoff.py
├── tests/                         # NEW: All tests here
│   └── [structure from Part 1.1]
├── docs/                          # Enhanced documentation
│   ├── api/                       # API reference
│   │   ├── core.md
│   │   ├── tobascco_net.md
│   │   └── mlip_relaxer.md
│   ├── guides/                    # User guides
│   │   ├── getting_started.md
│   │   ├── advanced_usage.md
│   │   └── troubleshooting.md
│   └── development/               # Developer docs
│       ├── contributing.md
│       ├── testing.md
│       └── architecture.md
├── examples/                      # Keep and organize
│   ├── basic/                     # Basic usage examples
│   ├── advanced/                  # Advanced examples
│   └── notebooks/                 # Jupyter notebooks
├── scripts/                       # NEW: Utility scripts
│   ├── run_tests.py               # Test runner
│   ├── validate_installation.py   # Installation checker
│   └── benchmark.py               # Performance benchmarks
├── README.md                       # Main user documentation
├── DEVELOPER_GUIDE.md              # Technical documentation
└── CONTRIBUTING.md                 # NEW: Contribution guidelines
```

### 2.3 Code Organization Improvements

#### Add Section Markers to `core.py`

Since we're keeping the file intact, add clear section markers:

```python
# ============================================================================
# SECTION 1: Exception Classes and Utilities
# ============================================================================

# ============================================================================
# SECTION 2: SLICES Class - Initialization and Configuration
# ============================================================================

# ============================================================================
# SECTION 3: SLICES Class - Encoding Methods (structure2SLICES)
# ============================================================================

# ============================================================================
# SECTION 4: SLICES Class - Decoding Methods (SLICES2structure)
# ============================================================================

# ============================================================================
# SECTION 5: SLICES Class - Graph Operations
# ============================================================================

# ============================================================================
# SECTION 6: SLICES Class - MLIP Relaxation
# ============================================================================

# ============================================================================
# SECTION 7: SLICES Class - XTB Integration
# ============================================================================
```

#### Create Module-Level Documentation

- Add `__init__.py` exports for public API
- Document which classes/functions are public vs internal
- Add version information

### 2.4 Test File Organization

Move existing test files:

- `test_slices_functions.py` → `tests/integration/test_round_trip_batch.py`
- `test_slices_encoding_only.py` → `tests/unit/test_encoding_only.py`

---

## Part 3: Documentation Enhancements

### 3.1 API Documentation

#### Create `docs/api/core.md`

- Document all public methods of `SLICES` class
- Include parameter descriptions, return types, exceptions
- Add code examples for each method
- Document encoding strategies

#### Create `docs/api/tobascco_net.md`

- Document `Net` class methods
- Explain graph theory concepts
- Document error conditions

### 3.2 User Guides

#### Create `docs/guides/getting_started.md`

- Quick start tutorial
- Installation verification
- First encoding/decoding example
- Common pitfalls

#### Create `docs/guides/advanced_usage.md`

- Custom MLIP models
- Performance tuning
- Batch processing
- Memory optimization

### 3.3 Developer Documentation

#### Create `docs/development/testing.md`

- How to write tests
- Test structure and conventions
- Running tests
- Adding new test cases

#### Create `docs/development/architecture.md`

- System architecture diagram
- Data flow diagrams
- Component interactions
- Extension points

### 3.4 Code Documentation

#### Improve Inline Documentation

- Add docstrings to all public methods (many already exist)
- Add type hints where missing
- Document complex algorithms
- Add "See Also" references

#### Create `CONTRIBUTING.md`

- Code style guidelines
- Testing requirements
- Pull request process
- Code review checklist

---

## Part 4: Validation and Checking Mechanisms

### 4.1 Pre-commit Hooks

Create `.pre-commit-config.yaml`:

- Run linters (flake8, black, mypy)
- Run tests on changed files
- Check for TODO/FIXME comments
- Validate documentation

### 4.2 Test Coverage Requirements

- Set minimum coverage threshold (e.g., 80% for core functionality)
- Track coverage over time
- Fail CI if coverage drops
- Generate coverage reports

### 4.3 Regression Test Database

- Maintain a database of known good structures
- Store expected SLICES strings
- Store expected round-trip results
- Automatically validate against this database

### 4.4 Performance Benchmarks

Create `scripts/benchmark.py`:

- Benchmark encoding time
- Benchmark decoding time
- Benchmark memory usage
- Track performance over time
- Alert on significant regressions

---

## Part 5: Implementation Strategy

### Phase 1: Foundation (Week 1)

1. Create test directory structure
2. Set up pytest configuration
3. Create conftest.py with fixtures
4. Move existing test files to proper locations
5. Create basic test infrastructure

### Phase 2: Core Tests (Week 2)

1. Write unit tests for encoding (`test_core_encoding.py`)
2. Write unit tests for decoding (`test_core_decoding.py`)
3. Write unit tests for validation methods
4. Write unit tests for tobascco_net

### Phase 3: Integration Tests (Week 3)

1. Write round-trip integration tests
2. Write MLIP integration tests
3. Write XTB integration tests
4. Create regression test suite

### Phase 4: Organization (Week 4)

1. Reorganize directory structure
2. Add section markers to large files
3. Create module-level documentation
4. Organize examples and scripts

### Phase 5: Documentation (Week 5)

1. Create API documentation
2. Write user guides
3. Write developer documentation
4. Update README and DEVELOPER_GUIDE

### Phase 6: CI/CD and Validation (Week 6)

1. Set up GitHub Actions
2. Configure pre-commit hooks
3. Set up coverage reporting
4. Create benchmark scripts

---

## Success Criteria

1. **Test Coverage**: ≥80% coverage for core functionality
2. **Regression Prevention**: All known good structures pass tests
3. **Documentation**: All public APIs documented with examples
4. **Organization**: Clear directory structure, easy to navigate
5. **CI/CD**: Automated testing on every commit
6. **No Breaking Changes**: All existing functionality preserved

---

## Files to Create/Modify

### New Files:

- `tests/__init__.py`
- `tests/conftest.py`
- `tests/unit/test_*.py` (multiple files)
- `tests/integration/test_*.py` (multiple files)
- `tests/regression/test_*.py` (multiple files)
- `docs/api/*.md` (multiple files)
- `docs/guides/*.md` (multiple files)
- `docs/development/*.md` (multiple files)
- `scripts/run_tests.py`
- `scripts/validate_installation.py`
- `scripts/benchmark.py`
- `.github/workflows/tests.yml`
- `.pre-commit-config.yaml`
- `CONTRIBUTING.md`
- `pytest.ini` or update `pyproject.toml`

### Modified Files:

- `src/slices/core.py` - Add section markers, improve docstrings
- `src/slices/__init__.py` - Add public API exports
- `README.md` - Add testing section, link to new docs
- `DEVELOPER_GUIDE.md` - Add testing guide section

### Files to Move:

- `test_slices_functions.py` → `tests/integration/test_round_trip_batch.py`
- `test_slices_encoding_only.py` → `tests/unit/test_encoding_only.py`

---

## Risk Mitigation

1. **Git Branch Isolation**: All changes on separate branch, main branch untouched
2. **Backup and Tagging**: Backup branch and stable tag created before any changes
3. **Incremental Checkpoints**: Checkpoint commits after each major change
4. **Continuous Verification**: Run tests after every significant modification
5. **No Breaking Changes**: All changes are additive or organizational
6. **Gradual Migration**: Move tests incrementally, verify at each step
7. **Backward Compatibility**: Maintain all existing APIs
8. **Documentation First**: Document before major refactoring
9. **Test Before Refactor**: Write tests for existing code before changing it
10. **Easy Rollback**: Multiple rollback options (checkpoint, backup branch, tag)

---

## Maintenance Plan

1. **Regular Test Updates**: Update tests when adding features
2. **Coverage Monitoring**: Track coverage trends
3. **Performance Tracking**: Monitor benchmark results
4. **Documentation Reviews**: Regular documentation updates
5. **Test Database Updates**: Add new known-good structures regularly

### To-dos

- [ ] Replace SymPy with NumPy/SciPy for nullspace computation - REVERTED per user request
- [x] Convert recursive iter_cycles() to iterative version
- [x] Add type hints and improve documentation to tobascco_net.py
- [x] Consolidate all MD files into two organized documentation files
- [ ] Phase 0: Create git tag (v2.0.12-working) and backup branch before any changes
- [ ] Phase 0: Run baseline tests and document results for comparison
- [x] Phase 0: Create and switch to feature/testing-and-organization branch
- [x] Phase 0: Create git_checkpoint.sh script for incremental checkpoints
- [x] Phase 1: Create tests/ directory structure with all subdirectories
- [x] Phase 1: Set up pytest.ini and test configuration
- [x] Phase 1: Create conftest.py with shared fixtures and copy test data
- [x] Phase 2: Write unit tests for encoding (structure2SLICES)
- [x] Phase 2: Write unit tests for decoding (SLICES2structure)
- [x] Phase 2: Write unit tests for validation methods
- [x] Phase 2: Write unit tests for tobascco_net module
- [x] Phase 3: Write integration tests for round-trip workflows
- [x] Phase 3: Write integration tests for MLIP model workflows
- [x] Phase 3: Move existing test files to proper locations and verify they work
- [x] Phase 4: Create regression tests with known good structures
- [x] Phase 4: Create backward compatibility tests
- [x] Phase 5: Create new directory structure (docs/, scripts/)
- [x] Phase 5: Move and organize files incrementally with verification
- [x] Phase 5: Add section markers to core.py for better readability
- [x] Phase 6: Create comprehensive API documentation
- [x] Phase 6: Create user guides (getting started, advanced, troubleshooting)
- [x] Phase 6: Create developer documentation (testing, architecture, contributing)
- [x] Phase 7: Set up GitHub Actions workflow for automated testing
- [x] Phase 7: Configure pre-commit hooks for code quality
- [x] Phase 7: Create benchmark scripts for performance monitoring
- [x] Final: Run comprehensive test suite, verify no regressions, create release candidate tag