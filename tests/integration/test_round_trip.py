"""End-to-end round-trip integration tests using GFN-FF and NequIP-OAM relaxation."""

from __future__ import annotations

import random

import numpy as np
import pytest
from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from slices.core import SLICES


def _element_matcher() -> StructureMatcher:
    """Construct a primitive-cell StructureMatcher using neutral ElementComparator."""
    return StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
        comparator=ElementComparator(),
    )


@pytest.mark.integration
def test_ndsiru_round_trip_nequip_auto(
    slices_nequip: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify full Strategy 4 encode-decode round-trip on NdSiRu with NequIP auto."""
    sli = slices_nequip.structure2SLICES(ndsiru_structure, strategy=4)
    assert slices_nequip.check_SLICES(sli, strategy=4) is True

    slices_nequip.from_SLICES(sli, strategy=4)
    structures, energy = slices_nequip.to_structures()
    assert len(structures) == 3
    assert np.isfinite(energy) and energy < 0.0

    std_struct, opt_struct, opt2_struct = structures
    assert bool(_element_matcher().fit(ndsiru_structure, opt2_struct)) is True

    match_res = slices_nequip.match_check3(
        ndsiru_structure, opt2_struct, opt_struct, std_struct
    )
    assert match_res[0] == "1"


@pytest.mark.integration
def test_sr3ru2o7_conventional_to_primitive_round_trip(
    slices_nequip: SLICES,
    sr3ru2o7_structure: Structure,
) -> None:
    """Verify 24-atom conventional Sr3Ru2O7 encodes/decodes as its 12-atom primitive cell."""
    sr_conv = SpacegroupAnalyzer(sr3ru2o7_structure).get_conventional_standard_structure()
    expected_prim = SLICES.to_primitive_if_smaller(sr_conv)
    assert len(sr_conv) == 24
    assert len(expected_prim) == 12

    sli = slices_nequip.structure2SLICES(sr_conv, strategy=4)
    reconstructed, energy = slices_nequip.SLICES2structure(sli, strategy=4)

    assert len(reconstructed) == len(expected_prim) == 12
    assert np.isfinite(energy) and energy < 0.0
    assert bool(_element_matcher().fit(sr_conv, reconstructed)) is True


@pytest.mark.integration
@pytest.mark.parametrize("strategy", [1, 3, 4])
def test_decodable_strategies_round_trip_equivalence(
    slices_nequip: SLICES,
    strategy: int,
) -> None:
    """Verify Strategies 1, 3, and 4 round-trip cleanly on a cubic CsCl crystal."""
    cscl = Structure(
        Lattice.cubic(4.12),
        ["Cs", "Cl"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
    )
    sli = slices_nequip.structure2SLICES(cscl, strategy=strategy)
    reconstructed, energy = slices_nequip.SLICES2structure(sli, strategy=strategy)

    assert len(reconstructed) == 2
    assert np.isfinite(energy) and energy < 0.0
    assert bool(_element_matcher().fit(cscl, reconstructed)) is True


@pytest.mark.integration
def test_canonical_and_augmented_slices_round_trip_invariance(
    slices_nequip: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify canonicalized and augmented SLICES strings decode to matching structures."""
    base_sli = slices_nequip.structure2SLICES(ndsiru_structure, strategy=4)
    canonical_sli = slices_nequip.get_canonical_SLICES(base_sli, strategy=4)

    random.seed(19)
    augmented = slices_nequip.structure2randomSLICES(ndsiru_structure, strategy=4, num=5)
    for aug in augmented:
        assert slices_nequip.get_canonical_SLICES(aug, strategy=4) == canonical_sli

    decoded_canon, energy_canon = slices_nequip.SLICES2structure(canonical_sli, strategy=4)
    assert np.isfinite(energy_canon) and energy_canon < 0.0
    assert bool(_element_matcher().fit(ndsiru_structure, decoded_canon)) is True


@pytest.mark.integration
def test_opt_in_robust_slices2structure_parity_on_valid_input(
    slices_nequip: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify opt-in robust_SLICES2structure matches standard SLICES2structure on clean input."""
    sli = slices_nequip.structure2SLICES(ndsiru_structure, strategy=4)
    std_decoded, std_energy = slices_nequip.SLICES2structure(sli, strategy=4)
    rob_decoded, rob_energy = slices_nequip.robust_SLICES2structure(sli, strategy=4)

    assert np.isclose(rob_energy, std_energy, atol=1e-12)
    assert bool(_element_matcher().fit(std_decoded, rob_decoded)) is True
