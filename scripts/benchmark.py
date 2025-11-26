#!/usr/bin/env python3
"""Performance benchmark script for SLICES."""

import time
import sys
from pathlib import Path
from slices.core import SLICES
from pymatgen.core.structure import Structure

def benchmark_encoding(structure, backend, iterations=10):
    """Benchmark encoding performance."""
    times = []
    for _ in range(iterations):
        start = time.time()
        slices_string = backend.structure2SLICES(structure)
        elapsed = time.time() - start
        times.append(elapsed)
    return sum(times) / len(times), min(times), max(times)

def main():
    """Run benchmarks."""
    print("SLICES Performance Benchmarks")
    print("=" * 50)
    
    # Load test structure
    cif_path = Path("examples/NdSiRu.cif")
    if not cif_path.exists():
        print("Error: Test structure not found")
        return 1
    
    structure = Structure.from_file(str(cif_path))
    backend = SLICES(relax_model='chgnet')
    
    # Benchmark encoding
    avg, min_t, max_t = benchmark_encoding(structure, backend)
    print(f"Encoding: avg={avg:.3f}s, min={min_t:.3f}s, max={max_t:.3f}s")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

