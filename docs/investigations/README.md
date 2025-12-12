# SLICES Investigations

This directory contains investigations into potential improvements and alternatives for SLICES.

## Current Investigations

### pGFNFF Integration

**Status**: Investigation Complete  
**Branch**: `investigate-pgfnff`  
**Date**: 2025-01-02

**Summary**: Investigated whether pGFNFF (https://github.com/jdgale/pGFNFF) can replace the modified XTB binary for generating GFN-FF bond and angle parameters.

**Key Findings**:
- ✅ pGFNFF is technically feasible but requires coordinates (not topology-only)
- ✅ Can work with workaround: generate coordinates from topology first
- ⚠️ Requires significant development effort (Fortran library integration, format conversion)
- 📊 Current XTB solution is more pragmatic for immediate needs

**Documents**:
- `PGFNFF_INVESTIGATION.md` - Detailed investigation notes
- `PGFNFF_SUMMARY.md` - Executive summary and recommendations

**Recommendation**: Document for future reference, but defer implementation unless specific pGFN-FF features are needed.

