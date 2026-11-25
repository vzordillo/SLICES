# API Reference: Periodic Graph Theory, GFN-FF Topology, and Wyckoff Encoding (`slices.tobascco_net`, `slices.gfnff_helper`, `slices.utils_wyckoff`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/tobascco_net.py`](../../src/slices/tobascco_net.py), [`src/slices/gfnff_helper.py`](../../src/slices/gfnff_helper.py), [`src/slices/utils_wyckoff.py`](../../src/slices/utils_wyckoff.py)

---

## 1. Periodic Quotient Graphs (`slices.tobascco_net`)

Adapted from Boyd & Woo's `tobascco` graph-theoretic net-embedding algorithms (Eon's barycentric placement and metric-tensor projection). Core topological basis selection (`DEF-003`) remains strictly frozen at upstream SLICES v4.0.2 (`0.0` ULP drift), while Wave 1 eliminated all `np.matrix` usage (`np.linalg.inv`, `DEF-011`), dead `np.random` mutations (`DEF-004`), mutable default arguments (`DEF-010`), and rectangular bounds overflows (`DEF-034`).

### Public Exports (`slices.tobascco_net.__all__`)

`DEG2RAD` (`np.pi / 180.0`), `Net`, `SystreDB`.

### `SystreDB(dict[Any, Any])`

Dictionary-backed parser for crystallographic net archives in Systre `.arc` format.

| Method | Signature | Description |
|---|---|---|
| `__init__` | `(self, filename: str | None = None) -> None` | Optionally parses `filename` via `read_store_file`. |
| `read_store_file` | `(self, file: str | None = None) -> None` | Parses all net blocks from `.arc` file into dictionary entries. |
| `get_key` | `(self, block: Sequence[str]) -> tuple[int, list[tuple[int, ...]]] | None` | Extracts `(dim, edge_tuples)` from a block's `key` line. |
| `get_name` | `(self, block: Sequence[str]) -> str | UUID` | Extracts the `id` token or generates a fallback UUID. |
| `Nd_chunks` | `(self, values: Sequence[int], dim: int) -> Iterator[tuple[int, ...]]` | Yields `(2 + dim)`-element chunks. |
| `gen_networkx_graph_format` | `(self, edges: Sequence[tuple[int, ...]], dim: int = 3) -> tuple[list[tuple[str, str, dict[str, str]]], list[tuple[int, ...]]]` | Builds NetworkX multi-edge tuples and voltage vectors. |
| `gen_sage_graph_format` | `(self, edges: Sequence[tuple[int, ...]]) -> tuple[dict[str, dict[str, list[str]]], list[tuple[int, int, int]]]` | Legacy 3D Sage adjacency dictionary converter. |

### `Net`

```python
class Net:
    def __init__(
        self,
        graph: Sequence[tuple[str, str, dict[str, Any]]] | None = None,
        dim: int = 3,
        options: Any = None,
    ) -> None
```

#### Core Basis, Projection & Embedding Methods

| Symbol | Kind / Signature | Description |
|---|---|---|
| `simple_cycle_basis` | `(self) -> None` | Builds fundamental cycle basis (`self.cycle`) and cycle voltages (`self.cycle_rep`) from a minimum spanning tree without touching global `np.random` (`DEF-004`). |
| `get_cycle_basis` | `(self) -> None` | Builds cycle basis of rank `E - V + 1` via `iter_cycles`. |
| `get_lattice_basis` | `(self) -> int` | Uses SymPy rational nullspace arithmetic (with zero `np.random` state mutation; `DEF-004`) to find `ndim` integral cycle combinations spanning unit lattice translations. Returns `1` on success and `-1` on failure (`DEF-003`, `DEF-021`). |
| `get_cocycle_basis` | `(self) -> None` | Constructs oriented cutset basis (`self.cocycle`, `self.cocycle_rep`) of size `V - 1` (`None` when `V == 1`). |
| `get_metric_tensor` | `(self) -> None` | Computes barycentric metric tensor `L @ eon_projection @ L.T`. |
| `barycentric_embedding` | `(self) -> None` | Sets zero cocycle coordinates (`periodic_rep`) and computes standard metric tensor. |
| `get_2d_params` / `get_3d_params` | `(self) -> tuple[float, ...]` | Extracts 2D `(a, b, gamma)` or 3D `(a, b, c, alpha, beta, gamma)` cell parameters in radians. |
| `is_integral` | `(self, vect: np.ndarray) -> bool` | Exact integer-entry check (`np.mod(vect, 1) == 0` and non-zero). |
| `clear_cache` | `(self) -> None` | **Additive:** Deletes cached `_kernel`, `_cycle_cocycle`, `_cycle_cocycle_I` and resets computed basis/metric arrays to `None` while retaining `self._graph`. |
| `nodes_iter` / `edges_iter` | `(self, data: bool = True) -> Iterator[Any]` | NetworkX 3.x-compatible node (`self._graph.nodes[node]`) and edge iterators. |

