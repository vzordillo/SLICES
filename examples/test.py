"""Decode a sample strategy-3 SLICES string to a relaxed CIF structure."""

from __future__ import annotations

from slices.core import SLICES


def main() -> None:
    """Reconstruct a quaternary Sb-Ti-Ir SLICES string and export it to ``1.cif``."""
    backend = SLICES()  # relax_model="auto": NequIP force field, GPU if available
    slices_str = (
        "Sb Ti Ti Ir 0 2 oo- 0 2 ooo 0 2 o-o 0 2 -oo "
        "0 3 ooo 0 3 o-o 0 3 oo- 0 3 -o- "
        "1 2 ooo 1 2 oo- 1 2 o-- 1 2 o-o "
        "1 3 ooo 1 3 o-- 1 3 o-o 1 3 -o- "
    )

    # If final_energy_per_atom_iap is 0, force-field relaxation failed and the
    # returned structure is the unrelaxed ZL*-optimized geometry.
    reconstructed_structure, final_energy_per_atom_iap = backend.SLICES2structure(slices_str)

    print("\nReconstructed_structure is: ", reconstructed_structure)
    print("\nfinal_energy_per_atom_IAP is: ", final_energy_per_atom_iap, " eV/atom")
    reconstructed_structure.to(filename="1.cif")


if __name__ == "__main__":
    main()
