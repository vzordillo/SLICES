"""
Pytest configuration and shared fixtures for SLICES tests.
"""

import pytest
import numpy as np
from pathlib import Path
from pymatgen.core.structure import Structure
from slices.core import SLICES
from slices.tobascco_net import Net
import networkx as nx

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "fixtures"
STRUCTURES_DIR = TEST_DATA_DIR / "structures"


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the test data directory path."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def structures_dir():
    """Return the structures directory path."""
    return STRUCTURES_DIR


@pytest.fixture
def sample_structure():
    """Load a known test structure (NdSiRu)."""
    cif_path = STRUCTURES_DIR / "NdSiRu.cif"
    if cif_path.exists():
        return Structure.from_file(str(cif_path))
    else:
        # Create a simple test structure if file doesn't exist
        from pymatgen.core import Lattice
        return Structure(
            Lattice.cubic(4.0),
            ["Si", "Si"],
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )


@pytest.fixture
def sample_structure_sr3ru2o7():
    """Load Sr3Ru2O7 test structure."""
    cif_path = STRUCTURES_DIR / "Sr3Ru2O7.cif"
    if cif_path.exists():
        return Structure.from_file(str(cif_path))
    else:
        return None


@pytest.fixture
def slices_backend():
    """Create SLICES backend with default settings (CHGNet)."""
    return SLICES(relax_model='chgnet')


@pytest.fixture
def slices_backend_m3gnet():
    """Create SLICES backend with M3GNet."""
    return SLICES(relax_model='m3gnet')


@pytest.fixture
def simple_net():
    """Create a simple Net object for testing."""
    x_dat = [('1', '2', {'label': 'e1'})]
    net = Net(x_dat, dim=3)
    net.voltage = np.array([[1.0, 0.0, 0.0]])
    return net


@pytest.fixture
def known_slices_string():
    """Return a known good SLICES string for testing."""
    # This is a placeholder - should be replaced with actual known good SLICES
    # from a verified structure
    return "Nd Si Ru 0 1 2 0 0 0 1 2 0 0 0 2 0 0 0 0"


@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test to prevent memory leaks."""
    import gc
    yield
    gc.collect()


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for tests."""
    return tmp_path

