# -*- coding: utf-8 -*-
"""
Unified interface for multiple Machine Learning Interatomic Potential (MLIP) models
Supports: M3GNet, MatGL, CHGNet, MatterSim, ORBv3
"""

import warnings
from abc import ABC, abstractmethod
from pymatgen.core.structure import Structure
from contextlib import contextmanager
import sys
import os


class MLIPRelaxer(ABC):
    """Abstract base class for MLIP relaxers"""
    
    @abstractmethod
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        """
        Relax a structure using the MLIP model.
        
        Args:
            structure: pymatgen Structure object
            fmax: Maximum force convergence criterion (eV/Angstrom)
            steps: Maximum number of optimization steps
            
        Returns:
            dict with keys:
                - 'final_structure': Optimized Structure object
                - 'trajectory': Object with 'energies' attribute (list of energies)
        """
        pass


class M3GNetRelaxer(MLIPRelaxer):
    """M3GNet relaxer adapter"""
    
    def __init__(self, optimizer="BFGS"):
        try:
            from m3gnet.models import Relaxer
            self.relaxer = Relaxer(optimizer=optimizer)
        except ImportError:
            raise ImportError("M3GNet is not installed. Install with: pip install m3gnet")
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        return self.relaxer.relax(structure, fmax=fmax, steps=steps)


class MatGLRelaxer(MLIPRelaxer):
    """MatGL relaxer adapter"""
    
    def __init__(self, model_name="MP3-2024.2.8-PES", optimizer="FIRE"):
        try:
            from matgl.ext.ase import Relaxer
            from matgl import load_model
            # Try to load the MatGL model
            # If model_name fails, try default model
            try:
                potential, state = load_model(model_name)
            except Exception:
                # Try with default model name
                try:
                    potential, state = load_model()
                except Exception:
                    # Try alternative model names
                    potential, state = load_model("MP3-2024.2.8-PES")
            # Create relaxer with potential
            self.relaxer = Relaxer(potential=potential, optimizer=optimizer, relax_cell=True)
        except ImportError:
            raise ImportError("MatGL is not installed. Install with: pip install matgl")
    
    def relax(self, structure: Structure, fmax: float = 0.2, steps: int = 100):
        # MatGL Relaxer uses fmax in eV/Angstrom (same as M3GNet)
        result = self.relaxer.relax(structure, fmax=fmax, steps=steps)
        # MatGL returns dict with 'final_structure' and 'trajectory'
        # Ensure trajectory has energies attribute
        if 'trajectory' in result and hasattr(result['trajectory'], 'energies'):
            return result
        else:
            # Create a compatible trajectory object
            class Trajectory:
                def __init__(self, energies):
                    self.energies = energies
            return {
                'final_structure': result.get('final_structure', result.get('structure')),
                'trajectory': Trajectory(result.get('energies', [result.get('energy', 0.0)]))
            }


class CHGNetRelaxer(MLIPRelaxer):
    """CHGNet relaxer adapter"""
    
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
    """MatterSim relaxer adapter"""
    
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
    """ORBv3 relaxer adapter"""
    
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
    Factory function to get the appropriate relaxer based on model name.
    
    Args:
        model_name: Name of the MLIP model. Options: 'm3gnet', 'matgl', 'chgnet', 'mattersim', 'orbv3'
        **kwargs: Additional arguments passed to the relaxer constructor
        
    Returns:
        MLIPRelaxer instance
        
    Raises:
        ValueError: If model_name is not supported
        ImportError: If required package is not installed
    """
    model_name = model_name.lower()
    
    if model_name == "m3gnet":
        optimizer = kwargs.get("optimizer", "BFGS")
        return M3GNetRelaxer(optimizer=optimizer)
    
    elif model_name == "matgl":
        model_name_arg = kwargs.get("model_name", "MP3-2024.2.8-PES")
        optimizer = kwargs.get("optimizer", "FIRE")
        return MatGLRelaxer(model_name=model_name_arg, optimizer=optimizer)
    
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
        raise ValueError(f"Unsupported model: {model_name}. Supported models: m3gnet, matgl, chgnet, mattersim, orbv3")

