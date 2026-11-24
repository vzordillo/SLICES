# SLICES v4.0.2 Migration — Final Scientific & Engineering Report

**Date:** 2026-11-25  
**Target Branch:** `slices-4-personal` (forked from `upstream/main` @ `94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`)  
**Personal Reference Branch:** `backup/v3-personal` (`origin/main` @ `301c75fcdfb2d553b616c30178ccc7b0161b1fe7`)  
**Immutable Baseline Worktree:** `/home/ordillo/tests/SLICES-upstream-baseline` (`94ef8e0`, detached, `git worktree lock`, `chmod -R a-w`)  
**Remote Policy:** **LOCAL-ONLY — ZERO REMOTE PUSHES** (`git config push.default nothing`)

---

## 1. Mission, Branch Topology & Governing Invariants

This migration ported personal software-engineering, structured exception, optional multi-MLIP, opt-in robust decoding, CLI, cross-platform safety, testing, and documentation improvements from `backup/v3-personal` (`vzordillo/SLICES`) onto the upstream **SLICES v4.0.2** codebase (`xiaohang007/SLICES`) while preserving **100% numerical and functional equivalence** with upstream v4.0.2 as a golden scientific baseline.

### Branch & Ancestry Architecture

| Ref / Worktree | Verified SHA / Tree | Role |
|---|---|---|
| `upstream/main` (`v4.0.2`) | `94ef8e079b69c37138159805e3c701b8df87a5d7` | Authoritative upstream v4.0.2 baseline (23 commits ahead of `142298b`) |
| `backup/v3-personal` (`origin/main`) | `301c75fcdfb2d553b616c30178ccc7b0161b1fe7` | Preserved personal fork snapshot (30 commits ahead of `cea17da`) |
| Verified Fork-Base Equivalence | `142298b^{tree} == cea17da^{tree} == e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9` | Proved bit-identical common tree despite rewritten history on `origin` |
| `slices-4-personal` (active branch) | `c7d2868` (8 local commits ahead of `94ef8e0`, plus Stage 7 final commit) | Clean linear history re-anchored directly on `upstream/main` (`94ef8e0`) |
| `/home/ordillo/tests/SLICES-upstream-baseline` | Detached `94ef8e0` (locked, read-only) | Physical reference tree for dual-tree golden equivalence verification |

### Invariants Enforced End-to-End
1. **Strict Math/Algorithm Freeze:** Upstream v4.0.2 NequIP (`relax_model="auto"` -> CPU `nequip-s+l`), bundled Linux `libgfnff` (`legacy86_overlay`), `config.py`, `utils_wyckoff.py`, `tobascco_net.py`, and `core.py` encoding/decoding/ZL* logic remain numerically invariant (`atol=1e-12`, `0.000e+00` CPU repeat variance).
2. **Additive Isolation:** Optional MLIP adapters (`mlip_relaxer.py`), opt-in recovery strategies (`decoding_strategies.py` / `robust_SLICES2structure`), CLI (`cli.py`), and non-Linux external `xtb` fallback (`gfnff_helper.py`) never alter default v4.0.2 execution or import-time side effects.
3. **Repository Scope:** `src/slices/`, `tests/`, `docs/`, `examples/`, `tools/`, `Dockerfile/`, `data/`, `benchmark/`, and `HTS/` preserved; `MatterGPT/` and legacy Sphinx HTML cleanly removed after relocating the 2,383-row Strategy-4 benchmark dataset and `chemPotMP.json` into `data/mp20_nonmetal/`.
4. **Local-Only & Storage Discipline:** Zero remote pushes (`push.default=nothing`); shared workspace toolchain under `/home/ordillo/tests/{.tools,.venv-upstream,.cache}` kept root `/` steady at `9.7 GB` free throughout all 7 stages.

---

## 2. Seven-Stage Pipeline Completion & Model-Tier Delegation

The migration followed a disciplined 7-stage scientific engineering workflow with independent verification gates and clean separation between **Carbon High** (architecture, code refactoring, test engineering, independent verification) and **Neon XHigh** (CJK translation, primary/API documentation, scientific lab logging):

