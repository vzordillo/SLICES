"""Comprehensive regression suite for all 15 Wave 1 (SAFE_NOW) fixes.

Covers memory-safety bounds in ``gfnff_helper`` (DEF-028), ``np.matrix`` and
global ``np.random`` removal plus stateless defaults in ``tobascco_net``
(DEF-004, DEF-010, DEF-011, DEF-034), environment and warning scoping across
``core`` and ``relax_backends`` (DEF-005, DEF-009), instance-reuse space-group
purity (DEF-023), periodic self-image structural validity (DEF-019, DEF-025),
``func_check`` zero-distance clamping (DEF-027), large-cell relaxation forwarding
(DEF-008), multi-strategy ``SLICES2formula`` parsing (DEF-012), empty-structure
and ``graph_method`` validation (DEF-018, DEF-026), ``from_SLICES`` parser
guards (DEF-024), topology/angle/pair guards (DEF-021, DEF-030, DEF-032), and
dual-inheritance exception contracts.
"""

from __future__ import annotations

import ast
import contextlib
import inspect
import io
import json
import math
import os
import subprocess
import sys
import types
import warnings
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pytest
from ase.build import bulk
from pymatgen.core import IStructure, Lattice, Structure
from pymatgen.core.composition import Composition

import slices.core as core_mod
from slices.core import SLICES, VALID_GRAPH_METHODS
from slices.exceptions import (
    CocycleBasisError,
    GFNFFExecutionError,
    GraphTopologyError,
    LatticeBasisError,
    ModelDownloadError,
    RelaxBackendError,
    SLICESDecodingError,
    SLICESEncodingError,
    SLICESError,
)
from slices.gfnff_helper import parse_nbf_text, run_gfnff_helper
from slices.relax_backends import _cell_filter
from slices.tobascco_net import Net

pytestmark = [
    pytest.mark.regression,
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:spglib\..*"),
]


def _load_golden_metadata(repo_root: Path) -> dict[str, Any]:
    """Load golden baseline metadata JSON for canonical G01, G18, and E11 strings."""
    meta_path = repo_root / "tests" / "baseline" / "fixtures" / "golden_metadata.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _two_atom_nbf(sym_a: str, sym_b: str = "O") -> str:
    """Construct a minimal valid 22-line 2-atom NBF neighbor table."""
    return f"2\n{sym_a} {sym_b}\n2 1\n" + "0 0\n" * 18 + "1 1\n"


def test_def028_gfnff_atomic_number_bounds_guard() -> None:
    """Verify DEF-028 enforces 1 <= Z <= 103 in parse_nbf_text and run_gfnff_helper."""
    for sym, expected_z in (("Th", 90), ("Lr", 103)):
        nbf = _two_atom_nbf(sym, "O")
        z_arr, table = parse_nbf_text(nbf)
        assert list(z_arr) == [expected_z, 8]
        assert table.shape == (20, 2)
        topo = run_gfnff_helper(nbf)
        assert len(topo["blist"]) == 1
        assert np.all(np.isfinite(np.asarray(topo["vbond"], dtype=float)))

    for sym, expected_z in (("Rf", 104), ("Db", 105), ("Og", 118)):
        nbf = _two_atom_nbf(sym, "O")
        for fn in (parse_nbf_text, run_gfnff_helper):
            with pytest.raises(GFNFFExecutionError) as exc_info:
                fn(nbf)
            msg = str(exc_info.value)
            assert sym in msg
            assert str(expected_z) in msg

    with pytest.raises(ValueError, match="Unknown chemical element"):
        parse_nbf_text(_two_atom_nbf("NotAnElement", "O"))


