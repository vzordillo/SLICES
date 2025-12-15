#!/usr/bin/env python3
"""
Generic script to encode/decode structures and calculate formation energies with any MLIP model.
Supports default/canonical SLICES and standard/robust decoding strategies.
Works with any MLIP model: m3gnet, chgnet, mattersim, orbv3.
"""

import os
import sys
import csv
import json
import argparse
import pandas as pd
from pathlib import Path
from slices.core import SLICES
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.core.composition import Composition
import configparser

def load_chemical_potentials(chem_pot_file=None):
    """Load chemical potentials from JSON file."""
    if chem_pot_file is None:
        # Try multiple possible paths
        possible_paths = [
            Path("MatterGPT_no_flash/demo_decode_novelty_check_eform_m3gnet/workflow/chemPotMP.json"),
            Path("MatterGPT/demo_decode_novelty_check_eform_m3gnet/workflow/chemPotMP.json"),
            Path("demo_decode_novelty_check_eform_m3gnet/workflow/chemPotMP.json"),
            Path("HTS/9_EAH_Band_gap_PBE/workflow/chemPotMP.json"),
        ]
        
        chem_pot_path = None
        for path in possible_paths:
            if path.exists():
                chem_pot_path = path
                break
    else:
        chem_pot_path = Path(chem_pot_file)
    
    if chem_pot_path is None or not chem_pot_path.exists():
        print(f"Warning: Chemical potential file not found. Formation energy calculation will be skipped.")
        print("  Searched paths:")
        for path in possible_paths if chem_pot_file is None else [Path(chem_pot_file)]:
            print(f"    - {path}")
        return {}
    
    print(f"Loading chemical potentials from: {chem_pot_path}")
    with open(chem_pot_path, 'r') as f:
        return json.load(f)

def calculate_formation_energy(structure, energy_per_atom, chem_pot):
    """Calculate formation energy per atom from total energy and chemical potentials."""
    comp = structure.composition
    enthalpy_form = energy_per_atom * comp.num_atoms
    el_amt_dict = comp.get_el_amt_dict()
    
    for element, amount in el_amt_dict.items():
        if element in chem_pot:
            enthalpy_form -= amount * chem_pot[element]
        else:
            print(f"Warning: Chemical potential for {element} not found")
    
    return enthalpy_form / comp.num_atoms

def encode_decode_benchmark(input_csv, output_csv, model="m3gnet", use_canonical=False, use_robust=False, threads=8, max_samples=None):
    """
    Generic encode/decode benchmark with configurable model and decoding strategies.
    
    Args:
        input_csv: Path to input CSV file with CIF structures
        output_csv: Path to output CSV file with results
        model: MLIP model name ('m3gnet', 'chgnet', 'mattersim', 'orbv3')
        use_canonical: If True, use canonical SLICES instead of default
        use_robust: If True, use robust decoding instead of standard
        threads: Number of threads for parallel processing (not used currently)
        max_samples: Maximum number of samples to process (None for all)
    """
    print(f"Loading dataset from {input_csv}...")
    df = pd.read_csv(input_csv)
    
    # Determine CIF column (usually last column or named 'cif')
    cif_column = None
    if 'cif' in df.columns:
        cif_column = 'cif'
    else:
        # Assume last column is CIF
        cif_column = df.columns[-1]
    
    print(f"Using CIF column: {cif_column}")
    
    # Limit samples if specified
    if max_samples:
        df = df.head(max_samples)
        print(f"Processing first {max_samples} samples...")
    
    # Load chemical potentials
    chem_pot = load_chemical_potentials()
    
    # Initialize SLICES with specified model
    print(f"Initializing SLICES with {model}...")
    backend = SLICES(relax_model=model, check_results=False)
    
    # Determine SLICES and decoding method names for output columns
    slices_type = "canonical" if use_canonical else "default"
    decoding_type = "robust" if use_robust else "standard"
    model_key = model.lower()
    
    results = []
    successful = 0
    failed = 0
    
    print(f"Processing {len(df)} structures...")
    print(f"  SLICES type: {slices_type}")
    print(f"  Decoding: {decoding_type}")
    print(f"  Model: {model}")
    
    for idx, row in df.iterrows():
        try:
            cif_string = row[cif_column]
            
            # Skip if CIF is empty or NaN
            if pd.isna(cif_string) or not cif_string.strip():
                print(f"Skipping row {idx}: empty CIF")
                failed += 1
                continue
            
            # Parse structure from CIF
            structure = Structure.from_str(cif_string, fmt="cif")
            
            # Encode to SLICES (default or canonical)
            if use_canonical:
                slices_string = backend.structure2SLICES(structure)
                slices_string = backend.get_canonical_SLICES(slices_string, strategy=4)
            else:
                slices_string = backend.structure2SLICES(structure)
            
            # Decode back to structure and get energy (standard or robust)
            if use_robust:
                decoded_structure, energy_per_atom = backend.robust_SLICES2structure(slices_string)
            else:
                decoded_structure, energy_per_atom = backend.SLICES2structure(slices_string)
            
            if decoded_structure is None or energy_per_atom is None:
                print(f"Decoding failed for row {idx}")
                failed += 1
                continue
            
            # Get space group
            finder = SpacegroupAnalyzer(decoded_structure, symprec=0.1, angle_tolerance=15)
            space_group = finder.get_space_group_number()
            
            # Calculate formation energy (if chemical potentials available)
            if chem_pot:
                formation_energy = calculate_formation_energy(
                    decoded_structure, energy_per_atom, chem_pot
                )
            else:
                formation_energy = None
            
            # Store results with model-specific column names (essential columns only)
            result_row = {
                'slices': slices_string,
                f'energy_per_atom_{model_key}': energy_per_atom,
                f'formation_energy_per_atom_{model_key}': formation_energy,
                'space_group': space_group,
                'formula': decoded_structure.formula,
                'slices_type': slices_type,
                'decoding_type': decoding_type
            }
            
            # Optionally preserve original formation_energy_per_atom for comparison
            if 'formation_energy_per_atom' in df.columns:
                result_row['formation_energy_per_atom'] = row.get('formation_energy_per_atom')
            
            results.append(result_row)
            successful += 1
            
            if (idx + 1) % 100 == 0:
                print(f"Processed {idx + 1}/{len(df)} structures (successful: {successful}, failed: {failed})")
                
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            failed += 1
            continue
    
    # Save results to CSV
    print(f"\nSaving results to {output_csv}...")
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    
    print(f"\nCompleted!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {successful/(successful+failed)*100:.2f}%")
    print(f"  Results saved to: {output_csv}")
    
    return output_csv

