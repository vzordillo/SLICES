"""Core invertible crystal representation (SLICES) encoder and decoder.

Implements conversion between 3D periodic crystal structures and SLICES strings
via labeled quotient graphs, Eon's barycentric net embedding, GFN-FF equilibrium
bond/angle target generation, ZL* non-barycentric optimization, and force-field
structural relaxation.
"""

from __future__ import annotations

# Hang Xiao 2023.04
# xiaohang07@live.cn
import os
import random
import warnings

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONWARNINGS"] = "ignore"

import copy
import gc
import json
import math
import re
import signal
import sys
import threading
from collections import defaultdict, deque
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from networkx.algorithms import tree
from pymatgen.analysis.dimensionality import (
    get_dimensionality_larsen,
    get_structure_components,
)
from pymatgen.analysis.graphs import StructureGraph
from pymatgen.analysis.local_env import CrystalNN, EconNN, MinimumDistanceNN
from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core.composition import Composition
from pymatgen.core.periodic_table import Element, ElementBase
from pymatgen.core.structure import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy.optimize import fmin_l_bfgs_b

try:
    from pymatgen.analysis.local_env import BrunnerNN_reciprocal
except ImportError:  # renamed to BrunnerNNReciprocal in pymatgen 2026.3
    from pymatgen.analysis.local_env import (
        BrunnerNNReciprocal as BrunnerNN_reciprocal,
    )

from slices.config import LJ_PARAMS_LIST, OFFSET, PERIODIC_DATA
from slices.exceptions import (
    CocycleBasisError,
    GFNFFExecutionError,
    GraphTopologyError,
    LatticeBasisError,
    MLIPRelaxationError,
    ModelDownloadError,
    RelaxBackendError,
    SLICESDecodingError,
    SLICESEncodingError,
    SLICESError,
    TimeoutException,
    XTBExecutionError,
)
from slices.gfnff_helper import run_gfnff_helper, write_debug_files
from slices.relax_backends import make_relaxer
from slices.tobascco_net import Net
from slices.utils_wyckoff import get_space_group_num_from_letter_enc, get_tokenized_enc

__all__ = [
    "SLICES",
    "CocycleBasisError",
    "GFNFFExecutionError",
    "GraphTopologyError",
    "LatticeBasisError",
    "MLIPRelaxationError",
    "ModelDownloadError",
    "RelaxBackendError",
    "SLICESDecodingError",
    "SLICESEncodingError",
    "SLICESError",
    "TimeoutException",
    "XTBExecutionError",
    "function_timeout",
]


# === Timeout Utilities ===


