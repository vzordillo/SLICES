#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for structure2SLICES function only (encoding test)
This is a simpler test that focuses on verifying encoding works correctly.
"""

import os
import sys
import pandas as pd
import numpy as np
from pymatgen.core.structure import Structure
from slices.core import SLICES
import warnings
warnings.filterwarnings("ignore")

def parse_cif_from_csv_row(cif_string):
    """Parse CIF string from CSV row (handles escaped newlines)"""
    if pd.isna(cif_string):
        return None
    cif_string = str(cif_string).replace('\\n', '\n')
    if cif_string.startswith('"') and cif_string.endswith('"'):
        cif_string = cif_string[1:-1]
    return cif_string

def test_encoding(dataset_path, num_samples=100):
    """Test structure2SLICES encoding on mp-20 dataset"""
    
    print("=" * 80)
    print("SLICES Encoding Test (structure2SLICES)")
    print("=" * 80)
    print(f"Dataset: {dataset_path}")
    print(f"Number of samples: {num_samples}")
    print()
    
    # Load dataset
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file {dataset_path} not found")
        return 1
    
    print("Loading dataset...")
    try:
        df = pd.read_csv(dataset_path)
        print(f"  ✓ Loaded {len(df)} structures from dataset")
    except Exception as e:
        print(f"  ✗ Failed to load dataset: {e}")
        return 1
    
    if num_samples > len(df):
        num_samples = len(df)
    
    sample_indices = np.random.choice(len(df), size=num_samples, replace=False)
    df_sample = df.iloc[sample_indices]
    
    print(f"  ✓ Selected {num_samples} random samples for testing")
    print()
    
    # Initialize SLICES backend (use CHGNet to avoid M3GNet issues)
    print("Initializing SLICES backend...")
    try:
        backend = SLICES(relax_model="chgnet")
        print("  ✓ SLICES backend initialized (using CHGNet)")
    except Exception as e:
        print(f"  ✗ Failed to initialize SLICES: {e}")
        return 1
    
    print()
    print("Testing encoding...")
    print("-" * 80)
    
    results = []
    successes = 0
    failures = 0
    
    for idx, row in df_sample.iterrows():
        material_id = row.get('material_id', f'unknown_{idx}')
        cif_string = row.get('cif', '')
        
        if not cif_string or pd.isna(cif_string):
            continue
        
        try:
            # Parse CIF string
            cif_string = parse_cif_from_csv_row(cif_string)
            if cif_string is None or len(cif_string.strip()) == 0:
                continue
            structure = Structure.from_str(cif_string, fmt='cif')
            if len(structure) == 0:
                continue
        except Exception as e:
            continue
        
        # Test encoding
        try:
            slices_string = backend.structure2SLICES(structure)
            if slices_string and len(slices_string) > 0:
                successes += 1
                results.append({
                    'material_id': material_id,
                    'formula': structure.formula,
                    'natoms': len(structure),
                    'slices_length': len(slices_string),
                    'success': True
                })
            else:
                failures += 1
                results.append({
                    'material_id': material_id,
                    'formula': structure.formula,
                    'natoms': len(structure),
                    'success': False,
                    'error': 'Empty SLICES string'
                })
        except Exception as e:
            failures += 1
            results.append({
                'material_id': material_id,
                'formula': structure.formula,
                'natoms': len(structure),
                'success': False,
                'error': str(e)[:100]
            })
        
        if (successes + failures) % 10 == 0:
            print(f"  Processed {successes + failures} structures... (Success: {successes}, Failed: {failures})")
    
    # Print summary
    print()
    print("=" * 80)
    print("Encoding Test Summary")
    print("=" * 80)
    print(f"Total structures tested: {len(results)}")
    print(f"Successful encodings: {successes}/{len(results)} ({100*successes/len(results):.1f}%)")
    print(f"Failed encodings: {failures}/{len(results)} ({100*failures/len(results):.1f}%)")
    
    if successes > 0:
        successful_results = [r for r in results if r['success']]
        avg_slices_length = np.mean([r['slices_length'] for r in successful_results])
        print(f"Average SLICES string length: {avg_slices_length:.1f} characters")
    
    if failures > 0:
        failed_results = [r for r in results if not r['success']]
        print(f"\nFailed cases (first 5):")
        for i, r in enumerate(failed_results[:5]):
            print(f"  {i+1}. {r['material_id']}: {r['formula']} - {r.get('error', 'Unknown error')}")
    
    print()
    print("=" * 80)
    
    if successes == len(results):
        print("✓ All encoding tests passed!")
        return 0
    elif successes / len(results) > 0.95:
        print(f"✓ {successes}/{len(results)} encoding tests passed ({100*successes/len(results):.1f}%)")
        return 0
    else:
        print(f"⚠ {successes}/{len(results)} encoding tests passed ({100*successes/len(results):.1f}%)")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test structure2SLICES encoding with mp-20 dataset')
    parser.add_argument('--dataset', type=str, default='data/mp20/test.csv',
                       help='Path to dataset CSV file')
    parser.add_argument('--samples', type=int, default=100,
                       help='Number of samples to test (default: 100)')
    
    args = parser.parse_args()
    
    sys.exit(test_encoding(args.dataset, args.samples))