def combine_datasets(train_csv, val_csv, test_csv, output_csv):
    """Combine train, val, and test CSV files into a single dataset."""
    print(f"Combining datasets...")
    print(f"  Train: {train_csv}")
    print(f"  Val: {val_csv}")
    print(f"  Test: {test_csv}")
    
    dfs = []
    for csv_file, split_name in [(train_csv, 'train'), (val_csv, 'val'), (test_csv, 'test')]:
        if not Path(csv_file).exists():
            print(f"Warning: {csv_file} not found, skipping...")
            continue
        df = pd.read_csv(csv_file)
        df['split'] = split_name
        dfs.append(df)
        print(f"  Loaded {len(df)} structures from {split_name}")
    
    if not dfs:
        raise ValueError("No datasets found to combine")
    
    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined dataset: {len(combined_df)} structures")
    
    # Save combined dataset
    combined_df.to_csv(output_csv, index=False)
    print(f"Combined dataset saved to: {output_csv}")
    
    return output_csv

# Backward compatibility wrapper
def encode_decode_with_orbv3(input_csv, output_csv, threads=8, max_samples=None):
    """Backward compatibility wrapper for ORBv3 benchmark."""
    return encode_decode_benchmark(input_csv, output_csv, model="orbv3", use_canonical=False, use_robust=False, threads=threads, max_samples=max_samples)

def run_benchmark_mattergpt_no_flash(input_csv, output_dir="benchmark_orbv3_results"):
    """
    Run benchmark on mattergpt_no_flash using orbv3.
    
    Args:
        input_csv: Path to CSV file with SLICES strings (generated from MatterGPT)
        output_dir: Output directory for benchmark results
    """
    print(f"\nRunning benchmark on mattergpt_no_flash with orbv3...")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Check if input CSV exists
    if not Path(input_csv).exists():
        print(f"Error: Input CSV {input_csv} not found")
        print("Please generate SLICES using MatterGPT first, or use the encoded dataset")
        return None
    
    # Load the CSV
    df = pd.read_csv(input_csv)
    
    # Find SLICES column
    slices_column = None
    if 'SLICES' in df.columns:
        slices_column = 'SLICES'
    elif 'slices' in df.columns:
        slices_column = 'slices'
    else:
        # Assume first column is SLICES
        slices_column = df.columns[0]
    
    print(f"Using SLICES column: {slices_column}")
    
    # Load chemical potentials
    chem_pot = load_chemical_potentials()
    
    # Initialize SLICES with orbv3
    print("Initializing SLICES with orbv3 for benchmark...")
    backend = SLICES(relax_model="orbv3", check_results=False)
    
    benchmark_results = []
    successful = 0
    failed = 0
    
    print(f"Processing {len(df)} SLICES strings...")
    for idx, row in df.iterrows():
        try:
            slices_string = row[slices_column]
            
            if pd.isna(slices_string) or not str(slices_string).strip():
                print(f"Skipping row {idx}: empty SLICES")
                failed += 1
                continue
            
            # Decode SLICES to structure
            decoded_structure, energy_per_atom = backend.SLICES2structure(str(slices_string))
            
            # Get space group
            finder = SpacegroupAnalyzer(decoded_structure, symprec=0.1, angle_tolerance=15)
            space_group = finder.get_space_group_number()
            
            # Calculate formation energy (if chemical potentials available)
            if chem_pot:
                formation_energy = calculate_formation_energy(
                    decoded_structure, energy_per_atom, chem_pot
                )
            else:
                formation_energy = None
            
            # Store results
            result_row = {
                'slices': slices_string,
                'energy_per_atom_orbv3': energy_per_atom,
                'formation_energy_per_atom_orbv3': formation_energy,
                'space_group': space_group,
                'formula': decoded_structure.formula,
                'poscar': decoded_structure.to(fmt="poscar")
            }
            
            # Preserve original columns if they exist
            for col in df.columns:
                if col not in result_row and col != slices_column:
                    result_row[col] = row[col]
            
            benchmark_results.append(result_row)
            successful += 1
            
            if (idx + 1) % 10 == 0:
                print(f"Processed {idx + 1}/{len(df)} SLICES (successful: {successful}, failed: {failed})")
                
        except Exception as e:
            print(f"Error processing row {idx}: {e}")
            failed += 1
            continue
    
    # Save benchmark results
    output_csv = output_path / "benchmark_orbv3_results.csv"
    print(f"\nSaving benchmark results to {output_csv}...")
    results_df = pd.DataFrame(benchmark_results)
    results_df.to_csv(output_csv, index=False)
    
    print(f"\nBenchmark completed!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Results saved to: {output_csv}")
    
    return str(output_csv)

