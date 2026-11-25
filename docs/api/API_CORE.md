# API Reference: Core Encoding, Decoding, and Exceptions (`slices`, `slices.core`, `slices.exceptions`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/__init__.py`](../../src/slices/__init__.py), [`src/slices/core.py`](../../src/slices/core.py), [`src/slices/exceptions.py`](../../src/slices/exceptions.py)

---

## 1. Top-Level Package Interface (`slices`)

The top-level `slices` package uses **PEP 562 lazy attribute loading** (`__getattr__` / `__dir__`) so importing lightweight submodules (such as `slices.exceptions`, `slices.relax_backends`, or `slices.mlip_relaxer`) incurs zero deep-learning startup overhead and does not execute `slices.core`'s import-time `setdefault` environment configuration (`OMP_NUM_THREADS`, `TF_CPP_MIN_LOG_LEVEL`).

### Public Exports (`slices.__all__`)

| Symbol | Loading Mode | Description |
|---|---|---|
| `__version__` | Eager (`"4.0.2"`) | Installed SLICES package version string |
| `SLICESError` and subclasses (12 names) | Eager (from `slices.exceptions`) | Structured exception hierarchy and `XTBExecutionError` alias |
| `SLICES` | Lazy (`__getattr__`) | Main crystal encoder/decoder class from `slices.core` |
| `check_SLICES` | Lazy function wrapper | Validates a SLICES string via `SLICES(relax_model=None).check_SLICES(...)` |

### `slices.check_SLICES`

```python
def check_SLICES(
    slices_str: str,
    strategy: int = 4,
    dupli_check: bool = False,
    graph_rank_check: bool = True,
) -> bool
```

Validates whether `slices_str` satisfies SLICES syntax and 3D quotient-graph constraints without loading any force-field relaxer.

- **Args:**
  - `slices_str`: Input SLICES representation string.
  - `strategy`: Encoding strategy (`1`, `3`, or `4`). Defaults to `4`.
  - `dupli_check`: If `True`, reject duplicate quotient-graph edges rather than deduplicating them. Defaults to `False`.
  - `graph_rank_check`: If `True`, require first Betti number `H1(X, Z) >= 3`. Defaults to `True`.
- **Returns:** `True` if valid; `False` otherwise.

---

## 2. Structured Exception Hierarchy (`slices.exceptions`)

All package exceptions inherit from `SLICESError(Exception)`. They are defined with zero third-party dependencies in `slices.exceptions` and re-exported in both `slices` and `slices.core`.

```text
Exception
└── SLICESError
    ├── SLICESEncodingError(SLICESError, ValueError)   # Crystal-to-SLICES encoding failure
    ├── SLICESDecodingError(SLICESError, ValueError)   # SLICES-to-crystal decoding failure
    ├── GraphTopologyError           # Periodic quotient-graph / net failure
    │   ├── LatticeBasisError        # 3D lattice basis cannot be found
    │   └── CocycleBasisError        # Linearly independent cocycle basis failure
    ├── GFNFFExecutionError          # GFN-FF topology, Z-bounds, or external xtb failure
    │   (alias: XTBExecutionError = GFNFFExecutionError)
    ├── MLIPRelaxationError          # Optional/external MLIP relaxation failure
    ├── TimeoutException             # Wall-clock limit exceeded in function_timeout
    ├── RelaxBackendError(SLICESError, RuntimeError)   # Model compile/load/eval failure
    └── ModelDownloadError(SLICESError, RuntimeError)  # Network weight-download failure
```

### Dual-Inheritance & Sibling Invariant

