"""Encode and reconstruct NdSiRu between crystal structure and SLICES string."""

from __future__ import annotations

import os
from pathlib import Path

from pymatgen.core.structure import Structure

from slices.core import SLICES


def main() -> None:
    """Run an encode-decode SLICES round-trip on the example NdSiRu structure."""
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

    cif_path = Path(__file__).resolve().parent / "NdSiRu.cif"
    original_structure = Structure.from_file(filename=str(cif_path))

    # Initialize SLICES with relax_model="auto" (NequIP force field).
    backend = SLICES()

    # Convert the crystal structure to its SLICES string.
    slices_ndsiru = backend.structure2SLICES(original_structure)

    # Reconstruct the crystal structure and compute its force-field energy per atom.
    # If final_energy_per_atom_iap is 0, force-field relaxation failed and the
    # returned structure is the unrelaxed ZL*-optimized geometry.
    reconstructed_structure, final_energy_per_atom_iap = backend.SLICES2structure(slices_ndsiru)

    print("SLICES string of NdSiRu is: ", slices_ndsiru)
    print("\nOriginal_structure is: ", original_structure)
    print("\nReconstructed_structure is: ", reconstructed_structure)
    print("\nfinal_energy_per_atom_IAP is: ", final_energy_per_atom_iap, " eV/atom")


if __name__ == "__main__":
    main()
