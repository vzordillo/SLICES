#!/usr/bin/env python3
"""
Benchmark test for encoding/decoding with all available MLIP models.
Tests default SLICES, canonical SLICES, standard decoding, and robust decoding.
"""

import sys
import os
import json
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import pandas as pd
import random
from pymatgen.core.structure import Structure
from slices.core import SLICES
import time

def test_mlip_model(model_name, sample_structures):
    """Test encoding/decoding with a specific MLIP model using pre-sampled structures."""
    print(f"\n{'='*70}")
    print(f"Testing {model_name.upper()}")
    print(f"{'='*70}")
    
    try:
        backend = SLICES(relax_model=model_name)
        print(f"✓ {model_name} initialized successfully")
    except Exception as e:
        print(f"✗ {model_name} initialization failed: {e}")
        return None
    
    results = {
        'model': model_name,
        'default_standard': {'success': 0, 'failed': 0, 'times': [], 'errors': []},
        'default_robust': {'success': 0, 'failed': 0, 'times': [], 'errors': []},
        'canonical_standard': {'success': 0, 'failed': 0, 'times': [], 'errors': []},
        'canonical_robust': {'success': 0, 'failed': 0, 'times': [], 'errors': []}
    }
    
    print(f"Testing {len(sample_structures)} structures...\n")
    
    for idx, structure in enumerate(sample_structures, 1):
        formula = structure.formula
        if idx % 10 == 0 or idx == 1:
            print(f"  Sample {idx}/{len(sample_structures)}: {formula}")
        
        # Test 1: Default SLICES with standard decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            reconstructed, energy = backend.SLICES2structure(slices_str)
            elapsed = time.time() - start_time
            
            if reconstructed is not None and energy is not None:
                results['default_standard']['success'] += 1
                results['default_standard']['times'].append(elapsed)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✓ Default+Standard: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['default_standard']['failed'] += 1
                error_msg = "Decoding returned None"
                results['default_standard']['errors'].append(error_msg)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✗ Default+Standard: {error_msg}")
        except Exception as e:
            results['default_standard']['failed'] += 1
            error_msg = str(e)[:60]
            results['default_standard']['errors'].append(error_msg)
            if idx % 10 == 0 or idx == 1:
                print(f"    ✗ Default+Standard failed: {error_msg}")
        
        # Test 2: Default SLICES with robust decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            reconstructed, energy = backend.robust_SLICES2structure(slices_str)
            elapsed = time.time() - start_time
            
            if reconstructed is not None and energy is not None:
                results['default_robust']['success'] += 1
                results['default_robust']['times'].append(elapsed)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✓ Default+Robust: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['default_robust']['failed'] += 1
                error_msg = "Decoding returned None"
                results['default_robust']['errors'].append(error_msg)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✗ Default+Robust: {error_msg}")
        except Exception as e:
            results['default_robust']['failed'] += 1
            error_msg = str(e)[:60]
            results['default_robust']['errors'].append(error_msg)
            if idx % 10 == 0 or idx == 1:
                print(f"    ✗ Default+Robust failed: {error_msg}")
        
        # Test 3: Canonical SLICES with standard decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            canonical_slices = backend.get_canonical_SLICES(slices_str)
            reconstructed, energy = backend.SLICES2structure(canonical_slices)
            elapsed = time.time() - start_time
            
            if reconstructed is not None and energy is not None:
                results['canonical_standard']['success'] += 1
                results['canonical_standard']['times'].append(elapsed)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✓ Canonical+Standard: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['canonical_standard']['failed'] += 1
                error_msg = "Decoding returned None"
                results['canonical_standard']['errors'].append(error_msg)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✗ Canonical+Standard: {error_msg}")
        except Exception as e:
            results['canonical_standard']['failed'] += 1
            error_msg = str(e)[:60]
            results['canonical_standard']['errors'].append(error_msg)
            if idx % 10 == 0 or idx == 1:
                print(f"    ✗ Canonical+Standard failed: {error_msg}")
        
        # Test 4: Canonical SLICES with robust decoding
        try:
            start_time = time.time()
            slices_str = backend.structure2SLICES(structure)
            canonical_slices = backend.get_canonical_SLICES(slices_str)
            reconstructed, energy = backend.robust_SLICES2structure(canonical_slices)
            elapsed = time.time() - start_time
            
            if reconstructed is not None and energy is not None:
                results['canonical_robust']['success'] += 1
                results['canonical_robust']['times'].append(elapsed)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✓ Canonical+Robust: {elapsed:.2f}s, Energy: {energy:.4f} eV/atom")
            else:
                results['canonical_robust']['failed'] += 1
                error_msg = "Decoding returned None"
                results['canonical_robust']['errors'].append(error_msg)
                if idx % 10 == 0 or idx == 1:
                    print(f"    ✗ Canonical+Robust: {error_msg}")
        except Exception as e:
            results['canonical_robust']['failed'] += 1
            error_msg = str(e)[:60]
            results['canonical_robust']['errors'].append(error_msg)
            if idx % 10 == 0 or idx == 1:
                print(f"    ✗ Canonical+Robust failed: {error_msg}")
    
    return results