def function_timeout(seconds: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator that enforces a wall-clock timeout on POSIX main threads.

    Uses ``signal.SIGALRM`` when available and running on the main thread of the
    main Python interpreter; otherwise executes the wrapped function directly
    without signal manipulation.

    Args:
        seconds: Time limit in seconds before raising :class:`TimeoutException`.

    Returns:
        A decorator wrapping a callable with the configured timeout limit.

    Raises:
        TimeoutException: If the wrapped call exceeds ``seconds`` on a POSIX
            main thread.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @contextmanager
        def time_limit(seconds_: int) -> Iterator[None]:
            if (
                hasattr(signal, "SIGALRM")
                and threading.current_thread() is threading.main_thread()
            ):

                def signal_handler(signum: int, frame: Any) -> None:
                    raise TimeoutException("Timed out!")

                signal.signal(signal.SIGALRM, signal_handler)
                signal.alarm(seconds_)
                try:
                    yield
                finally:
                    signal.alarm(0)
            else:
                yield

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with time_limit(seconds):
                return func(*args, **kwargs)

        return wrapper

    return decorator


class SLICES:
    """Invertible crystal representation via SLICES strings and labeled quotient graphs."""

    # === Initialization & Output Suppression ===

    def __init__(
        self,
        atom_types: np.ndarray | None = None,
        edge_indices: np.ndarray | None = None,
        to_jimages: np.ndarray | None = None,
        graph_method: str = "econnn",
        check_results: bool = False,
        optimizer: str = "BFGS",
        fmax: float = 0.2,
        steps: int = 100,
        relax_model: str | None = "auto",
    ) -> None:
        """Initialize a SLICES encoder/decoder instance.

        Args:
            atom_types: Atomic numbers (Z) of atoms in a parsed SLICES graph.
                Defaults to ``None``.
            edge_indices: Directed edge endpoint index pairs ``(N_edges, 2)``.
                Defaults to ``None``.
            to_jimages: Periodic image translation triplets ``(N_edges, 3)``.
                Defaults to ``None``.
            graph_method: Local-environment method used to construct labeled
                quotient graphs (``'econnn'``, ``'crystalnn'``, ``'brunnernn'``,
                or ``'mininn'``). Defaults to ``'econnn'``.
            check_results: Whether to write intermediate debug files and print
                diagnostic output. Defaults to ``False``.
            optimizer: Cell relaxation optimizer (``"BFGS"``, ``"LBFGS"``,
                ``"FIRE"``, or ``"FIRE+BFGS"``). Defaults to ``"BFGS"``.
            fmax: Maximum atomic force convergence threshold in eV/Angstrom.
                Defaults to ``0.2``.
            steps: Maximum force-field optimization steps for cells up to 40
                atoms. Defaults to ``100``.
            relax_model: Force field used for final structural relaxation.
                Defaults to ``"auto"``, which resolves to ``"nequip-s+l"`` on CPU
                (or ``SLICES_RELAX_MODEL`` when set; GPU execution is opt-in via
                ``SLICES_DEVICE=cuda``). Other built-in values are
                ``"nequip-s+l"``, ``"nequip-m+l"``, ``"nequip-l"``, and ``None``
                or ``"none"`` to disable relaxation. Optional MLIP adapters
                (``"chgnet"``, ``"mattersim"``, ``"orbv3"``, ``"mace"``,
                ``"m3gnet"``) are supported when their packages are installed.
                After initialization, ``self.relax_model`` stores the resolved
                canonical backend name.
        """
        gc.collect()
        self.atom_types = atom_types
        self.edge_indices = edge_indices
        self.to_jimages = to_jimages
        self.graph_method = graph_method
        self.check_results = check_results
        self.atom_symbols: list[str] | None = None
        self.SLICES: str | None = None
        self.unstable_graph = False
        self.fmax = fmax
        self.steps = steps
        self.space_group_num: int | None = None
        self.relaxer, self.relax_model = make_relaxer(relax_model, optimizer)

    @contextmanager
    def suppress_output(self) -> Iterator[None]:
        """Temporarily redirect Python ``sys.stdout`` and ``sys.stderr`` to ``os.devnull``."""
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

    @staticmethod
    def get_index_list_allow_duplicates(ori: list[Any], mod: list[Any]) -> list[int]:
        """Map elements in ``ori`` to their matching positions in ``mod`` preserving duplicates.

        Args:
            ori: Original sequence of elements.
            mod: Permuted sequence containing the same multiset of elements.

        Returns:
            List of indices into ``mod`` corresponding to each entry in ``ori``.
        """
        indexes: defaultdict[Any, deque[int]] = defaultdict(deque)
        for i, x in enumerate(mod):
            indexes[x].append(i)
        ids = [indexes[x].popleft() for x in ori]
        return ids

    # === Element, Dimensionality & Structure-Graph Construction ===

    @staticmethod
    def check_element(structure: Structure) -> bool:
        """Return whether every atom in ``structure`` has atomic number ``Z < 87``.

        Enforces the ``Z <= 86`` element filter inherited from the legacy 86-element
        GFN-FF parameter set (note: ``slices.gfnff_helper`` additionally supports
        ``Z = 87..103`` via modern library fallback when invoked directly).

        Args:
            structure: Input pymatgen ``Structure``.

        Returns:
            ``True`` if all sites satisfy ``Z < 87``, else ``False``.
        """
        atom_types = np.array(structure.atomic_numbers)
        return bool(atom_types.max() < 87)

    def check_2D(self, structure: Structure) -> bool:
        """Return whether all connected components of ``structure`` are 2-dimensional."""
        structure_graph = self.structure2structure_graph(structure)
        structure_components = get_structure_components(structure_graph)
        dim = [component["dimensionality"] for component in structure_components]
        return all(b == 2 for b in dim)

    def check_3D(self, structure: Structure) -> bool:
        """Return whether ``structure`` forms a single connected 3-dimensional network."""
        structure_graph = self.structure2structure_graph(structure)
        structure_components = get_structure_components(structure_graph)
        dim = [component["dimensionality"] for component in structure_components]
        return all(b == 3 for b in dim) and len(structure_components) == 1

    def cif2structure_graph(self, string: str) -> tuple[StructureGraph, Structure]:
        """Parse a CIF string and construct its pymatgen ``StructureGraph``.

        Args:
            string: CIF file contents.

        Returns:
            Tuple of ``(structure_graph, structure)``.
        """
        structure = Structure.from_str(string, "cif")
        return self.structure2structure_graph(structure), structure

    def structure2structure_graph(self, structure: Structure) -> StructureGraph:
        """Convert a pymatgen ``Structure`` into a ``StructureGraph`` via ``self.graph_method``.

        Args:
            structure: Input pymatgen ``Structure``.

        Returns:
            Constructed ``StructureGraph`` instance.
        """
        if self.graph_method == "brunnernn":
            structure_graph = StructureGraph.from_local_env_strategy(
                structure, BrunnerNN_reciprocal()
            )
        elif self.graph_method == "econnn":
            structure_graph = StructureGraph.from_local_env_strategy(
                structure, EconNN()
            )
        elif self.graph_method == "mininn":
            structure_graph = StructureGraph.from_local_env_strategy(
                structure, MinimumDistanceNN()
            )
        elif self.graph_method == "crystalnn":
            structure_graph = StructureGraph.from_local_env_strategy(
                structure, CrystalNN(porous_adjustment=False, weighted_cn=True)
            )
        else:
            print("ERROR - graph_method not implemented")
        return structure_graph

    # === SLICES String Parsing & Serialization ===

    def from_SLICES(
        self,
        SLICES: str,
        strategy: int = 4,
        fix_duplicate_edge: bool = True,
    ) -> None:
        """Parse a SLICES string into ``atom_types``, ``edge_indices``, and ``to_jimages``.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy format (1, 3, or 4). Defaults to 4.
            fix_duplicate_edge: Whether to canonicalize edge orientation and
                deduplicate identical edges. Defaults to ``True``.

        Raises:
            Exception: If element tokens, space-group prefix tokens, atom indices,
                or periodic image labels are malformed.
        """
        self.atom_types = None
        self.edge_indices = None
        self.to_jimages = None
        tokens = SLICES.strip().split(" ")
        if strategy == 3:
            for i in range(len(tokens)):
                if tokens[i].isnumeric():
                    num_atoms = i
                    break
            self.atom_symbols = tokens[:num_atoms]
            num_edges = int((len(tokens) - len(self.atom_symbols)) / 5)
            edge_indices = np.zeros([num_edges, 2], dtype=int)
            to_jimages = np.zeros([num_edges, 3], dtype=int)
            for i in range(num_edges):
                edge = tokens[num_atoms + i * 5 : num_atoms + (i + 1) * 5]
                edge_indices[i, 0] = int(edge[0])
                edge_indices[i, 1] = int(edge[1])
                if edge_indices[i, 0] > num_atoms - 1 or edge_indices[i, 1] > num_atoms - 1:
                    raise Exception("Error: wrong edge indices")
                for j in range(3):
                    if edge[j + 2] == "-":
                        to_jimages[i, j] = -1
                    elif edge[j + 2] == "o":
                        to_jimages[i, j] = 0
                    elif edge[j + 2] == "+":
                        to_jimages[i, j] = 1
                    else:
                        raise Exception("Error: wrong edge label")

        if strategy == 1:
            temp_list = []
            for i in range(len(tokens)):
                if tokens[i].isnumeric():
                    temp_list.append(int(tokens[i]))
            num_atoms = max(temp_list) + 1
            num_edges = int(len(tokens) / 7)
            edge_indices = np.zeros([num_edges, 2], dtype=int)
            to_jimages = np.zeros([num_edges, 3], dtype=int)
            self.atom_symbols = ["NaN"] * num_atoms
            for i in range(num_edges):
                edge = tokens[i * 7 : (i + 1) * 7]
                edge_indices[i, 0] = int(edge[2])
                edge_indices[i, 1] = int(edge[3])
                self.atom_symbols[edge_indices[i, 0]] = edge[0]
                self.atom_symbols[edge_indices[i, 1]] = edge[1]
                if edge_indices[i, 0] > num_atoms - 1 or edge_indices[i, 1] > num_atoms - 1:
                    raise Exception("Error: wrong edge indices")
                for j in range(3):
                    if edge[j + 4] == "-":
                        to_jimages[i, j] = -1
                    elif edge[j + 4] == "o":
                        to_jimages[i, j] = 0
                    elif edge[j + 4] == "+":
                        to_jimages[i, j] = 1
                    else:
                        raise Exception("Error: wrong edge label")
            if "NaN" in self.atom_symbols:
                raise Exception("Error: wrong atom symbols")

        if strategy == 4:
            first_elem_idx = self._first_element_index(tokens)
            if first_elem_idx is None:
                raise Exception("Error: no valid element symbols found")

            if first_elem_idx > 0:
                letter_enc = "".join(tokens[:first_elem_idx])
                try:
                    space_group_num = get_space_group_num_from_letter_enc(letter_enc)
                except Exception as err:
                    space_group_num = None
                    raise Exception("Error: space_group_num = None") from err
            else:
                space_group_num = None
            for i in range(first_elem_idx, len(tokens)):
                if tokens[i].isnumeric():
                    num_atoms = i - first_elem_idx
                    break
            self.space_group_num = space_group_num
            self.atom_symbols = tokens[first_elem_idx : first_elem_idx + num_atoms]
            start_idx = first_elem_idx + len(self.atom_symbols)
            num_edges = int((len(tokens) - start_idx) / 3)
            edge_indices = np.zeros([num_edges, 2], dtype=int)
            to_jimages = np.zeros([num_edges, 3], dtype=int)

            for i in range(num_edges):
                edge = tokens[start_idx + i * 3 : start_idx + (i + 1) * 3]
                edge_indices[i, 0] = int(edge[0])
                edge_indices[i, 1] = int(edge[1])
                if edge_indices[i, 0] > num_atoms - 1 or edge_indices[i, 1] > num_atoms - 1:
                    raise Exception("Error: wrong edge indices")
                for j in range(3):
                    if edge[2][j] == "-":
                        to_jimages[i, j] = -1
                    elif edge[2][j] == "o":
                        to_jimages[i, j] = 0
                    elif edge[2][j] == "+":
                        to_jimages[i, j] = 1
                    else:
                        raise Exception("Error: wrong edge label")

        if fix_duplicate_edge:
            edge_data_ascending = []
            for i in range(len(edge_indices)):
                if edge_indices[i][0] <= edge_indices[i][1]:
                    edge_data_ascending.append([*edge_indices[i], *to_jimages[i]])
                else:
                    edge_data_ascending.append(
                        [edge_indices[i][1], edge_indices[i][0], *(np.array(to_jimages[i]) * -1)]
                    )
            edge_data_ascending_arr = np.array(edge_data_ascending, dtype=int)
            edge_data_ascending_unique = np.unique(edge_data_ascending_arr, axis=0)
            edge_indices = edge_data_ascending_unique[:, :2]
            to_jimages = edge_data_ascending_unique[:, 2:]

        self.edge_indices = edge_indices
        self.to_jimages = to_jimages
        self.atom_types = np.array(
            [
                int(PERIODIC_DATA.loc[PERIODIC_DATA["symbol"] == i].values[0][0])
                for i in self.atom_symbols
            ]
        )

    @staticmethod
    def _first_element_index(tokens: list[str]) -> int | None:
        """Return the index of the first valid chemical element token, or ``None``."""
        for i, token in enumerate(tokens):
            try:
                Element(token)
                return i
            except ValueError:
                continue
        return None

    def get_slices_by_strategy(
        self,
        strategy: int,
        atom_symbols: list[str],
        edge_indices: np.ndarray,
        to_jimages: np.ndarray,
        space_group_num: int | None,
    ) -> str:
        """Serialize graph arrays into a SLICES string using ``strategy`` (1..4)."""
        strategy_method_map = {
            1: self.get_slices1,
            2: self.get_slices2,
            3: self.get_slices3,
            4: self.get_slices4,
        }
        method = strategy_method_map.get(strategy)
        if method:
            return method(atom_symbols, edge_indices, to_jimages, space_group_num)
        raise ValueError(f"Unknown strategy {strategy}")

    @staticmethod
    def get_slices1(
        atom_symbols: list[str],
        edge_indices: np.ndarray,
        to_jimages: np.ndarray,
        space_group_num: int | None = None,
    ) -> str:
        """Serialize graph components using Strategy 1 (interleaved symbols, indices, labels)."""
        SLICES = ""
        for i in range(len(edge_indices)):
            SLICES += (
                atom_symbols[edge_indices[i][0]]
                + " "
                + atom_symbols[edge_indices[i][1]]
                + " "
                + str(edge_indices[i][0])
                + " "
                + str(edge_indices[i][1])
                + " "
            )
            for j in to_jimages[i]:
                if j <= -1:
                    SLICES += "- "
                if j == 0:
                    SLICES += "o "
                if j >= 1:
                    SLICES += "+ "
        return SLICES

    @staticmethod
    def get_slices2(
        atom_symbols: list[str],
        edge_indices: np.ndarray,
        to_jimages: np.ndarray,
        space_group_num: int | None = None,
    ) -> str:
        """Serialize graph components using Strategy 2 (compact fixed-width unspaced encoding)."""
        atom_symbols_mod = [(i + "_")[:2] for i in atom_symbols]
        SLICES = ""
        for i in atom_symbols_mod:
            SLICES += i
        for i in range(len(edge_indices)):
            SLICES += ("0" + str(edge_indices[i][0]))[-2:] + ("0" + str(edge_indices[i][1]))[-2:]
            for j in to_jimages[i]:
                if j <= -1:
                    SLICES += "-"
                if j == 0:
                    SLICES += "o"
                if j >= 1:
                    SLICES += "+"
        return SLICES

    @staticmethod
    def get_slices3(
        atom_symbols: list[str],
        edge_indices: np.ndarray,
        to_jimages: np.ndarray,
        space_group_num: int | None = None,
    ) -> str:
        """Serialize graph components using Strategy 3 (atom header + spaced edge labels)."""
        SLICES = ""
        for i in atom_symbols:
            SLICES += i + " "
        for i in range(len(edge_indices)):
            SLICES += str(edge_indices[i][0]) + " " + str(edge_indices[i][1]) + " "
            for j in to_jimages[i]:
                if j <= -1:
                    SLICES += "- "
                if j == 0:
                    SLICES += "o "
                if j >= 1:
                    SLICES += "+ "
        return SLICES

    @staticmethod
    def get_slices4(
        atom_symbols: list[str],
        edge_indices: np.ndarray,
        to_jimages: np.ndarray,
        space_group_num: int | None,
    ) -> str:
        """Serialize graph components via Strategy 4 (optional space-group token + compact labels).

        Args:
            atom_symbols: List of chemical element symbols in the unit cell.
            edge_indices: Edge endpoint index array ``(N_edges, 2)``.
            to_jimages: Periodic translation label array ``(N_edges, 3)``.
            space_group_num: International space-group number (1..230) or ``None``.

        Returns:
            Encoded Strategy 4 SLICES string.
        """
        SLICES = ""
        if space_group_num is not None:
            tokenized_enc = get_tokenized_enc(space_group_num)
            SLICES = tokenized_enc + " "

        for i in atom_symbols:
            SLICES += i + " "

        for i in range(len(edge_indices)):
            SLICES += str(edge_indices[i][0]) + " " + str(edge_indices[i][1]) + " "
            for j in to_jimages[i]:
                if j <= -1:  # deal with -2, -3, etc. (just in case)
                    SLICES += "-"
                if j == 0:
                    SLICES += "o"
                if j >= 1:  # deal with 2, 3, etc. (just in case)
                    SLICES += "+"
            SLICES += " "
        return SLICES

    def to_SLICES(self, strategy: int = 4) -> str:
        """Serialize currently stored graph attributes into a SLICES string.

        Args:
            strategy: Encoding strategy number (1, 2, 3, or 4). Defaults to 4.

        Returns:
            Encoded SLICES string.
        """
        atom_symbols = [str(ElementBase.from_Z(i)) for i in self.atom_types]
        return self.get_slices_by_strategy(
            strategy, atom_symbols, self.edge_indices, self.to_jimages, self.space_group_num
        )

    # === Syntax Validation, Canonicalization & Formula Extraction ===

    @staticmethod
    def check_structural_validity(str1: Structure) -> bool:
        """Return whether distinct sites in ``str1`` have pairwise distance ``> 0.5`` Angstrom.

        Args:
            str1: Input pymatgen ``Structure``.

        Returns:
            ``True`` if all distinct site pairs exceed ``0.5`` Angstrom, else ``False``.
        """
        distance_matrix = str1.lattice.get_all_distances(str1.frac_coords, str1.frac_coords)
        min_value = 10000000  # inf

        rows, cols = len(distance_matrix), len(distance_matrix[0])
        for i in range(rows):
            for j in range(i + 1, cols):
                min_value = min(min_value, distance_matrix[i][j])
        return bool(min_value > 0.5)

    def check_SLICES(
        self,
        SLICES: str,
        strategy: int = 4,
        dupli_check: bool = False,
        graph_rank_check: bool = True,
    ) -> bool:
        """Validate whether a SLICES string satisfies syntax and 3D quotient-graph constraints.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.
            dupli_check: If ``True``, fail when duplicate edges exist instead of
                deduplicating them during parsing. Defaults to ``False``.
            graph_rank_check: If ``True``, require first homology group rank
                ``H1(X, Z) >= 3`` so Eon's method can construct a 3D embedding.
                Set ``True`` for generative models and ``False`` when 3D
                invertibility is not required. Defaults to ``True``.

        Returns:
            ``True`` if ``SLICES`` passes validation, else ``False``.
        """
        try:
            if dupli_check:
                self.from_SLICES(SLICES, strategy, fix_duplicate_edge=False)
            else:
                self.from_SLICES(SLICES, strategy, fix_duplicate_edge=True)
        except Exception:
            return False
        # Ensure rank of first homology group >= 3 for 3D embedding: rank H1(X,Z) = |E| - |E1|
        G = nx.MultiGraph()
        G.add_nodes_from([i for i in range(len(self.atom_types))])
        G.add_edges_from(self.edge_indices)
        mst = tree.minimum_spanning_edges(G, algorithm="kruskal", data=False)
        b = G.size() - len(list(mst))
        if b < 3 and graph_rank_check:
            return False
        # Check that all nodes are covered by edges
        nodes_covered = []
        for i in self.edge_indices:
            nodes_covered.append(i[0])
            nodes_covered.append(i[1])
        if len(set(nodes_covered)) != len(self.atom_types):
            return False
        # Check that edge labels cover all 3 dimensions across at least 3 edges
        edge_index_covered: list[list[int]] = [[], [], []]
        for i in range(len(self.to_jimages)):
            for j in range(3):
                if self.to_jimages[i][j] != 0:
                    edge_index_covered[j].append(i)
        for i in edge_index_covered:
            if len(i) == 0:
                return False
        # Check duplicates (including flipped orientation)
        if dupli_check:
            edge_data_ascending = []
            for i in range(len(self.edge_indices)):
                if self.edge_indices[i][0] <= self.edge_indices[i][1]:
                    edge_data_ascending.append([*self.edge_indices[i], *self.to_jimages[i]])
                else:
                    edge_data_ascending.append(
                        [
                            self.edge_indices[i][1],
                            self.edge_indices[i][0],
                            *(np.array(self.to_jimages[i]) * -1),
                        ]
                    )

            def remove_duplicate_arrays(arrays: list[list[Any]]) -> list[list[Any]]:
                unique_arrays = []
                for array in arrays:
                    if array not in unique_arrays:
                        unique_arrays.append(array)
                return unique_arrays

            if len(edge_data_ascending) > len(remove_duplicate_arrays(edge_data_ascending)):
                return False
        # Strict dimensional independence check
        if len(edge_index_covered[1]) >= len(edge_index_covered[0]):
            b_sub_a = [i for i in edge_index_covered[1] if i not in edge_index_covered[0]]
        else:
            b_sub_a = [i for i in edge_index_covered[0] if i not in edge_index_covered[1]]
        a_add_b = edge_index_covered[0] + edge_index_covered[1]
        if len(a_add_b) >= len(edge_index_covered[2]):
            c_sub_ab = [i for i in a_add_b if i not in edge_index_covered[2]]
        else:
            c_sub_ab = [i for i in edge_index_covered[2] if i not in a_add_b]
        if len(b_sub_a) == 0 or len(c_sub_ab) == 0:
            return False
        try:
            x_dat, net_voltage = self.convert_graph()
            net = Net(x_dat, dim=3)
            net.voltage = net_voltage
            net.simple_cycle_basis()
            net.get_lattice_basis()
            net.get_cocycle_basis()
        except Exception:
            return False
        return True

    def check_SLICES_basic(self, SLICES: str, strategy: int = 4) -> bool:
        """Perform lightweight syntax and node-coverage validation on a SLICES string.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.

        Returns:
            ``True`` if ``SLICES`` parses cleanly and every atom participates in
            at least one edge, else ``False``.
        """
        try:
            self.from_SLICES(SLICES, strategy)
        except Exception:
            return False
        nodes_covered = []
        for i in self.edge_indices:
            nodes_covered.append(i[0])
            nodes_covered.append(i[1])
        return len(set(nodes_covered)) == len(self.atom_types)

    def get_canonical_SLICES(self, SLICES: str, strategy: int = 4) -> str:
        """Convert a SLICES string into its canonical atom-, edge-, and label-sorted form.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.

        Returns:
            Canonical SLICES string.
        """

        def get_index_list_allow_duplicates(ori: Any, mod: Any) -> list[int]:
            indexes: defaultdict[Any, deque[int]] = defaultdict(deque)
            for i, x in enumerate(mod):
                indexes[x].append(i)
            ids = [indexes[x].popleft() for x in ori]
            return ids

        self.from_SLICES(SLICES, strategy)
        # Sort elements by atomic number
        atom_types_sorted_arr = copy.deepcopy(self.atom_types)
        atom_types_sorted_arr = np.sort(atom_types_sorted_arr)
        atom_types_sorted = list(atom_types_sorted_arr)
        index_mapping = get_index_list_allow_duplicates(self.atom_types, atom_types_sorted)
        edge_indices = copy.deepcopy(self.edge_indices)
        space_group_num = self.space_group_num
        for j in range(len(self.edge_indices)):
            edge_indices[j][0] = index_mapping[edge_indices[j][0]]
            edge_indices[j][1] = index_mapping[edge_indices[j][1]]
        # Sort edges to facilitate consistent edge-label ordering
        edge_indices_asc = copy.deepcopy(edge_indices)
        to_jimages_asc = copy.deepcopy(self.to_jimages)
        for i in range(len(edge_indices)):
            if edge_indices[i][0] > edge_indices[i][1]:
                edge_indices_asc[i][0] = edge_indices[i][1]
                edge_indices_asc[i][1] = edge_indices[i][0]
                to_jimages_asc[i] = self.to_jimages[i] * -1
        atom_symbols = [str(ElementBase.from_Z(i)) for i in atom_types_sorted]
        c = np.concatenate((edge_indices_asc, to_jimages_asc), axis=1)
        sorted_data = np.array(sorted(c, key=lambda x: (x[0], x[1])))
        edge_indices = sorted_data[:, :2]
        to_jimages = sorted_data[:, 2:]
        # Sort periodic boundary condition columns
        column_sums = np.sum(to_jimages, axis=0)

        def custom_sort_rule(column: np.ndarray) -> list[Any]:  # sum(x * index_x**3)
            weighted_sum = []
            for i in range(3):
                temp = 0
                for j in range(len(column)):
                    temp += (j + 1) ** 3 * column[j, i]
                weighted_sum.append(temp)
            return weighted_sum

        sorted_column_indices = np.lexsort((custom_sort_rule(to_jimages), column_sums))
        to_jimages_column_sorted = to_jimages[:, sorted_column_indices]
        # Sort edges and periodic labels lexicographically
        c = np.concatenate((edge_indices, to_jimages_column_sorted), axis=1)
        sorted_data = np.array(sorted(c, key=lambda x: (x[0], x[1], x[2], x[3], x[4])))
        edge_indices = sorted_data[:, :2]
        to_jimages = sorted_data[:, 2:]
        return self.get_slices_by_strategy(
            strategy, atom_symbols, edge_indices, to_jimages, space_group_num
        )

    def SLICES2formula(self, SLICES: str) -> str | None:
        """Extract the compact chemical formula from a Strategy 3 or Strategy 4 SLICES string.

        Args:
            SLICES: Input SLICES string containing an atom-symbol header followed
                by numeric edge indices.

        Returns:
            Unspaced formula string (e.g., ``'Nd2Si2Ru2'``), or ``None`` if
            composition parsing fails.
        """
        tokens = SLICES.split()
        first_elem_idx = self._first_element_index(tokens)
        if first_elem_idx:  # skip the space-group tokens of Strategy 4
            SLICES = " ".join(tokens[first_elem_idx:])
        match = re.search(r"^(.*?)(\d+)", SLICES)
        extracted_string = match.group(1)  # type: ignore[union-attr]
        try:
            composition = Composition(extracted_string)
            formula = composition.formula.replace(" ", "")
            return formula
        except Exception:
            print(SLICES, extracted_string)
            return None

    # === Primitive-Cell Encoding & Data Augmentation ===

    @staticmethod
    def to_primitive_if_smaller(structure: Structure) -> Structure:
        """Return the primitive standard cell if it has fewer atoms, otherwise ``structure``.

        Falls back to the input structure if symmetry conversion fails or changes
        the reduced chemical formula.

        Args:
            structure: Input pymatgen ``Structure``.

        Returns:
            Primitive cell when strictly smaller with identical reduced formula,
            otherwise ``structure``.
        """
        try:
            primitive = SpacegroupAnalyzer(structure).get_primitive_standard_structure()
            if len(primitive) < len(structure):
                if primitive.composition.reduced_formula == structure.composition.reduced_formula:
                    return primitive
                print("Warning: primitive cell changed the formula, using the input cell.")
        except Exception as e:
            print(f"Warning: primitive cell conversion failed, using the input cell: {e}")
        return structure

    def _run_with_primitive_fallback(
        self,
        structure: Structure,
        encode: Callable[[Structure], Any],
    ) -> Any:
        """Run ``encode`` on the reduced primitive cell, retrying on ``structure`` if needed.

        Args:
            structure: Input pymatgen ``Structure``.
            encode: Callable accepting a ``Structure`` and returning its graph
                representation.

        Returns:
            Result returned by ``encode``.
        """
        primitive = self.to_primitive_if_smaller(structure)
        if primitive is not structure:
            try:
                return encode(primitive)
            except (ValueError, RuntimeError, ArithmeticError, LookupError) as e:
                print(f"Warning: encoding the primitive cell failed, using the input cell: {e}")
        return encode(structure)

    def structure2SLICES(self, structure: Structure, strategy: int = 4) -> str:
        """Encode a pymatgen ``Structure`` into a SLICES string.

        The structure is first reduced to its primitive standard cell if doing so
        decreases the atom count.

        Args:
            structure: Input pymatgen ``Structure``.
            strategy: Encoding strategy number (1, 2, 3, or 4). Defaults to 4.

        Returns:
            Encoded SLICES string.
        """
        atom_types, edge_indices, to_jimages, space_group_num = self.structure2crystal_graph_rep(
            structure
        )
        atom_symbols = [str(ElementBase.from_Z(i)) for i in atom_types]
        return self.get_slices_by_strategy(
            strategy, atom_symbols, edge_indices, to_jimages, space_group_num
        )

    def structure2randomSLICES(
        self,
        structure: Structure,
        strategy: int = 4,
        num: int = 50,
        shuffle_atom_order: bool = True,
        shuffle_bond_order: bool = True,
        flip_bonds: bool = True,
        batch_multiplier: int = 10,
    ) -> list[str]:
        """Convert a ``Structure`` into deduplicated randomly augmented SLICES strings.

        Includes the original SLICES string alongside randomly permuted variants
        (atom-order permutation, edge-order shuffling, and edge-direction flips).
        If the primitive standard cell has fewer atoms, ``structure`` is reduced
        to its primitive cell first.

        Args:
            structure: Input pymatgen ``Structure``.
            strategy: Encoding strategy number (1, 2, 3, or 4). Defaults to 4.
            num: Target number of unique SLICES strings to return. Defaults to 50.
            shuffle_atom_order: Whether to randomly permute atom indices.
                Defaults to ``True``.
            shuffle_bond_order: Whether to randomly permute edge order.
                Defaults to ``True``.
            flip_bonds: Whether to randomly invert edge directions and periodic
                image signs. Defaults to ``True``.
            batch_multiplier: Candidate-generation multiplier ``(num * batch_multiplier)``
                used to sample unique permutations. Defaults to 10.

        Returns:
            List of up to ``num`` unique SLICES strings. Note that exact list
            ordering across separate Python processes depends on ``PYTHONHASHSEED``
            as well as ``random.seed``.
        """
        # Extract crystal graph representation
        crystal_graph_rep = self.structure2crystal_graph_rep(structure)
        atom_types = crystal_graph_rep[0]
        atom_symbols = [str(Element.from_Z(i)) for i in atom_types]
        edge_indices = crystal_graph_rep[1]
        to_jimages = crystal_graph_rep[2]
        space_group_num = crystal_graph_rep[3]
        # Track SLICES strings in a set to guarantee uniqueness
        SLICES_set = set()

        # Generate and include the unpermuted SLICES string
        try:
            original_SLICES = self.get_slices_by_strategy(
                strategy,
                atom_symbols,
                edge_indices,
                to_jimages,
                space_group_num,
            )
            SLICES_set.add(original_SLICES)
        except Exception as e:
            print(f"Error generating original SLICES: {e}")

        # Total candidate permutations to attempt
        total_permutations = num * batch_multiplier

        for _ in range(total_permutations):
            # Create mutable copies for this permutation
            atom_symbols_aug = copy.deepcopy(atom_symbols)
            edge_indices_aug = copy.deepcopy(edge_indices)
            to_jimages_aug = copy.deepcopy(to_jimages)

            # Randomly permute atom order if enabled
            if shuffle_atom_order:
                num_atoms = len(atom_symbols_aug)
                shuffled_indices = random.sample(range(num_atoms), num_atoms)
                atom_symbols_aug = [atom_symbols_aug[i] for i in shuffled_indices]
                # Map original atom positions to permuted positions allowing duplicate species
                index_mapping = self.get_index_list_allow_duplicates(
                    [str(Element.from_Z(i)) for i in atom_types],
                    atom_symbols_aug,
                )
                # Remap edge endpoint atom indices
                edge_indices_aug = np.array(
                    [[index_mapping[edge[0]], index_mapping[edge[1]]] for edge in edge_indices_aug]
                )

            # Randomly shuffle edge order if enabled
            if shuffle_bond_order:
                bond_order = list(zip(edge_indices_aug, to_jimages_aug, strict=False))
                random.shuffle(bond_order)
                if bond_order:
                    edge_indices_tup, to_jimages_tup = zip(*bond_order, strict=False)
                    edge_indices_aug = np.array(edge_indices_tup)
                    to_jimages_aug = np.array(to_jimages_tup)
                else:
                    edge_indices_aug, to_jimages_aug = ([], [])  # type: ignore[assignment]

            # Randomly flip edge directions if enabled
            if flip_bonds:
                for i in range(len(edge_indices_aug)):
                    if random.choice([True, False]):
                        # Swap endpoint indices and negate periodic image translation
                        edge_indices_aug[i] = edge_indices_aug[i][::-1]
                        to_jimages_aug[i] = -to_jimages_aug[i]

            # Validate atomic symbols
            atom_types_aug = []
            invalid_symbols = []
            for symbol in atom_symbols_aug:
                try:
                    element = Element(symbol)
                    atom_types_aug.append(element.Z)
                except Exception:
                    invalid_symbols.append(symbol)

            if invalid_symbols:
                print(f"Warning: Could not find atomic numbers for symbols: {invalid_symbols}")
                continue

            atom_types_aug = np.array(atom_types_aug)  # type: ignore[assignment]

            # Serialize augmented SLICES string
            try:
                SLICES_aug = self.get_slices_by_strategy(
                    strategy,
                    atom_symbols_aug,
                    edge_indices_aug,
                    to_jimages_aug,
                    space_group_num,
                )
            except Exception as e:
                print(f"Error generating SLICES: {e}")
                continue

            SLICES_set.add(SLICES_aug)

            if len(SLICES_set) >= num:
                break

        if len(SLICES_set) < num:
            print(
                f"Warning: Only generated {len(SLICES_set)} unique augmented SLICES strings "
                f"(target: {num}); insufficient unique permutations available."
            )

        SLICES_list = list(SLICES_set)
        random.shuffle(SLICES_list)
        return SLICES_list[:num]

    def structure2SLICESAug_atom_order(
        self,
        structure: Structure,
        strategy: int = 4,
        num: int = 50,
    ) -> list[str]:
        """Generate augmented SLICES strings by randomly permuting atom order only.

        Args:
            structure: Input pymatgen ``Structure`` to encode and augment.
            strategy: Encoding strategy number (1, 2, 3, or 4). Defaults to 4.
            num: Target number of unique SLICES strings to generate. Defaults to 50.

        Returns:
            List of up to ``num`` unique SLICES strings sharing identical bond
            ordering and periodic orientations up to atom-index permutation.
        """
        return self.structure2randomSLICES(
            structure=structure,
            strategy=strategy,
            num=num,
            shuffle_atom_order=True,
            shuffle_bond_order=False,
            flip_bonds=False,
        )

    def get_dim(self, structure: Structure) -> int:
        """Determine the Larsen structural dimensionality of ``structure``.

        Args:
            structure: Input pymatgen ``Structure``.

        Returns:
            Integer dimensionality (0, 1, 2, or 3).
        """
        if self.graph_method == "brunnernn":
            bonded_structure = BrunnerNN_reciprocal().get_bonded_structure(structure)
        elif self.graph_method == "econnn":
            bonded_structure = EconNN().get_bonded_structure(structure)
        elif self.graph_method == "mininn":
            bonded_structure = MinimumDistanceNN().get_bonded_structure(structure)
        elif self.graph_method == "crystalnn":
            bonded_structure = CrystalNN(
                porous_adjustment=False, weighted_cn=True
            ).get_bonded_structure(structure)
        else:
            print("ERROR - graph_method not implemented")
        dim = get_dimensionality_larsen(bonded_structure)
        return int(dim)

    def from_cif(self, string: str) -> None:
        """Populate graph attributes directly from a CIF string.

        Reduces the structure to its primitive standard cell first if that lowers
        the number of atoms.

        Args:
            string: CIF file contents.
        """
        structure_graph, structure = self._run_with_primitive_fallback(
            Structure.from_str(string, "cif"),
            lambda s: (self.structure2structure_graph(s), s),
        )
        if self.check_results:
            structure_graph.draw_graph_to_file("sg.png", hide_image_edges=False, node_labels=True)
        self.atom_types = np.array(structure.atomic_numbers)
        try:
            self.space_group_num = SpacegroupAnalyzer(structure).get_space_group_number()
        except Exception:
            self.space_group_num = None
        edge_indices, to_jimages = [], []
        for i, j, to_jimage in structure_graph.graph.edges(data="to_jimage"):
            edge_indices.append([i, j])
            to_jimages.append(to_jimage)
        self.edge_indices = np.array(edge_indices)
        self.to_jimages = np.array(to_jimages)

    def structure2crystal_graph_rep(
        self,
        structure: Structure,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, int | None]:
        """Convert a ``Structure`` into ``(atom_types, edge_indices, to_jimages, space_group_num)``.

        Reduces ``structure`` to its primitive standard cell first if doing so
        decreases the atom count, so returned atom indices correspond to the
        reduced cell when applicable.

        Args:
            structure: Input pymatgen ``Structure``.

        Returns:
            Tuple ``(atom_types, edge_indices, to_jimages, space_group_number)``.
        """
        return self._run_with_primitive_fallback(structure, self._crystal_graph_rep)

    def _crystal_graph_rep(
        self,
        structure: Structure,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, int | None]:
        """Construct crystal graph arrays directly on ``structure`` without cell reduction."""
        structure_graph = self.structure2structure_graph(structure)
        if self.check_results:
            structure_graph.draw_graph_to_file("graph.png", hide_image_edges=False)

        try:
            analyzer = SpacegroupAnalyzer(structure)
            space_group_number = analyzer.get_space_group_number()
        except Exception:
            space_group_number = None

        atom_types = np.array(structure.atomic_numbers)
        edge_indices, to_jimages = [], []
        for i, j, to_jimage in structure_graph.graph.edges(data="to_jimage"):
            edge_indices.append([i, j])
            to_jimages.append(to_jimage)

        return atom_types, np.array(edge_indices), np.array(to_jimages), space_group_number

    # === GFN-FF Supercell Neighbor List & Inner-Product Targets ===

    def get_nbf_blist(self) -> tuple[str, np.ndarray]:
        """Build the 3x3x3 supercell NBF neighbor table and central-cell bond list.

        Returns:
            Tuple ``(nbf, blist)`` where ``nbf`` is the ``testBonds_cut.top``
            20-row neighbor table string for ``run_gfnff_helper`` and ``blist``
            is the ``(N_edges, 2)`` array of 1-based central-cell atom indices.
        """
        if (
            self.atom_types is not None
            and self.edge_indices is not None
            and self.to_jimages is not None
        ):
            n_atom = len(self.atom_types)
            voltage = np.concatenate((self.edge_indices, self.to_jimages), axis=1)
            voltage_super = []
            for i in range(len(OFFSET)):
                for j in range(len(voltage)):
                    temp = []
                    temp.append(voltage[j, 0] + i * n_atom)
                    voltage_sum = voltage[j, 2:] + OFFSET[i, :]
                    voltage_sum_new = voltage_sum.copy()
                    for k in range(len(voltage_sum)):
                        if voltage_sum[k] == 2:
                            voltage_sum_new[k] = 1
                        elif voltage_sum[k] == -2:
                            voltage_sum_new[k] = -1
                        else:
                            voltage_sum_new[k] = 0
                    target_block = voltage_sum.copy()
                    for k in range(len(voltage_sum)):
                        if voltage_sum[k] == 2:
                            target_block[k] = voltage_sum[k] - 3
                        elif voltage_sum[k] == -2:
                            target_block[k] = voltage_sum[k] + 3
                    target_block = np.array(target_block)
                    for k in range(len(OFFSET)):
                        if np.array_equal(target_block, OFFSET[k]):
                            target_index = k
                    temp.append(voltage[j, 1] + target_index * n_atom)
                    temp.append(voltage_sum_new[0])
                    temp.append(voltage_sum_new[1])
                    temp.append(voltage_sum_new[2])
                    voltage_super.append(temp)
            voltage_super_arr = np.array(voltage_super, dtype=int)
            # Filter out supercell boundary wrap-around edges
            voltage_super_cut_list = []
            for i in range(len(voltage_super_arr)):
                if (
                    voltage_super_arr[i, 2] == 0
                    and voltage_super_arr[i, 3] == 0
                    and voltage_super_arr[i, 4] == 0
                ):
                    temp = []
                    temp.append(voltage_super_arr[i, 0])
                    temp.append(voltage_super_arr[i, 1])
                    voltage_super_cut_list.append(temp)
            voltage_super_cut = np.array(voltage_super_cut_list, dtype=int)
            # Reindex after removing isolated supercell atoms with zero neighbors
            no_neighbor_index = []
            for i in range(n_atom * 27):
                row, _column = np.where(voltage_super_cut == i)
                total = len(row)
                if total == 0:
                    no_neighbor_index.append(i)
            atom_symbol_list_super = []
            atom_symbols = [str(ElementBase.from_Z(i)) for i in self.atom_types]
            for _ in range(len(OFFSET)):
                for j in range(n_atom):
                    atom_symbol_list_super.append(atom_symbols[j])
            if 1:  # remove atoms with no neighbors
                for i in range(len(voltage_super_cut)):
                    voltage_super_cut[i, 0] = voltage_super_cut[i, 0] - len(
                        np.where(no_neighbor_index < voltage_super_cut[i, 0])[0]
                    )
                    voltage_super_cut[i, 1] = voltage_super_cut[i, 1] - len(
                        np.where(no_neighbor_index < voltage_super_cut[i, 1])[0]
                    )
                for i in range(len(voltage_super_arr)):
                    voltage_super_arr[i, 0] = voltage_super_arr[i, 0] - len(
                        np.where(no_neighbor_index < voltage_super_arr[i, 0])[0]
                    )
                    voltage_super_arr[i, 1] = voltage_super_arr[i, 1] - len(
                        np.where(no_neighbor_index < voltage_super_arr[i, 1])[0]
                    )
                no_neighbor_index.reverse()
                for i in no_neighbor_index:
                    del atom_symbol_list_super[i]
            else:
                no_neighbor_index = []
            # Populate 19-slot NBF neighbor list (row 19 stores listed neighbor count <= 19)
            neighbor_list = np.zeros((20, n_atom * 27 - len(no_neighbor_index)))
            for i in range(n_atom * 27 - len(no_neighbor_index)):
                row, column = np.where(voltage_super_cut == i)
                total = len(row)
                if total > 19:
                    row = row[:19]
                    column = column[:19]
                for j in range(len(row)):
                    neighbor_list[j, i] = voltage_super_cut[row[j], 1 - column[j]] + 1
                neighbor_list[19, i] = len(row)

            nbf = (
                str(n_atom * 27 - len(no_neighbor_index))
                + "\n"
                + " ".join(atom_symbol_list_super)
                + "\n"
            )
            for i in range(20):
                nbf = nbf + " ".join([str(int(x)) for x in neighbor_list[i, :].tolist()]) + "\n"
            blist = voltage_super_arr[len(voltage) * 13 : len(voltage) * 14, :2] + 1
        else:
            print("ERROR - crystalgraph is not defined")
        if self.check_results:
            with open("testBonds_cut.top", "w") as f:
                f.write(nbf)
            bdict = {"blist": blist.tolist()}
            with open("blist.json", "w") as f:
                json.dump(bdict, f)
        return nbf, blist

    def get_inner_p_target_debug(
        self,
        bond_scaling: float = 1.05,
    ) -> tuple[np.ndarray, list[list[int]], list[float]]:
        """Compute GFN-FF inner-product target matrix, colattice indices, and weights (debug).

        Args:
            bond_scaling: Empirical bond-length scaling factor. Defaults to ``1.05``.

        Returns:
            Tuple ``(inner_p_target, colattice_inds, colattice_weights)``.
        """
        nbf, blist = self.get_nbf_blist()
        data = run_gfnff_helper(nbf)
        if self.check_results:
            write_debug_files(nbf, data)
        blist_original = blist
        blist_flip = np.flip(blist_original, 1)
        bond_weight: list[float] = []
        blist_super = np.array(data["blist"], dtype=int)
        inner_p_target = np.zeros((len(blist_original), len(blist_original)))
        for i in range(len(blist_original)):
            temp1 = np.where((blist_super == blist_original[i]).all(axis=1))
            temp2 = np.where((blist_super == blist_flip[i]).all(axis=1))
            if len(temp1[0]):
                index = temp1[0][0]
            elif len(temp2[0]):
                index = temp2[0][0]
            else:
                print("Cannot find bond!!!")
                continue
            if np.isnan(data["vbond"][index][2]):
                bond_weight.append(1)
                data["vbond"][index][2] = 1
            else:
                bond_weight.append(abs(data["vbond"][index][2]))
            inner_p_target[i, i] = round(
                (data["vbond"][index][3] * 0.529177 * 1.05 * bond_scaling) ** 2, 5
            )
        alist_original = np.array(data["alist"], dtype=int)
        colattice_inds: list[list[int]] = [[], []]
        colattice_weights: list[float] = []
        for i in range(len(alist_original)):
            ab = alist_original[i][[0, 1]]
            ac = alist_original[i][[0, 2]]
            temp1 = np.where((blist_original == ab).all(axis=1))
            temp2 = np.where((blist_flip == ab).all(axis=1))
            temp3 = np.where((blist_original == ac).all(axis=1))
            temp4 = np.where((blist_flip == ac).all(axis=1))
            if (len(temp1[0]) + len(temp2[0])) and (len(temp3[0]) + len(temp4[0])):
                sign = 1
                if len(temp1[0]):
                    index_x = temp1[0][0]
                elif len(temp2[0]):
                    index_x = temp2[0][0]
                    sign = sign * (-1)
                else:
                    print("Cannot find bond1!!!")
                if len(temp3[0]):
                    index_y = temp3[0][0]
                elif len(temp4[0]):
                    index_y = temp4[0][0]
                    sign = sign * (-1)
                else:
                    print("Cannot find bond2!!!")
                inner_p_target[index_x, index_y] = (
                    sign
                    * math.sqrt(inner_p_target[index_x, index_x])
                    * math.sqrt(inner_p_target[index_y, index_y])
                    * math.cos(data["vangl"][i][0])
                )
                colattice_inds[0].append(int(index_x))
                colattice_inds[1].append(int(index_y))
                colattice_weights.append(abs(data["vangl"][i][1]))
        # Normalize angle weights first, then bond weights
        temp_max: float = 0
        for i in range(len(colattice_weights)):
            temp_max = max(temp_max, colattice_weights[i])
        for i in range(len(colattice_weights)):
            colattice_weights[i] = round(colattice_weights[i] / temp_max, 2)
        temp_max = 0
        for i in range(len(bond_weight)):
            temp_max = max(temp_max, bond_weight[i])
        for i in range(len(bond_weight)):
            colattice_inds[0].append(i)
            colattice_inds[1].append(i)
            colattice_weights.append(round(bond_weight[i] / temp_max, 2))
        if self.check_results:
            inner_p_target_dict = {
                "inner_p_target": inner_p_target.tolist(),
                "colattice_inds": colattice_inds,
                "colattice_weights": colattice_weights,
            }
            with open("inner_p_target.json", "w") as f:
                json.dump(inner_p_target_dict, f)
        return inner_p_target, colattice_inds, colattice_weights

    def get_inner_p_target(
        self,
        bond_scaling: float = 1.05,
    ) -> tuple[np.ndarray, list[list[int]], list[float]] | None:
        """Compute GFN-FF inner-product target matrix, colattice indices, and weights.

        Args:
            bond_scaling: Empirical bond-length scaling factor. Defaults to ``1.05``.

        Returns:
            Tuple ``(inner_p_target, colattice_inds, colattice_weights)``, or
            ``None`` if topology target generation raises an exception.
        """
        nbf, blist = self.get_nbf_blist()
        try:
            data = run_gfnff_helper(nbf)
            if self.check_results:
                write_debug_files(nbf, data)
            blist_original = blist
            blist_flip = np.flip(blist_original, 1)
            bond_weight: list[float] = []
            blist_super = np.array(data["blist"], dtype=int)
            inner_p_target = np.zeros((len(blist_original), len(blist_original)))
            for i in range(len(blist_original)):
                temp1 = np.where((blist_super == blist_original[i]).all(axis=1))
                temp2 = np.where((blist_super == blist_flip[i]).all(axis=1))
                if len(temp1[0]):
                    index = temp1[0][0]
                elif len(temp2[0]):
                    index = temp2[0][0]
                else:
                    print("Cannot find bond!!!")
                    continue
                if np.isnan(data["vbond"][index][2]):
                    bond_weight.append(1)
                    data["vbond"][index][2] = 1
                else:
                    bond_weight.append(abs(data["vbond"][index][2]))
                inner_p_target[i, i] = round(
                    (data["vbond"][index][3] * 0.529177 * 1.05 * bond_scaling) ** 2, 5
                )
            alist_original = np.array(data["alist"], dtype=int)
            colattice_inds: list[list[int]] = [[], []]
            colattice_weights: list[float] = []
            for i in range(len(alist_original)):
                ab = alist_original[i][[0, 1]]
                ac = alist_original[i][[0, 2]]
                temp1 = np.where((blist_original == ab).all(axis=1))
                temp2 = np.where((blist_flip == ab).all(axis=1))
                temp3 = np.where((blist_original == ac).all(axis=1))
                temp4 = np.where((blist_flip == ac).all(axis=1))
                if (len(temp1[0]) + len(temp2[0])) and (len(temp3[0]) + len(temp4[0])):
                    sign = 1
                    if len(temp1[0]):
                        index_x = temp1[0][0]
                    elif len(temp2[0]):
                        index_x = temp2[0][0]
                        sign = sign * (-1)
                    else:
                        print("Cannot find bond1!!!")
                    if len(temp3[0]):
                        index_y = temp3[0][0]
                    elif len(temp4[0]):
                        index_y = temp4[0][0]
                        sign = sign * (-1)
                    else:
                        print("Cannot find bond2!!!")
                    inner_p_target[index_x, index_y] = (
                        sign
                        * math.sqrt(inner_p_target[index_x, index_x])
                        * math.sqrt(inner_p_target[index_y, index_y])
                        * math.cos(data["vangl"][i][0])
                    )
                    colattice_inds[0].append(int(index_x))
                    colattice_inds[1].append(int(index_y))
                    colattice_weights.append(abs(data["vangl"][i][1]))
            # Normalize angle weights first, then bond weights
            temp_max: float = 0
            for i in range(len(colattice_weights)):
                temp_max = max(temp_max, colattice_weights[i])
            for i in range(len(colattice_weights)):
                colattice_weights[i] = round(colattice_weights[i] / temp_max, 2)
            temp_max = 0
            for i in range(len(bond_weight)):
                temp_max = max(temp_max, bond_weight[i])
            for i in range(len(bond_weight)):
                colattice_inds[0].append(i)
                colattice_inds[1].append(i)
                colattice_weights.append(round(bond_weight[i] / temp_max, 2))
            if self.check_results:
                inner_p_target_dict = {
                    "inner_p_target": inner_p_target.tolist(),
                    "colattice_inds": colattice_inds,
                    "colattice_weights": colattice_weights,
                }
                with open("inner_p_target.json", "w") as f:
                    json.dump(inner_p_target_dict, f)
            return inner_p_target, colattice_inds, colattice_weights
        except Exception as e:
            print(e)
            return None

    # === Net Conversion, Lennard-Jones Parameters & Rescaling ===

    def convert_graph(self) -> tuple[list[tuple[str, str, dict[str, str]]], np.ndarray]:
        """Convert ``self.edge_indices`` and ``self.to_jimages`` into ``Net`` input format.

        Returns:
            Tuple ``(x_dat, net_voltage)`` for :class:`slices.tobascco_net.Net`.
        """
        edges = list(np.concatenate((self.edge_indices, self.to_jimages), axis=1))
        x_dat, net_voltage = [], []
        for edge_id, (v1, v2, e1, e2, e3) in enumerate(edges):
            ename = f"e{edge_id + 1}"
            net_voltage.append((e1, e2, e3))
            x_dat.append((str(v1 + 1), str(v2 + 1), {"label": ename}))
        net_voltage_arr = np.array(net_voltage)
        return x_dat, net_voltage_arr

    @staticmethod
    def get_uncovered_pair(graph: nx.Graph) -> list[list[Any]]:
        """Return 0-based atom-index pairs not directly connected by an edge in ``graph``.

        Args:
            graph: NetworkX graph with 1-based string vertex labels.

        Returns:
            List of ``[i, j]`` upper-triangular atom-index pairs without edges.
        """
        num_nodes = len(graph.nodes)
        covered_pair = []
        for i in graph.edges:
            covered_pair.append(i[0] + "," + i[1])
        unique_covered_pair = list(dict.fromkeys(covered_pair))
        unique_covered_pair_int = []
        for i in unique_covered_pair:
            unique_covered_pair_int.append([int(i.split(",")[0]) - 1, int(i.split(",")[1]) - 1])
        uncovered_pair = []
        index_i, index_j = np.triu_indices(num_nodes)
        triu_pair = []
        for i in range(len(index_i)):
            if index_i[i] != index_j[i]:
                triu_pair.append([index_i[i], index_j[i]])
        for i in triu_pair:
            if i not in unique_covered_pair_int:
                uncovered_pair.append(i)
        return uncovered_pair

    def get_uncovered_pair_lj(self, uncovered_pair: list[list[Any]]) -> list[list[float]]:
        """Return Lennard-Jones ``[cutoff, sigma]`` parameters for non-bonded atom pairs.

        Args:
            uncovered_pair: Non-bonded ``[i, j]`` atom-index pairs.

        Returns:
            List of ``[r_cut, sigma]`` parameter pairs corresponding to ``uncovered_pair``.
        """
        uncovered_pair_lj = []
        lj_param = {}
        for i in LJ_PARAMS_LIST:
            lj_param[i[0]] = [i[1], i[2]]
        for i in uncovered_pair:
            if i[0] == i[1]:
                uncovered_pair_lj.append(lj_param[self.atom_types[i[0]]])
            else:
                uncovered_pair_lj.append(
                    [
                        lj_param[self.atom_types[i[0]]][0] / 2
                        + lj_param[self.atom_types[i[0]]][0] / 2,
                        lj_param[self.atom_types[i[0]]][1] / 2
                        + lj_param[self.atom_types[i[0]]][1] / 2,
                    ]
                )
        return uncovered_pair_lj

    def get_covered_pair_lj(self) -> list[list[float]]:
        """Return Lennard-Jones ``[cutoff, sigma]`` parameters for bonded atom pairs."""
        covered_pair_lj = []
        lj_param = {}
        for i in LJ_PARAMS_LIST:
            lj_param[i[0]] = [i[1], i[2]]
        for i in self.edge_indices:
            if i[0] == i[1]:
                covered_pair_lj.append(lj_param[self.atom_types[i[0]]])
            else:
                covered_pair_lj.append(
                    [
                        lj_param[self.atom_types[i[0]]][0] / 2
                        + lj_param[self.atom_types[i[0]]][0] / 2,
                        lj_param[self.atom_types[i[0]]][1] / 2
                        + lj_param[self.atom_types[i[0]]][1] / 2,
                    ]
                )
        return covered_pair_lj

    def get_rescaled_lattice_vectors(
        self,
        inner_p_target: np.ndarray,
        inner_p_std: np.ndarray,
        lattice_vectors_std: np.ndarray,
        arc_coord_std: np.ndarray,
    ) -> np.ndarray:
        """Anisotropically rescale barycentric lattice vectors using GFN-FF bond lengths.

        Args:
            inner_p_target: Target inner-product matrix from GFN-FF.
            inner_p_std: Inner-product matrix of the standard barycentric placement.
            lattice_vectors_std: Cholesky lattice vectors of the barycentric metric tensor.
            arc_coord_std: Fractional edge vectors of the barycentric placement.

        Returns:
            Rescaled ``(3, 3)`` lattice vector matrix.
        """
        scaleList = []
        inner_p_std_diag = np.diag(inner_p_std)
        nonzero_edge_index = np.where(inner_p_std_diag > 0.0001)[0].tolist()
        if len(nonzero_edge_index) < len(inner_p_std_diag):
            self.unstable_graph = True
        else:
            self.unstable_graph = False
        scale_sum_temp = 0.0
        for i in range(len(self.edge_indices)):
            if i in nonzero_edge_index:
                scaleList.append(inner_p_target[i, i] ** (0.5) / inner_p_std[i, i] ** (0.5))
                scale_sum_temp += inner_p_target[i, i] ** (0.5) / inner_p_std[i, i] ** (0.5)
            else:
                scaleList.append(0)
        scale_ave_temp = scale_sum_temp / len(nonzero_edge_index)
        for i in range(len(self.edge_indices)):
            if i not in nonzero_edge_index:
                scaleList[i] = scale_ave_temp
        weight_sum: Any = [0, 0, 0]
        scale_sum: Any = [0, 0, 0]
        for i in range(len(arc_coord_std)):
            weight_sum += abs(arc_coord_std[i])
            scale_sum += abs(arc_coord_std[i]) * scaleList[i]
        scale_vector = [0.0, 0.0, 0.0]
        for i in range(len(scale_sum)):
            scale_vector[i] = scale_sum[i] / weight_sum[i]
        lattice_vectors_scaled = np.dot(lattice_vectors_std, np.diag(scale_vector))
        return lattice_vectors_scaled

    @staticmethod
    def get_coordinates(
        arc_coord: np.ndarray,
        num_nodes: int,
        shortest_path_spanning_graph: dict[str, list[str]],
        spanning: list[Any],
    ) -> np.ndarray:
        """Compute fractional vertex coordinates by integrating edge vectors along a spanning tree.

        Args:
            arc_coord: Fractional edge-vector coordinates ``(N_edges, 3)``.
            num_nodes: Number of vertices in the quotient graph.
            shortest_path_spanning_graph: Shortest paths from root vertex ``'1'``.
            spanning: Directed edges belonging to the minimum spanning tree.

        Returns:
            Fractional atomic coordinates ``(num_nodes, 3)``.
        """
        coordinates = np.zeros((num_nodes, 3))
        if num_nodes > 1:
            for i in range(num_nodes)[1:]:
                for h in range(len(shortest_path_spanning_graph[str(i + 1)][1:])):
                    for j in spanning:
                        if set(shortest_path_spanning_graph[str(i + 1)][h : h + 2]) == set(j[:2]):
                            if int(shortest_path_spanning_graph[str(i + 1)][h]) == int(j[0]):
                                coordinates[i, :] = (
                                    coordinates[i, :] + arc_coord[int(j[2][1:]) - 1]
                                )
                            else:
                                coordinates[i, :] = (
                                    coordinates[i, :] - arc_coord[int(j[2][1:]) - 1]
                                )
        else:
            coordinates[0, :] = [0, 0, 0]
        return coordinates

    # === ZL* Lattice/Cocycle Optimization & Space-Group Recovery ===

    @staticmethod
    def convert_params(
        x: np.ndarray,
        ndim: int,
        cocycle_size: int,
        lattice_type: int,
        metric_tensor_std: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray | None]:
        """Unpack ZL* optimization vector ``x`` into ``(metric_tensor, cocycle_rep)``.

        Args:
            x: Flattened vector of independent metric-tensor diagonals and cocycle
                coordinates.
            ndim: Spatial dimensionality (3).
            cocycle_size: Number of cocycle basis rows ``(order - 1)``.
            lattice_type: Symmetry constraint code (``1``: ``a=b=c``;
                ``21``: ``a!=b=c``; ``22``: ``b!=a=c``; ``23``: ``c!=a=b``;
                ``3``: ``a!=b!=c``).
            metric_tensor_std: Rescaled standard metric tensor fixing inter-axial
                angles.

        Returns:
            Tuple ``(metric_tensor, cocycle_rep)``.
        """
        if lattice_type == 1:
            cocycle = x[1:]
            mt = np.empty((ndim, ndim))
            for i in range(ndim):
                mt[i, i] = x[0]
        elif lattice_type > 20:
            cocycle = x[2:]
            mt = np.empty((ndim, ndim))
            if lattice_type == 21:
                mt[0, 0] = x[0]
                mt[1, 1] = x[1]
                mt[2, 2] = x[1]
            if lattice_type == 22:
                mt[0, 0] = x[0]
                mt[1, 1] = x[1]
                mt[2, 2] = x[0]
            if lattice_type == 23:
                mt[0, 0] = x[0]
                mt[1, 1] = x[0]
                mt[2, 2] = x[1]
        else:
            cocycle = x[3:]
            mt = np.empty((ndim, ndim))
            for i in range(ndim):
                mt[i, i] = x[i]
        g = np.triu_indices(ndim, 1)
        for i, j in zip(*g, strict=False):
            mt[i, j] = (
                metric_tensor_std[i, j]
                / np.sqrt(metric_tensor_std[i, i])
                / np.sqrt(metric_tensor_std[j, j])
                * np.sqrt(mt[i, i])
                * np.sqrt(mt[j, j])
            )
            mt[j, i] = mt[i, j]
        cocycle_rep = None if cocycle_size == 0 else np.reshape(cocycle, (cocycle_size, ndim))
        return mt, cocycle_rep

    @staticmethod
    def initialize_x_bounds(
        ndim: int,
        cocycle_rep: np.ndarray | None,
        metric_tensor_std: np.ndarray,
        lattice_type: int,
        delta_theta: float,
        delta_x: float,
        lattice_expand: float,
        lattice_shrink: float,
    ) -> tuple[np.ndarray, list[tuple[float, float]]]:
        """Initialize ZL* parameter vector ``x`` and box bounds ``(lb, ub)``.

        Args:
            ndim: Spatial dimensionality (3).
            cocycle_rep: Initial cocycle matrix ``(order - 1, ndim)`` or ``None``.
            metric_tensor_std: Rescaled standard metric tensor.
            lattice_type: Symmetry constraint code (1, 21, 22, 23, or 3).
            delta_theta: Deprecated angle-change parameter retained for HTS
                script compatibility.
            delta_x: Half-width bound ``[-delta_x, delta_x]`` on cocycle entries.
            lattice_expand: Upper scale factor for lattice vector lengths.
            lattice_shrink: Lower scale factor for lattice vector lengths.

        Returns:
            Tuple ``(x0, bounds)`` for ``scipy.optimize.fmin_l_bfgs_b``.
        """
        if lattice_type == 1:
            mtsize = 1
            size = int(mtsize + cocycle_rep.shape[0] * ndim) if cocycle_rep is not None else mtsize
            x = np.empty(size)
            ub = np.empty(size)
            lb = np.empty(size)
            xinc = 0
            x[xinc] = metric_tensor_std[0, 0]
            ub[xinc] = metric_tensor_std[0, 0] * (1.01 * lattice_expand) ** 2
            lb[xinc] = metric_tensor_std[0, 0] * (lattice_shrink) ** 2
            xinc += 1
        elif lattice_type > 20:
            mtsize = 2
            size = int(mtsize + cocycle_rep.shape[0] * ndim) if cocycle_rep is not None else mtsize
            x = np.empty(size)
            ub = np.empty(size)
            lb = np.empty(size)
            if lattice_type == 21 or lattice_type == 22:
                xinc = 0
                x[xinc] = metric_tensor_std[0, 0]
                ub[xinc] = metric_tensor_std[0, 0] * (1.01 * lattice_expand) ** 2
                lb[xinc] = metric_tensor_std[0, 0] * (lattice_shrink) ** 2
                xinc += 1
                x[xinc] = metric_tensor_std[1, 1]
                ub[xinc] = metric_tensor_std[1, 1] * (1.01 * lattice_expand) ** 2
                lb[xinc] = metric_tensor_std[1, 1] * (lattice_shrink) ** 2
                xinc += 1
            else:
                xinc = 0
                x[xinc] = metric_tensor_std[0, 0]
                ub[xinc] = metric_tensor_std[0, 0] * (1.01 * lattice_expand) ** 2
                lb[xinc] = metric_tensor_std[0, 0] * (lattice_shrink) ** 2
                xinc += 1
                x[xinc] = metric_tensor_std[2, 2]
                ub[xinc] = metric_tensor_std[2, 2] * (1.01 * lattice_expand) ** 2
                lb[xinc] = metric_tensor_std[2, 2] * (lattice_shrink) ** 2
                xinc += 1
        else:
            mtsize = 3
            size = int(mtsize + cocycle_rep.shape[0] * ndim) if cocycle_rep is not None else mtsize
            x = np.empty(size)
            ub = np.empty(size)
            lb = np.empty(size)
            xinc = 0
            for i in range(3):
                x[xinc] = metric_tensor_std[i, i]
                ub[xinc] = metric_tensor_std[i, i] * (1.01 * lattice_expand) ** 2
                lb[xinc] = metric_tensor_std[i, i] * (lattice_shrink) ** 2
                xinc += 1
        if cocycle_rep is not None:
            x[xinc:] = cocycle_rep.flatten()
            ub[xinc:] = delta_x
            lb[xinc:] = -1 * delta_x
        bounds = []
        for i in range(len(x)):
            bounds.append((lb[i], ub[i]))
        return x, bounds

    @staticmethod
    def all_distances(coords1: Any, coords2: Any) -> np.ndarray:
        """Compute pairwise Euclidean distances between two sets of Cartesian coordinates.

        Args:
            coords1: First coordinate array ``(N, 3)``.
            coords2: Second coordinate array ``(M, 3)``.

        Returns:
            Pairwise Euclidean distance matrix ``(N, M)``.
        """
        c1 = np.array(coords1)
        c2 = np.array(coords2)
        z = (c1[:, None, :] - c2[None, :, :]) ** 2
        return np.sum(z, axis=-1) ** 0.5

    def func(
        self,
        x: np.ndarray,
        ndim: int,
        order: int,
        mat_target: np.ndarray,
        colattice_inds: list[list[int]],
        colattice_weights: list[float],
        cycle_rep: np.ndarray,
        cycle_cocycle_I: np.ndarray,
        num_nodes: int,
        shortest_path: dict[str, list[str]],
        spanning: list[Any],
        uncovered_pair: list[list[Any]],
        uncovered_pair_lj: list[list[float]],
        covered_pair_lj: list[list[float]],
        vbond_param_ave_covered: float,
        vbond_param_ave: float,
        lattice_vectors_scaled: np.ndarray,
        structure_species: list[str],
        angle_weight: float,
        repul: bool,
        lattice_type: int,
        metric_tensor_std: np.ndarray,
    ) -> float:
        """Evaluate the ZL* objective function matching GFN-FF inner products plus LJ repulsion."""
        square_diff = 0.0
        metric_tensor, cocycle_rep = self.convert_params(
            x, ndim, int(order - 1), lattice_type, metric_tensor_std
        )
        if cocycle_rep is not None:
            periodic_rep = np.concatenate((cycle_rep, cocycle_rep))
        else:
            periodic_rep = cycle_rep
        lattice_arcs = np.dot(cycle_cocycle_I, periodic_rep)
        inner_p = np.dot(np.dot(lattice_arcs, metric_tensor), lattice_arcs.T)
        epsilon2 = 1e-10
        for k in range(len(colattice_inds[0])):
            i = colattice_inds[0][k]
            j = colattice_inds[1][k]
            if i == j:
                # inner_p units are Angstrom^2
                square_diff += (inner_p[i][j] - mat_target[i][j]) ** 2 + (
                    4
                    * vbond_param_ave_covered
                    * (covered_pair_lj[i][1] / np.sqrt(max(inner_p[i][j], epsilon2))) ** 12
                )
            else:
                square_diff += (
                    angle_weight * colattice_weights[k] * (inner_p[i][j] - mat_target[i][j]) ** 2
                )
        # Repulsive Lennard-Jones term to prevent non-bonded atom collisions
        if repul:
            coordinates_temp = self.get_coordinates(
                lattice_arcs, num_nodes, shortest_path, spanning
            )
            coordinates_temp_cart = np.dot(coordinates_temp, lattice_vectors_scaled)
            distance_matrix = self.all_distances(coordinates_temp_cart, coordinates_temp_cart)
            for i in range(len(uncovered_pair)):
                r_temp = distance_matrix[uncovered_pair[i][0], uncovered_pair[i][1]]
                r_temp = max(r_temp, 1e-8)
                if r_temp < uncovered_pair_lj[i][0]:
                    square_diff += 4 * vbond_param_ave * (uncovered_pair_lj[i][1] / r_temp) ** 12

        return float(square_diff)

    def func_check(
        self,
        x: np.ndarray,
        ndim: int,
        order: int,
        mat_target: np.ndarray,
        colattice_inds: list[list[int]],
        colattice_weights: list[float],
        cycle_rep: np.ndarray,
        cycle_cocycle_I: np.ndarray,
        num_nodes: int,
        shortest_path: dict[str, list[str]],
        spanning: list[Any],
        uncovered_pair: list[list[Any]],
        uncovered_pair_lj: list[list[float]],
        covered_pair_lj: list[list[float]],
        vbond_param_ave_covered: float,
        vbond_param_ave: float,
        lattice_vectors_scaled: np.ndarray,
        structure_species: list[str],
        angle_weight: float,
        repul: bool,
        lattice_type: int,
        metric_tensor_std: np.ndarray,
    ) -> float:
        """Evaluate the ZL* objective while printing per-bond/angle/repulsion diagnostics."""
        square_diff = 0.0
        metric_tensor, cocycle_rep = self.convert_params(
            x, ndim, int(order - 1), lattice_type, metric_tensor_std
        )
        if cocycle_rep is not None:
            periodic_rep = np.concatenate((cycle_rep, cocycle_rep))
        else:
            periodic_rep = cycle_rep
        lattice_arcs = np.dot(cycle_cocycle_I, periodic_rep)
        inner_p = np.dot(np.dot(lattice_arcs, metric_tensor), lattice_arcs.T)
        coordinates_temp = self.get_coordinates(lattice_arcs, num_nodes, shortest_path, spanning)
        coordinates_temp_cart = np.dot(coordinates_temp, lattice_vectors_scaled)
        distance_matrix = self.all_distances(coordinates_temp_cart, coordinates_temp_cart)
        for k in range(len(colattice_inds[0])):
            i = colattice_inds[0][k]
            j = colattice_inds[1][k]
            if i == j:
                # inner_p units are Angstrom^2
                square_diff += (inner_p[i][j] - mat_target[i][j]) ** 2 + (
                    4
                    * vbond_param_ave_covered
                    * (covered_pair_lj[i][1] / np.sqrt(inner_p[i][j])) ** 12
                )
                print(
                    "bond:"
                    + str(i)
                    + ","
                    + str(j)
                    + ","
                    + str(round(np.sqrt(inner_p[i][j]), 2))
                    + ","
                    + str(round(np.sqrt(mat_target[i][j]), 2))
                    + ","
                    + str(round((inner_p[i][j] - mat_target[i][j]) ** 2, 5))
                    + ","
                    + str(
                        round(
                            4
                            * vbond_param_ave_covered
                            * (covered_pair_lj[i][1] / np.sqrt(inner_p[i][j])) ** 12,
                            5,
                        )
                    )
                )
            else:
                square_diff += (
                    angle_weight * colattice_weights[k] * (inner_p[i][j] - mat_target[i][j]) ** 2
                )
                print(
                    "angle:"
                    + str(i)
                    + ","
                    + str(j)
                    + ","
                    + str(
                        round(
                            inner_p[i][j] / np.sqrt(inner_p[i][i]) / np.sqrt(inner_p[j][j]),
                            5,
                        )
                    )
                    + ","
                    + str(
                        round(
                            mat_target[i][j]
                            / np.sqrt(mat_target[i][i])
                            / np.sqrt(mat_target[j][j]),
                            5,
                        )
                    )
                    + ","
                    + str(
                        round(
                            angle_weight
                            * colattice_weights[k]
                            * (inner_p[i][j] - mat_target[i][j]) ** 2,
                            5,
                        )
                    )
                )
        if repul:
            for i in range(len(uncovered_pair)):
                r_temp = distance_matrix[uncovered_pair[i][0], uncovered_pair[i][1]]
                if r_temp < uncovered_pair_lj[i][0]:
                    square_diff += 4 * vbond_param_ave * (uncovered_pair_lj[i][1] / r_temp) ** 12
                    print(
                        "repul:"
                        + str(uncovered_pair[i][0])
                        + ","
                        + str(uncovered_pair[i][1])
                        + ","
                        + str(round(r_temp, 4))
                        + ","
                        + str(
                            round(
                                4 * vbond_param_ave * (uncovered_pair_lj[i][1] / r_temp) ** 12,
                                4,
                            )
                        )
                    )
        return float(square_diff)

    def SLICES2space_group_number(
        self,
        SLICES: str,
        strategy: int = 4,
        fix_duplicate_edge: bool = True,
    ) -> int | None:
        """Estimate the space-group number of a SLICES string from its barycentric placement.

        Reconstructs only the unscaled standard barycentric embedding (skipping
        GFN-FF, ZL*, and MLIP relaxation) and analyzes symmetry via pymatgen's
        ``SpacegroupAnalyzer``.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.
            fix_duplicate_edge: Whether to deduplicate repeated edges. Defaults to ``True``.

        Returns:
            International space-group number (1..230), or ``None`` if graph
            embedding or symmetry analysis fails.
        """
        try:
            self.from_SLICES(SLICES, strategy, fix_duplicate_edge)

            x_dat, net_voltage = self.convert_graph()
            net = Net(x_dat, dim=3)
            net.voltage = net_voltage

            if self.check_results:
                fig = plt.figure()
                nx.draw(net.graph, ax=fig.add_subplot(111))
                fig.savefig("graph.png")

            net.simple_cycle_basis()
            net.get_lattice_basis()
            net.get_cocycle_basis()

            net.get_metric_tensor()
            lattice_vectors_std = np.linalg.cholesky(net.metric_tensor)
            if net.cocycle is not None:
                net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
            else:
                net.periodic_rep = net.cycle_rep
            num_nodes = len(net.graph.nodes)
            G = nx.MultiDiGraph()
            G.add_nodes_from(net.vertices())
            G.add_edges_from(net.all_edges())
            edges = list(G.edges)
            G_nonDi = nx.MultiGraph()
            G_nonDi.add_nodes_from(net.vertices())
            G_nonDi.add_edges_from(net.all_edges())
            mst = tree.minimum_spanning_edges(G_nonDi, algorithm="kruskal", data=False)
            spanning = list(mst)
            for i in range(len(spanning)):
                for j in range(len(edges)):
                    if spanning[i][2] == edges[j][2]:
                        spanning[i] = edges[j]
            spanning_graph = nx.MultiGraph()
            spanning_graph.add_nodes_from(G.nodes)
            spanning_graph.add_edges_from(spanning)
            shortest_path = nx.shortest_path(spanning_graph, source="1")
            arc_coord_std = net.lattice_arcs
            if self.unstable_graph:
                net.cocycle_rep = np.zeros((net.order - 1, net.ndim)) + 0.5
                net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
                arc_coord_std = net.lattice_arcs
            coordinates_std = self.get_coordinates(
                arc_coord_std, num_nodes, shortest_path, spanning
            )

            atom_symbols = [str(ElementBase.from_Z(i)) for i in self.atom_types]
            structure_recreated_std = Structure(lattice_vectors_std, atom_symbols, coordinates_std)

            sga = SpacegroupAnalyzer(structure_recreated_std)
            space_group_num = sga.get_space_group_number()
        except Exception as e:
            print(f"Error in get_space_group_number: {e}")
            return None
        return space_group_num

    # === Structure Reconstruction, Force-Field Relaxation & Matching ===

    def to_structures(
        self,
        bond_scaling: float = 1.05,
        delta_theta: float = 0.005,
        delta_x: float = 0.45,
        lattice_shrink: float = 1,
        lattice_expand: float = 1.25,
        angle_weight: float = 0.5,
        vbond_param_ave_covered: float = 0.00,
        vbond_param_ave: float = 0.01,
        repul: bool = True,
    ) -> tuple[list[Structure], float]:
        """Reconstruct intermediate and force-field-relaxed crystal structures from graph state.

        Produces up to three structures in progressive refinement order:
        ``[rescaled_barycentric_std, zl_star_opt, force_field_relaxed_opt2]``.
        When ``self.relaxer is None`` or force-field relaxation fails, returns
        ``([structure_recreated_std, structure_recreated_opt], 0)``.

        Args:
            bond_scaling: Empirical GFN-FF bond-length scale factor. Defaults to ``1.05``.
            delta_theta: Deprecated angle-limit argument retained for HTS
                compatibility. Defaults to ``0.005``.
            delta_x: Cocycle coordinate bound ``[-delta_x, delta_x]``. Defaults to ``0.45``.
            lattice_shrink: Minimum lattice-length scale factor. Defaults to ``1``.
            lattice_expand: Maximum lattice-length scale factor. Defaults to ``1.25``.
            angle_weight: Weight of off-diagonal bond-angle terms in ``func``.
                Defaults to ``0.5``.
            vbond_param_ave_covered: LJ repulsive well depth for bonded pairs.
                Defaults to ``0.00``.
            vbond_param_ave: LJ repulsive well depth for non-bonded pairs.
                Defaults to ``0.01``.
            repul: Whether to include non-bonded LJ repulsion during ZL*.
                Defaults to ``True``.

        Returns:
            Tuple ``(structures, final_energy_per_atom)`` where ``structures`` has
            length 3 when relaxed or length 2 when unrelaxed/failed, and
            ``final_energy_per_atom`` is in eV/atom (``0`` if unrelaxed).
        """
        x_dat, net_voltage = self.convert_graph()
        net = Net(x_dat, dim=3)
        net.voltage = net_voltage
        if self.check_results:
            fig = plt.figure()
            nx.draw(net.graph, ax=fig.add_subplot(111))
            fig.savefig("graph.png")
        net.simple_cycle_basis()
        net.get_lattice_basis()
        net.get_cocycle_basis()
        if self.check_results:
            inner_p_target, colattice_inds, colattice_weights = self.get_inner_p_target_debug(
                bond_scaling
            )
        else:
            target_res = self.get_inner_p_target(bond_scaling)
            inner_p_target, colattice_inds, colattice_weights = target_res  # type: ignore[misc]
        uncovered_pair = self.get_uncovered_pair(net.graph)
        uncovered_pair_lj = self.get_uncovered_pair_lj(uncovered_pair)
        covered_pair_lj = self.get_covered_pair_lj()
        if net.cocycle is not None:
            net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
        else:
            net.periodic_rep = net.cycle_rep
        net.get_metric_tensor()
        lattice_vectors_std = np.linalg.cholesky(net.metric_tensor)
        arc_coord_std = net.lattice_arcs
        num_nodes = len(net.graph.nodes)
        G = nx.MultiDiGraph()
        G.add_nodes_from(net.vertices())
        G.add_edges_from(net.all_edges())
        edges = list(G.edges)
        G_nonDi = nx.MultiGraph()
        G_nonDi.add_nodes_from(net.vertices())
        G_nonDi.add_edges_from(net.all_edges())
        mst = tree.minimum_spanning_edges(G_nonDi, algorithm="kruskal", data=False)
        spanning = list(mst)
        for i in range(len(spanning)):
            for j in range(len(edges)):
                if spanning[i][2] == edges[j][2]:
                    spanning[i] = edges[j]
        spanning_graph = nx.MultiGraph()
        spanning_graph.add_nodes_from(G.nodes)
        spanning_graph.add_edges_from(spanning)
        shortest_path = nx.shortest_path(spanning_graph, source="1")
        inner_p_std = np.dot(np.dot(net.lattice_arcs, net.metric_tensor), net.lattice_arcs.T)
        lattice_vectors_scaled = self.get_rescaled_lattice_vectors(
            inner_p_target, inner_p_std, lattice_vectors_std, arc_coord_std
        )
        metric_tensor_std = np.dot(lattice_vectors_scaled, lattice_vectors_scaled.T)
        if self.unstable_graph:
            net.cocycle_rep = np.zeros((net.order - 1, net.ndim)) + 0.5
            net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
            arc_coord_std = net.lattice_arcs
        coordinates_std = self.get_coordinates(arc_coord_std, num_nodes, shortest_path, spanning)
        atom_symbols = [str(ElementBase.from_Z(i)) for i in self.atom_types]
        structure_recreated_std = Structure(lattice_vectors_scaled, atom_symbols, coordinates_std)
        if net.cocycle_rep is None:
            structure_recreated_opt = structure_recreated_std
        else:
            lattice_length_list = [
                metric_tensor_std[0, 0],
                metric_tensor_std[1, 1],
                metric_tensor_std[2, 2],
            ]
            lattice_length_list_unique = list(set(lattice_length_list))
            lattice_type = len(lattice_length_list_unique)
            if lattice_type == 2:
                if metric_tensor_std[0, 0] == metric_tensor_std[1, 1]:
                    lattice_type = 23
                if metric_tensor_std[0, 0] == metric_tensor_std[2, 2]:
                    lattice_type = 22
                if metric_tensor_std[2, 2] == metric_tensor_std[1, 1]:
                    lattice_type = 21
            x0, bounds = self.initialize_x_bounds(
                net.ndim,
                net.cocycle_rep,
                metric_tensor_std,
                lattice_type,
                delta_theta,
                delta_x,
                lattice_expand,
                lattice_shrink,
            )
            x_res = fmin_l_bfgs_b(
                self.func,
                x0,
                fprime=None,
                args=(
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
                    vbond_param_ave_covered,
                    vbond_param_ave,
                    lattice_vectors_scaled,
                    atom_symbols,
                    angle_weight,
                    repul,
                    lattice_type,
                    metric_tensor_std,
                ),
                approx_grad=True,
                bounds=bounds,
                m=10,
                factr=10000000.0,
                pgtol=1e-05,
                epsilon=1e-08,
                maxfun=15000,
                maxiter=15000,
                callback=None,
                maxls=20,
            )
            net.metric_tensor, net.cocycle_rep = self.convert_params(
                x_res[0], net.ndim, int(net.order - 1), lattice_type, metric_tensor_std
            )
            lattice_vectors_new = np.linalg.cholesky(net.metric_tensor)
            if net.cocycle is not None:
                net.periodic_rep = np.concatenate((net.cycle_rep, net.cocycle_rep), axis=0)
            else:
                net.periodic_rep = net.cycle_rep
            arc_coord_new = net.lattice_arcs
            coordinates_new = self.get_coordinates(
                arc_coord_new, num_nodes, shortest_path, spanning
            )
            structure_recreated_opt = Structure(
                lattice_vectors_new, atom_symbols, coordinates_new
            )
            if self.check_results:
                print(x_res[0])
                print(
                    self.func_check(
                        x_res[0],
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
                        vbond_param_ave_covered,
                        vbond_param_ave,
                        lattice_vectors_scaled,
                        atom_symbols,
                        angle_weight,
                        repul,
                        lattice_type,
                        metric_tensor_std,
                    )
                )
        if self.relaxer is None:
            return [structure_recreated_std, structure_recreated_opt], 0
        try:
            if num_nodes <= 20:
                structure_recreated_opt2, final_energy_per_atom = self.relax(
                    structure_recreated_opt
                )
            elif 20 < num_nodes <= 40:
                structure_recreated_opt2, final_energy_per_atom = self.relax_large_cell1(
                    structure_recreated_opt
                )
            else:
                structure_recreated_opt2, final_energy_per_atom = self.relax_large_cell2(
                    structure_recreated_opt
                )
            return [
                structure_recreated_std,
                structure_recreated_opt,
                structure_recreated_opt2,
            ], final_energy_per_atom
        except Exception as e:
            print(e)
            return [structure_recreated_std, structure_recreated_opt], 0

    def SLICES2structure(
        self,
        SLICES: str,
        strategy: int = 4,
        fix_duplicate_edge: bool = True,
    ) -> tuple[Structure, float]:
        """Decode a SLICES string into its reconstructed crystal structure and energy/atom.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.
            fix_duplicate_edge: Whether to deduplicate repeated edges. Defaults to ``True``.

        Returns:
            Tuple ``(structure, final_energy_per_atom)`` returning the most
            refined structure from ``to_structures()`` and its predicted energy
            in eV/atom (``0`` if relaxation was skipped or failed).
        """
        self.from_SLICES(SLICES, strategy, fix_duplicate_edge)
        structures, final_energy_per_atom = self.to_structures()
        return structures[-1], final_energy_per_atom

    def robust_SLICES2structure(
        self,
        SLICES: str,
        strategy: int = 4,
        fix_duplicate_edge: bool = True,
        n_starts: int = 3,
        seed: int = 0,
    ) -> tuple[Structure, float]:
        """Decode a SLICES string with opt-in multi-stage recovery fallbacks.

        Executes the standard v4.0.2 ``SLICES2structure`` path first, delegating
        to :func:`slices.decoding_strategies.robust_decode` (seeded multi-start
        ZL* optimization and progressive force-field relaxation) only when
        standard decoding fails or yields an unrelaxed fallback structure.

        Args:
            SLICES: Input SLICES string.
            strategy: Encoding strategy number (1, 3, or 4). Defaults to 4.
            fix_duplicate_edge: Whether to deduplicate repeated edges. Defaults to ``True``.
            n_starts: Number of seeded ZL* optimization starts on fallback.
                Defaults to 3.
            seed: Random-number generator seed for fallback perturbations.
                Defaults to 0.

        Returns:
            Tuple ``(structure, final_energy_per_atom)``.

        Raises:
            SLICESDecodingError: If all decoding and recovery stages fail.
        """
        from slices.decoding_strategies import robust_decode

        return robust_decode(
            self,
            slices_str=SLICES,
            strategy=strategy,
            fix_duplicate_edge=fix_duplicate_edge,
            n_starts=n_starts,
            seed=seed,
        )

    def to_relaxed_structure(
        self,
        bond_scaling: float = 1.05,
        delta_theta: float = 0.005,
        delta_x: float = 0.45,
        lattice_shrink: float = 1,
        lattice_expand: float = 1.25,
        angle_weight: float = 0.5,
        vbond_param_ave_covered: float = 0.000,
        vbond_param_ave: float = 0.01,
        repul: bool = True,
    ) -> tuple[Structure, float]:
        """Reconstruct a force-field-relaxed crystal structure, raising if relaxation failed.

        Args:
            bond_scaling: Empirical GFN-FF bond-length scale factor. Defaults to ``1.05``.
            delta_theta: Deprecated angle-limit parameter. Defaults to ``0.005``.
            delta_x: Cocycle coordinate bound. Defaults to ``0.45``.
            lattice_shrink: Minimum lattice-length scale factor. Defaults to ``1``.
            lattice_expand: Maximum lattice-length scale factor. Defaults to ``1.25``.
            angle_weight: Angular term weight in ``func``. Defaults to ``0.5``.
            vbond_param_ave_covered: Bonded LJ repulsive well depth. Defaults to ``0.000``.
            vbond_param_ave: Non-bonded LJ repulsive well depth. Defaults to ``0.01``.
            repul: Whether to include non-bonded LJ repulsion. Defaults to ``True``.

        Returns:
            Tuple ``(relaxed_structure, final_energy_per_atom)``.

        Raises:
            Exception: ``"relax failed"`` if relaxation was disabled or failed.
        """
        structures, final_energy_per_atom = self.to_structures(
            bond_scaling,
            delta_theta,
            delta_x,
            lattice_shrink,
            lattice_expand,
            angle_weight,
            vbond_param_ave_covered,
            vbond_param_ave,
            repul,
        )
        if len(structures) == 3:
            return structures[-1], final_energy_per_atom
        raise Exception("relax failed")

    def to_4structures(
        self,
        bond_scaling: float = 1.05,
        delta_theta: float = 0.005,
        delta_x: float = 0.45,
        lattice_shrink: float = 1,
        lattice_expand: float = 1.25,
        angle_weight: float = 0.5,
        vbond_param_ave_covered: float = 0.000,
        vbond_param_ave: float = 0.01,
        repul: bool = True,
    ) -> tuple[list[Structure], float]:
        """Reconstruct four benchmark structures including direct relaxation of ``std``.

        Returns ``[std, std_relaxed, zl_opt, zl_opt_relaxed]`` when relaxation
        succeeds, or falls back to ``to_structures()`` output when ``self.relaxer``
        is ``None`` or ``std`` relaxation fails.
        """
        structures, final_energy_per_atom = self.to_structures(
            bond_scaling,
            delta_theta,
            delta_x,
            lattice_shrink,
            lattice_expand,
            angle_weight,
            vbond_param_ave_covered,
            vbond_param_ave,
            repul,
        )
        if self.relaxer is None:
            return structures, final_energy_per_atom
        try:
            std2, final_energy_per_atom = self.relax(structures[0])
            return [structures[0], std2, structures[1], structures[2]], final_energy_per_atom
        except Exception as e:
            print(e)
            return structures, final_energy_per_atom

    @function_timeout(seconds=360)
    def relax(self, struc: Structure) -> tuple[Structure, float]:
        """Relax ``struc`` (<= 20 atoms) with ``self.relaxer`` under a 360-second timeout.

        Args:
            struc: Input pymatgen ``Structure``.

        Returns:
            Tuple ``(final_structure, final_energy_per_atom)`` in eV/atom.
        """
        if self.check_results:
            relax_results = self.relaxer.relax(struc, fmax=self.fmax, steps=self.steps)
        else:
            with self.suppress_output():
                relax_results = self.relaxer.relax(struc, fmax=self.fmax, steps=self.steps)
        final_structure = relax_results["final_structure"]
        final_energy_per_atom = float(relax_results["trajectory"].energies[-1] / len(struc))
        return final_structure, final_energy_per_atom

    @function_timeout(seconds=720)
    def relax_large_cell1(self, struc: Structure) -> tuple[Structure, float]:
        """Relax ``struc`` (21..40 atoms) with ``self.relaxer`` under a 720-second timeout.

        Args:
            struc: Input pymatgen ``Structure``.

        Returns:
            Tuple ``(final_structure, final_energy_per_atom)`` in eV/atom.
        """
        if self.check_results:
            relax_results = self.relaxer.relax(struc, fmax=self.fmax, steps=self.steps)
        else:
            with self.suppress_output():
                relax_results = self.relaxer.relax(struc, fmax=self.fmax, steps=self.steps)
        final_structure = relax_results["final_structure"]
        final_energy_per_atom = float(relax_results["trajectory"].energies[-1] / len(struc))
        return final_structure, final_energy_per_atom

    @function_timeout(seconds=2000)
    def relax_large_cell2(self, struc: Structure) -> tuple[Structure, float]:
        """Relax ``struc`` (> 40 atoms) with ``self.relaxer`` under a 2000-second timeout.

        Calls ``self.relaxer.relax(struc)`` using the relaxer's own default
        ``fmax`` and ``steps`` parameters.

        Args:
            struc: Input pymatgen ``Structure``.

        Returns:
            Tuple ``(final_structure, final_energy_per_atom)`` in eV/atom.
        """
        if self.check_results:
            relax_results = self.relaxer.relax(struc)
        else:
            with self.suppress_output():
                relax_results = self.relaxer.relax(struc)
        final_structure = relax_results["final_structure"]
        final_energy_per_atom = float(relax_results["trajectory"].energies[-1] / len(struc))
        return final_structure, final_energy_per_atom

    def match_check(
        self,
        ori: Structure,
        opt: Structure,
        std: Structure,
        ltol: float = 0.2,
        stol: float = 0.3,
        angle_tol: float = 5,
    ) -> tuple[str, str, str, str]:
        """Compare ``opt`` and ``std`` against ``ori`` via ``StructureMatcher`` and graph diff."""
        ori_checked = Structure.from_str(ori.to(fmt="poscar"), "poscar")
        opt_checked = Structure.from_str(opt.to(fmt="poscar"), "poscar")
        std_checked = Structure.from_str(std.to(fmt="poscar"), "poscar")
        sg_ori = self.structure2structure_graph(ori_checked)
        sg_opt = self.structure2structure_graph(opt_checked)
        sg_std = self.structure2structure_graph(std_checked)
        sm = StructureMatcher(
            ltol,
            stol,
            angle_tol,
            primitive_cell=True,
            scale=True,
            attempt_supercell=False,
            comparator=ElementComparator(),
        )
        return (
            str(int(sm.fit(ori_checked, opt_checked))),
            str(int(sm.fit(ori_checked, std_checked))),
            str(sg_ori.diff(sg_opt, strict=False)["dist"]),
            str(sg_ori.diff(sg_std, strict=False)["dist"]),
        )

    def match_check3(
        self,
        ori: Structure,
        opt2: Structure,
        opt: Structure,
        std: Structure,
        ltol: float = 0.2,
        stol: float = 0.3,
        angle_tol: float = 5,
    ) -> tuple[str, str, str, str, str, str]:
        """Compare ``opt2``, ``opt``, and ``std`` with ``ori`` via matcher and graph Jaccard."""
        ori_checked = Structure.from_str(ori.to(fmt="poscar"), "poscar")
        opt2_checked = Structure.from_str(opt2.to(fmt="poscar"), "poscar")
        opt_checked = Structure.from_str(opt.to(fmt="poscar"), "poscar")
        std_checked = Structure.from_str(std.to(fmt="poscar"), "poscar")
        sg_ori = self.structure2structure_graph(ori_checked)
        sg_opt = self.structure2structure_graph(opt_checked)
        sg_opt2 = self.structure2structure_graph(opt2_checked)
        sg_std = self.structure2structure_graph(std_checked)
        sm = StructureMatcher(
            ltol,
            stol,
            angle_tol,
            primitive_cell=True,
            scale=True,
            attempt_supercell=False,
            comparator=ElementComparator(),
        )
        return (
            str(int(sm.fit(ori_checked, opt2_checked))),
            str(int(sm.fit(ori_checked, opt_checked))),
            str(int(sm.fit(ori_checked, std_checked))),
            str(sg_ori.diff(sg_opt2, strict=False)["dist"]),
            str(sg_ori.diff(sg_opt, strict=False)["dist"]),
            str(sg_ori.diff(sg_std, strict=False)["dist"]),
        )

    def match_check4(
        self,
        ori: Structure,
        opt2: Structure,
        opt: Structure,
        std2: Structure,
        std: Structure,
        ltol: float = 0.2,
        stol: float = 0.3,
        angle_tol: float = 5,
    ) -> tuple[str, str, str, str, str, str, str, str]:
        """Compare ``opt2``, ``opt``, ``std2``, and ``std`` against ``ori``.

        Args:
            ori: Reference original ``Structure``.
            opt2: Force-field-relaxed ZL* ``Structure``.
            opt: Unrelaxed ZL*-optimized ``Structure``.
            std2: Force-field-relaxed barycentric ``Structure``.
            std: Rescaled barycentric ``Structure``.
            ltol: Fractional lattice-length tolerance. Defaults to ``0.2``.
            stol: Site coordinate tolerance. Defaults to ``0.3``.
            angle_tol: Lattice angle tolerance in degrees. Defaults to ``5``.

        Returns:
            8-tuple of stringified match indicators (``"1"`` or ``"0"``) and
            topological Jaccard distances for ``(opt2, opt, std2, std)``.
        """
        ori_checked = Structure.from_str(ori.to(fmt="poscar"), "poscar")
        opt2_checked = Structure.from_str(opt2.to(fmt="poscar"), "poscar")
        opt_checked = Structure.from_str(opt.to(fmt="poscar"), "poscar")
        std_checked = Structure.from_str(std.to(fmt="poscar"), "poscar")
        std2_checked = Structure.from_str(std2.to(fmt="poscar"), "poscar")
        sg_ori = self.structure2structure_graph(ori_checked)
        sg_opt = self.structure2structure_graph(opt_checked)
        sg_opt2 = self.structure2structure_graph(opt2_checked)
        sg_std = self.structure2structure_graph(std_checked)
        sg_std2 = self.structure2structure_graph(std2_checked)
        sm = StructureMatcher(
            ltol,
            stol,
            angle_tol,
            primitive_cell=True,
            scale=True,
            attempt_supercell=False,
            comparator=ElementComparator(),
        )
        return (
            str(int(sm.fit(ori_checked, opt2_checked))),
            str(int(sm.fit(ori_checked, opt_checked))),
            str(int(sm.fit(ori_checked, std2_checked))),
            str(int(sm.fit(ori_checked, std_checked))),
            str(sg_ori.diff(sg_opt2, strict=False)["dist"]),
            str(sg_ori.diff(sg_opt, strict=False)["dist"]),
            str(sg_ori.diff(sg_std2, strict=False)["dist"]),
            str(sg_ori.diff(sg_std, strict=False)["dist"]),
        )
