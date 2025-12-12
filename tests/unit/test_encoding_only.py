#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory-efficient test suite for structure2SLICES function only (encoding test)
This is a simpler test that focuses on verifying encoding works correctly.

Memory optimizations:
- Processes structures one at a time
- Uses single backend (reused)
- Clears results after batches
- Processes CSV in chunks
- Aggregates statistics instead of storing all results
"""

import os
import sys
import pandas as pd
import numpy as np
from pymatgen.core.structure import Structure
from slices.core import SLICES
import warnings
import gc
warnings.filterwarnings("ignore")

def parse_cif_from_csv_row(cif_string):
    """Parse CIF string from CSV row (handles escaped newlines)"""
    if pd.isna(cif_string):
        return None
    cif_string = str(cif_string).replace('\\n', '\n')
    if cif_string.startswith('"') and cif_string.endswith('"'):
        cif_string = cif_string[1:-1]
    return cif_string

def test_encoding(dataset_path, num_samples=100, batch_size=10):
    """Test structure2SLICES encoding on mp-20 dataset with memory-efficient processing"""
    
    print("=" * 80)
    print("SLICES Encoding Test (structure2SLICES) - Memory-Efficient")
    print("=" * 80)
    print(f"Dataset: {dataset_path}")
    print(f"Number of samples: {num_samples}")
    print(f"Batch size: {batch_size}")
    print()
    
    # Load dataset
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file {dataset_path} not found")
        return 1
    
    print("Loading dataset indices...")
    try:
        # Read only the columns we need
        df_full = pd.read_csv(dataset_path, usecols=['material_id', 'cif'])
        print(f"  ✓ Loaded {len(df_full)} structures from dataset")
    except Exception as e:
        print(f"  ✗ Failed to load dataset: {e}")
        return 1
    
    if num_samples > len(df_full):
        num_samples = len(df_full)
    
    sample_indices = np.random.choice(len(df_full), size=num_samples, replace=False)
    df_sample = df_full.iloc[sample_indices]
    
    # Clear full dataframe from memory
    del df_full
    gc.collect()
    
    print(f"  ✓ Selected {num_samples} random samples for testing")
    print()
    
    # Initialize SLICES backend
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
    
    # Statistics (aggregated, not stored per-structure)
    stats = {
        'total': 0,
        'successes': 0,
        'failures': 0,
        'slices_lengths': [],
        'errors': []
    }
    
    # Process structures in batches
    structures_batch = []
    batch_num = 0
    
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
        
        structures_batch.append((material_id, structure))
        
        # Process batch when it reaches batch_size
        if len(structures_batch) >= batch_size:
            batch_num += 1
            
            for material_id, structure in structures_batch:
                stats['total'] += 1
                
                try:
                    slices_string = backend.structure2SLICES(structure)
                    if slices_string and len(slices_string) > 0:
                        stats['successes'] += 1
                        stats['slices_lengths'].append(len(slices_string))
                    else:
                        stats['failures'] += 1
                        stats['errors'].append(f"{material_id}: Empty SLICES string")
                except Exception as e:
                    stats['failures'] += 1
                    stats['errors'].append(f"{material_id}: {str(e)[:100]}")
                
                # Clear structure reference
                del structure
                gc.collect()
            
            print(f"  Processed batch {batch_num} ({stats['total']}/{num_samples} structures)... "
                  f"(Success: {stats['successes']}, Failed: {stats['failures']})")
            
            # Clear batch
            structures_batch = []
            gc.collect()
    
    # Process remaining structures
    if structures_batch:
        batch_num += 1
        
        for material_id, structure in structures_batch:
            stats['total'] += 1
            
            try:
                slices_string = backend.structure2SLICES(structure)
                if slices_string and len(slices_string) > 0:
                    stats['successes'] += 1
                    stats['slices_lengths'].append(len(slices_string))
                else:
                    stats['failures'] += 1
                    stats['errors'].append(f"{material_id}: Empty SLICES string")
            except Exception as e:
                stats['failures'] += 1
                stats['errors'].append(f"{material_id}: {str(e)[:100]}")
            
            # Clear structure reference
            del structure
            gc.collect()
        
        print(f"  Processed final batch ({stats['total']}/{num_samples} structures)...")
        structures_batch = []
        gc.collect()
    
    # Clear backend
    del backend
    gc.collect()
    
    # Print summary
    print()
    print("=" * 80)
    print("Encoding Test Summary")
    print("=" * 80)
    print(f"Total structures tested: {stats['total']}")
    if stats['total'] > 0:
        print(f"Successful encodings: {stats['successes']}/{stats['total']} "
              f"({100*stats['successes']/stats['total']:.1f}%)")
        print(f"Failed encodings: {stats['failures']}/{stats['total']} "
              f"({100*stats['failures']/stats['total']:.1f}%)")
        
        if stats['successes'] > 0 and stats['slices_lengths']:
            avg_slices_length = np.mean(stats['slices_lengths'])
            print(f"Average SLICES string length: {avg_slices_length:.1f} characters")
        
        if stats['failures'] > 0 and stats['errors']:
            print(f"\nFailed cases (first 5):")
            for i, error in enumerate(stats['errors'][:5]):
                print(f"  {i+1}. {error}")
    
    print()
    print("=" * 80)
    
    if stats['total'] == 0:
        print("⚠ No structures were tested")
        return 1
    elif stats['successes'] == stats['total']:
        print("✓ All encoding tests passed!")
        return 0
    elif stats['successes'] / stats['total'] > 0.95:
        print(f"✓ {stats['successes']}/{stats['total']} encoding tests passed "
              f"({100*stats['successes']/stats['total']:.1f}%)")
        return 0
    else:
        print(f"⚠ {stats['successes']}/{stats['total']} encoding tests passed "
              f"({100*stats['successes']/stats['total']:.1f}%)")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test structure2SLICES encoding with mp-20 dataset (memory-efficient)')
    parser.add_argument('--dataset', type=str, default='data/mp20/test.csv',
                       help='Path to dataset CSV file')
    parser.add_argument('--samples', type=int, default=100,
                       help='Number of samples to test (default: 100)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Batch size for processing structures (default: 10, lower = less memory)')
    
    args = parser.parse_args()
    
    sys.exit(test_encoding(args.dataset, args.samples, args.batch_size))
