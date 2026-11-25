"""Comprehensive regression suite for all 5 Wave 3 (VERSIONED_OPT_IN) features.

Covers Lorentz-Berthelot Lennard-Jones steric mixing (DEF-001), three-tiered
element validation and NequIP-OAM 89-element pre-check guards (DEF-006, DEF-029),
incomplete-GFN-FF Stage 1 -> Stage 2 recovery in ``robust_decode`` (DEF-015,
DEF-031), ``PYTHONHASHSEED``-invariant seeded SLICES augmentation without global
RNG mutation (DEF-022, DEF-033), and opt-in ``strict=True`` trailing-edge-token
validation across Strategies 1, 3, and 4 including authentic HTS PBE rows
(DEF-024 Gap 3a), while verifying 100% default v4.0.2 invariance.
"""

from __future__ import annotations

import contextlib
import csv
import inspect
import io
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pymatgen.core import Lattice, Structure
from pymatgen.core.periodic_table import ElementBase
from pymatgen.io.ase import AseAtomsAdaptor

import slices.core as core_mod
import slices.decoding_strategies as ds
import slices.relax_backends as rb
from slices.config import LJ_PARAMS_LIST
from slices.core import SLICES, VALID_ELEMENT_MODES, VALID_LJ_MIXING_MODES
from slices.decoding_strategies import (
    BondParameterFallback,
    ProgressiveRelaxer,
    _compute_lorentz_pair_lj,
    _evaluate_lorentz_lj_pairs,
    _reconstruct_zl_multistart,
    robust_decode,
)
from slices.exceptions import (
    RelaxBackendError,
    SLICESDecodingError,
    SLICESEncodingError,
    SLICESError,
)
from slices.relax_backends import (
    NEQUIP_OAM_ATOMIC_NUMBERS,
    NequIPRelaxer,
    _validate_nequip_elements,
    make_relaxer,
)
from slices.tobascco_net import Net

pytestmark = [
    pytest.mark.regression,
    pytest.mark.filterwarnings(r"ignore::DeprecationWarning:spglib\..*"),
]


def _load_golden_metadata(repo_root: Path) -> dict[str, Any]:
    """Load golden baseline metadata JSON for canonical G01 and G18 strings."""
    meta_path = repo_root / "tests" / "baseline" / "fixtures" / "golden_metadata.json"
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _build_reversed_atom_order_slices(slices_str: str, strategy: int = 4) -> str:
    """Construct an isomorphic SLICES string with reversed unit-cell atom ordering."""
    parser = SLICES(relax_model=None)
    parser.from_SLICES(slices_str, strategy=strategy, fix_duplicate_edge=True)
    assert parser.atom_types is not None
    assert parser.edge_indices is not None
    assert parser.to_jimages is not None

    n_atoms = len(parser.atom_types)
    rev_symbols = [str(ElementBase.from_Z(int(z))) for z in parser.atom_types[::-1]]
    rev_edges = np.array(
        [[n_atoms - 1 - int(u), n_atoms - 1 - int(v)] for u, v in parser.edge_indices],
        dtype=int,
    )
    return parser.get_slices_by_strategy(
        strategy,
        rev_symbols,
        rev_edges,
        parser.to_jimages.copy(),
        parser.space_group_num,
    )


def _uncovered_pairs_for_instance(inst: SLICES) -> list[list[Any]]:
    """Compute uncovered upper-triangular atom-index pairs for a parsed SLICES instance."""
    x_dat, net_voltage = inst.convert_graph()
    net = Net(x_dat, dim=3)
    net.voltage = net_voltage
    return inst.get_uncovered_pair(net.graph)


# === 1. DEF-001: Lorentz-Berthelot LJ Mixing ===