def main():
    parser = argparse.ArgumentParser(
        description="Generic encode/decode benchmark with any MLIP model"
    )
    parser.add_argument(
        "--train_csv",
        type=str,
        default="data/mp20/train.csv",
        help="Path to training dataset CSV file"
    )
    parser.add_argument(
        "--val_csv",
        type=str,
        default=None,
        help="Path to validation dataset CSV file (optional, for combining datasets)"
    )
    parser.add_argument(
        "--test_csv",
        type=str,
        default=None,
        help="Path to test dataset CSV file (optional, for combining datasets)"
    )
    parser.add_argument(
        "--combined_csv",
        type=str,
        default=None,
        help="Path to save combined dataset (if combining train/val/test)"
    )
    parser.add_argument(
        "--input_csv",
        type=str,
        default=None,
        help="Path to input CSV file (if not combining datasets, use this or --train_csv)"
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default="train_encoded_decoded.csv",
        help="Path to output CSV file with encoded/decoded results"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="m3gnet",
        choices=["m3gnet", "chgnet", "mattersim", "orbv3"],
        help="MLIP model to use"
    )
    parser.add_argument(
        "--use_canonical",
        action="store_true",
        help="Use canonical SLICES instead of default"
    )
    parser.add_argument(
        "--use_robust",
        action="store_true",
        help="Use robust decoding instead of standard"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="Number of threads for processing"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=None,
        help="Maximum number of samples to process (for testing)"
    )
    parser.add_argument(
        "--benchmark_csv",
        type=str,
        default=None,
        help="Path to CSV file with MatterGPT generated SLICES for benchmark"
    )
    parser.add_argument(
        "--skip_encode_decode",
        action="store_true",
        help="Skip encode/decode step and only run benchmark"
    )
    
    args = parser.parse_args()
    
    # Determine input CSV
    input_csv = args.input_csv
    if input_csv is None:
        # Check if we need to combine datasets
        if args.val_csv and args.test_csv:
            combined_path = args.combined_csv or "data/mp20/combined.csv"
            combine_datasets(args.train_csv, args.val_csv, args.test_csv, combined_path)
            input_csv = combined_path
        else:
            input_csv = args.train_csv
    
    # Step 1: Encode/decode training dataset
    if not args.skip_encode_decode:
        print("=" * 70)
        print(f"Encoding/Decoding Dataset with {args.model.upper()}")
        print(f"  SLICES: {'canonical' if args.use_canonical else 'default'}")
        print(f"  Decoding: {'robust' if args.use_robust else 'standard'}")
        print("=" * 70)
        encode_decode_benchmark(
            input_csv,
            args.output_csv,
            model=args.model,
            use_canonical=args.use_canonical,
            use_robust=args.use_robust,
            threads=args.threads,
            max_samples=args.max_samples
        )
    
    # Step 2: Run benchmark if benchmark CSV is provided
    if args.benchmark_csv:
        print("\n" + "=" * 60)
        print(f"Step 2: Running Benchmark on mattergpt_no_flash with {args.model}")
        print("=" * 60)
        run_benchmark_mattergpt_no_flash(args.benchmark_csv)
    elif not args.skip_encode_decode:
        print("\n" + "=" * 60)
        print("Note: To run benchmark on MatterGPT generated SLICES,")
        print("      provide --benchmark_csv argument")
        print("=" * 60)

if __name__ == "__main__":
    main()

