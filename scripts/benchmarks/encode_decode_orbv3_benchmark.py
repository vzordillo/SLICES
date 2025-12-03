#!/usr/bin/env python3
"""
Script to encode/decode training dataset and calculate orbv3 formation energies,
then run benchmark on mattergpt_no_flash.
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

def encode_decode_with_orbv3(input_csv, output_csv, threads=8, max_samples=None):
    """
    Encode structures to SLICES, decode back, and calculate orbv3 formation energies.
    
    Args:
        input_csv: Path to input CSV file with CIF structures
        output_csv: Path to output CSV file with results
        threads: Number of threads for parallel processing
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
    
    # Initialize SLICES with orbv3
    print("Initializing SLICES with orbv3...")
    backend = SLICES(relax_model="orbv3", check_results=False)
    
    results = []
    successful = 0
    failed = 0
    
    print(f"Processing {len(df)} structures...")
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
            
            # Encode to SLICES
            slices_string = backend.structure2SLICES(structure)
            
            # Decode back to structure and get energy
            decoded_structure, energy_per_atom = backend.SLICES2structure(slices_string)
            
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
                'original_index': idx,
                'slices': slices_string,
                'energy_per_atom_orbv3': energy_per_atom,
                'formation_energy_per_atom_orbv3': formation_energy,
                'space_group': space_group,
                'formula': decoded_structure.formula,
                'poscar': decoded_structure.to(fmt="poscar")
            }
            
            # Preserve original columns
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            
            results.append(result_row)
            successful += 1
            
            if (idx + 1) % 10 == 0:
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
    print(f"  Results saved to: {output_csv}")
    
    return output_csv

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
        description="Encode/decode training dataset with orbv3 and run benchmark"
    )
    parser.add_argument(
        "--train_csv",
        type=str,
        default="data/mp20/train.csv",
        help="Path to training dataset CSV file"
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default="train_encoded_decoded_orbv3.csv",
        help="Path to output CSV file with encoded/decoded results"
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
    
    # Step 1: Encode/decode training dataset
    if not args.skip_encode_decode:
        print("=" * 60)
        print("Step 1: Encoding/Decoding Training Dataset with orbv3")
        print("=" * 60)
        encode_decode_with_orbv3(
            args.train_csv,
            args.output_csv,
            threads=args.threads,
            max_samples=args.max_samples
        )
    
    # Step 2: Run benchmark if benchmark CSV is provided
    if args.benchmark_csv:
        print("\n" + "=" * 60)
        print("Step 2: Running Benchmark on mattergpt_no_flash with orbv3")
        print("=" * 60)
        run_benchmark_mattergpt_no_flash(args.benchmark_csv)
    elif not args.skip_encode_decode:
        print("\n" + "=" * 60)
        print("Note: To run benchmark on MatterGPT generated SLICES,")
        print("      provide --benchmark_csv argument")
        print("=" * 60)

if __name__ == "__main__":
    main()

