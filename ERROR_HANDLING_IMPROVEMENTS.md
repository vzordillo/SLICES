# Error Handling Improvements Summary

## Overview

This document summarizes the error handling improvements made to the SLICES codebase to ensure consistency, better error messages, and proper exception handling throughout.

---

## ✅ Implemented Improvements

### 1. **Custom Exception Classes**

Created a hierarchy of custom exceptions for better error categorization:

#### SLICES Core Exceptions (`src/slices/core.py`)
- `SLICESError`: Base exception class for all SLICES-related errors
- `SLICESEncodingError`: Raised when encoding a structure to SLICES fails
- `SLICESDecodingError`: Raised when decoding a SLICES string to structure fails
- `GraphTopologyError`: Raised when graph topology is incompatible for SLICES operations
- `LatticeBasisError`: Raised when lattice basis cannot be computed (inherits from GraphTopologyError)
- `XTBExecutionError`: Raised when XTB binary execution fails
- `MLIPRelaxationError`: Raised when MLIP relaxation fails

#### Net Module Exceptions (`src/slices/tobascco_net.py`)
- `NetError`: Base exception class for Net-related errors
- `LatticeBasisError`: Raised when lattice basis cannot be computed from cycle vectors
- `CocycleBasisError`: Raised when cocycle basis cannot be computed

### 2. **Standardized Error Handling**

#### Before:
```python
def get_lattice_basis(self) -> int:
    # ...
    if not found_vector:
        error("Could not obtain the lattice basis from the cycle vectors!")
        return -1  # ❌ Inconsistent return value
    return 1
```

#### After:
```python
def get_lattice_basis(self) -> None:
    # ...
    if not found_vector:
        raise LatticeBasisError(
            f"Could not obtain lattice basis vector {i+1} from cycle vectors. "
            "This structure may have incompatible graph topology for SLICES decoding."
        )  # ✅ Consistent exception-based error handling
```

### 3. **Replaced Bare `except:` Clauses**

#### Before:
```python
try:
    Element(token)
    first_elem_idx = i
    break
except:  # ❌ Catches all exceptions, including system exits
    continue
```

#### After:
```python
try:
    Element(token)
    first_elem_idx = i
    break
except (ValueError, KeyError):  # ✅ Specific exception types
    continue
```

### 4. **Improved Error Messages**

#### Before:
```python
raise Exception("Error: wrong edge indices")  # ❌ Generic, unhelpful
```

#### After:
```python
raise SLICESEncodingError(
    "Invalid edge indices in SLICES string. "
    "Edge indices must be valid and within bounds."
)  # ✅ Specific, informative
```

### 5. **Consistent Exception Propagation**

Updated all callers of `get_lattice_basis()` to handle exceptions properly:

#### Before:
```python
lattice_basis_result = net.get_lattice_basis()
if lattice_basis_result == -1:
    raise RuntimeError("Failed to obtain lattice basis...")
```

#### After:
```python
try:
    net.get_lattice_basis()
except LatticeBasisError as e:
    raise GraphTopologyError(
        "Failed to obtain lattice basis from cycle vectors. "
        "This structure may have incompatible graph topology for SLICES decoding."
    ) from e  # ✅ Proper exception chaining
```

---

## 📊 Error Handling Patterns

### Pattern 1: Validation Errors → Specific Exceptions
```python
if edge_indices[i,0] > num_atoms-1 or edge_indices[i,1] > num_atoms-1:
    raise SLICESEncodingError("Invalid edge indices in SLICES string...")
```

### Pattern 2: External Tool Failures → Tool-Specific Exceptions
```python
except subprocess.TimeoutExpired:
    raise XTBExecutionError("XTB execution timed out after 30 seconds...")
```

### Pattern 3: Graph Topology Issues → GraphTopologyError
```python
except LatticeBasisError as e:
    raise GraphTopologyError("Failed to obtain lattice basis...") from e
```

### Pattern 4: Expected Errors in Validation → Return False
```python
except (SLICESEncodingError, ValueError, KeyError, IndexError) as e:
    # Expected errors for invalid SLICES strings
    return False
except Exception as e:
    # Unexpected errors should be logged
    logging.debug(f"Unexpected error in check_SLICES: {e}")
    return False
```

---

## 🔍 Files Modified

### `src/slices/core.py`
- Added custom exception classes
- Replaced all `raise Exception(...)` with specific exceptions
- Replaced bare `except:` with specific exception types
- Updated `get_lattice_basis()` callers to handle exceptions
- Improved error messages throughout

### `src/slices/tobascco_net.py`
- Added custom exception classes
- Changed `get_lattice_basis()` to raise exceptions instead of returning -1
- Changed `get_cocycle_basis()` to raise exceptions on failure
- Improved error messages with context

---

## ✅ Benefits

1. **Consistency**: All errors now use exceptions instead of mixed return codes
2. **Clarity**: Specific exception types make it clear what went wrong
3. **Debugging**: Better error messages with context help identify issues
4. **Maintainability**: Exception hierarchy makes it easier to handle errors appropriately
5. **Type Safety**: Type hints and specific exceptions improve IDE support

---

## 🧪 Testing

All improvements have been verified:
- ✅ Custom exception classes import successfully
- ✅ Exception hierarchy is correct
- ✅ Error handling works in practice
- ✅ Test suite runs successfully

---

## 📝 Usage Examples

### Catching Specific Errors
```python
from slices.core import SLICES, SLICESEncodingError, GraphTopologyError

backend = SLICES(relax_model='chgnet')

try:
    slices_string = backend.structure2SLICES(structure)
except SLICESEncodingError as e:
    print(f"Encoding failed: {e}")
except GraphTopologyError as e:
    print(f"Graph topology issue: {e}")
```

### Handling XTB Errors
```python
from slices.core import XTBExecutionError

try:
    structure, energy = backend.SLICES2structure(slices_string)
except XTBExecutionError as e:
    print(f"XTB execution failed: {e}")
    # Handle XTB-specific issues
```

---

## 🎯 Future Improvements

- [ ] Add more specific exception types for edge cases
- [ ] Create error code constants for programmatic error handling
- [ ] Add error recovery mechanisms where appropriate
- [ ] Improve error logging and diagnostics

---

## 📚 References

- Python Exception Handling: https://docs.python.org/3/tutorial/errors.html
- Exception Best Practices: https://docs.python.org/3/library/exceptions.html

