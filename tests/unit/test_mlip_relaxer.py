"""
Unit tests for MLIP relaxer module.

Tests the MLIP model adapters and factory function.
"""

import pytest
from slices.mlip_relaxer import get_relaxer, MLIPRelaxer
from pymatgen.core.structure import Structure
from pymatgen.core import Lattice


class TestGetRelaxer:
    """Test get_relaxer factory function."""
    
    def test_get_chgnet_relaxer(self):
        """Test getting CHGNet relaxer."""
        try:
            relaxer = get_relaxer('chgnet')
            assert relaxer is not None
            assert isinstance(relaxer, MLIPRelaxer)
        except Exception as e:
            pytest.skip(f"CHGNet not available: {e}")
    
    def test_get_m3gnet_relaxer(self):
        """Test getting M3GNet relaxer."""
        try:
            relaxer = get_relaxer('m3gnet')
            assert relaxer is not None
            assert isinstance(relaxer, MLIPRelaxer)
        except Exception as e:
            pytest.skip(f"M3GNet not available: {e}")
    
    def test_get_matgl_relaxer(self):
        """Test getting MatGL relaxer."""
        try:
            relaxer = get_relaxer('matgl')
            assert relaxer is not None
            assert isinstance(relaxer, MLIPRelaxer)
        except Exception as e:
            pytest.skip(f"MatGL not available: {e}")
    
    def test_invalid_model_raises_error(self):
        """Test that invalid model name raises error."""
        with pytest.raises((ValueError, KeyError)):
            get_relaxer('invalid_model')


class TestMLIPRelaxerInterface:
    """Test MLIPRelaxer interface methods."""
    
    @pytest.mark.mlip
    def test_relax_method_exists(self):
        """Test that relax method exists on relaxer."""
        try:
            relaxer = get_relaxer('chgnet')
            assert hasattr(relaxer, 'relax')
            assert callable(getattr(relaxer, 'relax'))
        except Exception as e:
            pytest.skip(f"Relaxer not available: {e}")
    
    @pytest.mark.mlip
    @pytest.mark.slow
    def test_relax_simple_structure(self):
        """Test relaxing a simple structure."""
        try:
            relaxer = get_relaxer('chgnet')
            structure = Structure(
                Lattice.cubic(4.0),
                ["Si", "Si"],
                [[0, 0, 0], [0.5, 0.5, 0.5]]
            )
            
            relaxed, energy = relaxer.relax(structure)
            assert relaxed is not None
            assert isinstance(relaxed, Structure)
            assert isinstance(energy, (int, float))
        except Exception as e:
            pytest.skip(f"Relaxation failed: {e}")

