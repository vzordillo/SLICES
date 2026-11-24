"""Unit tests for SLICES syntax validation, structural validity, and canonicalization."""

from __future__ import annotations

import random

import pytest
from pymatgen.core.composition import Composition
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from slices import check_SLICES as top_level_check_slices
from slices.core import SLICES


@pytest.mark.unit
@pytest.mark.parametrize("strategy", [1, 3, 4])
def test_check_slices_accepts_valid_encoded_strings(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
    strategy: int,
) -> None:
    """Verify check_SLICES returns True for valid Strategy 1, 3, and 4 encodings."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=strategy)
    assert slices_no_relax.check_SLICES(sli, strategy=strategy) is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_sli",
    [
        "",
        "foo bar baz",
        "q q q Si O 0 1 ooo",
        "Si O 0 5 ooo",
        "Si O 0 1 oox",
        "Si O 0 1 ooo 0 1 +oo",
        "Si O 0 1 ooo 0 1 +oo 0 1 o+o",
        "Si O C 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+",
        "Si O 0 1 ooo 0 1 +oo 0 1 -oo 0 1 ++o",
    ],
)
def test_check_slices_rejects_invalid_and_rank_deficient_graphs(
    slices_no_relax: SLICES,
    invalid_sli: str,
) -> None:
    """Verify check_SLICES rejects malformed, disconnected, collinear, and H1 < 3 strings."""
    assert slices_no_relax.check_SLICES(invalid_sli, strategy=4) is False


@pytest.mark.unit
def test_check_slices_dupli_check_and_graph_rank_flags(slices_no_relax: SLICES) -> None:
    """Verify dupli_check and graph_rank_check flags control duplicate and rank checks."""
    dup_flipped = "Si O 0 1 ooo 1 0 ooo 0 1 +oo 0 1 o+o 0 1 oo+"
    assert slices_no_relax.check_SLICES(dup_flipped, strategy=4, dupli_check=False) is True
    assert slices_no_relax.check_SLICES(dup_flipped, strategy=4, dupli_check=True) is False

    low_rank_3d_labels = "Si O C 0 1 +oo 1 2 o+o 0 2 oo+"
    assert (
        slices_no_relax.check_SLICES(
            low_rank_3d_labels, strategy=4, graph_rank_check=True
        )
        is False
    )


@pytest.mark.unit
def test_check_slices_basic_syntax_and_node_coverage(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify check_SLICES_basic checks parsing and atom coverage without rank checks."""
    valid_sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    assert slices_no_relax.check_SLICES_basic(valid_sli, strategy=4) is True
    assert slices_no_relax.check_SLICES_basic("Si O 0 1 ooo 0 1 +oo", strategy=4) is True
    assert slices_no_relax.check_SLICES_basic("Si O C 0 1 ooo", strategy=4) is False
    assert slices_no_relax.check_SLICES_basic("Si O 0 9 ooo", strategy=4) is False


@pytest.mark.unit
def test_check_structural_validity_distance_threshold(
    ndsiru_structure: Structure,
) -> None:
    """Verify check_structural_validity enforces pairwise interatomic distance > 0.5 A."""
    assert bool(SLICES.check_structural_validity(ndsiru_structure)) is True

    single_atom = Structure(Lattice.cubic(3.5), ["Na"], [[0.0, 0.0, 0.0]])
    assert bool(SLICES.check_structural_validity(single_atom)) is True

    overlapping = Structure(
        Lattice.cubic(5.0),
        ["Si", "O"],
        [[0.0, 0.0, 0.0], [0.02, 0.0, 0.0]],
    )
    assert bool(SLICES.check_structural_validity(overlapping)) is False

    exact_half_angstrom = Structure(
        Lattice.cubic(5.0),
        ["Si", "O"],
        [[0.0, 0.0, 0.0], [0.10, 0.0, 0.0]],
    )
    assert bool(SLICES.check_structural_validity(exact_half_angstrom)) is False


@pytest.mark.unit
def test_get_canonical_slices_idempotence_and_permutation_invariance(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify get_canonical_SLICES is idempotent and invariant to graph permutations."""
    sli4 = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    canon4 = slices_no_relax.get_canonical_SLICES(sli4, strategy=4)
    assert slices_no_relax.get_canonical_SLICES(canon4, strategy=4) == canon4

    random.seed(123)
    augmented = slices_no_relax.structure2randomSLICES(ndsiru_structure, strategy=4, num=10)
    for aug in augmented:
        assert slices_no_relax.get_canonical_SLICES(aug, strategy=4) == canon4

    for strategy in (1, 3):
        sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=strategy)
        canon = slices_no_relax.get_canonical_SLICES(sli, strategy=strategy)
        assert slices_no_relax.get_canonical_SLICES(canon, strategy=strategy) == canon


@pytest.mark.unit
def test_slices2formula_and_space_group_number(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify SLICES2formula and SLICES2space_group_number extract expected metadata."""
    sli4 = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    sli3 = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=3)

    formula4 = slices_no_relax.SLICES2formula(sli4)
    formula3 = slices_no_relax.SLICES2formula(sli3)
    assert formula4 is not None and " " not in formula4
    assert formula4 == formula3
    assert Composition(formula4).reduced_formula == ndsiru_structure.composition.reduced_formula

    sg_num = slices_no_relax.SLICES2space_group_number(sli4, strategy=4)
    assert sg_num == 129
    assert slices_no_relax.SLICES2space_group_number("invalid slices", strategy=4) is None


@pytest.mark.unit
def test_top_level_check_slices_helper(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify top-level slices.check_SLICES convenience function matches SLICES.check_SLICES."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    assert top_level_check_slices(sli, strategy=4) is True
    assert top_level_check_slices("Si O 0 1 ooo", strategy=4) is False
