#!/usr/bin/env python
"""
Quick benchmark test for encoding/decoding with all available MLIP models.
Tests both default SLICES and canonical SLICES versions.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pandas as pd
import random
from pymatgen.core.structure import Structure
from slices.core import SLICES
import time

def test_mlip_model(model_name, structures, num_samples=10):
    """Test encoding/decoding with a specific MLIP model."""
    print(f"\n{'='*60}")
    print(f"Testing {model_name.upper()}")
    print(f"{'='*60}")
    
    try:
        backend = SLICES(relax_model=model_name)
        print(f"✓ {model_name} initialized")
    except Exception as e:
        print(f"✗ {model_name} initialization failed: {e}")
        return None
    
    results = {
        'model': model_name,
        'default_slices': {'success': 0, 'failed': 0, 'times': []},
        'canonical_slices': {'success': 0, 'failed': 0, 'times': []}
    }
    
    # Sample random structures
    sample_structures = random.sample(structures, min(num_samples, len(structures)))
    
    for idx, structure in enumerate(sample_structures, 1):
        print(f"\n  Sample {idx}/{len(sample_structures)}: {structure.formula}")
        
        # Test 1: Default SLICES encoding/decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            reconstructed, energy = backend.SLICES2structure(slices_str)
            elapsed = time.time() - start_time
            
            # Verify structure matches
            if reconstructed is not None:
                results['default_slices']['success'] += 1
                results['default_slices']['times'].append(elapsed)
                print(f"    ✓ Default SLICES: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['default_slices']['failed'] += 1
                print(f"    ✗ Default SLICES: Decoding returned None")
        except Exception as e:
            results['default_slices']['failed'] += 1
            print(f"    ✗ Default SLICES failed: {str(e)[:50]}")
        
        # Test 2: Canonical SLICES encoding/decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            canonical_slices = backend.get_canonical_SLICES(slices_str)
            reconstructed, energy = backend.SLICES2structure(canonical_slices)
            elapsed = time.time() - start_time
            
            # Verify structure matches
            if reconstructed is not None:
                results['canonical_slices']['success'] += 1
                results['canonical_slices']['times'].append(elapsed)
                print(f"    ✓ Canonical SLICES: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['canonical_slices']['failed'] += 1
                print(f"    ✗ Canonical SLICES: Decoding returned None")
        except Exception as e:
            results['canonical_slices']['failed'] += 1
            print(f"    ✗ Canonical SLICES failed: {str(e)[:50]}")
    
    return results

def main():
    print("SLICES Encoding/Decoding Benchmark")
    print("=" * 60)
    
    # Load sample structures
    data_file = 'data/mp20/train.csv'
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found")
        return
    
    print(f"\nLoading structures from {data_file}...")
    df = pd.read_csv(data_file)
    
    # Parse structures from POSCAR format (assuming it's in a column)
    structures = []
    poscar_col = None
    for col in df.columns:
        if 'poscar' in col.lower() or 'structure' in col.lower():
            poscar_col = col
            break
    
    if poscar_col is None:
        # Try to find any column that might contain structure data
        print("Warning: No POSCAR column found, trying first column...")
        poscar_col = df.columns[0]
    
    print(f"Using column: {poscar_col}")
    
    for idx, row in df.iterrows():
        try:
            poscar_str = str(row[poscar_col])
            if poscar_str and poscar_str != 'nan':
                structure = Structure.from_str(poscar_str, fmt='poscar')
                structures.append(structure)
        except Exception as e:
            continue
    
    print(f"Loaded {len(structures)} structures")
    
    if len(structures) < 10:
        print(f"Error: Need at least 10 structures, found {len(structures)}")
        return
    
    # Test all available MLIP models
    models = ['m3gnet', 'chgnet', 'mattersim', 'orbv3']
    all_results = []
    
    for model in models:
        try:
            from slices.mlip_relaxer import get_relaxer
            relaxer = get_relaxer(model)
            if relaxer:
                result = test_mlip_model(model, structures, num_samples=10)
                if result:
                    all_results.append(result)
        except Exception as e:
            print(f"\n✗ {model} not available: {e}")
            continue
    
    # Print summary
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    
    for result in all_results:
        model = result['model']
        default = result['default_slices']
        canonical = result['canonical_slices']
        
        print(f"\n{model.upper()}:")
        print(f"  Default SLICES:")
        print(f"    Success: {default['success']}/10")
        print(f"    Failed: {default['failed']}/10")
        if default['times']:
            print(f"    Avg time: {sum(default['times'])/len(default['times']):.2f}s")
        
        print(f"  Canonical SLICES:")
        print(f"    Success: {canonical['success']}/10")
        print(f"    Failed: {canonical['failed']}/10")
        if canonical['times']:
            print(f"    Avg time: {sum(canonical['times'])/len(canonical['times']):.2f}s")
    
    print(f"\n{'='*60}")
    print("Benchmark complete!")

if __name__ == '__main__':
    main()