def test_def001_lj_mixing_modes_defaults_and_validation() -> None:
    """Verify VALID_LJ_MIXING_MODES, default 'legacy' mode, and ValueError validation."""
    assert VALID_LJ_MIXING_MODES == ("legacy", "lorentz")
    assert "VALID_LJ_MIXING_MODES" in core_mod.__all__

    default_inst = SLICES(relax_model=None)
    assert default_inst.lj_mixing == "legacy"

    lorentz_inst = SLICES(relax_model=None, lj_mixing="lorentz")
    assert lorentz_inst.lj_mixing == "lorentz"

    with pytest.raises(ValueError, match="Unsupported lj_mixing"):
        SLICES(relax_model=None, lj_mixing="bogus")  # type: ignore[arg-type]

    default_inst.from_SLICES("Si O 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+", strategy=4)
    default_inst.lj_mixing = "bogus"  # type: ignore[assignment]
    with pytest.raises(ValueError, match="Unsupported lj_mixing"):
        default_inst.get_uncovered_pair_lj([[0, 1]])
    with pytest.raises(ValueError, match="Unsupported lj_mixing"):
        default_inst.get_covered_pair_lj()


def test_def001_g18_atom_order_permutation_invariance_and_legacy_asymmetry(
    repo_root: Path,
) -> None:
    """Verify 'legacy' 5.0x G18 sigma^12 asymmetry vs exact 0.0 ULP 'lorentz' invariance."""
    meta = _load_golden_metadata(repo_root)
    g18_fwd = meta["corpus"]["G18"]["canonical_s4"]
    g18_rev = _build_reversed_atom_order_slices(g18_fwd, strategy=4)

    # 1. Default 'legacy' mode exhibits ~5.0x sum(sigma^12) swing on G18 (YHO2).
    leg_fwd = SLICES(relax_model=None, lj_mixing="legacy")
    leg_rev = SLICES(relax_model=None, lj_mixing="legacy")
    leg_fwd.from_SLICES(g18_fwd, strategy=4)
    leg_rev.from_SLICES(g18_rev, strategy=4)

    unc_leg_fwd = np.asarray(
        leg_fwd.get_uncovered_pair_lj(_uncovered_pairs_for_instance(leg_fwd)),
        dtype=float,
    )
    unc_leg_rev = np.asarray(
        leg_rev.get_uncovered_pair_lj(_uncovered_pairs_for_instance(leg_rev)),
        dtype=float,
    )
    sigma12_leg_fwd = float(np.sum(unc_leg_fwd[:, 1] ** 12))
    sigma12_leg_rev = float(np.sum(unc_leg_rev[:, 1] ** 12))
    assert sigma12_leg_rev / sigma12_leg_fwd == pytest.approx(5.0, rel=1e-3)

    cov_leg_fwd = np.asarray(leg_fwd.get_covered_pair_lj(), dtype=float)
    cov_leg_rev = np.asarray(leg_rev.get_covered_pair_lj(), dtype=float)
    assert not np.allclose(
         cov_leg_fwd[np.lexsort((cov_leg_fwd[:, 1], cov_leg_fwd[:, 0]))],
        cov_leg_rev[np.lexsort((cov_leg_rev[:, 1], cov_leg_rev[:, 0]))],
    )

    # 2. Opt-in 'lorentz' mode restores exact 0.0 ULP permutation invariance on both methods.
    lor_fwd = SLICES(relax_model=None, lj_mixing="lorentz")
    lor_rev = SLICES(relax_model=None, lj_mixing="lorentz")
    lor_fwd.from_SLICES(g18_fwd, strategy=4)
    lor_rev.from_SLICES(g18_rev, strategy=4)

    unc_pairs_fwd = _uncovered_pairs_for_instance(lor_fwd)
    unc_pairs_rev = _uncovered_pairs_for_instance(lor_rev)
    unc_lor_fwd = np.asarray(lor_fwd.get_uncovered_pair_lj(unc_pairs_fwd), dtype=float)
    unc_lor_rev = np.asarray(lor_rev.get_uncovered_pair_lj(unc_pairs_rev), dtype=float)

    unc_sorted_fwd = unc_lor_fwd[np.lexsort((unc_lor_fwd[:, 1], unc_lor_fwd[:, 0]))]
    unc_sorted_rev = unc_lor_rev[np.lexsort((unc_lor_rev[:, 1], unc_lor_rev[:, 0]))]
    assert float(np.max(np.abs(unc_sorted_fwd - unc_sorted_rev))) == 0.0
    assert float(np.sum(unc_sorted_fwd[:, 1] ** 12)) == float(np.sum(unc_sorted_rev[:, 1] ** 12))
    assert float(np.sum(unc_lor_fwd[:, 1] ** 12)) == pytest.approx(
        float(np.sum(unc_lor_rev[:, 1] ** 12)),
        rel=1e-14,
    )

    cov_lor_fwd = np.asarray(lor_fwd.get_covered_pair_lj(), dtype=float)
    cov_lor_rev = np.asarray(lor_rev.get_covered_pair_lj(), dtype=float)
    cov_sorted_fwd = cov_lor_fwd[np.lexsort((cov_lor_fwd[:, 1], cov_lor_fwd[:, 0]))]
    cov_sorted_rev = cov_lor_rev[np.lexsort((cov_lor_rev[:, 1], cov_lor_rev[:, 0]))]
    assert float(np.max(np.abs(cov_sorted_fwd - cov_sorted_rev))) == 0.0

    # Verify exact arithmetic mean against LJ_PARAMS_LIST for H (Z=1) and Y (Z=39).
    lj_map = {int(row[0]): (float(row[1]), float(row[2])) for row in LJ_PARAMS_LIST}
    expected_hy = [
        (lj_map[1][0] + lj_map[39][0]) / 2.0,
        (lj_map[1][1] + lj_map[39][1]) / 2.0,
    ]
    hy_direct = _compute_lorentz_pair_lj(np.array([1, 39]), [[0, 1]])[0]
    yh_direct = _compute_lorentz_pair_lj(np.array([39, 1]), [[0, 1]])[0]
    assert hy_direct == yh_direct == expected_hy