| Stage | Phase | Key Deliverables | Independent Gate Result |
|---|---|---|---|
| **Stage 1** | Plan & Environment Setup | Repo/branch/worktree setup, `.tools`/`.venv-upstream`/`.cache`, [PLAN.md](PLAN.md) | Exact SHAs & tree match; smoke + `0.00e+00` CPU repeat variance; `0` tracked edits |
| **Stage 2** | Parallel Audit (3 Slices) | [AUDIT_FORK_DIFF.md](AUDIT_FORK_DIFF.md) (30 commits / 1,377 diffs), [AUDIT_UPSTREAM_STYLE.md](AUDIT_UPSTREAM_STYLE.md) (23 commits / 60 CJK files), [AUDIT_BASELINE_HARNESS.md](AUDIT_BASELINE_HARNESS.md) (19-crystal corpus), [LAB_LOG.md](LAB_LOG.md), [DEFERRED_CORE_REGISTER.md](DEFERRED_CORE_REGISTER.md) | 100% commit & CJK coverage; `30.52s`/`30.05s` dual-pass `0.000e+00` variance; 27 deduplicated register entries; `0` tracked edits |
| **Stage 3** | Review & Freeze Sign-Off | [REVIEW_SIGNOFF.md](REVIEW_SIGNOFF.md) (`CA-01`–`CA-09`, `RUL-01`–`RUL-08`), frozen `tests/baseline/` suite (`381.8 KiB` fixtures) | `APPROVED FOR STAGE 4`; Pass A (`91.47 s`) & Pass B (`90.99 s`) **`89/89` green**; strict `ruff` `0` errors |
| **Stage 4** | Refactor & Additive Port | Wave 4A (`MatterGPT/` prune + fixture relocation + `pyproject.toml`/`uv.lock` + core/exceptions/utils/backends refactor) & Wave 4B (`mlip_relaxer.py`, `decoding_strategies.py`, `cli.py`, `examples/`, `tools/`, 32 baseline/Docker CJK files) | Gate 4A (`88.68 s`) & Gate 4B (`88.18 s`) **`89/89` golden pass**; `0` ruff errors; `0` CJK across `1,407` files; `0` `uv.lock` core drift; 5 local commits |
| **Stage 5** | Refine, Types & Tests | Strict Google-style `[tool.ruff]` (`E,F,W,I,B,UP,SIM,RUF,D`), PEP 604 typing polish, 18 new/ported test files (`tests/{conftest,unit,integration,regression}`) fixing all 9 legacy fork test bugs | Gate 5 **`250 passed, 5 skipped, 0 failed` (`117.12 s`)**; `0` strict Google ruff errors; `100%` AST parity on style polish; 2 local commits |
| **Stage 6** | Document (100% English) | Rewritten [README.md](../../README.md), [TECHNICAL.md](../../TECHNICAL.md), [CHANGELOG.md](../../CHANGELOG.md), [docs/README.md](../README.md), 6 AST-verified `docs/api/API_*.md` files, `26` legacy Sphinx files removed | Gate 6 **`1,441` repo files `0` CJK hits**; `0` broken links/anchors; `123/123` `__all__` exports & `52/52` `SLICES` methods verified; live API/CLI spot-checks pass; 1 local commit |
| **Stage 7** | Systematize & Final Gate | Dry-run wheel/sdist build & repo hygiene audit (`7A`, `#64`), `docs/migration/` CJK sanitization (`18 -> 0`), finalized [LAB_LOG.md](LAB_LOG.md) & `FINAL_REPORT.md` (`7B`), Final Gate 7 sign-off & commit | `slices-4.0.2` wheel/sdist verified & unpacked smoke PASS; `0` CJK across **100% of files** incl. `docs/migration/`; `0` broken gitlinks/`.egg-info`; ready for Gate 7 commit |

---

## 3. Complete Local Atomic Commit Ledger (`slices-4-personal`)

All commits reside strictly on local branch `slices-4-personal` ahead of `upstream/main` (`94ef8e0`), with zero remote pushes:

