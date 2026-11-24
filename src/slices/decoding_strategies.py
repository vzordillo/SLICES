"""Opt-in multi-stage decoding and recovery strategies for SLICES reconstruction.

Provides standalone recovery utilities invoked **exclusively** when a caller
opts into :meth:`slices.core.SLICES.robust_SLICES2structure` (or
``slices decode --robust``). Standard ``SLICES.to_structures()`` and
``SLICES.SLICES2structure()`` never import or execute this module, preserving
exact SLICES v4.0.2 baseline determinism.

Key components:

* :func:`robust_decode`: Multi-stage recovery pipeline (standard v4.0.2 fast
  path -> optional cycle-basis / covalent-radii fallback + seeded multi-start
  ZL* optimization -> progressive force-field relaxation).
* :class:`MultiStartOptimizer`: Seeded multi-start L-BFGS-B wrapper using an
  isolated ``numpy.random.Generator`` (zero global RNG mutation).
* :class:`AdaptiveConvergence`: Atom-count-scaled L-BFGS-B tolerances.
* :class:`ProgressiveRelaxer`: Multi-tier force-field relaxation schedule.
* :class:`CycleBasisOptimizer` & :func:`is_approximately_integral`: Opt-in
  cycle-ordering and approximate integrality helpers for edge-case nets.
* :class:`BondParameterFallback`: Covalent-radius bond-length estimator when
  topology bond parameters are missing.

References:
    * Boyd, P. G., & Woo, T. K. (2016). CrystEngComm, 18(21), 3777-3792.
    * Lenstra, A. K., Lenstra, H. W., & Lovasz, L. (1982). Math. Ann., 261, 515-534.
    * Nocedal, J., & Wright, S. J. (2006). Numerical Optimization (2nd ed.). Springer.
    * Pauling, L. (1960). The Nature of the Chemical Bond (3rd ed.). Cornell Univ. Press.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

from slices.exceptions import SLICESDecodingError

if TYPE_CHECKING:
    from collections.abc import Callable

    from pymatgen.core.structure import Structure

    from slices.core import SLICES
    from slices.tobascco_net import Net

__all__ = [
    "AdaptiveConvergence",
    "BondParameterFallback",
    "CycleBasisOptimizer",
    "MultiStartOptimizer",
    "ProgressiveRelaxer",
    "calculate_topology_timeout",
    "calculate_xtb_timeout",
    "is_approximately_integral",
    "robust_decode",
]

_logger = logging.getLogger(__name__)

_BOHR_TO_ANGSTROM: float = 0.529177
_SUPPORTED_DECODE_STRATEGIES: tuple[int, ...] = (1, 3, 4)


def is_approximately_integral(vect: np.ndarray, tolerance: float = 1e-6) -> bool:
    """Return whether ``vect`` is non-zero and every entry is within ``tolerance`` of an integer.

    Uses elementwise comparison so vectors mixing slightly positive and slightly
    negative rounding residuals (e.g., ``[1.0 + 1e-8, 2.0 - 1e-8]``) are handled
    accurately.

    Args:
        vect: Candidate 1D numeric array.
        tolerance: Maximum absolute deviation from the nearest integer.
            Defaults to ``1e-6``.

    Returns:
        ``True`` if ``vect`` is non-empty, non-zero, and elementwise integral
        within ``tolerance``; ``False`` otherwise.
    """
    arr = np.asarray(vect, dtype=float)
    if arr.size == 0 or bool(np.all(np.abs(arr) <= tolerance)):
        return False
    fractional_parts = np.mod(np.abs(arr), 1.0)
    near_int = (fractional_parts <= tolerance) | (fractional_parts >= 1.0 - tolerance)
    return bool(np.all(near_int))


class CycleBasisOptimizer:
    """Opt-in cycle-ordering and approximate-integrality helpers for periodic nets."""

    @staticmethod
    def is_approximately_integral(vect: np.ndarray, tolerance: float = 1e-6) -> bool:
        """Delegate to :func:`is_approximately_integral`."""
        return is_approximately_integral(vect, tolerance=tolerance)

    @staticmethod
    def select_optimal_cycle_basis(
        cycle_rep: np.ndarray,
        max_attempts: int = 50,
        seed: int | None = 0,
    ) -> np.ndarray:
        """Select a cycle-row permutation whose leading spanning subset is well-conditioned.

        Row permutations of ``cycle_rep`` preserve total matrix rank, but SymPy's
        nullspace basis construction depends on row pivot ordering. This helper
        scores candidate permutations by the smallest singular value of the first
        ``rank`` linearly independent rows using an isolated RNG.

        Args:
            cycle_rep: Cycle voltage matrix ``(N_cycles, ndim)``.
            max_attempts: Number of candidate shuffles to evaluate. Defaults to 50.
            seed: Seed for ``numpy.random.default_rng``. Defaults to 0.

        Returns:
            1D integer index array of length ``N_cycles``.
        """
        n_cycles = int(cycle_rep.shape[0])
        if n_cycles == 0:
            return np.array([], dtype=int)

        target_rank = int(np.linalg.matrix_rank(cycle_rep))
        if target_rank == 0:
            return np.arange(n_cycles, dtype=int)

        rng = np.random.default_rng(seed)
        best_inds = np.arange(n_cycles, dtype=int)
        best_score = -1.0

        for attempt in range(max(1, max_attempts)):
            inds = (
                np.arange(n_cycles, dtype=int)
                if attempt == 0
                else rng.permutation(n_cycles)
            )
            shuffled = cycle_rep[inds]
            selected_rows: list[np.ndarray] = []
            for row in shuffled:
                candidate = np.vstack([*selected_rows, row]) if selected_rows else row[None, :]
                if np.linalg.matrix_rank(candidate) > len(selected_rows):
                    selected_rows.append(row)
                    if len(selected_rows) == target_rank:
                        break
            if len(selected_rows) == target_rank:
                sv = np.linalg.svd(np.vstack(selected_rows), compute_uv=False)
                score = float(sv[-1]) / max(float(sv[0]), 1e-12)
                if score > best_score:
                    best_score = score
                    best_inds = inds.copy()

        return best_inds

    @classmethod
    def find_lattice_basis(
        cls,
        net: Net,
        max_attempts: int = 20,
        tolerance: float = 1e-6,
        seed: int | None = 0,
    ) -> bool:
        """Attempt to populate ``net.lattice_basis`` across seeded cycle permutations.

        Args:
            net: Initialized :class:`slices.tobascco_net.Net` with ``cycle`` and
                ``cycle_rep`` already computed.
            max_attempts: Maximum cycle-ordering attempts. Defaults to 20.
            tolerance: Integrality tolerance for nullspace combinations.
                Defaults to ``1e-6``.
            seed: Random seed for candidate permutations. Defaults to 0.

        Returns:
            ``True`` if a full ``ndim`` integral lattice basis was found and
            stored in ``net.lattice_basis``; ``False`` otherwise.
        """
        import sympy as sy

        if net.cycle_rep is None or net.cycle is None or len(net.cycle_rep) == 0:
            return False

        rng = np.random.default_rng(seed)
        n_cycles = len(net.cycle_rep)
        preferred = cls.select_optimal_cycle_basis(
            net.cycle_rep,
            max_attempts=min(25, max(1, max_attempts)),
            seed=seed,
        )

        for attempt in range(max(1, max_attempts)):
            inds = preferred if attempt == 0 else rng.permutation(n_cycles)
            cycle_rep = net.cycle_rep[inds]
            cycle = net.cycle[inds]
            lattice: list[np.ndarray] = []
            all_found = True
            for basis_vec in np.identity(net.ndim):
                kk = np.vstack((basis_vec, cycle_rep))
                null = np.array(
                    [np.array(k).flatten() for k in sy.Matrix(kk.T).nullspace()],
                    dtype=float,
                )
                found_vec = False
                for nulv in null:
                    if abs(nulv[0]) > 1e-8:
                        v = -nulv[1:] / nulv[0]
                        nz = np.nonzero(v)
                        tv = np.sum(cycle[nz] * v[nz][:, None], axis=0)
                        if is_approximately_integral(tv, tolerance=tolerance):
                            lattice.append(np.rint(tv))
                            found_vec = True
                            break
                if not found_vec:
                    all_found = False
                    break
            if all_found and len(lattice) == net.ndim:
                net.lattice_basis = np.array(lattice, dtype=float)
                return True
        return False


class BondParameterFallback:
    """Covalent-radius bond-parameter fallback when GFN-FF bond targets are unavailable."""

    @staticmethod
    def _covalent_radius_angstrom(symbol: str) -> float:
        """Return the covalent radius in Angstrom for element ``symbol``."""
        from pymatgen.analysis.local_env import CovalentRadius

        return float(CovalentRadius.radius.get(symbol, 1.5))

    @classmethod
    def estimate_bond_length(cls, atom1_symbol: str, atom2_symbol: str) -> float:
        """Estimate equilibrium bond length in Bohr from sum of covalent radii.

        Args:
            atom1_symbol: Chemical symbol of the first bonded site.
            atom2_symbol: Chemical symbol of the second bonded site.

        Returns:
            Estimated bond length in atomic units (Bohr).
        """
        r1 = cls._covalent_radius_angstrom(atom1_symbol)
        r2 = cls._covalent_radius_angstrom(atom2_symbol)
        return (r1 + r2) / _BOHR_TO_ANGSTROM

    @classmethod
    def estimate_bond_energy(
        cls,
        atom1_symbol: str,
        atom2_symbol: str,
        bond_length_bohr: float,
    ) -> float:
        """Estimate relative bond-stretching weight from bond length in Bohr.

        Args:
            atom1_symbol: Chemical symbol of the first bonded site.
            atom2_symbol: Chemical symbol of the second bonded site.
            bond_length_bohr: Equilibrium bond length in Bohr.

        Returns:
            Positive heuristic bond weight.
        """
        _ = (atom1_symbol, atom2_symbol)
        return 1.0 / (max(float(bond_length_bohr), 0.0) + 0.1)

    @classmethod
    def build_inner_p_target(
        cls,
        atom_types: np.ndarray,
        edge_indices: np.ndarray,
        bond_scaling: float = 1.05,
    ) -> tuple[np.ndarray, list[list[int]], list[float]]:
        """Build a diagonal covalent-radius ``inner_p_target`` matrix using 0-based indices.

        Safely maps atom indices modulo ``len(atom_types)`` so both unit-cell
        0-based indices and 1-based supercell indices (when converted via
        ``idx - 1``) never raise ``IndexError``.

        Args:
            atom_types: Atomic numbers ``(N_atoms,)`` of unit-cell sites.
            edge_indices: Edge endpoint index pairs ``(N_edges, 2)`` (0-based).
            bond_scaling: Empirical bond-length scale factor. Defaults to ``1.05``.

        Returns:
            Tuple ``(inner_p_target, colattice_inds, colattice_weights)``.
        """
        from pymatgen.core.periodic_table import ElementBase

        n_atoms = len(atom_types)
        n_edges = len(edge_indices)
        symbols = [str(ElementBase.from_Z(int(z))) for z in atom_types]
        inner_p_target = np.zeros((n_edges, n_edges), dtype=float)
        raw_weights: list[float] = []

        for i in range(n_edges):
            idx0 = int(edge_indices[i][0]) % n_atoms
            idx1 = int(edge_indices[i][1]) % n_atoms
            bohr = cls.estimate_bond_length(symbols[idx0], symbols[idx1])
            length_ang = bohr * _BOHR_TO_ANGSTROM * 1.05 * bond_scaling
            inner_p_target[i, i] = round(length_ang**2, 5)
            raw_weights.append(cls.estimate_bond_energy(symbols[idx0], symbols[idx1], bohr))

        max_w = max(raw_weights) if raw_weights else 1.0
        colattice_inds: list[list[int]] = [list(range(n_edges)), list(range(n_edges))]
        colattice_weights = [round(w / max_w, 2) for w in raw_weights]
        return inner_p_target, colattice_inds, colattice_weights


class MultiStartOptimizer:
    """Seeded multi-start wrapper around ``scipy.optimize.fmin_l_bfgs_b``."""

    @staticmethod
    def optimize(
        func: Callable[..., float],
        x0: np.ndarray,
        bounds: list[tuple[float, float]],
        n_starts: int = 3,
        seed: int | None = 0,
        perturbation_scale: float = 0.1,
        **kwargs: Any,
    ) -> tuple[np.ndarray, float, dict[str, Any]]:
        """Minimize ``func`` from ``x0`` plus ``n_starts - 1`` seeded perturbations.

        Uses ``numpy.random.default_rng(seed)`` so global ``numpy.random`` state
        is never mutated, and strips deprecated ``scipy>=1.15`` ``iprint`` /
        ``disp`` keyword arguments automatically.

        Args:
            func: Objective callable returning a scalar float.
            x0: Initial parameter guess ``(D,)``.
            bounds: Box ``(lower, upper)`` bounds of length ``D``.
            n_starts: Number of starting points to evaluate (>= 1). Defaults to 3.
            seed: Seed for the local random generator. Defaults to 0.
            perturbation_scale: Standard deviation of Gaussian perturbations
                added on starts ``1 .. n_starts - 1``. Defaults to ``0.1``.
            **kwargs: Extra keyword arguments forwarded to ``fmin_l_bfgs_b``.

        Returns:
            Tuple ``(best_x, best_fval, best_info_dict)`` achieving the lowest
            objective value across all starts.
        """
        from scipy.optimize import fmin_l_bfgs_b

        clean_kwargs = dict(kwargs)
        clean_kwargs.pop("iprint", None)
        clean_kwargs.pop("disp", None)
        clean_kwargs.setdefault("approx_grad", clean_kwargs.get("fprime") is None)

        rng = np.random.default_rng(seed)
        bounds_arr = np.asarray(bounds, dtype=float)
        best_x: np.ndarray | None = None
        best_val = float("inf")
        best_info: dict[str, Any] = {}

        for start_idx in range(max(1, n_starts)):
            if start_idx == 0:
                x_start = np.array(x0, dtype=float, copy=True)
            else:
                delta = rng.normal(0.0, perturbation_scale, size=x0.shape)
                x_start = np.clip(x0 + delta, bounds_arr[:, 0], bounds_arr[:, 1])

            try:
                x_opt, f_opt, info = fmin_l_bfgs_b(
                    func,
                    x_start,
                    bounds=bounds,
                    **clean_kwargs,
                )
                f_scalar = float(f_opt)
                if np.isfinite(f_scalar) and f_scalar < best_val:
                    best_val = f_scalar
                    best_x = np.asarray(x_opt, dtype=float)
                    best_info = dict(info) if isinstance(info, dict) else {}
            except Exception as exc:
                _logger.debug("Multi-start L-BFGS-B start %d failed: %s", start_idx, exc)

        if best_x is None:
            x_opt, f_opt, info = fmin_l_bfgs_b(func, x0, bounds=bounds, **clean_kwargs)
            return (
                np.asarray(x_opt, dtype=float),
                float(f_opt),
                dict(info) if isinstance(info, dict) else {},
            )

        return best_x, best_val, best_info


class AdaptiveConvergence:
    """Atom-count-scaled convergence tolerances for opt-in ZL* optimization."""

    @staticmethod
    def get_convergence_params(num_atoms: int) -> dict[str, float]:
        """Return ``{"factr": ..., "pgtol": ...}`` scaled by ``num_atoms``.

        Args:
            num_atoms: Number of atoms in the unit cell.

        Returns:
            Dictionary with ``factr`` and ``pgtol`` parameters for L-BFGS-B.
        """
        if num_atoms <= 10:
            return {"factr": 1e7, "pgtol": 1e-5}
        if num_atoms <= 20:
            return {"factr": 1e6, "pgtol": 1e-4}
        if num_atoms <= 40:
            return {"factr": 1e5, "pgtol": 1e-3}
        return {"factr": 1e4, "pgtol": 1e-2}


class ProgressiveRelaxer:
    """Progressive force-field relaxation schedule for opt-in error recovery."""

    @staticmethod
    def get_relaxation_strategies(
        base_fmax: float = 0.2,
        base_steps: int = 100,
    ) -> list[dict[str, Any]]:
        """Return ordered relaxation tiers starting from caller's ``(base_fmax, base_steps)``.

        Args:
            base_fmax: Primary force threshold in eV/Angstrom. Defaults to ``0.2``.
            base_steps: Primary step budget. Defaults to ``100``.

        Returns:
            Ordered list of ``{"name", "fmax", "steps"}`` tier dictionaries.
        """
        tiers: list[dict[str, Any]] = [
            {"name": "primary", "fmax": float(base_fmax), "steps": int(base_steps)},
            {
                "name": "moderate",
                "fmax": max(float(base_fmax), 0.3),
                "steps": max(int(base_steps), 120),
            },
            {
                "name": "loose",
                "fmax": max(float(base_fmax), 0.5),
                "steps": max(int(base_steps), 150),
            },
        ]
        # Deduplicate consecutive identical (fmax, steps) pairs.
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[float, int]] = set()
        for tier in tiers:
            key = (tier["fmax"], tier["steps"])
            if key not in seen:
                seen.add(key)
                deduped.append(tier)
        return deduped

    @staticmethod
    def calculate_timeout(num_atoms: int) -> int:
        """Compute an adaptive wall-clock timeout (seconds) capped at 3000 seconds.

        Args:
            num_atoms: Number of atoms in the structure.

        Returns:
            Timeout in seconds.
        """
        return min(60 + int(num_atoms) * 10, 3000)

    @classmethod
    def relax_with_fallbacks(
        cls,
        slices_inst: SLICES,
        structure: Structure,
    ) -> tuple[Structure, float] | None:
        """Attempt force-field relaxation across progressive tiers, restoring instance state.

        Args:
            slices_inst: Configured :class:`slices.core.SLICES` instance.
            structure: Candidate ZL*-optimized or rescaled ``Structure``.

        Returns:
            Tuple ``(relaxed_structure, energy_per_atom)`` on first succeeding
            tier, or ``None`` if ``slices_inst.relaxer`` is ``None`` or all tiers
            fail.
        """
        if slices_inst.relaxer is None:
            return None
        num_nodes = len(structure)
        orig_fmax = slices_inst.fmax
        orig_steps = slices_inst.steps
        for tier in cls.get_relaxation_strategies(orig_fmax, orig_steps):
            try:
                slices_inst.fmax = tier["fmax"]
                slices_inst.steps = tier["steps"]
                if num_nodes <= 20:
                    return slices_inst.relax(structure)
                if num_nodes <= 40:
                    return slices_inst.relax_large_cell1(structure)
                return slices_inst.relax_large_cell2(structure)
            except Exception as exc:
                _logger.debug("Progressive relaxation tier %s failed: %s", tier["name"], exc)
            finally:
                slices_inst.fmax = orig_fmax
                slices_inst.steps = orig_steps
        return None


def calculate_topology_timeout(num_atoms: int, num_bonds: int) -> int:
    """Compute an adaptive external topology-helper timeout (capped at 120 seconds).

    Args:
        num_atoms: Number of atoms in the unit cell.
        num_bonds: Number of edges in the unit cell.

    Returns:
        Timeout in seconds.
    """
    raw = 30.0 + float(num_atoms) * 0.5 + float(num_bonds) * 0.1
    return min(int(raw), 120)


# Backward-compatible alias retained for pre-v4.0 callers.
calculate_xtb_timeout = calculate_topology_timeout


def _reconstruct_zl_multistart(
    slices_inst: SLICES,
    n_starts: int = 3,
    seed: int = 0,
    bond_scaling: float = 1.05,
) -> tuple[Structure, Structure]:
    """Reconstruct ``(std_structure, opt_structure)`` with opt-in fallbacks and multi-start ZL*."""
    import networkx as nx
    from networkx.algorithms import tree
    from pymatgen.core.periodic_table import ElementBase
    from pymatgen.core.structure import Structure

    from slices.tobascco_net import Net

    x_dat, net_voltage = slices_inst.convert_graph()
    net = Net(x_dat, dim=3)
    net.voltage = net_voltage
    net.simple_cycle_basis()
    basis_status = net.get_lattice_basis()
    if (
        basis_status == -1 or net.lattice_basis is None
    ) and not CycleBasisOptimizer.find_lattice_basis(net, max_attempts=20, seed=seed):
        raise SLICESDecodingError(
            "Could not construct an integral 3D lattice basis from cycle vectors."
        )
    net.get_cocycle_basis()

    target_res = slices_inst.get_inner_p_target(bond_scaling)
    if target_res is None or np.any(np.diag(target_res[0]) <= 0.0):
        inner_p_target, colattice_inds, colattice_weights = (
            BondParameterFallback.build_inner_p_target(
                slices_inst.atom_types,
                slices_inst.edge_indices,
                bond_scaling=bond_scaling,
            )
        )
    else:
        inner_p_target, colattice_inds, colattice_weights = target_res

    uncovered_pair = slices_inst.get_uncovered_pair(net.graph)
    uncovered_pair_lj = slices_inst.get_uncovered_pair_lj(uncovered_pair)
    covered_pair_lj = slices_inst.get_covered_pair_lj()

    if net.cocycle is not None:
        net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
    else:
        net.periodic_rep = net.cycle_rep
    net.get_metric_tensor()
    lattice_vectors_std = np.linalg.cholesky(net.metric_tensor)
    arc_coord_std = net.lattice_arcs

    num_nodes = len(net.graph.nodes)
    g_di = nx.MultiDiGraph()
    g_di.add_nodes_from(net.vertices())
    g_di.add_edges_from(net.all_edges())
    edges = list(g_di.edges)
    g_undir = nx.MultiGraph()
    g_undir.add_nodes_from(net.vertices())
    g_undir.add_edges_from(net.all_edges())
    spanning = list(tree.minimum_spanning_edges(g_undir, algorithm="kruskal", data=False))
    for i in range(len(spanning)):
        for edge in edges:
            if spanning[i][2] == edge[2]:
                spanning[i] = edge
    spanning_graph = nx.MultiGraph()
    spanning_graph.add_nodes_from(g_di.nodes)
    spanning_graph.add_edges_from(spanning)
    shortest_path = nx.shortest_path(spanning_graph, source="1")

    inner_p_std = np.dot(np.dot(net.lattice_arcs, net.metric_tensor), net.lattice_arcs.T)
    lattice_vectors_scaled = slices_inst.get_rescaled_lattice_vectors(
        inner_p_target,
        inner_p_std,
        lattice_vectors_std,
        arc_coord_std,
    )
    metric_tensor_std = np.dot(lattice_vectors_scaled, lattice_vectors_scaled.T)
    if slices_inst.unstable_graph:
        net.cocycle_rep = np.zeros((net.order - 1, net.ndim)) + 0.5
        net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
        arc_coord_std = net.lattice_arcs

    coordinates_std = slices_inst.get_coordinates(
        arc_coord_std,
        num_nodes,
        shortest_path,
        spanning,
    )
    atom_symbols = [str(ElementBase.from_Z(int(z))) for z in slices_inst.atom_types]
    std_structure = Structure(lattice_vectors_scaled, atom_symbols, coordinates_std)

    if net.cocycle_rep is None:
        return std_structure, std_structure

    diag_vals = [metric_tensor_std[0, 0], metric_tensor_std[1, 1], metric_tensor_std[2, 2]]
    lattice_type = len(set(diag_vals))
    if lattice_type == 2:
        if metric_tensor_std[0, 0] == metric_tensor_std[1, 1]:
            lattice_type = 23
        if metric_tensor_std[0, 0] == metric_tensor_std[2, 2]:
            lattice_type = 22
        if metric_tensor_std[2, 2] == metric_tensor_std[1, 1]:
            lattice_type = 21

    x0, bounds = slices_inst.initialize_x_bounds(
        net.ndim,
        net.cocycle_rep,
        metric_tensor_std,
        lattice_type,
        0.005,
        0.45,
        1.25,
        1.0,
    )
    conv = AdaptiveConvergence.get_convergence_params(num_nodes)

    def objective(x_vec: np.ndarray) -> float:
        return slices_inst.func(
            x_vec,
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
            0.00,
            0.01,
            lattice_vectors_scaled,
            atom_symbols,
            0.5,
            True,
            lattice_type,
            metric_tensor_std,
        )

    x_best, _, _ = MultiStartOptimizer.optimize(
        objective,
        x0,
        bounds,
        n_starts=n_starts,
        seed=seed,
        fprime=None,
        approx_grad=True,
        m=10,
        factr=conv["factr"],
        pgtol=conv["pgtol"],
        epsilon=1e-8,
        maxfun=15000,
        maxiter=15000,
        maxls=20,
    )
    net.metric_tensor, net.cocycle_rep = slices_inst.convert_params(
        x_best,
        net.ndim,
        int(net.order - 1),
        lattice_type,
        metric_tensor_std,
    )
    lattice_vectors_new = np.linalg.cholesky(net.metric_tensor)
    if net.cocycle is not None:
        net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
    else:
        net.periodic_rep = net.cycle_rep
    coordinates_new = slices_inst.get_coordinates(
        net.lattice_arcs,
        num_nodes,
        shortest_path,
        spanning,
    )
    opt_structure = Structure(lattice_vectors_new, atom_symbols, coordinates_new)
    return std_structure, opt_structure


def robust_decode(
    slices_inst: SLICES,
    slices_str: str,
    strategy: int = 4,
    fix_duplicate_edge: bool = True,
    n_starts: int = 3,
    seed: int = 0,
) -> tuple[Structure, float]:
    """Decode ``slices_str`` using standard v4.0.2 decoding with multi-stage recovery fallbacks.

    Stage 1 executes the untouched ``SLICES.from_SLICES`` + ``SLICES.to_structures``
    pipeline, returning immediately whenever standard decoding succeeds. Only if
    standard reconstruction raises an error or fails force-field relaxation does
    Stage 2/3 run opt-in cycle-basis / covalent-radius fallbacks, seeded
    multi-start ZL* optimization, and progressive relaxation tiers.

    Args:
        slices_inst: Active :class:`slices.core.SLICES` encoder/decoder instance.
        slices_str: Input SLICES representation string.
        strategy: Encoding strategy format (1, 3, or 4). Defaults to 4.
        fix_duplicate_edge: Whether to deduplicate repeated edges. Defaults to ``True``.
        n_starts: Number of seeded starting points for fallback ZL* optimization.
            Defaults to 3.
        seed: Seed for deterministic fallback perturbations. Defaults to 0.

    Returns:
        Tuple ``(structure, energy_per_atom)`` in eV/atom (``0.0`` if force-field
        relaxation is disabled or all relaxation fallbacks fail).

    Raises:
        SLICESDecodingError: If ``strategy`` is unsupported, ``slices_str`` is
            syntactically invalid, or all embedding stages fail.
    """
    if strategy not in _SUPPORTED_DECODE_STRATEGIES:
        raise SLICESDecodingError(
            f"Unsupported decoding strategy {strategy!r}; choose from "
            f"{_SUPPORTED_DECODE_STRATEGIES} (strategy 2 is encode-only)."
        )

    try:
        slices_inst.from_SLICES(
            slices_str,
            strategy=strategy,
            fix_duplicate_edge=fix_duplicate_edge,
        )
    except Exception as exc:
        raise SLICESDecodingError(f"Invalid SLICES string: {exc}") from exc

    fallback_std: Structure | None = None
    fallback_opt: Structure | None = None

    # Stage 1: Standard untouched v4.0.2 path.
    try:
        structures, energy = slices_inst.to_structures()
        if slices_inst.relaxer is None or len(structures) == 3:
            return structures[-1], float(energy)
        if len(structures) >= 2:
            fallback_std, fallback_opt = structures[0], structures[1]
        elif len(structures) == 1:
            fallback_std = structures[0]
    except Exception as exc:
        _logger.debug("Standard to_structures() failed, entering robust fallback: %s", exc)

    # Stage 2: Opt-in topology/bond-parameter fallback + seeded multi-start ZL*.
    try:
        std_struct, opt_struct = _reconstruct_zl_multistart(
            slices_inst,
            n_starts=n_starts,
            seed=seed,
        )
    except Exception as exc:
        if fallback_opt is not None:
            std_struct, opt_struct = fallback_std or fallback_opt, fallback_opt
        elif fallback_std is not None:
            std_struct, opt_struct = fallback_std, fallback_std
        else:
            raise SLICESDecodingError(
                f"All SLICES decoding strategies failed: {exc}"
            ) from exc

    # Stage 3: Progressive force-field relaxation across candidates.
    if slices_inst.relaxer is not None:
        for candidate in (opt_struct, std_struct):
            relaxed = ProgressiveRelaxer.relax_with_fallbacks(slices_inst, candidate)
            if relaxed is not None:
                return relaxed[0], float(relaxed[1])

    return opt_struct, 0.0
