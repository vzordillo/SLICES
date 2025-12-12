# How to Access Predicted Formation Energies

## Overview

The predicted formation energies from ORBv3 are stored in the encoded/decoded dataset file.

## Location

**Primary Dataset**: `docs/benchmarks/train_encoded_decoded_orbv3.csv`

This CSV file contains:
- `formation_energy_per_atom_orbv3`: **Predicted formation energy per atom** (eV/atom) from ORBv3
- `energy_per_atom_orbv3`: Total energy per atom (eV/atom) from ORBv3
- `formation_energy_per_atom`: Original formation energy from the source dataset (if available)

## Quick Access

### Using Python (Pandas)

```python
import pandas as pd

# Load the dataset
df = pd.read_csv('docs/benchmarks/train_encoded_decoded_orbv3.csv')

# Access formation energies
formation_energies = df['formation_energy_per_atom_orbv3']

# Get statistics
print(f"Mean formation energy: {formation_energies.mean():.4f} eV/atom")
print(f"Std formation energy: {formation_energies.std():.4f} eV/atom")
print(f"Min: {formation_energies.min():.4f} eV/atom")
print(f"Max: {formation_energies.max():.4f} eV/atom")

# Filter by formula
df[df['formula'] == 'Li2O'][['formula', 'formation_energy_per_atom_orbv3']]

# Sort by formation energy
df_sorted = df.sort_values('formation_energy_per_atom_orbv3')
```

### Using Command Line

```bash
# View first few rows with formation energies
cut -d',' -f6,4 docs/benchmarks/train_encoded_decoded_orbv3.csv | head -20

# Count non-null formation energies
awk -F',' 'NR>1 && $4!="" && $4!="NaN" {count++} END {print count}' docs/benchmarks/train_encoded_decoded_orbv3.csv
```

## Energy Columns Explained

1. **`formation_energy_per_atom_orbv3`** (Column 4)
   - **This is the predicted formation energy you want**
   - Calculated from: `E_formation = (E_total - Σ(n_i * μ_i)) / N_atoms`
   - Where `E_total` is from ORBv3 relaxation, `μ_i` are chemical potentials, and `N_atoms` is the number of atoms
   - Units: eV/atom

2. **`energy_per_atom_orbv3`** (Column 3)
   - Total energy per atom from ORBv3 MLIP relaxation
   - This is the raw energy before subtracting chemical potentials
   - Units: eV/atom

3. **`formation_energy_per_atom`** (Column 10)
   - Original formation energy from the source dataset (e.g., Materials Project)
   - This is the ground truth/reference value for comparison
   - Units: eV/atom

## Comparison Test Results

The comparison test JSON files (`decoding_comparison_report_*.json`) contain:
- Success rates
- Processing times
- Error breakdowns

**Note**: The comparison test stores `energy_per_atom` (total energy) in the results, but **not** formation energies. To get formation energies, use the main dataset CSV file.

## Example: Compare Predicted vs. Original Formation Energies

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('docs/benchmarks/train_encoded_decoded_orbv3.csv')

# Filter rows where both energies are available
valid = df.dropna(subset=['formation_energy_per_atom_orbv3', 'formation_energy_per_atom'])

# Calculate correlation
correlation = valid['formation_energy_per_atom_orbv3'].corr(valid['formation_energy_per_atom'])
print(f"Correlation: {correlation:.4f}")

# Plot comparison
plt.scatter(valid['formation_energy_per_atom'], 
            valid['formation_energy_per_atom_orbv3'], 
            alpha=0.5)
plt.xlabel('Original Formation Energy (eV/atom)')
plt.ylabel('ORBv3 Predicted Formation Energy (eV/atom)')
plt.title(f'Formation Energy Comparison (r={correlation:.3f})')
plt.plot([valid['formation_energy_per_atom'].min(), valid['formation_energy_per_atom'].max()],
         [valid['formation_energy_per_atom'].min(), valid['formation_energy_per_atom'].max()],
         'r--', label='Perfect agreement')
plt.legend()
plt.show()
```

## Notes

- Formation energies are calculated using chemical potentials from `data/chemical_potentials.json`
- If chemical potentials are not available for all elements, some formation energies may be `NaN`
- The formation energy calculation is: `E_form = (E_total - Σ(n_i * μ_i)) / N_atoms`


