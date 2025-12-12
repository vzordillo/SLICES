# -*- coding: utf-8 -*-
"""
Unified interface for multiple Machine Learning Interatomic Potential (MLIP) models
Supports: M3GNet, CHGNet, MatterSim, ORBv3

Note: MatGL has been removed due to model download/cache issues.
"""

import warnings
from abc import ABC, abstractmethod
from pymatgen.core.structure import Structure
from contextlib import contextmanager
import sys
import os

# Enable Keras 2 compatibility mode for M3GNet (must be done before any TensorFlow imports)
if "TF_USE_LEGACY_KERAS" not in os.environ:
    os.environ["TF_USE_LEGACY_KERAS"] = "1"

# Try to use tf_keras (legacy Keras 2) if available - must be done before any keras imports
try:
    import tf_keras
    # Monkey-patch keras to use tf_keras before any other modules import keras
    if 'keras' not in sys.modules:
        sys.modules['keras'] = tf_keras
except ImportError:
    # tf_keras not available, rely on TF_USE_LEGACY_KERAS env var
    pass


class MLIPRelaxer(ABC):
    """
    Abstract base class for machine learning interatomic potential (MLIP) relaxers.
    
    Provides a unified interface for different MLIP models to perform structure relaxation.
    All relaxers must implement the relax() method which optimizes atomic positions and
    optionally the unit cell to minimize the potential energy.
    """
    
    @abstractmethod
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        """
        Relax a crystal structure using the MLIP model.
        
        Performs energy minimization by optimizing atomic positions and optionally the unit cell
        until forces on all atoms are below the convergence threshold or maximum steps are reached.
        
        Args:
            structure (Structure): pymatgen Structure object to relax
            fmax (float, optional): Maximum force convergence criterion in eV/Å. Optimization stops
                when all atomic forces are below this value. Defaults to 0.2.
            steps (int, optional): Maximum number of optimization steps. Defaults to 100.
            
        Returns:
            dict: Dictionary containing:
                - 'final_structure' (Structure): Optimized Structure object
                - 'trajectory' (object): Trajectory object with 'energies' attribute (list of
                  energies at each optimization step)
        """
        pass


class M3GNetRelaxer(MLIPRelaxer):
    """
    Adapter for M3GNet (Materials Project 3D Graph Network) MLIP model.
    
    M3GNet is a graph neural network-based interatomic potential developed by the Materials Project.
    This adapter handles TensorFlow/Keras compatibility issues and provides a unified interface.
    """
    
    def __init__(self, optimizer="BFGS"):
        try:
            # Ensure TF_USE_LEGACY_KERAS is set
            if "TF_USE_LEGACY_KERAS" not in os.environ:
                os.environ["TF_USE_LEGACY_KERAS"] = "1"
            
            # Try to use tf_keras (legacy Keras 2) if available
            # This must be done before importing TensorFlow or M3GNet
            try:
                import tf_keras
                # Patch both keras and tensorflow.keras to use tf_keras
                if 'keras' not in sys.modules:
                    sys.modules['keras'] = tf_keras
                # Also patch tensorflow.keras after TensorFlow is imported
                import tensorflow as tf
                if not hasattr(tf, 'keras') or not isinstance(tf.keras, type(tf_keras)):
                    tf.keras = tf_keras
            except ImportError:
                # tf_keras not available, rely on TF_USE_LEGACY_KERAS env var
                pass
            
            from m3gnet.models import Relaxer
            self.relaxer = Relaxer(optimizer=optimizer)
        except ImportError:
            raise ImportError("M3GNet is not installed. Install with: pip install m3gnet")
        except Exception as e:
            error_str = str(e).lower()
            # If still getting Keras 3 errors, try installing tf_keras
            if "file format not supported" in error_str or "keras 3" in error_str or "only supports v3" in error_str or "keras cannot be imported" in error_str:
                raise RuntimeError(
                    f"M3GNet failed with Keras 3 compatibility issue: {str(e)[:200]}\n\n"
                    "Workaround: Install tf_keras (legacy Keras 2) package in the conda environment:\n"
                    "  conda activate slices\n"
                    "  /opt/miniconda3/envs/slices/bin/pip install tf_keras\n"
                    "Then try again. The TF_USE_LEGACY_KERAS environment variable is already set."
                ) from e
            raise
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        """
        Relax structure using M3GNet model.
        
        Args:
            structure (Structure): pymatgen Structure object
            fmax (float, optional): Maximum force convergence criterion (eV/Å). Defaults to 0.2.
            steps (int, optional): Maximum optimization steps. Defaults to 100.
            
        Returns:
            dict: Dictionary with 'final_structure' and 'trajectory' keys
        """
        return self.relaxer.relax(structure, fmax=fmax, steps=steps)


