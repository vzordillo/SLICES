#!/usr/bin/env python3
"""
Test improved decoding on structures that previously failed.

This script extracts structures that failed in the original encoding
and tests them with both standard and robust decoding methods.

Usage:
    python scripts/tests/test_failed_structures.py --log docs/benchmarks/encode_decode_orbv3.log --dataset data/mp20/train.csv
"""

import argparse
import pandas as pd
import re
from pathlib import Path
import logging
from slices.core import SLICES, GraphTopologyError, LatticeBasisError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_failed_indices(log_file):
    """Extract row indices of failed structures from log file."""
    failed_indices = []
    
    with open(log_file, 'r') as f:
        for line in f:
            # Match "Error processing row X:"
            match = re.search(r'Error processing row (\d+):', line)
            if match:
                failed_indices.append(int(match.group(1)))
    
    return sorted(set(failed_indices))


def test_failed_structures(dataset_file, failed_indices, max_samples=None):
    """Test failed structures with both decoding methods."""
    logger.info(f"Loading dataset from {dataset_file}...")
    df = pd.read_csv(dataset_file)
    
    # Find CIF column
    cif_column = None
    if 'cif' in df.columns:
        cif_column = 'cif'
    else:
        cif_column = df.columns[-1]
    
    logger.info(f"Found {len(failed_indices)} failed structures")
    
    # Limit samples
    if max_samples:
        failed_indices = failed_indices[:max_samples]
        logger.info(f"Testing first {max_samples} failed structures...")
    
    # Initialize backends
    backend_standard = SLICES(relax_model="orbv3", check_results=False)
    backend_robust = SLICES(relax_model="orbv3", check_results=False)
    
    results = []
    
    for idx in failed_indices:
        if idx >= len(df):
            continue
        
        row = df.iloc[idx]
        cif_string = row[cif_column]
        
        if pd.isna(cif_string) or not str(cif_string).strip():
            continue
        
        # Encode to SLICES first
        try:
            slices_string = backend_standard.structure2SLICES(
                backend_standard.from_file(cif_string) if hasattr(backend_standard, 'from_file') 
                else None
            )
            # Actually, we need to use pymatgen Structure
            from pymatgen.core.structure import Structure
            structure = Structure.from_str(cif_string, fmt="cif")
            slices_string = backend_standard.structure2SLICES(structure)
        except Exception as e:
            logger.warning(f"Row {idx}: Failed to encode: {e}")
            continue
        
        # Test standard decoding
        standard_success = False
        standard_error = None
        try:
            decoded, energy = backend_standard.SLICES2structure(slices_string)
            standard_success = True
        except Exception as e:
            standard_error = type(e).__name__
        
        # Test robust decoding
        robust_success = False
        robust_error = None
        try:
            decoded, energy = backend_robust.robust_SLICES2structure(slices_string)
            robust_success = True
        except Exception as e:
            robust_error = type(e).__name__
        
        results.append({
            'original_index': idx,
            'standard_success': standard_success,
            'standard_error': standard_error,
            'robust_success': robust_success,
            'robust_error': robust_error,
            'improved': robust_success and not standard_success
        })
        
        if robust_success and not standard_success:
            logger.info(f"✓ Row {idx}: Robust decoding succeeded where standard failed!")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Test failed structures")
    parser.add_argument("--log", type=str, required=True, help="Log file with errors")
    parser.add_argument("--dataset", type=str, required=True, help="Dataset CSV file")
    parser.add_argument("--samples", type=int, default=50, help="Max samples to test")
    
    args = parser.parse_args()
    
    # Extract failed indices
    failed_indices = extract_failed_indices(args.log)
    logger.info(f"Extracted {len(failed_indices)} failed structure indices")
    
    # Test them
    results = test_failed_structures(args.dataset, failed_indices, args.samples)
    
    # Summary
    total = len(results)
    standard_success = sum(1 for r in results if r['standard_success'])
    robust_success = sum(1 for r in results if r['robust_success'])
    improved = sum(1 for r in results if r['improved'])
    
    logger.info("\n" + "="*60)
    logger.info("RESULTS")
    logger.info("="*60)
    logger.info(f"Total tested: {total}")
    logger.info(f"Standard success: {standard_success} ({standard_success/total*100:.1f}%)")
    logger.info(f"Robust success: {robust_success} ({robust_success/total*100:.1f}%)")
    logger.info(f"Improved by robust: {improved} structures")
    logger.info(f"Improvement: +{robust_success - standard_success} structures ({improved/total*100:.1f}%)")


if __name__ == "__main__":
    main()

