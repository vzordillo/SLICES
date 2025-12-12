# ORBv3 Encode/Decode and Benchmark Guide

## Overview

This guide explains how to:
1. Encode and decode the training dataset using SLICES with ORBv3
2. Calculate formation energies using ORBv3
3. Run benchmarks on MatterGPT_no_flash generated structures using ORBv3

## Files Created

1. **`encode_decode_orbv3_benchmark.py`**: Main Python script for encoding/decoding and benchmarking
2. **`run_orbv3_benchmark.sh`**: Shell script to activate conda environment and run the workflow

## Step 1: Encode/Decode Training Dataset

### Quick Test (5 samples)
```bash
source $(conda info --base)/etc/profile.d/conda.sh
conda activate slices
python encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded_orbv3.csv \
    --threads 8 \
    --max_samples 5
```

### Full Dataset
```bash
# Using the shell script
./run_orbv3_benchmark.sh data/mp20/train.csv train_encoded_decoded_orbv3.csv 8

# Or directly with Python
python encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded_orbv3.csv \
    --threads 8
```

### Output
The script generates `train_encoded_decoded_orbv3.csv` with the following columns:
- `original_index`: Original row index from training dataset
- `slices`: SLICES string representation
- `energy_per_atom_orbv3`: ORBv3 calculated energy per atom (eV/atom)
- `formation_energy_per_atom_orbv3`: Formation energy per atom (eV/atom)
- `space_group`: Space group number
- `formula`: Chemical formula
- `poscar`: POSCAR format structure
- All original columns from the training dataset

## Step 2: Run Benchmark on MatterGPT_no_flash

### Option A: If you have MatterGPT generated SLICES

If you have a CSV file with MatterGPT generated SLICES (e.g., from `MatterGPT_no_flash/1_train_generate/`):

```bash
python encode_decode_orbv3_benchmark.py \
    --skip_encode_decode \
    --benchmark_csv path/to/mattergpt_generated_slices.csv
```

### Option B: Generate SLICES using MatterGPT first

1. **Train MatterGPT** (if not already trained):
```bash
cd MatterGPT_no_flash/1_train_generate
python train.py \
    --run_name eform \
    --batch_size 36 \
    --max_epochs 50 \
    --train_dataset ../0_dataset/train_data.csv \
    --val_dataset ../0_dataset/val_data.csv \
    --slices_column_index 0 \
    --prop_column_index_list 1
```

2. **Generate SLICES**:
```bash
cd MatterGPT_no_flash/1_train_generate
python generate.py \
    --model_weight eform.pt \
    --batch_size 5 \
    --output_csv eform_generated.csv \
    --gen_size 100 \
    --train_dataset ../0_dataset/train_data.csv \
    --prop_targets [[-2.0],[-1.5],[-1.0]]
```

3. **Run benchmark with ORBv3**:
```bash
python encode_decode_orbv3_benchmark.py \
    --skip_encode_decode \
    --benchmark_csv MatterGPT_no_flash/1_train_generate/eform_generated.csv
```

### Output
The benchmark generates `benchmark_orbv3_results/benchmark_orbv3_results.csv` with:
- `slices`: SLICES string
- `energy_per_atom_orbv3`: ORBv3 energy per atom
- `formation_energy_per_atom_orbv3`: Formation energy per atom
- `space_group`: Space group number
- `formula`: Chemical formula
- `poscar`: POSCAR format structure
- Original property columns from MatterGPT output

## Monitoring Progress

### Check encode/decode progress:
```bash
tail -f encode_decode_orbv3.log
```

### Check if process is running:
```bash
ps aux | grep encode_decode_orbv3
```

### Check output file size:
```bash
ls -lh train_encoded_decoded_orbv3.csv
```

## Notes

1. **Chemical Potentials**: The script automatically searches for `chemPotMP.json` in common locations. If not found, formation energy calculation will be skipped (but energy_per_atom will still be calculated).

2. **Threading**: Adjust `--threads` based on your system. More threads = faster processing but higher memory usage.

3. **Memory**: ORBv3 can be memory-intensive. If you encounter memory issues, reduce `--threads` or process in smaller batches using `--max_samples`.

4. **Failed Structures**: Some structures may fail to decode due to incompatible graph topology. This is normal and the script will continue processing.

5. **Time**: Processing the full training dataset (1M+ structures) can take several hours depending on your hardware.

## Troubleshooting

### Conda environment not found
```bash
conda create -n slices python=3.11
conda activate slices
# Install required packages (see project requirements)
```

### ORBv3 not installed
```bash
pip install orb-models
```

### Chemical potentials not found
The script will still work but formation energies won't be calculated. To fix:
- Download `chemPotMP.json` from Materials Project or use existing one
- Place it in `MatterGPT_no_flash/demo_decode_novelty_check_eform_m3gnet/workflow/`

### Out of memory
- Reduce `--threads` (e.g., from 8 to 4)
- Process in batches using `--max_samples` and combine results later

## Example Workflow

```bash
# 1. Activate environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate slices

# 2. Test with small sample
python encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv test_orbv3.csv \
    --max_samples 10 \
    --threads 4

# 3. Run full dataset (background)
nohup python encode_decode_orbv3_benchmark.py \
    --train_csv data/mp20/train.csv \
    --output_csv train_encoded_decoded_orbv3.csv \
    --threads 8 > encode_decode_orbv3.log 2>&1 &

# 4. Generate MatterGPT SLICES (if needed)
cd MatterGPT_no_flash/1_train_generate
python generate.py --model_weight eform.pt --output_csv eform_100.csv --gen_size 100

# 5. Run benchmark
cd ../..
python encode_decode_orbv3_benchmark.py \
    --skip_encode_decode \
    --benchmark_csv MatterGPT_no_flash/1_train_generate/eform_100.csv
```

