"""Unit tests for SLICES crystal structure encoding, augmentation, and dimensionality."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pytest
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from slices.core import SLICES


@pytest.mark.unit
@pytest.mark.parametrize("strategy", [1, 2, 3, 4])
def test_structure2slices_all_strategies(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
    strategy: int,
) -> None:
    """Encode NdSiRu across strategies 1-4 and verify format invariants."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=strategy)
    assert isinstance(sli, str)
    assert len(sli.strip()) > 0

    if strategy == 2:
        assert " " not in sli.strip()
        assert "Nd" in sli and "Si" in sli and "Ru" in sli
    elif strategy == 4:
        tokens = sli.strip().split()
        first_elem_idx = SLICES._first_element_index(tokens)
        assert first_elem_idx is not None and first_elem_idx > 0
    else:
        assert "Nd" in sli.split()


@pytest.mark.unit
def test_get_slices_by_strategy_invalid_raises(slices_no_relax: SLICES) -> None:
    """Verify get_slices_by_strategy raises ValueError on an unknown strategy code."""
    atoms = ["Si", "O"]
    edges = np.array([[0, 1]], dtype=int)
    jimages = np.array([[0, 0, 0]], dtype=int)
    with pytest.raises(ValueError, match="Unknown strategy"):
        slices_no_relax.get_slices_by_strategy(99, atoms, edges, jimages, 1)


@pytest.mark.unit
@pytest.mark.parametrize("graph_method", ["econnn", "crystalnn", "brunnernn", "mininn"])
def test_encoding_valid_graph_methods(
    ndsiru_structure: Structure,
    graph_method: str,
) -> None:
    """Encode NdSiRu with each of the four supported local-environment graph methods."""
    backend = SLICES(graph_method=graph_method, relax_model=None)
    sli = backend.structure2SLICES(ndsiru_structure, strategy=4)
    assert backend.check_SLICES(sli, strategy=4) is True


@pytest.mark.unit
def test_from_cif_matches_structure2crystal_graph_rep(
    slices_no_relax: SLICES,
    examples_dir: Path,
    ndsiru_structure: Structure,
) -> None:
    """Verify from_cif and structure2crystal_graph_rep produce identical graph arrays."""
    cif_text = (examples_dir / "NdSiRu.cif").read_text(encoding="utf-8")
    slices_no_relax.from_cif(cif_text)
    sli_from_cif = slices_no_relax.to_SLICES(strategy=4)

    atom_types, edge_indices, to_jimages, sg_num = slices_no_relax.structure2crystal_graph_rep(
        ndsiru_structure
    )
    assert sg_num == 129
    assert slices_no_relax.space_group_num == 129
    np.testing.assert_array_equal(slices_no_relax.atom_types, atom_types)
    np.testing.assert_array_equal(slices_no_relax.edge_indices, edge_indices)
    np.testing.assert_array_equal(slices_no_relax.to_jimages, to_jimages)
    assert sli_from_cif == slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)


