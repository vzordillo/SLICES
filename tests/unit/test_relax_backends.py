"""Unit tests for built-in NequIP relaxation backends and geometry safety guards."""

from __future__ import annotations

import sys
from typing import Any

import numpy as np
import pytest
from ase.calculators.emt import EMT
from pymatgen.core import Lattice, Structure
from pymatgen.io.ase import AseAtomsAdaptor

import slices.relax_backends as rb
from slices.exceptions import ModelDownloadError, RelaxBackendError, SLICESError
from slices.mlip_relaxer import OPTIONAL_MLIP_MODELS
from slices.relax_backends import (
    OPTIMIZERS,
    RELAX_MODELS,
    CellCollapse,
    NequIPRelaxer,
    _cell_filter,
    _collapse_guard,
    _compiled_name,
    _optimize,
    _short_error,
    choose_device,
    closest_pair_ratio,
    make_relaxer,
    preoptimize,
    remove_overlaps,
    resolve_relax_model,
)

pytestmark = pytest.mark.unit


def _make_nacl_normal() -> Structure:
    """Build a non-overlapping cubic CsCl-type NaCl test structure."""
    return Structure(Lattice.cubic(4.3), ["Na", "Cl"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])


def _make_nacl_overlapping() -> Structure:
    """Build the S01 severely overlapping cubic NaCl test structure."""
    return Structure(
        Lattice.cubic(3.6),
        ["Na", "Cl"],
        [[0.0, 0.0, 0.0], [0.12, 0.12, 0.12]],
    )


def _make_fcc_cu_perturbed() -> Structure:
    """Build a slightly perturbed 4-atom fcc Cu cell compatible with ASE EMT."""
    return Structure(
        Lattice.cubic(3.65),
        ["Cu", "Cu", "Cu", "Cu"],
        [
            [0.02, 0.0, 0.0],
            [0.0, 0.5, 0.5],
            [0.5, 0.0, 0.5],
            [0.5, 0.5, 0.0],
        ],
    )