- Both `SLICESEncodingError` and `SLICESDecodingError` inherit from `(SLICESError, ValueError)` so callers catching either `SLICESError` or standard `ValueError` handle empty structures, malformed SLICES inputs, or unsupported decoding strategies consistently.
- Both `RelaxBackendError` and `ModelDownloadError` inherit from `(SLICESError, RuntimeError)` so callers catching either `SLICESError` or `RuntimeError` handle them consistently.
- `ModelDownloadError` is deliberately a **sibling** of `RelaxBackendError` (`not issubclass(ModelDownloadError, RelaxBackendError)`). In `slices.relax_backends.get_calculator`, transient network download failures therefore propagate without writing permanent `.failed` compilation markers.
- `XTBExecutionError` is an exact identity alias (`XTBExecutionError is GFNFFExecutionError`) for compatibility with pre-v4.0 scripts.

---

## 3. Timeout Decorator & Constants (`slices.core`)

### `slices.core.VALID_GRAPH_METHODS`

```python
VALID_GRAPH_METHODS: tuple[str, ...] = ("econnn", "crystalnn", "brunnernn", "mininn")
```

Exported in `slices.core.__all__`. Passing any `graph_method` outside `VALID_GRAPH_METHODS` raises `ValueError` in `SLICES.__init__`, `SLICES.structure2structure_graph`, and `SLICES.get_dim` (`DEF-026`).

### `slices.core.function_timeout`

```python
def function_timeout(
    seconds: int,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]
```

Enforces a wall-clock timeout using `signal.SIGALRM` whenever `hasattr(signal, "SIGALRM")` and `threading.current_thread() is threading.main_thread()` (Linux and macOS main threads), raising `TimeoutException("Timed out!")` and unconditionally clearing `signal.alarm(0)` in a `finally:` block. On Windows or non-main worker threads, it yields directly without attempting signal registration.

---

## 4. `slices.core.SLICES` Class Reference

`SLICES` implements invertible crystal-structure encoding and reconstruction using labeled quotient graphs (`slices.tobascco_net.Net`), topology-only GFN-FF targets (`slices.gfnff_helper`), ZL* L-BFGS-B optimization, and NequIP or optional MLIP cell relaxation (`slices.relax_backends` / `slices.mlip_relaxer`).

> **Import-Time Environment & Warning Behavior (`DEF-005`, resolved in Wave 1):** Importing `slices.core` defaults `TF_CPP_MIN_LOG_LEVEL` to `"3"` and `OMP_NUM_THREADS` to `"1"` via `os.environ.setdefault(...)` — preserving single-thread defaults when unset while honoring explicit user overrides. It no longer sets `PYTHONWARNINGS="ignore"` or blanket warning filters; instead, `DeprecationWarning` filtering is scoped strictly to `module=r"^spglib\."`, `BrunnerNNReciprocal` is imported before legacy aliases, and `relax_backends._cell_filter` locally suppresses ASE's `ExpCellFilter` `DeprecationWarning`. See [API_CONFIG.md](API_CONFIG.md) and [DEFERRED_CORE_REGISTER.md](../migration/DEFERRED_CORE_REGISTER.md).

### 4.1 Initialization & Context Helpers

```python
class SLICES:
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
    ) -> None
```

| Parameter | Default | Description |
|---|---|---|
| `atom_types` | `None` | 1D integer array of atomic numbers `Z` |
| `edge_indices` | `None` | `(E, 2)` integer array of directed quotient-graph edges |
| `to_jimages` | `None` | `(E, 3)` integer array of periodic image translation vectors |
| `graph_method` | `"econnn"` | Local-environment bond finder in `VALID_GRAPH_METHODS` (`"econnn"`, `"crystalnn"`, `"brunnernn"`, or `"mininn"`); raises `ValueError` otherwise (`DEF-026`) |
| `check_results` | `False` | Write intermediate debug artifacts (`graph.png`, `testBonds_cut.top`, `gfnff_lists.json`, `inner_p_target.json`) and print `func_check` output |
| `optimizer` | `"BFGS"` | ASE optimizer for final cell relaxation: `"BFGS"`, `"LBFGS"`, `"FIRE"`, or `"FIRE+BFGS"` |
| `fmax` | `0.2` | Maximum atomic force convergence threshold (eV/Angstrom) |
| `steps` | `100` | Maximum optimization steps |
| `relax_model` | `"auto"` | Force-field backend: `"auto"` (resolves to `"nequip-s+l"` on CPU), `"nequip-s+l"`, `"nequip-m+l"`, `"nequip-l"`, `None`/`"none"`, or optional MLIP (`"chgnet"`, `"mattersim"`, `"orbv3"`, `"mace"`, `"m3gnet"`). Resolved backend name is stored in `self.relax_model`; relaxer instance (or `None`) is stored in `self.relaxer`. |

