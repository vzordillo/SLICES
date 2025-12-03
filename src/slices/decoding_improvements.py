"""
Enhanced decoding algorithms for improving SLICES decoding success rate.

This module implements scientifically-backed improvements to address common
failure modes in SLICES decoding:
1. Enhanced cycle basis selection for better lattice basis computation
2. Fallback bond parameter estimation when XTB fails
3. Multi-start optimization for ZL* algorithm
4. Progressive MLIP relaxation strategies

References:
- Boyd, P. M., & Woo, T. K. (2016). A generalized method for constructing 
  hypothetical nanoporous materials of any net topology from graph theory.
  CrystEngComm, 18(21), 3777-3792.
- Lenstra, A. K., Lenstra, H. W., & Lovász, L. (1982). Factoring polynomials 
  with rational coefficients. Mathematische Annalen, 261(4), 515-534.
- Nocedal, J., & Wright, S. (2006). Numerical optimization. Springer.
- Pauling, L. (1960). The nature of the chemical bond. Cornell University Press.
"""

import numpy as np
import time
from typing import List, Tuple, Optional, Dict, Any
from scipy.optimize import fmin_l_bfgs_b
from pymatgen.core import Element
from pymatgen.core.periodic_table import ElementBase
import logging

logger = logging.getLogger(__name__)


class CycleBasisOptimizer:
    """
    Enhanced cycle basis selection for improved lattice basis computation.
    
    Implements multiple strategies to find cycle bases that maximize the
    probability of finding integral lattice basis vectors.
    """
    
    @staticmethod
    def select_optimal_cycle_basis(cycle_rep: np.ndarray, max_attempts: int = 100) -> np.ndarray:
        """
        Select cycle basis that maximizes linear independence rank.
        
        Args:
            cycle_rep: Cycle representation matrix (n_cycles x n_edges)
            max_attempts: Maximum number of random shuffles to try
            
        Returns:
            Array of indices representing optimal cycle ordering
        """
        if cycle_rep.shape[0] == 0:
            return np.array([])
        
        best_inds = None
        best_rank = 0
        
        for attempt in range(max_attempts):
            inds = list(range(cycle_rep.shape[0]))
            np.random.shuffle(inds)
            shuffled = cycle_rep[inds]
            
            # Check linear independence rank
            rank = np.linalg.matrix_rank(shuffled)
            if rank > best_rank:
                best_rank = rank
                best_inds = np.array(inds)
        
        return best_inds if best_inds is not None else np.array(range(cycle_rep.shape[0]))
    
    @staticmethod
    def is_approximately_integral(vect: np.ndarray, tolerance: float = 1e-6) -> bool:
        """
        Check if vector is approximately integral with given tolerance.
        
        This relaxed constraint helps handle numerical errors in lattice
        basis computation while maintaining mathematical correctness.
        
        Args:
            vect: Vector to check
            tolerance: Maximum deviation from integer values
            
        Returns:
            True if vector is approximately integral
        """
        if len(vect) == 0:
            return False
        
        fractional_parts = np.mod(np.abs(vect), 1)
        # Check if all components are close to integers
        is_integral = np.all(fractional_parts < tolerance) or np.all(fractional_parts > 1 - tolerance)
        return is_integral


