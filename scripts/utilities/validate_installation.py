#!/usr/bin/env python3
"""
Installation validation script for SLICES.

Checks that all dependencies are installed and working correctly.
"""

import sys
import importlib


def check_import(module_name, package_name=None):
    """Check if a module can be imported."""
    try:
        importlib.import_module(module_name)
        print(f"✓ {package_name or module_name}")
        return True
    except ImportError as e:
        print(f"✗ {package_name or module_name}: {e}")
        return False


def main():
    """Validate installation."""
    print("=" * 60)
    print("SLICES Installation Validation")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # Core dependencies
    print("Core Dependencies:")
    all_ok &= check_import("pymatgen", "pymatgen")
    all_ok &= check_import("numpy", "numpy")
    all_ok &= check_import("networkx", "networkx")
    all_ok &= check_import("scipy", "scipy")
    print()
    
    # MLIP models (optional)
    print("MLIP Models (optional):")
    check_import("m3gnet", "M3GNet")
    check_import("chgnet", "CHGNet")
    check_import("mattersim", "MatterSim")
    check_import("orb_models", "ORBv3")
    print()
    
    # SLICES package
    print("SLICES Package:")
    all_ok &= check_import("slices", "slices")
    all_ok &= check_import("slices.core", "slices.core")
    all_ok &= check_import("slices.tobascco_net", "slices.tobascco_net")
    all_ok &= check_import("slices.mlip_relaxer", "slices.mlip_relaxer")
    print()
    
    # Test basic functionality
    print("Basic Functionality Test:")
    try:
        from slices.core import SLICES
        backend = SLICES(relax_model='m3gnet')
        print("✓ SLICES backend initialization")
    except Exception as e:
        print(f"✗ SLICES backend initialization: {e}")
        all_ok = False
    
    print()
    print("=" * 60)
    if all_ok:
        print("✓ Installation validation passed!")
        return 0
    else:
        print("✗ Some checks failed. Please install missing dependencies.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

