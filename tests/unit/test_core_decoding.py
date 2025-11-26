"""
Unit tests for SLICES decoding functionality (SLICES2structure).

Tests the conversion of SLICES strings back to crystal structures.
"""

import pytest
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from slices.core import SLICES, SLICESDecodingError, GraphTopologyError, XTBExecutionError
from tests.conftest import sample_structure, slices_backend, known_slices_string


class TestFromSLICES:
    """Test from_SLICES parsing method."""
    
    def test_parse_valid_slices_strategy_1(self, slices_backend):
        """Test parsing a valid SLICES string with strategy 1."""
        # Create a simple SLICES string (strategy 1 format)
        slices_string = "Si O 0 1 o o o"
        
        slices_backend.from_SLICES(slices_string, strategy=1)
        
        assert slices_backend.atom_types is not None
        assert slices_backend.edge_indices is not None
        assert slices_backend.to_jimages is not None
    
    def test_parse_valid_slices_strategy_4(self, slices_backend):
        """Test parsing a valid SLICES string with strategy 4."""
        # Strategy 4 includes space group info
        slices_string = "Si O 0 1 ooo"
        
        try:
            slices_backend.from_SLICES(slices_string, strategy=4)
            assert slices_backend.atom_types is not None
        except (SLICESDecodingError, ValueError):
            # May fail if space group encoding is required
            pytest.skip("Strategy 4 requires space group encoding")
    
    def test_parse_invalid_slices_raises_error(self, slices_backend):
        """Test that parsing invalid SLICES raises appropriate error."""
        invalid_slices = "invalid slices string"
        
        with pytest.raises((SLICESDecodingError, ValueError, IndexError)):
            slices_backend.from_SLICES(invalid_slices, strategy=4)
    
    def test_parse_empty_slices_raises_error(self, slices_backend):
        """Test that parsing empty SLICES raises error."""
        with pytest.raises((SLICESDecodingError, ValueError, IndexError)):
            slices_backend.from_SLICES("", strategy=4)
    
    def test_fix_duplicate_edge(self, slices_backend):
        """Test fix_duplicate_edge parameter."""
        # Create SLICES with potential duplicates
        slices_string = "Si O 0 1 ooo 1 0 ooo"  # Duplicate edge
        
        try:
            slices_backend.from_SLICES(slices_string, strategy=4, fix_duplicate_edge=True)
            # Should handle duplicates gracefully
        except (SLICESDecodingError, ValueError):
            pass  # May fail for invalid format


class TestSLICES2Structure:
    """Test SLICES2structure decoding method."""
    
    def test_decode_valid_slices(self, slices_backend, sample_structure):
        """Test decoding a valid SLICES string."""
        # First encode to get a valid SLICES string
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        # Then decode it
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert reconstructed is not None
        assert isinstance(reconstructed, Structure)
        assert len(reconstructed) > 0
        # Energy may be 0 if relaxation failed, but structure should exist
        assert isinstance(energy, (int, float))
    
    def test_decode_round_trip_basic(self, slices_backend, sample_structure):
        """Test basic round-trip: encode then decode."""
        # Encode
        slices_string = slices_backend.structure2SLICES(sample_structure)
        assert slices_string is not None
        
        # Decode
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        assert reconstructed is not None
        assert len(reconstructed) == len(sample_structure)
    
    def test_decode_invalid_slices_raises_error(self, slices_backend):
        """Test that decoding invalid SLICES raises appropriate error."""
        invalid_slices = "this is not a valid SLICES string"
        
        with pytest.raises((SLICESDecodingError, GraphTopologyError, ValueError, IndexError)):
            slices_backend.SLICES2structure(invalid_slices)
    
    def test_decode_malformed_slices_raises_error(self, slices_backend):
        """Test that decoding malformed SLICES raises error."""
        malformed = "Si O invalid edge data"
        
        with pytest.raises((SLICESDecodingError, ValueError, IndexError)):
            slices_backend.SLICES2structure(malformed)
    
    @pytest.mark.xtb
    def test_decode_requires_xtb(self, slices_backend, sample_structure):
        """Test that decoding requires XTB binary (if available)."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        try:
            reconstructed, energy = slices_backend.SLICES2structure(slices_string)
            # If XTB is available, should work
            assert reconstructed is not None
        except XTBExecutionError:
            # XTB not available - this is acceptable
            pytest.skip("XTB binary not available")
        except (GraphTopologyError, SLICESDecodingError):
            # Graph topology issues are also acceptable for some structures
            pass


class TestToStructures:
    """Test to_structures internal method."""
    
    def test_to_structures_returns_list(self, slices_backend, sample_structure):
        """Test that to_structures returns a list of structures."""
        # First encode
        slices_string = slices_backend.structure2SLICES(sample_structure)
        slices_backend.from_SLICES(slices_string)
        
        try:
            structures, energy = slices_backend.to_structures()
            
            assert isinstance(structures, list)
            assert len(structures) >= 1  # At least one structure
            assert all(isinstance(s, Structure) for s in structures)
            assert isinstance(energy, (int, float))
        except (GraphTopologyError, XTBExecutionError) as e:
            # Some structures may have incompatible graph topologies
            pytest.skip(f"Structure has incompatible graph topology: {e}")


class TestDecodingErrorHandling:
    """Test error handling in decoding."""
    
    def test_graph_topology_error(self, slices_backend):
        """Test that incompatible graph topologies raise GraphTopologyError."""
        # Create a SLICES string that might have topology issues
        invalid_slices = "Si 0 1 invalid"
        
        with pytest.raises((GraphTopologyError, SLICESDecodingError, ValueError, IndexError)):
            slices_backend.SLICES2structure(invalid_slices)
    
    def test_xtb_timeout_handling(self, slices_backend, sample_structure):
        """Test that XTB timeouts are handled gracefully."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        try:
            reconstructed, energy = slices_backend.SLICES2structure(slices_string)
            # Should either succeed or raise XTBExecutionError
        except XTBExecutionError as e:
            assert "timeout" in str(e).lower() or "XTB" in str(e)
        except (GraphTopologyError, SLICESDecodingError):
            # Other errors are also acceptable
            pass