- `suppress_output(self) -> Iterator[None]` (`@contextmanager`): Redirects `sys.stdout` and `sys.stderr` to `os.devnull` within a `with` block.
- `get_index_list_allow_duplicates(ori: list[Any], mod: list[Any]) -> list[int]` (`@staticmethod`): Maps elements of `ori` to matching indices in `mod` preserving duplicate multiplicity.

### 4.2 Graph Construction, Element/Dimensionality Checks & Encoding

| Method | Signature | Description |
|---|---|---|
| `check_element` (`@staticmethod`) | `(structure: Structure) -> bool` | Returns `True` iff `max(structure.atomic_numbers) < 87` (legacy86 boundary `Z <= 86`; see `DEF-006`). Raises `SLICESEncodingError` (also `ValueError`) if `len(structure) == 0` (`DEF-018`). |
| `check_2D` | `(self, structure: Structure) -> bool` | Returns `True` iff all connected graph components have Larsen dimensionality `2`. |
| `check_3D` | `(self, structure: Structure) -> bool` | Returns `True` iff the structure forms a single connected 3D network (`dim == 3` and `len(components) == 1`). |
| `get_dim` | `(self, structure: Structure) -> int` | Computes structural dimensionality via `pymatgen.analysis.dimensionality.get_dimensionality_larsen`. Raises `ValueError` if `self.graph_method` is not in `VALID_GRAPH_METHODS`. |
| `cif2structure_graph` | `(self, string: str) -> tuple[StructureGraph, Structure]` | Parses a CIF string and returns `(StructureGraph, Structure)`. |
| `structure2structure_graph` | `(self, structure: Structure) -> StructureGraph` | Constructs a `StructureGraph` using `self.graph_method` via `StructureGraph.from_local_env_strategy`. Raises `SLICESEncodingError` on 0-site structures (`DEF-018`) and `ValueError` on invalid `graph_method` (`DEF-026`). |
| `to_primitive_if_smaller` (`@staticmethod`) | `(structure: Structure) -> Structure` | Reduces `structure` to its primitive standard cell via `SpacegroupAnalyzer` if that lowers atom count while preserving reduced formula; otherwise returns `structure`. Raises `SLICESEncodingError` if `len(structure) == 0` (`DEF-018`). |
| `from_cif` | `(self, string: str) -> None` | Parses a CIF string, reduces to primitive cell if smaller, and populates `atom_types`, `edge_indices`, `to_jimages`, and `space_group_num`. |
| `structure2crystal_graph_rep` | `(self, structure: Structure) -> tuple[np.ndarray, np.ndarray, np.ndarray, int | None]` | Converts `structure` (with primitive-cell pre-reduction fallback) into `(atom_types, edge_indices, to_jimages, space_group_num)`. |
| `structure2SLICES` | `(self, structure: Structure, strategy: int = 4) -> str` | Encodes `structure` into a SLICES string using `strategy` (`1`, `2`, `3`, or `4`). Raises `SLICESEncodingError` on 0-site structures. |
| `structure2randomSLICES` | `(self, structure: Structure, strategy: int = 4, num: int = 50, shuffle_atom_order: bool = True, shuffle_bond_order: bool = True, flip_bonds: bool = True, batch_multiplier: int = 10) -> list[str]` | Generates up to `num` deduplicated randomly augmented SLICES strings. Set `PYTHONHASHSEED=0` alongside `random.seed(...)` for cross-process list-order reproducibility (`DEF-022`). |
| `structure2SLICESAug_atom_order` | `(self, structure: Structure, strategy: int = 4, num: int = 50) -> list[str]` | Convenience wrapper calling `structure2randomSLICES` with `shuffle_atom_order=True`, `shuffle_bond_order=False`, and `flip_bonds=False`. |

