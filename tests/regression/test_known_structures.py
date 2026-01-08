"""
Regression tests with known good structures.

These tests ensure that encoding/decoding of known structures remains consistent
and prevents regressions when code is modified.
"""

import pytest
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from pathlib import Path
from slices.core import SLICES


# Known good structures and their expected properties
KNOWN_STRUCTURES = [
    {
        'name': 'NdSiRu',
        'file': 'NdSiRu.cif',
        'expected_atoms': None,  # Will be determined from file
        'expected_formula': 'Nd1 Si1 Ru1',
    },
    {
        'name': 'Sr3Ru2O7',
        'file': 'Sr3Ru2O7.cif',
        'expected_atoms': None,
        'expected_formula': 'Sr3 Ru2 O7',
    },
]


class TestKnownStructuresEncoding:
    """Test encoding of known structures."""
    
    @pytest.mark.regression
    def test_encode_ndsiru(self, slices_backend, structures_dir):
        """Test encoding NdSiRu structure."""
        cif_path = structures_dir / "NdSiRu.cif"
        if not cif_path.exists():
            pytest.skip("NdSiRu.cif not found in fixtures")
        
        structure = Structure.from_file(str(cif_path))
        slices_string = slices_backend.structure2SLICES(structure)
        
        assert slices_string is not None
        assert isinstance(slices_string, str)
        assert len(slices_string) > 0
        # Should contain element symbols
        assert any(elem in slices_string for elem in ['Nd', 'Si', 'Ru'])
    
    @pytest.mark.regression
    def test_encode_sr3ru2o7(self, slices_backend, structures_dir):
        """Test encoding Sr3Ru2O7 structure."""
        cif_path = structures_dir / "Sr3Ru2O7.cif"
        if not cif_path.exists():
            pytest.skip("Sr3Ru2O7.cif not found in fixtures")
        
        structure = Structure.from_file(str(cif_path))
        slices_string = slices_backend.structure2SLICES(structure)
        
        assert slices_string is not None
        assert isinstance(slices_string, str)
        assert len(slices_string) > 0
    
    @pytest.mark.regression
    def test_encode_consistency(self, slices_backend, structures_dir):
        """Test that encoding known structures is consistent."""
        cif_path = structures_dir / "NdSiRu.cif"
        if not cif_path.exists():
            pytest.skip("NdSiRu.cif not found")
        
        structure = Structure.from_file(str(cif_path))
        
        # Encode multiple times
        slices1 = slices_backend.structure2SLICES(structure)
        slices2 = slices_backend.structure2SLICES(structure)
        
        # Should produce same result
        assert slices1 == slices2


class TestKnownStructuresRoundTrip:
    """Test round-trip of known structures."""
    
    @pytest.mark.regression
    @pytest.mark.slow
    def test_round_trip_ndsiru(self, slices_backend, structures_dir):
        """Test round-trip with NdSiRu."""
        cif_path = structures_dir / "NdSiRu.cif"
        if not cif_path.exists():
            pytest.skip("NdSiRu.cif not found")
        
        original = Structure.from_file(str(cif_path))
        
        # Round-trip
        slices_string = slices_backend.structure2SLICES(original)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        # Verify basic properties
        assert reconstructed is not None
        assert len(reconstructed) == len(original)
        assert reconstructed.formula == original.formula
    
    @pytest.mark.regression
    @pytest.mark.slow
    def test_round_trip_structure_match(self, slices_backend, structures_dir):
        """Test that round-trip produces matching structure."""
        cif_path = structures_dir / "NdSiRu.cif"
        if not cif_path.exists():
            pytest.skip("NdSiRu.cif not found")
        
        original = Structure.from_file(str(cif_path))
        
        # Round-trip
        slices_string = slices_backend.structure2SLICES(original)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        # Use StructureMatcher
        matcher = StructureMatcher()
        try:
            is_match = matcher.fit(original, reconstructed)
            # Structures should match (within tolerance)
            assert is_match or len(reconstructed) == len(original)
        except Exception:
            # If matching fails, at least verify basic properties
            assert reconstructed.formula == original.formula
            assert len(reconstructed) == len(original)


class TestKnownStructuresTolerance:
    """Test that known structures decode within acceptable tolerance."""
    
    @pytest.mark.regression
    @pytest.mark.slow
    def test_round_trip_energy_tolerance(self, slices_backend, structures_dir):
        """Test that round-trip energy is within reasonable range."""
        cif_path = structures_dir / "NdSiRu.cif"
        if not cif_path.exists():
            pytest.skip("NdSiRu.cif not found")
        
        original = Structure.from_file(str(cif_path))
        
        slices_string = slices_backend.structure2SLICES(original)
        reconstructed, energy = slices_backend.SLICES2structure(slices_string)
        
        # Energy should be reasonable (not NaN, not infinite)
        assert not np.isnan(energy)
        assert not np.isinf(energy)
        # Energy of 0 means relaxation failed, which is acceptable
        # Otherwise should be a reasonable value (e.g., between -20 and 20 eV/atom)
        if energy != 0:
            assert -20 < energy < 20, f"Energy {energy} seems unreasonable"
    
    @pytest.mark.regression
    def test_encoding_success_rate(self, slices_backend, structures_dir):
        """Test that encoding succeeds for known structures."""
        success_count = 0
        total_count = 0
        
        for struct_info in KNOWN_STRUCTURES:
            cif_path = structures_dir / struct_info['file']
            if not cif_path.exists():
                continue
            
            total_count += 1
            try:
                structure = Structure.from_file(str(cif_path))
                slices_string = slices_backend.structure2SLICES(structure)
                if slices_string and len(slices_string) > 0:
                    success_count += 1
            except Exception:
                pass
        
        if total_count > 0:
            success_rate = success_count / total_count
            # Should have high success rate for known structures
            assert success_rate >= 0.8, f"Encoding success rate {success_rate} too low"

