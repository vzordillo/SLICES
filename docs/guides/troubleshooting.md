# Troubleshooting Guide

## Common Issues and Solutions

### Import Errors

**Problem**: `ImportError: No module named 'slices'`

**Solution**:
```bash
# Make sure you're in the conda environment
conda activate slices

# Install in development mode
pip install -e .
```

### MLIP Model Errors

**Problem**: `RuntimeError: Failed to initialize m3gnet`

**Solution**:
- Install required MLIP packages:
  ```bash
  pip install chgnet m3gnet matgl
  ```
- For M3GNet on TensorFlow 2.16+, install `tf_keras`:
  ```bash
  pip install tf_keras
  ```

### XTB Binary Errors

**Problem**: `XTBExecutionError: XTB binary not found`

**Solution**:
- For macOS: Build XTB from source: https://github.com/xiaohang007/xtb
- For Linux: The included binary should work
- Check if system XTB is available: `which xtb`

### Memory Errors

**Problem**: `MemoryError` or out of memory

**Solution**:
- Process structures in smaller batches
- Use `clear_cache()` on Net objects
- Clear TensorFlow sessions: `tf.keras.backend.clear_session()`
- Reduce batch size in test scripts

### Graph Topology Errors

**Problem**: `GraphTopologyError: Incompatible graph topology`

**Solution**:
- Some structures may have incompatible topologies for SLICES
- Try a different graph method: `graph_method='crystalnn'`
- This is expected for some edge cases

### Encoding/Decoding Failures

**Problem**: Round-trip fails or produces incorrect structure

**Solution**:
- Check that structure is 3D: `backend.check_3D(structure)`
- Verify elements are supported: `backend.check_element(structure)`
- Try different encoding strategy (1-4)
- Check MLIP relaxation succeeded (energy != 0)

## Getting Help

1. Check the [README.md](../README.md) for installation instructions
2. Review [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md) for technical details
3. Open an issue on GitHub with:
   - Error message
   - Structure file (if applicable)
   - Python version
   - Operating system

