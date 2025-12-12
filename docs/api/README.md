# API Reference Documentation

This directory contains complete API reference documentation for all SLICES modules.

## API Documentation Files

1. **[API_CORE.md](API_CORE.md)** - Core SLICES class and encoding/decoding functionality
   - SLICES class initialization and methods
   - Encoding and decoding functions
   - Validation methods
   - XTB integration
   - Structure relaxation

2. **[API_MLIP.md](API_MLIP.md)** - Machine Learning Interatomic Potential (MLIP) relaxers
   - MLIPRelaxer base class
   - M3GNetRelaxer, CHGNetRelaxer, MatterSimRelaxer, ORBv3Relaxer
   - Factory function for creating relaxers

3. **[API_GRAPH.md](API_GRAPH.md)** - Graph theory operations
   - Net class for periodic graphs
   - Cycle and cocycle basis computation
   - Lattice basis determination
   - SystreDB for reading network files

4. **[API_UTILITIES.md](API_UTILITIES.md)** - Utility functions
   - File operations
   - Process management (SLURM, parallel processing)
   - Data collection functions
   - Space group utilities
   - Statistical functions

5. **[API_DECODING_STRATEGIES.md](API_DECODING_STRATEGIES.md)** - Decoding strategies
   - CycleBasisOptimizer
   - BondParameterFallback
   - MultiStartOptimizer
   - ProgressiveRelaxer
   - AdaptiveConvergence

6. **[API_CONFIG.md](API_CONFIG.md)** - Configuration constants
   - OFFSET array (supercell offsets)
   - LJ_PARAMS_LIST (Lennard-Jones parameters)
   - PERIODIC_DATA (periodic table data)

## Quick Reference

### Most Common Classes

- **SLICES** - Main class for encoding/decoding ([API_CORE.md](API_CORE.md#slices-class))
- **MLIPRelaxer** - Base class for MLIP models ([API_MLIP.md](API_MLIP.md#mliprelaxer-base-class))
- **Net** - Periodic graph representation ([API_GRAPH.md](API_GRAPH.md#net-class))

### Most Common Functions

- `structure2SLICES()` - Encode structure to SLICES string ([API_CORE.md](API_CORE.md#structure2slices))
- `SLICES2structure()` - Decode SLICES string to structure ([API_CORE.md](API_CORE.md#slices2structure))
- `get_relaxer()` - Get MLIP relaxer instance ([API_MLIP.md](API_MLIP.md#factory-function))

## Navigation

- Return to [main documentation index](../README.md)
- See [TECHNICAL.md](../../TECHNICAL.md) for system architecture
- See [main README](../../README.md) for installation and usage

