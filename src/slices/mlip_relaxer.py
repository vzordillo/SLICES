"""Optional machine-learning interatomic potential (MLIP) relaxer adapters.

Extends :mod:`slices.relax_backends` with opt-in adapters for external force-field
packages while keeping the default SLICES v4.0.2 NequIP-OAM backends
(``"auto"``, ``"nequip-s+l"``, ``"nequip-m+l"``, ``"nequip-l"``, ``None``)
completely untouched.

Supported optional ``relax_model`` identifiers:

* ``"chgnet"``: Charge-informed Graph Neural Network (``pip install chgnet``).
* ``"mattersim"``: Microsoft MatterSim universal potential (``pip install mattersim``).
* ``"orbv3"`` (aliases ``"orb-v3"``, ``"orb_v3"``, ``"orb"``): Orbital Materials
  ORBv3 force field (``pip install orb-models``).
* ``"mace"`` (aliases ``"mace-mp"``, ``"mace_mp"``): MACE-MP foundation potential
  (``pip install mace-torch``).
* ``"m3gnet"``: Legacy Materials Project M3GNet potential (``pip install m3gnet``
  plus ``tf_keras`` in a TensorFlow-compatible environment).

All heavy deep-learning frameworks (PyTorch, TensorFlow, ASE calculators) are
imported lazily inside adapter constructors so importing this module has zero
startup overhead or global environment side effects.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from slices.exceptions import MLIPRelaxationError
from slices.relax_backends import (
    OPTIMIZERS,
    RELAX_MODELS,
    CellCollapse,
    _announce,
    _cell_filter,
    _collapse_guard,
    _log,
    _optimize,
    choose_device,
    make_relaxer,
    preoptimize,
)

if TYPE_CHECKING:
    from pymatgen.core.structure import Structure

__all__ = [
    "OPTIONAL_MLIP_ALIASES",
    "OPTIONAL_MLIP_MODELS",
    "CHGNetRelaxer",
    "M3GNetRelaxer",
    "MACERelaxer",
    "MLIPRelaxer",
    "MatterSimRelaxer",
    "ORBv3Relaxer",
    "choose_mlip_device",
    "get_relaxer",
    "make_optional_relaxer",
    "mlip_available",
    "resolve_optional_mlip",
]

OPTIONAL_MLIP_MODELS: tuple[str, ...] = (
    "chgnet",
    "mattersim",
    "orbv3",
    "mace",
    "m3gnet",
)

OPTIONAL_MLIP_ALIASES: dict[str, str] = {
    "chgnet": "chgnet",
    "mattersim": "mattersim",
    "orbv3": "orbv3",
    "orb-v3": "orbv3",
    "orb_v3": "orbv3",
    "orb": "orbv3",
    "mace": "mace",
    "mace-mp": "mace",
    "mace_mp": "mace",
    "m3gnet": "m3gnet",
}

_INSTALL_HINTS: dict[str, str] = {
    "chgnet": (
        "relax_model='chgnet' requires the optional 'chgnet' package; "
        "install with `pip install chgnet` or use relax_model='auto' (NequIP-OAM)."
    ),
    "mattersim": (
        "relax_model='mattersim' requires the optional 'mattersim' package; "
        "install with `pip install mattersim` or use relax_model='auto' (NequIP-OAM)."
    ),
    "orbv3": (
        "relax_model='orbv3' requires the optional 'orb-models' package; "
        "install with `pip install orb-models` or use relax_model='auto' (NequIP-OAM)."
    ),
    "mace": (
        "relax_model='mace' requires the optional 'mace-torch' package; "
        "install with `pip install mace-torch` or use relax_model='auto' (NequIP-OAM)."
    ),
    "m3gnet": (
        "relax_model='m3gnet' is an optional legacy backend (replaced as the SLICES v4.0 "
        "default by NequIP-OAM via relax_model='auto'). To use legacy M3GNet opt-in, "
        "install `m3gnet` and `tf_keras` in a TensorFlow-compatible environment."
    ),
}

_PACKAGE_SPECS: dict[str, tuple[str, ...]] = {
    "chgnet": ("chgnet",),
    "mattersim": ("mattersim",),
    "orbv3": ("orb_models",),
    "mace": ("mace",),
    "m3gnet": ("m3gnet", "tensorflow"),
}


def mlip_available(model_name: str) -> bool:
    """Return ``True`` if the distribution(s) required for ``model_name`` are installed.

    Args:
        model_name: Canonical or alias optional MLIP model identifier.

    Returns:
        ``True`` if all required top-level modules can be located via
        ``importlib.util.find_spec``, else ``False``.
    """
    canonical = OPTIONAL_MLIP_ALIASES.get(model_name.strip().lower())
    if canonical is None:
        return False
    required = _PACKAGE_SPECS[canonical]
    return all(importlib.util.find_spec(pkg) is not None for pkg in required)


def choose_mlip_device(explicit_device: str | None = None) -> str:
    """Resolve compute device for PyTorch-backed optional MLIP relaxers.

    Honors ``explicit_device`` when provided; otherwise inspects ``SLICES_DEVICE``
    (supporting ``"cpu"``, ``"cuda"``, and Apple Silicon ``"mps"`` for optional
    PyTorch MLIPs, defaulting to ``"cpu"``).

    Args:
        explicit_device: Optional explicit device string override.

    Returns:
        Resolved device string (``"cpu"``, ``"cuda"``, or ``"mps"``).

    Raises:
        ValueError: If the requested device string is unsupported.
    """
    raw = (explicit_device or os.environ.get("SLICES_DEVICE", "")).strip().lower() or "cpu"
    if raw == "mps":
        if importlib.util.find_spec("torch") is not None:
            import torch

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        _announce("SLICES_DEVICE=mps requested but PyTorch MPS is unavailable; using CPU")
        return "cpu"
    if explicit_device is not None:
        if raw not in ("cpu", "cuda"):
            raise ValueError(
                f"Device must be 'cpu', 'cuda', or 'mps', got {explicit_device!r}"
            )
        if raw == "cuda" and importlib.util.find_spec("torch") is not None:
            import torch

            if not torch.cuda.is_available():
                _announce("CUDA requested but torch sees no CUDA GPU; using CPU")
                return "cpu"
        return raw
    return choose_device()


def resolve_optional_mlip(name: str) -> tuple[str, str]:
    """Resolve an optional MLIP model name into ``(canonical_name, device)``.

    Args:
        name: Requested optional MLIP name or alias.

    Returns:
        Tuple ``(canonical_name, resolved_device)``.

    Raises:
        ValueError: If ``name`` is neither a built-in ``RELAX_MODELS`` entry nor a
            supported optional MLIP identifier.
        ImportError: If the required optional package is not installed.
    """
    key = str(name).strip().lower()
    if key not in OPTIONAL_MLIP_ALIASES:
        valid = RELAX_MODELS + OPTIONAL_MLIP_MODELS
        raise ValueError(f"Unknown relax_model {name!r}; choose from {valid}")
    canonical = OPTIONAL_MLIP_ALIASES[key]
    if not mlip_available(canonical):
        raise ImportError(_INSTALL_HINTS[canonical])
    if canonical == "m3gnet":
        raw_dev = os.environ.get("SLICES_DEVICE", "").strip().lower() or "cpu"
        if raw_dev not in ("cpu", "cuda"):
            raise ValueError(f"SLICES_DEVICE must be 'cpu' or 'cuda', got {raw_dev!r}")
        return canonical, raw_dev
    return canonical, choose_mlip_device()


class MLIPRelaxer(ABC):
    """Abstract base class for optional MLIP crystal structure relaxers.

    All subclasses expose ``name``, ``device``, ``optimizer``, and ``description``
    attributes and return a ``NequIPRelaxer``-compatible dictionary from
    :meth:`relax` whose ``trajectory.energies[-1]`` holds total potential energy
    in eV.
    """

    name: str
    device: str
    optimizer: str
    description: str

    @abstractmethod
    def relax(
        self,
        structure: Structure,
        fmax: float = 0.2,
        steps: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Relax ``structure`` and return a ``NequIPRelaxer``-compatible result dict.

        Args:
            structure: Input ``pymatgen`` ``Structure`` to relax.
            fmax: Maximum atomic force threshold in eV/Angstrom. Defaults to ``0.2``.
            steps: Maximum number of optimization steps. Defaults to ``100``.
            **kwargs: Extra keyword arguments accepted for interface compatibility.

        Returns:
            Dictionary with keys ``final_structure``, ``trajectory`` (namespace
            with ``energies`` list of total energies in eV), ``steps``,
            ``preoptimized``, and ``retry``.
        """