#### Key Algebraic Properties

| Property | Return Type | Mathematical Definition |
|---|---|---|
| `graph` (get/set) | `nx.MultiDiGraph` | Underlying directed multigraph (`order` = `V`, `shape` = `E`) |
| `minimal` | `bool` | `True` iff cycle space dimension equals `self.ndim` |
| `kernel` | `np.ndarray` | Stacked basis of zero-voltage cycles and cocycles |
| `eon_projection` | `np.ndarray` | Orthogonal projector `I - K^T (K K^T)^{-1} K` onto `ker(alpha)^perp` (uses `np.linalg.inv`, zero `np.matrix`; `DEF-011`) |
| `cycle_cocycle` | `np.ndarray` | Stacked `(E, E)` basis matrix `B = [cycle; cocycle]` |
| `cycle_cocycle_I` | `np.ndarray` | Cached matrix inverse `B^{-1}` computed via `np.linalg.inv` (`DEF-011`) |
| `lattice_arcs` | `np.ndarray` | Fractional edge displacement vectors `B^{-1} @ periodic_rep` |
| `projection` | `np.ndarray` | Orthogonal projector onto column space of `lattice_arcs` (uses `np.linalg.inv`; `DEF-011`) |

Additional graph utilities on `Net`: `vertices`, `out_edges`, `in_edges`, `all_edges`, `neighbours`, `loop_edges`, `add_vertex`, `add_edge`, `delete_edge`, `insert_and_join`, `add_edges_between`, `get_voltage`, `get_index` (expects 1-based `'e1'`, `'e2'`, ... labels), `return_indices`, `return_coeff`, `to_ind`, `indices_with_voltage`, `iter_cycles` (stateless `None` default containers; `DEF-010`), `linear_independent_vectors` (`np.atleast_2d(np.asarray(...))` with `r == 0` and `counter < r - 1` bounds guards; `DEF-034`), `check_linear_dependency`, `cycle_cocycle_check`, `assign_ip_matrix`, `convert_params`, `vertex_positions` (stateless `None` default containers; `DEF-010`), `print_edge_count`, `report_errors`, `report_errors_nlopt`, `add_to_array`, `add_name`, `debug_print`.

---

## 2. Topology-Only GFN-FF Helper (`slices.gfnff_helper`)

Computes equilibrium bond-length and angle targets (`blist`, `vbond`, `alist`, `vangl`) from the `testBonds_cut.top` NBF neighbor table built by `SLICES.get_nbf_blist`.

### Public Exports (`slices.gfnff_helper.__all__`)

`LEGACY86_PARAM_FILE`, `parse_nbf_text`, `run_gfnff_helper`, `write_debug_files`.

### Execution Backends & Cross-Platform Fallback

