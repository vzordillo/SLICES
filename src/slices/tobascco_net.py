"""Periodic net topology and barycentric embedding algorithms for SLICES.

Adapted from Boyd, P. G. & Woo, T. K., *CrystEngComm* 2016, 18 (21), 3777-3792
(https://github.com/peteboyd/tobascco) and modified by Hang Xiao to handle self-loop
edges in labeled quotient crystal graphs.

Provides ``Net`` for cycle/cocycle basis construction, SymPy rational nullspace
lattice-basis extraction, Eon's orthogonal projection, and barycentric metric
tensor calculation, alongside ``SystreDB`` for parsing Systre ``.arc`` archives.
"""

from __future__ import annotations

import itertools
import logging
import math
import sys
from collections.abc import Iterator, Sequence
from typing import Any
from uuid import UUID, uuid4

import networkx as nx
import numpy as np
import sympy as sy

_logger = logging.getLogger(__name__)

__all__ = ["DEG2RAD", "Net", "SystreDB"]

DEG2RAD: float = np.pi / 180.0


class SystreDB(dict[Any, Any]):
    """Dictionary-backed reader for crystallographic net archives in Systre ``.arc`` format."""

    def __init__(self, filename: str | None = None) -> None:
        """Initialize ``SystreDB`` and optionally parse ``filename``."""
        super().__init__()
        self.voltages: dict[Any, np.ndarray] = {}
        self.read_store_file(filename)
        self.scale: tuple[Any, Any] = (None, None)

    def read_store_file(self, file: str | None = None) -> None:
        """Read and store all net blocks from a Systre ``.arc`` file."""
        if file is None:
            return

        with open(file, encoding="utf-8") as handle:
            block: list[str] = []
            while True:
                line = handle.readline()
                if not line:
                    break

                tokens = line.strip().split()
                if tokens and tokens[0].lower() != "end":
                    block.append(" ".join(tokens))
                elif tokens and tokens[0].lower() == "end":
                    name = self.get_name(block)
                    parsed = self.get_key(block)
                    if parsed is not None:
                        ndim, systre_key = parsed
                        g, v = self.gen_networkx_graph_format(systre_key, ndim)
                        self[name] = g
                        self.voltages[name] = np.array(v)
                    block = []

    def get_key(self, block: Sequence[str]) -> tuple[int, list[tuple[int, ...]]] | None:
        """Extract ``(dimension, edge_tuples)`` from the ``key`` line of a Systre block."""
        for entry in block:
            tokens = entry.split()
            if tokens[0].lower() == "key":
                dim = int(tokens[1])
                return dim, list(self.Nd_chunks([int(i) for i in tokens[2:]], dim))
        return None

    def get_name(self, block: Sequence[str]) -> str | UUID:
        """Extract the net ``id`` identifier from ``block`` (or generate a UUID)."""
        name: str | UUID = uuid4()
        for entry in block:
            tokens = entry.split()
            if tokens[0].lower() == "id":
                name = tokens[1]
        return name

    def Nd_chunks(self, values: Sequence[int], dim: int) -> Iterator[tuple[int, ...]]:
        """Yield ``(2 + dim)``-element tuples from ``values``."""
        n = 2 + dim
        for i in range(0, len(values), n):
            yield tuple(values[i : i + n])

    def gen_networkx_graph_format(
        self,
        edges: Sequence[tuple[int, ...]],
        dim: int = 3,
    ) -> tuple[list[tuple[str, str, dict[str, str]]], list[tuple[int, ...]]]:
        """Convert Systre key edge tuples into NetworkX edge list and voltage list."""
        x_dat: list[tuple[str, str, dict[str, str]]] = []
        voltages: list[tuple[int, ...]] = []
        if dim == 2:
            for idx, (v1, v2, e1, e2) in enumerate(edges):
                ename = f"e{idx + 1}"
                voltages.append((e1, e2))
                x_dat.append((str(v1), str(v2), {"label": ename}))
        elif dim == 3:
            for idx, (v1, v2, e1, e2, e3) in enumerate(edges):
                ename = f"e{idx + 1}"
                voltages.append((e1, e2, e3))
                x_dat.append((str(v1), str(v2), {"label": ename}))
        else:
            _logger.error(f"Embedding nets of dimension {dim} is not currently implemented.")
        return (x_dat, voltages)

    def gen_sage_graph_format(
        self,
        edges: Sequence[tuple[int, ...]],
    ) -> tuple[dict[str, dict[str, list[str]]], list[tuple[int, int, int]]]:
        """Convert 3D Systre key edge tuples into a legacy Sage adjacency dictionary."""
        sage_dict: dict[str, dict[str, list[str]]] = {}
        voltages: list[tuple[int, int, int]] = []
        for idx, (v1, v2, e1, e2, e3) in enumerate(edges):
            ename = f"e{idx + 1}"
            voltages.append((e1, e2, e3))
            n1 = str(v1)
            n2 = str(v2)
            sage_dict.setdefault(n1, {})
            sage_dict.setdefault(n2, {})
            sage_dict[n1].setdefault(n2, [])
            sage_dict[n1][n2].append(ename)
        return (sage_dict, voltages)


