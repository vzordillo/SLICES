# Windows Compatibility Report for SLICES

## Executive Summary

**Overall Compatibility: ⚠️ PARTIAL - Requires Significant Modifications**

The SLICES codebase is **NOT fully compatible with Windows** in its current state. While the core Python code can run on Windows, there are several critical issues, especially related to the XTB binary and Unix-specific commands.

---

## Critical Issues

### 1. XTB Binary Compatibility ❌ **BLOCKER**

**Status**: **NOT COMPATIBLE**

**Problem**:
- The bundled XTB binary (`src/slices/xtb_noring_nooutput_nostdout_noCN`) is **macOS ARM64 only**
- No Windows binary is provided
- XTB is **required for decoding** (`SLICES2structure()` function)
- The custom XTB fork from `xiaohang007/xtb` must be built from source for Windows

**Impact**: 
- ✅ **Encoding** (`structure2SLICES`) works on Windows (doesn't require XTB)
- ❌ **Decoding** (`SLICES2structure`) **will fail** on Windows without a Windows XTB binary

**Location**: `src/slices/core.py` lines 10-51, 1119-1140, 1259-1285

**Current Code**:
```python
xtb_custom = os.path.abspath(os.path.dirname(__file__))+"/xtb_noring_nooutput_nostdout_noCN"
# Only checks for macOS/Linux compatibility, no Windows support
```

**Solution Required**:
1. Build XTB from source for Windows (requires CMake, GCC/MinGW, Fortran compiler)
2. Add Windows binary detection in `core.py`
3. Handle Windows executable extension (`.exe`)

---

### 2. Unix-Specific Commands ❌ **BLOCKER**

**Status**: **NOT COMPATIBLE**

**Problems Found**:

#### a) `file` command (Unix-only)
**Location**: `src/slices/core.py` line 25
```python
result = subprocess.run(['file', xtb_custom], capture_output=True, text=True)
```
- `file` command doesn't exist on Windows
- Will raise `FileNotFoundError` on Windows
- Currently wrapped in try/except, but falls back silently

**Solution**: Use Python's `platform` module or `pefile` library instead

#### b) `cp` command (Unix-only)
**Location**: `src/slices/core.py` lines 1143, 1145, 1283, 1285
```python
os.system("cp "+temp_dir.name+'/testBonds_cut.top '+os.getcwd())
os.system("cp "+gfnff_json_path+' '+os.getcwd())
```
- `cp` doesn't exist on Windows (use `copy` or `xcopy`)
- Will fail silently or raise errors

**Solution**: Use `shutil.copy()` or `shutil.copy2()` instead of `os.system()`

#### c) `chmod` command (Unix-only)
**Location**: `README.md` line 366, various shell scripts
- Not critical for Python execution, but mentioned in documentation
- Windows doesn't have `chmod`

**Solution**: Use `os.chmod()` in Python or document Windows-specific instructions

---

### 3. Path Handling Issues ⚠️ **MODERATE**

**Status**: **PARTIALLY COMPATIBLE** (works but not ideal)

**Problems**:
- Uses string concatenation with `/` instead of `os.path.join()`
- Works on Windows (Python handles it) but not best practice

**Locations**:
- `src/slices/core.py` line 13: `os.path.abspath(os.path.dirname(__file__))+"/xtb_noring_nooutput_nostdout_noCN"`
- `src/slices/core.py` line 1116: `temp_dir.name+'/testBonds_cut.top'`
- `src/slices/core.py` line 1128: `temp_dir.name+'/gfnff_lists.json'`

**Solution**: Replace with `os.path.join()` for cross-platform compatibility

---

### 4. Shell Scripts ❌ **NOT COMPATIBLE**

**Status**: **NOT COMPATIBLE** (but not required for core functionality)

**Problem**:
- 62+ `.sh` shell scripts throughout the codebase
- Cannot run natively on Windows (requires WSL, Git Bash, or Cygwin)

**Locations**:
- `entrypoint_set_cpus.sh`
- `entrypoint_set_cpus_gradio.sh`
- `MatterGPT_no_flash/0_dataset/1_build_dataset.sh`
- All workflow scripts in `benchmark/`, `HTS/`, `MatterGPT/` directories

**Impact**: 
- **Low** for core SLICES functionality (Python API)
- **High** for workflow automation and batch processing

**Solution**: 
- Use WSL2 (recommended by README)
- Or convert critical scripts to Python
- Or use PowerShell equivalents

---

### 5. PBS/SLURM Scripts ❌ **NOT COMPATIBLE**

**Status**: **NOT COMPATIBLE**

**Problem**:
- 76+ `.pbs` files for job scheduling
- PBS/SLURM are Linux/Unix cluster job schedulers
- Not available on Windows

**Impact**: 
- **Low** for local development
- **High** for HPC cluster usage

**Solution**: Use WSL2 or run on Linux cluster

---

### 6. Linux-Specific Features ⚠️ **MODERATE**

**Status**: **HAS FALLBACK** (works but suboptimal)

**Problem**: `/dev/shm` usage
**Location**: `src/slices/core.py` lines 1110-1115, 1249-1254
```python
if platform.system() == 'Linux' and os.path.exists("/dev/shm"):
    temp_dir = tempfile.TemporaryDirectory(dir="/dev/shm")
else:
    temp_dir = tempfile.TemporaryDirectory()
```

**Status**: ✅ **HAS FALLBACK** - Uses system temp directory on Windows
- This is actually **correctly implemented** with a fallback
- No changes needed

---

## What Works on Windows ✅

### 1. Core Python Dependencies
- All Python packages (pymatgen, numpy, scipy, tensorflow, etc.) support Windows
- Installation via pip/conda works on Windows

### 2. Encoding Function (`structure2SLICES`)
- ✅ **Fully compatible** - No external binaries required
- Pure Python implementation
- Works on Windows without modifications

### 3. MLIP Models
- ✅ All MLIP models (M3GNet, CHGNet, MatGL, MatterSim, ORBv3) support Windows
- PyTorch and TensorFlow work on Windows

### 4. Python API Usage
- ✅ Core SLICES class can be imported
- ✅ Structure manipulation works
- ✅ Graph operations work

---

## Required Modifications for Windows Support

### Priority 1: Critical (Required for Decoding)

1. **Build Windows XTB Binary**
   - Clone `https://github.com/xiaohang007/xtb`
   - Install build tools: CMake, MinGW-w64 or MSVC, Fortran compiler
   - Build for Windows (x64)
   - Add `.exe` extension handling in code

2. **Fix Unix Commands in `core.py`**
   ```python
   # Replace 'file' command with platform detection
   # Replace 'cp' commands with shutil.copy()
   # Add Windows executable extension (.exe) handling
   ```

3. **Update Path Handling**
   ```python
   # Replace string concatenation with os.path.join()
   xtb_custom = os.path.join(os.path.dirname(__file__), "xtb_noring_nooutput_nostdout_noCN")
   # Add .exe extension on Windows
   if platform.system() == 'Windows':
       xtb_custom += '.exe'
   ```

### Priority 2: Important (For Full Functionality)

4. **Add Windows Binary Detection**
   - Check for Windows XTB binary
   - Provide clear error messages if missing
   - Add Windows build instructions to README

5. **Update Documentation**
   - Add Windows installation section
   - Document WSL2 requirement for workflows
   - Provide Windows-specific troubleshooting

### Priority 3: Nice to Have (For Workflows)

6. **Convert Shell Scripts to Python**
   - Or provide PowerShell equivalents
   - Or document WSL2 usage clearly

---

## Recommended Approach for Windows Users

### Option 1: Use WSL2 (Recommended)
- ✅ Full compatibility with minimal changes
- ✅ All shell scripts work
- ✅ Can use Linux XTB binary
- ✅ Follow existing Linux installation guide

**Steps**:
1. Install WSL2 with Ubuntu on Windows 11
2. Follow Linux installation instructions in README
3. Build XTB from source in WSL2

### Option 2: Native Windows (Requires Modifications)
- ⚠️ Requires code changes
- ⚠️ Need to build Windows XTB binary
- ✅ Better integration with Windows tools
- ✅ No WSL overhead

**Steps**:
1. Apply code modifications listed above
2. Build XTB for Windows
3. Test encoding/decoding

### Option 3: Docker (If Available)
- ✅ Uses Linux container (full compatibility)
- ⚠️ Requires Docker Desktop on Windows
- ✅ No code changes needed

---

## Testing Checklist for Windows

- [ ] XTB binary detection works on Windows
- [ ] XTB execution works (if Windows binary available)
- [ ] Encoding (`structure2SLICES`) works
- [ ] Decoding (`SLICES2structure`) works
- [ ] Path handling works with Windows paths
- [ ] File operations work (no `cp` command issues)
- [ ] Temp directory creation works
- [ ] MLIP models load and run
- [ ] No Unix command dependencies

---

## Code Locations Requiring Changes

### `src/slices/core.py`
- **Lines 13**: Path handling for XTB binary
- **Lines 20-40**: Platform detection (add Windows support)
- **Lines 25**: `file` command (replace with Python alternative)
- **Lines 1116, 1128**: Path concatenation (use `os.path.join()`)
- **Lines 1143, 1145**: `cp` commands (use `shutil.copy()`)
- **Lines 1261**: XTB execution (ensure Windows compatibility)
- **Lines 1283, 1285**: `cp` commands (use `shutil.copy()`)

### `README.md`
- Add Windows installation section
- Document XTB Windows build process
- Update troubleshooting for Windows

### `pyproject.toml`
- Consider adding Windows XTB binary to package data (if built)

---

## Summary

| Component | Windows Status | Notes |
|-----------|----------------|-------|
| **Encoding** (`structure2SLICES`) | ✅ **Works** | Pure Python, no issues |
| **Decoding** (`SLICES2structure`) | ❌ **Blocked** | Requires Windows XTB binary |
| **XTB Binary** | ❌ **Missing** | Only macOS ARM64 provided |
| **Core Python Code** | ⚠️ **Partial** | Unix commands need fixing |
| **Path Handling** | ⚠️ **Works but suboptimal** | Should use `os.path.join()` |
| **Shell Scripts** | ❌ **Not Compatible** | Use WSL2 or convert to Python |
| **PBS Scripts** | ❌ **Not Compatible** | Linux cluster only |
| **MLIP Models** | ✅ **Works** | All support Windows |
| **Dependencies** | ✅ **Works** | All available for Windows |

**Recommendation**: Use **WSL2** for best compatibility, or apply the modifications listed above for native Windows support.

---

## Estimated Effort for Full Windows Support

- **XTB Windows Build**: 4-8 hours (if build environment set up)
- **Code Modifications**: 2-4 hours
- **Testing**: 4-8 hours
- **Documentation**: 2-4 hours
- **Total**: 12-24 hours of development work

---

*Report generated: 2024*
*Codebase version: Based on current git status*

