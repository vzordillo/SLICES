import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import math
from slices.utils import adaptive_dynamic_binning


# Load data
data = pd.read_csv('mp20_eform_bandgap_nonmetal.csv')
target_column = data.columns[-1]  # Assume the last column is the target value

# Perform adaptive dynamic binning
train_data, test_data, bins = adaptive_dynamic_binning(data, target_column)

# Check distributions
print("\nTraining set distribution:")
print(train_data[target_column].value_counts(bins=bins, normalize=True).sort_index())
print("\nTest set distribution:")
print(test_data[target_column].value_counts(bins=bins, normalize=True).sort_index())

# Save split datasets
train_data.to_csv('train_data_auto_binned.csv', index=False)
test_data.to_csv('test_data_auto_binned.csv', index=False)

# Print bin details
print(f"\nNumber of bins used: {len(bins) - 1}")
print("Bin edges:")
for i, (low, high) in enumerate(zip(bins[:-1], bins[1:])):
    print(f"Bin {i+1}: {low:.4f} to {high:.4f}")

# Count data points per bin
bin_counts = pd.cut(data[target_column], bins=bins, labels=[f'Bin{i+1}' for i in range(len(bins)-1)], include_lowest=True).value_counts().sort_index()
print("\nData point count per bin:")
print(bin_counts)

# Compute count difference between smallest and largest bins
min_count = bin_counts.min()
max_count = bin_counts.max()
print(f"\nSmallest bin count: {min_count}")
print(f"Largest bin count: {max_count}")
print(f"Count difference between largest and smallest bins: {max_count - min_count}")
print(f"Count ratio between largest and smallest bins: {max_count / min_count:.2f}")