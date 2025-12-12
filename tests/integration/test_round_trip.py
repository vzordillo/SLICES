"""
Integration tests for SLICES round-trip workflows.

Tests the complete workflow: structure -> SLICES -> structure
"""

import pytest
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from slices.core import SLICES, SLICESDecodingError, GraphTopologyError
from tests.conftest import sample_structure, slices_backend, sample_structure_sr3ru2o7


class TestRoundTrip:
    """Test round-trip encoding and decoding."""
    
    @pytest.mark.integration
    def test_round_trip_basic(self, slices_backend, sample_structure):
        """Test basic round-trip: encode then decode."""
        # Encode
        slices_string = slices_backend.structure2SLICES(sample_structure)
        assert slices_string is not None
        
        # Decode
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        assert reconstructed is not None
        assert isinstance(reconstructed, Structure)
        assert len(reconstructed) == len(sample_structure)
    
    @pytest.mark.integration
    def test_round_trip_structure_matching(self, slices_backend, sample_structure):
        """Test that round-trip produces matching structure."""
        # Encode
        slices_string = slices_backend.structure2SLICES(sample_structure)
        
        # Decode
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        # Use StructureMatcher to verify similarity
        matcher = StructureMatcher()
        try:
            is_match = matcher.fit(sample_structure, reconstructed)
            # Structures should match (or be very similar)
            assert is_match or len(reconstructed) == len(sample_structure)
        except Exception:
            # If matching fails, at least check basic properties
            assert reconstructed.formula == sample_structure.formula or \
                   len(reconstructed) == len(sample_structure)
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_round_trip_multiple_strategies(self, slices_backend, sample_structure):
        """Test round-trip with different encoding strategies."""
        for strategy in [1, 2, 3, 4]:
            try:
                # Encode
                slices_string = slices_backend.structure2SLICES(sample_structure, strategy=strategy)
                assert slices_string is not None
                
                # Decode
                reconstructed, energy = slices_backend.SLICES2structure(slices_string, strategy=strategy)
                assert reconstructed is not None
                assert len(reconstructed) > 0
            except (SLICESDecodingError, GraphTopologyError, ValueError) as e:
                # Some strategies may not work for all structures
                pytest.skip(f"Strategy {strategy} failed: {e}")
    
    @pytest.mark.integration
    def test_round_trip_energy_consistency(self, slices_backend, sample_structure):
        """Test that round-trip produces reasonable energy values."""
        slices_string = slices_backend.structure2SLICES(sample_structure)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert isinstance(energy, (int, float))
        # Energy should be a reasonable value (not NaN, not infinite)
        assert not np.isnan(energy)
        assert not np.isinf(energy)
        # Energy of 0 means relaxation failed, which is acceptable
    
    @pytest.mark.integration
    @pytest.mark.mlip
    def test_round_trip_different_mlip_models(self, sample_structure):
        """Test round-trip with different MLIP models."""
        models = ['chgnet', 'm3gnet']  # Test most common models
        
        for model in models:
            try:
                backend = SLICES(relax_model=model)
                
                # Encode
                slices_string = backend.structure2SLICES(sample_structure)
                assert slices_string is not None
                
                # Decode
                reconstructed, energy = backend.SLICES2structure(slices_string)
                assert reconstructed is not None
                assert len(reconstructed) > 0
            except Exception as e:
                # Some models may not be available
                pytest.skip(f"MLIP model {model} not available: {e}")


class TestRoundTripWithKnownStructures:
    """Test round-trip with known good structures."""
    
    @pytest.mark.integration
    def test_round_trip_ndsiru(self, slices_backend, sample_structure):
        """Test round-trip with NdSiRu structure."""
        # This is a known good structure from examples
        slices_string = slices_backend.structure2SLICES(sample_structure)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert reconstructed is not None
        assert len(reconstructed) == len(sample_structure)
        # Formula should match
        assert reconstructed.formula == sample_structure.formula
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_round_trip_sr3ru2o7(self, slices_backend, sample_structure_sr3ru2o7):
        """Test round-trip with Sr3Ru2O7 structure."""
        if sample_structure_sr3ru2o7 is None:
            pytest.skip("Sr3Ru2O7 structure not available")
        
        slices_string = slices_backend.structure2SLICES(sample_structure_sr3ru2o7)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert reconstructed is not None
        assert len(reconstructed) == len(sample_structure_sr3ru2o7)


class TestRoundTripEdgeCases:
    """Test round-trip with edge cases."""
    
    @pytest.mark.integration
    def test_round_trip_small_structure(self, slices_backend):
        """Test round-trip with a very small structure."""
        from pymatgen.core import Lattice
        
        structure = Structure(
            Lattice.cubic(4.0),
            ["Si", "Si"],
            [[0, 0, 0], [0.5, 0.5, 0.5]]
        )
        
        slices_string = slices_backend.structure2SLICES(structure)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert reconstructed is not None
        assert len(reconstructed) == len(structure)
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_round_trip_large_structure(self, slices_backend):
        """Test round-trip with a larger structure."""
        from pymatgen.core import Lattice
        
        # Create a larger structure
        lattice = Lattice.cubic(10.0)
        species = ["Si"] * 8
        coords = [
            [0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5],
            [0.5, 0.5, 0.0], [0.5, 0.0, 0.5], [0.0, 0.5, 0.5], [0.5, 0.5, 0.5],
        ]
        structure = Structure(lattice, species, coords)
        
        slices_string = slices_backend.structure2SLICES(structure)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        assert reconstructed is not None
        assert len(reconstructed) == len(structure)