| # | Stage Tag | Short SHA | Full SHA | Subject | Diff Summary |
|---|---|---|---|---|---|
| 1 | `3-a` | `e0142f8` | `e0142f8f514a5a9c3e49907a31048763ed404614` | `test(baseline): add frozen v4.0.2 golden equivalence harness` | `5 files, +4,603` |
| 2 | `4A-a` | `984416b` | `984416bfe3a08708254996ec35dd10bcc1e2493a` | `chore: prune MatterGPT, relocate MP-20 benchmark fixtures, and clean packaging` | `85 files, +1,093 / -113,930` |
| 3 | `4A-b` | `49237f6` | `49237f659a88f9d9d22d5b60b09263c240276786` | `refactor(slices): add exception hierarchy, lazy exports, and clean core modules` | `9 files, +4,055 / -2,859` |
| 4 | `4B-a` | `1320773` | `13207735f5ccee259490b3cb7e157217f6bf12f6` | `feat(slices): add optional multi-MLIP relaxers, decoding strategies, CLI, and v4.0.2 tools` | `11 files, +2,995 / -167` |
| 5 | `4B-b` | `479f0a2` | `479f0a261d213fb536aa7e5ac39a7a016bc200b6` | `docs(baselines): translate CJK comments in HTS, benchmark, data, and Docker scripts` | `32 files, +159 / -145` |
| 6 | `5-a` | `ad4446b` | `ad4446bdadde2df920456af816a5bcac3be26b87` | `style(slices): enforce Google Python style ruff rules and polish docstrings/formatting` | `8 files, +77 / -49` |
| 7 | `5-b` | `8d9314b` | `8d9314bf2f5e9710666d5392ae8cd32c62db95b7` | `test(slices): add comprehensive v4.0.2 unit, integration, and regression test suites` | `18 files, +2,843` |
| 8 | `6-a` | `c7d2868` | `c7d28683b53c46583dc0755fee0c639b298be187` | `docs: rewrite README, TECHNICAL, CHANGELOG, and API reference suite in English` | `36 files, +1,402 / -5,422` |
| 9 | `7-a` | *(Final Gate 7)* | *(Committed by `reviewer` at Gate 7)* | Final Stage 7 systematization polish & `docs/migration/` scientific record archive | `docs/migration/` + any Stage 7A index polish |

---

## 4. Quantitative Verification Scorecard

| Verification Metric | Target | Verified Measurement | Evidence Ref |
|---|---|---|---|
| **Unified `pytest tests/` Suite** | `0` failures | **`250 passed, 5 skipped (@pytest.mark.mlip), 0 failed`** (`117.12 s`) | `LAB_LOG.md` `S5-04` (`#55`) |
| **Frozen v4.0.2 Golden Equivalence** | `100%` pass (`atol=1e-12`) | **`89 / 89` passed** across 19 stratified crystals, 3 safety fixtures, 11 edge strings, 230 SGs (`0.000e+00` CPU repeat variance) | `S3-01`, `S4-04`, `S4-08`, `S5-04` |
| **Strict Google Python Style `ruff`** | `0` errors | **`0` errors** under `E,F,W,I,B,UP,SIM,RUF,D` (`convention="google"`) across `src/`, `examples/`, `tools/`, `tests/` | `S5-03`, `S5-04` (`#51`, `#55`) |
| **PEP 604 Type Annotation Coverage** | `100%` on code modules | **`0` `ANN`/`UP` errors** across all 19 files in `src/slices/`, `examples/`, `tools/` | `S5-03` (`#51`) |
| **AST Behavioral Invariance** | `0` unintended AST drift | **`100%` bit-identical ASTs** on Stage 5C polish (`7/7`) and **`23/23` AST equivalence** on baseline CJK translations | `S4-05`, `S5-04` (`#40`, `#55`) |
| **Repo-Wide CJK Character Count** | `0` hits | **`0` CJK hits** across `1,441` repo files **and** all `8` `docs/migration/` files (`18/18` historical quotes sanitized) | `S6-03`, `S7-02` (`#61`, `#63`) |
| **Core `uv.lock` Version Drift** | `0` core package upgrades | **`0` drift** across all 10 core scientific packages (`170 -> 136` entries: `-39` Gradio/MatterGPT, `+5` `dev`) | `S4-01`, `S4-04` (`#30`, `#34`) |
| **Storage Cleanup & Disk Headroom** | `/` >= `5 GB` free | **`15.83 MiB`** MatterGPT/clutter pruned + **`26`** legacy Sphinx files removed; `/` steady at **`9.7 GB` free** | `S4-01`, `S6-03` (`#30`, `#61`) |
| **API Reference Completeness** | `100%` public symbols | **`123 / 123` `__all__` exports** across all 12 `src/slices/*.py` modules + **`52 / 52` public `SLICES` methods**; `0` broken links | `S6-02`, `S6-03` (`#59`, `#61`) |
| **Workstation Safety (`utils.py`)** | `0` `pgrep` / `os.system` | **`0` hits** (`_SUBMITTED_LOCAL_PROCS` + `_SUBMITTED_SLURM_JOBS` verified in `test_utils.py` & `test_edge_cases.py`) | `S4-03`, `S5-01` (`#32`, `#53`) |
| **Packaging (`uv build` Wheel / sdist)** | Clean build + unpacked import/CLI | **`slices-4.0.2.tar.gz`** (`9.1 MiB`, `49` entries) & **`slices-4.0.2-py3-none-manylinux2014_x86_64.whl`** (`9.1 MiB`, `37` entries: `12/12` `slices/*.py` + `17/17` `_vendor/**` + `console_scripts` `slices = slices.cli:main`); unpacked `/dev/shm` import, methane GFN-FF (`4 bonds, 6 angles`), and `slices 4.0.2` CLI PASS; `0` broken gitlinks/`.egg-info`/`MatterGPT`; scratch cleaned | `S7-01` (`#64`) |

