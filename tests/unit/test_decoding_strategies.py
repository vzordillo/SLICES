"""Unit tests for opt-in multi-stage SLICES decoding and recovery strategies."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from pymatgen.core import Structure

import slices.decoding_strategies as ds
from slices.core import SLICES
from slices.decoding_strategies import (
    AdaptiveConvergence,
    BondParameterFallback,
    CycleBasisOptimizer,
    MultiStartOptimizer,
    ProgressiveRelaxer,
    calculate_topology_timeout,
    calculate_xtb_timeout,
    is_approximately_integral,
    robust_decode,
)
from slices.exceptions import SLICESDecodingError
from slices.tobascco_net import Net

pytestmark = pytest.mark.unit

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

# Compact 3-atom trigonal BaSn2 (G10) SLICES string for fast baseline isolation checks.
BASN2_SLICES: str = (
    "+ x n OOO e OOO o Ba Sn Sn 0 1 o-o 0 1 -oo 0 1 ooo 0 2 ooo 0 2 o+o "
    "0 2 +oo 1 2 oo- 1 2 +o- 1 2 o+-"
)


class TestFreezeIsolationGuard:
    """Verify standard SLICES decoding never calls into slices.decoding_strategies."""

    def test_standard_decoding_never_invokes_robust_decode(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify SLICES.to_structures and SLICES2structure bypass decoding_strategies."""

        def forbidden_hook(*_args: object, **_kwargs: object) -> None:
            pytest.fail("Standard decoding unexpectedly invoked slices.decoding_strategies")

        monkeypatch.setattr(ds, "robust_decode", forbidden_hook)
        monkeypatch.setenv("SLICES_DEVICE", "cpu")

        no_relax = SLICES(relax_model=None)
        no_relax.from_SLICES(BASN2_SLICES)
        structs, energy_zero = no_relax.to_structures()
        assert len(structs) == 2
        assert energy_zero == 0

        auto_backend = SLICES(relax_model="auto")
        rec, energy = auto_backend.SLICES2structure(BASN2_SLICES)
        assert isinstance(rec, Structure)
        assert energy < 0.0


