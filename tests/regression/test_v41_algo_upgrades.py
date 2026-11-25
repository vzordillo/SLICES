"""Regression suite for SLICES v4.1 core algorithmic upgrades (DEF-003, DEF-014, DEF-021, DEF-031).

Verifies transitive ``math.isclose`` metric-tensor symmetry classification and
cross-module parity (DEF-014), exact integer Smith Normal Form ``basis == -1``
unimodular lattice-basis rescue with zero global RNG mutation (DEF-003),
``check_SLICES(..., graph_rank_check=True)`` 3D lattice and cocycle basis
enforcement preserving ``graph_rank_check=False`` and 1-atom cells (DEF-021),
and true matched-edge diagonal index alignment in ``get_inner_p_target`` and
``get_inner_p_target_debug`` when GFN-FF drops hypervalent bonds (DEF-031).
"""

from __future__ import annotations

import contextlib
import csv
import functools
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import slices.core as core_mod
import slices.decoding_strategies as ds_mod
from slices.core import SLICES, _classify_lattice_type
from slices.exceptions import CocycleBasisError, LatticeBasisError
from slices.tobascco_net import Net

pytestmark = [
    pytest.mark.regression,
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:spglib\..*"),
]


@functools.cache
def _load_mp20_v4_slices(repo_root: Path) -> tuple[str, ...]:
    """Load the 2,383 SLICES strings from ``data/mp20_nonmetal/mp20_v4_benchmark_2383.csv``."""
    csv_path = repo_root / "data" / "mp20_nonmetal" / "mp20_v4_benchmark_2383.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(str(row["SLICES"]) for row in reader)


@functools.cache
def _load_golden_metadata(repo_root: Path) -> dict[str, Any]:
    """Load the locked v4.0.2 golden metadata fixture."""
    meta_path = repo_root / "tests" / "baseline" / "fixtures" / "golden_metadata.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))


# === 1. DEF-014: Transitive math.isclose lattice_type Symmetry Classifier ===


@pytest.mark.parametrize(
    ("diag", "expected_code"),
    [
        # Exact and IEEE-754-noisy cubic / rhombohedral (a == b == c -> 1)
        ((9.0, 9.0, 9.0), 1),
        ((12.5, 12.5 * (1.0 + 4e-16), 12.5 * (1.0 - 8e-16)), 1),
        ((1e-13, 2e-13, 3e-13), 1),
        # Transitive closure: g0 ~ g1 and g1 ~ g2 within rel_tol=1e-9, even though
        # |g0 - g2| / g2 == 1.4e-9 > 1e-9 on the direct (0, 2) pair!
        ((4.0, 4.0 * (1.0 + 7e-10), 4.0 * (1.0 + 1.4e-9)), 1),
        ((4.0 * (1.0 + 7e-10), 4.0, 4.0 * (1.0 - 7e-10)), 1),
        ((4.0, 4.0 * (1.0 + 1.4e-9), 4.0 * (1.0 + 7e-10)), 1),
        # Two equal axial lengths (23: a==b!=c, 22: a==c!=b, 21: b==c!=a)
        ((9.0, 9.0, 25.0), 23),
        ((9.0, 9.0 * (1.0 + 5e-15), 25.0), 23),
        ((9.0, 25.0, 9.0), 22),
        ((9.0, 25.0, 9.0 * (1.0 - 5e-15)), 22),
        ((25.0, 9.0, 9.0), 21),
        ((25.0, 9.0, 9.0 * (1.0 + 5e-15)), 21),
        # Genuine crystallographic anisotropy (>= 1e-6 relative difference -> 3)
        ((10.0, 10.0 * (1.0 + 1e-6), 10.0 * (1.0 + 2e-6)), 3),
        ((9.0, 16.0, 25.0), 3),
    ],
)
def test_def014_classify_lattice_type_and_cross_module_parity(
    diag: tuple[float, float, float],
    expected_code: int,
) -> None:
    """Verify exact/noisy/transitive/anisotropic symmetry codes and parity with decoding_strategies."""
    mt = np.array(
        [
            [diag[0], 0.25, -0.15],
            [0.25, diag[1], 0.10],
            [-0.15, 0.10, diag[2]],
        ],
        dtype=float,
    )
    core_code = _classify_lattice_type(mt)
    strat_code = ds_mod._classify_lattice_type(mt)
    assert core_code == expected_code
    assert strat_code == expected_code