class BondParameterFallback:
    """
    Fallback bond parameter estimation when XTB calculation fails.
    
    Uses empirical relationships based on covalent radii and bond types
    to estimate bond lengths and angles.
    """
    
    # Covalent radii in Angstrom (from PyMatGen defaults, based on Pauling 1960)
    COVALENT_RADII = {
        'H': 0.31, 'He': 0.28, 'Li': 1.28, 'Be': 0.96, 'B': 0.84, 'C': 0.76,
        'N': 0.71, 'O': 0.66, 'F': 0.57, 'Ne': 0.58, 'Na': 1.66, 'Mg': 1.41,
        'Al': 1.21, 'Si': 1.11, 'P': 1.07, 'S': 1.05, 'Cl': 1.02, 'Ar': 1.06,
        'K': 2.03, 'Ca': 1.76, 'Sc': 1.70, 'Ti': 1.60, 'V': 1.53, 'Cr': 1.39,
        'Mn': 1.39, 'Fe': 1.32, 'Co': 1.26, 'Ni': 1.24, 'Cu': 1.32, 'Zn': 1.22,
        'Ga': 1.22, 'Ge': 1.20, 'As': 1.19, 'Se': 1.20, 'Br': 1.20, 'Kr': 1.16,
        'Rb': 2.20, 'Sr': 1.95, 'Y': 1.90, 'Zr': 1.75, 'Nb': 1.64, 'Mo': 1.54,
        'Tc': 1.47, 'Ru': 1.46, 'Rh': 1.42, 'Pd': 1.39, 'Ag': 1.45, 'Cd': 1.44,
        'In': 1.42, 'Sn': 1.39, 'Sb': 1.39, 'Te': 1.38, 'I': 1.39, 'Xe': 1.40,
        'Cs': 2.44, 'Ba': 2.15, 'La': 2.07, 'Ce': 2.04, 'Pr': 2.03, 'Nd': 2.01,
        'Pm': 1.99, 'Sm': 1.98, 'Eu': 1.98, 'Gd': 1.96, 'Tb': 1.94, 'Dy': 1.92,
        'Ho': 1.92, 'Er': 1.89, 'Tm': 1.90, 'Yb': 1.87, 'Lu': 1.87, 'Hf': 1.75,
        'Ta': 1.70, 'W': 1.62, 'Re': 1.51, 'Os': 1.44, 'Ir': 1.41, 'Pt': 1.36,
        'Au': 1.36, 'Hg': 1.32, 'Tl': 1.45, 'Pb': 1.46, 'Bi': 1.48, 'Po': 1.40,
        'At': 1.50, 'Rn': 1.50
    }
    
    @classmethod
    def estimate_bond_length(cls, atom1_symbol: str, atom2_symbol: str) -> float:
        """
        Estimate bond length using covalent radii (Pauling, 1960).
        
        Args:
            atom1_symbol: Symbol of first atom
            atom2_symbol: Symbol of second atom
            
        Returns:
            Estimated bond length in Bohr (atomic units)
        """
        r1 = cls.COVALENT_RADII.get(atom1_symbol, 1.5)
        r2 = cls.COVALENT_RADII.get(atom2_symbol, 1.5)
        
        # Sum of covalent radii in Angstrom
        bond_length_angstrom = r1 + r2
        
        # Convert to Bohr (1 Bohr = 0.529177 Angstrom)
        bond_length_bohr = bond_length_angstrom / 0.529177
        
        return bond_length_bohr
    
    @classmethod
    def estimate_bond_energy(cls, atom1_symbol: str, atom2_symbol: str, 
                            bond_length_bohr: float) -> float:
        """
        Estimate bond energy parameter using empirical relationship.
        
        Uses a simple inverse relationship: stronger bonds are shorter.
        
        Args:
            atom1_symbol: Symbol of first atom
            atom2_symbol: Symbol of second atom
            bond_length_bohr: Bond length in Bohr
            
        Returns:
            Estimated bond energy parameter
        """
        # Empirical scaling: shorter bonds = stronger bonds
        # This is a simplified model; XTB provides more accurate values
        base_energy = 1.0
        length_factor = 1.0 / (bond_length_bohr + 0.1)  # Avoid division by zero
        return base_energy * length_factor