### 4.3 Parsing, Serialization, Validation & Canonicalization

| Method | Signature | Description |
|---|---|---|
| `from_SLICES` | `(self, SLICES: str, strategy: int = 4, fix_duplicate_edge: bool = True) -> None` | Parses a Strategy `1`, `3`, or `4` SLICES string into `self.atom_types`, `self.atom_symbols`, `self.edge_indices`, `self.to_jimages`, and `self.space_group_num`, resetting `self.unstable_graph = False` (`DEF-023`). Raises `SLICESDecodingError` (also `ValueError`) for unsupported strategies (including encode-only `strategy=2`) or strings lacking numeric edge tokens/complete edges, and enforces `0 <= idx < num_atoms` and 3-char Strategy-4 edge labels (`DEF-024`). |
| `to_SLICES` | `(self, strategy: int = 4) -> str` | Serializes stored graph arrays via `get_slices_by_strategy`. |
| `get_slices_by_strategy` | `(self, strategy: int, atom_symbols: list[str], edge_indices: np.ndarray, to_jimages: np.ndarray, space_group_num: int | None) -> str` | Dispatches serialization to `get_slices1`, `get_slices2`, `get_slices3`, or `get_slices4`; raises `ValueError` for unknown strategy. |
| `get_slices1` / `get_slices2` / `get_slices3` (`@staticmethod`) | `(atom_symbols, edge_indices, to_jimages, space_group_num: int | None = None) -> str` | Format-specific serializers (Strategy `1` interleaved, Strategy `2` fixed-width unspaced encode-only, Strategy `3` atom header + spaced labels). |
| `get_slices4` (`@staticmethod`) | `(atom_symbols, edge_indices, to_jimages, space_group_num: int | None) -> str` | Strategy `4` serializer: optional tokenized Wyckoff space-group prefix (`utils_wyckoff.get_tokenized_enc`) + atom symbols + compact `o`/`+`/`-` image triplets. |
| `check_structural_validity` (`@staticmethod`) | `(str1: IStructure) -> bool` | Enforces `isinstance(str1, IStructure)` (`TypeError`), returns `False` on 0-site structures, and checks all distinct site and periodic self-image distances via `str1.get_neighbor_list(r=0.5 + 1e-9)` excluding `(i == j) & (img == 0)` (`True` iff all exceed `0.5` Angstrom; `DEF-025`, `DEF-019` Part 2). |
| `check_SLICES` | `(self, SLICES: str, strategy: int = 4, dupli_check: bool = False, graph_rank_check: bool = True) -> bool` | Full syntax, connectivity, duplicate-edge, `H1(X, Z) >= 3`, and `Net` basis validation. Returns `bool` without raising. |
| `check_SLICES_basic` | `(self, SLICES: str, strategy: int = 4) -> bool` | Lightweight syntax and node-coverage check (for encoding verification). |
| `get_canonical_SLICES` | `(self, SLICES: str, strategy: int = 4) -> str` | Sorts atoms, edges, and periodic image signs into canonical form. |
| `SLICES2formula` | `(self, SLICES: str) -> str | None` | Grammar-aware extraction of the compact chemical formula from Strategy `1`, `2`, `3`, or `4` SLICES strings; returns `None` cleanly on malformed or digit-free inputs (`DEF-012`). |
| `SLICES2space_group_number` | `(self, SLICES: str, strategy: int = 4, fix_duplicate_edge: bool = True) -> int | None` | Reconstructs the zero-cocycle barycentric net placement (stateless across instance reuse; `DEF-023`) and returns its international space-group number (`1..230`) via `SpacegroupAnalyzer`, or `None` on failure. |

