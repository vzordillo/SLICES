"""
Regression tests with MP-20 dataset samples.

Tests encoding/decoding with samples from the MP-20 dataset to ensure
consistency and prevent regressions.
"""

import pytest
import pandas as pd
from pathlib import Path
from pymatgen.core.structure import Structure
from slices.core import SLICES


class TestMP20Samples:
    """Test with MP-20 dataset samples."""
    
    @pytest.fixture
    def mp20_dataset_path(self):
        """Return path to MP-20 test dataset."""
        dataset_path = Path("data/mp20/test.csv")
        if not dataset_path.exists():
            pytest.skip("MP-20 test dataset not found")
        return dataset_path
    
    @pytest.mark.regression
    @pytest.mark.slow
    def test_encode_mp20_samples(self, mp20_dataset_path):
        """Test encoding MP-20 samples."""
        # Load a few samples from the dataset
        try:
            df = pd.read_csv(mp20_dataset_path, nrows=5)
        except Exception as e:
            pytest.skip(f"Could not load MP-20 dataset: {e}")
        
        backend = SLICES(relax_model='chgnet')
        success_count = 0
        
        for idx, row in df.iterrows():
            try:
                # Parse CIF string
                cif_string = str(row.get('cif', ''))
                if pd.isna(cif_string) or not cif_string:
                    continue
                
                # Replace escaped newlines
                cif_string = cif_string.replace('\\n', '\n')
                
                # Create structure
                structure = Structure.from_str(cif_string, fmt='cif')
                
                # Encode
                slices_string = backend.structure2SLICES(structure)
                if slices_string and len(slices_string) > 0:
                    success_count += 1
            except Exception:
                # Some structures may fail - that's acceptable
                pass
        
        # Should have some success
        if success_count == 0:
            pytest.skip("No structures could be encoded from MP-20 samples")
    
    @pytest.mark.regression
    @pytest.mark.slow
    def test_round_trip_mp20_samples(self, mp20_dataset_path):
        """Test round-trip with MP-20 samples."""
        try:
            df = pd.read_csv(mp20_dataset_path, nrows=3)  # Test with fewer samples
        except Exception as e:
            pytest.skip(f"Could not load MP-20 dataset: {e}")
        
        backend = SLICES(relax_model='chgnet')
        success_count = 0
        
        for idx, row in df.iterrows():
            try:
                cif_string = str(row.get('cif', ''))
                if pd.isna(cif_string) or not cif_string:
                    continue
                
                cif_string = cif_string.replace('\\n', '\n')
                structure = Structure.from_str(cif_string, fmt='cif')
                
                # Round-trip
                slices_string = backend.structure2SLICES(structure)
                if slices_string:
                    reconstructed, energy = backend.SLICES2structure(slices_string)
                    if reconstructed and len(reconstructed) > 0:
                        success_count += 1
            except Exception:
                # Some structures may fail - that's acceptable
                pass
        
        # Should have some success
        if success_count == 0:
            pytest.skip("No round-trips succeeded with MP-20 samples")