class TestResolveRelaxModelAndDevice:
    """Verify model resolution, environment overrides, and device selection."""

    def test_none_and_string_none_resolution(self) -> None:
        """Verify None and 'none' resolve to ('none', None) with a None relaxer."""
        assert resolve_relax_model(None) == ("none", None)
        assert resolve_relax_model("none") == ("none", None)
        assert resolve_relax_model("  NONE  ") == ("none", None)
        assert make_relaxer(None) == (None, "none")
        assert make_relaxer("none") == (None, "none")

    @pytest.mark.parametrize(
        ("requested", "expected"),
        [
            ("auto", "nequip-s+l"),
            (" AUTO ", "nequip-s+l"),
            ("nequip-s+l", "nequip-s+l"),
            ("nequip-m+l", "nequip-m+l"),
            ("nequip-l", "nequip-l"),
            ("NEQUIP-S+L", "nequip-s+l"),
        ],
    )
    def test_builtin_nequip_model_resolution(
        self,
        monkeypatch: pytest.MonkeyPatch,
        requested: str,
        expected: str,
    ) -> None:
        """Verify built-in NequIP plans and case-insensitive 'auto' resolve cleanly."""
        monkeypatch.delenv("SLICES_RELAX_MODEL", raising=False)
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        assert resolve_relax_model(requested) == (expected, "cpu")

    def test_slices_relax_model_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify SLICES_RELAX_MODEL overrides relax_model='auto'."""
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        monkeypatch.setenv("SLICES_RELAX_MODEL", "none")
        assert resolve_relax_model("auto") == ("none", None)

        monkeypatch.setenv("SLICES_RELAX_MODEL", "nequip-l")
        assert resolve_relax_model("auto") == ("nequip-l", "cpu")

    def test_ca04_m3gnet_unblocked_into_optional_mlip_resolver(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify m3gnet delegates to mlip_relaxer instead of raising hardcoded ValueError."""
        import importlib.util

        monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
        with pytest.raises(ImportError, match="m3gnet"):
            resolve_relax_model("m3gnet")

    def test_unknown_model_raises_value_error_listing_valid_choices(self) -> None:
        """Verify unrecognized model names raise ValueError listing built-in and optional names."""
        with pytest.raises(ValueError, match="Unknown relax_model") as exc_info:
            resolve_relax_model("nonexistent_model_xyz")
        msg = str(exc_info.value)
        for builtin in RELAX_MODELS:
            assert builtin in msg
        for opt in OPTIONAL_MLIP_MODELS:
            assert opt in msg

    def test_choose_device_cpu_invalid_and_cuda_fallback(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify choose_device validates SLICES_DEVICE and falls back when CUDA is absent."""
        import torch

        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        assert choose_device() == "cpu"

        monkeypatch.setenv("SLICES_DEVICE", "tpu")
        with pytest.raises(ValueError, match="SLICES_DEVICE"):
            choose_device()

        monkeypatch.setenv("SLICES_DEVICE", "cuda")
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert choose_device() == "cpu"


class TestGeometryAndCollapseSafetyGuards:
    """Verify overlap detection, overlap removal, preoptimize, and _collapse_guard."""

    def test_closest_pair_ratio_normal_vs_overlapping(self) -> None:
        """Verify closest_pair_ratio distinguishes normal and overlapping cells."""
        normal = _make_nacl_normal()
        overlap = _make_nacl_overlapping()
        assert closest_pair_ratio(normal) >= 0.5
        ratio_overlap = closest_pair_ratio(overlap)
        assert ratio_overlap < 0.5
        assert np.isclose(ratio_overlap, 0.279162, atol=1e-4)

    def test_remove_overlaps_deterministic_and_preserves_global_rng(self) -> None:
        """Verify remove_overlaps resolves exact coincidences without mutating np.random."""
        coincident = Structure(
            Lattice.cubic(3.0),
            ["Na", "Cl"],
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        )
        np.random.seed(777)
        rng_before = np.random.get_state()[1].copy()

        fixed_a = remove_overlaps(coincident, seed=0)
        fixed_b = remove_overlaps(coincident, seed=0)

        rng_after = np.random.get_state()[1].copy()
        assert np.array_equal(rng_before, rng_after)
        assert closest_pair_ratio(fixed_a) >= 0.69
        np.testing.assert_allclose(fixed_a.lattice.matrix, fixed_b.lattice.matrix, atol=1e-12)
        np.testing.assert_allclose(fixed_a.frac_coords, fixed_b.frac_coords, atol=1e-12)

    def test_preoptimize_skips_clean_and_repairs_overlapping_structure(self) -> None:
        """Verify preoptimize leaves clean cells untouched and repairs overlapping cells."""
        clean = _make_nacl_normal()
        out_clean, meta_clean = preoptimize(clean)
        assert out_clean is clean
        assert meta_clean["applied"] is False

        overlap = _make_nacl_overlapping()
        out_rep, meta_rep = preoptimize(overlap)
        assert meta_rep["applied"] is True
        assert meta_rep["ratio_before"] < 0.5
        assert meta_rep["ratio"] >= 0.69
        assert closest_pair_ratio(out_rep) >= 0.69

    def test_cell_collapse_inheritance_and_guard_triggers_and_restores(self) -> None:
        """Verify _collapse_guard raises CellCollapse on degeneration and restores calc."""
        assert issubclass(CellCollapse, RelaxBackendError)
        assert issubclass(CellCollapse, SLICESError)
        assert issubclass(CellCollapse, RuntimeError)
        assert not issubclass(ModelDownloadError, CellCollapse)

        atoms = AseAtomsAdaptor.get_atoms(_make_fcc_cu_perturbed())
        calc = EMT()
        orig_calculate = calc.calculate

        # 1. Volume collapse trigger (< COLLAPSE_VOLUME).
        collapsed_atoms = atoms.copy()
        collapsed_atoms.set_cell([1.0, 1.0, 1.0], scale_atoms=True)
        with pytest.raises(CellCollapse, match="collapsed"), _collapse_guard(calc, atoms):
            calc.calculate(collapsed_atoms)
        assert calc.calculate == orig_calculate

        # 2. Extreme aspect-ratio trigger (> 20x).
        elongated = atoms.copy()
        elongated.set_cell([1.5, 1.5, 40.0], scale_atoms=True)
        with pytest.raises(CellCollapse, match="degenerated"), _collapse_guard(calc, atoms):
            calc.calculate(elongated)
        assert calc.calculate == orig_calculate

        # 3. Acute cell-angle trigger (< 5 degrees, with volume >= COLLAPSE_VOLUME).
        skewed = atoms.copy()
        skewed.set_cell([10.0, 10.0, 10.0, 4.0, 90.0, 90.0], scale_atoms=True)
        with pytest.raises(CellCollapse, match="degenerated"), _collapse_guard(calc, atoms):
            calc.calculate(skewed)
        assert calc.calculate == orig_calculate


class TestOptimizersMockedRetryAndLiveNequIP:
    """Verify _optimize, mocked NequIPRelaxer collapse retry, and live cached CPU NequIP."""

    @pytest.mark.parametrize("opt_name", OPTIMIZERS)
    def test_all_optimizers_run_cleanly_on_emt_copper(self, opt_name: str) -> None:
        """Verify BFGS, LBFGS, FIRE, and FIRE+BFGS execute within step budgets."""
        atoms = AseAtomsAdaptor.get_atoms(_make_fcc_cu_perturbed())
        atoms.calc = EMT()
        steps = _optimize(_cell_filter(atoms), opt_name, fmax=0.05, steps=15)
        assert 0 <= steps <= 15

    def test_nequip_relaxer_rejects_unsupported_optimizer(self) -> None:
        """Verify NequIPRelaxer raises ValueError on unknown optimizer names."""
        with pytest.raises(ValueError, match="optimizer"):
            NequIPRelaxer("nequip-s+l", "cpu", optimizer="CG_UNKNOWN")

    def test_mocked_nequip_relaxer_collapse_retry_with_fire(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify NequIPRelaxer catches CellCollapse once and retries with S + FIRE."""

        class CollapsingCalc:
            """Dummy calculator whose calculate method shrinks cell volume below threshold."""

            def get_potential_energy(self, atoms: Any = None, **kwargs: Any) -> float:
                self.calculate(atoms)
                return -10.0

            def get_forces(self, atoms: Any = None, **kwargs: Any) -> np.ndarray:
                self.calculate(atoms)
                return np.zeros((len(atoms), 3))

            def get_stress(self, atoms: Any = None, **kwargs: Any) -> np.ndarray:
                self.calculate(atoms)
                return np.zeros(6)

            def calculate(self, atoms: Any = None, *args: Any, **kwargs: Any) -> None:
                raise CellCollapse("simulated primary collapse")

        emt_calc = EMT()

        def fake_get_calculator(size: str, device: str) -> tuple[Any, str]:
            if size == "M":
                return CollapsingCalc(), "mock-M.nequip.pth"
            return emt_calc, f"mock-{size}.nequip.pth"

        monkeypatch.setattr(rb, "get_calculator", fake_get_calculator)
        relaxer = NequIPRelaxer("nequip-m+l", "cpu", optimizer="BFGS")
        result = relaxer.relax(_make_fcc_cu_perturbed(), fmax=0.05, steps=10)

        assert result["retry"] == 1
        assert isinstance(result["final_structure"], Structure)
        assert isinstance(result["trajectory"].energies[-1], float)
        assert isinstance(result["steps"], int)
        assert result["preoptimized"] is False

    def test_compiled_name_and_short_error_helpers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify cache filename formatting and _short_error message summarization."""
        name_ts = _compiled_name("S", "cpu", "torchscript", False)
        assert name_ts.startswith("NequIP-OAM-S-0.1__torchscript__cpu__torch")
        assert name_ts.endswith(".nequip.pth")

        name_pt2 = _compiled_name("L", "cpu", "aotinductor", True)
        assert "aotinductor-oeq__cpu" in name_pt2
        assert name_pt2.endswith(".nequip.pt2")

        assert _short_error(None) == "unknown error"
        assert "ReadTimeout" in _short_error(RuntimeError("HTTPSConnectionPool ReadTimeout"))

        monkeypatch.setattr(sys, "argv", ["relax_backends", "--relax-model", "none"])
        rb._main()

    def test_live_cached_cpu_nequip_relaxer_on_overlapping_nacl(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify live cached CPU NequIPRelaxer pre-optimizes and relaxes S01 NaCl."""
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        relaxer, resolved = make_relaxer("auto", optimizer="BFGS")
        assert resolved == "nequip-s+l"
        assert relaxer is not None

        out = relaxer.relax(_make_nacl_overlapping(), fmax=0.2, steps=100)
        assert set(out.keys()) == {
            "final_structure",
            "trajectory",
            "steps",
            "preoptimized",
            "retry",
        }
        assert out["preoptimized"] is True
        assert out["retry"] == 0
        assert out["trajectory"].energies[-1] < 0.0
        assert closest_pair_ratio(out["final_structure"]) >= 0.5
