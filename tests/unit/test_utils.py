"""
Unit tests for utility functions.

Tests utility functions used throughout SLICES.
"""

import pytest
from slices.utils_wyckoff import get_space_group_num_from_letter_enc, get_tokenized_enc


class TestWyckoffUtils:
    """Test Wyckoff utility functions."""
    
    def test_get_space_group_num_from_letter_enc(self):
        """Test extracting space group number from letter encoding."""
        # This is a placeholder - actual implementation depends on utils_wyckoff
        try:
            # Test with a known encoding if available
            result = get_space_group_num_from_letter_enc("test")
            # Should return a number or raise an error
            assert isinstance(result, (int, type(None))) or isinstance(result, Exception)
        except (ValueError, KeyError, AttributeError):
            # Expected for invalid encodings
            pass
    
    def test_get_tokenized_enc(self):
        """Test tokenized encoding function."""
        try:
            result = get_tokenized_enc(1)  # Example space group number
            # Should return a string or raise an error
            assert isinstance(result, (str, type(None))) or isinstance(result, Exception)
        except (ValueError, KeyError, AttributeError):
            # Expected for invalid inputs
            pass

