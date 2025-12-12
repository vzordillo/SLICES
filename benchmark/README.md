# Benchmark Directory

This directory contains benchmark results, datasets, and analysis scripts for SLICES.

## Directory Structure

```
benchmark/
├── results/              # Benchmark results and outputs
│   ├── data/            # Benchmark datasets
│   ├── reports/         # Comparison reports and analysis
│   └── images/          # Visualization images
├── match_rate_mp20/     # MP-20 match rate benchmarks
├── match_rate_mp21_40/  # MP-21-40 match rate benchmarks
├── match_rate_qmof/     # QMOF match rate benchmarks
└── validity_rate_rnn/   # RNN validity rate benchmarks
```

## Results

### Large-Scale Decoding Comparison

- **Dataset**: `results/data/train_encoded_decoded_orbv3.csv`
- **Report**: `results/reports/decoding_comparison_report_*.txt`
- **Results**: Standard vs Robust decoding on 24,502 structures

### MLIP Model Comparison

- **Script**: `scripts/benchmarks/test_all_mlips.py`
- **Output**: `results/mlip_benchmark_YYYYMMDD_HHMMSS.json`
- **Tests**: 20 random structures across M3GNet, CHGNet, MatterSim, ORBv3

## Running Benchmarks

See main README.md for instructions on running benchmarks.