# === 2. DEF-003 + DEF-021: Exact SNF Unimodular Rescue & check_SLICES Rank Gate ===


@pytest.mark.parametrize(
    ("row_idx", "expected_formula"),
    [
        (74, "V5Te8"),
        (1417, "Li2Fe2P2O8F2"),
    ],
)
def test_def003_def021_snf_unimodular_rescue_and_rng_purity(
    repo_root: Path,
    slices_no_relax: SLICES,
    slices_nequip: SLICES,
    row_idx: int,
    expected_formula: str,
) -> None:
    """Verify SNF rescues real MP-20 unimodular basis==-1 crystals with zero global RNG mutation."""
    sli = _load_mp20_v4_slices(repo_root)[row_idx]
    assert slices_no_relax.SLICES2formula(sli) == expected_formula

    np.random.seed(20261125)
    rng_before = np.random.get_state()

    slices_no_relax.from_SLICES(sli, strategy=4)
    x_dat, net_voltage = slices_no_relax.convert_graph()
    net = Net(x_dat, dim=3)
    net.voltage = net_voltage
    net.simple_cycle_basis()
    status = net.get_lattice_basis()

    rng_after = np.random.get_state()
    assert rng_before[0] == rng_after[0]
    assert np.array_equal(rng_before[1], rng_after[1])
    assert rng_before[2:] == rng_after[2:]

    assert status == 1
    assert net.lattice_basis is not None
    assert net.lattice_basis.shape == (3, net.shape)
    assert slices_no_relax.check_SLICES(sli, strategy=4, graph_rank_check=True) is True

    decoded_struct, energy_per_atom = slices_nequip.SLICES2structure(sli, strategy=4)
    assert len(decoded_struct) > 0
    assert np.isfinite(energy_per_atom) and energy_per_atom < 0.0


def test_def021_rejects_sublattice_quasi1d_and_disconnected_while_preserving_norank_and_1atom(
    repo_root: Path,
    slices_no_relax: SLICES,
) -> None:
    """Verify check_SLICES rejects non-unimodular/1D/disconnected nets only when graph_rank_check=True."""
    meta = _load_golden_metadata(repo_root)

    # 1. Proper sublattice MP-20 row 2178 (mp-29816 Ag8Hg4O8, SNF == (1, 1, 3))
    sublattice_sli = _load_mp20_v4_slices(repo_root)[2178]
    assert slices_no_relax.check_SLICES(sublattice_sli, strategy=4, graph_rank_check=True) is False
    assert slices_no_relax.check_SLICES(sublattice_sli, strategy=4, graph_rank_check=False) is True
    slices_no_relax.from_SLICES(sublattice_sli, strategy=4)
    with pytest.raises(LatticeBasisError):
        slices_no_relax.to_structures()

    # 2. Quasi-1D E11 (TiBr3, SNF == (1, 1, 0))
    e11_sli = meta["edges"]["E11_quasi1d_lattice_basis_neg1"]["slices"]
    assert slices_no_relax.check_SLICES(e11_sli, strategy=4, graph_rank_check=True) is False
    assert slices_no_relax.check_SLICES(e11_sli, strategy=4, graph_rank_check=False) is True

    # 3. 1-atom primitive cell G14 (Na, net.order == 1, cocycle is None) stays valid!
    g14_sli = meta["corpus"]["G14"]["slices_by_strategy"]["4"]
    assert slices_no_relax.check_SLICES(g14_sli, strategy=4, graph_rank_check=True) is True
    assert slices_no_relax.check_SLICES(g14_sli, strategy=4, graph_rank_check=False) is True

    # 4. Disconnected 2-component graph (cocycle rank V - 2 < V - 1) rejected under rank check
    disconnected_sli = "Si O Si O 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+ 2 3 ooo"
    with contextlib.redirect_stdout(io.StringIO()):
        assert (
            slices_no_relax.check_SLICES(disconnected_sli, strategy=4, graph_rank_check=True)
            is False
        )
        assert (
            slices_no_relax.check_SLICES(disconnected_sli, strategy=4, graph_rank_check=False)
            is True
        )
        slices_no_relax.from_SLICES(disconnected_sli, strategy=4)
        with pytest.raises(CocycleBasisError):
            slices_no_relax.to_structures()