class Net:
    """Periodic labeled quotient graph (crystallographic net) for 3D crystal embedding."""

    def __init__(
        self,
        graph: Sequence[tuple[str, str, dict[str, Any]]] | None = None,
        dim: int = 3,
        options: Any = None,
    ) -> None:
        """Initialize a periodic ``Net`` from labeled directed multi-edges.

        Args:
            graph: Optional sequence of ``(u, v, {"label": "e1", ...})`` edge tuples.
            dim: Periodicity dimension (default ``3``).
            options: Optional configuration namespace for diagnostic error reporting.
        """
        self.name: str | None = None
        self.lattice_basis: Any = None
        self.metric_tensor: Any = None
        self.cycle: Any = None
        self.cycle_rep: Any = None
        self.cocycle: Any = None
        self.cocycle_rep: Any = None
        self.periodic_rep: Any = None  # alpha(B)
        self.edge_labels: Any = None
        self.node_labels: Any = None
        self.colattice_dotmatrix: Any = None
        self.colattice_inds: Any = None
        self.voltage: Any = None
        self._graph: Any = graph
        self.ndim: int = dim
        if graph is not None:
            self._graph = nx.MultiDiGraph()
            self.original_graph = nx.MultiDiGraph()
            for e1, e2, d in graph:
                self._graph.add_edge(e1, e2, **d, key=d["label"])
                self.original_graph.add_edge(e1, e2, **d, key=d["label"])

        self.options = options

    def clear_cache(self) -> None:
        """Clear cached algebraic basis properties and computed arrays while keeping ``graph``."""
        for attr in ("_kernel", "_cycle_cocycle", "_cycle_cocycle_I"):
            if hasattr(self, attr):
                delattr(self, attr)
        self.cycle = None
        self.cocycle = None
        self.cycle_rep = None
        self.cocycle_rep = None
        self.periodic_rep = None
        self.lattice_basis = None
        self.metric_tensor = None
        self.colattice_dotmatrix = None

    def nodes_iter(self, data: bool = True) -> Iterator[Any]:
        """Yield graph nodes, optionally paired with their node attribute dictionary."""
        for node in self._graph.nodes():
            if data:
                d = self._graph.nodes[node]
                yield (node, d)
            else:
                yield node

    def edges_iter(self, data: bool = True) -> Iterator[Any]:
        """Yield directed edges, optionally including their edge attribute dictionary."""
        for erp in self._graph.edges(data=data):
            if data:
                yield (erp[0], erp[1], erp[2])
            else:
                yield (erp[0], erp[1])

    def get_cocycle_basis(self) -> None:
        """Construct a linearly independent oriented cutset (cocycle) basis of size ``V - 1``."""
        size = self._graph.order() - 1
        length = self._graph.size()
        count = 0
        for vert in self.vertices():
            if count == size:
                break
            vect = np.zeros(length)
            inds_out = self.return_indices(self.out_edges(vert))
            inds_in = self.return_indices(self.in_edges(vert))
            # Self-loop edges appear in both out_edges and in_edges and cancel out.
            inds_in_out = [value for value in inds_out if value in inds_in]
            if inds_out:
                vect[inds_out] = 1.0
            if inds_in:
                vect[inds_in] = -1.0
            if inds_in_out:
                vect[inds_in_out] = 0
            if self.cycle_cocycle_check(vect):
                count += 1
                self.cocycle = self.add_to_array(vect, self.cocycle)

        if count != size:
            print("ERROR - could not find a linearly independent cocycle basis!")
        if size == 0:
            self.cocycle = None
            self.cocycle_rep = None
        else:
            self.cocycle = np.array(self.cocycle)
            self.cocycle_rep = np.zeros((size, self.ndim))

    def add_name(self) -> str:
        """Return the string label for the next inserted vertex."""
        return str(self.order + 1)

    def insert_and_join(
        self,
        vfrom: str,
        vto: str,
        edge_label: str | None = None,
    ) -> tuple[str, str, str]:
        """Insert vertex ``vto`` and connect ``vfrom -> vto`` with ``edge_label``."""
        if edge_label is None:
            edge_label = f"e{self.shape}"
        self.add_vertex(vto)
        edge = (vfrom, vto, edge_label)
        self.add_edge(vfrom, vto, edge_label)
        return edge

    def add_edges_between(
        self,
        edge: tuple[str, str, str],
        n_subdivisions: int,
    ) -> tuple[list[str], list[tuple[str, str, str]]]:
        """Subdivide ``edge`` into ``n_subdivisions + 1`` edges connected by new vertices."""
        newedges: list[tuple[str, str, str]] = []
        v1 = edge[0] if edge in self.out_edges(edge[0]) else edge[1]
        v2 = edge[1] if edge in self.in_edges(edge[1]) else edge[0]

        name = self.add_name()
        newedges.append(self.insert_and_join(v1, name, edge_label=edge[2]))
        vfrom = name
        d = self.ndim
        newnodes: list[str] = []
        for _ in range(n_subdivisions - 1):
            newnodes.append(vfrom)
            name = self.add_name()
            newedges.append(self.insert_and_join(vfrom, name))
            vfrom = name
            self.voltage = np.concatenate((self.voltage, np.zeros(d).reshape(1, d)))
        newnodes.append(v2)
        lastedge = (vfrom, v2, f"e{self.shape}")
        newedges.append(lastedge)

        self.add_edge(vfrom, v2, f"e{self.shape}")
        self.delete_edge(edge)
        self.voltage = np.concatenate((self.voltage, np.zeros(d).reshape(1, d)))
        return newnodes, newedges

    def cycle_cocycle_check(self, vect: np.ndarray) -> bool:
        """Return ``True`` if ``vect`` is linearly independent of current cycle/cocycle rows."""
        if self.cocycle is None and self.cycle is None:
            return True
        if self.cocycle is None and self.cycle is not None:
            return self.check_linear_dependency(vect, self.cycle)
        return self.check_linear_dependency(vect, self.add_to_array(self.cocycle, self.cycle))

    def get_cycle_basis(self) -> None:
        """Populate ``self.cycle`` and ``self.cycle_rep`` of rank ``E - V + 1`` via DFS cycles."""
        c = self.iter_cycles(
            node=self.vertices(0),
            edge=None,
            cycle=[],
            used=[],
            nodes_visited=[],
            cycle_baggage=[],
            counter=0,
        )
        n = self.shape - self.order + 1
        count = 0
        if self.lattice_basis is not None:
            self.cycle = self.add_to_array(self.lattice_basis, self.cycle)
            self.cycle_rep = self.add_to_array(np.identity(self.ndim), self.cycle_rep)
            count += self.ndim
        for cycle in c:
            if count >= n:
                break
            vect = np.zeros(self.shape)
            vect[self.return_indices(cycle)] = self.return_coeff(cycle)
            volt = self.get_voltage(vect)
            check = self.cycle_cocycle_check(vect)
            if np.all(np.abs(volt) < 1.001) and np.sum(np.abs(volt) > 0.0) and check:
                self.cycle = self.add_to_array(vect, self.cycle)
                self.cycle_rep = self.add_to_array(volt, self.cycle_rep)
                count += 1
        self.cycle = np.array(self.cycle)
        self.cycle_rep = np.array(self.cycle_rep)
        del c

    def add_to_array(self, vect: np.ndarray, rep: np.ndarray | None) -> np.ndarray:
        """Append row(s) ``vect`` onto 2D array ``rep`` (or initialize a copy if ``None``)."""
        v = np.reshape(vect, (1, vect.shape[-1])) if len(vect.shape) == 1 else vect
        if rep is None:
            return v.copy()
        return np.concatenate((rep, v))

    def get_voltage(self, cycle: np.ndarray) -> np.ndarray:
        """Compute net lattice translation (voltage) along ``cycle``."""
        return np.dot(cycle, self.voltage)

    def debug_print(self, val: int, msg: str) -> None:
        """Print an indented diagnostic trace line."""
        print(f"{'  ' * val}[{val}] {msg}")

    def simple_cycle_basis(self) -> None:
        """Construct fundamental cycle basis and cycle voltages from a minimum spanning tree."""
        edges = self.all_edges()
        st_vtx = np.random.choice(range(self.graph.order()))  # noqa: F841 (DEF-004 frozen RNG)
        mst_tree = nx.minimum_spanning_tree(self.graph.to_undirected())
        mspt_edges = [(i, j, d["label"]) for (i, j, d) in mst_tree.edges(data=True)]
        cycle_completes = [
            i
            for i in edges
            if i not in mspt_edges and (i[1], i[0], i[2]) not in mspt_edges
        ]
        self.cycle = []
        self.cycle_rep = []
        for v1, v2, e in cycle_completes:
            path = nx.shortest_path(mst_tree, source=v1, target=v2)
            basis_vector = np.zeros(self.shape)
            cycle: list[tuple[str, str, str]] = []
            coefficients: list[float] = []
            for pv1, pv2 in itertools.pairwise(path):
                edge = next(
                    (i, j, d["label"])
                    for (i, j, d) in mst_tree.edges(nbunch=[pv1, pv2], data=True)
                    if pv1 in (i, j) and pv2 in (i, j)
                )
                if edge not in edges:
                    edge = (edge[1], edge[0], edge[2])
                    if edge not in edges:
                        _logger.error(
                            f"Encountered an edge ({edge[0]}, {edge[1]}, {edge[2]}) not in "
                            "the graph while finding the basis of the cycle space!"
                        )
                coeff = 1.0 if edge in self.out_edges(pv1) else -1.0
                coefficients.append(coeff)
                cycle.append(edge)
            # Closing edge from v2 back to v1
            edge = (v1, v2, e) if (v1, v2, e) in edges else (v2, v1, e)
            coeff = 1.0 if edge in self.in_edges(v1) else -1.0
            coefficients.append(coeff)
            cycle.append(edge)
            basis_vector[self.return_indices(cycle)] = coefficients
            voltage = self.get_voltage(basis_vector)
            self.cycle.append(basis_vector)
            self.cycle_rep.append(voltage)
        self.cycle = np.array(self.cycle)
        self.cycle_rep = np.array(self.cycle_rep)

    def iter_cycles(
        self,
        node: str | None = None,
        edge: tuple[Any, ...] | None = None,
        cycle: list[Any] = [],  # noqa: B006 (DEF-010 frozen signature)
        used: list[Any] = [],  # noqa: B006
        nodes_visited: list[Any] = [],  # noqa: B006
        cycle_baggage: list[Any] = [],  # noqa: B006
        counter: int = 0,
    ) -> Iterator[list[Any]]:
        """Recursively yield simple oriented cycles of the net."""
        if node is None:
            node = self.vertices(0)
        if node in nodes_visited:
            i = nodes_visited.index(node)
            nodes_visited.append(node)
            cycle.append(edge)
            assert edge is not None
            used.append(edge[:3])
            c = cycle[i:]
            uc = sorted([j[:3] for j in c])
            if uc not in cycle_baggage:
                cycle_baggage.append(uc)
                yield c
        else:
            nodes_visited.append(node)
            if edge:
                cycle.append(edge)
                used.append(edge[:3])
            e = [(x, y, z, 1) for x, y, z in self.out_edges(node) if (x, y, z) not in used]
            e += [(x, y, z, -1) for x, y, z in self.in_edges(node) if (x, y, z) not in used]
            for j in e:
                newnode = j[0] if j[0] != node else j[1]
                yield from self.iter_cycles(
                    node=newnode,
                    edge=j,
                    cycle=cycle,
                    used=used,
                    nodes_visited=nodes_visited,
                    cycle_baggage=cycle_baggage,
                    counter=counter + 1,
                )
                nodes_visited.pop(-1)
                cycle.pop(-1)
                used.pop(-1)

    def linear_independent_vectors(self, r_mat: Any, dim: int) -> np.ndarray:
        """Select ``rank(r_mat)`` non-collinear columns from ``r_mat``."""
        mat = np.matrix(r_mat)  # DEF-011 frozen np.matrix
        r = np.linalg.matrix_rank(mat)
        index = np.zeros(r)
        counter = 0
        index[0] = 0
        j = 0
        for i in range(mat.shape[1]):
            if i != j:
                inner_product = np.dot(mat[:, i].T, mat[:, j])
                norm_i = np.linalg.norm(mat[:, i])
                norm_j = np.linalg.norm(mat[:, j])
                if np.abs(inner_product - norm_j * norm_i) > 1e-4:
                    counter += 1
                    index[counter] = i
                    j = i

        r_independent = np.zeros((r, dim))
        i = 0
        while i < r:
            r_independent[i, :] = mat[int(index[i]), :]
            i += 1
        return r_independent

    def get_lattice_basis(self) -> int:
        """Solve for integral cycle combinations spanning the ``ndim`` unit lattice vectors.

        Returns:
            ``1`` if all ``ndim`` integral basis vectors were found, ``-1`` otherwise.
        """
        L = []  # noqa: F841
        inds = list(range(self.cycle_rep.shape[0]))
        np.random.shuffle(inds)  # DEF-004 frozen RNG draw
        cycle_rep = self.cycle_rep.copy()
        cycle = self.cycle.copy()
        lattice: list[np.ndarray] = []
        for e in np.identity(self.ndim):
            kk = np.vstack((e, cycle_rep))
            j = sy.Matrix(kk.T)
            null = np.array([np.array(k).flatten() for k in j.nullspace()], dtype=float)
            found_vector = False
            for nulv in null:
                if abs(nulv[0]) == 1.0:
                    v = -nulv[1:] * nulv[0]
                    nz = np.nonzero(v)
                    tv = np.sum(cycle[nz] * v[nz][:, None], axis=0)
                    if self.is_integral(tv):
                        found_vector = True
                        lattice.append(tv)
                        break
            if not found_vector:
                _logger.error("Could not obtain the lattice basis from the cycle vectors!")
                return -1
        self.lattice_basis = np.array(lattice)
        return 1

    def check_linear_dependency(self, vect: np.ndarray, vset: np.ndarray) -> bool:
        """Return ``True`` if appending ``vect`` increases the matrix rank of ``vset``."""
        if not np.any(vset):
            return True
        a_mat = np.concatenate((vset, np.reshape(vect, (1, self.shape))))
        lrank = vset.shape[0] + 1
        return bool(np.linalg.matrix_rank(a_mat) == lrank)

    def get_index(self, edge: Sequence[Any]) -> int:
        """Return 0-based edge index parsed from ``edge[2]`` (e.g. ``'e1' -> 0``)."""
        return int(edge[2][1:]) - 1

    def return_indices(self, edges: Sequence[Sequence[Any]]) -> list[int]:
        """Return 0-based edge indices for a sequence of labeled edges."""
        return [self.get_index(i) for i in edges]

    def return_coeff(self, edges: Sequence[Sequence[Any]]) -> list[Any]:
        """Return orientation coefficients ``edge[3]`` for a sequence of oriented edges."""
        assert edges[0][3]
        return [i[3] for i in edges]

    def to_ind(self, str_obj: str) -> tuple[int, ...]:
        """Parse underscore-delimited integer indices from ``str_obj``."""
        return tuple(int(i) for i in str_obj.split("_")[1:])

    def assign_ip_matrix(self, mat: np.ndarray, inds: Any) -> None:
        """Normalize and store the target inner-product matrix ``mat`` and indices ``inds``."""
        max_ind, max_val = (
            mat[np.diag_indices_from(mat)].argmax(),
            mat[np.diag_indices_from(mat)].max(),
        )
        self.scale = (([max_ind], [max_ind]), max_val)
        self.sbu_tensor_matrix = mat
        self.colattice_inds = inds
        self.colattice_dotmatrix = np.zeros((mat.shape[0], mat.shape[1]))
        for i, j in zip(*np.triu_indices_from(mat), strict=False):
            if i == j:
                self.colattice_dotmatrix[i, j] = mat[i, j] / max_val
            else:
                val = mat[i, j] / np.sqrt(mat[i, i]) / np.sqrt(mat[j, j])
                self.colattice_dotmatrix[i, j] = val
                self.colattice_dotmatrix[j, i] = val

    def convert_params(
        self,
        x: np.ndarray,
        ndim: int,
        angle_inds: int,
        cocycle_size: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Unpack flat optimization vector ``x`` into ``(metric_tensor, cocycle_rep)``."""
        cell_lengths = x[:ndim]  # noqa: F841
        angles = x[ndim : ndim + angle_inds]  # noqa: F841
        cocycle = x[ndim + angle_inds :]
        mt = np.empty((ndim, ndim))
        i = 0
        for i in range(ndim):
            mt[i, i] = x[i]
        count = i + 1
        g = np.triu_indices(ndim, 1)
        for i, j in zip(*g, strict=False):
            val = x[count] * np.sqrt(mt[i, i]) * np.sqrt(mt[j, j])
            mt[i, j] = val
            mt[j, i] = val
            count += 1
        cocycle_rep = np.reshape(cocycle, (cocycle_size, ndim))
        return mt, cocycle_rep

    def report_errors_nlopt(self) -> None:
        """Log RMS edge-length and angle deviations against ``colattice_dotmatrix``."""
        la = np.dot(self.cycle_cocycle_I, self.periodic_rep)
        inner_p = np.dot(np.dot(la, self.metric_tensor), la.T)
        nz = self.colattice_inds
        cdmat = self.colattice_dotmatrix
        edge_lengths: list[float] = []
        angles: list[float] = []

        for i, j in zip(*nz, strict=False):
            if i != j:
                ang1 = np.arccos(
                    inner_p[i, j] / np.sqrt(inner_p[i, i]) / np.sqrt(inner_p[j, j])
                )
                ang2 = np.arccos(cdmat[i, j])
                angles.append(float((ang1 - ang2) ** 2))
            else:
                diff_sq = (np.sqrt(inner_p[i, j]) - np.sqrt(cdmat[i, j] * self.scale[1])) ** 2
                edge_lengths.append(float(diff_sq))
        edge_average, edge_std = (
            float(np.sqrt(np.mean(edge_lengths))),
            float(np.sqrt(np.std(edge_lengths))),
        )
        _logger.debug(
            f"Average error in edge length: {edge_average:12.5f} +/- {edge_std:9.5f} Angstroms"
        )
        angle_average, angle_std = (
            float(np.sqrt(np.mean(angles))),
            float(np.sqrt(np.std(angles))),
        )
        _logger.debug(
            f"Average error in edge angles: {angle_average / DEG2RAD:12.5f} "
            f"+/- {angle_std / DEG2RAD:9.5f} degrees"
        )
        if self.options is not None:
            self.options.csv.add_data(**{"edge_length_err.1": edge_average})
            self.options.csv.add_data(**{"edge_length_std.1": edge_std})
            self.options.csv.add_data(**{"edge_angle_err.1": angle_average / DEG2RAD})
            self.options.csv.add_data(**{"edge_angle_std.1": angle_std / DEG2RAD})

    def report_errors(self, fit: Sequence[float]) -> None:
        """Log signed mean and standard deviation of edge-length and angle residuals."""
        edge_lengths: list[float] = []
        angles: list[float] = []
        nz = np.nonzero(np.triu(np.array(self.colattice_dotmatrix)))
        for count, (i, j) in enumerate(zip(*nz, strict=False)):
            if i != j:
                angles.append(fit[count])
            else:
                edge_lengths.append(fit[count])
        edge_average, edge_std = float(np.mean(edge_lengths)), float(np.std(edge_lengths))
        scaled_avg = math.copysign(1, edge_average) * np.sqrt(abs(edge_average) * self.scale[1])
        scaled_std = math.copysign(1, edge_std) * np.sqrt(abs(edge_std) * self.scale[1])
        _logger.debug(
            f"Average error in edge length: {scaled_avg:12.5f} +/- {scaled_std:9.5f} Angstroms"
        )
        angle_average, angle_std = float(np.mean(angles)), float(np.std(angles))
        _logger.debug(
            f"Average error in edge angles: {angle_average / DEG2RAD:12.5f} "
            f"+/- {angle_std / DEG2RAD:9.5f} degrees"
        )

    def get_metric_tensor(self) -> None:
        """Compute the standard barycentric metric tensor via Eon's projection."""
        self.metric_tensor = np.dot(
            np.dot(self.lattice_basis, self.eon_projection), self.lattice_basis.T
        )

    def print_edge_count(self) -> str:
        """Initialize zero cocycle coordinates and return comma-joined lattice basis L1 norms."""
        if self.cocycle is not None:
            self.cocycle_rep = np.zeros((self.order - 1, self.ndim))
            self.periodic_rep = np.concatenate((self.cycle_rep, self.cocycle_rep), axis=0)
        else:
            self.periodic_rep = self.cycle_rep
        latt_counts = [int(np.sum(np.abs(j))) for j in self.lattice_basis]
        return ",".join(f"{i}" for i in latt_counts)

    def barycentric_embedding(self) -> None:
        """Compute the zero-cocycle barycentric embedding and standard metric tensor."""
        if self.cocycle is not None:
            self.cocycle_rep = np.zeros((self.order - 1, self.ndim))
            self.periodic_rep = np.concatenate((self.cycle_rep, self.cocycle_rep), axis=0)
        else:
            self.periodic_rep = self.cycle_rep
        self.get_metric_tensor()

    def get_2d_params(self) -> tuple[float, float, float]:
        """Return 2D lattice parameters ``(a, b, gamma_rad)`` from ``projection``."""
        self.metric_tensor = np.dot(
            np.dot(self.lattice_basis, self.projection), self.lattice_basis.T
        )
        lena = math.sqrt(self.metric_tensor[0, 0])
        lenb = math.sqrt(self.metric_tensor[1, 1])
        gamma = math.acos(self.metric_tensor[1, 0] / lena / lenb)
        return lena, lenb, gamma

    def get_3d_params(self) -> tuple[float, float, float, float, float, float]:
        """Return 3D unit-cell parameters ``(a, b, c, alpha, beta, gamma)`` in radians."""
        if self.ndim == 2:
            lena = math.sqrt(self.metric_tensor[0, 0])
            lenb = math.sqrt(self.metric_tensor[1, 1])
            lenc = float(self.options.third_dimension)
            alpha = np.pi / 2.0
            beta = np.pi / 2.0
            gamma = math.acos(self.metric_tensor[0, 1] / lena / lenb)
        else:
            lena = math.sqrt(self.metric_tensor[0, 0])
            lenb = math.sqrt(self.metric_tensor[1, 1])
            lenc = math.sqrt(self.metric_tensor[2, 2])
            alpha = math.acos(self.metric_tensor[1, 2] / lenb / lenc)
            beta = math.acos(self.metric_tensor[0, 2] / lena / lenc)
            gamma = math.acos(self.metric_tensor[0, 1] / lena / lenb)
        return lena, lenb, lenc, alpha, beta, gamma

    def vertex_positions(
        self,
        edges: list[Any],
        used: list[Any],
        pos: dict[str, np.ndarray] = {},  # noqa: B006 (DEF-010 frozen signature)
        bad_ones: dict[Any, Any] = {},  # noqa: B006
    ) -> dict[str, np.ndarray]:
        """Recursively assign fractional unit-cell positions to vertices along ``edges``."""
        lattice_arcs = self.lattice_arcs
        if self.ndim == 2:
            lattice_arcs = np.hstack(
                (np.array(lattice_arcs), np.zeros((np.array(lattice_arcs).shape[0], 1)))
            )
        if len(pos) == self.graph.order():
            return pos
        e = edges[0]
        if e[0] not in pos and e[1] not in pos:
            pass
        elif e[0] not in pos or e[1] not in pos:
            from_v = e[0] if e[0] in pos else e[1]
            to_v = e[1] if e[1] not in pos else e[0]

            coeff = 1.0 if e in self.out_edges(from_v) else -1.0
            index = self.get_index(e)

            to_pos = coeff * np.array(lattice_arcs)[index] + pos[from_v]
            to_pos = np.array([i % 1 for i in to_pos])
            pos.update({to_v: to_pos})
            used.append(e)
            ee = self.neighbours(to_v)
            newedges = [i for i in ee if i not in used and i not in edges]
            edges = newedges + edges[1:]
        else:
            used.append(e)
            edges = edges[1:]
        return self.vertex_positions(edges, used, pos, bad_ones)

    def indices_with_voltage(self, volt: np.ndarray) -> tuple[np.ndarray, ...]:
        """Return indices of rows in ``self.cycle_rep`` matching ``volt``."""
        return np.where([np.all(i == volt) for i in self.cycle_rep])

    def is_integral(self, vect: np.ndarray) -> bool:
        """Return ``True`` if ``vect`` is non-zero and every component is an exact integer."""
        return bool(np.all(np.equal(np.mod(vect, 1), 0)) and not np.all(np.equal(0, vect)))

    @property
    def kernel(self) -> np.ndarray:
        """Basis of the kernel space combining zero-voltage cycle vectors and cocycles."""
        if hasattr(self, "_kernel"):
            return self._kernel
        kernel_vectors: list[np.ndarray] = []
        max_count = self.shape - self.ndim - (self.order - 1)
        if max_count == 0:
            self._kernel = self.cocycle.copy()
            return self._kernel
        j = sy.Matrix(self.cycle_rep.T)
        null = np.array([np.array(k).flatten() for k in j.nullspace()], dtype=float)
        for null_vector in null:
            nz = np.nonzero(null_vector)
            cv_comb = np.sum(self.cycle[nz] * null_vector[nz][:, None], axis=0)
            if self.is_integral(cv_comb):
                kernel_vectors.append(cv_comb)
            if len(kernel_vectors) >= max_count:
                break
        # Fallback traversal over linearly independent zero-voltage cycles (slow on large graphs).
        if len(kernel_vectors) != max_count:
            _logger.warning(
                "The number of vectors in the kernel does not match the size of the graph!"
            )
            edge_list = list(self.graph.edges)
            cycle_vect: list[list[tuple[str, str, str, int]]] = []
            for row in self.cycle:
                vect_temp: list[tuple[str, str, str, int]] = []
                for idx in range(len(row)):
                    if row[idx] != 0:
                        x, y, z = edge_list[idx]
                        vect_temp.append((x, y, z, int(row[idx])))
                cycle_vect.append(vect_temp)

            c = iter(cycle_vect)
            while len(kernel_vectors) < max_count:
                try:
                    cycle = next(c)
                except StopIteration:
                    self._kernel = self.cocycle.copy()
                    return self._kernel
                vect = np.zeros(self.shape)
                vect[self.return_indices(cycle)] = self.return_coeff(cycle)
                volt = self.get_voltage(vect)
                if np.allclose(np.abs(volt), np.zeros(3)) and self.check_linear_dependency(
                    vect, np.array(kernel_vectors)
                ):
                    kernel_vectors.append(vect)
        try:
            self._kernel = np.concatenate((np.array(kernel_vectors), self.cocycle))
        except ValueError:
            self._kernel = np.array(kernel_vectors)
        return self._kernel

    def vertices(self, vertex: int | None = None) -> Any:
        """Return all vertex labels, or the single vertex label at index ``vertex``."""
        if vertex is not None:
            return list(self._graph.nodes())[vertex]
        return list(self._graph.nodes())

    def out_edges(self, vertex: str) -> list[tuple[str, str, str]]:
        """Return outgoing ``(u, v, label)`` edges from ``vertex``."""
        return [(i, j, d["label"]) for (i, j, d) in self.graph.out_edges(vertex, data=True)]

    def in_edges(self, vertex: str) -> list[tuple[str, str, str]]:
        """Return incoming ``(u, v, label)`` edges into ``vertex``."""
        return [(i, j, d["label"]) for (i, j, d) in self.graph.in_edges(vertex, data=True)]

    def all_edges(self) -> list[tuple[str, str, str]]:
        """Return all ``(u, v, label)`` edges in the net."""
        return [(i, j, d["label"]) for (i, j, d) in self.graph.edges(data=True)]

    def neighbours(self, vertex: str) -> list[tuple[str, str, str]]:
        """Return all incident outgoing and incoming edges for ``vertex``."""
        return self.out_edges(vertex) + self.in_edges(vertex)

    def loop_edges(self) -> list[tuple[str, str, str]]:
        """Return all self-loop ``(u, u, label)`` edges in the net."""
        return [(i, j, d["label"]) for (i, j, d) in self.graph.edges(data=True) if i == j]

    def add_vertex(self, v: str) -> None:
        """Add node ``v`` to the underlying ``MultiDiGraph``."""
        self.graph.add_node(v)

    def add_edge(self, v1: str, v2: str, name: str) -> None:
        """Add directed edge ``v1 -> v2`` keyed and labeled by ``name``."""
        self.graph.add_edge(v1, v2, label=name, key=name)

    def delete_edge(self, e: Sequence[str]) -> None:
        """Remove edge ``(v1, v2, label)`` from the underlying ``MultiDiGraph``."""
        for v1, v2, d in self._graph.edges(data=True):
            if (v1, v2, d["label"]) == e:
                self._graph.remove_edge(v1, v2, key=d["label"])
                return

        _logger.error(f"could not find the edge ({e[0]}, {e[1]}, {e[2]}) in the graph")
        sys.exit()

    @property
    def minimal(self) -> bool:
        """Return ``True`` if the cycle space dimension equals ``self.ndim``."""
        if len(self.cycle) > self.ndim:
            return False
        if len(self.cycle) == self.ndim:
            return True
        _logger.info(
            "Net is not periodic in the number of desired dimensions. "
            "This feature has not been implemented yet"
        )
        return False

    @property
    def eon_projection(self) -> np.ndarray:
        """Orthogonal projection matrix onto the orthogonal complement of ``kernel``."""
        if not self.minimal:
            d = np.dot(self.kernel, self.kernel.T)
            d_inv = np.array(np.matrix(d).I)  # DEF-011 frozen np.matrix.I
            sub_mat = np.dot(np.dot(self.kernel.T, d_inv), self.kernel)
            return np.identity(self.shape) - sub_mat
        return np.identity(self.shape)

    @property
    def projection(self) -> np.ndarray:
        """Orthogonal projection matrix onto the column space of ``lattice_arcs``."""
        la = self.lattice_arcs
        d = np.dot(la.T, la)
        d_inv = np.array(np.matrix(d).I)  # DEF-011 frozen np.matrix.I
        return np.dot(np.dot(la, d_inv), la.T)

    @property
    def lattice_arcs(self) -> np.ndarray:
        """Fractional edge displacement vectors ``B^{-1} alpha(B)``."""
        return np.dot(self.cycle_cocycle_I, self.periodic_rep)

    @property
    def shape(self) -> int:
        """Number of edges in the net."""
        return int(self._graph.size())

    @property
    def order(self) -> int:
        """Number of vertices in the net."""
        return int(self._graph.order())

    @property
    def graph(self) -> nx.MultiDiGraph:
        """Underlying ``networkx.MultiDiGraph`` instance."""
        return self._graph

    @graph.setter
    def graph(self, g: Any) -> None:
        self._graph = nx.MultiDiGraph(g)

    @property
    def cycle_cocycle_I(self) -> np.ndarray:
        """Cached matrix inverse ``B^{-1}`` of the stacked ``(cycle, cocycle)`` basis."""
        try:
            return self._cycle_cocycle_I
        except AttributeError:
            self._cycle_cocycle_I = np.array(np.matrix(self.cycle_cocycle).I)  # DEF-011 frozen
            return self._cycle_cocycle_I

    @property
    def cycle_cocycle(self) -> np.ndarray:
        """Cached stacked basis matrix ``B`` of ``self.cycle`` and ``self.cocycle``."""
        try:
            return self._cycle_cocycle
        except AttributeError:
            if self.cocycle is None and self.cycle is None:
                raise AttributeError(
                    "Both the cycle and cocycle basis have not been allocated"
                ) from None
            if self.cocycle is None:
                self._cycle_cocycle = self.cycle.copy()
            elif self.cycle is None:
                raise AttributeError("The cycle basis has not been allocated") from None
            else:
                self._cycle_cocycle = np.concatenate((self.cycle, self.cocycle))
            return self._cycle_cocycle
