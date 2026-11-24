"""Demonstrate SLICES data augmentation and canonical SLICES reduction on Sr3Ru2O7."""

from __future__ import annotations

from pathlib import Path

from pymatgen.core.structure import Structure

from slices.core import SLICES


def main() -> None:
    """Generate augmented SLICES strings for Sr3Ru2O7 and collapse them to canonical form."""
    cif_path = Path(__file__).resolve().parent / "Sr3Ru2O7.cif"
    original_structure = Structure.from_file(filename=str(cif_path))

    backend = SLICES(graph_method="econnn")

    # Generate augmented SLICES strings via random atom-order permutations.
    slices_list = backend.structure2randomSLICES(
        structure=original_structure,
        strategy=4,
        num=50,
        shuffle_bond_order=False,
        flip_bonds=False,
    )
    slices_list_unique = list(set(slices_list))

    canonical_slices_list = [
        backend.get_canonical_SLICES(slices_str, strategy=4) for slices_str in slices_list_unique
    ]

    # All augmented SLICES representations collapse to 1 canonical SLICES string.
    print(len(slices_list), len(set(canonical_slices_list)))


if __name__ == "__main__":
    main()
