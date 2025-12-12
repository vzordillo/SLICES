# Utilities API Documentation

Complete reference for utility modules: `slices.utils` and `slices.utils_wyckoff`.

## Table of Contents

1. [File Operations](#file-operations)
2. [Process Management](#process-management)
3. [Data Collection](#data-collection)
4. [Space Group Utilities](#space-group-utilities)
5. [Statistical Functions](#statistical-functions)

---

## File Operations

### `temporaryWorkingDirectory(path)`

Context manager to temporarily change the working directory.

**Parameters:**
- `path` (str): Path to the directory to change to

**Returns:**
- Context manager that yields control to the block

**Example:**
```python
from slices.utils import temporaryWorkingDirectory

with temporaryWorkingDirectory('/tmp/work'):
    # All operations here happen in /tmp/work
    # Original directory is restored automatically
    pass
```

---

## Process Management

### `is_slurm_available()`

Checks if SLURM job management system is installed.

**Returns:**
- `bool`: True if SLURM is available, False otherwise

**Example:**
```python
from slices.utils import is_slurm_available

if is_slurm_available():
    print("SLURM is available")
else:
    print("SLURM not found - will use local execution")
```

---

### `splitRun(filename, threads, skip_header=False)`

Splits and runs tasks locally, automatically adjusting thread count.

**Parameters:**
- `filename` (str): Path to JSON file containing task list
- `threads` (int): Desired number of threads
- `skip_header` (bool, optional): Whether to skip header in task list. Defaults to False.

**Example:**
```python
from slices.utils import splitRun

# Run tasks from JSON file with 8 threads
splitRun('tasks.json', threads=8)
```

**Notes:**
- Automatically adjusts thread count if task count is less than thread count
- Cleans up previous task directories and results
- Creates job directories and processes tasks in parallel

---

### `splitRun_csv(filename, threads, skip_header=False)`

Splits and runs tasks from CSV file.

**Parameters:**
- `filename` (str): Path to CSV file containing task list
- `threads` (int): Desired number of threads
- `skip_header` (bool, optional): Whether to skip header. Defaults to False.

**Example:**
```python
from slices.utils import splitRun_csv

splitRun_csv('tasks.csv', threads=4, skip_header=True)
```

---

### `splitRun_sample(threads=8, sample_size=8000)`

Splits and runs sampling tasks.

**Parameters:**
- `threads` (int, optional): Number of threads. Defaults to 8.
- `sample_size` (int, optional): Sample size. Defaults to 8000.

---

### `show_progress(total_jobs=None, check_interval=5)`

Shows progress of running jobs.

**Parameters:**
- `total_jobs` (int, optional): Total number of jobs. Defaults to None.
- `check_interval` (int, optional): Interval in seconds between checks. Defaults to 5.

**Example:**
```python
from slices.utils import show_progress

# Monitor 100 jobs
show_progress(total_jobs=100, check_interval=10)
```

---

### `cancel_all_jobs()`

Cancels all running SLURM jobs.

**Example:**
```python
from slices.utils import cancel_all_jobs

cancel_all_jobs()
```

---

## Data Collection

### `collect_json(output, glob_target, cleanup=True)`

Collects JSON files matching a glob pattern into a single file.

**Parameters:**
- `output` (str): Output file path
- `glob_target` (str): Glob pattern to match files
- `cleanup` (bool, optional): Delete source files after collection. Defaults to True.

**Example:**
```python
from slices.utils import collect_json

# Collect all result_*.json files
collect_json('all_results.json', 'result_*.json', cleanup=True)
```

---

### `collect_csv(output, glob_target, header="", index=False, cleanup=True)`

Collects CSV files matching a glob pattern into a single file.

**Parameters:**
- `output` (str): Output file path
- `glob_target` (str): Glob pattern to match files
- `header` (str, optional): Header row. Defaults to "".
- `index` (bool, optional): Include index column. Defaults to False.
- `cleanup` (bool, optional): Delete source files after collection. Defaults to True.

**Example:**
```python
from slices.utils import collect_csv

# Collect all result_*.csv files
collect_csv('all_results.csv', 'result_*.csv', header='col1,col2', cleanup=True)
```

---

### `collect_csv_filter(output, glob_target, header, condition, cleanup=True)`

Collects CSV files matching a glob pattern with filtering.

**Parameters:**
- `output` (str): Output file path
- `glob_target` (str): Glob pattern to match files
- `header` (str): Header row
- `condition` (callable): Filter function that takes a row and returns bool
- `cleanup` (bool, optional): Delete source files after collection. Defaults to True.

**Example:**
```python
from slices.utils import collect_csv_filter

# Collect only rows where energy < 0
def filter_negative_energy(row):
    return float(row['energy']) < 0

collect_csv_filter('negative_energy.csv', 'result_*.csv', 
                   header='id,energy', condition=filter_negative_energy)
```

---

### `exclude_elements_json(input_json, exclude_elements)`

Excludes structures containing specified elements from JSON file.

**Parameters:**
- `input_json` (str): Input JSON file path
- `exclude_elements` (list): List of element symbols to exclude

**Returns:**
- `list`: Filtered list of structures

**Example:**
```python
from slices.utils import exclude_elements_json

# Exclude structures with rare earth elements
filtered = exclude_elements_json('structures.json', ['La', 'Ce', 'Pr', 'Nd'])
```

---

## Space Group Utilities

### `get_tokenized_enc(int_number)`

Converts space group number to tokenized encoding string.

**Parameters:**
- `int_number` (int): Space group number (1-230)

**Returns:**
- `str`: Tokenized encoding string

**Example:**
```python
from slices.utils_wyckoff import get_tokenized_enc

# Space group 225 (Fm-3m)
enc = get_tokenized_enc(225)
print(enc)  # Tokenized string representation
```

---

### `get_space_group_num_from_letter_enc(letter_enc)`

Converts tokenized encoding string to space group number.

**Parameters:**
- `letter_enc` (str): Tokenized encoding string

**Returns:**
- `int`: Space group number (1-230)

**Raises:**
- `ValueError`: If encoding is invalid

**Example:**
```python
from slices.utils_wyckoff import get_space_group_num_from_letter_enc

sg_num = get_space_group_num_from_letter_enc(tokenized_string)
print(f"Space group: {sg_num}")
```

---

### `get_space_group_num(enc)`

Gets space group number from encoding (wrapper function).

**Parameters:**
- `enc`: Encoding (various formats supported)

**Returns:**
- `int`: Space group number

---

### `tokenize_enc(enc_string)`

Tokenizes an encoding string.

**Parameters:**
- `enc_string` (str): Encoding string

**Returns:**
- `str`: Tokenized encoding

---

## Statistical Functions

### `determine_bin_count(data_size, target_values)`

Determines appropriate number of bins for histogram based on data size.

**Parameters:**
- `data_size` (int): Size of dataset
- `target_values` (array-like): Target values for binning

**Returns:**
- `int`: Number of bins

**Example:**
```python
from slices.utils import determine_bin_count
import numpy as np

data_size = 1000
target_values = np.random.normal(0, 1, 1000)
bins = determine_bin_count(data_size, target_values)
print(f"Use {bins} bins")
```

---

### `adaptive_dynamic_binning(data, target_column, test_size=0.2, random_state=42)`

Performs adaptive dynamic binning for data analysis.

**Parameters:**
- `data` (DataFrame): Input data
- `target_column` (str): Name of target column
- `test_size` (float, optional): Test set size. Defaults to 0.2.
- `random_state` (int, optional): Random seed. Defaults to 42.

**Returns:**
- Binning information

**Example:**
```python
from slices.utils import adaptive_dynamic_binning
import pandas as pd

df = pd.read_csv('data.csv')
bins = adaptive_dynamic_binning(df, target_column='energy', test_size=0.2)
```

---

## Parallel Processing

### `parallel_process_json(process_func, data, n_processes=16, output_file='result.csv', **kwargs)`

Processes data in parallel using JSON format.

**Parameters:**
- `process_func` (callable): Function to process each item
- `data` (list): List of data items to process
- `n_processes` (int, optional): Number of processes. Defaults to 16.
- `output_file` (str, optional): Output CSV file. Defaults to 'result.csv'.
- `**kwargs`: Additional arguments passed to process_func

**Returns:**
- Results written to output_file

**Example:**
```python
from slices.utils import parallel_process_json

def process_structure(structure_data):
    # Process structure
    return result

data = load_structures()
parallel_process_json(process_structure, data, n_processes=8, 
                     output_file='results.csv')
```

---

### `parallel_process_csv(process_func, filename, n_processes=16, output_file='result.csv', skip_header=False, **kwargs)`

Processes CSV file in parallel.

**Parameters:**
- `process_func` (callable): Function to process each row
- `filename` (str): Input CSV file path
- `n_processes` (int, optional): Number of processes. Defaults to 16.
- `output_file` (str, optional): Output CSV file. Defaults to 'result.csv'.
- `skip_header` (bool, optional): Skip header row. Defaults to False.
- `**kwargs`: Additional arguments passed to process_func

**Example:**
```python
from slices.utils import parallel_process_csv

def process_row(row):
    # Process CSV row
    return result

parallel_process_csv(process_row, 'input.csv', n_processes=8,
                     output_file='output.csv', skip_header=True)
```

---

## Helper Functions

### `split_list(a, n)`

Splits a list into n approximately equal parts.

**Parameters:**
- `a` (list): List to split
- `n` (int): Number of parts

**Returns:**
- Generator yielding each sublist

**Example:**
```python
from slices.utils import split_list

my_list = list(range(100))
parts = list(split_list(my_list, 4))
print(f"Split into {len(parts)} parts")
```

---

## Usage Examples

### Batch Processing with Parallel Execution

```python
from slices.utils import parallel_process_csv
from slices.core import SLICES

def encode_structure(row):
    backend = SLICES()
    structure = Structure.from_file(row['cif_path'])
    slices_string = backend.structure2SLICES(structure)
    return {
        'id': row['id'],
        'slices': slices_string,
        'formula': structure.formula
    }

# Process CSV file in parallel
parallel_process_csv(encode_structure, 'structures.csv', 
                    n_processes=8, output_file='encoded.csv')
```

### Collecting Results

```python
from slices.utils import collect_csv, collect_json

# Collect all CSV results
collect_csv('all_results.csv', 'job_*/result_*.csv', cleanup=True)

# Collect all JSON results
collect_json('all_results.json', 'job_*/result_*.json', cleanup=True)
```

### Space Group Encoding/Decoding

```python
from slices.utils_wyckoff import get_tokenized_enc, get_space_group_num_from_letter_enc

# Encode space group to tokenized string
sg_num = 225
tokenized = get_tokenized_enc(sg_num)
print(f"Space group {sg_num} -> {tokenized}")

# Decode tokenized string to space group
sg_num_back = get_space_group_num_from_letter_enc(tokenized)
print(f"{tokenized} -> Space group {sg_num_back}")
```