def test_def011_def034_no_np_matrix_and_linear_independent_vectors_bounds(
    repo_root: Path,
) -> None:
    """Verify DEF-011/DEF-034 remove np.matrix/pinv and guard rectangular rank-deficient inputs."""
    net_source = (repo_root / "src" / "slices" / "tobascco_net.py").read_text(encoding="utf-8")
    tree = ast.parse(net_source)
    attr_names = [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
    assert "matrix" not in attr_names
    assert "asmatrix" not in attr_names
    assert "pinv" not in attr_names
    assert "np.matrix" not in net_source

    net = Net()
    zero_out = net.linear_independent_vectors(np.zeros((3, 3)), 3)
    assert isinstance(zero_out, np.ndarray) and not isinstance(zero_out, np.matrix)
    assert zero_out.shape == (0, 3)

    # Rank-2 (3, 4) matrix with 3 non-collinear adjacent column transitions previously
    # overflowed index = np.zeros(r) with IndexError.
    rect_3x4 = np.array(
        [
            [1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, 0.0],
        ]
    )
    out_dim3 = net.linear_independent_vectors(rect_3x4, 3)
    out_dim4 = net.linear_independent_vectors(rect_3x4, 4)
    assert out_dim3.shape == (2, 3)
    assert out_dim4.shape == (2, 4)

    rect_4x3 = rect_3x4.T
    out_tall = net.linear_independent_vectors(rect_4x3, 3)
    assert out_tall.shape == (2, 3)

    full_sq = np.array([[1.0, 2.0, 0.0], [0.0, 1.0, 3.0], [1.0, 0.0, 1.0]])
    out_sq = net.linear_independent_vectors(full_sq, 3)
    assert out_sq.shape == (3, 3)


def test_def004_net_methods_preserve_global_numpy_rng_state(repo_root: Path) -> None:
    """Verify DEF-004 removes all np.random mutations from Net cycle/lattice methods."""
    net_source = (repo_root / "src" / "slices" / "tobascco_net.py").read_text(encoding="utf-8")
    assert "np.random" not in net_source
    assert "random" not in net_source

    edges = [
        ("1", "2", {"label": "e1"}),
        ("2", "1", {"label": "e2"}),
        ("1", "2", {"label": "e3"}),
        ("2", "1", {"label": "e4"}),
    ]
    net = Net(edges, dim=3)
    net.voltage = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=int)

    np.random.seed(20261125)
    before = np.random.get_state()
    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1
    net.get_cocycle_basis()
    net.barycentric_embedding()
    _ = net.projection
    after = np.random.get_state()

    assert before[0] == after[0]
    assert np.array_equal(before[1], after[1])
    assert before[2:] == after[2:]


