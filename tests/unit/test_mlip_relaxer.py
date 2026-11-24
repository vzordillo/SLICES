"""Unit tests for optional MLIP relaxer adapters and lazy-import isolation."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from ase.calculators.emt import EMT
from pymatgen.core import Lattice, Structure

from slices.exceptions import MLIPRelaxationError
from slices.mlip_relaxer import (
    OPTIONAL_MLIP_ALIASES,
    OPTIONAL_MLIP_MODELS,
    CHGNetRelaxer,
    M3GNetRelaxer,
    MACERelaxer,
    MatterSimRelaxer,
    MLIPRelaxer,
    ORBv3Relaxer,
    _ASEMLIPRelaxer,
    choose_mlip_device,
    get_relaxer,
    make_optional_relaxer,
    mlip_available,
    resolve_optional_mlip,
)
from slices.relax_backends import CellCollapse, NequIPRelaxer

pytestmark = pytest.mark.unit

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")


def _make_cu_structure(overlapping: bool = False) -> Structure:
    """Build a 4-atom fcc Cu structure (either clean or with severe atomic overlap)."""
    coords = (
        [[0.0, 0.0, 0.0], [0.08, 0.08, 0.08], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]]
        if overlapping
        else [[0.02, 0.0, 0.0], [0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]]
    )
    return Structure(Lattice.cubic(3.65), ["Cu", "Cu", "Cu", "Cu"], coords)


class TestLazyImportAndModelResolution:
    """Verify zero eager imports, alias normalization, and ImportError hints."""

    def test_import_mlip_relaxer_has_zero_side_effects(self) -> None:
        """Verify importing slices.mlip_relaxer leaves torch, TF, Keras, and env vars untouched."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OMP_NUM_THREADS", "TF_USE_LEGACY_KERAS")
        }
        env["PYTHONPATH"] = _REPO_SRC
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        code = (
            "import os, sys\n"
            "import slices.mlip_relaxer\n"
            "assert 'OMP_NUM_THREADS' not in os.environ\n"
            "assert 'TF_USE_LEGACY_KERAS' not in os.environ\n"
            "for pkg in ('torch', 'tensorflow', 'keras', 'tf_keras', 'chgnet', "
            "'mattersim', 'orb_models', 'mace', 'm3gnet', 'slices.core'):\n"
            "    assert pkg not in sys.modules, pkg\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr

    def test_optional_mlip_models_and_aliases(self) -> None:
        """Verify canonical optional model tuple and alias normalization table."""
        assert OPTIONAL_MLIP_MODELS == ("chgnet", "mattersim", "orbv3", "mace", "m3gnet")
        assert OPTIONAL_MLIP_ALIASES["orb-v3"] == "orbv3"
        assert OPTIONAL_MLIP_ALIASES["orb_v3"] == "orbv3"
        assert OPTIONAL_MLIP_ALIASES["orb"] == "orbv3"
        assert OPTIONAL_MLIP_ALIASES["mace-mp"] == "mace"
        assert OPTIONAL_MLIP_ALIASES["mace_mp"] == "mace"
        assert mlip_available("unknown_model") is False

    @pytest.mark.parametrize(
        "alias",
        ["chgnet", "mattersim", "orbv3", "orb-v3", "orb", "mace", "mace-mp", "mace_mp", "m3gnet"],
    )
    def test_uninstalled_optional_mlip_raises_clear_import_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        alias: str,
    ) -> None:
        """Verify uninstalled optional MLIPs raise ImportError with install guidance."""
        monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
        assert mlip_available(alias) is False
        with pytest.raises(ImportError) as exc_info:
            resolve_optional_mlip(alias)
        msg = str(exc_info.value).lower()
        assert "install" in msg
        if alias == "m3gnet":
            assert "nequip" in msg or "auto" in msg

    def test_unknown_optional_mlip_raises_value_error(self) -> None:
        """Verify unknown model names raise ValueError."""
        with pytest.raises(ValueError, match="Unknown relax_model"):
            resolve_optional_mlip("unknown_potential_xyz")

    def test_choose_mlip_device_variants(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify choose_mlip_device handles cpu, invalid names, and mps fallback."""
        assert choose_mlip_device("cpu") == "cpu"
        with pytest.raises(ValueError, match="Device must be"):
            choose_mlip_device("quantum_tpu")

        monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
        assert choose_mlip_device("mps") == "cpu"


class TestMockedASEAndConcreteMLIPAdapters:
    """Verify _ASEMLIPRelaxer and all 5 concrete adapters using lightweight mocks."""

    def test_ase_mlip_relaxer_five_key_contract_and_preoptimize(self) -> None:
        """Verify _ASEMLIPRelaxer returns the exact 5-key NequIPRelaxer-compatible dict."""
        relaxer = _ASEMLIPRelaxer(
            name="mock-emt",
            device="cpu",
            optimizer="BFGS",
            calculator=EMT(),
            model_label="EMT",
        )
        assert isinstance(relaxer, MLIPRelaxer)
        assert relaxer.name == "mock-emt"
        assert relaxer.device == "cpu"
        assert relaxer.optimizer == "BFGS"
        assert "EMT" in relaxer.description

        out = relaxer.relax(_make_cu_structure(overlapping=True), fmax=0.05, steps=25)
        assert set(out.keys()) == {
            "final_structure",
            "trajectory",
            "steps",
            "preoptimized",
            "retry",
        }
        assert isinstance(out["final_structure"], Structure)
        assert isinstance(out["trajectory"].energies[-1], float)
        assert isinstance(out["steps"], int)
        assert out["preoptimized"] is True
        assert out["retry"] == 0

        with pytest.raises(ValueError, match="optimizer"):
            _ASEMLIPRelaxer("mock", "cpu", "INVALID_OPT", EMT(), "EMT")

    def test_ase_mlip_relaxer_collapse_retry_and_persistent_failure(self) -> None:
        """Verify _ASEMLIPRelaxer retries once with FIRE on CellCollapse and wraps fatal errors."""
        calls = {"count": 0}
        emt_calc = EMT()

        class CollapseOnceEMT:
            """Calculator wrapper raising CellCollapse on the first force/energy call."""

            def get_potential_energy(self, atoms: Any = None, **kwargs: Any) -> float:
                self.calculate(atoms)
                return float(emt_calc.get_potential_energy(atoms))

            def get_forces(self, atoms: Any = None, **kwargs: Any) -> np.ndarray:
                self.calculate(atoms)
                return np.asarray(emt_calc.get_forces(atoms), dtype=float)

            def get_stress(self, atoms: Any = None, **kwargs: Any) -> np.ndarray:
                self.calculate(atoms)
                return np.asarray(emt_calc.get_stress(atoms), dtype=float)

            def calculate(self, atoms: Any = None, *args: Any, **kwargs: Any) -> None:
                calls["count"] += 1
                if calls["count"] == 1:
                    raise CellCollapse("initial step collapsed")

        relaxer = _ASEMLIPRelaxer("mock-emt", "cpu", "BFGS", CollapseOnceEMT(), "EMT")
        res = relaxer.relax(_make_cu_structure(), fmax=0.05, steps=10)
        assert res["retry"] == 1

        class AlwaysCollapseCalc(CollapseOnceEMT):
            """Calculator wrapper that always raises CellCollapse."""

            def calculate(self, atoms: Any = None, *args: Any, **kwargs: Any) -> None:
                raise CellCollapse("permanent collapse")

        failing = _ASEMLIPRelaxer("mock-fail", "cpu", "BFGS", AlwaysCollapseCalc(), "Fail")
        with pytest.raises(MLIPRelaxationError, match="after cell collapse retry"):
            failing.relax(_make_cu_structure(), fmax=0.05, steps=5)

    def test_mocked_concrete_adapters_and_get_relaxer_factory(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify CHGNet, MatterSim, ORBv3, MACE, and M3GNet adapters via mocked modules."""
        monkeypatch.setattr(importlib.util, "find_spec", lambda _: object())
        cu = _make_cu_structure()

        # 1. CHGNet mocked module.
        chg_pkg = types.ModuleType("chgnet")
        chg_mod = types.ModuleType("chgnet.model")
        chg_mod.CHGNetCalculator = lambda use_device="cpu": EMT()  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "chgnet", chg_pkg)
        monkeypatch.setitem(sys.modules, "chgnet.model", chg_mod)
        chg = make_optional_relaxer("chgnet", device="cpu")
        assert isinstance(chg, CHGNetRelaxer)
        assert isinstance(chg.relax(cu, fmax=0.1, steps=5)["final_structure"], Structure)

        # 2. MatterSim mocked module.
        ms_pkg = types.ModuleType("mattersim")
        ms_ff = types.ModuleType("mattersim.forcefield")
        ms_ff.MatterSimCalculator = lambda **_: EMT()  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "mattersim", ms_pkg)
        monkeypatch.setitem(sys.modules, "mattersim.forcefield", ms_ff)
        ms = make_optional_relaxer("mattersim", device="cpu")
        assert isinstance(ms, MatterSimRelaxer)
        assert isinstance(ms.relax(cu, fmax=0.1, steps=5)["final_structure"], Structure)

        # 3. ORBv3 mocked module (via alias 'orb-v3').
        orb_pkg = types.ModuleType("orb_models")
        orb_ff = types.ModuleType("orb_models.forcefield")
        orb_calc_mod = types.ModuleType("orb_models.forcefield.calculator")
        orb_pre_mod = types.ModuleType("orb_models.forcefield.pretrained")
        orb_calc_mod.ORBCalculator = lambda model=None, device="cpu": EMT()  # type: ignore[attr-defined]
        orb_pre_mod.ORB_PRETRAINED_MODELS = {  # type: ignore[attr-defined]
            "orb-v3-conservative-inf-omat": lambda device="cpu": object()
        }
        monkeypatch.setitem(sys.modules, "orb_models", orb_pkg)
        monkeypatch.setitem(sys.modules, "orb_models.forcefield", orb_ff)
        monkeypatch.setitem(sys.modules, "orb_models.forcefield.calculator", orb_calc_mod)
        monkeypatch.setitem(sys.modules, "orb_models.forcefield.pretrained", orb_pre_mod)
        orb = make_optional_relaxer("orb-v3", device="cpu")
        assert isinstance(orb, ORBv3Relaxer)
        assert orb.name == "orbv3"

        # 4. MACE mocked module (via alias 'mace-mp').
        mace_pkg = types.ModuleType("mace")
        mace_calc = types.ModuleType("mace.calculators")
        mace_calc.mace_mp = lambda **_: EMT()  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "mace", mace_pkg)
        monkeypatch.setitem(sys.modules, "mace.calculators", mace_calc)
        mace_rel = make_optional_relaxer("mace-mp", device="cpu")
        assert isinstance(mace_rel, MACERelaxer)
        assert mace_rel.name == "mace"

        # 5. M3GNet mocked module (verifying TF_USE_LEGACY_KERAS is scoped inside __init__).
        monkeypatch.delenv("TF_USE_LEGACY_KERAS", raising=False)
        tf_mod = types.ModuleType("tensorflow")
        m3_pkg = types.ModuleType("m3gnet")
        m3_models = types.ModuleType("m3gnet.models")

        class FakeM3GNetRelaxer:
            """Lightweight stand-in for m3gnet.models.Relaxer."""

            def __init__(self, optimizer: str = "BFGS") -> None:
                self.optimizer = optimizer

            def relax(self, structure: Structure, **_: Any) -> dict[str, Any]:
                return {
                    "final_structure": structure,
                    "trajectory": types.SimpleNamespace(energies=[-12.5, -13.25]),
                }

        m3_models.Relaxer = FakeM3GNetRelaxer  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "tensorflow", tf_mod)
        monkeypatch.setitem(sys.modules, "m3gnet", m3_pkg)
        monkeypatch.setitem(sys.modules, "m3gnet.models", m3_models)
        assert "TF_USE_LEGACY_KERAS" not in os.environ
        m3 = M3GNetRelaxer(device="cpu")
        assert os.environ.get("TF_USE_LEGACY_KERAS") == "1"
        m3_out = m3.relax(cu, fmax=0.1, steps=5)
        assert m3_out["trajectory"].energies == [-13.25]
        assert m3_out["steps"] == 2

    def test_get_relaxer_delegates_none_and_auto(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify get_relaxer handles None/'none' and delegates 'auto' to NequIPRelaxer."""
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        assert get_relaxer(None) is None
        assert get_relaxer("none") is None
        auto_rel = get_relaxer("auto")
        assert isinstance(auto_rel, NequIPRelaxer)


@pytest.mark.mlip
@pytest.mark.parametrize("model_name", OPTIONAL_MLIP_MODELS)
def test_live_optional_mlip_when_installed(model_name: str) -> None:
    """Run a live NaCl smoke relaxation when an optional MLIP package is installed."""
    if not mlip_available(model_name):
        pytest.skip(f"Optional MLIP package for {model_name!r} is not installed")
    relaxer = make_optional_relaxer(model_name, device="cpu")
    nacl = Structure(Lattice.cubic(4.3), ["Na", "Cl"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])
    out = relaxer.relax(nacl, fmax=0.2, steps=10)
    assert isinstance(out["final_structure"], Structure)
    assert np.isfinite(out["trajectory"].energies[-1])