class _ASEMLIPRelaxer(MLIPRelaxer):
    """Shared ASE relaxation engine with overlap pre-optimization and collapse guards."""

    def __init__(
        self,
        name: str,
        device: str,
        optimizer: str,
        calculator: Any,
        model_label: str,
    ) -> None:
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        self.name = name
        self.device = device
        self.optimizer = optimizer
        self.calculator = calculator
        self.description = f"relax {model_label}, optimizer {optimizer}"

    def relax(
        self,
        structure: Structure,
        fmax: float = 0.2,
        steps: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Relax ``structure`` using the shared ASE cell filter and safety guards."""
        from pymatgen.io.ase import AseAtomsAdaptor

        structure_clean, pre = preoptimize(structure)
        atoms = AseAtomsAdaptor.get_atoms(structure_clean)
        retry = 0
        try:
            with _collapse_guard(self.calculator, atoms):
                atoms.calc = self.calculator
                n_steps = _optimize(_cell_filter(atoms), self.optimizer, fmax, steps)
        except CellCollapse as exc:
            from ase.optimize import FIRE

            retry = 1
            atoms = AseAtomsAdaptor.get_atoms(structure_clean)
            try:
                with _collapse_guard(self.calculator, atoms):
                    atoms.calc = self.calculator
                    opt = FIRE(_cell_filter(atoms), logfile=None, maxstep=0.1)
                    opt.run(fmax=fmax, steps=2 * steps)
                    n_steps = int(opt.nsteps)
                _log(f"{self.name} relaxation collapsed ({exc}); retried with FIRE")
            except Exception as retry_exc:
                raise MLIPRelaxationError(
                    f"{self.name} relaxation failed after cell collapse retry: {retry_exc}"
                ) from retry_exc
        except Exception as exc:
            raise MLIPRelaxationError(f"{self.name} relaxation failed: {exc}") from exc

        atoms.calc = None
        final = AseAtomsAdaptor.get_structure(atoms)
        atoms.calc = self.calculator
        energy = float(atoms.get_potential_energy())
        return {
            "final_structure": final,
            "trajectory": types.SimpleNamespace(energies=[energy]),
            "steps": int(n_steps),
            "preoptimized": bool(pre["applied"]),
            "retry": int(retry),
        }


class CHGNetRelaxer(_ASEMLIPRelaxer):
    """Adapter for CHGNet (Charge-informed Graph Neural Network)."""

    def __init__(
        self,
        device: str | None = None,
        optimizer: str = "BFGS",
    ) -> None:
        """Initialize the CHGNet ASE calculator or StructOptimizer fallback.

        Args:
            device: Compute device (``"cpu"``, ``"cuda"``, or ``"mps"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.

        Raises:
            ImportError: If ``chgnet`` is not installed.
            ValueError: If ``optimizer`` is unsupported.
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        if importlib.util.find_spec("chgnet") is None:
            raise ImportError(_INSTALL_HINTS["chgnet"])
        resolved_device = choose_mlip_device(device)
        self._struct_optimizer: Any = None
        try:
            from chgnet.model import CHGNetCalculator

            calc = CHGNetCalculator(use_device=resolved_device)
            super().__init__(
                name="chgnet",
                device=resolved_device,
                optimizer=optimizer,
                calculator=calc,
                model_label="CHGNet",
            )
        except ImportError:
            from chgnet.model import StructOptimizer

            opt_cls = "FIRE" if optimizer == "FIRE+BFGS" else optimizer
            self._struct_optimizer = StructOptimizer(
                optimizer_class=opt_cls,
                use_device=resolved_device,
            )
            self.name = "chgnet"
            self.device = resolved_device
            self.optimizer = optimizer
            self.calculator = None
            self.description = f"relax CHGNet (StructOptimizer), optimizer {optimizer}"

    def relax(
        self,
        structure: Structure,
        fmax: float = 0.2,
        steps: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Relax ``structure`` using CHGNet."""
        if self._struct_optimizer is None:
            return super().relax(structure, fmax=fmax, steps=steps, **kwargs)

        structure_clean, pre = preoptimize(structure)
        try:
            raw = self._struct_optimizer.relax(
                structure_clean,
                fmax=fmax,
                steps=steps,
                verbose=False,
            )
        except Exception as exc:
            raise MLIPRelaxationError(f"chgnet relaxation failed: {exc}") from exc
        final = raw["final_structure"]
        traj = raw.get("trajectory")
        energies = getattr(traj, "energies", None)
        if not energies:
            raise MLIPRelaxationError("chgnet trajectory did not report energies")
        return {
            "final_structure": final,
            "trajectory": types.SimpleNamespace(energies=[float(energies[-1])]),
            "steps": len(energies),
            "preoptimized": bool(pre["applied"]),
            "retry": 0,
        }


class MatterSimRelaxer(_ASEMLIPRelaxer):
    """Adapter for Microsoft MatterSim universal interatomic potential."""

    def __init__(
        self,
        device: str | None = None,
        optimizer: str = "BFGS",
        model_name: str | None = None,
    ) -> None:
        """Initialize ``MatterSimCalculator``.

        Args:
            device: Compute device (``"cpu"``, ``"cuda"``, or ``"mps"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.
            model_name: Optional checkpoint path or identifier (defaults to
                ``SLICES_MATTERSIM_MODEL`` if set, else MatterSim's default).
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        if importlib.util.find_spec("mattersim") is None:
            raise ImportError(_INSTALL_HINTS["mattersim"])
        resolved_device = choose_mlip_device(device)
        from mattersim.forcefield import MatterSimCalculator

        load_path = model_name or os.environ.get("SLICES_MATTERSIM_MODEL") or None
        calc = (
            MatterSimCalculator(load_path=load_path, device=resolved_device)
            if load_path
            else MatterSimCalculator(device=resolved_device)
        )
        label = f"MatterSim ({load_path})" if load_path else "MatterSim"
        super().__init__(
            name="mattersim",
            device=resolved_device,
            optimizer=optimizer,
            calculator=calc,
            model_label=label,
        )


class ORBv3Relaxer(_ASEMLIPRelaxer):
    """Adapter for Orbital Materials ORBv3 pretrained force fields."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        optimizer: str = "BFGS",
    ) -> None:
        """Initialize ``ORBCalculator``.

        Args:
            model_name: Pretrained ORB model key (defaults to
                ``SLICES_ORBV3_MODEL`` if set, else
                ``"orb-v3-conservative-inf-omat"`` when available or
                ``"orb-v3-direct-inf-mpa"``).
            device: Compute device (``"cpu"``, ``"cuda"``, or ``"mps"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        if importlib.util.find_spec("orb_models") is None:
            raise ImportError(_INSTALL_HINTS["orbv3"])
        resolved_device = choose_mlip_device(device)
        from orb_models.forcefield.calculator import ORBCalculator
        from orb_models.forcefield.pretrained import ORB_PRETRAINED_MODELS

        variant = model_name or os.environ.get("SLICES_ORBV3_MODEL")
        if not variant:
            variant = (
                "orb-v3-conservative-inf-omat"
                if "orb-v3-conservative-inf-omat" in ORB_PRETRAINED_MODELS
                else "orb-v3-direct-inf-mpa"
            )
        if variant not in ORB_PRETRAINED_MODELS:
            available = sorted(ORB_PRETRAINED_MODELS)[:8]
            raise ValueError(
                f"ORBv3 model {variant!r} not found; available examples: {available}"
            )
        loader = ORB_PRETRAINED_MODELS[variant]
        try:
            orbff = loader(device=resolved_device)
        except TypeError:
            orbff = loader()
        calc = ORBCalculator(model=orbff, device=resolved_device)
        super().__init__(
            name="orbv3",
            device=resolved_device,
            optimizer=optimizer,
            calculator=calc,
            model_label=f"ORBv3 ({variant})",
        )


class MACERelaxer(_ASEMLIPRelaxer):
    """Adapter for MACE-MP foundation interatomic potentials."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        optimizer: str = "BFGS",
    ) -> None:
        """Initialize ``mace_mp`` ASE calculator.

        Args:
            model_name: MACE-MP model size or checkpoint path (defaults to
                ``SLICES_MACE_MODEL`` if set, else ``"medium"``).
            device: Compute device (``"cpu"``, ``"cuda"``, or ``"mps"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        if importlib.util.find_spec("mace") is None:
            raise ImportError(_INSTALL_HINTS["mace"])
        resolved_device = choose_mlip_device(device)
        from mace.calculators import mace_mp

        variant = model_name or os.environ.get("SLICES_MACE_MODEL") or "medium"
        calc = mace_mp(
            model=variant,
            device=resolved_device,
            default_dtype="float32",
        )
        super().__init__(
            name="mace",
            device=resolved_device,
            optimizer=optimizer,
            calculator=calc,
            model_label=f"MACE-MP ({variant})",
        )


class M3GNetRelaxer(MLIPRelaxer):
    """Opt-in legacy adapter for Materials Project M3GNet (TensorFlow/Keras 2)."""

    def __init__(
        self,
        device: str | None = None,
        optimizer: str = "BFGS",
    ) -> None:
        """Initialize legacy ``m3gnet.models.Relaxer`` with scoped Keras 2 compatibility.

        Args:
            device: Compute device label (``"cpu"`` or ``"cuda"``).
            optimizer: Optimizer name from ``OPTIMIZERS``.
        """
        if optimizer not in OPTIMIZERS:
            raise ValueError(
                f"optimizer {optimizer!r} is not supported; choose from {OPTIMIZERS}"
            )
        if not mlip_available("m3gnet"):
            raise ImportError(_INSTALL_HINTS["m3gnet"])

        self.name = "m3gnet"
        self.device = (device or os.environ.get("SLICES_DEVICE", "")).strip().lower() or "cpu"
        self.optimizer = optimizer
        self.description = f"relax M3GNet (MP-2021.2.8-EFS), optimizer {optimizer}"

        # Scoped legacy Keras 2 setup strictly inside M3GNetRelaxer initialization.
        os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")
        try:
            import tf_keras

            sys.modules.setdefault("keras", tf_keras)
            import tensorflow as tf

            if not hasattr(tf, "keras") or not isinstance(tf.keras, type(tf_keras)):
                tf.keras = tf_keras
        except ImportError:
            pass

        opt_name = "FIRE" if optimizer == "FIRE+BFGS" else optimizer
        try:
            from m3gnet.models import Relaxer

            self._relaxer = Relaxer(optimizer=opt_name)
        except ImportError as exc:
            raise ImportError(_INSTALL_HINTS["m3gnet"]) from exc
        except Exception as exc:
            msg = str(exc).lower()
            if "keras 3" in msg or "only supports v3" in msg or "file format not supported" in msg:
                raise MLIPRelaxationError(
                    f"Legacy M3GNet failed due to Keras 3 incompatibility ({exc}). "
                    "Install `tf_keras` or switch to `relax_model='auto'` (NequIP-OAM)."
                ) from exc
            raise MLIPRelaxationError(f"M3GNet initialization failed: {exc}") from exc

    def relax(
        self,
        structure: Structure,
        fmax: float = 0.2,
        steps: int = 100,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Relax ``structure`` using legacy M3GNet."""
        structure_clean, pre = preoptimize(structure)
        try:
            raw = self._relaxer.relax(structure_clean, fmax=fmax, steps=steps)
        except Exception as exc:
            raise MLIPRelaxationError(f"m3gnet relaxation failed: {exc}") from exc
        final = raw["final_structure"]
        traj = raw.get("trajectory")
        energies = getattr(traj, "energies", None)
        if not energies:
            raise MLIPRelaxationError("m3gnet trajectory did not report energies")
        return {
            "final_structure": final,
            "trajectory": types.SimpleNamespace(energies=[float(energies[-1])]),
            "steps": len(energies),
            "preoptimized": bool(pre["applied"]),
            "retry": 0,
        }


def make_optional_relaxer(
    name: str,
    device: str | None = None,
    optimizer: str = "BFGS",
    model_variant: str | None = None,
) -> MLIPRelaxer:
    """Instantiate the optional MLIP relaxer corresponding to ``name``.

    Args:
        name: Canonical or alias optional MLIP identifier.
        device: Compute device (``"cpu"``, ``"cuda"``, or ``"mps"``). When
            ``None``, resolves automatically via :func:`resolve_optional_mlip`.
        optimizer: Optimizer name from ``OPTIMIZERS``. Defaults to ``"BFGS"``.
        model_variant: Optional model checkpoint/variant name for ``mattersim``,
            ``orbv3``, or ``mace``.

    Returns:
        Configured :class:`MLIPRelaxer` instance.

    Raises:
        ValueError: If ``name`` or ``optimizer`` is invalid.
        ImportError: If the required optional MLIP package is not installed.
    """
    canonical, resolved_device = resolve_optional_mlip(name)
    target_device = device or resolved_device
    if canonical == "chgnet":
        return CHGNetRelaxer(device=target_device, optimizer=optimizer)
    if canonical == "mattersim":
        return MatterSimRelaxer(
            device=target_device,
            optimizer=optimizer,
            model_name=model_variant,
        )
    if canonical == "orbv3":
        return ORBv3Relaxer(
            model_name=model_variant,
            device=target_device,
            optimizer=optimizer,
        )
    if canonical == "mace":
        return MACERelaxer(
            model_name=model_variant,
            device=target_device,
            optimizer=optimizer,
        )
    if canonical == "m3gnet":
        return M3GNetRelaxer(device=target_device, optimizer=optimizer)
    raise ValueError(f"Unsupported optional MLIP model: {name!r}")


def get_relaxer(model_name: str | None = "auto", **kwargs: Any) -> Any:
    """Create a built-in NequIP relaxer or an optional MLIP relaxer.

    Provides a unified factory compatible with both SLICES v4.0.2 built-in
    ``RELAX_MODELS`` (delegated to :func:`slices.relax_backends.make_relaxer`)
    and optional external MLIP adapters.

    Args:
        model_name: Force-field identifier (default ``"auto"`` -> ``"nequip-s+l"``).
        **kwargs: Optional keyword arguments:
            * ``optimizer`` (``str``): Optimizer name (default ``"BFGS"``).
            * ``device`` (``str | None``): Compute device override for optional MLIPs.
            * ``model_variant`` or ``variant`` (``str | None``): Model variant
              name for ``orbv3``, ``mace``, or ``mattersim``.

    Returns:
        Relaxer instance (or ``None`` when ``model_name`` resolves to ``"none"``).
    """
    optimizer = str(kwargs.get("optimizer", "BFGS"))
    if model_name is None:
        return None
    norm = str(model_name).strip().lower()
    if norm in RELAX_MODELS:
        relaxer, _ = make_relaxer(norm, optimizer=optimizer)
        return relaxer
    device = kwargs.get("device")
    variant = kwargs.get("model_variant") or kwargs.get("variant")
    return make_optional_relaxer(
        norm,
        device=device,
        optimizer=optimizer,
        model_variant=variant,
    )