### 4.4 GFN-FF Geometry Targets & ZL* Optimization Internals

| Method | Signature | Description |
|---|---|---|
| `get_nbf_blist` | `(self) -> tuple[str, np.ndarray]` | Builds the `3x3x3` supercell NBF neighbor table (`testBonds_cut.top` text, capped at 19 neighbors per site) and central-cell 1-based bond list `blist`. |
| `get_inner_p_target` | `(self, bond_scaling: float = 1.05) -> tuple[np.ndarray, list[list[int]], list[float]] | None` | Calls `slices.gfnff_helper.run_gfnff_helper` (skipping non-finite `vangl` entries; `DEF-030`) and builds `(inner_p_target, colattice_inds, colattice_weights)`. Returns `None` on failure. |
| `get_inner_p_target_debug` | `(self, bond_scaling: float = 1.05) -> tuple[np.ndarray, list[list[int]], list[float]]` | Debug variant (also guarding non-finite `vangl`; `DEF-030`) that writes `testBonds_cut.top` and `gfnff_lists.json` via `write_debug_files`. |
| `convert_graph` | `(self) -> tuple[list[tuple[str, str, dict[str, str]]], np.ndarray]` | Converts stored edges and image translations into `Net` input edge tuples (1-based `'e1'`, `'e2'`, ...) and voltage matrix. |
| `get_uncovered_pair` (`@staticmethod`) | `(graph: nx.Graph) -> list[list[Any]]` | Returns 0-based upper-triangular atom index pairs not directly bonded in `graph` (canonicalizing bonded edges as `(min(u, v), max(u, v))`; `DEF-032`). |
| `get_uncovered_pair_lj` / `get_covered_pair_lj` | `(self, ...) -> list[list[float]]` | Retrieves Lennard-Jones `[cutoff, sigma]` lengths (in Angstrom) from `slices.config.LJ_PARAMS_LIST`. *(Preserves frozen v4.0.2 indexing; see `DEF-001`.)* |
| `get_rescaled_lattice_vectors` | `(self, inner_p_target, inner_p_std, lattice_vectors_std, arc_coord_std) -> np.ndarray` | Anisotropically rescales barycentric lattice vectors using GFN-FF bond lengths and updates `self.unstable_graph`. |
| `get_coordinates` (`@staticmethod`) | `(arc_coord, num_nodes, shortest_path_spanning_graph, spanning) -> np.ndarray` | Integrates fractional vertex positions along the spanning tree rooted at `'1'`. |
| `convert_params` (`@staticmethod`) | `(x, ndim, cocycle_size, lattice_type, metric_tensor_std) -> tuple[np.ndarray, np.ndarray | None]` | Unpacks flat ZL* vector `x` into `(metric_tensor, cocycle_rep)`. |
| `initialize_x_bounds` (`@staticmethod`) | `(ndim, cocycle_rep, metric_tensor_std, lattice_type, delta_theta, delta_x, lattice_expand, lattice_shrink) -> tuple[np.ndarray, list[tuple[float, float]]]` | Builds initial parameter vector `x` and L-BFGS-B box bounds. |
| `all_distances` (`@staticmethod`) | `(coords1: Any, coords2: Any) -> np.ndarray` | Pairwise Euclidean distance matrix between Cartesian coordinate arrays. |
| `func` / `func_check` | `(self, x, ...) -> float` | ZL* inner-product + Lennard-Jones repulsion objective (`func_check` prints per-term diagnostics using the same `1e-10` / `1e-8` distance clamps as `func`; `DEF-027`). |

### 4.5 Decoding, Relaxation, Matching & Opt-In Robust Decoding

