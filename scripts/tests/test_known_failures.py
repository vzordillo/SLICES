#!/usr/bin/env python3
"""
Test improved decoding on structures known to have failed previously.

This script uses the encoded dataset and tests structures that were
identified as failures in the original encoding process.

Usage:
    python scripts/tests/test_known_failures.py --samples 100
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import time
import logging
from collections import defaultdict
from slices.core import (
    SLICES, GraphTopologyError, LatticeBasisError,
    XTBExecutionError, MLIPRelaxationError, TimeoutException
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_structures(dataset_file, indices=None, max_samples=None, use_robust=False):
    """
    Test specific structures from the dataset.
    
    Args:
        dataset_file: Path to dataset CSV
        indices: List of specific indices to test (None for random sample)
        max_samples: Maximum number of samples
        use_robust: Whether to use robust decoding
    """
    logger.info(f"Loading dataset from {dataset_file}...")
    df = pd.read_csv(dataset_file)
    
    # Find SLICES column
    slices_column = 'slices' if 'slices' in df.columns else df.columns[0]
    logger.info(f"Using SLICES column: {slices_column}")
    
    # Select indices to test
    if indices:
        test_indices = [idx for idx in indices if idx < len(df)][:max_samples] if max_samples else [idx for idx in indices if idx < len(df)]
    else:
        test_indices = list(range(min(max_samples or len(df), len(df))))
    
    logger.info(f"Testing {len(test_indices)} structures...")
    
    # Initialize backend
    backend = SLICES(relax_model="orbv3", check_results=False)
    
    stats = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'errors': defaultdict(int),
        'times': []
    }
    
    start_time = time.time()
    
    for idx in test_indices:
        stats['total'] += 1
        row = df.iloc[idx]
        slices_string = row[slices_column]
        
        if pd.isna(slices_string) or not str(slices_string).strip():
            stats['failed'] += 1
            stats['errors']['empty'] += 1
            continue
        
        struct_start = time.time()
        try:
            if use_robust:
                decoded, energy = backend.robust_SLICES2structure(str(slices_string))
            else:
                decoded, energy = backend.SLICES2structure(str(slices_string))
            
            elapsed = time.time() - struct_start
            stats['times'].append(elapsed)
            stats['successful'] += 1
            
        except GraphTopologyError as e:
            stats['failed'] += 1
            stats['errors']['graph_topology'] += 1
        except LatticeBasisError as e:
            stats['failed'] += 1
            stats['errors']['lattice_basis'] += 1
        except XTBExecutionError as e:
            stats['failed'] += 1
            stats['errors']['xtb'] += 1
        except (MLIPRelaxationError, TimeoutException) as e:
            stats['failed'] += 1
            stats['errors']['mlip'] += 1
        except Exception as e:
            stats['failed'] += 1
            stats['errors']['other'] += 1
        
        if stats['total'] % 10 == 0:
            elapsed_total = time.time() - start_time
            success_rate = stats['successful'] / stats['total'] * 100
            logger.info(
                f"Progress: {stats['total']}/{len(test_indices)} | "
                f"Success: {stats['successful']} ({success_rate:.1f}%)"
            )
    
    total_time = time.time() - start_time
    success_rate = stats['successful'] / stats['total'] * 100 if stats['total'] > 0 else 0
    
    return {
        **stats,
        'success_rate': success_rate,
        'total_time': total_time,
        'avg_time': np.mean(stats['times']) if stats['times'] else 0
    }


def main():
    parser = argparse.ArgumentParser(description="Test known failure cases")
    parser.add_argument("--dataset", type=str, 
                       default="docs/benchmarks/train_encoded_decoded_orbv3.csv",
                       help="Dataset CSV file")
    parser.add_argument("--samples", type=int, default=100, help="Number of samples")
    parser.add_argument("--use-robust", action="store_true", help="Use robust decoding")
    parser.add_argument("--indices", type=str, help="Comma-separated list of indices to test")
    
    args = parser.parse_args()
    
    # Parse indices if provided
    indices = None
    if args.indices:
        indices = [int(x.strip()) for x in args.indices.split(',')]
    
    # Test
    stats = test_structures(
        args.dataset,
        indices=indices,
        max_samples=args.samples,
        use_robust=args.use_robust
    )
    
    # Report
    logger.info("\n" + "="*60)
    logger.info("RESULTS")
    logger.info("="*60)
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Successful: {stats['successful']} ({stats['success_rate']:.2f}%)")
    logger.info(f"Failed: {stats['failed']} ({100-stats['success_rate']:.2f}%)")
    logger.info(f"Total time: {stats['total_time']:.2f} seconds")
    logger.info(f"Avg time: {stats['avg_time']:.2f} seconds")
    logger.info("\nError breakdown:")
    for error_type, count in sorted(stats['errors'].items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {error_type}: {count}")


if __name__ == "__main__":
    main()