def test_def005_def009_env_setdefault_and_scoped_warning_hygiene(repo_root: Path) -> None:
    """Verify DEF-005/DEF-009 honor pre-set env vars and suppress only scoped warnings."""
    atoms = bulk("Cu", "fcc", a=3.65)
    with warnings.catch_warnings(record=True) as local_caught:
        warnings.simplefilter("always")
        filt = _cell_filter(atoms)
    dep_warnings = [w for w in local_caught if issubclass(w.category, DeprecationWarning)]
    assert type(filt).__name__ == "ExpCellFilter"
    assert len(dep_warnings) == 0

    src_dir = str(repo_root / "src")
    cif_path = str(repo_root / "examples" / "NdSiRu.cif")

    # 1. Pre-set OMP_NUM_THREADS="4" must be preserved; PYTHONWARNINGS must stay unset.
    env_preset = os.environ.copy()
    env_preset["PYTHONPATH"] = src_dir
    env_preset["PYTHONDONTWRITEBYTECODE"] = "1"
    env_preset["OMP_NUM_THREADS"] = "4"
    env_preset["TF_CPP_MIN_LOG_LEVEL"] = "1"
    env_preset.pop("PYTHONWARNINGS", None)
    probe_preset = (
        "import os, slices.core\n"
        "assert os.environ['OMP_NUM_THREADS'] == '4'\n"
        "assert os.environ['TF_CPP_MIN_LOG_LEVEL'] == '1'\n"
        "assert 'PYTHONWARNINGS' not in os.environ\n"
    )
    res_preset = subprocess.run(
        [sys.executable, "-c", probe_preset],
        env=env_preset,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_preset.returncode == 0, res_preset.stderr

    # 2. Unset OMP_NUM_THREADS defaults to "1", and _cell_filter / spglib / brunnernn
    # emit 0 DeprecationWarning or FutureWarning without silencing user warnings.
    env_unset = os.environ.copy()
    env_unset["PYTHONPATH"] = src_dir
    env_unset["PYTHONDONTWRITEBYTECODE"] = "1"
    env_unset.pop("OMP_NUM_THREADS", None)
    env_unset.pop("TF_CPP_MIN_LOG_LEVEL", None)
    env_unset.pop("PYTHONWARNINGS", None)
    probe_unset = (
        "import os, warnings\n"
        "import slices.core as core\n"
        "from ase.build import bulk\n"
        "from pymatgen.core import Structure\n"
        "from pymatgen.symmetry.analyzer import SpacegroupAnalyzer\n"
        "from slices.relax_backends import _cell_filter\n"
        "assert os.environ['OMP_NUM_THREADS'] == '1'\n"
        "assert os.environ['TF_CPP_MIN_LOG_LEVEL'] == '3'\n"
        "assert 'PYTHONWARNINGS' not in os.environ\n"
        f"struct = Structure.from_file({cif_path!r})\n"
        "with warnings.catch_warnings(record=True) as rec:\n"
        "    _cell_filter(bulk('Cu', 'fcc', a=3.65))\n"
        "    SpacegroupAnalyzer(struct).get_space_group_number()\n"
        "    s = core.SLICES(graph_method='brunnernn', relax_model=None)\n"
        "    s.structure2structure_graph(struct)\n"
        "    bad = [w for w in rec if issubclass(w.category, (DeprecationWarning, FutureWarning))]\n"
        "    assert len(bad) == 0, [str(w.message) for w in bad]\n"
        "    warnings.warn('caller_dep_probe', DeprecationWarning, stacklevel=1)\n"
        "    assert any('caller_dep_probe' in str(w.message) for w in rec)\n"
    )
    res_unset = subprocess.run(
        [sys.executable, "-W", "default", "-c", probe_unset],
        env=env_unset,
        capture_output=True,
        text=True,
        check=False,
    )
    assert res_unset.returncode == 0, res_unset.stderr


def test_def023_reused_slices_instance_after_unstable_graph_preserves_space_group(
    repo_root: Path,
    slices_no_relax: SLICES,
) -> None:
    """Verify DEF-023 prevents stale unstable_graph state from corrupting space groups."""
    meta = _load_golden_metadata(repo_root)
    g18_s4 = meta["corpus"]["G18"]["canonical_s4"]
    g01_s4 = meta["corpus"]["G01"]["slices_by_strategy"]["4"]

    slices_no_relax.from_SLICES(g18_s4, strategy=4)
    assert slices_no_relax.unstable_graph is False
    slices_no_relax.to_structures()
    assert slices_no_relax.unstable_graph is True

    sg_after_unstable = slices_no_relax.SLICES2space_group_number(g01_s4, strategy=4)
    assert slices_no_relax.unstable_graph is False
    assert sg_after_unstable == 129


def test_def025_def019_check_structural_validity_types_empty_and_periodic_self_images(
    ndsiru_structure: Structure,
) -> None:
    """Verify DEF-019/DEF-025 enforce IStructure type, 0-site False, and periodic self-images."""
    for invalid_arg in ("not_a_structure", None, 123, {"lattice": []}):
        with pytest.raises(TypeError, match="IStructure"):
            SLICES.check_structural_validity(invalid_arg)  # type: ignore[arg-type]

    immutable_ndsiru = IStructure.from_sites(ndsiru_structure)
    assert SLICES.check_structural_validity(immutable_ndsiru) is True

    empty = Structure(Lattice.cubic(5.0), [], [])
    assert SLICES.check_structural_validity(empty) is False

    na_short = Structure(Lattice.cubic(0.3), ["Na"], [[0.0, 0.0, 0.0]])
    na_boundary = Structure(Lattice.cubic(0.5), ["Na"], [[0.0, 0.0, 0.0]])
    na_valid = Structure(Lattice.cubic(0.5001), ["Na"], [[0.0, 0.0, 0.0]])
    assert SLICES.check_structural_validity(na_short) is False
    assert SLICES.check_structural_validity(na_boundary) is False
    assert SLICES.check_structural_validity(na_valid) is True

    # Sheared cell D5: min(abc) == 1.0 A > 0.5 A, yet ||a - b|| == 0.2956 A <= 0.5 A.
    sheared_d5 = Structure(
        Lattice.from_parameters(1.0, 1.0, 5.0, 90.0, 90.0, 17.0),
        ["Na"],
        [[0.0, 0.0, 0.0]],
    )
    assert min(sheared_d5.lattice.abc) == pytest.approx(1.0)
    assert np.linalg.norm(sheared_d5.lattice.matrix[0] - sheared_d5.lattice.matrix[1]) <= 0.5
    assert SLICES.check_structural_validity(sheared_d5) is False


def test_def027_func_check_zero_distance_clamping_on_unstable_g18(
    repo_root: Path,
    slices_no_relax: SLICES,
) -> None:
    """Verify DEF-027 clamps zero-length bonds and non-bonded distances in func_check."""
    meta = _load_golden_metadata(repo_root)
    g18_s4 = meta["corpus"]["G18"]["canonical_s4"]

    slices_no_relax.from_SLICES(g18_s4, strategy=4)
    x_dat, net_voltage = slices_no_relax.convert_graph()
    net = Net(x_dat, dim=3)
    net.voltage = net_voltage
    net.simple_cycle_basis()
    assert net.get_lattice_basis() == 1
    net.get_cocycle_basis()

    target_res = slices_no_relax.get_inner_p_target()
    assert target_res is not None
    inner_p_target, colattice_inds, colattice_weights = target_res
    uncovered_pair = slices_no_relax.get_uncovered_pair(net.graph)
    uncovered_pair_lj = slices_no_relax.get_uncovered_pair_lj(uncovered_pair)
    covered_pair_lj = slices_no_relax.get_covered_pair_lj()

    # Evaluate at cocycle_rep = 0 where G18 has exact zero-length barycentric edges.
    net.cocycle_rep = np.zeros((net.order - 1, net.ndim))
    net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
    net.get_metric_tensor()
    lattice_vectors_std = np.linalg.cholesky(net.metric_tensor)
    arc_coord_std = net.lattice_arcs
    inner_p_std = np.dot(np.dot(arc_coord_std, net.metric_tensor), arc_coord_std.T)
    assert float(np.min(np.diag(inner_p_std))) == 0.0

    lattice_vectors_scaled = slices_no_relax.get_rescaled_lattice_vectors(
        inner_p_target, inner_p_std, lattice_vectors_std, arc_coord_std
    )
    metric_tensor_std = np.dot(lattice_vectors_scaled, lattice_vectors_scaled.T)

    num_nodes = len(net.graph.nodes)
    g_di = nx.MultiDiGraph()
    g_di.add_nodes_from(net.vertices())
    g_di.add_edges_from(net.all_edges())
    edges = list(g_di.edges)
    g_undir = nx.MultiGraph()
    g_undir.add_nodes_from(net.vertices())
    g_undir.add_edges_from(net.all_edges())
    spanning = list(nx.minimum_spanning_edges(g_undir, algorithm="kruskal", data=False))
    for i in range(len(spanning)):
        for j in range(len(edges)):
            if spanning[i][2] == edges[j][2]:
                spanning[i] = edges[j]
    spanning_graph = nx.MultiGraph()
    spanning_graph.add_nodes_from(g_di.nodes)
    spanning_graph.add_edges_from(spanning)
    shortest_path = nx.shortest_path(spanning_graph, source="1")
    atom_symbols = ["H", "H", "O", "O", "O", "O", "Y", "Y"]

    lattice_type = 3
    x_zero, _ = slices_no_relax.initialize_x_bounds(
        net.ndim,
        np.zeros((net.order - 1, net.ndim)),
        metric_tensor_std,
        lattice_type,
        0.005,
        0.45,
        1.25,
        1.0,
    )

    for repul_flag in (True, False):
        common_args = (
            x_zero,
            net.ndim,
            net.order,
            inner_p_target,
            colattice_inds,
            colattice_weights,
            net.cycle_rep,
            net.cycle_cocycle_I,
            num_nodes,
            shortest_path,
            spanning,
            uncovered_pair,
            uncovered_pair_lj,
            covered_pair_lj,
            0.0,
            0.01,
            lattice_vectors_scaled,
            atom_symbols,
            0.5,
            repul_flag,
            lattice_type,
            metric_tensor_std,
        )
        val_func = slices_no_relax.func(*common_args)
        buf = io.StringIO()
        with warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(buf):
            warnings.simplefilter("always")
            val_check = slices_no_relax.func_check(*common_args)
        runtime_warns = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        assert len(runtime_warns) == 0, [str(w.message) for w in runtime_warns]
        assert math.isfinite(val_check)
        assert val_check == pytest.approx(val_func, rel=0.0, abs=1e-12)


def test_def008_relax_large_cell2_forwards_fmax_and_steps_in_both_branches(
    ndsiru_structure: Structure,
) -> None:
    """Verify DEF-008 forwards self.fmax and self.steps in both relax_large_cell2 branches."""
    supercell = ndsiru_structure.copy()
    supercell.make_supercell([2, 2, 2])
    assert len(supercell) == 48

    recorded_calls: list[tuple[float, int]] = []

    class SpyRelaxer:
        """Mock relaxer recording (fmax, steps) keyword arguments."""

        def relax(
            self,
            struc: Structure,
            fmax: float = 0.1,
            steps: int = 500,
        ) -> dict[str, Any]:
            recorded_calls.append((fmax, steps))
            return {
                "final_structure": struc,
                "trajectory": types.SimpleNamespace(energies=[-96.0]),
            }

    for check_flag in (False, True):
        inst = SLICES(
            relax_model=None,
            fmax=0.23,
            steps=37,
            check_results=check_flag,
        )
        inst.relaxer = SpyRelaxer()
        relaxed_struct, energy_per_atom = inst.relax_large_cell2(supercell)
        assert len(relaxed_struct) == 48
        assert energy_per_atom == pytest.approx(-2.0)

    assert recorded_calls == [(0.23, 37), (0.23, 37)]


def test_def010_net_iter_cycles_and_vertex_positions_stateless_defaults() -> None:
    """Verify DEF-010 replaces mutable defaults with None and makes iter_cycles stateless."""
    iter_sig = inspect.signature(Net.iter_cycles)
    for param_name in ("cycle", "used", "nodes_visited", "cycle_baggage"):
        assert iter_sig.parameters[param_name].default is None

    vp_sig = inspect.signature(Net.vertex_positions)
    for param_name in ("pos", "bad_ones"):
        assert vp_sig.parameters[param_name].default is None

    edges = [
        ("1", "2", {"label": "e1"}),
        ("2", "1", {"label": "e2"}),
        ("1", "2", {"label": "e3"}),
        ("2", "1", {"label": "e4"}),
    ]
    net_a = Net(edges, dim=3)
    net_a.voltage = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=int)
    first_cycles = list(net_a.iter_cycles())
    second_cycles = list(net_a.iter_cycles())

    net_b = Net(edges, dim=3)
    net_b.voltage = net_a.voltage.copy()
    fresh_cycles = list(net_b.iter_cycles())

    assert len(first_cycles) == 6
    assert first_cycles == second_cycles == fresh_cycles