@pytest.mark.unit
def test_to_primitive_if_smaller_reduces_conventional_cells(
    slices_no_relax: SLICES,
    sr3ru2o7_structure: Structure,
) -> None:
    """Verify to_primitive_if_smaller shrinks reducible conventional cells only."""
    bcc_na_conv = Structure(
        Lattice.cubic(4.23),
        ["Na", "Na"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
    )
    bcc_na_prim = SLICES.to_primitive_if_smaller(bcc_na_conv)
    assert len(bcc_na_conv) == 2
    assert len(bcc_na_prim) == 1
    assert bcc_na_prim.composition.reduced_formula == "Na"

    unchanged = SLICES.to_primitive_if_smaller(bcc_na_prim)
    assert unchanged is bcc_na_prim
    assert len(unchanged) == 1

    sr_conv = SpacegroupAnalyzer(sr3ru2o7_structure).get_conventional_standard_structure()
    sr_prim = SLICES.to_primitive_if_smaller(sr_conv)
    assert len(sr_conv) == 24
    assert len(sr_prim) == 12
    atom_types, _, _, _ = slices_no_relax.structure2crystal_graph_rep(sr_conv)
    assert len(atom_types) == 12


@pytest.mark.unit
def test_structure2random_slices_determinism_and_uniqueness(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify seeded structure2randomSLICES produces unique, canonical-equivalent strings."""
    random.seed(42)
    aug_first = slices_no_relax.structure2randomSLICES(ndsiru_structure, strategy=4, num=12)
    random.seed(42)
    aug_second = slices_no_relax.structure2randomSLICES(ndsiru_structure, strategy=4, num=12)

    assert aug_first == aug_second
    assert len(aug_first) == 12
    assert len(set(aug_first)) == 12

    canonical_ref = slices_no_relax.get_canonical_SLICES(aug_first[0], strategy=4)
    for sli in aug_first:
        assert slices_no_relax.check_SLICES(sli, strategy=4) is True
        assert slices_no_relax.get_canonical_SLICES(sli, strategy=4) == canonical_ref


@pytest.mark.unit
def test_structure2slices_aug_atom_order_preserves_bond_order_and_jimages(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify structure2SLICESAug_atom_order permutes atom order without flipping bonds."""
    base_sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    random.seed(7)
    aug_list = slices_no_relax.structure2SLICESAug_atom_order(
        ndsiru_structure, strategy=4, num=10
    )
    assert 1 < len(aug_list) <= 10
    assert len(set(aug_list)) == len(aug_list)

    def extract_jimage_tokens(sli: str) -> list[str]:
        tokens = sli.strip().split()
        first_elem = SLICES._first_element_index(tokens)
        assert first_elem is not None
        first_num = next(i for i in range(first_elem, len(tokens)) if tokens[i].isnumeric())
        edge_tokens = tokens[first_num:]
        return [edge_tokens[idx + 2] for idx in range(0, len(edge_tokens), 3)]

    expected_jimages = extract_jimage_tokens(base_sli)
    canonical_ref = slices_no_relax.get_canonical_SLICES(base_sli, strategy=4)
    for sli in aug_list:
        assert extract_jimage_tokens(sli) == expected_jimages
        assert slices_no_relax.get_canonical_SLICES(sli, strategy=4) == canonical_ref


@pytest.mark.unit
def test_check_element_z87_boundary(ndsiru_structure: Structure) -> None:
    """Verify check_element accepts Z <= 86 (Rn) and rejects Z >= 87 (Fr, Th)."""
    rn_struct = Structure(Lattice.cubic(5.0), ["Rn"], [[0.0, 0.0, 0.0]])
    fr_struct = Structure(Lattice.cubic(5.0), ["Fr"], [[0.0, 0.0, 0.0]])
    mixed_actinide = Structure(
        Lattice.cubic(5.0),
        ["Si", "Th"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
    )

    assert SLICES.check_element(ndsiru_structure) is True
    assert SLICES.check_element(rn_struct) is True
    assert SLICES.check_element(fr_struct) is False
    assert SLICES.check_element(mixed_actinide) is False


@pytest.mark.unit
def test_dimensionality_helpers_2d_and_3d(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify get_dim, check_2D, and check_3D distinguish 2D sheets from 3D networks."""
    assert slices_no_relax.get_dim(ndsiru_structure) == 3
    assert slices_no_relax.check_3D(ndsiru_structure) is True
    assert slices_no_relax.check_2D(ndsiru_structure) is False

    graphene_2d = Structure(
        Lattice.hexagonal(2.46, 20.0),
        ["C", "C"],
        [[0.0, 0.0, 0.5], [1.0 / 3.0, 2.0 / 3.0, 0.5]],
    )
    backend_mininn = SLICES(graph_method="mininn", relax_model=None)
    assert backend_mininn.get_dim(graphene_2d) == 2
    assert backend_mininn.check_2D(graphene_2d) is True
    assert backend_mininn.check_3D(graphene_2d) is False