class CHGNetRelaxer(MLIPRelaxer):
    """
    Adapter for CHGNet (Charge-informed Graph Neural Network) MLIP model.
    
    CHGNet incorporates charge information into the graph neural network architecture
    for structure relaxation.
    """
    
    def __init__(self):
        try:
            from chgnet.model import StructOptimizer
            self.relaxer = StructOptimizer()
        except ImportError:
            raise ImportError("CHGNet is not installed. Install with: pip install chgnet")
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        # CHGNet StructOptimizer uses fmax and steps
        result = self.relaxer.relax(structure, fmax=fmax, steps=steps)
        # CHGNet returns dict with 'final_structure' and 'trajectory'
        # Ensure trajectory has energies attribute
        if 'trajectory' in result:
            if not hasattr(result['trajectory'], 'energies'):
                # Create compatible trajectory object
                class Trajectory:
                    def __init__(self, energies):
                        self.energies = energies
                # Extract energies from trajectory if available
                traj_energies = getattr(result['trajectory'], 'energies', [])
                if not traj_energies:
                    # Fallback: use final energy if available
                    final_energy = result.get('energy', 0.0)
                    traj_energies = [final_energy] if not isinstance(final_energy, list) else final_energy
                result['trajectory'] = Trajectory(traj_energies)
        return result


class MatterSimRelaxer(MLIPRelaxer):
    """
    Adapter for MatterSim MLIP model from Microsoft.
    
    MatterSim is a deep learning-based interatomic potential that uses ASE interface
    for structure optimization.
    """
    
    def __init__(self, device="cpu"):
        try:
            from mattersim.forcefield import MatterSimCalculator
            # MatterSimCalculator automatically loads the pretrained model
            self.calculator = MatterSimCalculator(device=device)
        except ImportError:
            raise ImportError("MatterSim is not installed. Install with: pip install mattersim")
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        # MatterSim uses ASE interface
        try:
            from pymatgen.io.ase import AseAtomsAdaptor
            from ase.optimize import BFGS
            try:
                from ase.filters import UnitCellFilter
            except ImportError:
                from ase.constraints import UnitCellFilter
            
            atoms = AseAtomsAdaptor.get_atoms(structure)
            atoms.calc = self.calculator
            
            # Use UnitCellFilter for cell relaxation
            ucf = UnitCellFilter(atoms)
            opt = BFGS(ucf)
            opt.run(fmax=fmax, steps=steps)
            
            final_structure = AseAtomsAdaptor.get_structure(atoms)
            energy = atoms.get_potential_energy()
            
            class Trajectory:
                def __init__(self, energy):
                    self.energies = [energy]
            
            return {
                'final_structure': final_structure,
                'trajectory': Trajectory(energy)
            }
        except Exception as e:
            raise RuntimeError(f"MatterSim relaxation failed: {e}")


