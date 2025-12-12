# Benchmark Results

This directory contains benchmark results and comparison reports.

## Reports

- **`decoding_comparison_report_*.txt`** - Text format comparison reports
- **`decoding_comparison_report_*.json`** - JSON format comparison data

## Running Benchmarks

### Compare Standard vs Robust Decoding

```bash
conda activate slices
python scripts/run_comparison_test.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 500
```

### Test Improved Decoding

```bash
conda activate slices
python scripts/test_improved_decoding.py \
    --dataset docs/benchmarks/train_encoded_decoded_orbv3.csv \
    --samples 1000 \
    --use-robust
```

## Report Format

Reports include:
- Success rates for standard and robust decoding
- Error breakdown by type
- Performance comparison
- Improvement metrics