1. **Linux x86_64 Default (Untouched Upstream v4.0.2 + `1 <= Z <= 103` Guard):** Loads the bundled open-source `pprcht/gfnff` shared library (`src/slices/_vendor/gfnff/libgfnff.so.0.1.1`, LGPL-3.0-or-later) in memory via `ctypes` with `param_gfnff_legacy86.xtb` overlay (`Z = 1..86` matching historical xtb targets; `Z = 87..103` using modern library parameters). Atomic numbers outside `1 <= Z <= 103` (e.g., trans-lawrencium `Rf..Og`) are rejected in `parse_nbf_text` with `GFNFFExecutionError` before invoking `libgfnff.so.0.1.1` (`DEF-028`).
2. **Non-Linux Fallback (`RUL-08`):** Only if importing/loading `slices._vendor.gfnff` raises `(ImportError, OSError)` (e.g., on macOS or Windows), `run_gfnff_helper` invokes `_run_external_xtb_fallback(nbf_text)`. It resolves an external modified `xtb` binary from `SLICES_XTB_PATH`, `XTB_MOD_PATH`, or `PATH` (`xtb_noring_nooutput_nostdout_noCN`), runs `subprocess.run(..., shell=False, timeout=30)` inside a `tempfile.TemporaryDirectory`, sanitizes Fortran `"********"` overflow fields, and raises `GFNFFExecutionError` with actionable setup guidance if no binary is configured.

### Functions & Constants

| Symbol | Signature / Value | Description |
|---|---|---|
| `LEGACY86_PARAM_FILE` | `Path(.../_vendor/gfnff_extra/param_gfnff_legacy86.xtb)` | Default 86-element overlay parameter table |
| `parse_nbf_text` | `(nbf_text: str) -> tuple[np.ndarray, np.ndarray]` | Parses `testBonds_cut.top` (`nat`, element symbols, 20 neighbor rows) into `(int32 Z array, (20, nat) int32 neighbor table)`. Raises `ValueError` on malformed line/shape counts or unrecognized element symbols, and raises `GFNFFExecutionError` if any atomic number lies outside `1 <= Z <= 103` (`H..Lr`; `DEF-028`). |
| `run_gfnff_helper` | `(nbf_text: str) -> dict[str, Any]` | Returns `{"blist": ..., "vbond": ..., "alist": ..., "vangl": ..., "metadata": {"param_mode": ...}}` with 1-based atom indices. |
| `write_debug_files` | `(nbf_text: str, data: dict[str, Any], directory: str | os.PathLike[str] = ".") -> None` | Writes `testBonds_cut.top` and `gfnff_lists.json` for `SLICES(check_results=True)`. |

Self-test CLI: `python -m slices.gfnff_helper` (verifies methane topology and `Na3MnCoNiO6` reference target `(178.74144, 178.74144, 126, 61.23)`).

---

## 3. Space-Group Wyckoff Token Encoding (`slices.utils_wyckoff`)

Provides a verified exact bijection between all 230 international crystallographic space groups (`1..230`, covering all 6 centering types `P`, `I`, `F`, `C`, `A`, `R`) and collision-free Strategy-4 letter tokens (zero overlap with `pymatgen.core.Element` symbols).

### Public Exports (`slices.utils_wyckoff.__all__`)

| Symbol | Signature / Type | Description |
|---|---|---|
| `sg_encoding` | `dict[str, dict[str, Any]]` | Frozen 250-entry mapping from Hermann-Mauguin space-group symbols to `{"enc", "full_symbol", "int_number", "order", "patterson_symmetry", "point_group", ...}`. |
| `tokenize_enc` | `(enc_string: str) -> str` | Converts a raw encoding string into space-separated Strategy-4 prefix tokens (`o`/`+` inversion flag, lattice/centering code, symmetry operations). |
| `get_tokenized_enc` | `(int_number: int) -> str` | Returns the Strategy-4 space-separated token prefix for space group `1 <= int_number <= 230`. Raises `ValueError` outside `1..230`. |
| `get_space_group_num` | `(enc: str) -> int` | Looks up the international space-group number (`1..230`) for raw `enc`. Raises `ValueError` if not found. |
| `get_space_group_num_from_letter_enc` | `(letter_enc: str) -> int` | Decodes a concatenated Strategy-4 token prefix (`"".join(tokens)`) back to its space-group number (`1..230`). Raises `ValueError` on invalid prefixes. |
