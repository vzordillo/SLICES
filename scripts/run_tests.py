#!/usr/bin/env python3
"""
Test runner script for SLICES.

Provides convenient commands for running different test suites.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}\n")
    
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="SLICES Test Runner")
    parser.add_argument(
        '--unit', action='store_true',
        help='Run unit tests only'
    )
    parser.add_argument(
        '--integration', action='store_true',
        help='Run integration tests only'
    )
    parser.add_argument(
        '--regression', action='store_true',
        help='Run regression tests only'
    )
    parser.add_argument(
        '--coverage', action='store_true',
        help='Run with coverage reporting'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Build pytest command
    cmd_parts = ['pytest']
    
    if args.unit:
        cmd_parts.append('tests/unit/')
    elif args.integration:
        cmd_parts.append('tests/integration/')
    elif args.regression:
        cmd_parts.append('tests/regression/')
    else:
        cmd_parts.append('tests/')
    
    if args.coverage:
        cmd_parts.extend(['--cov=src/slices', '--cov-report=html', '--cov-report=term-missing'])
    
    if args.verbose:
        cmd_parts.append('-v')
    else:
        cmd_parts.append('-q')
    
    cmd = ' '.join(cmd_parts)
    
    # Run tests
    success = run_command(cmd, "Running SLICES Tests")
    
    if args.coverage and success:
        print("\n✓ Coverage report generated: htmlcov/index.html")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

