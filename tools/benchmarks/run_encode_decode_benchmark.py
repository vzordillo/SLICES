#!/usr/bin/env python3
"""
Generic script to run comprehensive encode/decode benchmark with any MLIP model.
Tests all combinations of:
- Default SLICES + Standard decoding
- Default SLICES + Robust decoding
- Canonical SLICES + Standard decoding
- Canonical SLICES + Robust decoding

Combines train.csv, val.csv, test.csv into a single dataset.
Supports any MLIP model (m3gnet, chgnet, mattersim, orbv3).

Usage:
    python scripts/benchmarks/run_encode_decode_benchmark.py --model m3gnet
    
The script will:
1. Combine train/val/test datasets
2. Run all 4 combinations of SLICES type and decoding strategy
3. Generate formation energy comparison plot
4. Save results to benchmark/results/data/ with timestamp
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tools.benchmarks.encode_decode_benchmark import encode_decode_benchmark, combine_datasets

def run_all_combinations(combined_csv, model="m3gnet", output_dir="benchmark/results/data", max_samples=None):
    """
    Run all 4 combinations of SLICES type and decoding strategy.
    
    Args:
        combined_csv: Path to combined dataset CSV
        model: MLIP model name ('m3gnet', 'chgnet', 'mattersim', 'orbv3')
        output_dir: Output directory for results
        max_samples: Maximum number of samples to process (None for all)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_key = model.lower()
    
    combinations = [
        (False, False, "default_standard"),
        (False, True, "default_robust"),
        (True, False, "canonical_standard"),
        (True, True, "canonical_robust"),
    ]
    
    results = {}
    
    for use_canonical, use_robust, name in combinations:
        print("\n" + "=" * 70)
        print(f"Running: {name.upper()} with {model.upper()}")
        print("=" * 70)
        
        output_csv = output_dir / f"train_encoded_decoded_{model_key}_{name}_{timestamp}.csv"
        
        try:
            encode_decode_benchmark(
                input_csv=combined_csv,
                output_csv=str(output_csv),
                model=model,
                use_canonical=use_canonical,
                use_robust=use_robust,
                threads=8,
                max_samples=max_samples
            )
            results[name] = str(output_csv)
        except Exception as e:
            print(f"Error running {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = None
    
    return results, timestamp

def main():
    parser = argparse.ArgumentParser(
        description="Run comprehensive encode/decode benchmark with any MLIP model"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="m3gnet",
        choices=["m3gnet", "chgnet", "mattersim", "orbv3"],
        help="MLIP model to use"
    )
    parser.add_argument(
        "--train_csv",
        type=str,
        default="data/mp20/train.csv",
        help="Path to training dataset CSV"
    )
    parser.add_argument(
        "--val_csv",
        type=str,
        default="data/mp20/val.csv",
        help="Path to validation dataset CSV"
    )
    parser.add_argument(
        "--test_csv",
        type=str,
        default="data/mp20/test.csv",
        help="Path to test dataset CSV"
    )
    parser.add_argument(
        "--combined_csv",
        type=str,
        default=None,
        help="Path to save combined dataset (auto-generated if not specified)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="benchmark/results/data",
        help="Output directory for benchmark results"
    )
    parser.add_argument(
        "--max_samples",
        type=int,
        default=None,
        help="Maximum number of samples to process (for testing, None for all)"
    )
    parser.add_argument(
        "--skip_plot",
        action="store_true",
        help="Skip generation of formation energy comparison plot"
    )
    
    args = parser.parse_args()
    
    model = args.model.lower()
    model_upper = model.upper()
    
    print("=" * 70)
    print(f"Encode/Decode Benchmark - {model_upper}")
    print("=" * 70)
    
    # Step 1: Combine datasets
    print("\nStep 1: Combining datasets...")
    combined_csv = args.combined_csv or f"data/mp20/combined_{model}.csv"
    combine_datasets(args.train_csv, args.val_csv, args.test_csv, combined_csv)
    
    # Step 2: Run all combinations
    print("\nStep 2: Running all combinations...")
    results, timestamp = run_all_combinations(
        combined_csv, 
        model=model,
        output_dir=args.output_dir,
        max_samples=args.max_samples
    )
    
    # Step 3: Generate formation energy comparison plot
    if not args.skip_plot:
        print("\n" + "=" * 70)
        print("Step 3: Generating formation energy comparison plot...")
        print("=" * 70)
        
        # Use default_standard for the main plot
        main_result = results.get("default_standard")
        if main_result and Path(main_result).exists():
            output_image = f"benchmark/results/images/formation_energy_comparison_{model}.png"
            print(f"\nGenerating plot from {main_result}...")
            subprocess.run([
                sys.executable,
                "scripts/benchmarks/plot_formation_energy_comparison.py",
                "--input", main_result,
                "--output", output_image,
                "--model", model
            ])
            print(f"Plot saved to: {output_image}")
        else:
            print(f"Warning: Could not generate plot - {main_result} not found")
    
    # Summary
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    for name, csv_path in results.items():
        if csv_path and Path(csv_path).exists():
            # Count successful entries
            import pandas as pd
            df = pd.read_csv(csv_path)
            success_count = len(df[df[f'energy_per_atom_{model}'].notna()])
            total_count = len(df)
            print(f"  {name}: {csv_path}")
            print(f"    Success: {success_count}/{total_count} ({success_count/total_count*100:.2f}%)")
        else:
            print(f"  {name}: FAILED")
    print("=" * 70)

if __name__ == "__main__":
    main()