# === 3. DEF-031: get_inner_p_target & get_inner_p_target_debug Matched-Bond Alignment ===


@pytest.mark.parametrize(
    ("row_idx", "expected_formula", "expected_dropped"),
    [
        (563, "Lu4H4O8", [0, 7, 14, 21]),
        (994, "Eu2H6O6", [0, 1, 2, 3, 4, 5, 15, 16, 17, 18, 19, 20]),
    ],
)
def test_def031_real_mp20_oxyhydride_matched_bond_index_alignment(
    repo_root: Path,
    slices_no_relax: SLICES,
    row_idx: int,
    expected_formula: str,
    expected_dropped: list[int],
) -> None:
    """Verify diagonal colattice_inds match nonzero inner_p_target diagonals on MP-20 oxyhydrides."""
    sli = _load_mp20_v4_slices(repo_root)[row_idx]
    assert slices_no_relax.SLICES2formula(sli) == expected_formula
    slices_no_relax.from_SLICES(sli, strategy=4)

    with contextlib.redirect_stdout(io.StringIO()):
        res_std = slices_no_relax.get_inner_p_target()
        assert res_std is not None
        assert slices_no_relax._last_gfnff_incomplete is True
        ipt_std, c_inds_std, c_weights_std = res_std

        ipt_dbg, c_inds_dbg, c_weights_dbg = slices_no_relax.get_inner_p_target_debug()
        assert slices_no_relax._last_gfnff_incomplete is True

    np.testing.assert_array_equal(ipt_std, ipt_dbg)
    assert c_inds_std == c_inds_dbg
    assert c_weights_std == c_weights_dbg

    nonzero_diag = np.where(np.diag(ipt_std) > 0.0)[0].tolist()
    dropped_diag = np.where(np.diag(ipt_std) <= 0.0)[0].tolist()
    assert dropped_diag == expected_dropped

    diag_inds = [
        c_inds_std[0][k]
        for k in range(len(c_inds_std[0]))
        if c_inds_std[0][k] == c_inds_std[1][k]
    ]
    assert diag_inds == nonzero_diag
    assert diag_inds != list(range(len(diag_inds)))


def test_def031_controlled_skipped_bond_mock_alignment(
    slices_no_relax: SLICES,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify controlled skipped edge k=1 keeps true diagonal indices [0, 2, 3] and weights."""
    fake_blist = np.array([[1, 2], [2, 3], [3, 4], [4, 1]], dtype=int)
    fake_data: dict[str, Any] = {
        "blist": [[1, 2], [3, 4], [1, 4]],  # edge 1 ([2, 3]) skipped; edge 3 reversed ([1, 4])
        "vbond": [[0.0, 0.0, 2.0, 3.0], [0.0, 0.0, 4.0, 3.5], [0.0, 0.0, float("nan"), 4.0]],
        "alist": np.zeros((0, 3), dtype=int),
        "vangl": [],
    }
    monkeypatch.setattr(slices_no_relax, "get_nbf_blist", lambda: ("fake_nbf", fake_blist))
    monkeypatch.setattr(core_mod, "run_gfnff_helper", lambda _nbf: copy_fake_data(fake_data))

    def copy_fake_data(src: dict[str, Any]) -> dict[str, Any]:
        return {
            "blist": [list(r) for r in src["blist"]],
            "vbond": [list(r) for r in src["vbond"]],
            "alist": src["alist"].copy(),
            "vangl": list(src["vangl"]),
        }

    with contextlib.redirect_stdout(io.StringIO()):
        res = slices_no_relax.get_inner_p_target()
        assert res is not None
        ipt, c_inds, c_weights = res
        ipt_d, c_inds_d, c_weights_d = slices_no_relax.get_inner_p_target_debug()

    assert c_inds == [[0, 2, 3], [0, 2, 3]]
    assert c_inds_d == [[0, 2, 3], [0, 2, 3]]
    assert c_weights == [0.5, 1.0, 0.25]
    assert c_weights_d == [0.5, 1.0, 0.25]
    assert ipt[1, 1] == 0.0
    assert ipt[0, 0] > 0.0 and ipt[2, 2] > 0.0 and ipt[3, 3] > 0.0
    np.testing.assert_array_equal(ipt, ipt_d)
