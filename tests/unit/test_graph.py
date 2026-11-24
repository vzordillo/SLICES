"""Unit tests for periodic Net topology, SystreDB parsing, and space-group encodings."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pymatgen.core.periodic_table import Element
from pymatgen.core.structure import Structure

from slices.core import SLICES
from slices.tobascco_net import Net, SystreDB
from slices.utils_wyckoff import (
    get_space_group_num_from_letter_enc,
    get_tokenized_enc,
    sg_encoding,
)


@pytest.mark.unit
def test_net_pcu_single_vertex_basis_and_barycentric_embedding() -> None:
    """Verify 1-vertex primitive cubic net yields cocycle=None and identity metric tensor."""
    edges = [
        ("1", "1", {"label": "e1"}),
        ("1", "1", {"label": "e2"}),
        ("1", "1", {"label": "e3"}),
    ]
    net = Net(edges, dim=3)
    net.voltage = np.eye(3, dtype=int)

    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1
    net.get_cocycle_basis()
    assert net.cocycle is None
    assert net.cocycle_rep is None

    net.barycentric_embedding()
    assert net.metric_tensor is not None
    assert net.metric_tensor.shape == (3, 3)
    assert np.linalg.det(net.metric_tensor) > 0.0


@pytest.mark.unit
def test_net_rank_deficient_get_lattice_basis_returns_minus_one() -> None:
    """Verify Net.get_lattice_basis returns -1 (DEF-003) on a 1D rank-deficient graph."""
    edges = [
        ("1", "2", {"label": "e1"}),
        ("1", "2", {"label": "e2"}),
    ]
    net = Net(edges, dim=3)
    net.voltage = np.array([[0, 0, 0], [1, 0, 0]], dtype=int)

    net.simple_cycle_basis()
    status = net.get_lattice_basis()
    assert status == -1
    assert net.lattice_basis is None


@pytest.mark.unit
def test_net_multinode_clear_cache_and_networkx3_iterators(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify Net.clear_cache and nodes_iter/edges_iter on a multi-vertex crystal net."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    slices_no_relax.from_SLICES(sli, strategy=4)
    x_dat, net_voltage = slices_no_relax.convert_graph()

    net = Net(x_dat, dim=3)
    net.voltage = net_voltage
    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1
    net.get_cocycle_basis()
    net.barycentric_embedding()

    assert net.cocycle_rep is not None
    assert net.cocycle_rep.shape == (net.order - 1, 3)
    metric_before = net.metric_tensor.copy()
    _ = net.cycle_cocycle_I
    assert hasattr(net, "_cycle_cocycle_I")

    nodes_with_data = list(net.nodes_iter(data=True))
    nodes_plain = list(net.nodes_iter(data=False))
    edges_with_data = list(net.edges_iter(data=True))
    edges_plain = list(net.edges_iter(data=False))
    assert len(nodes_with_data) == 6 and len(nodes_plain) == 6
    assert all(isinstance(item[1], dict) for item in nodes_with_data)
    assert len(edges_with_data) == len(x_dat) and len(edges_plain) == len(x_dat)

    net.clear_cache()
    assert net.cycle is None
    assert net.cocycle is None
    assert net.lattice_basis is None
    assert net.metric_tensor is None
    assert not hasattr(net, "_kernel")
    assert not hasattr(net, "_cycle_cocycle_I")
    assert net.graph.number_of_nodes() == 6

    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1
    net.get_cocycle_basis()
    net.barycentric_embedding()
    np.testing.assert_allclose(net.metric_tensor, metric_before, atol=1e-12)


@pytest.mark.unit
def test_systredb_parses_arc_archive(tmp_path: Path) -> None:
    """Verify SystreDB parses a 3D Systre .arc net archive into Net-compatible inputs."""
    arc_path = tmp_path / "pcu.arc"
    arc_path.write_text(
        "id pcu\nkey 3 1 1 1 0 0 1 1 0 1 0 1 1 0 0 1\nend\n",
        encoding="utf-8",
    )
    db = SystreDB(str(arc_path))
    assert "pcu" in db
    assert len(db["pcu"]) == 3
    np.testing.assert_array_equal(db.voltages["pcu"], np.eye(3, dtype=int))

    net = Net(db["pcu"], dim=3)
    net.voltage = db.voltages["pcu"]
    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1


@pytest.mark.unit
def test_utils_wyckoff_full_230_space_group_bijection() -> None:
    """Verify exact 1-230 space-group token bijection and zero chemical element collisions."""
    assert len(sg_encoding) >= 230
    seen_encodings: set[str] = set()

    for sg_num in range(1, 231):
        tokenized = get_tokenized_enc(sg_num)
        assert isinstance(tokenized, str) and len(tokenized) > 0
        seen_encodings.add(tokenized)

        for token in tokenized.split():
            with pytest.raises(ValueError):
                Element(token)

        compact = tokenized.replace(" ", "")
        assert get_space_group_num_from_letter_enc(compact) == sg_num

    assert len(seen_encodings) == 230

    with pytest.raises(ValueError, match="not found"):
        get_tokenized_enc(0)
    with pytest.raises(ValueError, match="not found"):
        get_tokenized_enc(231)
    with pytest.raises(ValueError, match="not found"):
        get_space_group_num_from_letter_enc("NOT_A_VALID_ENC")