---

## 5. Deferred Core / Algorithm Register Summary (`27` Entries)

Every candidate defect, numerical quirk, or personal-fork algorithmic edit touching the frozen core was logged, deduplicated, and verified in [DEFERRED_CORE_REGISTER.md](DEFERRED_CORE_REGISTER.md):

| Disposition | Count | Entry IDs | Summary |
|---|---:|---|---|
| **Resolved in Stage 4 & Verified in Stage 5** | **2** | `DEF-007`, `DEF-013` | `DEF-007` (`RUL-01`): `TimeoutException` (`F821`) + POSIX main-thread `SIGALRM` scoping; `DEF-013` (`RUL-02`/`CA-06`): zero-stdout `if self.relaxer is None:` short-circuit in `to_structures()` & `to_4structures()`. Both verified in commit `49237f6` and `tests/unit/test_{exceptions,decoding}.py` (`8d9314b`) with zero normal-path mathematical drift. |
| **Blocked / Resolved Upstream** | **3** | `DEF-016`, `DEF-017`, `DEF-020` | Fork regressions permanently excluded from core (`from_SLICES` header error swallowing, deprecated `with_local_env_strategy` already fixed upstream in `2635bcc`, global root-logger `CRITICAL` & eager `tf_keras` monkey-patching). |
| **Frozen — Deferred (Baseline Preserved)** | **22** | `DEF-001`–`DEF-006`, `DEF-008`–`DEF-012`, `DEF-014`–`DEF-015`, `DEF-018`–`DEF-019`, `DEF-021`–`DEF-027` | Preserved verbatim at upstream v4.0.2 for golden baseline parity. Highest-value post-baseline research candidates for controlled A/B benchmarking on MP-20 (`data/mp20_nonmetal/mp20_v4_benchmark_2383.csv`): `DEF-001` (heteronuclear LJ `i[0]`-twice indexing), `DEF-008` (`relax_large_cell2` `fmax`/`steps`), `DEF-009` (`ExpCellFilter` -> `FrechetCellFilter`), `DEF-014`/`DEF-011`/`DEF-005` (`lattice_type` float tolerance + `np.linalg.inv` + scoped `OMP_NUM_THREADS`), `DEF-021` (`check_SLICES` `-1` handling), and `DEF-002`/`DEF-003` (benchmarking opt-in `robust_decode` against v4.0.2 NequIP). |

---

## 6. Local Maintenance, Verification & Future Upstream Sync Guide

### 6.1 Reproducible One-Command Verification
With `/home/ordillo/tests/.venv-upstream` and `/home/ordillo/tests/.tools/bin` on `PATH` (and `NEQUIP_CACHE_DIR`, `SLICES_MODEL_CACHE`, `PYTHONDONTWRITEBYTECODE=1` set):

```bash
# Lint + full test suite (unit, integration, regression, and 89 golden baseline checks)
python tools/run_tests.py --lint --no-cache

# Live installation & GFN-FF/NequIP/CLI sanity check
python tools/validate_installation.py --quick

# Standalone golden equivalence check against immutable SLICES-upstream-baseline
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 PYTHONPATH=src \
  pytest -p no:cacheprovider tests/baseline/test_golden_equivalence.py
```

### 6.2 Syncing Future Upstream `xiaohang007/SLICES` Releases
Because `slices-4-personal` is cleanly anchored on `upstream/main` (`94ef8e0`) with additive features isolated in dedicated modules (`exceptions.py`, `mlip_relaxer.py`, `decoding_strategies.py`, `cli.py`, `tests/`), pulling future upstream releases (e.g., `v4.1.x`) is straightforward:

```bash
git fetch upstream
git checkout slices-4-personal
git merge upstream/main          # or git rebase upstream/main on a fresh feature branch
python tools/run_tests.py --lint --no-cache
```

If an upstream update intentionally modifies core math or NequIP defaults, regenerate golden snapshots against the new upstream tag via `tests/baseline/generate_golden.py` and record the baseline transition in [LAB_LOG.md](LAB_LOG.md).

### 6.3 Publishing to GitHub (Manual Opt-In Only)
This repository deliberately sets `git config --local push.default nothing` to block accidental pushes. When you have reviewed `git log upstream/main..slices-4-personal` and wish to publish explicitly to your personal remote:

```bash
git push -u origin slices-4-personal
# Keep backup/v3-personal archived locally or push separately if desired:
# git push -u origin backup/v3-personal
```
