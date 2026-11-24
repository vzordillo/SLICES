# SLICES v4.0.2 Migration — Scientific Engineering Lab Log

## 1. Study Metadata & Reference Configuration

| Field | Value |
|---|---|
| **Project** | Migration of personal SLICES improvements (`vzordillo/SLICES`) onto upstream SLICES v4.0.2 (`xiaohang007/SLICES`) |
| **Log Initiated** | 2026-11-25 06:03 JST (2026-11-24 21:03 UTC) |
| **Working Repository** | `/home/ordillo/tests/SLICES` |
| **Active Target Branch** | `slices-4-personal` (forked from `upstream/main` @ `94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`) |
| **Reference Personal Branch** | `backup/v3-personal` (`origin/main` @ `301c75fcdfb2d553b616c30178ccc7b0161b1fe7`, 30 commits ahead of `cea17da`) |
| **Immutable Baseline Worktree** | `/home/ordillo/tests/SLICES-upstream-baseline` (detached HEAD `94ef8e079b69c37138159805e3c701b8df87a5d7`, `git worktree lock`, `chmod -R a-w`) |
| **Upstream Fork-Base** | `142298be4f83ab161d51298c82e74e94c3319891` (tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9`; 23 commits behind `94ef8e0`) |
| **Personal Fork-Base** | `cea17da95be2cd9d17f6c71765895dbb5cb64958` (tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9`; bit-identical tree to `142298b`) |
| **Remotes** | `origin` = `https://github.com/vzordillo/SLICES.git`; `upstream` = `https://github.com/xiaohang007/SLICES.git` |
| **Remote Push Policy** | **LOCAL-ONLY — NEVER PUSH** (`git config push.default nothing` verified in local repo config) |
| **Governing Blueprint** | [PLAN.md](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md) |
| **Deferred Core Register** | [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) |

---

## 2. Verified Host Hardware & Software Environment

| Component | Verified Specification | Operational Constraint / Note |
|---|---|---|
| **OS / Kernel** | Ubuntu 24.04.3 LTS (`Linux sage 6.8.0-87-generic x86_64`) | ABI-compatible with bundled `manylinux2014_x86_64` `libgfnff.so.0.1.1` |
| **CPU** | Intel(R) Xeon(R) 6731P (32 physical cores, 1 thread/core) | Used for deterministic CPU `nequip-s+l` relaxation and `pytest` |
| **System RAM** | 503 GiB total (~488 GiB available) | Supports multi-worker execution and `/dev/shm` scratch |
| **GPUs** | 2× NVIDIA RTX PRO 6000 Blackwell (97,887 MiB VRAM each) | Driver `580.95.05` (CUDA 13.0); Blackwell `sm_120` requires `cu128` for opt-in GPU runs; no system `nvcc` on `PATH` |
| **Root Filesystem (`/`)** | `/dev/nvme0n1p2` — 894 GB total, 884 GB used, **9.7 GB free (99%)** | **Critical constraint:** never install duplicate CUDA PyTorch wheels (~3.5 GB) onto `/` |
| **Secondary Storage** | `/data1`, `/data2` (7.0 TB NVMe each, `drwxr-xr-x root:root`) | Non-writable by user `ordillo` |
| **Ephemeral RAM Disk** | `/dev/shm` (`tmpfs`, 252 GiB total, ~23 MiB used, 1%) | Mandatory scratch location for `UV_CACHE_DIR` and transient test outputs |
| **System Compilers & VCS** | `gcc`, `g++`, `gfortran`, `cmake`, `git` (`/usr/bin/*`) | System `xtb` not on `PATH` (unnecessary on Linux SLICES v4.0.2) |
| **Workspace Tools (`.tools`)** | `uv 0.13.9`, `ruff 0.17.6`, managed CPython `3.10.22` (146 MB) | Installed under `/home/ordillo/tests/.tools` outside git worktrees |
| **Upstream Venv (`.venv-upstream`)** | Locked CPU environment (1.2 GB, `--no-install-project`) | `torch==2.9.1+cpu`, `nequip==0.17.1`, `pymatgen==2025.10.7`, `ase==3.29.0`, `matscipy==1.3.1`, `numpy==2.2.6`, `scipy==1.15.3`, `networkx==3.4.2`, `spglib==2.7.0`, `e3nn==0.6.0`, `einops==0.8.2`, `pytest==9.2.0`, `pytest-cov==7.1.0` |
| **NequIP Model Cache (`.cache`)** | Raw Zenodo weights + compiled CPU TorchScript models (121 MB) | `/home/ordillo/tests/.cache/{nequip_raw,slices/nequip}` |

---

## 3. Governing Invariants

1. **Local-Only Discipline:** No `git push` to `origin` or `upstream` under any circumstance (`push.default=nothing`).
2. **Repository Scope Boundary:**
   - **Retained:** `src/slices/`, CLI, `tests/`, `docs/`, `configs/` / Docker files, `examples/`, `data/`, `benchmark/`, and `HTS/`.
   - **Scheduled for Removal (Stage 4 only):** `MatterGPT/` (8.9 MB on `94ef8e0`; `MatterGPT_no_flash/` was already removed upstream between `142298b` and `94ef8e0`).
3. **Default Backend Preservation:** Upstream v4.0.2 NequIP (`src/slices/relax_backends.py`, `relax_model="auto"` resolving to CPU `nequip-s+l`) and Linux-bundled GFN-FF (`src/slices/gfnff_helper.py`, `src/slices/_vendor/gfnff*`) remain the default unmodified backend path. Personal `mlip_relaxer`, cross-platform fallbacks, and `decoding_strategies` are strictly optional/additive.
4. **Strict Math/Algorithm Freeze Boundary:** All mathematical, crystallographic, graph-theoretic, topological, GFN-FF target-building, ZL* L-BFGS-B optimization, and default NequIP relaxation symbols enumerated in [PLAN.md Section 4.1](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L145-L157) must remain exact or numerically invariant (`atol=1e-12` on CPU) relative to `/home/ordillo/tests/SLICES-upstream-baseline`. Any candidate bug fix or algorithmic enhancement is recorded in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) rather than applied to the frozen core.
5. **Disk Hygiene:** Reuse `/home/ordillo/tests/.venv-upstream` and `/home/ordillo/tests/.cache`; enforce `PYTHONDONTWRITEBYTECODE=1`, `UV_CACHE_DIR=/dev/shm/ordillo-uv-cache`, and `UV_LINK_MODE=copy`; keep root `/` free space >= 5 GB at all times (currently 9.7 GB).
6. **Language & Code Quality:** 100% English-only prose, comments, docstrings, filenames, and logs; factual scientific tone; Google Python Style Guide conventions merged with `backup/v3-personal` patterns.

---

## 4. Seven-Stage Pipeline Checklist