def main():
    print("=" * 70)
    print("SLICES Encoding/Decoding Benchmark - All MLIP Models")
    print("Standard vs Robust Decoding Comparison")
    print("=" * 70)
    
    # Load sample structures from train.csv
    data_file = 'data/mp20/train.csv'
    if not os.path.exists(data_file):
        print(f"Error: {data_file} not found")
        return
    
    print(f"\nLoading structures from {data_file}...")
    df = pd.read_csv(data_file)
    
    # Find CIF column (usually last column or named 'cif')
    cif_col = None
    if 'cif' in df.columns:
        cif_col = 'cif'
    else:
        # Assume last column contains CIF
        cif_col = df.columns[-1]
    
    print(f"Using column: {cif_col}")
    
    # Parse structures from CIF format
    structures = []
    for idx, row in df.iterrows():
        try:
            cif_str = str(row[cif_col])
            if cif_str and cif_str != 'nan' and cif_str.strip():
                structure = Structure.from_str(cif_str, fmt='cif')
                structures.append(structure)
        except Exception as e:
            continue
    
    print(f"Loaded {len(structures)} structures")
    
    if len(structures) < 20:
        print(f"Error: Need at least 20 structures, found {len(structures)}")
        return
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Sample 20 random structures once - same samples for all models
    num_samples = 20
    sample_structures = random.sample(structures, min(num_samples, len(structures)))
    print(f"\nSelected {len(sample_structures)} random structures for all benchmarks")
    print(f"Sample formulas: {', '.join([s.formula for s in sample_structures[:5]])}...")
    
    # Test all available MLIP models with the same samples
    models = ['m3gnet', 'chgnet', 'mattersim', 'orbv3']
    all_results = []
    
    for model in models:
        try:
            from slices.mlip_relaxer import get_relaxer
            relaxer = get_relaxer(model)
            if relaxer:
                result = test_mlip_model(model, sample_structures)
                if result:
                    all_results.append(result)
        except Exception as e:
            print(f"\n✗ {model} not available: {e}")
            continue
    
    # Print summary
    print(f"\n{'='*70}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*70}")
    
    for result in all_results:
        model = result['model']
        default_std = result['default_standard']
        default_rob = result['default_robust']
        canonical_std = result['canonical_standard']
        canonical_rob = result['canonical_robust']
        
        num_samples = len(sample_structures)
        print(f"\n{model.upper()}:")
        print(f"  Default SLICES:")
        print(f"    Standard decoding: {default_std['success']}/{num_samples} ({default_std['success']*100//num_samples}%)")
        print(f"    Robust decoding:  {default_rob['success']}/{num_samples} ({default_rob['success']*100//num_samples}%)")
        if default_std['times']:
            avg_time = sum(default_std['times']) / len(default_std['times'])
            print(f"    Standard avg time: {avg_time:.2f}s")
        if default_rob['times']:
            avg_time = sum(default_rob['times']) / len(default_rob['times'])
            print(f"    Robust avg time:  {avg_time:.2f}s")
        improvement = default_rob['success'] - default_std['success']
        if improvement > 0:
            print(f"    Robust improvement: +{improvement} structures ({improvement*100//num_samples}%)")
        
        print(f"  Canonical SLICES:")
        print(f"    Standard decoding: {canonical_std['success']}/{num_samples} ({canonical_std['success']*100//num_samples}%)")
        print(f"    Robust decoding:  {canonical_rob['success']}/{num_samples} ({canonical_rob['success']*100//num_samples}%)")
        if canonical_std['times']:
            avg_time = sum(canonical_std['times']) / len(canonical_std['times'])
            print(f"    Standard avg time: {avg_time:.2f}s")
        if canonical_rob['times']:
            avg_time = sum(canonical_rob['times']) / len(canonical_rob['times'])
            print(f"    Robust avg time:  {avg_time:.2f}s")
        improvement = canonical_rob['success'] - canonical_std['success']
        if improvement > 0:
            print(f"    Robust improvement: +{improvement} structures ({improvement*100//num_samples}%)")
        
        # Show unique errors if any
        if default_std['errors']:
            unique_errors = list(set(default_std['errors']))[:2]
            print(f"    Standard errors: {', '.join(unique_errors)}")
        if default_rob['errors']:
            unique_errors = list(set(default_rob['errors']))[:2]
            print(f"    Robust errors: {', '.join(unique_errors)}")
    
    # Overall comparison
    print(f"\n{'='*70}")
    print("OVERALL COMPARISON: Standard vs Robust Decoding")
    print(f"{'='*70}")
    
    for result in all_results:
        model = result['model']
        default_std = result['default_standard']
        default_rob = result['default_robust']
        canonical_std = result['canonical_standard']
        canonical_rob = result['canonical_robust']
        
        num_samples = len(sample_structures)
        total_std = default_std['success'] + canonical_std['success']
        total_rob = default_rob['success'] + canonical_rob['success']
        improvement = total_rob - total_std
        total_tests = num_samples * 2  # default + canonical
        
        print(f"{model.upper()}:")
        print(f"  Standard: {total_std}/{total_tests} ({total_std*100//total_tests}%)")
        print(f"  Robust:  {total_rob}/{total_tests} ({total_rob*100//total_tests}%)")
        if improvement > 0:
            print(f"  Improvement: +{improvement} structures ({improvement*100//total_tests}%)")
    
    print(f"\n{'='*70}")
    print("Benchmark complete!")
    print(f"{'='*70}")
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.path.dirname(__file__), '../../benchmark/results/reports')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'mlip_benchmark_{timestamp}.json')
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'num_samples': len(sample_structures),
            'sample_formulas': [s.formula for s in sample_structures],
            'results': all_results
        }, f, indent=2, default=str)
    
    print(f"\nResults saved to: {output_file}")
    
    return all_results, output_file

if __name__ == '__main__':
    main()

