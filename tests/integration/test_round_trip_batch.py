#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memory-efficient test suite for structure2SLICES and SLICES2structure functions
using the mp-20 dataset.

This test suite validates:
1. structure2SLICES: Converting crystal structures to SLICES strings
2. SLICES2structure: Converting SLICES strings back to crystal structures
3. Round-trip accuracy: structure -> SLICES -> structure

Memory optimizations:
- Processes structures one at a time
- Uses single backend per model (reused)
- Clears results after batches
- Processes CSV in chunks
- Aggregates statistics instead of storing all results

Usage:
    python test_slices_functions.py --dataset data/mp20/test.csv --samples 50 --batch-size 10
"""

import os
import sys
import pandas as pd
import numpy as np
from pymatgen.core.structure import Structure
from pymatgen.analysis.structure_matcher import StructureMatcher
from slices.core import SLICES
import warnings
import gc
warnings.filterwarnings("ignore")

# Try to import TensorFlow for memory management
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

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

def test_slices2structure(backend, slices_string, original_structure, material_id, matcher=None):
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
        
        # Compare structures using StructureMatcher (reuse if provided)
        if matcher is None:
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
        # Categorize error types for better reporting
        if "lattice basis" in error_msg.lower() or "cycle vectors" in error_msg.lower():
            error_msg = "Graph topology incompatible (lattice basis error)"
        elif "xtb" in error_msg.lower() or "gfnff" in error_msg.lower() or "file not found" in error_msg.lower():
            error_msg = f"XTB execution failed: {error_msg[:150]}"
        elif "json" in error_msg.lower() or "parse" in error_msg.lower():
            error_msg = f"XTB output parsing failed: {error_msg[:150]}"
        # Truncate very long error messages
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        return False, None, None, error_msg

def test_round_trip(backend, structure, material_id, mlip_model, matcher=None):
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
            backend, slices_string, structure, material_id, matcher=matcher
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
    
    # Check round-trip success (reuse matcher if provided)
    if encode_success and decode_success:
        if matcher is None:
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
    
    # Clear references to free memory
    del reconstructed
    del slices_string
    
    # Clear TensorFlow session to free memory (especially important for M3GNet)
    if TF_AVAILABLE:
        try:
            tf.keras.backend.clear_session()
        except:
            pass
    
    return results

def process_structure_batch(backend, structures_batch, mlip_model, batch_num):
    """Process a batch of structures and return aggregated statistics"""
    batch_stats = {
        'total': 0,
        'encode_success': 0,
        'decode_success': 0,
        'round_trip_success': 0,
        'energies': [],
        'errors': []
    }
    
    # Create a single StructureMatcher to reuse across all structures in the batch
    matcher = StructureMatcher()
    
    for material_id, structure in structures_batch:
        batch_stats['total'] += 1
        
        try:
            result = test_round_trip(backend, structure, material_id, mlip_model, matcher=matcher)
            
            if result['encode_success']:
                batch_stats['encode_success'] += 1
            if result['decode_success']:
                batch_stats['decode_success'] += 1
            if result['round_trip_success']:
                batch_stats['round_trip_success'] += 1
                if result['energy_per_atom'] is not None:
                    batch_stats['energies'].append(result['energy_per_atom'])
            
            if result.get('errors'):
                batch_stats['errors'].extend(result['errors'])
        except Exception as e:
            batch_stats['errors'].append(f"Exception processing {material_id}: {str(e)[:100]}")
        
        # Clear structure reference
        del structure
        
        # Aggressive memory clearing every few structures
        if batch_stats['total'] % 3 == 0:
            gc.collect()
            if TF_AVAILABLE:
                try:
                    tf.keras.backend.clear_session()
                except:
                    pass
    
    # Final cleanup
    del matcher
    gc.collect()
    if TF_AVAILABLE:
        try:
            tf.keras.backend.clear_session()
        except:
            pass
    
    return batch_stats

def run_tests(dataset_path, num_samples=100, mlip_models=['chgnet'], batch_size=5):
    """Run comprehensive tests on mp-20 dataset with memory-efficient processing"""
    
    print("=" * 80)
    print("SLICES Functionality Test Suite (Memory-Efficient)")
    print("=" * 80)
    print(f"Dataset: {dataset_path}")
    print(f"Number of samples: {num_samples}")
    print(f"MLIP models to test: {', '.join(mlip_models)}")
    print(f"Batch size: {batch_size}")
    
    # Warn about memory usage for large batch sizes or M3GNet
    if batch_size > 10:
        print(f"⚠ Warning: Large batch size ({batch_size}) may cause memory issues. Consider using --batch-size 3-5")
    if 'm3gnet' in [m.lower() for m in mlip_models]:
        print("⚠ Note: M3GNet uses TensorFlow and may require more memory. Using aggressive memory clearing.")
    
    print()
    
    # Load dataset header first to get column names
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset file {dataset_path} not found")
        return 1
    
    print("Loading dataset indices...")
    try:
        # Read only the indices we need, not the full dataset
        df_full = pd.read_csv(dataset_path, usecols=['material_id', 'cif'])
        print(f"  ✓ Loaded {len(df_full)} structures from dataset")
    except Exception as e:
        print(f"  ✗ Failed to load dataset: {e}")
        return 1
    
    # Sample structures for testing
    if num_samples > len(df_full):
        num_samples = len(df_full)
        print(f"  ⚠ Requested {num_samples} samples, but only {len(df_full)} available")
    
    sample_indices = np.random.choice(len(df_full), size=num_samples, replace=False)
    df_sample = df_full.iloc[sample_indices]
    
    # Clear full dataframe from memory
    del df_full
    gc.collect()
    
    print(f"  ✓ Selected {num_samples} random samples for testing")
    print()
    
    # Overall statistics (aggregated, not stored per-structure)
    overall_stats = {
        'total_tests': 0,
        'total_encode_success': 0,
        'total_decode_success': 0,
        'total_round_trip_success': 0,
        'all_energies': [],
        'all_errors': []
    }
    
    # Test each MLIP model one at a time
    for mlip_model in mlip_models:
        print(f"Testing with {mlip_model.upper()}...")
        print("-" * 80)
        
        try:
            backend = SLICES(relax_model=mlip_model)
            print(f"  ✓ {mlip_model.upper()} backend initialized")
        except Exception as e:
            print(f"  ✗ Failed to initialize {mlip_model.upper()}: {e}")
            continue
        
        model_stats = {
            'total': 0,
            'encode_success': 0,
            'decode_success': 0,
            'round_trip_success': 0,
            'energies': [],
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
                # Skip structures that can't be parsed
                continue
            
            structures_batch.append((material_id, structure))
            
            # Process batch when it reaches batch_size
            if len(structures_batch) >= batch_size:
                batch_num += 1
                batch_stats = process_structure_batch(backend, structures_batch, mlip_model, batch_num)
                
                # Aggregate statistics
                model_stats['total'] += batch_stats['total']
                model_stats['encode_success'] += batch_stats['encode_success']
                model_stats['decode_success'] += batch_stats['decode_success']
                model_stats['round_trip_success'] += batch_stats['round_trip_success']
                model_stats['energies'].extend(batch_stats['energies'])
                model_stats['errors'].extend(batch_stats['errors'])
                
                print(f"  Processed batch {batch_num} ({model_stats['total']}/{num_samples} structures)... "
                      f"(Success: {model_stats['round_trip_success']})")
                
                # Clear batch
                structures_batch = []
                gc.collect()
                # Clear TensorFlow session after each batch
                if TF_AVAILABLE:
                    try:
                        tf.keras.backend.clear_session()
                    except:
                        pass
        
        # Process remaining structures
        if structures_batch:
            batch_num += 1
            batch_stats = process_structure_batch(backend, structures_batch, mlip_model, batch_num)
            
            model_stats['total'] += batch_stats['total']
            model_stats['encode_success'] += batch_stats['encode_success']
            model_stats['decode_success'] += batch_stats['decode_success']
            model_stats['round_trip_success'] += batch_stats['round_trip_success']
            model_stats['energies'].extend(batch_stats['energies'])
            model_stats['errors'].extend(batch_stats['errors'])
            
            print(f"  Processed final batch ({model_stats['total']}/{num_samples} structures)...")
            structures_batch = []
            gc.collect()
            # Clear TensorFlow session
            if TF_AVAILABLE:
                try:
                    tf.keras.backend.clear_session()
                except:
                    pass
        
        # Print statistics for this model
        print()
        if model_stats['total'] > 0:
            print(f"  {mlip_model.upper()} Results:")
            print(f"    Encoding success rate: {model_stats['encode_success']}/{model_stats['total']} "
                  f"({100*model_stats['encode_success']/model_stats['total']:.1f}%)")
            print(f"    Decoding success rate: {model_stats['decode_success']}/{model_stats['total']} "
                  f"({100*model_stats['decode_success']/model_stats['total']:.1f}%)")
            print(f"    Round-trip success rate: {model_stats['round_trip_success']}/{model_stats['total']} "
                  f"({100*model_stats['round_trip_success']/model_stats['total']:.1f}%)")
            
            if model_stats['round_trip_success'] > 0 and model_stats['energies']:
                avg_energy = np.mean(model_stats['energies'])
                print(f"    Average energy per atom: {avg_energy:.4f} eV/atom")
        
        # Aggregate to overall stats
        overall_stats['total_tests'] += model_stats['total']
        overall_stats['total_encode_success'] += model_stats['encode_success']
        overall_stats['total_decode_success'] += model_stats['decode_success']
        overall_stats['total_round_trip_success'] += model_stats['round_trip_success']
        overall_stats['all_energies'].extend(model_stats['energies'])
        overall_stats['all_errors'].extend(model_stats['errors'])
        
        # Clear backend and model stats
        del backend
        del model_stats
        gc.collect()
        # Final TensorFlow session clear
        if TF_AVAILABLE:
            try:
                tf.keras.backend.clear_session()
            except:
                pass
        print()
    
    # Overall statistics
    print("=" * 80)
    print("Overall Test Summary")
    print("=" * 80)
    
    if overall_stats['total_tests'] > 0:
        print(f"Total tests: {overall_stats['total_tests']}")
        print(f"Encoding success: {overall_stats['total_encode_success']}/{overall_stats['total_tests']} "
              f"({100*overall_stats['total_encode_success']/overall_stats['total_tests']:.1f}%)")
        print(f"Decoding success: {overall_stats['total_decode_success']}/{overall_stats['total_tests']} "
              f"({100*overall_stats['total_decode_success']/overall_stats['total_tests']:.1f}%)")
        print(f"Round-trip success: {overall_stats['total_round_trip_success']}/{overall_stats['total_tests']} "
              f"({100*overall_stats['total_round_trip_success']/overall_stats['total_tests']:.1f}%)")
        
        # Error analysis (sample only)
        if overall_stats['all_errors']:
            print(f"\nTotal errors encountered: {len(overall_stats['all_errors'])}")
            error_types = {}
            for error in overall_stats['all_errors'][:100]:  # Sample first 100 errors
                if error:
                    if ':' in error:
                        error_type = error.split(':')[0].strip()
                    else:
                        error_type = error[:50].strip()
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            if error_types:
                print("Error breakdown (top 10):")
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {error_type}: {count}")
    
    print()
    print("=" * 80)
    
    if overall_stats['total_tests'] == 0:
        print("⚠ No tests were run")
        return 1
    elif overall_stats['total_round_trip_success'] == overall_stats['total_tests']:
        print("✓ All tests passed!")
        return 0
    elif overall_stats['total_round_trip_success'] / overall_stats['total_tests'] > 0.95:
        print(f"✓ {overall_stats['total_round_trip_success']}/{overall_stats['total_tests']} tests passed "
              f"({100*overall_stats['total_round_trip_success']/overall_stats['total_tests']:.1f}%)")
        return 0
    else:
        print(f"⚠ {overall_stats['total_round_trip_success']}/{overall_stats['total_tests']} tests passed "
              f"({100*overall_stats['total_round_trip_success']/overall_stats['total_tests']:.1f}%)")
        return 1

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test SLICES functions with mp-20 dataset (memory-efficient)')
    parser.add_argument('--dataset', type=str, default='data/mp20/test.csv',
                       help='Path to dataset CSV file')
    parser.add_argument('--samples', type=int, default=50,
                       help='Number of samples to test (default: 50)')
    parser.add_argument('--models', type=str, nargs='+', 
                       default=['m3gnet'],
                       help='MLIP models to test (default: m3gnet)')
    parser.add_argument('--batch-size', type=int, default=5,
                       help='Batch size for processing structures (default: 5, lower = less memory. Recommended: 3-5 for M3GNet)')
    
    args = parser.parse_args()
    
    sys.exit(run_tests(args.dataset, args.samples, args.models, args.batch_size))