class TestDecodingStrategyComponents:
    """Verify all 5 fork bug fixes across mathematical and optimization helpers."""

    def test_is_approximately_integral_elementwise_mixed_signs(self) -> None:
        """Verify mixed near-zero and near-one residuals pass and zero vectors fail."""
        mixed = np.array([1.0 + 1e-8, 2.0 - 1e-8, -3.0 + 1e-8])
        assert is_approximately_integral(mixed, tolerance=1e-6) is True
        assert CycleBasisOptimizer.is_approximately_integral(mixed, tolerance=1e-6) is True

        assert is_approximately_integral(np.zeros(3), tolerance=1e-6) is False
        assert is_approximately_integral(np.array([1e-9, -1e-9, 0.0]), tolerance=1e-6) is False
        assert is_approximately_integral(np.array([]), tolerance=1e-6) is False
        assert is_approximately_integral(np.array([1.25, 2.0, 3.0]), tolerance=1e-6) is False

    def test_multi_start_optimizer_strips_deprecated_kwargs_and_preserves_rng(self) -> None:
        """Verify MultiStartOptimizer strips iprint/disp, is seeded, and keeps np.random intact."""
        np.random.seed(2026)
        global_before = np.random.get_state()[1].copy()

        def objective(x_vec: np.ndarray) -> float:
            return float(np.sum((x_vec - 0.35) ** 2))

        bounds = [(-2.0, 2.0), (-2.0, 2.0), (-2.0, 2.0)]
        x_a, f_a, info_a = MultiStartOptimizer.optimize(
            objective,
            np.zeros(3),
            bounds=bounds,
            n_starts=4,
            seed=42,
            iprint=-1,
            disp=None,
        )
        x_b, f_b, _ = MultiStartOptimizer.optimize(
            objective,
            np.zeros(3),
            bounds=bounds,
            n_starts=4,
            seed=42,
            iprint=0,
            disp=False,
        )

        global_after = np.random.get_state()[1].copy()
        assert np.array_equal(global_before, global_after)
        assert f_a < 1e-9
        assert isinstance(info_a, dict)
        np.testing.assert_allclose(x_a, x_b, atol=1e-12)
        assert np.isclose(f_a, f_b, atol=1e-12)

    def test_adaptive_convergence_and_timeout_helpers(self) -> None:
        """Verify AdaptiveConvergence tiers and topology timeout caps."""
        assert AdaptiveConvergence.get_convergence_params(6)["factr"] == 1e7
        assert AdaptiveConvergence.get_convergence_params(16)["factr"] == 1e6
        assert AdaptiveConvergence.get_convergence_params(30)["factr"] == 1e5
        assert AdaptiveConvergence.get_convergence_params(64)["factr"] == 1e4

        assert calculate_xtb_timeout is calculate_topology_timeout
        assert calculate_topology_timeout(10, 20) == 37
        assert calculate_topology_timeout(500, 1000) == 120
        assert ProgressiveRelaxer.calculate_timeout(10) == 160
        assert ProgressiveRelaxer.calculate_timeout(500) == 3000

    def test_progressive_relaxer_restores_fmax_and_steps_on_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify ProgressiveRelaxer restores SLICES.fmax and SLICES.steps after exceptions."""
        tiers = ProgressiveRelaxer.get_relaxation_strategies(base_fmax=0.2, base_steps=100)
        assert len(tiers) == 3
        assert [t["fmax"] for t in tiers] == [0.2, 0.3, 0.5]

        backend = SLICES(relax_model=None, fmax=0.15, steps=85)
        backend.relaxer = object()  # Enable relaxation path with a failing relax method.
        monkeypatch.setattr(
            backend,
            "relax",
            lambda _s: (_ for _ in ()).throw(RuntimeError("simulated relax crash")),
        )
        sample = Structure.from_file(str(EXAMPLES_DIR / "NdSiRu.cif"))
        assert ProgressiveRelaxer.relax_with_fallbacks(backend, sample) is None
        assert backend.fmax == 0.15
        assert backend.steps == 85

    def test_cycle_basis_optimizer_deterministic_without_global_rng_mutation(self) -> None:
        """Verify CycleBasisOptimizer selects well-conditioned cycles without touching np.random."""
        assert CycleBasisOptimizer.select_optimal_cycle_basis(np.zeros((0, 3))).size == 0

        backend = SLICES(relax_model=None)
        backend.from_SLICES(BASN2_SLICES)
        x_dat, net_voltage = backend.convert_graph()
        net = Net(x_dat, dim=3)
        net.voltage = net_voltage
        net.simple_cycle_basis()

        np.random.seed(999)
        state_before = np.random.get_state()[1].copy()
        perm = CycleBasisOptimizer.select_optimal_cycle_basis(
            net.cycle_rep,
            max_attempts=15,
            seed=7,
        )
        ok = CycleBasisOptimizer.find_lattice_basis(net, max_attempts=10, seed=7)
        state_after = np.random.get_state()[1].copy()

        assert np.array_equal(state_before, state_after)
        assert len(perm) == len(net.cycle_rep)
        assert ok is True
        assert net.lattice_basis is not None
        assert net.lattice_basis.shape == (3, len(net.cycle[0]))

    def test_bond_parameter_fallback_handles_unit_and_supercell_indices(self) -> None:
        """Verify BondParameterFallback maps supercell indices safely via modulo arithmetic."""
        atom_types = np.array([14, 8], dtype=int)
        unit_edges = np.array([[0, 1], [1, 0]], dtype=int)
        supercell_edges = unit_edges + 6  # Simulates out-of-unit-cell supercell atom indices.

        ipt_unit, inds_u, wts_u = BondParameterFallback.build_inner_p_target(atom_types, unit_edges)
        ipt_sup, inds_s, wts_s = BondParameterFallback.build_inner_p_target(
            atom_types,
            supercell_edges,
        )
        np.testing.assert_allclose(ipt_unit, ipt_sup, atol=1e-12)
        assert inds_u == inds_s == [[0, 1], [0, 1]]
        assert wts_u == wts_s
        assert np.all(np.diag(ipt_unit) > 0.0)


class TestRobustDecodePipeline:
    """Verify end-to-end robust_decode validation, fallback recovery, and NdSiRu parity."""

    def test_rejects_encode_only_strategy_two_and_malformed_strings(self) -> None:
        """Verify robust_SLICES2structure raises SLICESDecodingError on strategy=2 or bad input."""
        backend = SLICES(relax_model=None)
        with pytest.raises(SLICESDecodingError, match="strategy 2 is encode-only"):
            backend.robust_SLICES2structure(BASN2_SLICES, strategy=2)

        with pytest.raises(SLICESDecodingError, match="Invalid SLICES string"):
            backend.robust_SLICES2structure("not a valid slices string", strategy=4)

    def test_stage_two_fallback_recovers_when_to_structures_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify robust_decode recovers via Stage 2 multi-start ZL* if Stage 1 raises."""
        backend = SLICES(relax_model=None)
        monkeypatch.setattr(
            backend,
            "to_structures",
            lambda *_, **__: (_ for _ in ()).throw(RuntimeError("forced Stage 1 failure")),
        )
        recovered, energy = robust_decode(backend, BASN2_SLICES, strategy=4, n_starts=2, seed=42)
        assert isinstance(recovered, Structure)
        assert len(recovered) == 3
        assert energy == 0.0

    def test_live_ndsiru_parity_with_standard_slices2structure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify robust_SLICES2structure matches SLICES2structure bit-for-bit on NdSiRu.cif."""
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        ndsiru = Structure.from_file(str(EXAMPLES_DIR / "NdSiRu.cif"))
        backend = SLICES(relax_model="auto")
        slices_str = backend.structure2SLICES(ndsiru)

        struct_std, energy_std = backend.SLICES2structure(slices_str)
        struct_rob, energy_rob = backend.robust_SLICES2structure(
            slices_str,
            strategy=4,
            n_starts=3,
            seed=42,
        )
        assert np.isclose(energy_rob, energy_std, rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(struct_rob.lattice.matrix, struct_std.lattice.matrix, atol=1e-12)
        np.testing.assert_allclose(struct_rob.frac_coords, struct_std.frac_coords, atol=1e-12)
