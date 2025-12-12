#!/usr/bin/env python3
"""
Test script for improved SLICES decoding on training dataset.

This script tests the enhanced decoding algorithms on the training dataset
and compares success rates before and after improvements.

Usage:
    python test_improved_decoding.py --dataset data/mp20/train.csv --samples 1000
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import time
import logging
from collections import defaultdict
from slices.core import SLICES, GraphTopologyError, LatticeBasisError, XTBExecutionError, MLIPRelaxationError, TimeoutException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_decoding_strategies(input_csv, output_csv, max_samples=None, use_robust=True):
    """
    Test improved decoding on training dataset.
    
    Args:
        input_csv: Path to input CSV file with SLICES strings
        output_csv: Path to output CSV file with results
        max_samples: Maximum number of samples to test (None for all)
        use_robust: Whether to use robust_SLICES2structure (default: True)
    """
    logger.info(f"Loading dataset from {input_csv}...")
    df = pd.read_csv(input_csv)
    
    # Find SLICES column
    slices_column = None
    if 'slices' in df.columns:
        slices_column = 'slices'
    elif 'SLICES' in df.columns:
        slices_column = 'SLICES'
    else:
        # Assume first column is SLICES
        slices_column = df.columns[0]
    
    logger.info(f"Using SLICES column: {slices_column}")
    
    # Limit samples if specified
    if max_samples:
        df = df.head(max_samples)
        logger.info(f"Processing first {max_samples} samples...")
    
    # Initialize SLICES with orbv3
    logger.info("Initializing SLICES with orbv3...")
    backend = SLICES(relax_model="orbv3", check_results=False)
    
    results = []
    stats = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'errors': defaultdict(int),
        'error_types': defaultdict(list)
    }
    
    logger.info(f"Processing {len(df)} SLICES strings...")
    start_time = time.time()
    
    for idx, row in df.iterrows():
        stats['total'] += 1
        try:
            slices_string = row[slices_column]
            
            if pd.isna(slices_string) or not str(slices_string).strip():
                logger.warning(f"Skipping row {idx}: empty SLICES")
                stats['failed'] += 1
                stats['errors']['empty_slices'] += 1
                continue
            
            # Use robust decoding if requested
            if use_robust:
                decoded_structure, energy_per_atom = backend.robust_SLICES2structure(str(slices_string))
            else:
                decoded_structure, energy_per_atom = backend.SLICES2structure(str(slices_string))
            
            # Store successful result
            result_row = {
                'original_index': idx,
                'slices': slices_string,
                'success': True,
                'energy_per_atom_orbv3': energy_per_atom,
                'formula': decoded_structure.formula,
                'num_atoms': len(decoded_structure),
                'error_type': None
            }
            
            # Preserve original columns
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            
            results.append(result_row)
            stats['successful'] += 1
            
            if (idx + 1) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (idx + 1) / elapsed if elapsed > 0 else 0
                success_rate = stats['successful'] / stats['total'] * 100
                logger.info(
                    f"Processed {idx + 1}/{len(df)} structures | "
                    f"Success: {stats['successful']} ({success_rate:.1f}%) | "
                    f"Failed: {stats['failed']} | "
                    f"Rate: {rate:.2f} structures/sec"
                )
                
        except GraphTopologyError as e:
            stats['failed'] += 1
            stats['errors']['graph_topology'] += 1
            stats['error_types']['graph_topology'].append(str(e)[:100])
            logger.debug(f"Row {idx}: Graph topology error: {e}")
            
            result_row = {
                'original_index': idx,
                'slices': row[slices_column] if slices_column in row else '',
                'success': False,
                'energy_per_atom_orbv3': None,
                'formula': None,
                'num_atoms': None,
                'error_type': 'graph_topology',
                'error_message': str(e)[:200]
            }
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            results.append(result_row)
            
        except LatticeBasisError as e:
            stats['failed'] += 1
            stats['errors']['lattice_basis'] += 1
            stats['error_types']['lattice_basis'].append(str(e)[:100])
            logger.debug(f"Row {idx}: Lattice basis error: {e}")
            
            result_row = {
                'original_index': idx,
                'slices': row[slices_column] if slices_column in row else '',
                'success': False,
                'energy_per_atom_orbv3': None,
                'formula': None,
                'num_atoms': None,
                'error_type': 'lattice_basis',
                'error_message': str(e)[:200]
            }
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            results.append(result_row)
            
        except XTBExecutionError as e:
            stats['failed'] += 1
            stats['errors']['xtb_execution'] += 1
            stats['error_types']['xtb_execution'].append(str(e)[:100])
            logger.debug(f"Row {idx}: XTB execution error: {e}")
            
            result_row = {
                'original_index': idx,
                'slices': row[slices_column] if slices_column in row else '',
                'success': False,
                'energy_per_atom_orbv3': None,
                'formula': None,
                'num_atoms': None,
                'error_type': 'xtb_execution',
                'error_message': str(e)[:200]
            }
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            results.append(result_row)
            
        except (MLIPRelaxationError, TimeoutException) as e:
            stats['failed'] += 1
            stats['errors']['mlip_relaxation'] += 1
            stats['error_types']['mlip_relaxation'].append(str(e)[:100])
            logger.debug(f"Row {idx}: MLIP relaxation error: {e}")
            
            result_row = {
                'original_index': idx,
                'slices': row[slices_column] if slices_column in row else '',
                'success': False,
                'energy_per_atom_orbv3': None,
                'formula': None,
                'num_atoms': None,
                'error_type': 'mlip_relaxation',
                'error_message': str(e)[:200]
            }
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            results.append(result_row)
            
        except Exception as e:
            stats['failed'] += 1
            stats['errors']['other'] += 1
            stats['error_types']['other'].append(str(e)[:100])
            logger.warning(f"Row {idx}: Unexpected error: {e}")
            
            result_row = {
                'original_index': idx,
                'slices': row[slices_column] if slices_column in row else '',
                'success': False,
                'energy_per_atom_orbv3': None,
                'formula': None,
                'num_atoms': None,
                'error_type': 'other',
                'error_message': str(e)[:200]
            }
            for col in df.columns:
                if col not in result_row:
                    result_row[col] = row[col]
            results.append(result_row)
    
    # Save results
    logger.info(f"\nSaving results to {output_csv}...")
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    
    # Print summary statistics
    elapsed = time.time() - start_time
    success_rate = stats['successful'] / stats['total'] * 100 if stats['total'] > 0 else 0
    
    logger.info("\n" + "="*60)
    logger.info("DECODING TEST SUMMARY")
    logger.info("="*60)
    logger.info(f"Total structures processed: {stats['total']}")
    logger.info(f"Successful: {stats['successful']} ({success_rate:.2f}%)")
    logger.info(f"Failed: {stats['failed']} ({100-success_rate:.2f}%)")
    logger.info(f"Total time: {elapsed:.2f} seconds")
    logger.info(f"Average time per structure: {elapsed/stats['total']:.2f} seconds")
    logger.info("\nError breakdown:")
    for error_type, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / stats['total'] * 100
        logger.info(f"  {error_type}: {count} ({percentage:.2f}%)")
    
    logger.info(f"\nResults saved to: {output_csv}")
    
    return results_df, stats


def main():
    parser = argparse.ArgumentParser(
        description="Test improved SLICES decoding on training dataset"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/mp20/train.csv",
        help="Path to training dataset CSV file with SLICES strings"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_improved_decoding_results.csv",
        help="Path to output CSV file with results"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=None,
        help="Maximum number of samples to test (for quick testing)"
    )
    parser.add_argument(
        "--use-robust",
        action="store_true",
        default=True,
        help="Use robust_SLICES2structure method (default: True)"
    )
    parser.add_argument(
        "--no-robust",
        action="store_false",
        dest="use_robust",
        help="Use standard SLICES2structure method instead of robust"
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not Path(args.dataset).exists():
        logger.error(f"Input file not found: {args.dataset}")
        return
    
    # Run test
    results_df, stats = test_decoding_strategies(
        args.dataset,
        args.output,
        max_samples=args.samples,
        use_robust=args.use_robust
    )
    
    logger.info("\nTest completed successfully!")


if __name__ == "__main__":
    main()