| Method | Signature | Description |
|---|---|---|
| `to_structures` | `(self, bond_scaling: float = 1.05, delta_theta: float = 0.005, delta_x: float = 0.45, lattice_shrink: float = 1, lattice_expand: float = 1.25, angle_weight: float = 0.5, vbond_param_ave_covered: float = 0.0, vbond_param_ave: float = 0.01, repul: bool = True) -> tuple[list[Structure], float]` | Runs `Net` basis + GFN-FF target + L-BFGS-B ZL* optimization + force-field relaxation. Raises `LatticeBasisError` if `net.get_lattice_basis() == -1` (or `net.lattice_basis is None`) and `CocycleBasisError` if a multi-vertex graph (`net.order > 1`) lacks a full-rank cocycle basis (`DEF-021` Wave 1). Returns `([std, opt, opt2], energy_per_atom)`, or `([std, opt], 0)` cleanly when `self.relaxer is None` (`DEF-013`) or relaxation fails. |
| `SLICES2structure` | `(self, SLICES: str, strategy: int = 4, fix_duplicate_edge: bool = True) -> tuple[Structure, float]` | Calls `from_SLICES` then `to_structures()` and returns `(structures[-1], final_energy_per_atom)`. |
| `robust_SLICES2structure` | `(self, SLICES: str, strategy: int = 4, fix_duplicate_edge: bool = True, n_starts: int = 3, seed: int = 0) -> tuple[Structure, float]` | **Opt-in** multi-stage recovery decoder delegating lazily to `slices.decoding_strategies.robust_decode`. Never called by default `SLICES2structure` / `to_structures`. See [API_DECODING_STRATEGIES.md](API_DECODING_STRATEGIES.md). |
| `to_relaxed_structure` | `(self, ...) -> tuple[Structure, float]` | Calls `to_structures(...)` and raises `Exception("relax failed")` if fewer than 3 structures were returned. |
| `to_4structures` | `(self, ...) -> tuple[list[Structure], float]` | Returns `([std, std2, opt, opt2], energy_per_atom)` including direct relaxation of `std`, or `(structures, final_energy_per_atom)` cleanly when `self.relaxer is None` (`DEF-013`). |
| `relax` / `relax_large_cell1` / `relax_large_cell2` | `(self, struc: Structure) -> tuple[Structure, float]` | Cell-size-dispatched relaxers decorated with `@function_timeout` (`360 s` for `<= 20` atoms, `720 s` for `21..40` atoms, `2000 s` for `> 40` atoms). All three methods forward `fmax=self.fmax, steps=self.steps` consistently to `self.relaxer.relax(...)` (`DEF-008`). |
| `match_check` | `(self, ori, opt, std, ltol=0.2, stol=0.3, angle_tol=5) -> tuple[str, str, str, str]` | Compares `opt` and `std` against `ori` via POSCAR-normalized `StructureMatcher(..., comparator=ElementComparator())` and graph Jaccard distance. |
| `match_check3` | `(self, ori, opt2, opt, std, ltol=0.2, stol=0.3, angle_tol=5) -> tuple[str, str, str, str, str, str]` | Compares `opt2`, `opt`, and `std` against `ori` (returns 3 binary `'0'`/`'1'` match flags + 3 Jaccard distance strings). |
| `match_check4` | `(self, ori, opt2, opt, std2, std, ltol=0.2, stol=0.3, angle_tol=5) -> tuple[str, str, str, str, str, str, str, str]` | Compares `opt2`, `opt`, `std2`, and `std` against `ori`. |

### Minimal Usage Example

```python
from pymatgen.core import Structure
from slices import SLICES, check_SLICES

structure = Structure.from_file("examples/NdSiRu.cif")
encoder = SLICES(relax_model=None)  # Zero MLIP overhead for encoding/validation
slices_str = encoder.structure2SLICES(structure, strategy=4)
assert check_SLICES(slices_str)

decoder = SLICES(relax_model="auto")  # CPU default: nequip-s+l
reconstructed, energy_per_atom = decoder.SLICES2structure(slices_str)
```
