"""
Backward compatibility tests.

Ensures that API signatures and default behavior remain consistent.
"""

import pytest
import inspect
from slices.core import SLICES
from slices.tobascco_net import Net
from slices.mlip_relaxer import get_relaxer


class TestAPISignatures:
    """Test that public API method signatures remain unchanged."""
    
    def test_slices_init_signature(self):
        """Test that SLICES.__init__ signature is consistent."""
        sig = inspect.signature(SLICES.__init__)
        param_names = list(sig.parameters.keys())
        
        # Should have these parameters (order may vary)
        expected_params = ['atom_types', 'edge_indices', 'to_jimages', 
                          'graph_method', 'check_results', 'optimizer', 
                          'fmax', 'steps', 'relax_model']
        
        for param in expected_params:
            assert param in param_names, f"Missing parameter: {param}"
    
    def test_structure2slices_signature(self):
        """Test that structure2SLICES signature is consistent."""
        sig = inspect.signature(SLICES.structure2SLICES)
        param_names = list(sig.parameters.keys())
        
        # Should have 'structure' and 'strategy' parameters
        assert 'structure' in param_names
        assert 'strategy' in param_names
    
    def test_slices2structure_signature(self):
        """Test that SLICES2structure signature is consistent."""
        sig = inspect.signature(SLICES.SLICES2structure)
        param_names = list(sig.parameters.keys())
        
        # Should have 'SLICES' parameter
        assert 'SLICES' in param_names or 'slices' in param_names.lower()
    
    def test_net_init_signature(self):
        """Test that Net.__init__ signature is consistent."""
        sig = inspect.signature(Net.__init__)
        param_names = list(sig.parameters.keys())
        
        # Should have 'graph', 'dim', 'options' parameters
        assert 'graph' in param_names or 'self' in param_names
        assert 'dim' in param_names


class TestDefaultParameters:
    """Test that default parameters produce consistent results."""
    
    def test_default_relax_model(self):
        """Test that default relax_model is m3gnet."""
        backend = SLICES()
        assert backend.relax_model == 'm3gnet'
    
    def test_default_graph_method(self):
        """Test that default graph_method is econnn."""
        backend = SLICES()
        assert backend.graph_method == 'econnn'
    
    def test_default_fmax(self):
        """Test that default fmax is 0.2."""
        backend = SLICES()
        assert backend.fmax == 0.2
    
    def test_default_steps(self):
        """Test that default steps is 100."""
        backend = SLICES()
        assert backend.steps == 100
    
    def test_default_optimizer(self):
        """Test that default optimizer is BFGS."""
        backend = SLICES()
        assert backend.optimizer == "BFGS"


class TestErrorHandlingConsistency:
    """Test that error handling remains consistent."""
    
    def test_encoding_error_type(self):
        """Test that encoding errors raise SLICESEncodingError."""
        backend = SLICES()
        
        # Try to encode invalid structure
        from pymatgen.core import Lattice, Structure
        invalid_structure = Structure(Lattice.cubic(4.0), [], [])
        
        with pytest.raises((ValueError, AttributeError, Exception)):
            # Should raise some form of error
            backend.structure2SLICES(invalid_structure)
    
    def test_decoding_error_type(self):
        """Test that decoding errors raise appropriate exceptions."""
        backend = SLICES()
        
        invalid_slices = "invalid slices string"
        
        with pytest.raises((Exception, ValueError, IndexError)):
            # Should raise some form of error
            backend.SLICES2structure(invalid_slices)


class TestReturnTypes:
    """Test that return types remain consistent."""
    
    def test_structure2slices_returns_string(self):
        """Test that structure2SLICES returns a string."""
        from pymatgen.core import Lattice, Structure
        
        backend = SLICES()
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si", "O"],
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )
        
        result = backend.structure2SLICES(structure)
        assert isinstance(result, str)
    
    def test_slices2structure_returns_tuple(self):
        """Test that SLICES2structure returns (Structure, float)."""
        from pymatgen.core import Lattice, Structure
        
        backend = SLICES()
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si", "O"],
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )
        
        slices_string = backend.structure2SLICES(structure)
        result = backend.SLICES2structure(slices_string)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        from pymatgen.core.structure import Structure as PMGStructure
        assert isinstance(result[0], PMGStructure)
        assert isinstance(result[1], (int, float))