| Stage | Phase | Status | Primary Artifacts | Mandatory Gate |
|---|---|---|---|---|
| **Stage 1** | Plan & Environment Setup | **Completed** (2026-11-25 06:01 JST) | [PLAN.md](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md), `.tools`, `.venv-upstream`, `.cache`, `SLICES-upstream-baseline` | Exact SHAs & tree match verified; zero tracked edits; smoke + CPU determinism `0.00e+00`; `/` >= 9 GB free |
| **Stage 2** | Parallel Audit (Slices 2A, 2B, 2C) | **Completed** (2026-11-25 06:30 JST) | [AUDIT_FORK_DIFF.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md), [AUDIT_UPSTREAM_STYLE.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md), [AUDIT_BASELINE_HARNESS.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md), [LAB_LOG.md](file:///home/ordillo/tests/SLICES/docs/migration/LAB_LOG.md), [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) | 30 personal + 23 upstream commits audited; 60 CJK files mapped; 19-crystal corpus verified at `0.000e+00` CPU variance; 27 deferred entries deduplicated; zero tracked edits |
| **Stage 3** | Review & Freeze Sign-Off | **Completed** (2026-11-25 06:43 JST) | [REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md), `tests/baseline/{generate_golden.py,test_golden_equivalence.py,fixtures/*}` | `APPROVED FOR STAGE 4` (`CA-01`–`CA-09`, `RUL-01`–`RUL-08`); `89/89` golden tests green on both trees (`91.47 s` / `90.99 s`); strict `ruff` 0 errors |
| **Stage 4** | Refactor & Additive Port | **Completed** (2026-11-25 07:34 JST) | Commits `e0142f8`–`479f0a2`: refactored `src/slices/`, `exceptions.py`, `mlip_relaxer.py`, `decoding_strategies.py`, `cli.py`, `examples/`, `tools/`, `pyproject.toml`, `MatterGPT/` removed, baseline CJK translated | Gate 4A (`88.68 s`) & Gate 4B (`88.18 s`) **`89/89` golden pass (`atol=1e-12`)**; `0` ruff errors; `0` CJK across `1,407` files; CLI & `validate_installation.py` pass; `0` pushes |
| **Stage 5** | Refine, Types & Tests | **Completed** (2026-11-25 07:52 JST) | Commits `ad4446b` & `8d9314b`: strict Google `ruff` config, PEP 604 typing polish, `tests/{unit,integration,regression}/` (18 files) | **`250 passed, 5 skipped, 0 failed` (`117.12 s`)**; `89/89` golden intact; `0` strict Google-style ruff errors; `100%` AST parity; `0` CJK; `0` pushes |
| **Stage 6** | Document (100% English) | **Completed** (2026-11-25 08:04 JST) | Commit `c7d2868`: `README.md`, `TECHNICAL.md`, `CHANGELOG.md`, `docs/README.md`, 6 `docs/api/API_*.md`, `26` legacy Sphinx files removed; `LAB_LOG.md` & `DEFERRED_CORE_REGISTER.md` synced | `1,441` repo files **`0` CJK hits**; `0` broken links/anchors; `0` hardcoded host paths; live API/CLI spot-check PASS |
| **Stage 7** | Systematize & Final Gate | **Completed** (2026-11-25 08:15 JST) | Commit `7-a`: `docs/README.md` + `docs/migration/` (`LAB_LOG.md`, `DEFERRED_CORE_REGISTER.md`, [FINAL_REPORT.md](file:///home/ordillo/tests/SLICES/docs/migration/FINAL_REPORT.md)); wheel/sdist verified | **`250 passed, 5 skipped, 0 failed` (`116.92 s`)**; `0.000e+00` live dual-tree parity; `0` ruff/compileall errors; **`0` CJK across `1,449` files (incl. `docs/migration/`)**; `332/332` links valid; `/` `9.7 GB` free; `0` pushes |

---

## 5. Chronological Execution Log

### Stage 1: Plan & Environment Setup (2026-11-25 05:46–06:01 JST)

**Executor:** `architect` (assigned in board post `#2`, completed in board post `#3`)  
**Scribe Verification:** Primary-source git config, worktree list, directory sizes, cache file sizes, and `PLAN.md` re-verified at 2026-11-25 06:02–06:03 JST.

#### Entry `S1-01` — Repository Clone, Remote Wiring & Local-Only Guard
- **Action:** Cloned `https://github.com/vzordillo/SLICES.git` into `/home/ordillo/tests/SLICES` (size: 704 MB including `.git` object database), added remote `upstream` pointing to `https://github.com/xiaohang007/SLICES.git`, fetched all refs/tags from both remotes, and set `git config --local push.default nothing`.
- **Verification:**
  - `origin/main` = `301c75fcdfb2d553b616c30178ccc7b0161b1fe7`
  - `upstream/main` (tag `v4.0.2`) = `94ef8e079b69c37138159805e3c701b8df87a5d7`
  - `git config --local --get push.default` = `nothing`

#### Entry `S1-02` — Branch Topology & Fork-Base Tree-Equivalence Proof
- **Action:** Created preservation branch `backup/v3-personal` at `origin/main` (`301c75f`) and working migration branch `slices-4-personal` at `upstream/main` (`94ef8e0`). Checked out `slices-4-personal`.
- **Tree-Equivalence Verification:** Because `origin` has a rewritten commit history, common ancestry was verified by git tree SHA comparison rather than commit SHA equality:
  - Upstream fork-base commit: `142298be4f83ab161d51298c82e74e94c3319891` -> tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9`
  - Personal fork-base commit: `cea17da95be2cd9d17f6c71765895dbb5cb64958` -> tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9`
  - `git diff 142298b cea17da` returned empty output (bit-identical trees).
- **Divergence Span:**
  - Personal delta (`cea17da..backup/v3-personal`): **30 commits**.
  - Upstream delta (`142298b..upstream/main`): **23 commits** (including `v4.0.0`, `v4.0.1`, `v4.0.2`).

#### Entry `S1-03` — Immutable Upstream Baseline Worktree Provisioning
- **Action:** Provisioned a detached reference git worktree at `/home/ordillo/tests/SLICES-upstream-baseline` checked out at `94ef8e079b69c37138159805e3c701b8df87a5d7` (274 MB), locked it with `git worktree lock`, and removed write permissions recursively (`chmod -R a-w`).
- **Rationale:** Guarantees an immutable, physically isolated upstream v4.0.2 reference tree for dual-tree golden equivalence testing in Stages 2–7 without git checkout switching or accidental mutation.

#### Entry `S1-04` — Host Resource & Storage Constraint Audit
- **Observation:** Host has ample compute (32-core Xeon 6731P, 503 GiB RAM, 2× RTX PRO 6000 Blackwell) and 252 GiB `/dev/shm` tmpfs, but root partition `/` (`/dev/nvme0n1p2`, 894 GB) is at 99% utilization with **9.7 GB free** after environment setup, while `/data1` and `/data2` are root-owned and non-writable.
- **Mitigation Established:** Enforced Workspace Disk Discipline Rule (single shared CPU virtualenv, `UV_CACHE_DIR=/dev/shm/ordillo-uv-cache`, `PYTHONDONTWRITEBYTECODE=1`, no duplicate CUDA PyTorch wheels on `/`; any future opt-in `cu128` GPU test must reside in `/dev/shm/venv-cu128`).

#### Entry `S1-05` — Isolated Toolchain, Locked Python 3.10 Environment & NequIP Cache
- **Workspace Artifacts Created (outside tracked git repositories):**
  1. `/home/ordillo/tests/.tools` (146 MB): standalone `uv 0.13.9`, `ruff 0.17.6`, and managed CPython `3.10.22`.
  2. `/home/ordillo/tests/.venv-upstream` (1.2 GB): provisioned via `uv sync --directory /home/ordillo/tests/SLICES --locked --extra cpu --no-install-project` plus `pytest==9.2.0` and `pytest-cov==7.1.0`.
     - *Design Decision:* `--no-install-project` prevents generating `src/slices.egg-info` in either worktree, ensuring both `PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src` and `PYTHONPATH=/home/ordillo/tests/SLICES/src` execute against identical locked dependency versions.
  3. `/home/ordillo/tests/.cache` (121 MB):
     - Raw Zenodo archives (`NEQUIP_CACHE_DIR=/home/ordillo/tests/.cache/nequip_raw`):
       - `b39e883d722e2108867a0b8028e90beeccf2e50c944c9063ef511711984a17fe.nequip.zip` (5,638,676 B — `NequIP-OAM-S`)
       - `039e5620e6c89fd53bdd3b6bd33574e5b29704bb4df5bc339869baca3d5eead6.nequip.zip` (78,464,590 B — `NequIP-OAM-L`)
     - Compiled CPU TorchScript caches (`SLICES_MODEL_CACHE=/home/ordillo/tests/.cache/slices/nequip`):
       - `NequIP-OAM-S-0.1__torchscript__cpu__torch2.9.1__nequip0.17.1.nequip.pth` (2,735,745 B)
       - `NequIP-OAM-L-0.1__torchscript__cpu__torch2.9.1__nequip0.17.1.nequip.pth` (39,328,139 B)
- **Network Latency Measurement:** `https://pypi.org/simple/` responded in `0.64 s` compared to `3.28 s` for upstream's default `https://pypi.tuna.tsinghua.edu.cn/simple/` index in `pyproject.toml` (~5.1× faster).
- **Standard Activation Environment (for all Stages 2–7 runs):**
  ```bash
  export PATH="/home/ordillo/tests/.tools/bin:/home/ordillo/tests/.venv-upstream/bin:$PATH"
  export PYTHONDONTWRITEBYTECODE=1
  export NEQUIP_CACHE_DIR="/home/ordillo/tests/.cache/nequip_raw"
  export SLICES_MODEL_CACHE="/home/ordillo/tests/.cache/slices/nequip"
  export UV_CACHE_DIR="/dev/shm/ordillo-uv-cache"
  export UV_LINK_MODE="copy"
  ```

#### Entry `S1-06` — Baseline Smoke & CPU Determinism Verification
All measurements were executed against the read-only upstream tree (`PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src`) using `/home/ordillo/tests/.venv-upstream`:

| Probe / Target | Command / Scope | Observed Result | Repeatability / Validation |
|---|---|---|---|
| **NequIP Backend Prep** | `python -m slices.relax_backends --prepare` | CsCl-type `NaCl` relaxed in `1.65 s`; `E = -3.2291 eV/atom`, `a = 3.452 Å` | Passed (`nequip-s+l` CPU default) |
| **Bundled GFN-FF Helper** | `python -m slices.gfnff_helper` | `methane`: 4 bonds, 6 angles (`legacy86_overlay`); `Na3MnCoNiO6` target tuple `(178.74144, 178.74144, 126, 61.23)` | Passed (`rtol=1e-6` vs xtb-era `d40c909` reference) |
| **`NdSiRu.cif` Round-Trip** | 6-atom cell; encode -> decode -> CPU `nequip-s+l` | `E = -7.26759387 eV/atom`; `match_check3` strict = `('1', '0', '0', '0.0', '0.25', '0.25')` | **Exact `0.00e+00` repeat diff** in lattice matrix, fractional coords, and energy |
| **`Sr3Ru2O7.cif` Round-Trip** | 24-atom conventional -> 12-atom primitive reduction; CPU `nequip-s+l` | `E = -6.79135010 eV/atom`; `match_check3` strict = `('1', '1', '0', '0.0', '0.5', '0.33333333333333337')` | **Exact `0.00e+00` repeat diff** in lattice matrix, fractional coords, and energy |

- **Empirical Diagnostic Finding (Oxidation-State Species):** `NdSiRu.cif` contains explicit oxidation states on CIF site species, whereas reconstructed SLICES `Structure` instances carry neutral `Element` symbols. Direct `pymatgen.analysis.structure_matcher.StructureMatcher()` without `ElementComparator()` or POSCAR round-trip returns `False`, whereas `SLICES.match_check*` normalizes via POSCAR and `ElementComparator()` and returns `'1'`. The Stage 2C golden harness specification explicitly incorporates both exact numerical array checks and `ElementComparator()` matching.

#### Entry `S1-07` — Architectural Decisions & Stage 1 Exit Gate
- **Preliminary Static Scans Performed:**
  - CJK scan across `upstream/main`: **59 file/content hits** identified (including `src/slices/core.py` 34 lines, `src/slices/relax_backends.py` 1 line, `src/slices/utils.py` 182 lines, `README.md` 70 lines, `HANDOFF_workstation.md` 67 lines, 2 CJK filenames under `docs/`, plus hits in `HTS/`, `benchmark/`, `data/`, `Dockerfile/`, `rundocker.sh`, and `MatterGPT/`).
  - `MatterGPT/` coupling scan: identified hard path couplings in `examples/3.benchmark_relax_models.py:49-50` (`MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv`, `MatterGPT/2_decode/workflow/chemPotMP.json`), `tools/workstation_check.sh`, `HANDOFF_workstation.md`, `entrypoint_set_cpus_gradio.sh`, `pyproject.toml`, and `README.md`.
  - Freeze-boundary seed scan: identified **6 initial deferred core/algorithm items** (`DEF-001` through `DEF-006`).
- **Key Architectural Decisions Logged in Stage 1:**
  - `DEC-001`: Fork `slices-4-personal` from `upstream/main` (`94ef8e0`) rather than rebasing `backup/v3-personal`, keeping v4.0.2 NequIP + bundled GFN-FF as untouched baseline.
  - `DEC-002`: Freeze all core math, graph, topology, GFN-FF target, ZL* optimization, and default NequIP relaxation behavior; defer candidate improvements/bugs to `DEFERRED_CORE_REGISTER.md`.
  - `DEC-003`: Port `mlip_relaxer.py`, `decoding_strategies.py` (`robust_SLICES2structure`), and `cli.py` strictly as additive/opt-in modules; dispatch optional MLIPs in `relax_backends.make_relaxer` only when `relax_model` is outside upstream `RELAX_MODELS`.
  - `DEC-004`: Design dual-inheriting exception classes (`RelaxBackendError(SLICESError, RuntimeError)`, `ModelDownloadError(SLICESError, RuntimeError)`) to satisfy both upstream `RuntimeError` handlers and personal `SLICESError` handlers without changing boolean/`None` failure contracts.
  - `DEC-005`: Preserve `data/`, `benchmark/`, and `HTS/` intact for later benchmarking; defer `MatterGPT/` removal cleanly to Stage 4 after full coupling audit.
- **Stage 1 Deliverable & Exit Verification:** Published [PLAN.md](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md) (226 lines, 35,223 bytes). Verified `git status --short` showed only untracked `docs/migration/` (`git diff upstream/main` empty), zero commits or pushes made, and `/` free space at `9.7 GB` (>= 9 GB gate). Stage 1 approved by `coordinator` (board post `#4`).

---

### Stage 2: Parallel Audit — Read-Only (2026-11-25 06:02–06:30 JST — Completed)

#### Stage 2 Audit Dispatch Matrix

| Slice / Role | Agent | Exclusive Output File | Scope | Status |
|---|---|---|---|---|
| **Slice 2A** | `auditor-fork` | [AUDIT_FORK_DIFF.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md) | 30 commits & 1,377 diff entries in `cea17da..backup/v3-personal`; 5-bucket classification; `mlip_relaxer` <-> `relax_backends` contract; `cli.py` & `decoding_strategies.py` port spec | **Completed** (2026-11-25 06:15 JST, `#13`) |
| **Slice 2B** | `architect` | [AUDIT_UPSTREAM_STYLE.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md) | 23 commits in `142298b..upstream/main`; 60-file CJK ledger; `MatterGPT/` decoupling map; `HTS/`/`benchmark/`/`data/` compatibility; `pyproject.toml`/`setup.cfg`/`utils.py`/`ruff` baseline | **Completed** (2026-11-25 06:11 JST, `#9`) |
| **Slice 2C** | `baseline` | [AUDIT_BASELINE_HARNESS.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md) | Empirical 19-crystal Golden Reference Corpus on CPU (`SLICES-upstream-baseline`); `generate_golden.py` & `test_golden_equivalence.py` spec; 27 `backup/v3-personal` test/tool files triaged | **Completed** (2026-11-25 06:28 JST, `#16`) |
| **Lab Scribe** | `scribe` | [LAB_LOG.md](file:///home/ordillo/tests/SLICES/docs/migration/LAB_LOG.md), [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) | Stage 1 notebook initialization, 6-item Deferred Register seeding, full Stage 2 consolidation across Slices 2A–2C | **Completed** (2026-11-25 06:31 JST, `#17`) |

#### Entry `S2-01` — Stage 2 Lab Notebook & Deferred Register Initialization (2026-11-25 06:03 JST)
- **Executor:** `scribe` (brief `#7`, completed `#8`)
- **Action:** Created `docs/migration/LAB_LOG.md` and `docs/migration/DEFERRED_CORE_REGISTER.md`. Independently verified git branch/worktree state, `push.default=nothing`, disk free space (`9.7 GB` on `/`, `252 GB` on `/dev/shm`), NequIP cache byte sizes, and exact source line numbers in `/home/ordillo/tests/SLICES/src/slices/{core.py,tobascco_net.py,gfnff_helper.py}` and `backup/v3-personal` diffs for seed items `DEF-001` through `DEF-006`.
- **Verification:** Zero tracked files modified; zero CJK hits; zero edits to SLICES source code or other workers' audit reports.

#### Entry `S2-02` — Slice 2A Consolidation: Personal Fork Diff & Portability Audit (2026-11-25 06:15–06:17 JST)
- **Auditor / Report:** `auditor-fork` -> [AUDIT_FORK_DIFF.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md) (281 lines, 61 KB, 0 CJK chars; completed `#13`; ingested by `scribe` per `#14`).
- **Scope & Verification State:** Strictly read-only audit across `cea17da..backup/v3-personal` (`301c75f`); zero tracked files modified (`git diff` empty); `/` unchanged at `9.7 GB` free.
- **Quantitative Findings Logged:**
  1. **30 Commits & 1,377 Net Diff Entries Classified (`cea17da..301c75f`):** Mapped full commit DAG (`28` regular commits + `2` merge commits `03cc621`, `ea35217`) and partitioned all `127` non-bulk entries + `1,250` bulk entries into the 5 migration buckets:
     - `PORT_ADDITIVE`: `src/slices/exceptions.py`, adapted `src/slices/mlip_relaxer.py`, strictly opt-in `src/slices/decoding_strategies.py` + `SLICES.robust_SLICES2structure`, `SLICES.structure2SLICESAug_atom_order`, `Net.clear_cache` + `Net.nodes_iter` NX 2.x fix, `src/slices/cli.py` (from `slices_cli.py`), `src/slices/__init__.py`, `tests/**` (16 files) + `pytest.ini` -> `pyproject.toml`, and `tools/validate_installation.py`.
     - `PORT_CROSS_PLATFORM`: 3-way merge of `shutil`/`pathlib` file ops into `utils.py` preserving upstream `_SUBMITTED_SLURM_JOBS`/`_submit_slurm_job`/`_run_local_job`; POSIX main-thread `SIGALRM` + safe non-POSIX fallback for `function_timeout`; optional non-Linux external-`xtb` fallback inside `gfnff_helper.py` only when `libgfnff.so` raises `OSError` (zero committed binaries).
     - `PORT_STYLE_DOCS`: English translations, factual scientific prose (`fbfb536`), `# === Section ===` headers, modular `TECHNICAL.md`/`CHANGELOG.md`/`docs/api/*.md`, and directory-scoped `.gitignore` based on `e37ce5e` (catching `0379d6a`'s accidental reversion to blanket `*.csv`/`*.json`/`*.pth` ignores).
     - `DEFER_CORE_FREEZE`: **12 candidates (`FC-01`..`FC-12`)** consolidated into `DEFERRED_CORE_REGISTER.md` (see below).
     - `DROP_OBSOLETE`: 71.0 MB `src/slices/bin/{linux,macos,windows}/xtb*` binaries, 6 tracked `src/slices/__pycache__/*.cpython-39.pyc` files, 5 `src/slices.egg-info/*` files, broken root gitlink `xtb` (`160000` without `.gitmodules` in `301c75f`), root scratch `test.slices`, obsolete `v2.0.12` M3GNet `pyproject.toml`, silent `m3gnet` fallback in `SLICES.__init__`, `examples/` -> `tutorial/` rename, `continue-on-error: true` / disabled CI commits (`01ee0dc..3162c99`), and **destructive `benchmark/` changes (`39` CSV/JSON/doc deletions + `1,199` directory-rename moves)** that must be dropped to preserve historical `benchmark/` reproducibility.
  2. **Unified `relax_backends.py` + `mlip_relaxer.py` Adapter Contract:**
     - Upstream `RELAX_MODELS` (`"auto"`, `None`/`"none"`, `"nequip-s+l"`, `"nequip-m+l"`, `"nequip-l"`) execute the 100% untouched v4.0.2 path; only names outside `RELAX_MODELS` dispatch lazily to `slices.mlip_relaxer` (`chgnet`, `mattersim`, `orbv3` [alias `orb-v3`], `mace` [aliases `mace-mp`, `mace_mp`], optional legacy `m3gnet`).
     - Zero import-time deep-learning imports or `TF_USE_LEGACY_KERAS`/`sys.modules["keras"]` side effects (strictly isolated inside `M3GNetRelaxer.__init__`); missing optional packages raise actionable `ImportError` via `importlib.util.find_spec(...)`.
     - Every optional `MLIPRelaxer` exposes `relaxer.{name,device,optimizer,description}`, reuses `relax_backends.{_cell_filter,_optimize,preoptimize,_collapse_guard}` quietly (`logfile=None`), and returns the exact `NequIPRelaxer` dict (`trajectory.energies[-1]` as `float` total potential energy in eV).
  3. **Critical Fork Bug Catches Resolved in Stage 4 Port Specs:**
     - `cli.py` (from `slices_cli.py`): switch `decode --model` default to `"auto"`; use `relax_model=None` in `encode`/`validate`/`canonicalize` (avoiding PyTorch/NequIP startup overhead); fix `slices validate` exit-code bug (returned `0` even on invalid SLICES); replace Unicode checkmarks with ASCII `VALID`/`INVALID`.
     - `decoding_strategies.py` & `robust_SLICES2structure`: fix 5 fork bugs — (1) remove `scipy>=1.15`-deprecated `iprint`/`disp` kwargs, (2) replace global `np.random` with seeded `np.random.default_rng(seed)`, (3) fix non-elementwise `np.all(...) or np.all(...)` in `is_approximately_integral`, (4) replace rank-permutation-invariant no-op in `CycleBasisOptimizer` with SymPy nullspace retry search, and (5) fix 1-based supercell `IndexError` in `BondParameterFallback` and `strategy=2` `UnboundLocalError` in `robust_SLICES2structure`.
     - `function_timeout`: caught fork's broken `threading.Timer` fallback (raising in a background timer thread never interrupts the main thread, and fork needlessly excluded macOS `Darwin` despite POSIX `SIGALRM` support on main threads).
     - `utils.py`: specified exact 3-way merge retaining upstream v4.0.2 `_SUBMITTED_SLURM_JOBS` alongside fork's `shutil`/`pathlib` file operations.
  4. **Deferred Core Register Deduplication & Ingestion (`FC-01`..`FC-12`):** Audited all 12 Slice 2A candidates against `DEF-001`..`DEF-014`:
     - **6 cross-referenced merges (zero duplication):** `FC-01`, `FC-02`, `FC-03` -> merged into `DEF-003`; `FC-04`, `FC-05` -> merged into `DEF-002`; `FC-08` -> merged into `DEF-008` (confirming independent discovery alongside Slice 2B `DEF-UP-002`).
     - **6 net-new entries assigned sequentially as `DEF-015` through `DEF-020`** (`FC-06`, `FC-07`, `FC-09`, `FC-10`, `FC-11`, `FC-12`) in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md).
- **Decisions Added from Slice 2A:**
  - `DEC-008`: Drop all `backup/v3-personal` `benchmark/` deletions (`39` files) and directory renames (`1,199` moves), `examples/` -> `tutorial/` rename, 71 MB `xtb` binaries, `.pyc` files, and broken `xtb` gitlink; base `.gitignore` on `e37ce5e` without blanket `*.csv`/`*.json` ignores.
  - `DEC-009`: Enforce strict lazy dispatch from `relax_backends.py` to `mlip_relaxer.py` only for names outside upstream `RELAX_MODELS`, with zero import-time MLIP/Keras mutations and unified `NequIPRelaxer`-compatible return dicts and attributes.
  - `DEC-010`: Fix all 5 identified fork bugs in opt-in `decoding_strategies.py`/`robust_SLICES2structure`, `slices validate` exit-code bug in `cli.py`, and POSIX main-thread `SIGALRM` scoping in `function_timeout` during Stage 4 porting.

#### Entry `S2-03` — Slice 2B Consolidation: Upstream v4.0.2 Architecture, Scope Coupling & CJK/Style Audit (2026-11-25 06:11–06:13 JST)
- **Auditor / Report:** `architect` -> [AUDIT_UPSTREAM_STYLE.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md) (256 lines, 43 KB; completed `#9`; ingested by `scribe` per `#11`).
- **Scope & Verification State:** Strictly read-only audit across `142298b..94ef8e0`; zero tracked files modified (`git diff` empty); `/` unchanged at `9.7 GB` free.
- **Quantitative Findings Logged:**
  1. **23 Upstream Commits (`142298b..94ef8e0`, 216 files changed, `+19,832 / -1,802,081` lines):** Full commit-by-commit ledger mapped. Identified 10 critical v4.0.x core/packaging commits (`#7 da0d873` primitive-cell pre-reduction, `#8 eb1f6c9` NequIP `relax_backends.py`, `#9 119afaf` `uv`/Python 3.10 & M3GNet removal, `#12 d40c909` bundled `libgfnff` + `neighbor_list[19, i] = len(row)`, `#13 4e5a9d9` xtb binary removal, `#14 b600715` `_SUBMITTED_SLURM_JOBS`, `#15 315d4f0` CPU `nequip-s+l` default + overlap/collapse guards, `#16 a096d91` species-map warning fix, `#21 2635bcc` `pymatgen>=2026.3` & `scipy>=1.15` fixes, `#23 94ef8e0` download retry/timeout) that Stage 4 **must not** regress with older `142298b`-era `backup/v3-personal` hunks.
  2. **Exhaustive CJK & Translation Ledger (60 distinct upstream files):** Reconciled Stage 1's suffix-filtered `59` hit count to **60 distinct upstream files** (`2` CJK filenames + `59` CJK content files, with the CJK-named local-run `utils` copy appearing in both; extensionless `Dockerfile/Dockerfile` closed the count gap):
     - *Category A — Core Library (`src/slices/`, translate in Stage 4):* **3 files, 217 lines** (`core.py` 34 lines, `relax_backends.py:251` 1 redundant error line, `utils.py` 182 lines).
     - *Category B — Top-level Docs, Configs & Docker:* **6 files** (`README.md` 70 lines, `HANDOFF_workstation.md` 67 lines, CJK-named MatterGPT intro PDF `6.27 MB` binary under `docs/`, CJK-named obsolete local-run `utils` copy `129` lines under `docs/`, `Dockerfile/{Dockerfile,docker-compose.yml}` 11+3 lines, `rundocker.sh` 1 line; exact upstream paths catalogued in `AUDIT_UPSTREAM_STYLE.md` Section 2.3).
     - *Category C — Kept Baselines (`HTS/`, `benchmark/`, `data/`, comments/docstrings/prints only):* **30 files** (zero edits to CSV/JSON data or numerical logic).
     - *Category D — `MatterGPT/` (dropped in Stage 4):* **21 files, 386 lines**.
     - *Programmatic Safety Check:* Verified **zero** code paths parse, compare, or key data structures on CJK strings anywhere in the repository.
  3. **Critical `MatterGPT/` Decoupling Finding (`mp20_eform_bandgap_nonmetal.csv` Mismatch):**
     - `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` (`1,006 KB`, `2,383` rows, SHA256 `07fee712...`, header `SLICES,formation_energy_per_atom,band_gap,crystal_system`, strategy-4 SLICES with space-group tokens) is **NOT** the same file as `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` (`14,303` rows, SHA256 `2a1866f7...`, header `SLICES,eform,bandgap`, no space-group tokens).
     - `MatterGPT/2_decode/workflow/chemPotMP.json` (`1.9 KB`, SHA256 `a01b28770d76d6ce...`) is bit-identical to the copy in `benchmark/.../4_eform_m3gnet/workflow/chemPotMP.json`.
     - Verified `einops` and `gui = ["gradio"]` in `pyproject.toml` are strictly MatterGPT-only (zero references in `src/slices/`, `examples/`, `HTS/`, `benchmark/`, `data/`).
  4. **Baseline Compatibility Audit (`HTS/` 97 files, `benchmark/` 121 files, `data/` 15 files) — Findings `BC-1`..`BC-6`:**
     - `BC-1`: 3 RNN scripts run `from slices import check_SLICES` (breaks when empty `src/slices/__init__.py` shadows local v1 `slices.py`; solvable additively via a lightweight wrapper in `src/slices/__init__.py`).
     - `BC-2`: Zero `SLICES(...)` calls in `HTS/` or `benchmark/` pass `relax_model="m3gnet"` (contrary to `HANDOFF_workstation.md:95`); only 2 standalone post-screening scripts import TensorFlow/M3GNet directly.
     - `BC-3`: Upstream `SyntaxError` (`from slices.utils import * splitRun,...`) at `HTS/0_get_json_mp_api/2_filter_prior_3d/1_run.py:5`.
     - `BC-4`: Legacy `search_materials` import & `/crystal/APIKEY.ini` in `HTS/0_get_json_mp_api/0_run.py:5` (archived dataset zip already bundled).
     - `BC-5`: Unused v1 `CrystalGraph` import in `benchmark/Match_rate_QMOF-21-40/0_get_json/1_element_filter/count.py:3` and raw traceback file `benchmark/.../2_train_sample/error.py` (exclude `benchmark/` & `HTS/` from strict `ruff`/`pytest`).
     - `BC-6`: 28 legacy `1_splitRun.py` scripts invoke `qsub 0_run.pbs`; preserve intact and document in Stage 6.
  5. **Critical Runtime/Safety Defects & `ruff 0.17.6` Static Baseline (`src/slices/` + `examples/`):**
     - **Baseline lint/style counts:** **694** core lint violations (`E,F,W,I,B,UP,SIM,RUF`) + **806** docstring/type-annotation violations (`D,ANN`), with `0/179` typed functions across `src/slices/` (`_vendor/gfnff/` excluded from style edits to keep vendored LGPL-3.0 code untouched).
     - **Critical runtime bug (`F821`):** `src/slices/core.py:60` raises undefined `TimeoutException` inside `function_timeout` (deleted in commit `119afaf`).
     - **Critical workstation safety hazard:** `src/slices/utils.py` (`show_progress` L364–428 & `cancel_all_jobs` L461–526) executes `pgrep -f "python"` followed by `kill` / `kill -9` on non-SLURM hosts, terminating unrelated user Python processes; also logged 11 `os.system` calls, 8 unguarded `os.chdir` calls, duplicate `finally` print (`L447-451`), and 5 stale docstring defaults in `core.py`.
  6. **Deferred Core Register Ingestion:** Audited and verified exact source lines for all 8 Slice 2B candidates (`DEF-UP-001`..`DEF-UP-008`); confirmed zero duplication against `DEF-001`..`DEF-006` and ingested sequentially as **`DEF-007` through `DEF-014`** in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md).
- **Decisions Added from Slice 2B:**
  - `DEC-006`: Before `git rm -r MatterGPT` in Stage 4, `git mv` `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` -> `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` and `MatterGPT/2_decode/workflow/chemPotMP.json` -> `data/mp20_nonmetal/chemPotMP.json`, and repoint `examples/3.benchmark_relax_models.py:49-50` and `src/slices/gfnff_helper.py:119` so the 2,383-structure v4.0.2 benchmark remains runnable without `MatterGPT/`.
  - `DEC-007`: Replace non-SLURM `pgrep -f python` + `kill -9` in `src/slices/utils.py` with tracked `_SUBMITTED_LOCAL_PIDS` process management (mirroring upstream commit `b600715`'s `_SUBMITTED_SLURM_JOBS`), alongside `pathlib`/`shutil` file operations and `temporaryWorkingDirectory` guards.

#### Entry `S2-04` — Slice 2C Consolidation: Golden Baseline Equivalence Harness & Test Suite Audit (2026-11-25 06:28–06:31 JST)
- **Auditor / Report:** `baseline` -> [AUDIT_BASELINE_HARNESS.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md) (415 lines, 64 KB, 0 CJK chars; completed `#16`; ingested by `scribe` per `#17`).
- **Scope & Verification State:** Strictly read-only empirical probing against `/home/ordillo/tests/SLICES-upstream-baseline/src` (`94ef8e0`) using `/home/ordillo/tests/.venv-upstream` and `/home/ordillo/tests/.cache`; transient `/dev/shm/baseline-probe` cleaned; zero tracked files modified; `/` unchanged at `9.7 GB` free.
- **Empirical Corpus & Determinism Findings Logged:**
  1. **Stratified 19-Structure Golden Reference Corpus (`G01`–`G19`) + Supplementary `G15b` + 3 Safety Fixtures (`S01`–`S03`) + 11 Invalid/Edge-Case SLICES Strings (`E01`–`E11`):**
     - **Full symmetry coverage:** All 7 crystal systems (`triclinic`, `monoclinic`, `orthorhombic`, `tetragonal`, `trigonal`, `hexagonal`, `cubic`) and all 6 Wyckoff centering types (`P`, `I`, `F`, `C`, `A`, `R`); exhaustive 230-space-group bijection in `utils_wyckoff.py` verified with **0** `pymatgen.core.Element` token collisions.
     - **Critical branch coverage:** Single-atom primitive cell (`G14` `Na`, `cocycle_rep is None`), conventional-to-primitive reduction (`G04` `VO` `8 -> 4`, `G06` `LiMnO2` `16 -> 8`), high-coordination `>19` truncation (`G15` `PrBi2IO4` `CN = 20 -> 19` and `G15b` `Cs2LiCoC6N6` `CN = 24 -> 19`), CIF oxidation-state species (`G01` `NdSiRu.cif`: `Nd2+/Si4-/Ru2+`), heavy/actinide boundaries (`S03` `Rn Z=86 -> True`, `Fr Z=87 -> False`; `G16` `SmThCN` `Z=90` `check_element=False` + bundled GFN-FF `modern` fallback), natural & synthetic `preoptimize` (`G05` `cpr=0.4024`, `G17` `cpr=0.2715`, `S01` `cpr=0.2792 -> 0.7210`), `CellCollapse` retry (`S02`), `unstable_graph=True` (`G18` `YHO2`), and `gfnff_helper` stored target (`G19` `Na3MnCoNiO6`).
     - **Dual-Pass CPU Benchmark (`relax_model="auto"` -> `nequip-s+l`, `OMP_NUM_THREADS=1`):** Wall-clock times **`30.52 s`** (Pass 1) and **`30.05 s`** (Pass 2); maximum numerical repeat variance **`0.000e+00`** (exact IEEE-754 bit-for-bit equality across all `inner_p_target`, `colattice_weights`, `[std, opt, opt2]` lattices/fractional coordinates, and energies); **`16 / 16` (`100%`)** strict and loose `match_check3` matches on all CIF-backed structures (`G01`–`G16`).
     - **Critical Cross-Process Determinism Catch (`PYTHONHASHSEED=0`):** Proved empirically that `structure2randomSLICES` (`core.py:741, 843-845`) converts a `set()` to `list()` before `random.shuffle()`, causing `16/16` list-order mismatches across separate Python processes under `random.seed(42)` unless `PYTHONHASHSEED=0` is set (`16/16` exact list-order match restored with `PYTHONHASHSEED=0`).
  2. **Golden Equivalence Harness Architecture (`tests/baseline/`):**
     - Compact `< 250 KB` fixture store (`corpus_manifest.json`, `golden_metadata.json`, exact IEEE-754 `golden_arrays.npz`), referencing existing `examples/` and `data/` without duplicating CIFs.
     - Per-entry fresh `SLICES(relax_model="auto")` instantiation (reusing module-cached `relax_backends._CALCULATORS` in `< 0.2 ms`) to isolate transient instance attributes (`self.unstable_graph`, `self.space_group_num`).
     - Three assertion tiers (`==` / `np.array_equal` discrete invariance, `rtol=0.0, atol=1e-12` CPU numerical invariance, `ElementComparator` + POSCAR normalization on `NdSiRu.cif`), plus an isolated `PYTHONHASHSEED=0` live dual-tree subprocess runner (`~16 s` stratified subset; `~60 s` `--dual-tree-full`) verifying `slices.__file__` origin against `/home/ordillo/tests/SLICES-upstream-baseline/src`.
  3. **Personal Test Suite Triage (All 27 Fork Test, Runner & CI Files) + 6 New Unit Test Modules:**
     - Classified every file in `backup/v3-personal:{pytest.ini, .github/workflows/tests.yml, tests/**, tools/tests/**, tools/validate_installation.py, tools/benchmarks/test_*.py}` into direct v4.0.2 ports, `@pytest.mark.mlip` + mocked ports, and obsolete drops.
     - Caught **9 concrete bugs** in legacy fork tests (e.g., passing a string to `check_structural_validity`, undefined `slices_backend` `NameError` in `test_round_trip_batch.py:217`, invalid `graph_method='econ'`, `strategy=2` decode crash, 0-based `'e0'` `Net` label index wraparound, missing `ElementComparator` on `NdSiRu.cif`, non-frozen `LatticeBasisError` expectations, unparseable `known_slices_string` placeholder, and blind `nrows=3` MP-20 selection hitting 2D `GaTe` and `Th`-bearing `SmThCN`).
     - Specified 6 new fast (`< 5 s`) v4.0.2 unit test suites for Stage 5: `test_relax_backends.py`, `test_gfnff_helper.py`, `test_utils_wyckoff.py`, `test_exceptions.py`, `test_cli.py`, and `test_decoding_strategies.py` (including freeze-isolation sentinel spy).
  4. **Deferred Core Register Ingestion (`DEF-BC-01`..`DEF-BC-07`):** Verified exact upstream line numbers and confirmed zero duplication against `DEF-001`..`DEF-020`; ingested all 7 net-new upstream quirks sequentially as **`DEF-021` through `DEF-027`** in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md).
- **Decisions Added from Slice 2C:**
  - `DEC-011`: Enforce `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `SLICES_TORCH_THREADS=1`, and per-entry fresh `SLICES` instances in `tests/baseline/generate_golden.py` and dual-tree equivalence subprocesses to ensure cross-process bit-exact reproducibility (including `structure2randomSLICES`).
  - `DEC-012`: Reuse existing `examples/` and `data/` fixtures (dropping duplicate `tests/fixtures/structures/*.cif` copies), fix all 9 legacy fork test bugs during Stage 5 porting, and add the 6 new v4.0.2 unit test modules plus freeze-isolation spy tests.

#### Entry `S2-05` — Stage 2 Completion & Mandatory Exit Gate Verification (2026-11-25 06:31 JST)
- **Executor:** `scribe` (consolidating Slices 2A `#13`, 2B `#9`, 2C `#16` per `#17`)
- **Stage 2 Exit Gate Verification Matrix (per [PLAN.md Section 6](file:///home/ordillo/tests/SLICES/docs/migration/PLAN.md#L221)):**

| Gate Criterion | Required Target | Verified Result | Status |
|---|---|---|---|
| Personal Fork Coverage | All 30 commits (`cea17da..301c75f`) classified | 30/30 commits + 1,377 diff entries classified across 5 buckets ([AUDIT_FORK_DIFF.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_FORK_DIFF.md)) | **PASS** |
| Upstream Evolution Coverage | All 23 commits (`142298b..94ef8e0`) mapped | 23/23 commits mapped; 10 critical v4.0.x commits flagged against regression ([AUDIT_UPSTREAM_STYLE.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_UPSTREAM_STYLE.md)) | **PASS** |
| CJK Audit Completeness | All 59+ CJK hits mapped & checked for parsing | 60/60 upstream files reconciled (3 core / 6 top+Docker+docs / 30 kept baselines / 21 `MatterGPT/`); zero programmatic CJK parsing | **PASS** |
| Golden Corpus Empirical Verification | Stratified 12–20 crystals, deterministic CPU run | 19-crystal corpus (`G01`–`G19`) + `G15b` + 3 safety fixtures + 11 edge strings; `30.52s`/`30.05s`; `0.000e+00` repeat variance; `16/16` strict matches ([AUDIT_BASELINE_HARNESS.md](file:///home/ordillo/tests/SLICES/docs/migration/AUDIT_BASELINE_HARNESS.md)) | **PASS** |
| Deferred Core Register Integrity | Deduplicated consolidation of all slices | **27 entries (`DEF-001`–`DEF-027`)** — 100% traceability across 6 seeds + 8 `DEF-UP-*` + 12 `FC-*` (6 merges, 6 net-new) + 7 `DEF-BC-*`, zero duplicates ([DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md)) | **PASS** |
| Read-Only & Hygiene Invariants | Zero tracked edits, zero pushes, `/` >= 9 GB | `git diff upstream/main` empty; `push.default=nothing`; `SLICES-upstream-baseline` untouched at `94ef8e0`; `/` at `9.7 GB` free; 0 CJK hits in `LAB_LOG.md` & `DEFERRED_CORE_REGISTER.md` | **PASS** |

- **Stage 2 Verdict:** **COMPLETE — ALL GATES PASSED.** Stage 3 launched (`baseline` building `tests/baseline/` per `#18`; independent `reviewer` authoring `docs/migration/REVIEW_SIGNOFF.md` per `#19`).

---

### Stage 3: Review & Freeze Sign-Off (2026-11-25 06:29–06:43 JST — Completed)

#### Stage 3 Dispatch Matrix

| Role | Agent | Exclusive Ownership | Scope | Status |
|---|---|---|---|---|
| **Golden Baseline Implementation** | `baseline` | `tests/baseline/{__init__.py, generate_golden.py, test_golden_equivalence.py, fixtures/*}` | Generate golden fixtures from `SLICES-upstream-baseline` (`PYTHONHASHSEED=0`), run Pass A (baseline) & Pass B (unmodified `slices-4-personal`), pass strict `ruff check` | **Completed** (2026-11-25 06:43 JST, `#23`) |
| **Independent Review & Sign-Off** | `reviewer` | [REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md) | Cross-audit Slices 2A–2C, issue `APPROVE`/`MODIFY`/`BLOCK` rulings on borderline decisions (`DEF-007`, `DEF-013`, `DEF-026`, `utils.py`, `MatterGPT/`, baselines, `__init__.py`, MLIP contract), produce Stage 4 disjoint file-ownership matrix & sign-off verdict | **Completed** (2026-11-25 06:42 JST, `#21`) |

#### Entry `S3-01` — Golden Baseline Equivalence Suite Implementation & Dual-Tree Verification (2026-11-25 06:43 JST)
- **Executor / Report:** `baseline` (brief `#18`, completed `#23`; logged by `scribe` per `#28`).
- **Implemented Suite (`/home/ordillo/tests/SLICES/tests/baseline/`):**
  - `__init__.py` (`277 B`), `generate_golden.py` (`26,917 B`), `test_golden_equivalence.py` (`15,820 B`) — 100% English (0 CJK hits), Google docstrings, Python 3.10+ PEP 604 type annotations, zero duplicated CIF files (reads directly from kept `examples/` and `data/`).
- **Generated Golden Fixtures (`40.10 s` runtime strictly against `/home/ordillo/tests/SLICES-upstream-baseline/src` @ `94ef8e0` with `PYTHONHASHSEED=0`):**
  - `tests/baseline/fixtures/golden_metadata.json`: `304,506 bytes` (`297.4 KiB`)
  - `tests/baseline/fixtures/golden_arrays.npz`: `86,406 bytes` (`84.4 KiB`)
  - **Combined Fixture Size:** `390,912 bytes` (`381.8 KiB`, within `< 500 KB` storage budget).
- **Dual-Tree Verification Measurements (`PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `pytest -p no:cacheprovider tests/baseline/test_golden_equivalence.py`):**

| Pass | Target `PYTHONPATH` | Result | Wall-Clock Time | Coverage Verified |
|---|---|---|---:|---|
| **Pass A** | `/home/ordillo/tests/SLICES-upstream-baseline/src` (`94ef8e0`) | **`89 passed`, `0 failed`, `0 skipped`** | **`91.47 s`** | 19-structure discrete/GFN-FF/ZL*/NequIP/matcher assertions (`atol=1e-12`), `to_4structures` (`G10`/`G12`), `G15b` (`24->19` CN cap), `S01` `preoptimize`, `S03` `Rn`/`Fr`, `G01` `ElementComparator` vs `SpeciesComparator`, `E01`–`E11`, 230-SG Wyckoff bijection, `config.py` hashes, live dual-tree subprocess parity |
| **Pass B** | `/home/ordillo/tests/SLICES/src` (unmodified `slices-4-personal`) | **`89 passed`, `0 failed`, `0 skipped`** | **`90.99 s`** | Identical 89/89 parity against frozen upstream fixtures prior to any Stage 4 edits |

- **Lint & Hygiene Verification:**
  - `ruff check tests/baseline/`: `All checks passed!` (`0` errors, also `All checks passed!` under strict `--select E,F,W,I,B,UP,SIM,RUF,D,ANN,BLE --line-length 100`).
  - Zero tracked files modified at Stage 3 completion (`git diff upstream/main` empty; only untracked `docs/migration/` and `tests/baseline/`); `/` free space steady at `9.7 GB`.

#### Entry `S3-02` — Independent Stage 3 Architectural Review & Freeze Sign-Off (2026-11-25 06:42–06:45 JST)
- **Reviewer / Report:** `reviewer` (Carbon High — independent of Stage 1 & Stage 2 authorship) -> [REVIEW_SIGNOFF.md](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md) (232 lines, 41 KB, 0 CJK hits; completed `#21`; ingested by `scribe` per `#22`).
- **Verification State:** Strictly read-only review; zero tracked files modified; `/` unchanged at `9.7 GB` free; lockfile refresh hypothesis (`CA-02`) empirically validated in `/dev/shm`.
- **Stage 3 Sign-Off Verdict:** **`APPROVED FOR STAGE 4`**, gated solely on `baseline` (`#18`) posting 100% green `PYTHONHASHSEED=0 pytest tests/baseline/test_golden_equivalence.py` against both `SLICES-upstream-baseline/src` and unmodified `SLICES/src` (plus `ruff check tests/baseline/` clean) and binding compliance with `CA-01`–`CA-09` and `RUL-01`–`RUL-08`.
- **Nine Cross-Audit Catches Resolved (`CA-01`–`CA-09`):**
  1. `CA-01` (High — directory conflict): Keep `Dockerfile/` in place (do NOT rename to `docker/` or create `configs/`); clean/translate `Dockerfile/*`, `rundocker.sh`, `entrypoint_set_cpus.sh`, `slurm.conf`, and `APIKEY.ini` in place; delete root `__init__.py`, `entrypoint_set_cpus_gradio.sh`, `HANDOFF_workstation.md`, and `src/slices/README.rst`.
  2. `CA-02` (Critical — lockfile drift trap, empirically verified in `/dev/shm`): Keep `[[tool.uv.index]] name = "tuna"` `default = true` in `pyproject.toml`, remove `"einops"` & `gui = ["gradio"]`, and put `dev` tools under PEP 735 `[dependency-groups]` (never adding conflicting external MLIPs to `[project.optional-dependencies]`). Verified `uv lock` strips 39 Gradio/MatterGPT packages while keeping **all 10 core scientific packages (`torch`, `nequip`, `pymatgen`, `ase`, `scipy`, `numpy`, `networkx`, `spglib`, `matscipy`, `e3nn`) 100% version-identical**.
  3. `CA-03` (Critical — CSV collision): Relocate `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` (2,383 Strategy-4 rows) -> `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` (preserving existing 14,303-row `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv`) and `MatterGPT/2_decode/workflow/chemPotMP.json` -> `data/mp20_nonmetal/chemPotMP.json`.
  4. `CA-04` (High — blocked opt-in MLIP): Delete hardcoded `if name == "m3gnet": raise ValueError(...)` (`relax_backends.py:106-108`) *before* `if name not in RELAX_MODELS:` so `"m3gnet"` reaches `mlip_relaxer.resolve_optional_mlip`.
  5. `CA-05` (High — import side-effect leak): Implement PEP 562 lazy `__getattr__` in `src/slices/__init__.py` for `SLICES` & `check_SLICES` (eager only for `__version__ = "4.0.2"` & `slices.exceptions`), preventing `python -m slices.relax_backends` from prematurely triggering `core.py:5-9` (`OMP_NUM_THREADS="1"`).
  6. `CA-06` (Medium — incomplete short-circuit): Apply `DEF-013` `if self.relaxer is None:` short-circuit to **both** `to_structures()` (`core.py:1900`) and `to_4structures()` (`core.py:1944`).
  7. `CA-07` (Medium — baseline script drift): Block all 3 fork `HTS/` workflow edits (`665b042`, which introduced broken `threading.Timer` `SystemExit`); restrict `HTS/` changes strictly to the 9 CJK files plus the 1-char stray `*` fix at `HTS/0_get_json_mp_api/2_filter_prior_3d/1_run.py:5`.
  8. `CA-08` (High — lint-induced math drift): Add `[tool.ruff.lint.per-file-ignores] "src/slices/core.py" = ["E402"]` so `core.py:5-9` remains above imports (`DEF-005`/`DEF-014`), and exclude `src/slices/_vendor`, `HTS`, `benchmark`, `data`, `docs` from `ruff` and `pytest`.
  9. `CA-09` (Low–Medium — asset retention): Treat `tests/baseline/**` as opaque to Stage 4 and delete only MatterGPT/CJK assets under `docs/`, preserving `SLICES_demo.png`, `figure_intro.png`, and `win11_wsl2.png`.
- **Eight Binding Borderline Rulings (`RUL-01`–`RUL-08`):**
  - `RUL-01` (`DEF-007`): **MODIFY & APPROVE** — `TimeoutException(SLICESError)` in `exceptions.py`; `SIGALRM` on POSIX main thread only (`hasattr(signal, "SIGALRM") and current is main`), direct `yield` off-main-thread/Windows (rejecting fork's broken `threading.Timer`).
  - `RUL-02` (`DEF-013`): **APPROVE** — verified `SLICES.__init__` already maps both `None` and `"none"` to `(None, "none")`; short-circuit `if self.relaxer is None:` in `to_structures()` and `to_4structures()` (`CA-06`).
  - `RUL-03` (`DEF-004`, `DEF-005`): **BLOCK / DEFER** — strict freeze confirmed on `tobascco_net.py:359,514` (`# noqa: F841`) and `core.py:5-9` (`E402` per-file-ignore), along with 20 additional `DEF-*` math/algo items (including `DEF-026`).
  - `RUL-04` (`utils.py`): **APPROVE** — replace `pgrep -f python` + `kill -9` with `_SUBMITTED_LOCAL_PROCS` `Popen` tracking, preserve `_SUBMITTED_SLURM_JOBS`, honor `SLICES_FORCE_LOCAL=1`, replace 11 `os.system` calls with `shutil`/`pathlib`, wrap submissions in `temporaryWorkingDirectory`, preserve all 16 public function names/signatures.
  - `RUL-05` (`MatterGPT/` & packaging): **MODIFY & APPROVE** — relocate `mp20_v4_benchmark_2383.csv` + `chemPotMP.json` (`CA-03`), prune `MatterGPT/` + clutter (~17 MB), repoint `examples/3.benchmark_relax_models.py`, `gfnff_helper.py`, and `tools/workstation_check.sh`, update `pyproject.toml`/`uv.lock` (`CA-02`) and `.gitignore` (`e37ce5e`).
  - `RUL-06` (`HTS/`, `benchmark/`, `data/`): **APPROVE** — surgical CJK comment/docstring/print translation across 30 files + `1_run.py:5` syntax typo fix; preserve `benchmark/.../error.py` untouched; zero algorithmic/data/path drift.
  - `RUL-07` (`src/slices/__init__.py`): **MODIFY & APPROVE** — PEP 562 lazy `__getattr__` for `SLICES` and `check_SLICES`, eager only for `__version__ = "4.0.2"` and `slices.exceptions` (`CA-05`).
  - `RUL-08` (MLIP & GFN-FF boundaries): **MODIFY & APPROVE** — sibling dual-inheriting `RelaxBackendError`/`ModelDownloadError` (`not issubclass(ModelDownloadError, RelaxBackendError)`), zero-side-effect `mlip_relaxer.py`, deleted `L106-108` `m3gnet` block (`CA-04`), and `(ImportError, OSError)`-gated external `SLICES_XTB_PATH` fallback in `gfnff_helper.py` (zero binaries committed).
- **Register Synchronization:** Updated Status columns and ruling annotations for all **27 entries (`DEF-001`–`DEF-027`)** in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md): **2 Approved for Stage 4** (`DEF-007`, `DEF-013`), **3 Blocked from Porting/Regression** (`DEF-016`, `DEF-017`, `DEF-020`), and **22 Frozen — Deferred (Stage 3 Confirmed)** (`DEF-001`–`DEF-006`, `DEF-008`–`DEF-012`, `DEF-014`–`DEF-015`, `DEF-018`–`DEF-019`, `DEF-021`–`DEF-027`).
- **Authoritative Stage 4 Disjoint Execution Plan (`workspace: "inherit"`, git commits at wave barriers only):**
  - **Wave 4A (Carbon High, parallel):** `4A-1 (refactor-pkg)` (`MatterGPT/` prune + fixture relocation + `pyproject.toml`/`uv.lock`/`.gitignore`/clutter), `4A-2 (refactor-core)` (`exceptions.py`, `__init__.py`, `core.py`), `4A-3 (refactor-backends-utils)` (`utils.py`, `relax_backends.py`, `gfnff_helper.py`, `tobascco_net.py`, `config.py`, `utils_wyckoff.py`) -> Gate 4A (`ruff` + golden equivalence) -> Atomic Commits `4A-a` & `4A-b`.
  - **Wave 4B (parallel after Gate 4A):** `4B-1 (port-additive, Carbon High)` (`mlip_relaxer.py`, `decoding_strategies.py`, `cli.py`, `examples/*`, `tools/*`), `4B-2 (translate-baselines, Neon XHigh)` (30 CJK files in `HTS/`/`benchmark/`/`data/` + `1_run.py:5` + `Dockerfile/*` & root Docker scripts) -> Gate 4B (full dual-tree golden pass + CLI smoke + CJK=0 scan) -> Atomic Commits `4B-a` & `4B-b`.
- **Decisions Added from Stage 3 Review:**
  - `DEC-013`: Retain `tuna` `default = true` in `pyproject.toml` and use PEP 735 `[dependency-groups]` for `dev` tools (omitting external MLIPs from `[project.optional-dependencies]`) so `uv.lock` keeps all 10 core scientific packages 100% version-identical (`CA-02`).
  - `DEC-014`: Implement PEP 562 lazy `__getattr__` in `src/slices/__init__.py` for `SLICES` & `check_SLICES` to guarantee zero import-time side effects on `python -m slices.relax_backends` (`CA-05`, `RUL-07`).

#### Entry `S3-03` — Stage 3 Completion & Mandatory Exit Gate Verification (2026-11-25 06:43 JST)
- **Stage 3 Exit Gate Matrix (per [REVIEW_SIGNOFF.md Section 1](file:///home/ordillo/tests/SLICES/docs/migration/REVIEW_SIGNOFF.md#L22-L27)):**

| Pre-Stage-4 Condition | Verification Evidence | Status |
|---|---|---|
| 1. Golden Baseline Suite 100% Pass + `ruff` Clean | `baseline` (`#23`): Pass A (`SLICES-upstream-baseline`) **`89/89` passed (`91.47 s`)**; Pass B (unmodified `SLICES`) **`89/89` passed (`90.99 s`)**; `381.8 KiB` fixtures; strict `ruff check tests/baseline/` **`0` errors** | **PASS** |
| 2. Clean Pre-Refactor Git Tree | `git diff upstream/main` empty prior to Wave 4A launch (only untracked `docs/migration/` and `tests/baseline/`) | **PASS** |
| 3. Immutable Baseline & Disk Headroom | `/home/ordillo/tests/SLICES-upstream-baseline` locked & read-only at `94ef8e079b69c37138159805e3c701b8df87a5d7`; `/` free space `9.7 GB` (`>= 9.0 GB`) | **PASS** |
| 4. Independent Sign-Off & Disjoint Wave Contracts | `reviewer` (`#21`): `APPROVED FOR STAGE 4` with `CA-01`–`CA-09`, `RUL-01`–`RUL-08`, pinned cross-wave contracts, and 27/27 `DEFERRED_CORE_REGISTER.md` dispositions synced | **PASS** |

- **Stage 3 Verdict:** **COMPLETE — 100% GREEN.** Stage 4 Wave 4A launched immediately (`#24`, `#25`, `#26`).

---

### Stage 4: Refactor & Additive Port (2026-11-25 06:44–07:34 JST — Completed)

#### Wave 4A Dispatch Matrix (Completed & Independently Verified at Gate 4A)

| Worker Slot | Agent (Tier) | Exclusive File Ownership | Key Directives & Rulings | Status |
|---|---|---|---|---|
| **Wave 4A-1** (`refactor-pkg`) | `baseline` (Carbon High) | Relocate `mp20_v4_benchmark_2383.csv` + `chemPotMP.json`; delete `MatterGPT/`, root clutter & MatterGPT `docs/` assets; update `pyproject.toml`, `uv.lock`, `.gitignore` | `CA-01`–`CA-03`, `CA-08`–`CA-09`, `RUL-05` (`tuna` `default=true`, PEP 735 `[dependency-groups]`, 0 core version drift) | **Completed** (2026-11-25 06:49 JST, `#30`) |
| **Wave 4A-2** (`refactor-core`) | `auditor-fork` (Carbon High) | `src/slices/exceptions.py` (new), `src/slices/__init__.py`, `src/slices/core.py` | `RUL-01` (`DEF-007`), `RUL-02`/`CA-06` (`DEF-013`), `RUL-03` (`DEF-005` frozen), `RUL-07`/`CA-05` (PEP 562 lazy `__init__.py`), 34 CJK lines -> English, additive `structure2SLICESAug_atom_order` & lazy `robust_SLICES2structure` | **Completed** (2026-11-25 07:00 JST, `#31`) |
| **Wave 4A-3** (`refactor-backends-utils`) | `architect` (Carbon High) | `src/slices/{utils.py, relax_backends.py, gfnff_helper.py, tobascco_net.py, config.py, utils_wyckoff.py}` (`_vendor/` untouched) | `RUL-04` (`_SUBMITTED_LOCAL_PROCS` replacing `pgrep`, `shutil`/`temporaryWorkingDirectory`, 182 CJK lines), `RUL-08`/`CA-04` (`mlip_relaxer` lazy hook, non-Linux `SLICES_XTB_PATH` fallback), `RUL-03` (`DEF-004`/`DEF-011` frozen, `clear_cache` + `nodes_iter`) | **Completed** (2026-11-25 07:09 JST, `#32`) |
| **Gate 4A Verification & Commits** | `reviewer` (Carbon High) | Independent audit, `ruff` + CJK=0 + `89/89` golden verification, local atomic commits `3-a`, `4A-a`, `4A-b` | Verify zero forbidden-path edits, zero math/lock drift, clean `git status` (`?? docs/migration/` only), zero pushes | **PASS** (2026-11-25 07:13 JST, `#34`) |

#### Entry `S4-01` — Wave 4A-1 Execution: `MatterGPT/` Removal, Fixture Relocation & Packaging (`baseline`, 2026-11-25 06:49 JST)
- **Executor / Report:** `baseline` (brief `#24`, completed `#30`; logged per `#38`).
- **Relocated Benchmark Fixtures (Verified Byte-Identical to `94ef8e0`):**
  - `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` -> `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` (`1,029,692 B` / `1,005.6 KiB`); existing 14,303-row `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` (`4,813,862 B`) verified untouched and byte-identical (`CA-03`).
  - `MatterGPT/2_decode/workflow/chemPotMP.json` -> `data/mp20_nonmetal/chemPotMP.json` (`1,862 B`).
- **Pruned Assets (`16,597,966 B` / `15.83 MiB` Net Removed):** Deleted `MatterGPT/` (`8,037,729 B` remaining after fixture relocation), root `__init__.py` (`1 B`), `entrypoint_set_cpus_gradio.sh` (`636 B`), `HANDOFF_workstation.md` (`9,560 B`), `src/slices/README.rst` (`59 B`), `docs/MatterGPT.jpg` (`1,709,498 B`), `docs/gui_snapshot.png` (`193,327 B`), `docs/huggingface_space.png` (`353,063 B`), CJK-named MatterGPT intro PDF under `docs/` (`6,272,092 B`), and CJK-named obsolete local-run `utils` copy under `docs/` (`22,001 B`). Preserved `docs/{SLICES_demo.png, figure_intro.png, win11_wsl2.png, migration/**}` (`CA-09`).
- **Packaging & Lockfile (`pyproject.toml`, `.gitignore`, `uv.lock`, `0` CJK hits):** Dropped `"einops"` and `gui = ["gradio"]`, retained `[[tool.uv.index]] name = "tuna"` (`default = true`), added `[project.scripts] slices = "slices.cli:main"`, PEP 735 `[dependency-groups] dev`, `[tool.ruff]` (`per-file-ignores "src/slices/core.py" = ["E402"]`, `extend-exclude`), and `[tool.pytest.ini_options]`; applied scoped `.gitignore` (`e37ce5e`, `!src/slices/_vendor/**`, zero blanket `*.csv`/`*.json`); regenerated `uv.lock` (`170 -> 136` `[[package]]` entries: `-39` Gradio/MatterGPT packages, `+5` `dev` packages; `/dev/shm/ordillo-uv-cache` cleaned) with **0 version drift** across all 10 core scientific packages (`torch 2.9.1`, `nequip 0.17.1`, `pymatgen`, `ase 3.29.0`, `scipy`, `numpy`, `networkx`, `spglib`, `matscipy 1.3.1`, `e3nn 0.6.0`).

#### Entry `S4-02` — Wave 4A-2 Execution: Structured Exceptions, Lazy Exports & Core Refactor (`auditor-fork`, 2026-11-25 07:00 JST)
- **Executor / Report:** `auditor-fork` (brief `#25`, completed `#31`; logged per `#38`).
- **Owned Files Delivered (`3` files, `0` CJK hits, `ruff check` `0` errors):**
  1. `src/slices/exceptions.py` (new, `77` lines): Implemented pinned `SLICESError` hierarchy (`SLICESEncodingError`, `SLICESDecodingError`, `GraphTopologyError` -> `LatticeBasisError`/`CocycleBasisError`, `GFNFFExecutionError` + `XTBExecutionError` alias, `MLIPRelaxationError`, `TimeoutException`) and sibling dual-inheriting `RelaxBackendError(SLICESError, RuntimeError)` & `ModelDownloadError(SLICESError, RuntimeError)` (`not issubclass(ModelDownloadError, RelaxBackendError)`), zero external dependencies.
  2. `src/slices/__init__.py` (`102` lines): Eagerly exports `__version__ = "4.0.2"` and exception hierarchy; implements PEP 562 `__getattr__` + `__dir__` (`CA-05`/`RUL-07`) for lazy `SLICES` and `check_SLICES(...)` (verified `env -u OMP_NUM_THREADS` leaves `OMP_NUM_THREADS` unset and `slices.core` unimported).
  3. `src/slices/core.py` (`2,678` lines): Preserved `core.py:5-9` env/warning header above imports (`DEF-005`/`RUL-03`) and all 22 frozen `DEF-*` math/algo behaviors; translated all 34 CJK lines to factual English; applied Stage 3 approved `DEF-007` (`TimeoutException` + POSIX main-thread `SIGALRM`, direct `yield` off-main-thread/Windows) and `DEF-013` (`if self.relaxer is None:` short-circuit in both `to_structures()` and `to_4structures()`); replaced 6 bare `except:` blocks with `except Exception:`; cleaned Google-style imports, `# === Section ===` dividers, stale docstrings, and PEP 604 type hints; added `structure2SLICESAug_atom_order` and lazy `robust_SLICES2structure`.
- **Local Smoke Checks:** `DEF-007` main-thread `SIGALRM` + worker-thread pass; `DEF-013` zero-stdout `relax_model=None`/`"none"` pass; `NdSiRu.cif` CPU `nequip-s+l` round-trip **`E = -7.26759387 eV/atom`** (exact 8-decimal parity to Stage 1).

#### Entry `S4-03` — Wave 4A-3 Execution: Backends, GFN-FF Fallback, Safe Job Utils & Frozen Graph/Data Modules (`architect`, 2026-11-25 07:09 JST)
- **Executor / Report:** `architect` (brief `#26`, completed `#32`; logged per `#38`).
- **Owned Files Delivered (`6` files, `src/slices/_vendor/**` untouched, `0` CJK hits, `ruff check` + Google pydocstyle `D` `0` errors):**
  1. `src/slices/config.py` (`296` lines) & `src/slices/utils_wyckoff.py` (`136` lines): Added Google docstrings, `__all__`, PEP 604 typing, removed 6 unused imports in `utils_wyckoff.py`; preserved all numeric/CSV constants and 230-SG bijection 100% invariant.
  2. `src/slices/gfnff_helper.py` (`307` lines): Imported `GFNFFExecutionError`; repointed provenance comments to `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv`; preserved Linux x86_64 bundled `libgfnff.so.0.1.1` ctypes path verbatim; added `(ImportError, OSError)`-gated `_run_external_xtb_fallback` (`RUL-08`); `python -m slices.gfnff_helper` self-test passed (`Na3MnCoNiO6` `(178.74144, 178.74144, 126, 61.23)`).
  3. `src/slices/relax_backends.py` (`874` lines): Imported sibling `RelaxBackendError`/`ModelDownloadError`; removed CJK L251; deleted `if name == "m3gnet": raise ValueError(...)` (`CA-04`); wired lazy `slices.mlip_relaxer.{resolve_optional_mlip, make_optional_relaxer}` delegation (`RUL-08`); kept all NequIP plans/constants/guards 100% invariant.
  4. `src/slices/utils.py` (`895` lines): Translated all 182 CJK lines; eliminated all `pgrep -f python`, `pgrep -f pt_main_thread`, indiscriminate `kill -9`, and `os.system` calls (`0` hits); implemented `_SUBMITTED_LOCAL_PROCS` (`Popen`, `start_new_session=(os.name != "nt")`) alongside `_SUBMITTED_SLURM_JOBS`; added `SLICES_FORCE_LOCAL=1`, `temporaryWorkingDirectory` wrappers, module `_logger`, and warning-free `adaptive_dynamic_binning`.
  5. `src/slices/tobascco_net.py` (`894` lines): Strictly preserved frozen `DEF-004` (`# noqa: F841`), `DEF-010`, `DEF-011` (`np.matrix.I`), `is_integral`, `get_lattice_basis`, and all topological math; added `Net.clear_cache()` and fixed `self._graph.nodes[node]` in `Net.nodes_iter(data=True)`.
- **Integrated Wave 4A Smoke:** All 6 modules import with `OMP_NUM_THREADS` unset and `slices.core` unimported; integrated working tree passed **`89/89` golden tests in `89.32 s`**.

#### Entry `S4-04` — Gate 4A Independent Verification & Local Atomic Commits (`reviewer`, 2026-11-25 07:13 JST)
- **Verifier / Report:** `reviewer` (brief `#33`, completed `#34`; SHAs cross-verified via `git log` by `scribe` per `#38`).
- **Independent Verification Results:**
  - **Forbidden Paths & Baseline Worktree:** `0` diffs across `src/slices/_vendor/**`, `HTS/**`, `benchmark/**`, `examples/**`, `tools/**`, `Dockerfile/**`, and existing `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` (byte-identical SHA-256 to `94ef8e0`). `R100` git renames verified on `mp20_v4_benchmark_2383.csv` (`1,029,692 B`) and `chemPotMP.json` (`1,862 B`). `/home/ordillo/tests/SLICES-upstream-baseline` untouched at `94ef8e0`; `/` free disk steady at **`9.7 GB`**.
  - **Freeze, Lazy-Import & Lockfile Audit:** Verified `DEF-001`, `DEF-004`, `DEF-005`, `DEF-010`, `DEF-011`, `DEF-014` frozen; `DEF-007` & `DEF-013` cleanly applied; `CA-05`/`RUL-07` lazy `__init__.py` leaves `slices.core` unimported and `OMP_NUM_THREADS` unset; `not issubclass(ModelDownloadError, RelaxBackendError)`; `0` `pgrep`/`os.system` in `utils.py`; **`0` version drift** across all 10 core packages in `uv.lock`.
  - **Lint, CJK & Independent Golden Suite:**
    - `ruff check --no-cache src/slices/ tests/baseline/`: **`All checks passed!` (`0` errors)**.
    - CJK scan across `src/slices/` (excl. `_vendor`), `tests/baseline/`, `pyproject.toml`, `.gitignore`: **`0` hits**.
    - Independent `PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH=/home/ordillo/tests/SLICES/src pytest -p no:cacheprovider tests/baseline/test_golden_equivalence.py`: **`89 passed`, `0 failed`, `0 skipped` in `88.68 s`** (`atol=1e-12`).
- **Local Atomic Commits Recorded on `slices-4-personal` (`0` Remote Pushes; `push.default=nothing`):**

| Tag | Short SHA | Full SHA | Timestamp (JST) | Commit Message | Diff Stat |
|---|---|---|---|---|---|
| `3-a` | `e0142f8` | `e0142f8f514a5a9c3e49907a31048763ed404614` | 2026-11-25 07:12:17 | `test(baseline): add frozen v4.0.2 golden equivalence harness` | `5 files changed, +4,603` |
| `4A-a` | `984416b` | `984416bfe3a08708254996ec35dd10bcc1e2493a` | 2026-11-25 07:12:17 | `chore: prune MatterGPT, relocate MP-20 benchmark fixtures, and clean packaging` | `85 files changed, +1,093 / -113,930` |
| `4A-b` | `49237f6` | `49237f659a88f9d9d22d5b60b09263c240276786` | 2026-11-25 07:12:17 | `refactor(slices): add exception hierarchy, lazy exports, and clean core modules` | `9 files changed, +4,055 / -2,859` |

- **Post-Commit Hygiene:** `git status --short` showed `?? docs/migration/` only. **Gate 4A Verdict: 100% PASS.**

#### Wave 4B Dispatch Matrix (Completed & Independently Verified at Gate 4B)

| Worker Slot | Agent (Tier) | Exclusive File Ownership | Key Directives & Rulings | Status |
|---|---|---|---|---|
| **Wave 4B-1a** (`port-additive-core`) | `auditor-fork` (Carbon High) | `src/slices/mlip_relaxer.py` (new), `src/slices/decoding_strategies.py` (new), `src/slices/cli.py` (new) | `RUL-08` optional MLIP adapters (`chgnet`, `mattersim`, `orbv3`, `mace`, `m3gnet`; zero import-time side effects), opt-in `robust_decode` fixing all 5 fork bugs, `slices` CLI (`encode`/`decode`/`validate`/`canonicalize`, exit code `1` on invalid) | **Completed** (2026-11-25 07:29 JST, `#42`) |
| **Wave 4B-1b** (`port-examples-tools`) | `architect` (Carbon High) | `examples/{2.1structure2SLICES_SLICES2structure.py, 2.2data_augmentation_get_canonical_slices.py, 3.benchmark_relax_models.py, test.py}`, `tools/{workstation_check.sh, validate_installation.py, run_tests.py}`, `tools/benchmarks/run_comparison_test.py` | `RUL-05` repoint `3.benchmark_relax_models.py` to `mp20_v4_benchmark_2383.csv` + `chemPotMP.json`, strip MatterGPT from `workstation_check.sh`, port/adapt v4.0.2 developer tools (`0` ruff errors, `0` CJK) | **Completed** (2026-11-25 07:25 JST, `#41`) |
| **Wave 4B-2** (`translate-baselines`) | `translate-baselines` (Neon XHigh) | `HTS/` (9 CJK files + `1_run.py` `L5` stray `*`), `benchmark/` (16 CJK files; `error.py` untouched), `data/` (3 CJK files), `Dockerfile/*` & root `{rundocker.sh, entrypoint_set_cpus.sh, slurm.conf, APIKEY.ini}` | `CA-01`, `CA-07`, `RUL-06` surgical CJK-to-English comments/docstrings/prints only (`0` algorithmic/data drift; `0` CJK; `py_compile` & `bash -n` 100% pass) | **Completed** (2026-11-25 07:20 JST, `#40`) |
| **Gate 4B Verification & Commits** | `reviewer` (Carbon High) | Independent audit, `ruff` + `compileall` + CJK=0 + CLI/tool smokes + `89/89` golden verification, local atomic commits `4B-a`, `4B-b` | Verify zero forbidden-path edits, zero baseline data drift, clean `git status` (`?? docs/migration/` only), zero pushes | **PASS** (2026-11-25 07:34 JST, `#45`) |

#### Entry `S4-05` — Wave 4B-2 Execution: Surgical CJK Translation of Kept Baselines & Docker Scripts (`translate-baselines`, 2026-11-25 07:20 JST)
- **Executor / Report:** `translate-baselines` (brief `#37`, completed `#40`; logged per `#49`).
- **Scope & Count Reconciliation (`32` Owned Files Modified, `+159 / -145` lines):**
  1. `HTS/` (`10` files): Translated CJK comments/docstrings in all `9` CJK files (`HTS/2_train_sample/{train_prior,transfer_userinpt}.py`, 7 `HTS/9_EAH_Band_gap_PBE/workflow/*.py`) and removed ONLY the stray `* ` syntax error on line 5 of `HTS/0_get_json_mp_api/2_filter_prior_3d/1_run.py` (`BC-3`).
  2. `benchmark/` (`16` files): Translated CJK comments/docstrings/`#SBATCH` notes in all `16` CJK files listed in `AUDIT_UPSTREAM_STYLE.md` Section 2.4 rows `#19`–`#34` (`3` `0_run.sh`, `1` `train_prior.py`, `2` `2_collect_clean_glob_details.py`, `6` `*_normal_distri_plot.py`, `4` `0_EnthalpyOfFormation*.py`), keeping `benchmark/.../error.py` and all data files untouched. *(Exact inventory note: rows `#10`–`#37` total `9 + 16 + 3 = 28` baseline CJK files rather than `30`; exhaustive scan confirmed zero remaining CJK files.)*
  3. `data/` (`3` files): Translated `#SBATCH` comments in `data/{mp20,mp20_nonmetal}/workflow/0_run.sh` and comments + `print(...)` labels in `data/mp20_nonmetal/2_stratified_sampling_split.py`.
  4. `Dockerfile/` & Root Scripts (`3` modified; `6` already clean): Translated `11` CJK comments in `Dockerfile/Dockerfile`; translated `3` CJK comments and parameterized volume mounts (`${SLICES_DATA_DIR:-..}:/crystal`, `${SLICES_DOCKER_DIR:-.}:/mnt`) in `Dockerfile/docker-compose.yml`; cleaned `rundocker.sh` (removed MatterGPT Gradio port `7860`, `entrypoint_set_cpus_gradio.sh`, and hardcoded personal/CJK paths; parameterized `SLICES_DATA_DIR`, `SLICES_IMAGE`, `SLICES_SHM_SIZE`). `Dockerfile/` retained at upstream path (`CA-01`).
- **Verification Results:**
  - Exhaustive CJK scan across all **`1,410` files** (contents + filenames) in `HTS/`, `benchmark/`, `data/`, `Dockerfile/`, and root scripts: **`0` hits**.
  - Syntax checks: `python3 -m py_compile` **`24/24` PASS**; `bash -n` **`9/9` PASS**; `yaml.safe_load` on `Dockerfile/docker-compose.yml` **PASS**.
  - AST zero-drift verification (`HEAD` vs working tree, excluding docstrings and `2_stratified_sampling_split.py` console labels): **`23/23` PASS**.

#### Entry `S4-06` — Wave 4B-1b Execution: `examples/` Refactor & v4.0.2 Developer Tools Port (`architect`, 2026-11-25 07:25 JST)
- **Executor / Report:** `architect` (brief `#36`, completed `#41`; logged per `#49`).
- **Owned Files Delivered (`8` files; CIF fixtures untouched; `0` CJK hits; `0` `MatterGPT`/`HANDOFF_workstation`/`flash_attn` hits):**
  1. `examples/*.py` (`4` files): Refactored `2.1structure2SLICES_SLICES2structure.py` (`38` L), `2.2data_augmentation_get_canonical_slices.py` (`38` L), `3.benchmark_relax_models.py` (`186` L; repointed `--csv` to `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` and `--chem-pot` to `data/mp20_nonmetal/chemPotMP.json` per `RUL-05`), and `test.py` (`28` L) to Google Python Style Guide while preserving exact outputs.
  2. `tools/workstation_check.sh` (`89` L): Removed MatterGPT Steps 4–5, `TRAIN_EPOCHS`, `DECODE_THREADS`, and `flash_attn` checks; retained Steps 1–3 and resource summary (`bash -n` PASS).
  3. Ported v4.0.2 developer tools (`3` new files): `tools/validate_installation.py` (`279` L), `tools/run_tests.py` (`190` L; `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `shell=False`), and `tools/benchmarks/run_comparison_test.py` (`299` L; graceful `[SKIP]` for uninstalled optional MLIPs).
- **Verification Results:** `ruff check --no-cache examples/ tools/` + Google pydocstyle `D` -> **`0` errors**; smoke runs passed on `2.1...py` (`-7.267593873805318 eV/atom`), `2.2...py` (`50 1`), `3.benchmark_relax_models.py --n 1 --models auto` (`0.37 s/structure`, `|eform - DFT| = 0.009 eV/atom` from relocated `mp20_v4_benchmark_2383.csv`), `tools/validate_installation.py --quick` (`exit=0`, methane GFN-FF + `NdSiRu.cif` 6-site `ZL*` round-trip), and `tools/benchmarks/run_comparison_test.py --n 1 --models auto chgnet` (`auto` `ok 1/1`, `chgnet` `[SKIP]`).

#### Entry `S4-07` — Wave 4B-1a Execution: Additive Optional MLIPs, Opt-In Decoding Strategies & CLI (`auditor-fork`, 2026-11-25 07:29 JST)
- **Executor / Report:** `auditor-fork` (brief `#35`, completed `#42`; logged per `#49`).
- **New Modules Delivered (`3` files, `0` CJK hits, `ruff check` + Google pydocstyle `D` `0` errors):**
  1. `src/slices/mlip_relaxer.py` (`703` lines): Implemented pinned `relax_backends.py` contract (`OPTIONAL_MLIP_MODELS`, `OPTIONAL_MLIP_ALIASES`, `resolve_optional_mlip`, `make_optional_relaxer`, `get_relaxer`, `mlip_available`, `choose_mlip_device`, `MLIPRelaxer`, `CHGNetRelaxer`, `MatterSimRelaxer`, `ORBv3Relaxer`, `MACERelaxer`, `M3GNetRelaxer`). Zero module-level imports of `torch`/`tensorflow`/MLIP libraries; `TF_USE_LEGACY_KERAS`/`tf_keras` scoped strictly inside `M3GNetRelaxer.__init__`; reuses `relax_backends` `preoptimize`/`_cell_filter`/`_collapse_guard`/`FIRE` retry with exact 5-key `NequIPRelaxer`-compatible return dicts and actionable `ImportError` hints.
  2. `src/slices/decoding_strategies.py` (`784` lines): Strictly opt-in `robust_decode`, `MultiStartOptimizer`, `AdaptiveConvergence`, `ProgressiveRelaxer`, `CycleBasisOptimizer`, `BondParameterFallback`, `is_approximately_integral`, and `calculate_topology_timeout` (`calculate_xtb_timeout` alias). Fixed all **5 fork bugs** (`AUDIT_FORK_DIFF.md` Sec 5.2): removed `scipy>=1.15` deprecated `iprint`/`disp`, isolated `np.random.default_rng(seed)` (`0` global RNG mutation), elementwise `is_approximately_integral`, SVD conditioning-scored `CycleBasisOptimizer`, modulo-safe 0-based `BondParameterFallback` + explicit `SLICESDecodingError` on encode-only `strategy=2`.
  3. `src/slices/cli.py` (`497` lines): Implements `[project.scripts] slices = "slices.cli:main"` (`--version`, `encode`, `decode`, `validate`, `canonicalize`, file/stdin/inline support); `relax_model=None` for non-relaxing subcommands, `relax_model="auto"` default on `decode`, exit code `1` on invalid SLICES or missing optional MLIPs.
- **Verification Results:** `env -u OMP_NUM_THREADS` confirmed `OMP_NUM_THREADS` unset and `torch`/`tensorflow`/`slices.core` unimported; `NdSiRu.cif` `robust_SLICES2structure` matched `SLICES2structure` bit-for-bit (`E = -7.267593873805318 eV/atom`, `|diff| = 0.0`); CLI smokes (`--version`, `encode`, `validate`, `canonicalize`, `decode`) all passed.

#### Entry `S4-08` — Gate 4B Independent Verification, Local Atomic Commits & Stage 4 Closeout (`reviewer`, 2026-11-25 07:34 JST)
- **Verifier / Report:** `reviewer` (brief `#43`, completed `#45`; SHAs cross-verified via `git log` by `scribe` per `#49`).
- **Independent Verification Results:**
  - **Forbidden Paths & Baseline Immutability:** `0` edits to Wave 4A `src/slices/*.py`, `src/slices/_vendor/**`, `benchmark/.../error.py`, or any CSV/JSON/ZIP/PKL/CKPT baseline files; zero stray `1.cif` or `__pycache__`. `/home/ordillo/tests/SLICES-upstream-baseline` untouched at `94ef8e0`; `/` steady at **`9.7 GB`** free.
  - **Lint, Syntax & Repo-Wide CJK Verification:**
    - `ruff check --no-cache src/ examples/ tools/ tests/baseline/`: **`All checks passed!` (`0` errors)**.
    - `python -m compileall -q -x 'error\.py' HTS/ benchmark/ data/`: **PASS (`0` syntax errors)**.
    - Repo-wide CJK scan across **`1,407` text files** (`src/`, `examples/`, `tools/`, `tests/baseline/`, `Dockerfile/`, `HTS/`, `benchmark/`, `data/`, root scripts): **`0` hits**.
  - **Additive Contract, CLI & Tool Smokes:** Verified zero import-time side effects in `mlip_relaxer.py`, `resolve_relax_model("auto") -> ("nequip-s+l", "cpu")`, clear `ImportError` on uninstalled optional MLIPs, `python -m slices.cli` (`--version` `slices 4.0.2`, `encode`, `validate` valid=`0`/invalid=`1`, `canonicalize`, `decode --relax-model none`), and `python tools/validate_installation.py --quick` PASS.
  - **Independent Golden Baseline Equivalence Run:**
    - `PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH=/home/ordillo/tests/SLICES/src pytest -p no:cacheprovider tests/baseline/test_golden_equivalence.py`: **`89 passed`, `0 failed`, `0 skipped` in `88.18 s`** (`atol=1e-12`).
- **Local Atomic Commits Created on `slices-4-personal` (`HEAD` = `479f0a2`; `0` Remote Pushes):**

| Tag | Short SHA | Full SHA | Timestamp (JST) | Commit Message | Diff Stat |
|---|---|---|---|---|---|
| `4B-a` | `1320773` | `13207735f5ccee259490b3cb7e157217f6bf12f6` | 2026-11-25 07:32:59 | `feat(slices): add optional multi-MLIP relaxers, decoding strategies, CLI, and v4.0.2 tools` | `11 files changed, +2,995 / -167` |
| `4B-b` | `479f0a2` | `479f0a261d213fb536aa7e5ac39a7a016bc200b6` | 2026-11-25 07:32:59 | `docs(baselines): translate CJK comments in HTS, benchmark, data, and Docker scripts` | `32 files changed, +159 / -145` |

- **Post-Commit Hygiene & Stage 4 Verdict:** `git status --short` showed `?? docs/migration/` only; cumulative Stage 3+4 history comprises **5 clean local atomic commits** (`e0142f8`, `984416b`, `49237f6`, `1320773`, `479f0a2`) ahead of `94ef8e0`. **Stage 4 Verdict: COMPLETE — 100% PASS.** Stage 5 (`Refine`) launched immediately (`#46`–`#48`).

---

### Stage 5: Refine, Types & Tests (2026-11-25 07:34–07:52 JST — Completed)

#### Stage 5 Dispatch Matrix (Completed & Independently Verified at Gate 5)

| Worker Slot | Agent (Tier) | Exclusive File Ownership | Key Directives | Status |
|---|---|---|---|---|
| **Stage 5A** (`tests-core`) | `baseline` (Carbon High) | `tests/{__init__.py, conftest.py}`, `tests/unit/{__init__.py, test_encoding.py, test_decoding.py, test_validation.py, test_graph.py, test_utils.py}`, `tests/integration/{__init__.py, test_round_trip.py}`, `tests/regression/{__init__.py, test_edge_cases.py}` | Port & expand core unit/integration/regression suites fixing all 9 legacy fork test bugs (`AUDIT_BASELINE_HARNESS.md`), testing `DEF-007`/`DEF-013`/`CA-01`–`CA-09`/`RUL-01`–`RUL-08`; `tests/baseline/**` untouched | **Completed** (2026-11-25 07:47 JST, `#53`) |
| **Stage 5B** (`tests-v4-additive`) | `auditor-fork` (Carbon High) | `tests/unit/{test_exceptions.py, test_relax_backends.py, test_gfnff_helper.py, test_mlip_relaxer.py, test_decoding_strategies.py, test_cli.py}` (self-contained, independent of `conftest.py`) | Author 6 new v4.0.2 & additive unit test suites (sibling dual-inheriting exceptions, NequIP/overlap/collapse guards, GFN-FF + mocked `xtb` fallback, mocked optional MLIPs + zero side effects, all 5 fixed `decoding_strategies` bugs, CLI exit codes & subcommands) | **Completed** (2026-11-25 07:46 JST, `#52`) |
| **Stage 5C** (`style-typing-polish`) | `architect` (Carbon High) | `src/slices/*.py` (excl. `_vendor/**`), `examples/*.py`, `tools/**/*.py`, `pyproject.toml` (`[tool.ruff]` section ONLY; no dependency/`uv.lock` edits) | Strict Google Python Style Guide audit (`E,F,W,I,B,UP,SIM,RUF,D` with `convention="google"`), non-behavioral polish respecting 100% Math/Algo Freeze (`DEF-004`/`005`/`010`/`011`/`014`), upgrade `[tool.ruff.lint]` in `pyproject.toml`, verify `0` ruff errors & `89/89` golden pass | **Completed** (2026-11-25 07:44 JST, `#51`) |
| **Gate 5 Verification & Commits** | `reviewer` (Carbon High) | Independent audit, AST invariance check, strict `ruff`, full unified `pytest tests/`, local atomic commits `5-a` & `5-b` | Verify zero forbidden-path edits, 100% AST parity on 5C, full test suite green, `git status` clean (`?? docs/migration/` only), zero pushes | **PASS** (2026-11-25 07:52 JST, `#55`) |

#### Entry `S5-01` — Stage 5A Execution: Core Unit, Integration & Regression Test Suite Port (`baseline`, 2026-11-25 07:47 JST)
- **Executor / Report:** `baseline` (brief `#46`, completed `#53`; logged per `#57`).
- **Delivered Files (`12` files, `1,353` total lines, `0` CJK hits; all 9 legacy fork test bugs fixed):**
  - `tests/__init__.py` (`1` L) & `tests/conftest.py` (`63` L; side-effect-free lazy fixtures leaving `OMP_NUM_THREADS`/`TF_USE_LEGACY_KERAS` untouched at collection).
  - `tests/unit/{__init__.py, test_encoding.py (197 L, 15 items), test_decoding.py (219 L, 15 items), test_validation.py (154 L, 18 items), test_graph.py (151 L, 5 items), test_utils.py (227 L, 8 items)}`: verified strategies 1–4, all 4 `graph_method`s, `to_primitive_if_smaller`, `DEF-007` main-thread/worker-thread `function_timeout`, `DEF-013` zero-stdout `relax_model=None`/`"none"`, `check_structural_validity` on `Structure`, `1..230` `utils_wyckoff` bijection, `Net.clear_cache()` & `nodes_iter`, `_SUBMITTED_LOCAL_PROCS` scoped cancellation sparing bystander processes, and warning-free `adaptive_dynamic_binning`.
  - `tests/integration/{__init__.py, test_round_trip.py (122 L, 7 items)}` & `tests/regression/{__init__.py, test_edge_cases.py (216 L, 7 items)}`: end-to-end NequIP/GFN-FF round-trips and regression guards for `CA-01`–`CA-09` and `RUL-01`–`RUL-08`.
- **Verification:** `75 passed, 0 failed, 0 skipped` in `28.76 s`; strict Google `ruff` `0` errors; `0` CJK hits.

#### Entry `S5-02` — Stage 5B Execution: Six New v4.0.2 & Additive Unit Test Suites (`auditor-fork`, 2026-11-25 07:46 JST)
- **Executor / Report:** `auditor-fork` (brief `#47`, completed `#52`; logged per `#57`).
- **Delivered Files (`6` self-contained unit suites, `1,490` total lines, `0` CJK hits):**
  1. `tests/unit/test_exceptions.py` (`174` L): full 11-subclass `SLICESError` hierarchy, `XTBExecutionError is GFNFFExecutionError`, sibling dual inheritance (`not issubclass(ModelDownloadError, RelaxBackendError)`), zero-side-effect import, and `function_timeout`.
  2. `tests/unit/test_relax_backends.py` (`323` L): `resolve_relax_model`, `CA-04` `m3gnet` unblock, `choose_device`, `closest_pair_ratio`, seeded `remove_overlaps`, `preoptimize`, `_collapse_guard`, all 4 `OPTIMIZERS`, `S + FIRE` collapse retry, and live cached CPU `NequIPRelaxer`.
  3. `tests/unit/test_gfnff_helper.py` (`215` L): `parse_nbf_text`, `_selected_params`, `_env_default`, live `@pytest.mark.gfnff` bundled `libgfnff` (methane, actinide `Th Z=90`, `Na3MnCoNiO6` reference target), and mocked `(ImportError, OSError)` `_run_external_xtb_fallback` with Fortran `"********"` sanitization.
  4. `tests/unit/test_mlip_relaxer.py` (`306` L): subprocess zero-side-effect import, aliases, uninstalled `ImportError` hints, mocked `_ASEMLIPRelaxer` 5-key contract + `FIRE` retry, mocked concrete adapters (`CHGNet`, `MatterSim`, `ORBv3`, `MACE`, `M3GNet` scoped Keras shim), and `@pytest.mark.mlip` live hooks.
  5. `tests/unit/test_decoding_strategies.py` (`239` L): spy guard proving freeze isolation of default `to_structures()`/`SLICES2structure()`, all 5 fixed fork bugs, and live `NdSiRu.cif` bit-for-bit parity (`atol=1e-12`).
  6. `tests/unit/test_cli.py` (`233` L): `python -m slices.cli` (`--version`, `encode`, `validate` valid=`0`/invalid=`1`, `canonicalize`, `decode` + `--robust` + uninstalled `--relax-model chgnet` exit `1`).
- **Verification (`91` items):** `86 passed, 5 skipped (@pytest.mark.mlip), 0 failed` in `18.70 s` (`18.22 s` with `-m "not mlip"`); strict Google `ruff` `0` errors; `0` CJK hits.

#### Entry `S5-03` — Stage 5C Execution: Strict Google Python Style Guide, Docstring & Typing Polish (`architect`, 2026-11-25 07:44 JST)
- **Executor / Report:** `architect` (brief `#48`, completed `#51`; logged per `#57`).
- **Configuration Upgrade (`pyproject.toml` `[tool.ruff]` ONLY, `+23` lines, `0` dependency/`uv.lock` edits):** Enabled `select = ["E", "F", "W", "I", "B", "UP", "SIM", "RUF", "D"]` with `[tool.ruff.lint.pydocstyle] convention = "google"` and minimal documented `per-file-ignores` (`core.py` `E402` for `DEF-005`, `utils_wyckoff.py` `E501` for frozen `sg_encoding`, `examples/3.benchmark_relax_models.py` `E402`, `tests/**/*.py` docstring/literal allowances).
- **Non-Behavioral Polish (`8 files changed, +77 / -49`):** Removed 42 obsolete `# noqa` tags (`RUF100`) and wrapped 7 lines `> 100` chars across 7 files (`core.py`, `cli.py`, `decoding_strategies.py`, `relax_backends.py`, `examples/3.benchmark_relax_models.py`, `tools/validate_installation.py`, `tools/benchmarks/run_comparison_test.py`).
- **Verification:** `ANN`/`UP` typing audit -> `0` errors (`100%` PEP 604 parameter & return coverage across 19 files); docstring-stripped `ast.dump` vs `479f0a2` -> **`100%` bit-identical ASTs**; `ruff check` -> `0` errors; `89/89` golden pass in `88.27 s` (`atol=1e-12`).

#### Entry `S5-04` — Gate 5 Independent Verification, Local Atomic Commits & Stage 5 Closeout (`reviewer`, 2026-11-25 07:52 JST)
- **Verifier / Report:** `reviewer` (brief `#54`, completed `#55`; SHAs cross-verified via `git log` by `scribe` per `#57`).
- **Independent Verification Results:**
  - **Disjoint Ownership & AST Invariance:** `0` edits to `src/slices/_vendor/**`, `tests/baseline/**`, `uv.lock`, `HTS/**`, `benchmark/**`, `data/**`, `Dockerfile/**`, or `rundocker.sh`; `100%` bit-identical docstring-stripped AST across all 7 Stage 5C `.py` files vs `479f0a2`; `/home/ordillo/tests/SLICES-upstream-baseline` untouched at `94ef8e0`; `/` steady at **`9.7 GB`** free.
  - **Static Analysis & CJK Scan:** `ruff check --no-cache src/ examples/ tools/ tests/` -> **`All checks passed!` (`0` errors)**; `python tools/run_tests.py --lint-only --no-cache` -> **`exit=0`**; CJK scan across `45` files -> **`0` hits**.
  - **Full Unified Pytest Suite (`PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH=src pytest -p no:cacheprovider tests/`):**
    - **`250 passed, 5 skipped, 0 failed` in `117.12 s`** (`255` collected: `89/89` frozen v4.0.2 golden baseline equivalence tests at `atol=1e-12`, `147` unit tests, `7` integration round-trip tests, `7` regression edge-case tests, and `5` clean `@pytest.mark.mlip` skips for uninstalled optional MLIPs).
- **Local Atomic Commits Created on `slices-4-personal` (`HEAD` = `8d9314b`, `7` commits ahead of `94ef8e0`; `0` Remote Pushes):**

| Tag | Short SHA | Full SHA | Timestamp (JST) | Commit Message | Diff Stat |
|---|---|---|---|---|---|
| `5-a` | `ad4446b` | `ad4446bdadde2df920456af816a5bcac3be26b87` | 2026-11-25 07:51:04 | `style(slices): enforce Google Python style ruff rules and polish docstrings/formatting` | `8 files changed, +77 / -49` |
| `5-b` | `8d9314b` | `8d9314bf2f5e9710666d5392ae8cd32c62db95b7` | 2026-11-25 07:51:04 | `test(slices): add comprehensive v4.0.2 unit, integration, and regression test suites` | `18 files changed, +2,843` |

- **Post-Commit Hygiene & Stage 5 Verdict:** `git status --short` showed `?? docs/migration/` only. **Stage 5 Verdict: COMPLETE — 100% PASS.** Stage 6 (`Document`) launched immediately (`#56`, `#57`).

---

### Stage 6: Document — 100% English (2026-11-25 07:53–08:04 JST — Completed)

#### Stage 6 Dispatch Matrix (Completed & Independently Verified at Gate 6)

| Worker Slot | Agent (Tier) | Exclusive File Ownership | Key Directives | Status |
|---|---|---|---|---|
| **Stage 6A** (`docs-primary`) | `translate-baselines` (Neon XHigh) | Stale Sphinx HTML cleanup in `docs/` (`26` tracked files removed; `SLICES_demo.png`, `figure_intro.png`, `win11_wsl2.png` preserved); `README.md`, `TECHNICAL.md`, `CHANGELOG.md`, `docs/README.md` | 100% factual scientific English (`0` CJK), zero MatterGPT or stale M3GNet-as-default claims, verified against `HEAD=8d9314b` and `git show 94ef8e0:HANDOFF_workstation.md` | **Completed** (2026-11-25 07:59 JST, `#58`) |
| **Stage 6B** (`docs-api-log`) | `scribe` (Neon XHigh) | `docs/api/API_{CORE,MLIP,DECODING_STRATEGIES,GRAPH,UTILITIES,CONFIG}.md`, `docs/migration/LAB_LOG.md`, `docs/migration/DEFERRED_CORE_REGISTER.md` | Primary-source AST-verified API reference suite against `HEAD=8d9314b` (`123/123` `__all__` exports, `52/52` `SLICES` methods), Stage 5/6 lab-log update, `DEF-007`/`DEF-013` resolution sync (`0` CJK) | **Completed** (2026-11-25 08:00 JST, `#59`) |
| **Gate 6 Verification & Commit** | `reviewer` (Carbon High) | Independent link/anchor/portability/API/CLI/CJK audit and local atomic commit `6-a` (`c7d2868`) | Verify zero forbidden-path edits, `0` broken links/anchors, `0` CJK across repo, clean `git status` (`?? docs/migration/` only), zero pushes | **PASS** (2026-11-25 08:04 JST, `#61`) |

#### Entry `S6-01` — Stage 6A Execution: Primary Repository Documentation & Stale Sphinx Cleanup (`translate-baselines`, 2026-11-25 07:59 JST)
- **Executor / Report:** `translate-baselines` (brief `#56`, completed `#58`; logged per `#63`).
- **Stale Sphinx Cleanup:** Removed all 13 legacy Sphinx HTML entries (`26` tracked files: `25` Sphinx build artifacts + `docs/jupyter.png`), preserving `docs/{SLICES_demo.png, figure_intro.png, win11_wsl2.png}`, `docs/api/**`, and `docs/migration/**`.
- **Delivered Primary Docs (`4` files, `0` CJK hits, `47/47` verified links, `0` promotional buzzwords, `0` stale `m3gnet`-as-default claims):**
  - `README.md` (`319` lines, `17,429 B`): Complete SLICES v4.0.2 guide (`uv` + Python 3.10+, Python API & `slices` CLI, CPU `nequip-s+l` + bundled GFN-FF + optional MLIPs + opt-in robust decoding, 2,383-structure MP-20 benchmark table, `tools/` runners, citations).
  - `TECHNICAL.md` (`252` lines, `25,145 B`): Deep architecture guide incorporating factual v4.0.2 NequIP/GFN-FF benchmark data extracted from `94ef8e0:HANDOFF_workstation.md`, Strategies 1–4 & 230-SG Wyckoff tokenization, primitive-cell reduction, `tobascco_net`, ZL* optimization, overlap/collapse safety, optional MLIPs, scoped `utils.py`, and baseline freeze invariant.
  - `CHANGELOG.md` (`102` lines, `10,713 B`): Chronological log covering `slices-4-personal` commits (`e0142f8`–`8d9314b`) and upstream `v1.0`–`v4.0.2`.
  - `docs/README.md` (`54` lines, `3,916 B`): Central documentation index linking primary docs, all 6 `docs/api/API_*.md` files, and `docs/migration/*.md`.

#### Entry `S6-02` — Stage 6B Execution: Primary-Source API Reference Suite & Stage 5/6 Record Sync (`scribe`, 2026-11-25 08:00 JST)
- **Executor / Report:** `scribe` (brief `#57`, completed `#59`).
- **API Reference Suite Created (`6` files under `docs/api/`, AST-verified against `HEAD=8d9314b`, `0` CJK hits, `0` hardcoded host paths, `100%` portable relative links):**
  - `API_CORE.md` (`199` L, `18,325 B`), `API_MLIP.md` (`139` L, `10,720 B`), `API_DECODING_STRATEGIES.md` (`139` L, `7,230 B`), `API_GRAPH.md` (`112` L, `9,099 B`), `API_UTILITIES.md` (`93` L, `9,071 B`), and `API_CONFIG.md` (`94` L, `8,614 B`) — verifying **`123/123` `__all__` exports across all 12 `src/slices/*.py` modules** plus **`52/52` public `SLICES` methods**.
- **Migration Records Synchronized:** Logged Stage 5 (`S5-01`–`S5-04`) in `LAB_LOG.md`; updated `DEF-007` and `DEF-013` in [DEFERRED_CORE_REGISTER.md](file:///home/ordillo/tests/SLICES/docs/migration/DEFERRED_CORE_REGISTER.md) to `Resolved in Stage 4` (`27/27` exact index<->detail Status parity).

#### Entry `S6-03` — Gate 6 Independent Verification, Local Atomic Commit & Stage 6 Closeout (`reviewer`, 2026-11-25 08:04 JST)
- **Verifier / Report:** `reviewer` (brief `#60`, completed `#61`; SHA cross-verified via `git log` by `scribe` per `#63`).
- **Independent Verification Results:**
  - **Forbidden Paths & Cleanup:** `0` edits outside Stage 6 docs; all `26` legacy Sphinx files removed (`docs/{SLICES_demo,figure_intro,win11_wsl2}.png` intact).
  - **Links, Anchors & Live Spot-Checks:** `0` broken relative file links, `0` broken `#anchor` slugs, `0` hardcoded host paths across all 10 Stage 6 docs; live verification of `slices.__version__ == "4.0.2"`, sibling exceptions, `SLICES.__init__`/`robust_SLICES2structure` defaults, all `__all__` export counts, `slices.cli` parser flags, and `--help` across all tools & examples **PASS**.
  - **Repo-Wide CJK Audit:**
    - Repository excluding `docs/migration/` & `_vendor/`: **`1,441` text files -> `0` CJK hits**.
    - `docs/migration/` (`7` files): `5/7` files (`AUDIT_FORK_DIFF.md`, `AUDIT_BASELINE_HARNESS.md`, `REVIEW_SIGNOFF.md`, `DEFERRED_CORE_REGISTER.md`, `LAB_LOG.md`) had `0` hits; `18` historical quoted CJK lines flagged in `PLAN.md` (`1` line: `L188`) and `AUDIT_UPSTREAM_STYLE.md` (`17` lines) for Stage 7B sanitization.
- **Local Atomic Commit Created on `slices-4-personal` (`HEAD` = `c7d2868`, `8` commits ahead of `94ef8e0`; `0` Remote Pushes):**

| Tag | Short SHA | Full SHA | Timestamp (JST) | Commit Message | Diff Stat |
|---|---|---|---|---|---|
| `6-a` | `c7d2868` | `c7d28683b53c46583dc0755fee0c639b298be187` | 2026-11-25 08:03:44 | `docs: rewrite README, TECHNICAL, CHANGELOG, and API reference suite in English` | `36 files changed, +1,402 / -5,422` |

- **Post-Commit Hygiene & Stage 6 Verdict:** `git status --short` showed `?? docs/migration/` only; `/` free space steady at **`9.7 GB`**. **Stage 6 Verdict: COMPLETE — 100% PASS.** Stage 7 launched (`#62`, `#63`).

---

### Stage 7: Systematize & Final Gate (2026-11-25 08:05–08:15 JST — Completed)

#### Stage 7 Dispatch Matrix (Completed & Independently Verified at Gate 7)

| Worker Slot | Agent (Tier) | Exclusive File Ownership | Key Directives | Status |
|---|---|---|---|---|
| **Stage 7A** (`pkg-wheel-hygiene`) | `architect` (Carbon High) | `pyproject.toml`, `setup.cfg`, `.gitignore`, `docs/README.md`, `CHANGELOG.md` (if needed) | Dry-run `uv build` (`sdist` + `wheel`) in `/dev/shm/slices-dist`, verify all 12 modules + 17 `_vendor/**` + `entry_points.txt`, test unpacked wheel import & CLI, clean `/dev/shm`, audit `git ls-files` hygiene, link `migration/FINAL_REPORT.md` in `docs/README.md` | **Completed** (2026-11-25 08:08 JST, `#64`) |
| **Stage 7B** (`migration-closeout`) | `scribe` (Neon XHigh) | `docs/migration/{PLAN.md, AUDIT_UPSTREAM_STYLE.md, LAB_LOG.md, FINAL_REPORT.md}` | Sanitize 18 historical quoted CJK lines (`0` CJK across 100% of `docs/migration/`), close Stage 6 & log Stage 7 (`S7-01`/`S7-02`) in `LAB_LOG.md`, author executive `FINAL_REPORT.md` | **Completed** (2026-11-25 08:09 JST, `#65`/`#67`) |
| **Gate 7 Final Sign-Off & Commit** | `reviewer` (Carbon High) | Final end-to-end verification gate, `LAB_LOG.md` `S7-03` seal, and final local commit `7-a` on `slices-4-personal` | Verify `ruff`, `compileall`, `validate_installation.py`, full `pytest`, live dual-tree parity, `0` CJK across 100% of repo + `docs/migration/`, `0` broken links, clean `git status`, `SLICES-upstream-baseline` untouched, `/` >= 5 GB, `0` remote pushes | **PASS** (2026-11-25 08:15 JST) |

#### Entry `S7-01` — Stage 7A Execution: Packaging, Wheel/sdist Build & Repository Hygiene Audit (`architect`, 2026-11-25 08:08 JST)
- **Executor / Report:** `architect` (brief `#62`, completed `#64`; logged by `scribe` per `#66`).
- **Dry-Run Packaging (`UV_CACHE_DIR=/dev/shm/ordillo-uv-cache uv build --out-dir /dev/shm/slices-dist`):**
  - Built `slices-4.0.2.tar.gz` (`9.1 MiB`, `49` entries) and `slices-4.0.2-py3-none-manylinux2014_x86_64.whl` (`9.1 MiB`, `37` entries — confirming `setup.cfg` `[bdist_wheel] plat_name = manylinux2014_x86_64` interoperability with `pyproject.toml`).
  - Archive inspection verified all **`12` `slices/*.py` modules**, `slices/nlopt.h`, all **`17` `slices/_vendor/**` files** (including `libgfnff.so.0.1.1`, 5 `gfnff.libs/*.so*` runtime libraries, `param_gfnff_legacy86.xtb`, and LGPL/MIT license files), and `entry_points.txt` (`[console_scripts] slices = slices.cli:main`), with **`0`** `__pycache__`, `.pyc`, `MatterGPT`, `1.cif`, or `test.slices` entries.
  - Unpacked wheel smoke test inside `/dev/shm/slices-wheel-check` (executed from `/dev/shm` outside repo CWD): imported `slices` directly from the unpacked wheel, ran `run_gfnff_helper` on methane (`4 bonds, 6 angles`), and invoked `python -m slices.cli --version` -> **`slices 4.0.2`** (**PASS**).
  - Cleaned 100% of temporary artifacts (`/dev/shm/slices-dist`, `/dev/shm/slices-wheel-check`, `/dev/shm/ordillo-uv-cache`, `build/`, `src/slices.egg-info`); `/` free disk steady at **`9.7 GB`**.
- **Repository Hygiene & Tooling Verification:**
  - Updated `docs/README.md` (`+1` line, `0` CJK) to link `[FINAL_REPORT.md](migration/FINAL_REPORT.md)` under `Migration and Audit Trail` (`pyproject.toml`, `setup.cfg`, `.gitignore`, and `CHANGELOG.md` required zero edits).
  - Audited `1,493` tracked entries in `git ls-files -s`: **`0`** broken gitlinks (`160000`), **`0`** `.egg-info`, **`0`** `MatterGPT` files, **`0`** `1.cif`/`test.slices`, and **`0`** `.pyc`/`__pycache__` in `src/`, `examples/`, `tools/`, `tests/`, or `docs/` (preserving only the 3 frozen historical `benchmark/.../2_train_sample/__pycache__/*.cpython-39.pyc` files per `RUL-06`).
  - Verified `tools/validate_installation.py --quick` (**PASS**, `exit=0`), `tools/run_tests.py --lint-only --no-cache` (**`0` errors**, `exit=0`), `slices-4-personal` (`c7d2868`), `backup/v3-personal` (`301c75f`), and locked read-only `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`) with `push.default=nothing`.

#### Entry `S7-02` — Stage 7B Execution: `docs/migration/` CJK Sanitization, Lab Log Update & `FINAL_REPORT.md` (`scribe`, 2026-11-25 08:08 JST)
- **Executor / Assignment:** `scribe` (Neon XHigh; brief `#63`).
- **CJK Sanitization (`18/18` Historical Quoted Lines Resolved):** Replaced raw CJK characters with English glosses and exact Unicode codepoint descriptors in `docs/migration/PLAN.md` (`1` line: `L188`) and `docs/migration/AUDIT_UPSTREAM_STYLE.md` (`17` lines: `L49, 51, 60, 61, 70, 71, 73, 82–88, 90, 143, 200`), preserving complete forensic traceability while reducing `docs/migration/` CJK hits from `18` to **`0`** (yielding **0 CJK hits across 100% of repository files**).
- **Executive Final Report Authored:** Created [FINAL_REPORT.md](file:///home/ordillo/tests/SLICES/docs/migration/FINAL_REPORT.md) synthesizing branch topology, 7-stage pipeline execution & model-tier delegation, complete local atomic commit ledger, quantitative verification scorecard, 27-entry Deferred Core Register disposition summary, and practical local maintenance & future upstream sync guide.
- **Verification:** Regex CJK scan across all 8 files in `docs/migration/` -> **`0` hits**; all relative links in `FINAL_REPORT.md` verified.

#### Entry `S7-03` — Final Gate 7 End-to-End Verification, Lab Log Seal & Final Local Commit (`reviewer`, 2026-11-25 08:15 JST)
- **Verifier / Assignment:** `reviewer` (Carbon High; brief `#68`).
- **End-to-End Verification Results:**
  - **100% Repo-Wide CJK Audit (Including `docs/migration/`):** Scanned **`1,449` non-binary text files** (`1,441` repository files + `8` `docs/migration/*.md` records) -> **`0` CJK hits** (`PASS`).
  - **Lint, Syntax & Tooling Gate:**
    - `ruff check --no-cache src/ examples/ tools/ tests/` -> **`All checks passed!` (`0` errors)**.
    - `python -m compileall -q -x 'error\.py' src/ examples/ tools/ tests/ HTS/ benchmark/ data/` (using transient `/dev/shm` bytecode prefix, immediately removed) -> **`0` syntax errors**.
    - `python tools/validate_installation.py --quick` -> **`exit=0`** (`SLICES v4.0.2 installation validation passed.`).
    - `python tools/run_tests.py --lint-only --no-cache` -> **`exit=0`** (`All checks passed!`).
  - **Markdown Link Audit:** Checked **`332` local links** across all `18` Markdown documents (`README.md`, `TECHNICAL.md`, `CHANGELOG.md`, `docs/README.md`, `6` `docs/api/*.md`, and `8` `docs/migration/*.md`) -> **`0` broken links**.
  - **Live Dual-Tree Subprocess Parity Probe (`/home/ordillo/tests/SLICES-upstream-baseline/src` vs `/home/ordillo/tests/SLICES/src`):**
    - `NdSiRu.cif` (`strategy=4`, `relax_model="auto"`): identical SLICES & canonical strings, `energy_diff = 0.000e+00`, `max_lattice_diff = 0.000e+00`, `max_frac_diff = 0.000e+00`.
    - `Sr3Ru2O7.cif` (`strategy=4`, `relax_model="auto"`): identical SLICES & canonical strings, `energy_diff = 0.000e+00`, `max_lattice_diff = 0.000e+00`, `max_frac_diff = 0.000e+00`.
  - **Full Unified Pytest Suite (`PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH=src pytest -p no:cacheprovider tests/`):**
    - **`250 passed, 5 skipped, 0 failed` in `116.92 s`** (`255` collected: `89/89` frozen v4.0.2 golden equivalence assertions at `atol=1e-12`, `147` unit tests, `7` integration round-trip tests, `7` regression edge-case tests, and `5` clean `@pytest.mark.mlip` skips for uninstalled optional MLIPs).
- **Final Local Commit (`7-a`) & Post-Commit Safety Invariants:**
  - Staged `docs/README.md` and `docs/migration/` (`8` files) and created final local commit `docs(migration): seal 7-stage scientific lab log, deferred register, and final report` (`9` linear atomic commits ahead of `upstream/main` @ `94ef8e0`).
  - Verified `git status --short` completely empty, `backup/v3-personal` @ `301c75f`, `upstream/main` @ `94ef8e0`, `/home/ordillo/tests/SLICES-upstream-baseline` locked & clean @ `94ef8e0`, `push.default=nothing` (**0 remote pushes**), and root `/` free disk **`9.7 GB` (`>= 5 GB`)**.
- **Final Migration Verdict:** **STAGE 1–7 COMPLETE — 100% VERIFIED & SEALED LOCALLY ON `slices-4-personal`.**
