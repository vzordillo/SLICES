# Stage 2 Audit (Slice 2B): Upstream v4.0.2 Architecture, Scope Coupling & CJK/Style Audit

**Date:** 2026-11-25  
**Auditor:** `architect` (Slice 2B)  
**Audited Target:** `upstream/main` (`94ef8e079b69c37138159805e3c701b8df87a5d7`, tag `v4.0.2`)  
**Audited Commit Range:** `142298be4f83ab161d51298c82e74e94c3319891..94ef8e079b69c37138159805e3c701b8df87a5d7` (23 commits)  
**Source Modifications Made:** None (strictly read-only audit)

---

## 1. Complete 23-Commit Upstream Evolution Ledger (`142298b..94ef8e0`)

Between the fork-base (`142298b`, tree `e36d7ff08bd4a9a8f9a5dcbeb6471d1249b2b5d9`) and `upstream/main` (`94ef8e0`, SLICES `v4.0.2`), upstream landed **23 commits** (`216 files changed, +19,832 / -1,802,081 lines`).

| # | Short SHA | Date | Author | Subject | Touched Scope & Migration Relevance |
|---|---|---|---|---|---|
| 1 | `931b3b0` | 2025-12-19 | YJC-log | SQLite lookup table optimization for post-decode `novelty_check` (>100x speedup) | `MatterGPT/` & `MatterGPT_no_flash/` only (`DROP_WITH_MATTERGPT` in Stage 4) |
| 2 | `ed6af0f` | 2025-12-21 | YJC-log | Optimize novelty check process and add terminal prompts | `MatterGPT/` & `MatterGPT_no_flash/` only (`DROP_WITH_MATTERGPT`) |
| 3 | `d9b3d79` | 2025-12-21 | Hang Xiao | Merge PR #21 (`optimized_novelty_check_process_add_terminal_prompts`) | Merge commit for #1–#2 |
| 4 | `1b26fb5` | 2026-01-23 | Hang Xiao | Fix bug in demo file | `MatterGPT*/demo_decode_novelty_check_eform_m3gnet/workflow/script.py` only |
| 5 | `5ac90d9` | 2026-02-27 | Hang Xiao | RTX 50 Series Support, Unified Flash-Attention Fallback, and Tutorial Refinements | **Deleted entire `MatterGPT_no_flash/` directory** (`-1,705,095` lines) and `MatterGPT/raw_mp20_dataset.csv`; added `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` (2,383 rows) |
| 6 | `a3d76a3` | 2026-03-03 | Hang Xiao | `multi-threads novelty check` | `MatterGPT/` & `README.md` only |
| 7 | `da0d873` | 2026-11-06 | Hang Xiao | Reduce structures to primitive cells before SLICES encoding | **CORE (`FROZEN`):** Added `to_primitive_if_smaller`, `_run_with_primitive_fallback`, `_crystal_graph_rep`, `_first_element_index` to [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py); updated `structure2SLICES`, `structure2randomSLICES`, `from_cif`, `SLICES2formula`, `get_slices1..3` (`space_group_num=None`), `data/mp20_nonmetal/workflow/0_run.py` |
| 8 | `eb1f6c9` | 2026-11-08 | Hang Xiao | Add `relax_model="auto"` with NequIP force fields | **CORE (`FROZEN`):** Added [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py) (`NequIP-OAM-S/M/L`), [3.benchmark_relax_models.py](file:///home/ordillo/tests/SLICES/examples/3.benchmark_relax_models.py); switched `SLICES.__init__` default `relax_model="auto"` |
| 9 | `119afaf` | 2026-11-08 | Hang Xiao | Switch to `uv` with Python 3.10 and drop M3GNet/TensorFlow | **PACKAGING & CORE:** Rewrote [pyproject.toml](file:///home/ordillo/tests/SLICES/pyproject.toml), added `.python-version` (`3.10`) & `uv.lock`; deleted `src/slices/MP-2021.2.8-EFS/*`, `src/slices.egg-info/*`, `src/slices/__pycache__/*`; removed `distutils` in [tobascco_net.py](file:///home/ordillo/tests/SLICES/src/slices/tobascco_net.py); **introduced `F821` undefined `TimeoutException` bug in `core.py:60`** |
| 10 | `aff08cf` | 2026-11-08 | Hang Xiao | Add workstation handoff and one-command GPU test script | Added [HANDOFF_workstation.md](file:///home/ordillo/tests/SLICES/HANDOFF_workstation.md) & [workstation_check.sh](file:///home/ordillo/tests/SLICES/tools/workstation_check.sh) |
| 11 | `a7efb1b` | 2026-11-08 | Hang Xiao | Make the xtb helper executable so decoding works on native Linux checkouts | Transient `xtb` permission fix (superseded by #12–#13) |
| 12 | `d40c909` | 2026-11-08 | Hang Xiao | Decode with the bundled open-source GFN-FF instead of the xtb binary | **CORE (`FROZEN`):** Added `src/slices/_vendor/gfnff*` (`libgfnff.so.0.1.1`, `gfnff.libs/*`, `param_gfnff_legacy86.xtb`) & [gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py); fixed `core.py:1018` `neighbor_list[19, i] = len(row)` (`<=19` cap) |
| 13 | `4e5a9d9` | 2026-11-08 | Hang Xiao | Remove the xtb helper; decode only with the bundled GFN-FF | Deleted 60.8 MB `src/slices/xtb_noring_nooutput_nostdout_noCN`; removed `/dev/shm` subprocess `XTB_MOD_PATH` calls in `core.py` (`get_inner_p_target*`) |
| 14 | `b600715` | 2026-11-08 | Hang Xiao | Let decoding use the GPU; track only the SLURM jobs SLICES submits | Added `_SUBMITTED_SLURM_JOBS`, `_submit_slurm_job`, `_run_local_job` in [utils.py](file:///home/ordillo/tests/SLICES/src/slices/utils.py) *(must preserve when porting OS-agnostic `utils.py` improvements!)* |
| 15 | `315d4f0` | 2026-11-09 | Hang Xiao | Decode on the CPU with `nequip-s+l` by default; stop relaxations from hanging | **CORE (`FROZEN`):** Defaulted `SLICES_DEVICE=cpu` (`auto` -> `nequip-s+l`); added `preoptimize`, `remove_overlaps`, `closest_pair_ratio`, `_collapse_guard`, and `CellCollapse` FIRE retry in `relax_backends.py` |
| 16 | `a096d91` | 2026-11-09 | Hang Xiao | Silence nequip's chemical-species map warning when loading NequIP models | Added `chemical_species_to_atom_type_map=True` in `relax_backends.py:314` |
| 17 | `9cc10fa` | 2026-11-09 | Hang Xiao | MatterGPT jobs: use the submitting interpreter; load force fields once per 10 SLICES | `MatterGPT/` scripts only |
| 18 | `9cc8879` | 2026-11-09 | Hang Xiao | MatterGPT: neutral names instead of M3GNet/CHGNet; remove the cancel-all scripts | `MatterGPT/` scripts only |
| 19 | `08a718b` | 2026-11-09 | Hang Xiao | Prepare the 4.0.0 PyPI release: version, platform-tagged wheel, install docs | Added [setup.cfg](file:///home/ordillo/tests/SLICES/setup.cfg) (`manylinux2014_x86_64`), bumped `pyproject.toml` to `4.0.0`, rewrote `README.md` install section in Chinese |
| 20 | `84da90f` | 2026-11-09 | Hang Xiao | Merge SLICES 4.0 (#24): uv environment, NequIP force fields, open-source GFN-FF decoder | Merge commit for SLICES 4.0 |
| 21 | `2635bcc` | 2026-11-09 | Hang Xiao | Fix import and runtime errors with current pymatgen and scipy | **CORE (`FROZEN`):** `StructureGraph.from_local_env_strategy`, `BrunnerNNReciprocal` import fallback (`pymatgen>=2026.3`), removed deprecated `iprint=-1` & `disp=None` from `fmin_l_bfgs_b` (`scipy>=1.15`) in `core.py` |
| 22 | `47bbd6e` | 2026-11-09 | Hang Xiao | Release 4.0.1 | Version bump `4.0.1` in `pyproject.toml` & `uv.lock` |
| 23 | `94ef8e0` | 2026-11-09 | Hang Xiao | Retry NequIP weight downloads with timeouts; release 4.0.2 | Added `ModelDownloadError`, `_download_model`, `_short_error`, retry/timeout constants in `relax_backends.py` (with 1 CJK line at L251); bumped `4.0.2` |

> [!NOTE]
> **Critical Divergence Alert vs `backup/v3-personal`:** `backup/v3-personal` (`301c75f`) was built on `142298b` (`StructureGraph.with_local_env_strategy`, `fmin_l_bfgs_b(..., iprint=-1, disp=None)`, `neighbor_list[19, i] = total`, no primitive-cell pre-reduction, M3GNet + `xtb` subprocess). Stage 4 MUST keep upstream `94ef8e0`'s implementations of all items in commits `#7, #8, #9, #12, #13, #14, #15, #16, #21, #23` and **never** overwrite them with older `backup/v3-personal` hunks.

---

## 2. Exhaustive CJK & Translation Ledger

### 2.1 Reconciliation of Hit Counts & Programmatic Parsing Verification
- **Count Reconciliation:** Stage 1's quick suffix-filtered scan reported `59` hits (`2` filenames + `57` suffixed text files). Scanning **all** non-binary files regardless of extension on `upstream/main` (`94ef8e0`, excluding Stage 1's newly created `docs/migration/PLAN.md`) identifies **60 distinct upstream files** (**2** CJK filenames + **59** CJK content files, with `docs/utils_<CJK-force-local:\u5f3a\u5236\u672c\u5730\u8fd0\u884c>.py` appearing in both; extensionless `Dockerfile/Dockerfile` accounted for the 2-count difference).
- **Programmatic Parsing Check (Verified Safe):** Every non-comment Python CJK string literal across all `.py` files in the repository was extracted and inspected. Outside `MatterGPT/` (deleted in Stage 4), executable CJK literals occur **exclusively** in:
  1. Docstrings (`src/slices/core.py:729-731`, `src/slices/utils.py`, `docs/utils_<CJK-force-local:\u5f3a\u5236\u672c\u5730\u8fd0\u884c>.py`, and module-top CJK docstring `<CJK: "Read structure file, automatically compute formation enthalpy">` in 11 `HTS/` & `benchmark/` PBE workflow scripts);
  2. Human-facing `print(...)` / `logging.*(...)` console messages (`src/slices/core.py:753,813,828,840`, `src/slices/utils.py`, `data/mp20_nonmetal/2_stratified_sampling_split.py`);
  3. One human-facing error message line in `ModelDownloadError` (`src/slices/relax_backends.py:251`).
  **Zero** code paths parse, compare (`==`, `in`, `re.*`), or key dictionaries/CSVs on CJK text. Translating all kept CJK text to English has **zero behavioral risk**.

### 2.2 Category A — Core Library (`src/slices/`): **MUST TRANSLATE IN STAGE 4** (3 files, 217 lines)

| # | File | CJK Lines | Exact Line Numbers & Content Purpose | Stage 4 Action |
|---|---|---|---|---|
| 1 | [core.py](file:///home/ordillo/tests/SLICES/src/slices/core.py) | 34 | `L729-731` (`structure2randomSLICES` docstring); `L733,740,743,754-755,758-759,762,767,772,777,780,782,792,794,797,799,802,814,818,827,831,834,838,842` (inline comments in `structure2randomSLICES`); `L753,813,828,840` (`print(...)` warnings/errors in `structure2randomSLICES`); `L1593` (`func` CJK comment gloss: `# inner_p units are Angstrom squared`); `L1660` (`func_check` CJK comment gloss: `# inner_p units are Angstrom squared`) | Translate docstring to Google style, translate comments and `print` warnings to English; also replace fullwidth punctuation (`U+FF0C`, `U+FF08`, `U+FF09`) and Unicode minus `U+2212` (`L502`) |
| 2 | [relax_backends.py](file:///home/ordillo/tests/SLICES/src/slices/relax_backends.py) | 1 | `L251` inside `_download_model` `ModelDownloadError`: CJK network-download error message (`<CJK: "Network issue, force-field weight download failed; check network and re-run (will retry automatically).">`, redundant duplicate of English L249–250 & L252) | Remove redundant Chinese line L251 (English error on L249–250 + L252 already states the exact cause, retry behavior, and `SLICES_NEQUIP_MODEL_<size>` fallback) |
| 3 | [utils.py](file:///home/ordillo/tests/SLICES/src/slices/utils.py) | 182 | `L21` (import comment); `L44-45` (`is_slurm_available` docstring); `L77-132` (`splitRun` docstring, comments, `print`s); `L135-176` (`splitRun_csv` comments, `print`s); `L202-451` (`show_progress` comments, `print`s, `logging` calls); `L456-543` (`cancel_all_jobs` comments, `print`s, `logging` calls); `L622-684` (`determine_bin_count` & `adaptive_dynamic_binning` comments, `print`s); `L692-793` (`parallel_process_json` & `parallel_process_csv` docstrings, comments, `print`s) | Full English translation + Google-style docstrings + safe process/file refactoring (see Section 5.2) |

### 2.3 Category B — Top-Level Docs, Configs & Docker: **TRANSLATE / REPLACE / PRUNE** (6 files)

| # | File | Filename CJK? | CJK Lines | Content Purpose & Stage 4/6 Action |
|---|---|---|---|---|
| 4 | [README.md](file:///home/ordillo/tests/SLICES/README.md) | No | 70 (`L7-191`) | Bilibili link labels (`L7-8,44`), Figshare description (`L14-15`), MatterGPT GUI header/tutorial links (`L31,45`), entire `uv` local install & NequIP guide (`L57-136`), entire Docker guide (`L139-191`). **Action (Stage 6):** Rewrite in 100% factual English, removing MatterGPT GUI/training sections while preserving v4.0.2 `uv` + NequIP + CLI + optional MLIP documentation |
| 5 | [HANDOFF_workstation.md](file:///home/ordillo/tests/SLICES/HANDOFF_workstation.md) | No | 67 (`L1-101`) | Internal Chinese developer handoff memo for testing the `refactor-uv` branch on a workstation. **Action (Stage 4/6):** Extract benchmark metrics & NequIP/GFN-FF design notes into English `TECHNICAL.md` / `docs/migration/LAB_LOG.md`, then delete `HANDOFF_workstation.md` from repo root |
| 6 | `docs/SLICES-MatterGPT_<CJK-intro:\u4ecb\u7ecd>.pdf` | **Yes** | Binary PDF (6.27 MB) | Legacy Chinese MatterGPT presentation PDF inside pre-built Sphinx `docs/`. **Action (Stage 4):** `git rm` (removes 6.3 MB + CJK filename + MatterGPT artifact) |
| 7 | `docs/utils_<CJK-force-local:\u5f3a\u5236\u672c\u5730\u8fd0\u884c>.py` | **Yes** | 129 (`L21-515`) | Obsolete copy of `src/slices/utils.py` with SLURM detection stripped out (verified via `diff -u`). **Action (Stage 4):** `git rm` (if local-only override is desired in `utils.py`, support `SLICES_FORCE_LOCAL=1` env var cleanly in `src/slices/utils.py`) |
| 8 | [Dockerfile/Dockerfile](file:///home/ordillo/tests/SLICES/Dockerfile/Dockerfile) & [Dockerfile/docker-compose.yml](file:///home/ordillo/tests/SLICES/Dockerfile/docker-compose.yml) | No | 11 (`L1-84`) + 3 (`L11-16`) | Chinese comments in legacy CUDA 12.1 / `slices==2.0.2` Docker files. **Action (Stage 4/6):** Translate comments to English and organize under `docker/` (as in `backup/v3-personal`) with clear legacy/v4 notes |
| 9 | [rundocker.sh](file:///home/ordillo/tests/SLICES/rundocker.sh) | No | 1 (`L2`) | Hardcoded author path `/media/xxx007/<CJK-new-volume:\u65b0\u52a0\u5377>/SLICES2:/crystal` + `C:\Users\admin\Desktop\...` on L1. **Action (Stage 4):** Parameterize host path (`$(pwd):/crystal`), remove MatterGPT Gradio command, and move/clean under `docker/` or `configs/` |

### 2.4 Category C — Kept Baseline Directories (`HTS/`, `benchmark/`, `data/`): **TRANSLATE COMMENTS/STRINGS ONLY** (30 files)

> [!IMPORTANT]
> To preserve baseline reproducibility in `HTS/`, `benchmark/`, and `data/`, translate **only** comments, module docstrings, and console `print` labels — do **not** alter any CSV/JSON data files, numerical thresholds, or output file schemas.

| # | File(s) | CJK Lines | Exact Lines & Content | Stage 4/6 Action |
|---|---|---|---|---|
| 10–11 | `HTS/2_train_sample/{train_prior.py,transfer_userinpt.py}` | 1 + 1 | `L75` / `L88`: trailing CJK inline comment (`<CJK: "issue with this line">`) | Translate comment (`# progress output newline`) |
| 12–18 | `HTS/9_EAH_Band_gap_PBE/workflow/{0_EnthalpyOfFormation0.5.py,0_EnthalpyOfFormation0.py,0_EnthalpyOfFormation1.py,0_band.py,0_scf.py,1_band.py,1_scf.py}` (7 files) | 3, 3, 1, 1, 1, 1, 1 | `L6` (`<CJK: "Read structure file, automatically compute formation enthalpy">`), plus `L20` (`<CJK: "Read chemical potential database">`) & `L22` (`<CJK: "Prepare energy calculation folder">`) in `0_EnthalpyOfFormation{0,0.5}.py` | Translate docstrings & comments to English |
| 19–21 | `benchmark/{1_Match_rate_MP-20/template,2_Match_rate_MP-21-40/1_get_json_mp_api/1_filter_prior_3d,2_Match_rate_MP-21-40/2_matchcheck3/template}/workflow/0_run.sh` (3 files) | 8 each (24) | `L2-7,11,15`: SLURM `#SBATCH` inline CJK comments (`<CJK: "Request 1 node">`, `<CJK: "Use 1 CPU core per task">`, etc.) | Translate `#SBATCH` comments to English |
| 22 | `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/1_unconditioned_RNN/2_train_sample/train_prior.py` | 1 | `L63`: commented-out code with trailing CJK note (`<CJK: "issue with this line">`) | Translate comment to English |
| 23–24 | `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/{4_eform_m3gnet,5_eform_PBE}/2_collect_clean_glob_details.py` (2 files) | 1 + 1 | `L29`: CJK comment (`<CJK: "Read CSV file">`) | Translate to `# Read CSV file` |
| 25–30 | `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/{4_eform_m3gnet/3_normal_distri_plot.py,5_eform_PBE/3_normal_distri_plot.py,Other_targets/3_eform_-{3,4,5,6}/5_EOF_m3gnet_statistics/4_normal_distri_plot.py}` (6 files) | 7 each (42) | `L6,10,22,36,43,59,64` (or `L5,9,21,35,42,58,63`): matplotlib plot CJK comments (`<CJK: "Set global style">`, `<CJK: "Plot histogram">`, etc.) | Translate comments to English |
| 31–34 | `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/5_eform_PBE/workflow/0_EnthalpyOfFormation{0.5,0,1,2}.py` (4 files) | 3, 3, 1, 4 | `L6`/`L4` CJK docstring (`<CJK: "Read structure file, automatically compute formation enthalpy">`) + comments on `L20,22` / `L17,23,27` | Translate docstrings & comments to English |
| 35 & 37 | `data/{mp20,mp20_nonmetal}/workflow/0_run.sh` (2 files) | 8 + 8 | `L2-7,11,15`: SLURM `#SBATCH` inline comments | Translate `#SBATCH` comments to English |
| 36 | `data/mp20_nonmetal/2_stratified_sampling_split.py` | 17 | `L8,10,12,15,16,18,21,25-27,31,33,36,39-42`: CJK comments and `print(...)` summary labels (`<CJK: "Training set distribution:">`, `<CJK: "Number of bins used:">`, etc.) | Translate comments and `print(...)` labels to English |

### 2.5 Category D — `MatterGPT/` Directory: **DROP IN STAGE 4** (21 files, 386 CJK lines)
All 21 files below reside strictly inside `MatterGPT/` and are deleted in Stage 4 (`git rm -r MatterGPT`) with **zero translation work needed**:
1. `MatterGPT/0_dataset/workflow/0_run.py` (11 lines)
2. `MatterGPT/0_dataset/workflow/0_run.sh` (7 lines)
3. `MatterGPT/1_train_generate/dataset.py` (10 lines)
4. `MatterGPT/1_train_generate/generate.py` (19 lines)
5. `MatterGPT/1_train_generate/model.py` (7 lines)
6. `MatterGPT/1_train_generate/train.py` (4 lines)
7. `MatterGPT/1_train_generate/trainer.py` (27 lines)
8. `MatterGPT/2_decode/1_decode.sh` (1 line)
9. `MatterGPT/2_decode/run.py` (13 lines)
10. `MatterGPT/2_decode/workflow/0_run.sh` (7 lines)
11. `MatterGPT/2_decode/workflow/script.py` (1 line)
12. `MatterGPT/3_novelty/run.py` (24 lines)
13. `MatterGPT/3_novelty/workflow/0_run.sh` (7 lines)
14. `MatterGPT/app.py` (154 lines)
15. `MatterGPT/demo_decode_novelty_check_eform/1_decode_eform.sh` (3 lines)
16. `MatterGPT/demo_decode_novelty_check_eform/run.py` (26 lines)
17. `MatterGPT/demo_decode_novelty_check_eform/workflow/0_run.sh` (7 lines)
18. `MatterGPT/demo_template_DFT/workflow/0_run.py` (3 lines)
19. `MatterGPT/tutorials_1_eform.sh` (19 lines)
20. `MatterGPT/tutorials_2_bandgap_vasp.sh` (25 lines)
21. `MatterGPT/tutorials_3_bandgap_eform_vasp.sh` (25 lines)

*(Total accounted for: `3 + 6 + 30 + 21 = 60` upstream files = 100% of CJK occurrences.)*

---

## 3. Complete `MatterGPT/` Removal Decoupling Map

> [!CAUTION]
> **Critical Dataset Mismatch Discovered (`mp20_eform_bandgap_nonmetal.csv`):**
> `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` and `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` share a filename but are **NOT** the same dataset:
> - `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` (`1,006 KB`, `2,383` structures, SHA256 `07fee712...`): Header `SLICES,formation_energy_per_atom,band_gap,crystal_system`; uses **strategy-4 SLICES with space-group tokens** (`o x a DDO j OOO o Na Na Na Mn Co Ni O ...`).
> - `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` (`14,303` structures, SHA256 `2a1866f7...`): Header `SLICES,eform,bandgap`; uses **SLICES without space-group tokens**.
>
> Repointing [3.benchmark_relax_models.py](file:///home/ordillo/tests/SLICES/examples/3.benchmark_relax_models.py) directly to `data/mp20_nonmetal/mp20_eform_bandgap_nonmetal.csv` would crash with `KeyError: 'formation_energy_per_atom'` and lose the 2,383-structure v4.0.2 reference benchmark corpus!
> Meanwhile, `MatterGPT/2_decode/workflow/chemPotMP.json` (`1.9 KB`, SHA256 `a01b28770d76d6ce...`) **is** bit-for-bit identical to `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/4_eform_m3gnet/workflow/chemPotMP.json`.

### 3.1 File-by-File Stage 4 Decoupling Actions (Before `git rm -r MatterGPT`)

| Kept File / Asset | Lines Referencing `MatterGPT` / `gradio` | Exact Coupling | Stage 4 Remediation |
|---|---|---|---|
| `MatterGPT/0_dataset/mp20_eform_bandgap_nonmetal.csv` & `MatterGPT/2_decode/workflow/chemPotMP.json` | Data files (`1.0 MB` + `1.9 KB`) | Required by `examples/3.benchmark_relax_models.py` and `gfnff_helper._self_test` provenance | **Relocate (`git mv`)** before deleting `MatterGPT/`: move `mp20_eform_bandgap_nonmetal.csv` -> `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` and `chemPotMP.json` -> `data/mp20_nonmetal/chemPotMP.json` |
| [examples/3.benchmark_relax_models.py](file:///home/ordillo/tests/SLICES/examples/3.benchmark_relax_models.py) | `L4, 6, 14, 49, 50` | Docstring + `--csv` default (`MatterGPT/0_dataset/...`) + `--chem-pot` default (`MatterGPT/2_decode/workflow/chemPotMP.json`) | Update `--csv` default to `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` and `--chem-pot` default to `data/mp20_nonmetal/chemPotMP.json`; update docstring wording to "MP-20 benchmark dataset" |
| [src/slices/gfnff_helper.py](file:///home/ordillo/tests/SLICES/src/slices/gfnff_helper.py) | `L17, 119` | Docstring (`On the 2383 MatterGPT MP-20 structures`) & comment (`# First structure of MatterGPT/0_dataset/...`) | Update comment on L119 to reference `data/mp20_nonmetal/mp20_v4_benchmark_2383.csv` |
| [pyproject.toml](file:///home/ordillo/tests/SLICES/pyproject.toml) & `uv.lock` | `pyproject.toml:8, 27, 43` & `uv.lock` (`gradio*`) | `description` mentions MatterGPT; `einops` (`# MatterGPT model`); `gui = ["gradio"]` (`# MatterGPT/app.py`) | Update `description` to focus on SLICES invertible crystal representation & CLI/MLIPs; remove `gui = ["gradio"]` extra; remove `einops` from core `dependencies` (verified unused anywhere in `src/slices/`, `examples/`, `HTS/`, `benchmark/`, `data/`); refresh `uv.lock` keeping exact locked versions of all remaining packages |
| [tools/workstation_check.sh](file:///home/ordillo/tests/SLICES/tools/workstation_check.sh) | `L2, 7, 79-124` | Steps 4 & 5 tar `MatterGPT/`, run `train.py`/`generate.py`, and run `MatterGPT/demo_decode_novelty_check_eform/run.py` | Refactor into a clean SLICES-only workstation check script (`tools/workstation_check.sh`): keep Steps 1–3 + Step 6 (`uv sync`, `torch_info`, `relax_backends --prepare` CPU/GPU, `examples/3.benchmark_relax_models.py`) and remove Steps 4–5 (`MatterGPT`) |
| [entrypoint_set_cpus_gradio.sh](file:///home/ordillo/tests/SLICES/entrypoint_set_cpus_gradio.sh) | `L21-22` (`cd MatterGPT && python app.py`) | Launches deleted Gradio MatterGPT app | `git rm entrypoint_set_cpus_gradio.sh` |
| [rundocker.sh](file:///home/ordillo/tests/SLICES/rundocker.sh) | `L1` (`-p 7860:7860 ... entrypoint_set_cpus_gradio.sh`) | Invokes deleted Gradio entrypoint | Replace with clean `entrypoint_set_cpus.sh` invocation under `docker/` or `configs/` |
| [README.md](file:///home/ordillo/tests/SLICES/README.md) | `L7, 10-11, 22-23, 29-32, 44-45, 68, 99-103, 106, 127-134, 176-185, 251, 265-273` | MatterGPT GUI, tutorials, memory notes, Gradio port 7860, BibTeX | Remove MatterGPT GUI/training/tutorial instructions in Stage 6 English rewrite; keep SLICES & SLICES-PLUS citations (optional related-work mention of MatterGPT paper if desired, clearly noting this repo is SLICES-core only) |
| `docs/{MatterGPT.jpg,gui_snapshot.png,huggingface_space.png,SLICES-MatterGPT_<CJK-intro:\u4ecb\u7ecd>.pdf}` | Static image/PDF files in `docs/` | MatterGPT screenshots & Chinese PDF | `git rm` during Stage 4/6 `docs/` cleanup |

*(Verification check: `grep` confirmed zero references to `einops` or `MatterGPT` anywhere inside `src/slices/` runtime code, `HTS/`, `benchmark/`, or `data/`.)*

---

## 4. `HTS/`, `benchmark/`, and `data/` Baseline Compatibility Audit

Scanning all **97** script/config files in `HTS/`, **121** script/config/doc files in `benchmark/`, and **15** script/config files in `data/` uncovered **six concrete compatibility findings**:

### 4.1 `SLICES` & `slices.utils` Public API Surface Used by Baselines
- **`slices.core` imports (39 files):** Every workflow script uses `from slices.core import SLICES` and calls:
  - `SLICES(graph_method=..., check_results=..., relax_model=...)`
  - `structure2SLICES`, `structure2randomSLICES`, `from_SLICES`, `to_SLICES`, `to_structures`, `to_4structures`, `SLICES2structure`, `SLICES2formula`, `check_SLICES`, `check_element`, `check_3D`, `check_structural_validity`, `get_canonical_SLICES`, `match_check3`, `match_check4`.
- **`slices.utils` imports (18 files):** Scripts import `temporaryWorkingDirectory`, `exclude_elements_json`, `splitRun`, `splitRun_csv`, `splitRun_sample`, `show_progress`, `collect_json`, `collect_csv`, `collect_csv_filter`, `adaptive_dynamic_binning`. **All 10 function names and parameter signatures in `src/slices/utils.py` MUST be preserved.**

### 4.2 Six Specific Baseline Compatibility Findings & Stage 4/6 Handling

| ID | Location(s) | Observed Issue | Impact & Recommended Handling |
|---|---|---|---|
| **BC-1** | `HTS/2_train_sample/{train_prior.py:14, transfer_userinpt.py:17}`, `benchmark/.../2_conditioned_RNN/2_train_sample/train_prior.py:15` | `from slices import check_SLICES` — those directories contain a legacy local `slices.py` (`v1` procedural `check_SLICES` function), whereas `src/slices/__init__.py` is currently empty! If installed `src/slices` takes precedence on `sys.path` over CWD, `ImportError: cannot import name 'check_SLICES' from 'slices'` occurs. | In `src/slices/__init__.py`, export `SLICES` and `__version__`, **and** optionally provide a lightweight module-level convenience wrapper `def check_SLICES(s, strategy=4, dupli_check=False, graph_rank_check=True): return SLICES(relax_model=None).check_SLICES(...)` (or document running RNN scripts with CWD first). Adding `check_SLICES` to `slices.__init__` is purely additive and unbreaks `from slices import check_SLICES`! |
| **BC-2** | `HTS/` & `benchmark/` `SLICES(...)` instantiations vs `m3gnet` | Contrary to `HANDOFF_workstation.md:95`, **zero** scripts in `HTS/` or `benchmark/` pass `relax_model="m3gnet"` to `SLICES(...)`! All `SLICES(...)` calls omit `relax_model` (so they automatically use `relax_model="auto"` -> `nequip-s+l` in v4.0.2), **except** 2 post-screening scripts that import TensorFlow/M3GNet directly: `HTS/5_symmetry_filter_refine/workflow/script.py:8-9` and `benchmark/Validity_rate_ucRNN__Success_rate_cRNN/2_conditioned_RNN/4_eform_m3gnet/workflow/script.py:10`. | Note in `benchmark/` & `HTS/` READMEs that those 2 standalone M3GNet scripts require optional `m3gnet` (or `slices.mlip_relaxer` adapter — check `auditor-fork`'s Slice 2A report, as `backup/v3-personal` updated `HTS/5_symmetry_filter_refine/workflow/script.py`!). Also note that `SLICES(graph_method=...)` in encoding-only scripts (`HTS/0_get_json_mp_api`, `HTS/1_augmentation`, `data/mp20/workflow/0_run.py:27`) omits `relax_model=None`, so `SLICES.__init__` eagerly loads NequIP on CPU unless `NequIP` is cached (already cached in `.cache`!). |
| **BC-3** | `HTS/0_get_json_mp_api/2_filter_prior_3d/1_run.py:5` | Upstream **SyntaxError**: `from slices.utils import * splitRun,show_progress,collect_json,collect_csv` (stray `*` before `splitRun`). | Fix the stray `* ` typo in Stage 4/5 (`from slices.utils import splitRun, show_progress, collect_json, collect_csv`) — clearly broken syntax, zero effect on historical data. |
| **BC-4** | `HTS/0_get_json_mp_api/0_run.py:5` & `HTS/Tutorial_2_inverse_design_case_study.ipynb` | Imports `search_materials` from `slices.utils` (removed upstream in v3 when MP migrated to `mp-api`) and hardcodes `/crystal/APIKEY.ini`. | Document in `HTS/` README as legacy MP-API data-acquisition step (archived dataset `HTS/0_get_json_mp_api/prior_model_dataset.zip` is already bundled in the repo). |
| **BC-5** | `benchmark/Match_rate_QMOF-21-40/0_get_json/1_element_filter/count.py:3` & `benchmark/.../2_conditioned_RNN/2_train_sample/error.py` | `count.py` imports `from slices.crystalgraph import CrystalGraph` (v1 name, unused in `count.py`!); `error.py` is a raw stderr traceback saved with a `.py` extension (triggers `SyntaxError` if `ruff` or `compileall` scans `benchmark/`). | Exclude `benchmark/` and `HTS/` from strict `ruff`/`pytest` collection (or exclude `error.py`), and document in `benchmark/` README without altering historical artifacts. |
| **BC-6** | `benchmark/**` (`28` `1_splitRun.py` scripts) & `benchmark/benchmarks.md` | Legacy `1_splitRun.py` scripts call `os.system('qsub 0_run.pbs')` directly (PBS/Torque inside old Docker v9/v12) and `benchmarks.md` hardcodes `/crystal/...` container paths. | Keep historical PBS reproduction scripts intact; update documentation in Stage 6 to explain `slices.utils.splitRun` (local/SLURM) vs legacy Docker PBS reproduction. |

---

## 5. Packaging, `src/slices/utils.py` Safety & Google Style / `ruff` Baseline Audit

### 5.1 Packaging & Root Configuration Audit (`pyproject.toml`, `setup.cfg`, Root Files)
1. **[pyproject.toml](file:///home/ordillo/tests/SLICES/pyproject.toml):**
   - **Tsinghua Mirror Default (`L59-62`):** Sets `https://pypi.tuna.tsinghua.edu.cn/simple` with `default = true` (5× slower outside China: `3.28s` vs `0.64s` for `pypi.org`). Evaluate in Stage 3 Review whether to remove `default = true` on TUNA (documenting TUNA as an opt-in `UV_DEFAULT_INDEX` mirror) or keep `uv.lock` pinned against PyPI.
   - **Torch Version Ceiling (`L31`):** `torch>=2.6,<2.10` (`uv.lock` pins `2.9.1`). Keep for the locked `uv` environment; note for optional MLIP users on existing conda envs (e.g., `torch 2.10–2.12`) that `nequip==0.17.1` is what pins `<2.10`.
   - **Missing CLI & Dev Tooling Sections:** Add `[project.scripts] slices = "slices.cli:main"`, `[project.optional-dependencies]` groups `dev = ["pytest>=8.0", "pytest-cov>=5.0", "ruff>=0.9"]` and optional MLIP extras (`chgnet`, `mace`, `mattersim`, `orb`), plus `[tool.ruff]` and `[tool.pytest.ini_options]`.
2. **[setup.cfg](file:///home/ordillo/tests/SLICES/setup.cfg):**
   - Hardcodes `[bdist_wheel] plat_name = manylinux2014_x86_64` because `_vendor/gfnff/libgfnff.so.0.1.1` is a Linux x86_64 ELF shared library. Keep on Linux x86_64 builds, and document cross-platform source/editable install behavior when optional non-Linux fallbacks are ported in Stage 4.
3. **Root Clutter (`__init__.py`, `APIKEY.ini`, `slurm.conf`, `entrypoint_set_cpus.sh`, `src/slices/README.rst`):**
   - Root `__init__.py` (`1 byte` blank file) makes the repo root an accidental namespace/package directory — **delete in Stage 4** (also deleted in `backup/v3-personal`).
   - `src/slices/README.rst` (`#Put this folder in ~ and python setup.py develop.`) is obsolete v1 instructions — **delete in Stage 4** (also deleted in `backup/v3-personal`).
   - Move `APIKEY.ini` (empty template), `slurm.conf`, `entrypoint_set_cpus.sh`, `rundocker.sh`, and `Dockerfile/*` into organized `configs/` and `docker/` directories (matching `backup/v3-personal` layout) while adding `APIKEY.ini` local secrets pattern to `.gitignore`!
   - **[.gitignore](file:///home/ordillo/tests/SLICES/.gitignore):** Upstream `.gitignore` is only 4 lines (`.venv/`, `__pycache__/`, `*.py[cod]`, `*.egg-info/`). Merge the specific, non-blanket ignore patterns from `backup/v3-personal` (commits `67d73f6..e37ce5e`, avoiding blanket `*.csv`/`*.json` ignores that previously hid `benchmark/` and `data/` files!).

### 5.2 Deep Safety & Portability Audit of [src/slices/utils.py](file:///home/ordillo/tests/SLICES/src/slices/utils.py)
1. **CRITICAL PROCESS-KILL HAZARD (`L364-428` in `show_progress` & `L461-526` in `cancel_all_jobs`):**
   - On any machine without SLURM (including this workstation!), pressing `Ctrl+C` during `show_progress()` or calling `cancel_all_jobs()` runs `pgrep -f "python"` and executes `kill` followed 5 seconds later by **`kill -9` on EVERY Python PID matched on the host** — indiscriminately killing the caller's own Python session, pytest runners, Jupyter servers, and unrelated background jobs of the user!
   - **Mandatory Stage 4 Fix:** Just as upstream commit `b600715` added `_SUBMITTED_SLURM_JOBS` to avoid running `scancel -u <user>` blindly, record `Popen.pid` (and process group / child PIDs) in a `_SUBMITTED_LOCAL_PIDS: list[int] = []` inside `_run_local_job()`, and have `show_progress()` (`KeyboardInterrupt`) and `cancel_all_jobs()` terminate **only** tracked PIDs in `_SUBMITTED_LOCAL_PIDS` (never `pgrep -f python`!).
2. **Shell Injection & Non-Portable `os.system` Calls (11 instances):**
   - `L85, 136, 180`: `os.system('rm -rf job_* structures_ori_opt ./result.csv')` -> replace with `glob` + `shutil.rmtree` / `Path.unlink(missing_ok=True)`.
   - `L119, 163, 186`: `os.system('cp -r ./workflow/. ' + job_dir)` -> replace with `shutil.copytree('./workflow', job_dir, dirs_exist_ok=True)`.
   - `L556, 579, 601`: `os.system('rm -r ' + i)` -> replace with `shutil.rmtree(i, ignore_errors=True)`.
3. **Unguarded `os.chdir` Directory-Nesting Bug (`L125-130`, `L169-174`, `L187-193`):**
   - `splitRun`, `splitRun_csv`, and `splitRun_sample` call `os.chdir(job_dir)` ... `os.chdir('..')` without `try/finally` (even though `temporaryWorkingDirectory` is defined at `L29` in the very same file!). Wrap each submission in `with temporaryWorkingDirectory(job_dir):` (or pass `cwd=job_dir` directly to `subprocess.run` / `subprocess.Popen`).
4. **Late Thread-Env Assignment (`L705-708`, `L754-757`):**
   - `parallel_process_json` and `parallel_process_csv` set `OMP_NUM_THREADS="1"`, `MKL_NUM_THREADS="1"`, `OPENBLAS_NUM_THREADS="1"` *after* `import numpy as np` at `L6` has already initialized BLAS thread pools, and spawn `Pool` with `fork` on Linux. Keep env vars set early or via `initializer` in `Pool`.
5. **Duplicate `finally` Logging (`L447-451`) & `pandas` Warnings (`L664, 677`):**
   - `show_progress` prints the CJK completion string (`<CJK: "Task monitoring finished.">`) twice (once at end of `except KeyboardInterrupt` L447 and immediately again in `finally:` L450).
   - `adaptive_dynamic_binning` mutates a slice `data_cleaned['bin'] = ...` (`SettingWithCopyWarning`) and calls `pd.concat` on an empty untyped `DataFrame` inside a loop (`FutureWarning` in `pandas>=2.1`). Fix cleanly without changing binning math or `random_state` order (`data_cleaned = data.dropna(subset=[target_column]).copy()`).

### 5.3 Quantitative `ruff` & Google Style Baseline (`src/slices/` & `examples/`)

Read-only `ruff 0.17.6` (`--target-version py310 --line-length 100`) and AST analysis across `src/slices/` and `examples/` established the exact Stage 2 baseline (**694** core lint violations + **806** docstring/type-annotation violations):

| File | Lines | Core Lint (`E,F,W,I,B,UP,SIM,RUF`) | Doc/Type (`D,ANN`) | Functions w/ Docstrings | Functions w/ Return Types | Critical Code Defects Found |
|---|---:|---:|---:|---:|---:|---|
| `src/slices/__init__.py` | 1 | 0 | 1 | 0/0 | 0/0 | Empty file (`__version__`, `SLICES`, `__all__` missing) |
| `src/slices/config.py` | 287 | 2 | 1 | 0/0 | 0/0 | Missing module docstring & trailing newline (`W292`) |
| `src/slices/core.py` | 2,086 | **335** | **332** | 47/62 | 0/62 | **`F821` undefined `TimeoutException` at L60!** 6 bare `except:` (`L285,495,557,572,662,921`); 6 unused imports (`SystreDB`, `fsolve`, `StringIO`, `pandas`, `logging`, `itertools`); 30 `E402` imports after env-vars; 5 unused local vars (`F841`); stale docstring defaults (`L208,477,714,1953,1974,1995`) |
| `src/slices/gfnff_helper.py` | 134 | 14 | 13 | 6/6 | 0/6 | Cleanest module; only `E501` (>100 chars), `UP009`, and missing type hints |
| `src/slices/relax_backends.py` | 602 | 30 | 94 | 12/33 | 0/33 | CJK string at `L251` (`RUF001`); `E501` (19); `ExpCellFilter` ASE deprecation warning on `ase>=3.23` (keep frozen for exact cell-filter parity!) |
| `src/slices/tobascco_net.py` | 1,012 | 72 | 187 | 11/60 | 0/60 | 6 mutable default args (`B006` on `iter_cycles` L413 & `vertex_positions` L767); broken NetworkX 1.x `self._graph.node[node]` in `nodes_iter` (`L196`); `sys.exit()` in library method `delete_edge` (`L935`); `UP036` Python 2 `version_info.major >= 3` (`L860`); deprecated `np.matrix` (`L478,954,964,993`) |
| `src/slices/utils.py` | 795 | 164 | 88 | 6/18 | 0/18 | Duplicate imports (`json`, `numpy`, `math` imported twice each: `F811`); `E711` `!= None` (`L615`); 2 bare `except:` (`L316,318`); 11 `os.system`; `pgrep` kill hazard; 182 CJK lines |
| `src/slices/utils_wyckoff.py` | 146 | 35 | 18 | 4/4 | 0/4 | 6 unused imports (`numpy`, `pandas`, `Structure`, `Lattice`, `SpacegroupAnalyzer`, `os`); missing module docstring & type hints |
| `src/slices/_vendor/gfnff/*.py` | 1,152 | 12 | 62 | Vendored | Vendored | **Exclude `src/slices/_vendor/` from `ruff` & style edits** to preserve vendored LGPL-3.0 code untouched |
| `examples/*.py` (4 files) | 172 | 30 | 10 | 0/2 | 0/2 | Unused imports (`F401`), hardcoded `os.environ["CUDA_VISIBLE_DEVICES"]=""` in `2.1...py`, `MatterGPT` paths in `3.benchmark_relax_models.py`, stale comments |

### 5.4 Specific Docstring-vs-Implementation Discrepancies in `src/slices/core.py` (Fix in Stage 4/5)
1. `SLICES.__init__` (`L96-98`): Docstring says `"auto"` uses *"NequIP-OAM-L on a CUDA GPU, otherwise NequIP-OAM-S..."* (stale from commit `eb1f6c9`), whereas commit `315d4f0` changed `"auto"` to use CPU `nequip-s+l` on **all** machines unless `SLICES_DEVICE=cuda`.
2. `from_SLICES` (`L208`): Docstring says `fix_duplicate_edge` *"Defaults to False"*, actual default is `True`; missing `strategy` arg in docstring.
3. `check_SLICES` (`L477`): Docstring says `dupli_check` *"Defaults to True"*, actual default is `False`; missing `strategy` arg in docstring.
4. `structure2SLICES` (`L714`): Docstring says `strategy` *"Defaults to 3"*, actual default is `4`.
5. `relax` (`L1953`), `relax_large_cell1` (`L1974`), `relax_large_cell2` (`L1995`): Docstrings state time limits of `60`, `360`, and `1000` seconds, whereas `@function_timeout` decorators are `360`, `720`, and `2000` seconds; also note `relax_large_cell2` (`L2007,2010`) does **not** pass `fmax=self.fmax, steps=self.steps` to `self.relaxer.relax(struc)`, so it uses `NequIPRelaxer.relax`'s own default (`fmax=0.1, steps=500`) instead of `SLICES`'s (`fmax=0.2, steps=100`)!

---

## 6. Deferred Core / Algorithm Candidates (For `@scribe` Consolidation into `DEFERRED_CORE_REGISTER.md`)

In addition to the 6 Stage 1 seed items (`PLAN.md` Section 4.2), Slice 2B identified **8 upstream core/algorithmic/runtime candidates**. Items marked **SAFE BUGFIX (Non-Math)** can be fixed in Stage 4 if approved in Stage 3 Review; items marked **DEFER (Frozen Baseline)** MUST NOT be changed in `slices-4-personal` and belong in `DEFERRED_CORE_REGISTER.md`:

1. **`DEF-UP-001` [SAFE BUGFIX Candidate — Crash on Timeout] — `src/slices/core.py:60` Undefined `TimeoutException` (`F821`):**
   - *Observed:* `signal_handler` inside `function_timeout` executes `raise TimeoutException("Timed out!")`, but commit `119afaf` deleted the definition/import of `TimeoutException`. Any relaxation exceeding 360/720/2000s crashes with `NameError: name 'TimeoutException' is not defined` instead of a timeout exception.
   - *Recommendation:* Define `class TimeoutException(SLICESError): pass` in `exceptions.py` and import it in `core.py` (zero impact on non-timed-out math/trajectories; restores intended timeout handling).
2. **`DEF-UP-002` [DEFER — Frozen Baseline] — `src/slices/core.py:2007,2010` (`relax_large_cell2` ignores `self.fmax` and `self.steps`):**
   - *Observed:* `relax` (`<=20` atoms) and `relax_large_cell1` (`21..40` atoms) call `self.relaxer.relax(struc, fmax=self.fmax, steps=self.steps)` (`0.2`, `100`), whereas `relax_large_cell2` (`>40` atoms) calls `self.relaxer.relax(struc)` with no kwargs, silently using `NequIPRelaxer.relax` defaults (`fmax=0.1, steps=500`).
   - *Why Defer:* Changing `relax_large_cell2` kwargs changes relaxation steps/forces for all cells with `>40` atoms relative to v4.0.2. Document in docstring and log in Register.
3. **`DEF-UP-003` [DEFER — Frozen Baseline] — `src/slices/relax_backends.py:369-372` (`ExpCellFilter` vs `FrechetCellFilter` in ASE >= 3.23):**
   - *Observed:* `ase==3.29.0` emits `DeprecationWarning: Use FrechetCellFilter for better convergence w.r.t. cell variables`.
   - *Why Defer:* Replacing `ExpCellFilter` with `FrechetCellFilter` changes cell gradient preconditioning and alters every `NequIPRelaxer` optimization trajectory and final energy. Keep `ExpCellFilter` frozen.
4. **`DEF-UP-004` [DEFER — Frozen Baseline] — `src/slices/tobascco_net.py:413` & `767` Mutable Default Arguments (`cycle=[]`, `used=[]`, `nodes_visited=[]`, `cycle_baggage=[]`, `pos={}`, `bad_ones={}`):**
   - *Observed:* `Net.iter_cycles` and `Net.vertex_positions` use mutable list/dict default arguments that persist across multiple calls if invoked without explicit arguments (`get_cycle_basis` passes explicit `[]` at L307–310, mitigating the primary path, though direct callers of `iter_cycles()` share state).
   - *Why Defer:* Audit carefully before touching `tobascco_net.py`; `iter_cycles` and `vertex_positions` are in the frozen `Net` class. Log in Register.
5. **`DEF-UP-005` [DEFER — Frozen Baseline] — `src/slices/tobascco_net.py:478,954,964,993` Deprecated `np.matrix(...).I` Usage:**
   - *Observed:* `Net` uses `np.matrix(d).I` in `eon_projection`, `projection`, `cycle_cocycle_I`, and `linear_independent_vectors`. `np.matrix` is pending deprecation in NumPy 2.x.
   - *Why Defer:* Replacing `np.matrix(d).I` with `np.linalg.inv(d)` can introduce `~1e-16` floating-point pivot differences that cascade through `np.linalg.cholesky` and `fmin_l_bfgs_b` finite-difference gradients (`epsilon=1e-8`). Keep frozen until post-baseline numerical verification.
6. **`DEF-UP-006` [DEFER — Frozen Baseline] — `src/slices/core.py:656-663` (`SLICES2formula` Bug on Atom Index `0` Without Space-Group Prefix or Strategy 1/2):**
   - *Observed:* `if first_elem_idx:` skips slicing when `first_elem_idx == 0` (fine), then `re.search(r'^(.*?)(\d+)', SLICES)` extracts symbols up to the first digit. For strategy 2 (`Si_O_0001...`), underscores break `Composition`; on invalid input without digits, `match` is `None` and `match.group(1)` raises `AttributeError` outside the `try` block; on `except:`, it prints and returns `None`.
   - *Why Defer:* Keep frozen for v4.0.2 parity; document strategy-3/4 input assumption and log in Register.
7. **`DEF-UP-007` [DEFER — Frozen Baseline] — `src/slices/core.py:1908-1910` (`to_structures` Swallows `relax_model=None` `AttributeError` and Prints `'NoneType' object has no attribute 'relax'`):**
   - *Observed:* When `SLICES(relax_model=None)` is used to compute unrelaxed ZL* structures via `to_structures()`, `self.relaxer` is `None`; `to_structures` calls `self.relax(...)`, catches `AttributeError`, prints `'NoneType' object has no attribute 'relax'` to stdout, and returns `[std, opt], 0`.
   - *Why Defer:* Check in Stage 3 Review whether short-circuiting `if self.relaxer is None: return [structure_recreated_std, structure_recreated_opt], 0` (eliminating the spurious `AttributeError` print while returning the exact same tuple!) is desired or should remain frozen.
8. **`DEF-UP-008` [DEFER — Frozen Baseline] — `src/slices/core.py:1869-1877` Exact Float Equality for `lattice_type` Symmetry Classification in `to_structures`:**
   - *Observed:* `lattice_length_list_unique = list(set([metric_tensor_std[0,0], metric_tensor_std[1,1], metric_tensor_std[2,2]]))` uses exact IEEE-754 float `set` deduplication and `==` comparisons on Cholesky/rescaled `metric_tensor_std` diagonals to classify cubic (`1`), tetragonal/hexagonal/orthorhombic-pair (`21,22,23`), vs triclinic (`3`). Floating-point rounding of `~1e-16` can flip `lattice_type` between `1`/`2x` and `3`, changing parameter dimensionality in `initialize_x_bounds`!
   - *Why Defer:* This is the #1 reason `tobascco_net.py` (`np.matrix.I`), `get_rescaled_lattice_vectors`, and `OMP_NUM_THREADS="1"` MUST remain bit-for-bit untouched in the frozen baseline! Log prominently in `DEFERRED_CORE_REGISTER.md`.