def test_def012_slices2formula_all_strategies_and_malformed_inputs(
    repo_root: Path,
    slices_no_relax: SLICES,
) -> None:
    """Verify DEF-012 extracts consistent formulas across Strategies 1-4 and rejects junk."""
    meta = _load_golden_metadata(repo_root)
    g01_by_strategy = meta["corpus"]["G01"]["slices_by_strategy"]

    formulas = {
        strat: slices_no_relax.SLICES2formula(sli)
        for strat, sli in g01_by_strategy.items()
    }
    assert set(formulas.keys()) == {"1", "2", "3", "4"}
    for strat, formula in formulas.items():
        assert formula == "Nd2Si2Ru2", f"Strategy {strat} returned {formula!r}"
        assert formula != "Nd1Si1"
        assert Composition(formula).reduced_formula == "NdSiRu"

    for malformed in ("Si O", "", "   ", "???", "q x z", "123 456"):
        assert slices_no_relax.SLICES2formula(malformed) is None
    assert slices_no_relax.SLICES2formula(None) is None  # type: ignore[arg-type]


def test_def018_empty_structure_raises_slices_encoding_error(
    slices_no_relax: SLICES,
) -> None:
    """Verify DEF-018 raises SLICESEncodingError (and ValueError) on 0-site Structures."""
    empty = Structure(Lattice.cubic(5.0), [], [])

    for call in (
        lambda: SLICES.to_primitive_if_smaller(empty),
        lambda: slices_no_relax.structure2structure_graph(empty),
        lambda: slices_no_relax.structure2SLICES(empty),
        lambda: slices_no_relax.structure2randomSLICES(empty, num=2),
        lambda: SLICES.check_element(empty),
    ):
        with pytest.raises(SLICESEncodingError) as exc_info:
            call()
        assert isinstance(exc_info.value, ValueError)