class MultiStartOptimizer:
    """
    Multi-start optimization for ZL* algorithm to improve convergence.
    
    Runs optimization from multiple random starting points and selects
    the best result, helping escape local minima.
    """
    
    @staticmethod
    def optimize(func, x0: np.ndarray, bounds: List[Tuple[float, float]], 
                 n_starts: int = 5, **kwargs) -> Tuple[np.ndarray, float, Dict]:
        """
        Run optimization from multiple starting points.
        
        Args:
            func: Objective function to minimize
            x0: Initial guess
            bounds: List of (min, max) tuples for each variable
            n_starts: Number of random starting points
            **kwargs: Additional arguments for fmin_l_bfgs_b
            
        Returns:
            Tuple of (best_x, best_value, best_info)
        """
        best_result = None
        best_value = float('inf')
        best_info = None
        
        bounds_array = np.array(bounds)
        
        for i in range(n_starts):
            # Perturb initial guess
            if i == 0:
                x_start = x0.copy()
            else:
                # Random perturbation within bounds
                perturbation = np.random.normal(0, 0.1, size=x0.shape)
                x_start = x0 + perturbation
                x_start = np.clip(x_start, bounds_array[:, 0], bounds_array[:, 1])
            
            try:
                result = fmin_l_bfgs_b(
                    func, x_start, 
                    bounds=bounds,
                    **kwargs
                )
                
                if result[1] < best_value:  # Lower is better
                    best_value = result[1]
                    best_result = result[0]
                    best_info = result[2]
            except Exception as e:
                logger.debug(f"Optimization attempt {i+1} failed: {e}")
                continue
        
        if best_result is None:
            # Fallback to single optimization
            result = fmin_l_bfgs_b(func, x0, bounds=bounds, **kwargs)
            return result[0], result[1], (result[2] if len(result) > 2 else {})
        
        return best_result, best_value, (best_info if best_info is not None else {})


class ProgressiveRelaxer:
    """
    Progressive MLIP relaxation with fallback strategies.
    
    Attempts relaxation with progressively looser convergence criteria,
    ensuring we get a result even if tight convergence fails.
    """
    
    @staticmethod
    def get_relaxation_strategies() -> List[Dict[str, Any]]:
        """
        Get list of relaxation strategies from tight to loose.
        
        Returns:
            List of strategy dictionaries with fmax and steps
        """
        return [
            {'fmax': 0.1, 'steps': 200, 'name': 'tight'},
            {'fmax': 0.2, 'steps': 100, 'name': 'standard'},
            {'fmax': 0.3, 'steps': 80, 'name': 'loose'},
            {'fmax': 0.5, 'steps': 50, 'name': 'very_loose'},
        ]
    
    @staticmethod
    def calculate_timeout(num_atoms: int) -> int:
        """
        Calculate adaptive timeout based on structure size.
        
        Args:
            num_atoms: Number of atoms in structure
            
        Returns:
            Timeout in seconds
        """
        base_timeout = 60  # Base 60 seconds
        timeout_per_atom = 10  # 10 seconds per atom
        calculated_timeout = base_timeout + num_atoms * timeout_per_atom
        return min(calculated_timeout, 3000)  # Cap at 3000s (50 minutes)


class AdaptiveConvergence:
    """
    Adaptive convergence criteria based on structure complexity.
    """
    
    @staticmethod
    def get_convergence_params(num_atoms: int) -> Dict[str, float]:
        """
        Get convergence parameters adapted to structure size.
        
        Args:
            num_atoms: Number of atoms in structure
            
        Returns:
            Dictionary with factr and pgtol parameters
        """
        if num_atoms <= 10:
            return {'factr': 1e7, 'pgtol': 1e-5}
        elif num_atoms <= 20:
            return {'factr': 1e6, 'pgtol': 1e-4}
        elif num_atoms <= 40:
            return {'factr': 1e5, 'pgtol': 1e-3}
        else:
            return {'factr': 1e4, 'pgtol': 1e-2}  # Looser for large structures


def calculate_xtb_timeout(num_atoms: int, num_bonds: int) -> int:
    """
    Calculate adaptive XTB timeout based on structure complexity.
    
    Args:
        num_atoms: Number of atoms
        num_bonds: Number of bonds
        
    Returns:
        Timeout in seconds (capped at 120s)
    """
    base_timeout = 30
    atom_factor = num_atoms * 0.5  # 0.5s per atom
    bond_factor = num_bonds * 0.1  # 0.1s per bond
    calculated_timeout = base_timeout + atom_factor + bond_factor
    return min(int(calculated_timeout), 120)  # Cap at 120s

