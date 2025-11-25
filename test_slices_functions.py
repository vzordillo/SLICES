#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for structure2SLICES and SLICES2structure functions
using the mp-20 dataset.

This test suite validates:
1. structure2SLICES: Converting crystal structures to SLICES strings
2. SLICES2structure: Converting SLICES strings back to crystal structures
3. Round-trip accuracy: structure -> SLICES -> structure

Usage:
    python test_slices_functions.py --dataset data/mp20/test.csv --samples 50
"""

import os
import sys
import pandas as pd
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from slices.core import SLICES
import warnings
warnings.filterwarnings("ignore")

def parse_cif_from_csv_row(cif_string):
    """Parse CIF string from CSV row (handles escaped newlines)"""
    if pd.isna(cif_string):
        return None
    # Replace escaped newlines with actual newlines
    cif_string = str(cif_string).replace('\\n', '\n')
    # Remove any leading/trailing quotes if present
    if cif_string.startswith('"') and cif_string.endswith('"'):
        cif_string = cif_string[1:-1]
    return cif_string

def test_structure2slices(backend, structure, material_id):
    """Test structure2SLICES function"""
    try:
        slices_string = backend.structure2SLICES(structure)
        if slices_string and len(slices_string) > 0:
            return True, slices_string, None
        else:
            return False, None, "Empty SLICES string"
    except Exception as e:
        return False, None, str(e)

def test_slices2structure(backend, slices_string, original_structure, material_id):
    """Test SLICES2structure function"""
    try:
        result = backend.SLICES2structure(slices_string)
        
        # Handle different return formats
        if result is None:
            return False, None, None, "SLICES2structure returned None"
        
        # Check if it's a tuple/list
        if isinstance(result, (tuple, list)) and len(result) >= 2:
            reconstructed_structure, energy = result[0], result[1]
        elif isinstance(result, (tuple, list)) and len(result) == 1:
            reconstructed_structure = result[0]
            energy = None
        else:
            # Assume it's a single structure
            reconstructed_structure = result
            energy = None
        
        if reconstructed_structure is None:
            return False, None, None, "Reconstructed structure is None"
        
        # Check if structure is valid
        if len(reconstructed_structure) == 0:
            return False, None, None, "Reconstructed structure has no atoms"
        
        # Compare structures using StructureMatcher
        matcher = StructureMatcher()
        try:
            is_match = matcher.fit(original_structure, reconstructed_structure)
        except Exception as match_error:
            # If matching fails, check basic properties
            is_match = False
            # Try to get more info about why matching failed
            if "Could not obtain" in str(match_error) or "cocycle" in str(match_error).lower():
                return False, reconstructed_structure, energy, f"Structure matching failed: {str(match_error)[:100]}"
        
        return True, reconstructed_structure, energy, None if is_match else "Structure mismatch"
    except Exception as e:
        error_msg = str(e)
        # Truncate very long error messages
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        return False, None, None, error_msg

def test_round_trip(backend, structure, material_id, mlip_model):
    """Test complete round-trip: structure -> SLICES -> structure"""
    results = {
        'material_id': material_id,
        'mlip_model': mlip_model,
        'original_formula': structure.formula,
        'original_natoms': len(structure),
        'encode_success': False,
        'decode_success': False,
        'round_trip_success': False,
        'slices_string': None,
        'reconstructed_formula': None,
        'reconstructed_natoms': None,
        'energy_per_atom': None,
        'structure_match': False,
        'errors': []
    }
    
    # Test encoding
    encode_success, slices_string, encode_error = test_structure2slices(backend, structure, material_id)
    results['encode_success'] = encode_success
    results['slices_string'] = slices_string
    
    if not encode_success:
        results['errors'].append(f"Encoding failed: {encode_error}")
        return results
    
    # Test decoding
    reconstructed = None
    energy = None
    decode_success = False
    try:
        decode_success, reconstructed, energy, decode_error = test_slices2structure(
            backend, slices_string, structure, material_id
        )
        results['decode_success'] = decode_success
        results['energy_per_atom'] = energy
        
        if not decode_success:
            results['errors'].append(f"Decoding failed: {decode_error}")
            return results
    except Exception as e:
        results['decode_success'] = False
        results['errors'].append(f"Decoding exception: {str(e)[:100]}")
        return results
    
    if reconstructed is not None:
        results['reconstructed_formula'] = reconstructed.formula
        results['reconstructed_natoms'] = len(reconstructed)
    
    # Check round-trip success
    if encode_success and decode_success:
        # Use StructureMatcher for comparison
        matcher = StructureMatcher()
        try:
            is_match = matcher.fit(structure, reconstructed)
            results['structure_match'] = is_match
            results['round_trip_success'] = is_match
        except:
            # Fallback: check if formulas and atom counts match
            formulas_match = structure.formula == reconstructed.formula
            natoms_match = len(structure) == len(reconstructed)
            results['round_trip_success'] = formulas_match and natoms_match
            results['structure_match'] = results['round_trip_success']
    
    return results

def run_tests(dataset_path, num_samples=100, mlip_models=['chgnet', 'mattersim', 'orbv3']):
    """Run comprehensive tests on mp-20 dataset"""
    
    print("=" * 80)
    print("SLICES Functionality Test Suite")
    print("=" * 80)
    print(f"Dataset: {dataset_path}")
    print(f"Number of samples: {num_samples}")
    print(f"MLIP models to test: {', '.join(mlip_models)}")
    print()
    
    # Load dataset
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file {dataset_path} not found")
        return
    
    print("Loading dataset...")
    try:
        df = pd.read_csv(dataset_path)
        print(f"  ✓ Loaded {len(df)} structures from dataset")
    except Exception as e:
        print(f"  ✗ Failed to load dataset: {e}")
        return
    
    # Sample structures for testing
    if num_samples > len(df):
        num_samples = len(df)
        print(f"  ⚠ Requested {num_samples} samples, but only {len(df)} available")
    
    sample_indices = np.random.choice(len(df), size=num_samples, replace=False)
    df_sample = df.iloc[sample_indices]
    
    print(f"  ✓ Selected {num_samples} random samples for testing")
    print()
    
    all_results = []
    
    # Test each MLIP model
    for mlip_model in mlip_models:
        print(f"Testing with {mlip_model.upper()}...")
        print("-" * 80)
        
        try:
            backend = SLICES(relax_model=mlip_model)
            print(f"  ✓ {mlip_model.upper()} backend initialized")
        except Exception as e:
            print(f"  ✗ Failed to initialize {mlip_model.upper()}: {e}")
            continue
        
        model_results = []
        encode_successes = 0
        decode_successes = 0
        round_trip_successes = 0
        
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
                # Skip structures that can't be parsed
                continue
            
            # Test round-trip
            result = test_round_trip(backend, structure, material_id, mlip_model)
            model_results.append(result)
            all_results.append(result)
            
            if result['encode_success']:
                encode_successes += 1
            if result['decode_success']:
                decode_successes += 1
            if result['round_trip_success']:
                round_trip_successes += 1
            
            # Progress indicator
            if len(model_results) % 10 == 0:
                print(f"  Processed {len(model_results)}/{num_samples} structures...")
        
        # Print statistics for this model
        print()
        print(f"  {mlip_model.upper()} Results:")
        print(f"    Encoding success rate: {encode_successes}/{len(model_results)} ({100*encode_successes/len(model_results):.1f}%)")
        print(f"    Decoding success rate: {decode_successes}/{len(model_results)} ({100*decode_successes/len(model_results):.1f}%)")
        print(f"    Round-trip success rate: {round_trip_successes}/{len(model_results)} ({100*round_trip_successes/len(model_results):.1f}%)")
        
        if round_trip_successes > 0:
            successful_results = [r for r in model_results if r['round_trip_success']]
            avg_energy = np.mean([r['energy_per_atom'] for r in successful_results if r['energy_per_atom'] is not None])
            print(f"    Average energy per atom: {avg_energy:.4f} eV/atom")
        
        print()
    
    # Overall statistics
    print("=" * 80)
    print("Overall Test Summary")
    print("=" * 80)
    
    total_tests = len(all_results)
    total_encode_success = sum(1 for r in all_results if r['encode_success'])
    total_decode_success = sum(1 for r in all_results if r['decode_success'])
    total_round_trip_success = sum(1 for r in all_results if r['round_trip_success'])
    
    print(f"Total tests: {total_tests}")
    print(f"Encoding success: {total_encode_success}/{total_tests} ({100*total_encode_success/total_tests:.1f}%)")
    print(f"Decoding success: {total_decode_success}/{total_tests} ({100*total_decode_success/total_tests:.1f}%)")
    print(f"Round-trip success: {total_round_trip_success}/{total_tests} ({100*total_round_trip_success/total_tests:.1f}%)")
    
    # Error analysis
    failed_tests = [r for r in all_results if not r['round_trip_success']]
    if failed_tests:
        print(f"\nFailed tests: {len(failed_tests)}")
        error_types = {}
        for r in failed_tests:
            for error in r.get('errors', []):
                if error:
                    # Extract error type (first part before colon or first 50 chars)
                    if ':' in error:
                        error_type = error.split(':')[0].strip()
                    else:
                        error_type = error[:50].strip()
                    error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            print("Error breakdown:")
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {error_type}: {count}")
        
        # Show sample failed cases
        print(f"\nSample failed cases (first 3):")
        for i, r in enumerate(failed_tests[:3]):
            print(f"  {i+1}. {r.get('material_id', 'unknown')}: {r.get('original_formula', 'N/A')}")
            if r.get('errors'):
                print(f"     Errors: {', '.join(r['errors'][:2])}")
    
    print()
    print("=" * 80)
    
    if total_round_trip_success == total_tests:
        print("✓ All tests passed!")
        return 0
    elif total_round_trip_success / total_tests > 0.95:
        print(f"✓ {total_round_trip_success}/{total_tests} tests passed ({100*total_round_trip_success/total_tests:.1f}%)")
        return 0
    else:
        print(f"⚠ {total_round_trip_success}/{total_tests} tests passed ({100*total_round_trip_success/total_tests:.1f}%)")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SLICES functions with mp-20 dataset')
    parser.add_argument('--dataset', type=str, default='data/mp20/test.csv',
                       help='Path to dataset CSV file')
    parser.add_argument('--samples', type=int, default=50,
                       help='Number of samples to test (default: 50)')
    parser.add_argument('--models', type=str, nargs='+', 
                       default=['chgnet', 'mattersim', 'orbv3'],
                       help='MLIP models to test')
    
    args = parser.parse_args()
    
    sys.exit(run_tests(args.dataset, args.samples, args.models))

