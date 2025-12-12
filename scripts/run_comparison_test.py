#!/usr/bin/env python3
"""
Comprehensive comparison test between standard and robust decoding.

This script tests both standard and robust decoding methods on the same
dataset sample and generates a detailed comparison report.

Usage:
    python scripts/run_comparison_test.py --samples 500
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import time
import logging
from collections import defaultdict
from datetime import datetime
import json
from slices.core import (
    SLICES, GraphTopologyError, LatticeBasisError, 
    XTBExecutionError, MLIPRelaxationError, TimeoutException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_decoding_method(backend, df, slices_column, method_name, use_robust=False):
    """
    Test a decoding method on the dataset.
    
    Args:
        backend: SLICES backend instance
        df: DataFrame with SLICES strings
        slices_column: Name of column containing SLICES strings
        method_name: Name of method being tested
        use_robust: Whether to use robust_SLICES2structure
        
    Returns:
        Dictionary with statistics
    """
    stats = {
        'method': method_name,
        'total': 0,
        'successful': 0,
        'failed': 0,
        'errors': defaultdict(int),
        'error_messages': defaultdict(list),
        'times': [],
        'start_time': time.time()
    }
    
    results = []
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing {method_name}")
    logger.info(f"{'='*60}")
    
    for idx, row in df.iterrows():
        stats['total'] += 1
        start_time = time.time()
        
        try:
            slices_string = row[slices_column]
            
            if pd.isna(slices_string) or not str(slices_string).strip():
                stats['failed'] += 1
                stats['errors']['empty_slices'] += 1
                continue
            
            # Decode using specified method
            if use_robust:
                decoded_structure, energy_per_atom = backend.robust_SLICES2structure(str(slices_string))
            else:
                decoded_structure, energy_per_atom = backend.SLICES2structure(str(slices_string))
            
            elapsed = time.time() - start_time
            stats['times'].append(elapsed)
            stats['successful'] += 1
            
            results.append({
                'index': idx,
                'success': True,
                'energy': energy_per_atom,
                'formula': decoded_structure.formula,
                'num_atoms': len(decoded_structure),
                'time': elapsed,
                'error_type': None
            })
            
        except GraphTopologyError as e:
            stats['failed'] += 1
            stats['errors']['graph_topology'] += 1
            stats['error_messages']['graph_topology'].append(str(e)[:100])
            results.append({
                'index': idx,
                'success': False,
                'error_type': 'graph_topology',
                'error_message': str(e)[:200]
            })
            
        except LatticeBasisError as e:
            stats['failed'] += 1
            stats['errors']['lattice_basis'] += 1
            stats['error_messages']['lattice_basis'].append(str(e)[:100])
            results.append({
                'index': idx,
                'success': False,
                'error_type': 'lattice_basis',
                'error_message': str(e)[:200]
            })
            
        except XTBExecutionError as e:
            stats['failed'] += 1
            stats['errors']['xtb_execution'] += 1
            stats['error_messages']['xtb_execution'].append(str(e)[:100])
            results.append({
                'index': idx,
                'success': False,
                'error_type': 'xtb_execution',
                'error_message': str(e)[:200]
            })
            
        except (MLIPRelaxationError, TimeoutException) as e:
            stats['failed'] += 1
            stats['errors']['mlip_relaxation'] += 1
            stats['error_messages']['mlip_relaxation'].append(str(e)[:100])
            results.append({
                'index': idx,
                'success': False,
                'error_type': 'mlip_relaxation',
                'error_message': str(e)[:200]
            })
            
        except Exception as e:
            stats['failed'] += 1
            stats['errors']['other'] += 1
            stats['error_messages']['other'].append(str(e)[:100])
            results.append({
                'index': idx,
                'success': False,
                'error_type': 'other',
                'error_message': str(e)[:200]
            })
        
        # Progress update
        if stats['total'] % 50 == 0:
            elapsed_total = time.time() - stats['start_time']
            success_rate = stats['successful'] / stats['total'] * 100
            rate = stats['total'] / elapsed_total if elapsed_total > 0 else 0
            logger.info(
                f"Progress: {stats['total']}/{len(df)} | "
                f"Success: {stats['successful']} ({success_rate:.1f}%) | "
                f"Rate: {rate:.2f} structures/sec"
            )
    
    stats['end_time'] = time.time()
    stats['total_time'] = stats['end_time'] - stats['start_time']
    stats['avg_time'] = np.mean(stats['times']) if stats['times'] else 0
    stats['success_rate'] = stats['successful'] / stats['total'] * 100 if stats['total'] > 0 else 0
    
    return stats, results


def generate_comparison_report(stats_standard, stats_robust, output_file):
    """
    Generate a detailed comparison report.
    
    Args:
        stats_standard: Statistics from standard decoding
        stats_robust: Statistics from robust decoding
        output_file: Path to output report file
    """
    report = []
    report.append("="*80)
    report.append("SLICES DECODING IMPROVEMENTS - COMPARISON REPORT")
    report.append("="*80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    report.append("SUMMARY")
    report.append("-"*80)
    report.append(f"Total structures tested: {stats_standard['total']}")
    report.append("")
    report.append(f"Standard Decoding (SLICES2structure):")
    report.append(f"  Success: {stats_standard['successful']} ({stats_standard['success_rate']:.2f}%)")
    report.append(f"  Failed: {stats_standard['failed']} ({100-stats_standard['success_rate']:.2f}%)")
    report.append(f"  Total time: {stats_standard['total_time']:.2f} seconds")
    report.append(f"  Avg time per structure: {stats_standard['avg_time']:.2f} seconds")
    report.append("")
    report.append(f"Robust Decoding (robust_SLICES2structure):")
    report.append(f"  Success: {stats_robust['successful']} ({stats_robust['success_rate']:.2f}%)")
    report.append(f"  Failed: {stats_robust['failed']} ({100-stats_robust['success_rate']:.2f}%)")
    report.append(f"  Total time: {stats_robust['total_time']:.2f} seconds")
    report.append(f"  Avg time per structure: {stats_robust['avg_time']:.2f} seconds")
    report.append("")
    
    # Improvement
    improvement = stats_robust['success_rate'] - stats_standard['success_rate']
    improvement_count = stats_robust['successful'] - stats_standard['successful']
    report.append("IMPROVEMENT")
    report.append("-"*80)
    report.append(f"Success rate improvement: +{improvement:.2f}%")
    report.append(f"Additional successful decodings: +{improvement_count} structures")
    report.append(f"Relative improvement: {(improvement/stats_standard['success_rate']*100) if stats_standard['success_rate'] > 0 else 0:.2f}%")
    report.append("")
    
    # Error breakdown - Standard
    report.append("ERROR BREAKDOWN - STANDARD DECODING")
    report.append("-"*80)
    for error_type, count in sorted(stats_standard['errors'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats_standard['total'] * 100
        report.append(f"  {error_type}: {count} ({percentage:.2f}%)")
    report.append("")
    
    # Error breakdown - Robust
    report.append("ERROR BREAKDOWN - ROBUST DECODING")
    report.append("-"*80)
    for error_type, count in sorted(stats_robust['errors'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats_robust['total'] * 100
        reduction = stats_standard['errors'].get(error_type, 0) - count
        reduction_pct = (reduction / stats_standard['errors'].get(error_type, 1) * 100) if stats_standard['errors'].get(error_type, 0) > 0 else 0
        report.append(f"  {error_type}: {count} ({percentage:.2f}%) [Reduced by {reduction} ({reduction_pct:.1f}%)]")
    report.append("")
    
    # Performance comparison
    report.append("PERFORMANCE COMPARISON")
    report.append("-"*80)
    time_diff = stats_robust['avg_time'] - stats_standard['avg_time']
    time_diff_pct = (time_diff / stats_standard['avg_time'] * 100) if stats_standard['avg_time'] > 0 else 0
    report.append(f"Average time per structure:")
    report.append(f"  Standard: {stats_standard['avg_time']:.3f} seconds")
    report.append(f"  Robust: {stats_robust['avg_time']:.3f} seconds")
    report.append(f"  Difference: {time_diff:+.3f} seconds ({time_diff_pct:+.1f}%)")
    report.append("")
    
    # Conclusion
    report.append("CONCLUSION")
    report.append("-"*80)
    if improvement > 0:
        report.append(f"✓ Robust decoding shows improvement of {improvement:.2f}% success rate")
        report.append(f"✓ {improvement_count} additional structures successfully decoded")
        if time_diff > 0:
            report.append(f"⚠ Robust decoding is {time_diff_pct:.1f}% slower on average")
        else:
            report.append(f"✓ Robust decoding is {abs(time_diff_pct):.1f}% faster on average")
    else:
        report.append("⚠ No improvement observed (may need larger sample size)")
    report.append("")
    report.append("="*80)
    
    # Write report
    report_text = "\n".join(report)
    with open(output_file, 'w') as f:
        f.write(report_text)
    
    # Also save JSON for programmatic access
    json_file = output_file.replace('.txt', '.json')
    comparison_data = {
        'timestamp': datetime.now().isoformat(),
        'total_structures': stats_standard['total'],
        'standard': {
            'success_rate': stats_standard['success_rate'],
            'successful': stats_standard['successful'],
            'failed': stats_standard['failed'],
            'avg_time': stats_standard['avg_time'],
            'total_time': stats_standard['total_time'],
            'errors': dict(stats_standard['errors'])
        },
        'robust': {
            'success_rate': stats_robust['success_rate'],
            'successful': stats_robust['successful'],
            'failed': stats_robust['failed'],
            'avg_time': stats_robust['avg_time'],
            'total_time': stats_robust['total_time'],
            'errors': dict(stats_robust['errors'])
        },
        'improvement': {
            'success_rate_delta': improvement,
            'additional_successful': improvement_count,
            'relative_improvement_pct': (improvement/stats_standard['success_rate']*100) if stats_standard['success_rate'] > 0 else 0
        }
    }
    
    with open(json_file, 'w') as f:
        json.dump(comparison_data, f, indent=2)
    
    logger.info(f"\nReport saved to: {output_file}")
    logger.info(f"JSON data saved to: {json_file}")
    
    # Print summary to console
    print("\n" + report_text)
    
    return comparison_data


def main():
    parser = argparse.ArgumentParser(
        description="Compare standard vs robust SLICES decoding"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="docs/benchmarks/train_encoded_decoded_orbv3.csv",
        help="Path to dataset CSV file with SLICES strings (default: encoded dataset)"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=500,
        help="Number of samples to test (default: 500)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/benchmarks",
        help="Output directory for reports"
    )
    
    args = parser.parse_args()
    
    # Check if dataset exists
    if not Path(args.dataset).exists():
        logger.error(f"Dataset not found: {args.dataset}")
        logger.info("Please ensure the dataset file exists or provide correct path")
        return
    
    # Load dataset
    logger.info(f"Loading dataset from {args.dataset}...")
    df = pd.read_csv(args.dataset)
    
    # Find SLICES column - check multiple possible names
    slices_column = None
    possible_names = ['slices', 'SLICES', 'Slices', 'slices_string', 'SLICES_string']
    
    for name in possible_names:
        if name in df.columns:
            slices_column = name
            break
    
    # If not found, check case-insensitive
    if slices_column is None:
        for col in df.columns:
            if col.lower() in ['slices', 'slices_string']:
                slices_column = col
                break
    
    # Last resort: check if first column looks like SLICES (contains element symbols)
    if slices_column is None:
        first_col = df.columns[0]
        sample_val = str(df[first_col].iloc[0]) if len(df) > 0 else ""
        # Check if it contains element symbols (heuristic)
        from pymatgen.core import Element
        try:
            tokens = sample_val.split()
            if any(len(t) <= 2 and t[0].isupper() for t in tokens[:5]):
                slices_column = first_col
                logger.warning(f"Assuming first column '{first_col}' contains SLICES strings")
        except:
            pass
    
    if slices_column is None:
        logger.error("Could not find SLICES column in dataset. Available columns:")
        logger.error(f"  {list(df.columns)[:10]}")
        return
    
    logger.info(f"Using SLICES column: {slices_column}")
    
    # Limit samples
    if args.samples and args.samples < len(df):
        df = df.head(args.samples)
        logger.info(f"Testing on {args.samples} samples...")
    else:
        logger.info(f"Testing on all {len(df)} samples...")
    
    # Initialize backends
    logger.info("Initializing SLICES backends...")
    backend_standard = SLICES(relax_model="orbv3", check_results=False)
    backend_robust = SLICES(relax_model="orbv3", check_results=False)
    
    # Test standard decoding
    stats_standard, results_standard = test_decoding_method(
        backend_standard, df, slices_column, "Standard Decoding", use_robust=False
    )
    
    # Test robust decoding
    stats_robust, results_robust = test_decoding_method(
        backend_robust, df, slices_column, "Robust Decoding", use_robust=True
    )
    
    # Generate report
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"decoding_comparison_report_{timestamp}.txt"
    
    comparison_data = generate_comparison_report(stats_standard, stats_robust, str(report_file))
    
    logger.info("\n" + "="*60)
    logger.info("COMPARISON TEST COMPLETED")
    logger.info("="*60)
    logger.info(f"Standard success rate: {stats_standard['success_rate']:.2f}%")
    logger.info(f"Robust success rate: {stats_robust['success_rate']:.2f}%")
    logger.info(f"Improvement: +{comparison_data['improvement']['success_rate_delta']:.2f}%")
    logger.info(f"Report: {report_file}")


if __name__ == "__main__":
    main()

