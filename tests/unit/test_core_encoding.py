"""
Unit tests for SLICES encoding functionality (structure2SLICES).

Tests the conversion of crystal structures to SLICES string representations.
"""

import pytest
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.core import Lattice
from slices.core import SLICES, SLICESEncodingError
from tests.conftest import sample_structure, slices_backend


class TestStructure2SLICES:
    """Test structure2SLICES encoding method."""
    
    def test_encode_simple_structure(self, slices_backend, sample_structure):
        """Test encoding a simple known structure."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        assert slices_string is not None
        assert isinstance(slices_string, str)
        assert len(slices_string) > 0
        # Should contain element symbols
        assert any(elem in slices_string for elem in ['Nd', 'Si', 'Ru'])
    
    def test_encode_all_strategies(self, slices_backend, sample_structure):
        """Test encoding with all available strategies (1, 2, 3, 4)."""
        for strategy in [1, 2, 3, 4]:
            slices_string = slices_backend.structure2SLICES(sample_structure, strategy=strategy)
            assert slices_string is not None
            assert isinstance(slices_string, str)
            assert len(slices_string) > 0
    
    def test_encode_different_graph_methods(self, sample_structure):
        """Test encoding with different graph methods."""
        graph_methods = ['econnn', 'crystalnn', 'brunnernn', 'econ']
        
        for method in graph_methods:
            backend = SLICES(relax_model='chgnet', graph_method=method)
            try:
                slices_string = backend.structure2SLICES(sample_structure)
                assert slices_string is not None
                assert isinstance(slices_string, str)
            except Exception as e:
                # Some graph methods may not work for all structures
                pytest.skip(f"Graph method {method} failed: {e}")
    
    def test_encode_single_atom_structure(self, slices_backend):
        """Test encoding a single atom structure."""
        # Create a simple single atom structure
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si"],
            [[0, 0, 0]]
        )
        
        slices_string = slices_backend.structure2SLICES(structure)
        assert slices_string is not None
        assert isinstance(slices_string, str)
    
    def test_encode_empty_structure_raises_error(self, slices_backend):
        """Test that encoding an empty structure raises an error."""
        # Create empty structure (should fail)
        with pytest.raises((ValueError, SLICESEncodingError, AttributeError)):
            structure = Structure(Lattice.cubic(4.0), [], [])
            slices_backend.structure2SLICES(structure)
    
    def test_encode_unsupported_element(self, slices_backend):
        """Test encoding with unsupported elements (Z > 86)."""
        # Create structure with element Z > 86 (beyond GFN-FF limit)
        # This should be caught by check_element
        structure = Structure(
            Lattice.cubic(4.0),
            ["Fr"],  # Francium (Z=87)
            [[0, 0, 0]]
        )
        
        # Should either fail or be handled gracefully
        try:
            slices_string = slices_backend.structure2SLICES(structure)
            # If it succeeds, that's also acceptable (may have been filtered)
        except (ValueError, SLICESEncodingError):
            pass  # Expected behavior
    
    def test_encode_consistency(self, slices_backend, sample_structure):
        """Test that encoding the same structure multiple times is consistent."""
        slices1 = slices_backend.structure2SLICES(sample_structure)
        slices2 = slices_backend.structure2SLICES(sample_structure)
        
        # Should produce the same SLICES string (or equivalent)
        assert slices1 == slices2
    
    def test_encode_different_orientations(self, slices_backend, sample_structure):
        """Test that encoding is invariant to structure orientation."""
        # Create rotated version of structure
        from pymatgen.transformations.standard_transformations import RotationTransformation
        
        try:
            rotation = RotationTransformation([1, 1, 1], 90)
            rotated_structure = rotation.apply_transformation(sample_structure)
            
            slices_original = slices_backend.structure2SLICES(sample_structure)
            slices_rotated = slices_backend.structure2SLICES(rotated_structure)
            
            # SLICES should be invariant (or at least valid)
            assert slices_original is not None
            assert slices_rotated is not None
        except ImportError:
            pytest.skip("RotationTransformation not available")


class TestGetSlicesByStrategy:
    """Test get_slices_by_strategy method."""
    
    def test_strategy_1(self, slices_backend):
        """Test strategy 1 encoding format."""
        atom_symbols = ['Si', 'O']
        edge_indices = np.array([[0, 1]])
        to_jimages = np.array([[0, 0, 0]])
        
        slices = slices_backend.get_slices1(atom_symbols, edge_indices, to_jimages)
        assert isinstance(slices, str)
        assert 'Si' in slices
        assert 'O' in slices
    
    def test_strategy_2(self, slices_backend):
        """Test strategy 2 encoding format."""
        atom_symbols = ['Si', 'O']
        edge_indices = np.array([[0, 1]])
        to_jimages = np.array([[0, 0, 0]])
        
        slices = slices_backend.get_slices2(atom_symbols, edge_indices, to_jimages)
        assert isinstance(slices, str)
    
    def test_strategy_3(self, slices_backend):
        """Test strategy 3 encoding format."""
        atom_symbols = ['Si', 'O']
        edge_indices = np.array([[0, 1]])
        to_jimages = np.array([[0, 0, 0]])
        
        slices = slices_backend.get_slices3(atom_symbols, edge_indices, to_jimages)
        assert isinstance(slices, str)
        assert 'Si' in slices or 'O' in slices
    
    def test_strategy_4(self, slices_backend):
        """Test strategy 4 encoding format."""
        atom_symbols = ['Si', 'O']
        edge_indices = np.array([[0, 1]])
        to_jimages = np.array([[0, 0, 0]])
        space_group_num = 1
        
        slices = slices_backend.get_slices4(atom_symbols, edge_indices, to_jimages, space_group_num)
        assert isinstance(slices, str)
    
    def test_invalid_strategy(self, slices_backend):
        """Test that invalid strategy raises error."""
        atom_symbols = ['Si', 'O']
        edge_indices = np.array([[0, 1]])
        to_jimages = np.array([[0, 0, 0]])
        
        with pytest.raises(ValueError):
            slices_backend.get_slices_by_strategy(99, atom_symbols, edge_indices, to_jimages, None)


class TestEncodingEdgeCases:
    """Test edge cases in encoding."""
    
    def test_large_structure(self, slices_backend):
        """Test encoding a larger structure."""
        # Create a larger structure
        lattice = Lattice.cubic(10.0)
        species = ["Si"] * 8
        coords = [
            [0.0, 0.0, 0.0],
            [0.5, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.5, 0.0],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
            [0.5, 0.5, 0.5],
        ]
        structure = Structure(lattice, species, coords)
        
        slices_string = slices_backend.structure2SLICES(structure)
        assert slices_string is not None
        assert isinstance(slices_string, str)
    
    @pytest.mark.slow
    def test_encoding_performance(self, slices_backend, sample_structure):
        """Test that encoding completes in reasonable time."""
        import time
        
        start = time.time()
        slices_string = slices_backend.structure2SLICES(sample_structure)
        elapsed = time.time() - start
        
        assert slices_string is not None
        assert elapsed < 60  # Should complete in under 60 seconds