def test_def001_reconstruct_zl_multistart_uses_lorentz_and_restores_lj_mixing(
    repo_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify _reconstruct_zl_multistart evaluates LJ in 'lorentz' mode and restores state."""
    meta = _load_golden_metadata(repo_root)
    g10_s4 = meta["corpus"]["G10"]["slices_by_strategy"]["4"]

    inst = SLICES(relax_model=None, lj_mixing="legacy")
    inst.from_SLICES(g10_s4, strategy=4)

    observed_modes: list[str] = []
    orig_unc = inst.get_uncovered_pair_lj
    orig_cov = inst.get_covered_pair_lj

    def spy_unc(pairs: list[list[Any]]) -> list[list[float]]:
        observed_modes.append(inst.lj_mixing)
        return orig_unc(pairs)

    def spy_cov() -> list[list[float]]:
        observed_modes.append(inst.lj_mixing)
        return orig_cov()

    monkeypatch.setattr(inst, "get_uncovered_pair_lj", spy_unc)
    monkeypatch.setattr(inst, "get_covered_pair_lj", spy_cov)

    std_s, opt_s = _reconstruct_zl_multistart(inst, n_starts=1, seed=0)
    assert isinstance(std_s, Structure) and isinstance(opt_s, Structure)
    assert observed_modes == ["lorentz", "lorentz"]
    assert inst.lj_mixing == "legacy"

    # Exception inside get_covered_pair_lj must still restore lj_mixing to 'legacy'.
    def raising_cov() -> list[list[float]]:
        raise RuntimeError("simulated covered LJ failure")

    monkeypatch.setattr(inst, "get_covered_pair_lj", raising_cov)
    with pytest.raises(RuntimeError, match="simulated covered LJ failure"):
        _reconstruct_zl_multistart(inst, n_starts=1, seed=0)
    assert inst.lj_mixing == "legacy"

    # Duck-typed object without lj_mixing attribute uses _compute_lorentz_pair_lj cleanly.
    assert inst.atom_types is not None and inst.edge_indices is not None
    duck = types.SimpleNamespace(
        atom_types=inst.atom_types,
        edge_indices=inst.edge_indices,
    )
    unc_duck, cov_duck = _evaluate_lorentz_lj_pairs(duck, [[0, 1]])  # type: ignore[arg-type]
    assert unc_duck == _compute_lorentz_pair_lj(inst.atom_types, [[0, 1]])
    assert cov_duck == _compute_lorentz_pair_lj(inst.atom_types, inst.edge_indices)


# === 2. DEF-006 + DEF-029: Element Modes & NequIP-OAM Pre-Check ===


def test_def006_def029_element_modes_constants_and_boundary_species(
    slices_no_relax: SLICES,
) -> None:
    """Verify VALID_ELEMENT_MODES, NEQUIP_OAM_ATOMIC_NUMBERS, and boundary species checks."""
    assert VALID_ELEMENT_MODES == ("legacy86", "nequip_oam", "gfnff103")
    assert "VALID_ELEMENT_MODES" in core_mod.__all__

    assert "NEQUIP_OAM_ATOMIC_NUMBERS" in rb.__all__
    expected_oam = frozenset(range(1, 84)) | frozenset(range(89, 95))
    assert expected_oam == NEQUIP_OAM_ATOMIC_NUMBERS
    assert len(NEQUIP_OAM_ATOMIC_NUMBERS) == 89

    si_cell = Structure(Lattice.cubic(5.43), ["Si"], [[0.0, 0.0, 0.0]])
    assert SLICES.check_element(si_cell) is True
    with pytest.raises(ValueError, match="Unsupported element check mode"):
        SLICES.check_element(si_cell, mode="bad")  # type: ignore[arg-type]

    empty = Structure(Lattice.cubic(5.0), [], [])
    for mode in VALID_ELEMENT_MODES:
        with pytest.raises(SLICESEncodingError):
            SLICES.check_element(empty, mode=mode)  # type: ignore[arg-type]

    boundary_cases: list[tuple[str, int, bool, bool, bool]] = [
        ("Bi", 83, True, True, True),
        ("Po", 84, True, False, True),
        ("Rn", 86, True, False, True),
        ("Fr", 87, False, False, True),
        ("Ac", 89, False, True, True),
        ("Th", 90, False, True, True),
        ("Pu", 94, False, True, True),
        ("Am", 95, False, False, True),
        ("Lr", 103, False, False, True),
        ("Rf", 104, False, False, False),
    ]
    for sym, expected_z, exp_leg, exp_oam, exp_gfn in boundary_cases:
        cell = Structure(Lattice.cubic(4.5), [sym, "O"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
        assert cell.atomic_numbers[0] == expected_z
        assert SLICES.check_element(cell) is exp_leg
        assert SLICES.check_element(cell, mode="legacy86") is exp_leg
        assert slices_no_relax.check_element(cell, mode="nequip_oam") is exp_oam
        assert SLICES.check_element(cell, mode="gfnff103") is exp_gfn


def test_def029_nequip_relaxer_precheck_rejects_unsupported_elements_before_calc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify NequIPRelaxer.relax raises RelaxBackendError on Po/Rn/Am and succeeds on Th."""
    monkeypatch.setenv("SLICES_DEVICE", "cpu")

    # 1. Mocked calculator + preoptimize spy proves unsupported species fail BEFORE both.
    preopt_calls: list[int] = []
    orig_preopt = rb.preoptimize

    def spy_preopt(structure: Structure, *args: Any, **kwargs: Any) -> tuple[Structure, dict[str, Any]]:
        preopt_calls.append(len(structure))
        return orig_preopt(structure, *args, **kwargs)

    class ForbiddenCalc:
        """Calculator stub that fails the test if invoked."""

        def calculate(self, *_args: Any, **_kwargs: Any) -> None:
            pytest.fail("NequIP calculator must not be called on unsupported elements")

        def get_potential_energy(self, *_args: Any, **_kwargs: Any) -> float:
            pytest.fail("NequIP calculator must not be called on unsupported elements")

    monkeypatch.setattr(
        rb,
        "get_calculator",
        lambda size, _device: (ForbiddenCalc(), f"stub-{size}.nequip.pth"),
    )
    monkeypatch.setattr(rb, "preoptimize", spy_preopt)

    mock_relaxer = NequIPRelaxer("nequip-s+l", "cpu", optimizer="BFGS")
    for sym, z_num in (("Po", 84), ("Rn", 86), ("Am", 95)):
        bad_cell = Structure(
            Lattice.cubic(3.2),
            [sym, "O"],
            [[0.0, 0.0, 0.0], [0.1, 0.1, 0.1]],  # Deliberate overlap to test preoptimize ordering
        )
        with pytest.raises(RelaxBackendError) as exc_info:
            mock_relaxer.relax(bad_cell, fmax=0.2, steps=10)
        err_val = exc_info.value
        assert isinstance(err_val, (SLICESError, RuntimeError))
        assert not isinstance(err_val, KeyError)
        msg = str(err_val)
        assert f"{sym} (Z={z_num})" in msg
        assert "{1..83, 89..94}" in msg
    assert preopt_calls == []

    # Direct helper check on multi-species unsupported cell verifies sorted formatting.
    multi_bad = AseAtomsAdaptor.get_atoms(
        Structure(Lattice.cubic(5.0), ["Am", "Po", "Th"], [[0, 0, 0], [0.3, 0.3, 0.3], [0.6, 0.6, 0.6]])
    )
    with pytest.raises(RelaxBackendError, match=r"Po \(Z=84\), Am \(Z=95\)"):
        _validate_nequip_elements(multi_bad)

    # 2. Live cached CPU NequIPRelaxer succeeds cleanly on actinide Th (Z=90).
    monkeypatch.undo()
    monkeypatch.setenv("SLICES_DEVICE", "cpu")
    live_relaxer, resolved = make_relaxer("auto", optimizer="BFGS")
    assert resolved == "nequip-s+l"
    assert live_relaxer is not None
    th_cell = Structure(Lattice.cubic(5.08), ["Th"], [[0.0, 0.0, 0.0]])
    th_out = live_relaxer.relax(th_cell, fmax=0.2, steps=15)
    assert isinstance(th_out["final_structure"], Structure)
    assert np.isfinite(th_out["trajectory"].energies[-1])


# === 3. DEF-015 + DEF-031: Incomplete GFN-FF Flag & robust_decode Stage 2 Trigger ===


def test_def015_def031_gfnff_incomplete_flag_lifecycle_and_ndsiru_zero_overhead(
    ndsiru_structure: Structure,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify _last_gfnff_incomplete lifecycle and 0% Stage 2 overhead on NdSiRu.cif."""
    monkeypatch.setenv("SLICES_DEVICE", "cpu")
    inst = SLICES(relax_model="auto")
    assert inst._last_gfnff_incomplete is False

    nd_slices = inst.structure2SLICES(ndsiru_structure, strategy=4)
    inst._last_gfnff_incomplete = True
    inst.from_SLICES(nd_slices, strategy=4)
    assert inst._last_gfnff_incomplete is False

    inst._last_gfnff_incomplete = True
    target = inst.get_inner_p_target()
    assert target is not None
    assert np.all(np.diag(target[0]) > 0.0)
    assert inst._last_gfnff_incomplete is False

    # Spy on _reconstruct_zl_multistart to prove Stage 2 is NOT called on NdSiRu.cif.
    stage2_calls: list[int] = []
    orig_stage2 = ds._reconstruct_zl_multistart

    def spy_stage2(*args: Any, **kwargs: Any) -> tuple[Structure, Structure]:
        stage2_calls.append(1)
        return orig_stage2(*args, **kwargs)

    monkeypatch.setattr(ds, "_reconstruct_zl_multistart", spy_stage2)
    struct_std, energy_std = inst.SLICES2structure(nd_slices, strategy=4)
    struct_rob, energy_rob = inst.robust_SLICES2structure(nd_slices, strategy=4, n_starts=3, seed=0)

    assert stage2_calls == []
    assert inst._last_gfnff_incomplete is False
    assert energy_rob == energy_std
    assert np.array_equal(struct_rob.lattice.matrix, struct_std.lattice.matrix)
    assert np.array_equal(struct_rob.frac_coords, struct_std.frac_coords)


def test_def015_def031_real_mp20_hydride_stage2_trigger_and_stage1_fallback(
    data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify real MP-20 bond-drop hydride triggers Stage 2 and Stage 2 errors fall back cleanly."""
    csv_path = data_dir / "mp20_nonmetal" / "mp20_v4_benchmark_2383.csv"
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    # Row 563 (Lu4H4O8) drops hypervalent Lu-H/O-H GFN-FF bonds ("Cannot find bond!!!").
    lu_slices = rows[563]["SLICES"]

    inst = SLICES(relax_model=None)
    with contextlib.redirect_stdout(io.StringIO()):
        inst.from_SLICES(lu_slices, strategy=4)
        ipt_res = inst.get_inner_p_target()
    assert ipt_res is not None
    assert bool(np.any(np.diag(ipt_res[0]) <= 0.0)) is True
    assert inst._last_gfnff_incomplete is True

    # 1. Even though Stage 1 to_structures() returns 2 structures without raising,
    # robust_decode detects _last_gfnff_incomplete=True and invokes Stage 2 + BondParameterFallback.
    stage2_calls: list[int] = []
    bpf_calls: list[int] = []
    orig_stage2 = ds._reconstruct_zl_multistart
    orig_bpf = BondParameterFallback.build_inner_p_target

    def spy_stage2(*args: Any, **kwargs: Any) -> tuple[Structure, Structure]:
        stage2_calls.append(1)
        return orig_stage2(*args, **kwargs)

    def spy_bpf(*args: Any, **kwargs: Any) -> tuple[np.ndarray, list[list[int]], list[float]]:
        bpf_calls.append(1)
        return orig_bpf(*args, **kwargs)

    monkeypatch.setattr(ds, "_reconstruct_zl_multistart", spy_stage2)
    monkeypatch.setattr(BondParameterFallback, "build_inner_p_target", spy_bpf)

    with contextlib.redirect_stdout(io.StringIO()):
        stage1_only, _ = inst.SLICES2structure(lu_slices, strategy=4)
        recovered_s2, energy_s2 = robust_decode(inst, lu_slices, strategy=4, n_starts=2, seed=0)

    assert len(stage2_calls) == 1
    assert len(bpf_calls) == 1
    assert isinstance(recovered_s2, Structure) and len(recovered_s2) == 16
    assert energy_s2 == 0.0
    assert inst.lj_mixing == "legacy"

    # 2. If Stage 2 raises, robust_decode falls back cleanly to Stage 1's valid structure.
    monkeypatch.setattr(
        ds,
        "_reconstruct_zl_multistart",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("forced Stage 2 failure")),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        fallback_s1, fallback_e1 = robust_decode(inst, lu_slices, strategy=4, n_starts=2, seed=0)
    assert fallback_e1 == 0.0
    np.testing.assert_allclose(fallback_s1.lattice.matrix, stage1_only.lattice.matrix, atol=1e-12)
    np.testing.assert_allclose(fallback_s1.frac_coords, stage1_only.frac_coords, atol=1e-12)

    # 3. With a relaxer active where Stage 1 produced a relaxed structure (len == 3) but
    # Stage 3 progressive relaxation fails, robust_decode preserves Stage 1's relaxed output.
    monkeypatch.setattr(ds, "_reconstruct_zl_multistart", orig_stage2)
    inst.relaxer = types.SimpleNamespace(
        relax=lambda struc, **_kw: {
            "final_structure": struc,
            "trajectory": types.SimpleNamespace(energies=[-112.0]),
        }
    )
    monkeypatch.setattr(ProgressiveRelaxer, "relax_with_fallbacks", lambda *_a, **_kw: None)
    with contextlib.redirect_stdout(io.StringIO()):
        kept_s1, kept_e1 = robust_decode(inst, lu_slices, strategy=4, n_starts=1, seed=0)
    assert isinstance(kept_s1, Structure)
    assert kept_e1 == pytest.approx(-112.0 / 16.0)


# === 4. DEF-022 + DEF-033: Seeded Augmentation & PYTHONHASHSEED Invariance ===


def test_def022_def033_seeded_augmentation_hashseed_invariance_and_rng_purity(
    repo_root: Path,
    ndsiru_structure: Structure,
) -> None:
    """Verify seed=... gives PYTHONHASHSEED invariance, num=1 exactness, and 0 RNG mutation."""
    sig_rand = inspect.signature(SLICES.structure2randomSLICES)
    sig_aug = inspect.signature(SLICES.structure2SLICESAug_atom_order)
    assert sig_rand.parameters["seed"].default is None
    assert sig_aug.parameters["seed"].default is None

    # Default seed=None continues to operate cleanly.
    local_inst = SLICES(relax_model=None)
    default_out = local_inst.structure2randomSLICES(ndsiru_structure, strategy=4, num=3)
    assert len(default_out) == 3 and len(set(default_out)) == 3

    # Different seeds produce distinct permutation sequences while same seed is identical.
    s42_a = local_inst.structure2randomSLICES(ndsiru_structure, strategy=4, num=8, seed=42)
    s42_b = local_inst.structure2randomSLICES(ndsiru_structure, strategy=4, num=8, seed=42)
    s43 = local_inst.structure2randomSLICES(ndsiru_structure, strategy=4, num=8, seed=43)
    assert s42_a == s42_b
    assert s42_a != s43

    # Cross-process PYTHONHASHSEED=0 vs PYTHONHASHSEED=999 invariance + global random purity.
    src_dir = str(repo_root / "src")
    cif_path = str(repo_root / "examples" / "NdSiRu.cif")
    probe_code = (
        "import json, random\n"
        "from slices.core import SLICES\n"
        "from pymatgen.core import Structure\n"
        f"struct = Structure.from_file({cif_path!r})\n"
        "inst = SLICES(relax_model=None)\n"
        "orig = inst.structure2SLICES(struct, strategy=4)\n"
        "random.seed(987654321)\n"
        "rng_before = random.getstate()\n"
        "r1 = inst.structure2randomSLICES(struct, strategy=4, num=1, seed=42)\n"
        "r8 = inst.structure2randomSLICES(struct, strategy=4, num=8, seed=42)\n"
        "aug6 = inst.structure2SLICESAug_atom_order(struct, strategy=4, num=6, seed=42)\n"
        "rng_after = random.getstate()\n"
        "assert rng_before == rng_after, 'Global random state was mutated!'\n"
        "assert r1 == [orig], f'DEF-033 regression: num=1 returned {r1!r} != {[orig]!r}'\n"
        "assert len(r8) == 8 and len(set(r8)) == 8\n"
        "assert len(aug6) == 6 and len(set(aug6)) == 6\n"
        "print(json.dumps({'orig': orig, 'r1': r1, 'r8': r8, 'aug6': aug6}))\n"
    )

    outputs: dict[str, dict[str, Any]] = {}
    for hash_seed in ("0", "999"):
        env = os.environ.copy()
        env["PYTHONPATH"] = src_dir
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["OMP_NUM_THREADS"] = "1"
        env["PYTHONHASHSEED"] = hash_seed
        proc = subprocess.run(
            [sys.executable, "-c", probe_code],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        outputs[hash_seed] = json.loads(proc.stdout.strip().splitlines()[-1])

    assert outputs["0"]["r1"] == outputs["999"]["r1"] == [outputs["0"]["orig"]]
    assert outputs["0"]["r8"] == outputs["999"]["r8"]
    assert outputs["0"]["aug6"] == outputs["999"]["aug6"]


# === 5. DEF-024 Gap 3a: Opt-In strict=True Trailing Partial Edge Token Guard ===


def test_def024_gap3a_strict_trailing_tokens_all_strategies_and_hts_pbe_rows(
    repo_root: Path,
    slices_no_relax: SLICES,
) -> None:
    """Verify strict=False vs strict=True across Strategies 1/3/4 and all 13 HTS PBE rows."""
    for fn in (SLICES.from_SLICES, SLICES.check_SLICES, SLICES.check_SLICES_basic):
        assert inspect.signature(fn).parameters["strict"].default is False

    meta = _load_golden_metadata(repo_root)
    g01_by_strategy = meta["corpus"]["G01"]["slices_by_strategy"]

    # 1. Valid full-stride strings pass under both strict=False and strict=True.
    for strat in (1, 3, 4):
        valid_sli = g01_by_strategy[str(strat)].strip()
        slices_no_relax.from_SLICES(valid_sli, strategy=strat, strict=False)
        edges_lenient = len(slices_no_relax.edge_indices)  # type: ignore[arg-type]
        slices_no_relax.from_SLICES(valid_sli, strategy=strat, strict=True)
        edges_strict = len(slices_no_relax.edge_indices)  # type: ignore[arg-type]
        assert edges_lenient == edges_strict > 0
        assert slices_no_relax.check_SLICES(valid_sli, strategy=strat, strict=False) is True
        assert slices_no_relax.check_SLICES(valid_sli, strategy=strat, strict=True) is True
        assert slices_no_relax.check_SLICES_basic(valid_sli, strategy=strat, strict=False) is True
        assert slices_no_relax.check_SLICES_basic(valid_sli, strategy=strat, strict=True) is True

    # 2. Trailing partial edge tokens for every strategy stride (7, 5, 3):
    # accepted under default strict=False, rejected under strict=True.
    trailing_cases: list[tuple[int, str]] = [
        (1, f"{g01_by_strategy['1'].strip()} Nd"),
        (1, f"{g01_by_strategy['1'].strip()} Nd Si 0 1 o o"),
        (3, f"{g01_by_strategy['3'].strip()} 0"),
        (3, f"{g01_by_strategy['3'].strip()} 0 1 o o"),
        (4, f"{g01_by_strategy['4'].strip()} 0"),
        (4, f"{g01_by_strategy['4'].strip()} 0 1"),
    ]
    for strat, truncated in trailing_cases:
        slices_no_relax.from_SLICES(truncated, strategy=strat)
        assert slices_no_relax.check_SLICES(truncated, strategy=strat) is True
        assert slices_no_relax.check_SLICES_basic(truncated, strategy=strat) is True

        with pytest.raises(SLICESDecodingError, match="trailing partial edge tokens") as exc_info:
            slices_no_relax.from_SLICES(truncated, strategy=strat, strict=True)
        assert isinstance(exc_info.value, ValueError)
        assert slices_no_relax.check_SLICES(truncated, strategy=strat, strict=True) is False
        assert slices_no_relax.check_SLICES_basic(truncated, strategy=strat, strict=True) is False

    # 3. Authentic RNN-truncated Strategy 3 rows in HTS/9_EAH_Band_gap_PBE (exact 13 rows).
    hts_csv = repo_root / "HTS" / "9_EAH_Band_gap_PBE" / "results_9_EAH_Band_gap_PBE.csv"
    truncated_hts_rows: list[str] = []
    with hts_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sli = row["SLICES"].strip()
            toks = sli.split(" ")
            first_int = next((i for i, t in enumerate(toks) if t.lstrip("-").isdigit()), None)
            if first_int is not None and (len(toks) - first_int) % 5 != 0:
                truncated_hts_rows.append(sli)

    assert len(truncated_hts_rows) == 13
    for hts_sli in truncated_hts_rows:
        assert slices_no_relax.check_SLICES(hts_sli, strategy=3, strict=False) is True
        assert slices_no_relax.check_SLICES_basic(hts_sli, strategy=3, strict=False) is True
        assert slices_no_relax.check_SLICES(hts_sli, strategy=3, strict=True) is False
        assert slices_no_relax.check_SLICES_basic(hts_sli, strategy=3, strict=True) is False
        with pytest.raises(SLICESDecodingError) as hts_exc:
            slices_no_relax.from_SLICES(hts_sli, strategy=3, strict=True)
        assert isinstance(hts_exc.value, ValueError)
