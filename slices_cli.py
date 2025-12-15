#!/usr/bin/env python3
"""
SLICES Command Line Interface

Simplified Line-Input Crystal-Encoding System (SLICES) CLI for encoding and decoding
crystal structures.

Usage:
    slices encode <input_file> [--output <output_file>] [--model <model>]
    slices decode <slices_file> [--output <output_file>] [--model <model>]
    slices validate <slices_file>
    slices canonicalize <slices_file> [--output <output_file>]
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from slices.core import SLICES
from pymatgen.core.structure import Structure


def encode_structure(input_file, output_file=None, model='m3gnet'):
    """Encode a crystal structure to SLICES string."""
    print(f"Loading structure from {input_file}...")
    structure = Structure.from_file(input_file)
    
    print(f"Initializing SLICES with {model}...")
    backend = SLICES(relax_model=model)
    
    print("Encoding structure to SLICES...")
    slices_string = backend.structure2SLICES(structure)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(slices_string)
        print(f"SLICES string saved to {output_file}")
    else:
        print("\nSLICES string:")
        print(slices_string)
    
    return slices_string


def decode_slices(slices_file, output_file=None, model='m3gnet', use_robust=False):
    """Decode a SLICES string to crystal structure."""
    print(f"Loading SLICES string from {slices_file}...")
    with open(slices_file, 'r') as f:
        slices_string = f.read().strip()
    
    print(f"Initializing SLICES with {model}...")
    backend = SLICES(relax_model=model)
    
    print("Decoding SLICES string to structure...")
    if use_robust:
        structure, energy = backend.robust_SLICES2structure(slices_string)
    else:
        structure, energy = backend.SLICES2structure(slices_string)
    
    if structure is None:
        print("ERROR: Failed to decode SLICES string")
        return None
    
    print(f"Energy: {energy:.4f} eV/atom")
    print(f"Formula: {structure.formula}")
    
    if output_file:
        structure.to(fmt='cif', filename=output_file)
        print(f"Structure saved to {output_file}")
    
    return structure, energy


def validate_slices(slices_file):
    """Validate a SLICES string."""
    print(f"Loading SLICES string from {slices_file}...")
    with open(slices_file, 'r') as f:
        slices_string = f.read().strip()
    
    backend = SLICES()
    is_valid = backend.check_SLICES(slices_string)
    
    if is_valid:
        print("✓ SLICES string is valid")
        return True
    else:
        print("✗ SLICES string is invalid")
        return False


def canonicalize_slices(slices_file, output_file=None):
    """Canonicalize a SLICES string."""
    print(f"Loading SLICES string from {slices_file}...")
    with open(slices_file, 'r') as f:
        slices_string = f.read().strip()
    
    backend = SLICES()
    canonical = backend.get_canonical_SLICES(slices_string, strategy=4)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(canonical)
        print(f"Canonical SLICES string saved to {output_file}")
    else:
        print("\nCanonical SLICES string:")
        print(canonical)
    
    return canonical


def main():
    parser = argparse.ArgumentParser(
        description="SLICES: Simplified Line-Input Crystal-Encoding System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Encode a structure
  slices encode structure.cif --output structure.slices
  
  # Decode a SLICES string
  slices decode structure.slices --output reconstructed.cif
  
  # Validate a SLICES string
  slices validate structure.slices
  
  # Canonicalize a SLICES string
  slices canonicalize structure.slices --output canonical.slices
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Encode command
    encode_parser = subparsers.add_parser('encode', help='Encode structure to SLICES')
    encode_parser.add_argument('input_file', help='Input structure file (CIF, POSCAR, etc.)')
    encode_parser.add_argument('--output', '-o', help='Output SLICES file')
    encode_parser.add_argument('--model', '-m', default='m3gnet',
                              choices=['m3gnet', 'chgnet', 'mattersim', 'orbv3'],
                              help='MLIP model for relaxation (default: m3gnet)')
    
    # Decode command
    decode_parser = subparsers.add_parser('decode', help='Decode SLICES to structure')
    decode_parser.add_argument('slices_file', help='Input SLICES file')
    decode_parser.add_argument('--output', '-o', help='Output structure file (CIF format)')
    decode_parser.add_argument('--model', '-m', default='m3gnet',
                              choices=['m3gnet', 'chgnet', 'mattersim', 'orbv3'],
                              help='MLIP model for relaxation (default: m3gnet)')
    decode_parser.add_argument('--robust', action='store_true',
                              help='Use robust decoding strategy')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate SLICES string')
    validate_parser.add_argument('slices_file', help='SLICES file to validate')
    
    # Canonicalize command
    canonicalize_parser = subparsers.add_parser('canonicalize', help='Canonicalize SLICES string')
    canonicalize_parser.add_argument('slices_file', help='Input SLICES file')
    canonicalize_parser.add_argument('--output', '-o', help='Output canonical SLICES file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'encode':
            encode_structure(args.input_file, args.output, args.model)
        elif args.command == 'decode':
            decode_slices(args.slices_file, args.output, args.model, args.robust)
        elif args.command == 'validate':
            validate_slices(args.slices_file)
        elif args.command == 'canonicalize':
            canonicalize_slices(args.slices_file, args.output)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

