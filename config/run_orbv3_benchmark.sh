#!/bin/bash

# Script to activate conda slices environment and run encode/decode with orbv3 benchmark

set -e  # Exit on error

echo "=============================================="
echo "Activating conda slices environment..."
echo "=============================================="

# Activate conda environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate slices

if [ $? -ne 0 ]; then
    echo "Error: Failed to activate conda slices environment"
    echo "Please make sure the environment exists: conda create -n slices ..."
    exit 1
fi

echo "Conda environment activated successfully"
echo "Python path: $(which python)"
echo "Python version: $(python --version)"

echo ""
echo "=============================================="
echo "Running encode/decode and orbv3 benchmark..."
echo "=============================================="

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Default training dataset path
TRAIN_CSV="${1:-data/mp20/train.csv}"
OUTPUT_CSV="${2:-train_encoded_decoded_orbv3.csv}"
THREADS="${3:-8}"
MAX_SAMPLES="${4:-}"

echo "Training dataset: $TRAIN_CSV"
echo "Output CSV: $OUTPUT_CSV"
echo "Threads: $THREADS"
if [ -n "$MAX_SAMPLES" ]; then
    echo "Max samples: $MAX_SAMPLES"
    MAX_SAMPLES_ARG="--max_samples $MAX_SAMPLES"
else
    MAX_SAMPLES_ARG=""
fi

# Run the encode/decode script
python encode_decode_orbv3_benchmark.py \
    --train_csv "$TRAIN_CSV" \
    --output_csv "$OUTPUT_CSV" \
    --threads "$THREADS" \
    $MAX_SAMPLES_ARG

echo ""
echo "=============================================="
echo "Encode/decode completed!"
echo "Results saved to: $OUTPUT_CSV"
echo "=============================================="

# If a benchmark CSV is provided as 5th argument, run benchmark
if [ -n "$5" ]; then
    BENCHMARK_CSV="$5"
    echo ""
    echo "=============================================="
    echo "Running benchmark on mattergpt_no_flash..."
    echo "=============================================="
    
    python encode_decode_orbv3_benchmark.py \
        --skip_encode_decode \
        --benchmark_csv "$BENCHMARK_CSV"
    
    echo ""
    echo "=============================================="
    echo "Benchmark completed!"
    echo "=============================================="
fi

