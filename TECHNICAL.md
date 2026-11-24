# SLICES Technical Architecture Guide

This document describes the internal architecture, mathematical pipeline, force-field relaxation backends, cross-platform boundaries, and baseline invariance guarantees of **SLICES v4.0.2** (`slices-4-personal`). For symbol-level signatures and defaults, consult the [API Reference](docs/README.md#api-reference).

---

## 1. Module Architecture and Import Boundaries

### Package Layout

| Module | Role | Startup Characteristics |
|---|---|---|
| `src/slices/__init__.py` | Public facade exporting `__version__`, `slices.exceptions`, lazy `SLICES`, and lazy `check_SLICES` | PEP 562 `__getattr__`; `< 1 ms`, zero scientific imports or environment mutations |
| `src/slices/exceptions.py` | Package exception hierarchy rooted at `SLICESError` | Zero external dependencies |
| `src/slices/core.py` | `SLICES` encoder/decoder class and `function_timeout` | Sets `OMP_NUM_THREADS="1"`, `TF_CPP_MIN_LOG_LEVEL="3"`, and warning filters before scientific imports (frozen per `DEF-005`) |
| `src/slices/tobascco_net.py` | Periodic quotient-graph `Net` topology, cycle/cocycle bases, Eon projection, and `SystreDB` | NetworkX, NumPy, SymPy |
| `src/slices/gfnff_helper.py` | Topology-only GFN-FF bond/angle generator (`libgfnff.so` on Linux x86\_64; external `xtb` fallback elsewhere) | Lazy `_vendor.gfnff` load on call |
| `src/slices/relax_backends.py` | Built-in NequIP-OAM compilation, caching, overlap pre-optimization, and cell-collapse recovery | Lazy `torch`/`nequip`/`ase` imports inside functions |
| `src/slices/mlip_relaxer.py` | Opt-in adapters for `chgnet`, `mattersim`, `orbv3`, `mace`, and legacy `m3gnet` | Zero module-level `torch`/`tensorflow`/`keras` imports or global env mutations |
| `src/slices/decoding_strategies.py` | Opt-in multi-stage recovery decoding (`robust_decode`, multi-start ZL\*, progressive relaxation) | Imported only when caller invokes `SLICES.robust_SLICES2structure` or `slices decode --robust` |
| `src/slices/cli.py` | Command-line interface (`slices` / `python -m slices.cli`) | Lazy `slices.core` import per subcommand |
| `src/slices/utils.py` | Scoped local/SLURM batch runner (`splitRun*`, `show_progress`, `cancel_all_jobs`), collectors, binning, multiprocessing | Scoped `_SUBMITTED_LOCAL_PROCS` and `_SUBMITTED_SLURM_JOBS` |
| `src/slices/utils_wyckoff.py` | 230 space-group `sg_encoding` table and lossless Strategy-4 tokenization | Pure Python (`re` only) |
| `src/slices/config.py` | Frozen `OFFSET`, `LJ_PARAMS_LIST`, and `PERIODIC_DATA` constants | NumPy / Pandas |

### Lazy Top-Level Loading (PEP 562)

`src/slices/__init__.py` eagerly imports only `__version__ = "4.0.2"` and the exception classes from `slices.exceptions`. Accessing `slices.SLICES` triggers `__getattr__` to import `slices.core.SLICES` on demand, and calling `slices.check_SLICES(...)` lazily instantiates `SLICES(relax_model=None)`. Consequently, CLI inspection commands (`python -m slices.relax_backends`), exception imports, and lightweight utilities do not execute `core.py`'s module-level `OMP_NUM_THREADS="1"` assignment or import `pymatgen`/`scipy`/`matplotlib`.

### Exception Hierarchy

All package exceptions inherit from `SLICESError`:

```text
Exception
└── SLICESError
    ├── SLICESEncodingError
    ├── SLICESDecodingError
    ├── GraphTopologyError
    │   ├── LatticeBasisError
    │   └── CocycleBasisError
    ├── GFNFFExecutionError          (alias: XTBExecutionError)
    ├── MLIPRelaxationError
    ├── TimeoutException
    ├── RelaxBackendError            (also inherits RuntimeError)
    └── ModelDownloadError           (also inherits RuntimeError; sibling of RelaxBackendError)
```

`ModelDownloadError` is deliberately a **sibling** of `RelaxBackendError` rather than a subclass (`not issubclass(ModelDownloadError, RelaxBackendError)`). Inside `relax_backends.get_calculator`, compilation errors (`RelaxBackendError`) write a `.failed` cache marker to prevent repeated failing compilations, whereas transient network errors (`ModelDownloadError`) bypass that handler so subsequent runs retry automatically.

---

## 2. Crystal Encoding Pipeline

### Primitive-Cell Pre-Reduction

Introduced in upstream v4.0 (`da0d873`), `SLICES.structure2SLICES`, `SLICES.structure2randomSLICES`, `SLICES.structure2crystal_graph_rep`, and `SLICES.from_cif` invoke `to_primitive_if_smaller(structure)` through `_run_with_primitive_fallback`:

1. Computes `SpacegroupAnalyzer(structure).get_primitive_standard_structure()`.
2. Adopts the primitive cell only if it contains strictly fewer atoms **and** preserves `structure.composition.reduced_formula`.
3. If symmetry conversion fails or graph construction on the primitive cell raises `(ValueError, RuntimeError, ArithmeticError, LookupError)`, encoding transparently falls back to the input cell.

### Labeled Quotient Graph Construction

`structure2structure_graph(structure)` constructs a periodic `pymatgen.analysis.graphs.StructureGraph` via `StructureGraph.from_local_env_strategy` using one of four local-environment strategies configured via `graph_method`:

- `econnn` (default): `EconNN()` (effective coordination number).
- `crystalnn`: `CrystalNN(porous_adjustment=False, weighted_cn=True)`.
- `brunnernn`: `BrunnerNN_reciprocal()` (with `BrunnerNNReciprocal` compatibility alias for `pymatgen >= 2026.3`).
- `mininn`: `MinimumDistanceNN()`.

Each directed bond `(u, v, to_jimage)` records endpoint indices in the unit cell and the integer lattice translation vector `to_jimage` in `{-1, 0, +1}^3` (values `<= -1` serialize as `-`, `0` as `o`, `>= 1` as `+`).

### Encoding Strategies (1–4) and Space-Group Tokenization

| Strategy | Format Summary | Decoding Support |
|---|---|---|
| **Strategy 1** | Interleaved per edge: `El_u El_v u v t_x t_y t_z` (spaced signs) | Encode & Decode |
| **Strategy 2** | Fixed-width unspaced 2-char symbols (`_` padded), 2-digit indices, compact signs | Encode-only (`from_SLICES` supports 1, 3, 4) |
| **Strategy 3** | Atom symbol header followed by `u v t_x t_y t_z` (spaced signs) | Encode & Decode |
| **Strategy 4** *(default)* | Optional tokenized space-group prefix (SLICES-PLUS), atom symbol header, then `u v t_x t_y t_z` with 3-char compact translation tokens (`ooo`, `+oo`, `o--`, etc.) | Encode & Decode |

In Strategy 4, `utils_wyckoff.py` maps all **230** international space-group numbers (`1..230`, covering 250 setting aliases in `sg_encoding`) to unambiguous lowercase/3-letter uppercase tokens via `get_tokenized_enc(int_number)` and recovers the space-group number via `get_space_group_num_from_letter_enc(letter_enc)`. Leading digit tokens are remapped (`0 -> o`, `1 -> +`; second digit `d -> chr(ord('z') - d)`) so space-group prefixes never collide with chemical element symbols or numeric atom indices.

### Augmentation and Canonicalization

- **`structure2randomSLICES(...)`**: Generates up to `num` unique representations (including the unpermuted string) by optionally permuting atom indices (`shuffle_atom_order`), edge ordering (`shuffle_bond_order`), and edge direction/translation signs (`flip_bonds`). Note that final list ordering depends on `PYTHONHASHSEED` because unique strings are collected in a Python `set` before `random.shuffle` (`DEF-022`).
- **`structure2SLICESAug_atom_order(...)`**: Convenience wrapper performing atom-order permutations only (`shuffle_atom_order=True, shuffle_bond_order=False, flip_bonds=False`).
- **`get_canonical_SLICES(...)`**: Sorts atoms by atomic number `Z`, canonicalizes each edge direction so `u <= v` (negating `to_jimage` when flipped), orders periodic translation columns via column sums and cubic index weights, and sorts edges lexicographically so equivalent graph permutations collapse to one canonical string.

---

## 3. Periodic Net Topology and Barycentric Embedding

During decoding (`SLICES.to_structures`), `convert_graph()` maps the parsed `(atom_types, edge_indices, to_jimages)` arrays into a `tobascco_net.Net(x_dat, dim=3)` multigraph with integer edge voltages:

1. **Cycle Basis (`simple_cycle_basis`):** Builds a spanning tree and enumerates fundamental cycles and their net lattice voltages (`cycle_rep`).
2. **Lattice Basis (`get_lattice_basis`):** Solves for integer combinations of cycle vectors spanning the 3D identity lattice via SymPy exact rational nullspace computation (`sy.Matrix(...).nullspace()`).
3. **Cocycle Basis (`get_cocycle_basis`):** Constructs the orthogonal cocycle space (`order - 1` rows) representing internal atomic degrees of freedom.
4. **Eon Orthogonal Projection & Metric Tensor (`get_metric_tensor`):** Projects graph edges into the cycle/cocycle periodic representation (`periodic_rep`), computes the Gram metric tensor, and extracts standard barycentric lattice vectors via `np.linalg.cholesky(net.metric_tensor)`.
5. **Fractional Coordinates (`get_coordinates`):** Recovers barycentric site positions by accumulating `lattice_arcs` along shortest paths of a Kruskal minimum spanning tree rooted at vertex `"1"`.

`tobascco_net.py` also exposes `Net.clear_cache()` (clearing cached periodic/metric arrays) and NetworkX 3.x-compatible `Net.nodes_iter(data=...)`.

---

## 4. Bundled GFN-FF Topology Engine and Non-Linux Fallback

Before optimizing non-barycentric coordinates, `SLICES.get_inner_p_target(bond_scaling=1.05)` needs equilibrium bond lengths (`blist`, `vbond`) and bond angles (`alist`, `vangl`) for a finite 3x3x3-expanded neighbor table (`testBonds_cut.top`, 20 neighbor rows per atom, built by `get_nbf_blist` with the v4.0 cap of `<= 19` listed neighbors in row 20).

### Linux x86\_64 Bundled Library (`slices._vendor.gfnff`)

On Linux x86\_64, `slices.gfnff_helper.run_gfnff_helper(nbf_text)` executes the bundled open-source GFN-FF shared library (`pprcht/gfnff` with the SLICES topology-export patch, LGPL-3.0, portable `manylinux2014_x86_64` ELF `libgfnff.so.0.1.1`) in memory via `ctypes`, eliminating `/dev/shm` scratch files and external subprocesses.

- **Parameterization modes:**
  - `legacy86_overlay` *(default)*: Uses `src/slices/_vendor/gfnff_extra/param_gfnff_legacy86.xtb` for `Z = 1..86` (matching the legacy modified `xtb` parameterization) and the library's internal parameters for `Z = 87..103`.
  - `modern` (`SLICES_VENDOR_GFNFF_PARAM_MODE=modern`): Uses the library's internal parameters for all elements.
  - Custom parameter table: `SLICES_VENDOR_GFNFF_PARAM_FILE=/path/to/params.xtb`.
- **Empirical comparison vs legacy `xtb` (2,383 MP-20 structures, CPU):**
  - **88%** of structures produced identical reconstruction targets.
  - On the **194** structures where targets differed, bundled GFN-FF matched **165 / 194** reference structures versus **79 / 194** for legacy `xtb` (which produced non-finite values for actinides and crashed on 39 inputs; 0 regressions under standard matcher, 1 under loose matcher).
  - Independent **40,000-structure** symSLICES validation confirmed consistent net gains (+262 strict matches, -30 loose matches).
  - Topology step latency is ~0.5 s vs ~0.12 s for `xtb`, yielding median total decode time of 1.59 s vs 1.37 s.

### Non-Linux External `xtb` Fallback

If importing `slices._vendor.gfnff` raises `ImportError` or `OSError` (for example on macOS ARM64 or native Windows), `run_gfnff_helper` invokes `_run_external_xtb_fallback(nbf_text)`:

1. Resolves the executable from `SLICES_XTB_PATH`, legacy `XTB_MOD_PATH`, or `shutil.which("xtb_noring_nooutput_nostdout_noCN")`.
2. Runs `[xtb_bin, "--gfnff", "testBonds_cut.top", "--wrtopo", "blist,vbond,alist,vangl"]` with `shell=False` and a 30 s timeout inside a `tempfile.TemporaryDirectory()`.
3. Sanitizes Fortran overflow fields (`"********"` -> `"       0"`) before JSON parsing and raises `GFNFFExecutionError` with build/configuration guidance if the binary is missing or fails.

---

## 5. ZL\* Non-Barycentric Optimization

Starting from the rescaled barycentric structure `structure_recreated_std` (`get_rescaled_lattice_vectors`), `SLICES.to_structures()` optimizes both lattice metric components and cocycle coordinates (`structure_recreated_opt`):

1. **Symmetry-Preserving Parameterization (`lattice_type`):** Inspects the diagonal elements of `metric_tensor_std` (`[G_00, G_11, G_22]`) to classify the metric into cubic (`1`), two-equal-axes (`21`, `22`, `23`), or general (`3`) parameterizations (`initialize_x_bounds`), constraining lattice scale within `[lattice_shrink, lattice_expand]` (`[1.0, 1.25]`) and cocycle displacements within `[-delta_x, +delta_x]` (`[-0.45, +0.45]`).
2. **Objective Function (`SLICES.func`):** Minimizes weighted squared inner-product errors against GFN-FF equilibrium bond lengths and bond-angle distances (`inner_p_target`, `angle_weight=0.5`), combined with Lennard-Jones repulsive penalties for uncovered non-bonded atom pairs (`vbond_param_ave=0.01`, `repul=True`) and covered pairs (`vbond_param_ave_covered=0.0`).
3. **Optimizer:** Single deterministic `scipy.optimize.fmin_l_bfgs_b` call (`approx_grad=True`, `m=10`, `factr=1e7`, `pgtol=1e-5`, `epsilon=1e-8`, `maxfun=15000`, `maxiter=15000`, `maxls=20`).
4. **Cell-Size Relaxation Dispatch & Timeouts:**
   - `<= 20` atoms: `relax(struc)` — `fmax=self.fmax`, `steps=self.steps`, 360 s timeout.
   - `21..40` atoms: `relax_large_cell1(struc)` — `fmax=self.fmax`, `steps=self.steps`, 720 s timeout.
   - `> 40` atoms: `relax_large_cell2(struc)` — calls `self.relaxer.relax(struc)` with the relaxer's own defaults (`fmax=0.1, steps=500` on `NequIPRelaxer`), 2000 s timeout (`DEF-008`).
   - When `self.relaxer is None` (`relax_model=None` or `"none"`), both `to_structures()` and `to_4structures()` short-circuit cleanly and return `[structure_recreated_std, structure_recreated_opt], 0` with zero error output (`DEF-013`).

---

## 6. NequIP Relaxation Backends and Empirical Benchmarks

### Built-In Plans and CPU Default Rationale

`src/slices/relax_backends.py` defines three NequIP-OAM plans backed by `mir-group/NequIP-OAM-{S,M,L}:0.1`:

| `relax_model` | Relaxation Model | Final Energy Model | Default Device |
|---|---|---|---|
| `"auto"` *(default)* | `NequIP-OAM-S` (or `SLICES_RELAX_MODEL`) | `NequIP-OAM-L` | `cpu` |
| `"nequip-s+l"` | `NequIP-OAM-S` | `NequIP-OAM-L` | `cpu` |
| `"nequip-m+l"` | `NequIP-OAM-M` | `NequIP-OAM-L` | `cpu` |
| `"nequip-l"` | `NequIP-OAM-L` | `NequIP-OAM-L` | `cpu` (intended for `SLICES_DEVICE=cuda`) |
| `None` / `"none"` | Disabled | Returns `0` | — |

Supported ASE optimizers (`OPTIMIZERS`): `BFGS` (default), `LBFGS`, `FIRE`, and `FIRE+BFGS` (10 `FIRE` pre-steps followed by `BFGS`), wrapped in ASE `ExpCellFilter`.

**Why CPU `nequip-s+l` is the default (`315d4f0`):** Single-process profiling on 32 MP-20 structures measured the per-structure decode breakdown as **0.43 s** GFN-FF topology (CPU) + **0.45 s** ZL\* optimization (CPU) + **0.10 s** NequIP relaxation on GPU (`OAM-L`, ~6.5 ms/call x ~11 calls) versus **0.25 s** on CPU (`OAM-S`, ~18 ms/call). Because ~90% of wall time is CPU-bound, GPU execution speeds up decoding by at most ~12% when AOTInductor is available, and without the CUDA toolkit (TorchScript fallback) GPU decoding measured 1.70 s/structure vs 1.15 s/structure on CPU. Defaulting to CPU `nequip-s+l` provides consistent results across workstations and laptops while keeping GPU execution opt-in via `SLICES_DEVICE=cuda`.

### Full MP-20 Benchmark Results (2,383 Structures, CPU)

Measured across all 2,383 structures in [data/mp20_nonmetal/mp20_v4_benchmark_2383.csv](data/mp20_nonmetal/mp20_v4_benchmark_2383.csv) using identical `StructureMatcher` tolerances and [data/mp20_nonmetal/chemPotMP.json](data/mp20_nonmetal/chemPotMP.json):

| Method | Decoded Successfully | Standard Match Rate | Loose Match Rate | Median \|E\_form - DFT\| (eV/atom) | Notes |
|---|---:|---:|---:|---:|---|
| Legacy `xtb` + M3GNet | 2,291 | 88.67% | 91.23% | 0.048 | Pre-v4 baseline |
| `nequip-s+l` (`auto`) | 2,374 | 93.79% | 95.97% | 0.025 | Default CPU plan (1.0x CPU time) |
| `nequip-m+l` | 2,374 | 94.80% | 96.18% | 0.021 | ~2.0x CPU time |
| MatterSim-1M | 2,374 | 94.67% | 96.01% | 0.050 | Identical ZL\* start structures |

### Compilation Tiers, Caching, and Download Retries

- **CPU compilation:** Uses TorchScript (`.nequip.pth`), which measured 3–4x faster than AOTInductor on CPU benchmarks.
- **CUDA compilation (`SLICES_DEVICE=cuda`):** Attempts tiers in order: (1) AOTInductor + OpenEquivariance (`--extra oeq`, importing `openequivariance` prior to loading to register custom operators), (2) AOTInductor (`--target ase --num-nodes 1,inf` to support 1-atom primitive cells), and (3) TorchScript fallback.
- **Concurrent safety:** `get_calculator` acquires an exclusive `fcntl.flock` lock on `<cache_path>.lock` and replaces compiled artifacts atomically via `os.replace`, preventing race conditions when multiple worker processes start simultaneously.
- **Network resilience:** `_download_model` applies `(30, 120)` s connect/read timeouts, verifies `content-length`, retries after `(5, 15, 30)` s on transient network/HTTP-429/5xx errors, and raises `ModelDownloadError` with direct URL and `SLICES_NEQUIP_MODEL_{S,M,L}` override instructions on exhaustion.

### Overlap Pre-Optimization and Cell-Collapse Recovery

Approximately **1.7%** (40 / 2,383) of ZL\*-optimized starting geometries contain severe atomic overlaps (minimum pair separation down to 0 Å). Under unconstrained MLIP relaxation, such geometries can collapse the unit cell so neighbor-list construction loops indefinitely inside compiled C extensions where POSIX `SIGALRM` cannot interrupt execution.

`NequIPRelaxer.relax` (and `_ASEMLIPRelaxer.relax` for optional MLIPs) applies two defenses:

1. **`preoptimize(structure)`:** Computes `closest_pair_ratio(structure) = min(d_ij / (r_i + r_j))` using pymatgen covalent radii. When `< OVERLAP_TRIGGER` (`0.5`), applies Niggli reduction followed by `remove_overlaps` (purely geometric soft-sphere repulsion targeting `OVERLAP_TARGET = 0.7`, deterministic `np.random.default_rng(seed=0)` for coincident atoms `d < 1e-3`, up to 300 iterations, and 2% isotropic cell expansion every 20 iterations up to `1.5x`).
2. **`_collapse_guard(calc, atoms)`:** Wraps `calc.calculate` to raise `CellCollapse` if `volume / natoms < min(2.0, 0.5 * init_vol_per_atom)`, `max_length > 20 * min_length`, or `min_angle < 5°`. Upon `CellCollapse`, `NequIPRelaxer.relax` retries once with `NequIP-OAM-S` + `FIRE(maxstep=0.1, steps=2*steps)`.

**Measured effect on the 2,383-structure MP-20 benchmark:**
- Non-terminating hangs: **2 -> 0**.
- Energy divergences (`|E_form - DFT| > 5 eV/atom`): **2 -> 0** (`nequip-s+l`), **11 -> 0** (`nequip-m+l`).
- Standard match count on the 40 overlapping structures: **13 -> 24** (all non-overlapping structures remain unchanged).

---

## 7. Optional Multi-MLIP Adapter Protocol

When `relax_model` is not in `RELAX_MODELS = ("auto", "none", "nequip-l", "nequip-s+l", "nequip-m+l")`, `relax_backends.resolve_relax_model` and `make_relaxer` lazily dispatch to `src/slices/mlip_relaxer.py`:

| Canonical Name | Aliases | Package | Calculator / Backend | Variant Env Override |
|---|---|---|---|---|
| `chgnet` | `chgnet` | `chgnet` | `CHGNetCalculator` (fallback: `StructOptimizer`) | — |
| `mattersim` | `mattersim` | `mattersim` | `MatterSimCalculator` | `SLICES_MATTERSIM_MODEL` |
| `orbv3` | `orb-v3`, `orb_v3`, `orb` | `orb-models` (`orb_models`) | `ORBCalculator` (`orb-v3-conservative-inf-omat` / `orb-v3-direct-inf-mpa`) | `SLICES_ORBV3_MODEL` |
| `mace` | `mace-mp`, `mace_mp` | `mace-torch` (`mace`) | `mace_mp(..., default_dtype="float32")` (`medium`) | `SLICES_MACE_MODEL` |
| `m3gnet` | `m3gnet` | `m3gnet` + `tensorflow` (+ `tf_keras`) | Legacy `m3gnet.models.Relaxer` | — |

Design invariants:
- **Zero module-level side effects:** Importing `slices.mlip_relaxer` never imports `torch`, `tensorflow`, or `keras` and never mutates `TF_USE_LEGACY_KERAS` or `sys.modules["keras"]`. Legacy Keras 2 compatibility shims are scoped strictly inside `M3GNetRelaxer.__init__`.
- **Unified return protocol:** Every `MLIPRelaxer` subclass exposes `.name`, `.device`, `.optimizer`, and `.description`, and returns `{"final_structure": Structure, "trajectory": SimpleNamespace(energies=[total_eV]), "steps": int, "preoptimized": bool, "retry": int}`.
- **Shared safety pipeline:** `_ASEMLIPRelaxer` reuses `preoptimize`, `_collapse_guard`, `_cell_filter`, and `_optimize` from `slices.relax_backends`.

---

## 8. Opt-In Multi-Stage Robust Decoding

`src/slices/decoding_strategies.py` is strictly decoupled from standard v4.0.2 decoding (`SLICES.to_structures` and `SLICES.SLICES2structure` never import it). It is entered only via `SLICES.robust_SLICES2structure(...)` or `slices decode --robust`:

1. **Stage 1 (Standard v4.0.2 Fast Path):** Validates `strategy in (1, 3, 4)`, parses via `from_SLICES`, and runs `to_structures()`. If `relaxer is None` or a relaxed 3-structure result succeeds, returns immediately with bit-identical output to `SLICES2structure`.
2. **Stage 2 (Topology & Multi-Start ZL\* Recovery):** Invoked only if Stage 1 raises or fails relaxation:
   - `CycleBasisOptimizer.find_lattice_basis` searches conditioned cycle-row permutations via singular-value ratio scoring and elementwise `is_approximately_integral(vect, tolerance=1e-6)` using an isolated `np.random.default_rng(seed)`.
   - `BondParameterFallback.build_inner_p_target` provides a 0-based covalent-radius fallback matrix if GFN-FF bond targets are missing or non-positive.
   - `MultiStartOptimizer.optimize` runs `fmin_l_bfgs_b` from `x0` plus `n_starts - 1` seeded Gaussian perturbations clipped to bounds (stripping `scipy>=1.15`-deprecated `iprint`/`disp` kwargs, with zero global `np.random` mutation) using atom-count-scaled tolerances from `AdaptiveConvergence`.
3. **Stage 3 (Progressive Relaxation):** `ProgressiveRelaxer.relax_with_fallbacks` attempts relaxation across deduplicated `(fmax, steps)` tiers (`primary`, `moderate: max(fmax, 0.3) / max(steps, 120)`, `loose: max(fmax, 0.5) / max(steps, 150)`) while restoring `slices_inst.fmax` and `slices_inst.steps` in a `finally` block.

---

## 9. Safe Local and SLURM Batch Utilities

`src/slices/utils.py` retains all 16 public utility functions (`temporaryWorkingDirectory`, `split_list`, `is_slurm_available`, `splitRun`, `splitRun_csv`, `splitRun_sample`, `show_progress`, `cancel_all_jobs`, `collect_json`, `collect_csv`, `collect_csv_filter`, `exclude_elements_json`, `determine_bin_count`, `adaptive_dynamic_binning`, `parallel_process_json`, `parallel_process_csv`) with three safety upgrades over legacy scripts:

1. **Scoped Process Tracking:** Local workers launched by `_run_local_job` use `subprocess.Popen(..., start_new_session=(os.name != "nt"))` and register their handles in `_SUBMITTED_LOCAL_PROCS` alongside SLURM job IDs in `_SUBMITTED_SLURM_JOBS`. `show_progress()` and `cancel_all_jobs()` act only on tracked handles/IDs — the legacy `pgrep -f python` + `kill -9` hazard has been completely removed.
2. **OS-Agnostic File Operations:** Directory creation, copying, cleanup, and working-directory scoping use `shutil.copytree`, `shutil.rmtree`, `Path.unlink`, and `with temporaryWorkingDirectory(job_dir):` instead of raw `os.system("rm ...")` / `os.system("cp ...")` calls.
3. **Local Override:** Setting `SLICES_FORCE_LOCAL=1` forces local execution in `is_slurm_available()` even on hosts with SLURM utilities installed.

---

## 10. Baseline Mathematical and Algorithmic Freeze Invariant

To guarantee exact scientific reproducibility against upstream SLICES v4.0.2 (`94ef8e0`), all core mathematical, topological, GFN-FF target-construction, ZL\* optimization, and default NequIP relaxation code paths remain strictly invariant:

- **Golden Equivalence Harness:** [tests/baseline/test_golden_equivalence.py](tests/baseline/test_golden_equivalence.py) verifies **89/89** deterministic assertions (encoding across Strategies 1–4, canonicalization, space-group round-trips, net bases, GFN-FF targets, ZL\* coordinates, NequIP energies, and structural matchers) against frozen upstream v4.0.2 fixtures at **`atol=1e-12`** (`PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`).
- **Formal Disposition Tracking:** All 27 audited behavioral items are documented in [docs/migration/DEFERRED_CORE_REGISTER.md](docs/migration/DEFERRED_CORE_REGISTER.md):
  - **2 non-math fixes applied in Stage 4:** `DEF-007` (define and import `TimeoutException`; guard POSIX main-thread `SIGALRM`) and `DEF-013` (short-circuit `self.relaxer is None` in `to_structures` and `to_4structures`).
  - **22 frozen deferred items:** Core math/compatibility quirks (such as heteronuclear LJ mixing in `DEF-001`, `np.random` draws in `DEF-004`, `core.py` import-time env block in `DEF-005`, `ExpCellFilter` in `DEF-009`, `np.matrix.I` in `DEF-011`, and exact float symmetry checks in `DEF-014`) preserved verbatim for controlled post-baseline ablation experiments.
  - **3 blocked regressions:** Legacy fork changes (`DEF-016`, `DEF-017`, `DEF-020`) explicitly excluded.