class ORBv3Relaxer(MLIPRelaxer):
    """
    Adapter for ORBv3 (Orbital Materials) MLIP model.
    
    ORBv3 is an interatomic potential from Orbital Materials that supports multiple
    model variants. Uses ASE interface for structure optimization.
    """
    
    def __init__(self, model_name="orb-v3-direct-inf-mpa", device="cpu"):
        try:
            from orb_models.forcefield.pretrained import ORB_PRETRAINED_MODELS
            from orb_models.forcefield.calculator import ORBCalculator
            
            # Load the pretrained model
            if model_name not in ORB_PRETRAINED_MODELS:
                raise ValueError(f"Model {model_name} not found. Available models: {list(ORB_PRETRAINED_MODELS.keys())[:5]}")
            
            model_func = ORB_PRETRAINED_MODELS[model_name]
            model = model_func()
            
            # Create calculator
            self.calculator = ORBCalculator(model=model, device=device)
        except ImportError:
            raise ImportError("ORBv3 is not installed. Install with: pip install orb-models")
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        # ORBv3 uses ASE interface
        try:
            from pymatgen.io.ase import AseAtomsAdaptor
            from ase.optimize import BFGS
            try:
                from ase.filters import UnitCellFilter
            except ImportError:
                from ase.constraints import UnitCellFilter
            
            atoms = AseAtomsAdaptor.get_atoms(structure)
            atoms.calc = self.calculator
            
            # Use UnitCellFilter for cell relaxation
            ucf = UnitCellFilter(atoms)
            opt = BFGS(ucf)
            opt.run(fmax=fmax, steps=steps)
            
            final_structure = AseAtomsAdaptor.get_structure(atoms)
            energy = atoms.get_potential_energy()
            
            class Trajectory:
                def __init__(self, energy):
                    self.energies = [energy]
            
            return {
                'final_structure': final_structure,
                'trajectory': Trajectory(energy)
            }
        except Exception as e:
            raise RuntimeError(f"ORBv3 relaxation failed: {e}")


def get_relaxer(model_name: str = "m3gnet", **kwargs):
    """
    Factory function to create the appropriate MLIP relaxer instance.
    
    Creates and returns a relaxer adapter for the specified MLIP model. Handles model
    initialization, error handling, and falls back to M3GNet if the requested model is
    unavailable.
    
    Args:
        model_name (str, optional): Name of the MLIP model. Options:
            - 'm3gnet': M3GNet (Materials Project, default)
            - 'chgnet': CHGNet (charge-informed GNN)
            - 'mattersim': MatterSim (Microsoft)
            - 'orbv3': ORBv3 (Orbital Materials)
            Defaults to "m3gnet".
        **kwargs: Additional arguments passed to the relaxer constructor:
            - optimizer (str): Optimizer algorithm ("BFGS", "FIRE", etc.)
            - model_name (str): Specific model variant name (for MatGL, ORBv3)
            - device (str): Computing device ("cpu", "cuda", "mps", etc.)
        
    Returns:
        MLIPRelaxer: Instance of the appropriate relaxer class
        
    Raises:
        ValueError: If model_name is not in the list of supported models
        ImportError: If the required package for the model is not installed
        RuntimeError: If model initialization fails (e.g., Keras compatibility issues)
    """
    model_name = model_name.lower()
    
    if model_name == "m3gnet":
        optimizer = kwargs.get("optimizer", "BFGS")
        return M3GNetRelaxer(optimizer=optimizer)
    
    elif model_name == "chgnet":
        return CHGNetRelaxer()
    
    elif model_name == "mattersim":
        device = kwargs.get("device", "cpu")
        return MatterSimRelaxer(device=device)
    
    elif model_name == "orbv3":
        model_name_arg = kwargs.get("model_name", "orb-v3-direct-inf-mpa")
        device = kwargs.get("device", "cpu")
        return ORBv3Relaxer(model_name=model_name_arg, device=device)
    
    else:
        raise ValueError(f"Unsupported model: {model_name}. Supported models: m3gnet, chgnet, mattersim, orbv3")

