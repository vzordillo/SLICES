# pGFNFF Integration Investigation

## Overview

This document investigates whether pGFNFF (https://github.com/jdgale/pGFNFF) can replace the modified XTB binary for generating GFN-FF bond and angle parameters in SLICES.

## Key Findings

### 1. pGFNFF Requirements

**Input Requirements:**
- ✅ Atomic numbers (`nat`)
- ✅ Coordinates (`x`, `y`, `z` arrays) - **REQUIRED**
- ✅ Lattice vectors (`rv`, `kv`) for periodic systems
- ✅ Number of periodic dimensions (`ndim`)

**Output:**
- Bond parameters: `par_bond(3, maxnbr, numat)` - [bond_length, bond_energy, bond_scale]
- Angle parameters: `par_angle(2, nangles)` - [angle_value, angle_weight]
- Bond connectivity: `nbrno_bond`, `ncnbr_bond` (neighbor lists)
- Angle connectivity: `nangleatomptr` (atom triplets)

### 2. Key Difference from XTB

**XTB (modified):**
- ✅ Works from topology-only (`.top` file with neighbor lists)
- ✅ No coordinates required
- ✅ Outputs JSON format directly

**pGFNFF:**
- ❌ Requires coordinates (`x`, `y`, `z` arrays)
- ✅ Library-based (can be called directly)
- ✅ More comprehensive parameter set
- ✅ Supports periodic systems (pGFN-FF)

### 3. Potential Workaround

Since pGFNFF requires coordinates but SLICES has topology only, we can:

1. **Generate initial coordinates from topology** using barycentric embedding (SLICES already does this)
2. **Call pGFNFF** with these coordinates
3. **Extract bond/angle parameters** in the format SLICES needs
4. **Convert to XTB-compatible format** for compatibility

### 4. Parameter Format Comparison

**XTB Output (gfnff_lists.json):**
```json
{
  "blist": [[atom1, atom2], ...],  // Bond connectivity
  "vbond": [[weight, param1, param2, bond_length_bohr, ...], ...],
  "alist": [[atom1, atom2, atom3], ...],  // Angle connectivity
  "vangl": [[angle_value, weight, ...], ...]
}
```

**pGFNFF Output:**
```fortran
par_bond(3, maxnbr, numat)  // [bond_length, bond_energy, bond_scale] for each bond
par_angle(2, nangles)       // [angle_value, angle_weight] for each angle
nbrno_bond, ncnbr_bond      // Bond connectivity (neighbor lists)
nangleatomptr               // Angle connectivity (atom triplets)
```

### 5. Integration Strategy

1. **Build pGFNFF library** (Fortran)
2. **Create Python bindings** using f2py or ctypes
3. **Implement adapter** to convert SLICES topology → pGFNFF input
4. **Implement converter** to convert pGFNFF output → XTB-compatible format
5. **Test** with existing SLICES test cases

### 6. Advantages of pGFNFF

- ✅ Library-based (no subprocess calls)
- ✅ Better error handling
- ✅ More comprehensive parameters
- ✅ Periodic system support (pGFN-FF)
- ✅ Active development (research code)

### 7. Challenges

- ❌ Requires coordinates (need to generate from topology)
- ❌ Fortran library integration (f2py/ctypes)
- ❌ Output format conversion needed
- ❌ Less documented than XTB
- ❌ May need to contact maintainer for support

### 8. Next Steps

1. ✅ Clone and examine pGFNFF repository
2. ⏳ Build pGFNFF library
3. ⏳ Create Python wrapper
4. ⏳ Test with simple structure
5. ⏳ Compare output with XTB
6. ⏳ Integrate into SLICES if successful

## References

- pGFNFF Repository: https://github.com/jdgale/pGFNFF
- Original GFN-FF: Spicher & Grimme, Angew. Chem. Int. Ed., 131, 11195 (2020)
- pGFN-FF: Gale et al., J. Chem. Theory Comput., 17, 7827 (2021)