def test_def026_invalid_graph_method_validation(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify DEF-026 validates graph_method in __init__, structure2structure_graph, and get_dim."""
    assert VALID_GRAPH_METHODS == ("econnn", "crystalnn", "brunnernn", "mininn")

    with pytest.raises(ValueError, match="Unsupported graph_method"):
        SLICES(graph_method="econ", relax_model=None)

    slices_no_relax.graph_method = "bogus"
    with pytest.raises(ValueError, match="Unsupported graph_method"):
        slices_no_relax.structure2structure_graph(ndsiru_structure)
    with pytest.raises(ValueError, match="Unsupported graph_method"):
        slices_no_relax.get_dim(ndsiru_structure)


def test_def024_from_slices_strategy_and_token_guards_preserving_golden_errors(
    slices_no_relax: SLICES,
) -> None:
    """Verify DEF-024 guards strategy=2/invalid, zero-edge strings, bounds, and 4-char labels."""
    for bad_strategy in (2, 99, 0, -1):
        with pytest.raises(SLICESDecodingError) as exc_info:
            slices_no_relax.from_SLICES("Si O 0 1 ooo", strategy=bad_strategy)
        assert isinstance(exc_info.value, ValueError)

    for strat in (1, 3, 4):
        with pytest.raises(SLICESDecodingError) as exc_info:
            slices_no_relax.from_SLICES("Si O", strategy=strat)
        assert isinstance(exc_info.value, ValueError)

    # Negative and out-of-range atom indices preserve exact golden error text.
    for s_bad_idx, strat in (
        ("Si O -1 1 ooo", 4),
        ("Si O 0 5 ooo", 4),
        ("Si O -1 1 o o o", 3),
        ("Si O 0 5 o o o", 3),
        ("Si O -1 1 o o o", 1),
    ):
        with pytest.raises(Exception) as exc_idx:
            slices_no_relax.from_SLICES(s_bad_idx, strategy=strat)
        assert str(exc_idx.value) == "Error: wrong edge indices"

    # Strategy 4 label length != 3 and bad characters preserve exact golden error text.
    for s_bad_lbl in ("Si O 0 1 oooo", "Si O 0 1 oo", "Si O 0 1 oox"):
        with pytest.raises(Exception) as exc_lbl:
            slices_no_relax.from_SLICES(s_bad_lbl, strategy=4)
        assert str(exc_lbl.value) == "Error: wrong edge label"

    # Trailing partial edge tokens remain lenient for HTS PBE compatibility.
    slices_no_relax.from_SLICES("Si O 0 1 ooo 0 1 +oo 0 1", strategy=4)
    assert slices_no_relax.edge_indices is not None
    assert len(slices_no_relax.edge_indices) == 2

    slices_no_relax.from_SLICES("Si O 0 1 o o o 0 1 + o", strategy=3)
    assert slices_no_relax.edge_indices is not None
    assert len(slices_no_relax.edge_indices) == 1


def test_def021_def030_def032_topology_errors_nan_vangl_and_reversed_bond_pair(
    repo_root: Path,
    slices_no_relax: SLICES,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify DEF-021 LatticeBasisError/CocycleBasisError, DEF-030 NaN vangl, and DEF-032 pairs."""
    meta = _load_golden_metadata(repo_root)
    e11_s4 = meta["edges"]["E11_quasi1d_lattice_basis_neg1"]["slices"]

    # DEF-021 (Wave 1): check_SLICES stays True for E11, while to_structures raises
    # structured LatticeBasisError instead of TypeError: NoneType * float.
    assert slices_no_relax.check_SLICES(e11_s4, strategy=4) is True
    slices_no_relax.from_SLICES(e11_s4, strategy=4)
    with pytest.raises(LatticeBasisError) as lat_exc:
        slices_no_relax.to_structures()
    assert isinstance(lat_exc.value, GraphTopologyError)

    # Disconnected 2-component net (vertices {0, 1} and {2, 3}) has a valid 3D
    # lattice basis on component 1, but cocycle rank is V - 2 == 2 < V - 1 == 3,
    # raising CocycleBasisError in to_structures().
    slices_no_relax.from_SLICES(
        "Si O Si O 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+ 2 3 ooo",
        strategy=4,
    )
    with contextlib.redirect_stdout(io.StringIO()), pytest.raises(CocycleBasisError):
        slices_no_relax.to_structures()

    # DEF-030: NaN equilibrium angle in vangl is skipped without ValueError: math domain error.
    slices_no_relax.from_SLICES(
        meta["corpus"]["G10"]["slices_by_strategy"]["4"],
        strategy=4,
    )
    real_run = core_mod.run_gfnff_helper

    def _nan_vangl_helper(nbf_text: str) -> dict[str, Any]:
        out = real_run(nbf_text)
        patched = dict(out)
        if patched.get("vangl"):
            vangl_copy = [list(row) for row in patched["vangl"]]
            vangl_copy[0][0] = float("nan")
            patched["vangl"] = vangl_copy
        return patched

    monkeypatch.setattr(core_mod, "run_gfnff_helper", _nan_vangl_helper)
    res_target = slices_no_relax.get_inner_p_target()
    assert res_target is not None
    assert np.all(np.isfinite(res_target[0]))
    res_debug = slices_no_relax.get_inner_p_target_debug()
    assert np.all(np.isfinite(res_debug[0]))

    # DEF-032: Reversed directed edge (2 -> 1, u > v) is canonicalized identically to (1 -> 2).
    g_forward = nx.MultiDiGraph()
    g_forward.add_nodes_from(["1", "2", "3"])
    g_forward.add_edge("1", "2", label="e1", key="e1")

    g_reversed = nx.MultiDiGraph()
    g_reversed.add_nodes_from(["1", "2", "3"])
    g_reversed.add_edge("2", "1", label="e1", key="e1")

    assert SLICES.get_uncovered_pair(g_forward) == [[0, 2], [1, 2]]
    assert SLICES.get_uncovered_pair(g_reversed) == [[0, 2], [1, 2]]


def test_wave1_exception_hierarchy_invariants() -> None:
    """Verify dual-inheritance ValueError/RuntimeError contracts and sibling separation."""
    assert issubclass(SLICESEncodingError, SLICESError)
    assert issubclass(SLICESEncodingError, ValueError)
    assert issubclass(SLICESDecodingError, SLICESError)
    assert issubclass(SLICESDecodingError, ValueError)
    assert issubclass(LatticeBasisError, GraphTopologyError)
    assert issubclass(CocycleBasisError, GraphTopologyError)
    assert issubclass(RelaxBackendError, (SLICESError, RuntimeError))
    assert issubclass(ModelDownloadError, (SLICESError, RuntimeError))
    assert not issubclass(ModelDownloadError, RelaxBackendError)
    assert not issubclass(RelaxBackendError, ModelDownloadError)
