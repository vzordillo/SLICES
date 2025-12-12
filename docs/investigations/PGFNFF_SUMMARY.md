# pGFNFF Integration Summary

## Investigation Status: ⚠️ **FEASIBLE BUT COMPLEX**

## Key Finding

**pGFNFF CAN be used, but requires a workaround since it needs coordinates while SLICES has topology-only input.**

## Solution Approach

### Workflow:
1. **Generate initial coordinates** from topology using barycentric embedding (SLICES already does this)
2. **Call pGFNFF library** with these coordinates
3. **Extract bond/angle parameters** from pGFNFF output
4. **Convert to XTB-compatible format** for SLICES compatibility

### Implementation Steps:

1. **Build pGFNFF library**
   ```bash
   cd /tmp/pGFNFF/Src
   make lib
   ```

2. **Create Python bindings** (using f2py or ctypes)
   - Wrap key functions: `pgfnff_init`, `pgfnff_pargen`, `pgfnff_get_bond_parameters`, `pgfnff_get_angles`

3. **Create adapter module** (`src/slices/pgfnff_adapter.py`)
   - Convert SLICES topology → pGFNFF input format
   - Generate dummy coordinates from topology
   - Call pGFNFF library
   - Convert pGFNFF output → XTB JSON format

4. **Modify `get_inner_p_target()`** in `core.py`
   - Add option to use pGFNFF instead of XTB
   - Maintain backward compatibility

## Comparison

| Feature | Current XTB | pGFNFF |
|---------|-------------|--------|
| **Input** | Topology-only (`.top` file) | Coordinates required |
| **Integration** | Subprocess call | Library call |
| **Output Format** | JSON (compatible) | Fortran arrays (needs conversion) |
| **Periodic Support** | Standard GFN-FF | pGFN-FF (enhanced) |
| **Complexity** | Low (working) | Medium (needs adapter) |
| **Maintenance** | Fork maintained | Research code |

## Parameter Format Mapping

### XTB Format (current):
```python
{
  'blist': [[atom1, atom2], ...],
  'vbond': [[weight, param1, param2, bond_length_bohr, ...], ...],
  'alist': [[atom1, atom2, atom3], ...],
  'vangl': [[angle_value, weight, ...], ...]
}
```

### pGFNFF Format:
```fortran
par_bond(3, maxnbr, numat)  # [bond_length, bond_energy, bond_scale]
par_angle(2, nangles)       # [angle_value, angle_weight]
nbrno_bond, ncnbr_bond      # Bond connectivity
nangleatomptr               # Angle connectivity
```

### Conversion Needed:
- `par_bond[0]` (bond_length) → `vbond[3]` (in Bohr)
- `par_bond[1]` (bond_energy) → `vbond[2]` (weight)
- `par_angle[0]` (angle_value) → `vangl[0]`
- `par_angle[1]` (angle_weight) → `vangl[1]`
- Build `blist` and `alist` from neighbor lists

## Advantages

1. ✅ **Library-based**: No subprocess overhead
2. ✅ **Better error handling**: Direct function calls
3. ✅ **Periodic support**: pGFN-FF enhancements
4. ✅ **More parameters**: Comprehensive force field data
5. ✅ **Cross-platform**: Can build on macOS/Linux/Windows

## Challenges

1. ❌ **Requires coordinates**: Need to generate from topology first
2. ❌ **Fortran integration**: Need Python bindings (f2py/ctypes)
3. ❌ **Format conversion**: Need adapter code
4. ❌ **Less documented**: Research code, may need to contact maintainer
5. ❌ **Additional dependency**: Another library to maintain

## Recommendation

### Short-term: **Keep XTB**
- Current solution works well
- No additional complexity
- Proven in production

### Long-term: **Consider pGFNFF if:**
- You need periodic system improvements (pGFN-FF)
- You want library-based integration
- You're willing to invest in adapter development
- You want more comprehensive parameters

## Next Steps (if proceeding)

1. ✅ Clone and examine pGFNFF (DONE)
2. ⏳ Build pGFNFF library
3. ⏳ Create Python bindings (f2py)
4. ⏳ Implement adapter module
5. ⏳ Test with simple structure
6. ⏳ Compare output with XTB
7. ⏳ Benchmark performance
8. ⏳ Integrate into SLICES (optional)

## Conclusion

**pGFNFF is technically feasible** but requires significant development effort:
- Fortran library integration
- Coordinate generation from topology
- Format conversion
- Testing and validation

**Current XTB solution is more pragmatic** for immediate needs, but pGFNFF could be valuable for:
- Research applications needing pGFN-FF features
- Long-term maintainability (library vs binary)
- Enhanced periodic system support

**Recommendation**: Document this investigation, but **defer implementation** unless specific pGFN-FF features are needed.

