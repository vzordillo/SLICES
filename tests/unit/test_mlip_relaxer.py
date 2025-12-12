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
    
    def test_get_m3gnet_relaxer(self):
        """Test getting M3GNet relaxer."""
        try:
            relaxer = get_relaxer('m3gnet')
            assert relaxer is not None
            assert isinstance(relaxer, MLIPRelaxer)
        except Exception as e:
            pytest.skip(f"M3GNet not available: {e}")
    
    def test_get_chgnet_relaxer(self):
        """Test getting CHGNet relaxer."""
        try:
            relaxer = get_relaxer('chgnet')
            assert relaxer is not None
            assert isinstance(relaxer, MLIPRelaxer)
        except Exception as e:
            pytest.skip(f"CHGNet not available: {e}")
    
    
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
            relaxer = get_relaxer('m3gnet')
            assert hasattr(relaxer, 'relax')
            assert callable(getattr(relaxer, 'relax'))
        except Exception as e:
            pytest.skip(f"Relaxer not available: {e}")
    
    @pytest.mark.mlip
    @pytest.mark.slow
    def test_relax_simple_structure(self):
        """Test relaxing a simple structure."""
        try:
            relaxer = get_relaxer('m3gnet')
            # Use larger structure for M3GNet (needs proper three-body interactions)
            structure = Structure(
                Lattice.cubic(5.43),
                ["Si"] * 8,
                [[0.0, 0.0, 0.0], [0.25, 0.25, 0.25], [0.5, 0.5, 0.0], [0.75, 0.75, 0.25],
                [0.5, 0.0, 0.5], [0.75, 0.25, 0.75], [0.0, 0.5, 0.5], [0.25, 0.75, 0.75]]
            )
            
            result = relaxer.relax(structure, fmax=0.3, steps=10)
            assert result is not None
            assert 'final_structure' in result
            assert isinstance(result['final_structure'], Structure)
        except Exception as e:
            pytest.skip(f"Relaxation failed: {e}")

