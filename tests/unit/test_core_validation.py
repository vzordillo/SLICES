"""
Unit tests for SLICES validation methods.

Tests check_SLICES, check_SLICES_basic, check_element, and dimensionality checks.
"""

import pytest
from pymatgen.core.structure import Structure
from pymatgen.core import Lattice
from slices.core import SLICES
from tests.conftest import sample_structure, slices_backend


class TestCheckSLICES:
    """Test check_SLICES validation method."""
    
    def test_check_valid_slices(self, slices_backend, sample_structure):
        """Test checking a valid SLICES string."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        result = slices_backend.check_SLICES(slices_string)
        assert isinstance(result, bool)
        # Valid SLICES should pass
        assert result is True
    
    def test_check_invalid_slices(self, slices_backend):
        """Test checking an invalid SLICES string."""
        invalid_slices = "invalid slices string"
        
        result = slices_backend.check_SLICES(invalid_slices)
        assert isinstance(result, bool)
        # Invalid SLICES should fail
        assert result is False
    
    def test_check_slices_with_duplicate_check(self, slices_backend, sample_structure):
        """Test check_SLICES with duplicate edge checking enabled."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        result = slices_backend.check_SLICES(slices_string, dupli_check=True)
        assert isinstance(result, bool)
    
    def test_check_slices_with_graph_rank_check(self, slices_backend, sample_structure):
        """Test check_SLICES with graph rank checking."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        result = slices_backend.check_SLICES(slices_string, graph_rank_check=True)
        assert isinstance(result, bool)


class TestCheckSLICESBasic:
    """Test check_SLICES_basic method."""
    
    def test_check_basic_valid_slices(self, slices_backend, sample_structure):
        """Test basic check on valid SLICES."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        result = slices_backend.check_SLICES_basic(slices_string)
        assert isinstance(result, bool)
        assert result is True
    
    def test_check_basic_invalid_slices(self, slices_backend):
        """Test basic check on invalid SLICES."""
        invalid_slices = "not a valid slices string"
        
        result = slices_backend.check_SLICES_basic(invalid_slices)
        assert isinstance(result, bool)
        assert result is False


class TestCheckElement:
    """Test check_element method."""
    
    def test_check_element_valid(self, slices_backend):
        """Test checking structure with valid elements (Z < 87)."""
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si", "O"],
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )
        
        result = slices_backend.check_element(structure)
        assert result is True
    
    def test_check_element_invalid(self, slices_backend):
        """Test checking structure with invalid element (Z >= 87)."""
        # Create structure with Francium (Z=87) - beyond GFN-FF limit
        structure = Structure(
            Lattice.cubic(4.0),
            ["Fr"],  # Francium (Z=87)
            [[0, 0, 0]]
        )
        
        result = slices_backend.check_element(structure)
        assert result is False
    
    def test_check_element_mixed(self, slices_backend):
        """Test checking structure with mixed valid/invalid elements."""
        # Structure with both valid and invalid elements
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si", "Fr"],  # Si is valid, Fr is invalid
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )
        
        result = slices_backend.check_element(structure)
        # Should return False if any element is invalid
        assert result is False


class TestDimensionalityChecks:
    """Test check_2D and check_3D methods."""
    
    def test_check_3d_structure(self, slices_backend, sample_structure):
        """Test checking a 3D structure."""
        result = slices_backend.check_3D(sample_structure)
        assert isinstance(result, bool)
        # Most crystal structures should be 3D
        # Result depends on actual structure
    
    def test_check_2d_structure(self, slices_backend):
        """Test checking a 2D structure."""
        # Create a 2D-like structure (layered)
        structure = Structure(
            Lattice.orthorhombic(4.0, 4.0, 20.0),  # Large c for 2D
            ["Si", "Si"],
            [[0, 0, 0], [0.5, 0.5, 0.1]]  # Close in z direction
        )
        
        result = slices_backend.check_2D(structure)
        assert isinstance(result, bool)
    
    def test_check_structural_validity(self):
        """Test check_structural_validity static method."""
        valid_slices = "Si O 0 1 ooo"
        
        result = SLICES.check_structural_validity(valid_slices)
        assert isinstance(result, bool)


class TestCanonicalSLICES:
    """Test get_canonical_SLICES method."""
    
    def test_get_canonical_slices(self, slices_backend, sample_structure):
        """Test getting canonical SLICES representation."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        canonical = slices_backend.get_canonical_SLICES(slices_string)
        assert isinstance(canonical, str)
        assert len(canonical) > 0
    
    def test_canonical_consistency(self, slices_backend, sample_structure):
        """Test that canonical SLICES is consistent."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        canonical1 = slices_backend.get_canonical_SLICES(slices_string)
        canonical2 = slices_backend.get_canonical_SLICES(slices_string)
        
        # Should produce same canonical form
        assert canonical1 == canonical2

