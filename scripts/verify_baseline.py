#!/usr/bin/env python3
"""
Baseline Verification Script
Compares current test results with baseline to detect regressions.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_baseline_test():
    """Run baseline test and return results."""
    print("Running baseline test...")
    result = subprocess.run(
        [
            sys.executable, "test_slices_functions.py",
            "--dataset", "data/mp20/test.csv",
            "--samples", "10",
            "--models", "chgnet",
            "--batch-size", "5"
        ],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stdout, result.stderr

def verify_imports():
    """Verify that all critical imports work."""
    print("Verifying imports...")
    try:
        from slices.core import SLICES, SLICESError, SLICESEncodingError
        from slices.tobascco_net import Net, LatticeBasisError, CocycleBasisError
        from slices.mlip_relaxer import get_relaxer
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def main():
    """Main verification function."""
    print("=" * 60)
    print("Baseline Verification")
    print("=" * 60)
    print()
    
    # Verify imports
    if not verify_imports():
        print("\n✗ Import verification failed!")
        return 1
    
    # Run baseline test
    success, stdout, stderr = run_baseline_test()
    
    if success:
        print("\n✓ Baseline test passed")
        # Extract key metrics
        if "Encoding success" in stdout:
            print("\nTest Results Summary:")
            for line in stdout.split('\n'):
                if any(keyword in line for keyword in ['Encoding success', 'Decoding success', 'Round-trip success']):
                    print(f"  {line.strip()}")
        return 0
    else:
        print("\n✗ Baseline test failed!")
        print("\nError output:")
        print(stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

