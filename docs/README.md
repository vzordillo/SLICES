# SLICES Documentation Index

Central navigation hub for **SLICES v4.1** documentation, API references, benchmarks, and migration audit records.

---

## Primary Guides

| Document | Scope |
|---|---|
| [README](../README.md) | Overview, `uv` installation, Python API & `slices` CLI quickstart, v4.1 benchmark summary, and testing commands |
| [Technical Architecture Guide](../TECHNICAL.md) | Detailed design of Strategies 1–4, primitive-cell pre-reduction, periodic net embedding, bundled GFN-FF + non-Linux fallback, ZL\* optimization, NequIP relaxers, optional MLIPs, and opt-in robust decoding |
| [Changelog](../CHANGELOG.md) | Chronological release history from upstream v1.0 through v4.1.0 and post-release updates |
| [Benchmarks Reproduction Guide](../benchmark/benchmarks.md) | Historical MP-20, MP-21-40, QMOF-21-40, and RNN validity/success benchmark workflows |
| [License](../LICENSE) | GNU Lesser General Public License v2.1 (plus LGPL-3.0 for vendored GFN-FF in `src/slices/_vendor/gfnff_extra/LICENSE`) |

---

## Quantitative Benchmarks (`v4.0.2-baseline` & `v4.1`)

Locked full-dataset MP-20 non-metal control baseline (`2,383` structures, `nequip-s+l` CPU, paired `default` / `lorentz` / `robust` passes) archived on tag `v4.0.2-baseline` (`f248b3c`):

| Artifact | Scope |
|---|---|
| [BASELINE_REPORT.md](../benchmark/v4_0_2_baseline/BASELINE_REPORT.md) | Publication-grade quantitative baseline report: 3-pass metrics, crystal-system breakdown, failure & rescue taxonomy, paired A/B analysis, and reproduction protocol |
| [summary.json](../benchmark/v4_0_2_baseline/summary.json) | Machine-readable aggregate metrics, crystal-system summaries, paired transition counts, and environment metadata |
| [per_structure_metrics.csv](../benchmark/v4_0_2_baseline/per_structure_metrics.csv) | Wide-format control-group dataset (`2,383` rows × `53` columns) with lossless float64 formation energies and per-structure relaxation telemetry |
| [run_mp20_baseline.py](../tools/benchmarks/run_mp20_baseline.py) | Reproducible multi-process benchmark runner (`24` spawned CPU workers, 1-to-1 MP-20 reference CIF join) |

Paired A/B evaluation of `v4.1` core algorithmic upgrades (`DEF-003`, `DEF-014`, `DEF-021`, `DEF-031`) against locked `v4.0.2-baseline` across `2,383` MP-20 structures and `39,244` conditioned-RNN (`cRNN`) strings:

| Artifact | Scope |
|---|---|
| [AB_COMPARISON_REPORT.md](../benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md) | Head-to-head scientific A/B report: 5-comparison McNemar/Wilcoxon matrix, zero-regression audit, SNF rescue table, incomplete-GFN-FF oxyhydride diagnostics, crystal-system latency breakdown, `cRNN` validity scan, golden oracle deltas, and promotion recommendation |
| [ab_vs_v4_0_2.json](../benchmark/v4_1_experimental/ab_vs_v4_0_2.json) | Machine-readable paired statistical comparison (McNemar & Wilcoxon p-values, crystal-system latencies, rescued/oxyhydride crystal records, and 5-corpus `cRNN` audit) |
| [summary.json](../benchmark/v4_1_experimental/summary.json) | Candidate 3-pass aggregate metrics, crystal-system summaries, and environment metadata on `exp/v4.1-algo-upgrades` |
| [per_structure_metrics.csv](../benchmark/v4_1_experimental/per_structure_metrics.csv) | Candidate wide-format dataset (`2,383` rows × `53` columns) aligned 1-to-1 with `v4.0.2-baseline` |
| [compare_ab_baselines.py](../tools/benchmarks/compare_ab_baselines.py) | Paired statistical A/B comparison and `cRNN` validity-rate audit CLI |

Extended multi-GPU (`2x RTX PRO 6000 Blackwell`) and large-cell benchmark suites on `v4.1.0` covering 5-model `MP-20` (`N = 2,383` + 64-crystal stage breakdown), full `QMOF-21-40` (`N = 339`), and crystal-system-stratified `MP-21-40` (`N = 1,000 / 4,454`):

| Artifact | Scope |
|---|---|
| [EXTENDED_BENCHMARK_REPORT.md](../benchmark/v4_1_extended/EXTENDED_BENCHMARK_REPORT.md) | Publication-grade report covering 5-model GPU MP-20 comparison (`nequip-s+l`, `nequip-m+l`, `nequip-l`, `chgnet`, `mace`), CPU vs CUDA stage breakdown, transparent outlier audit, full `QMOF-21-40`, and stratified `MP-21-40` |
| [gpu_mp20_summary.json](../benchmark/v4_1_extended/gpu_mp20_summary.json) | Machine-readable 5-model GPU MP-20 metrics, VRAM telemetry, paired McNemar/Wilcoxon tests vs CPU `v4.1`, and `stage_breakdown_64` |
| [qmof_21_40_summary.json](../benchmark/v4_1_extended/qmof_21_40_summary.json) | Machine-readable full `QMOF-21-40` (`339` MOFs, `econnn`) `default` vs `lorentz` metrics, failure taxonomy, and stage timings |
| [mp21_40_summary.json](../benchmark/v4_1_extended/mp21_40_summary.json) | Machine-readable stratified `MP-21-40` (`1,000 / 4,454` crystals, `crystalnn`, `seed=0`) `default` vs `lorentz` metrics, 7-system breakdown, and sampled IDs |
| [run_gpu_extended_benchmarks.py](../tools/benchmarks/run_gpu_extended_benchmarks.py) | Reproducible multi-GPU benchmark runner supporting `--suite mp20|qmof|mp21-40|all` and `--work-dir` multi-environment checkpoint merging |

---

## API Reference

Module-by-module symbol references verified directly against `src/slices/`:

| Document | Covered Modules & Topics |
|---|---|
| [API_CORE.md](api/API_CORE.md) | Top-level lazy exports (`slices.__init__`), `slices.core.SLICES` methods, `function_timeout`, and `slices.exceptions` hierarchy |
| [API_MLIP.md](api/API_MLIP.md) | `slices.relax_backends` (NequIP-OAM plans, caching, overlap/collapse guards) and optional `slices.mlip_relaxer` adapters (`chgnet`, `mattersim`, `orbv3`, `mace`, `m3gnet`) |
| [API_DECODING_STRATEGIES.md](api/API_DECODING_STRATEGIES.md) | Opt-in `slices.decoding_strategies` (`robust_decode`, `MultiStartOptimizer`, `AdaptiveConvergence`, `ProgressiveRelaxer`, `CycleBasisOptimizer`, `BondParameterFallback`) |
| [API_GRAPH.md](api/API_GRAPH.md) | `slices.tobascco_net` (`Net`, `SystreDB`), `slices.gfnff_helper` (bundled `libgfnff` and non-Linux `xtb` fallback), and `slices.utils_wyckoff` (230 space-group tokenization) |
| [API_UTILITIES.md](api/API_UTILITIES.md) | `slices.utils` (scoped local/SLURM batch jobs, collectors, adaptive binning, multiprocessing) and `slices.cli` (`slices` CLI subcommands) |
| [API_CONFIG.md](api/API_CONFIG.md) | `slices.config` constants (`OFFSET`, `LJ_PARAMS_LIST`, `PERIODIC_DATA`), complete environment variable reference, and `pyproject.toml` Ruff/Pytest/`uv` settings |

---

## Migration and Audit Trail

Primary-source planning, audits, review rulings, execution logs, and frozen-behavior records from the `v4.0.2` migration (`slices-4-personal`):

| Document | Purpose |
|---|---|
| [PLAN.md](migration/PLAN.md) | Master 7-stage migration plan, invariants, and Math/Algorithm Freeze policy |
| [AUDIT_FORK_DIFF.md](migration/AUDIT_FORK_DIFF.md) | Stage 2A audit comparing `backup/v3-personal` against upstream `v4.0.2` |
| [AUDIT_UPSTREAM_STYLE.md](migration/AUDIT_UPSTREAM_STYLE.md) | Stage 2B audit of upstream commits, CJK inventory, safety hazards, and Ruff/Google-style baseline |
| [AUDIT_BASELINE_HARNESS.md](migration/AUDIT_BASELINE_HARNESS.md) | Stage 2C specification of the 89-test golden equivalence harness and test suite design |
| [REVIEW_SIGNOFF.md](migration/REVIEW_SIGNOFF.md) | Stage 3 independent architectural review, cross-audit resolutions (`CA-01`–`CA-09`), and binding rulings (`RUL-01`–`RUL-08`) |
| [DEFERRED_CORE_REGISTER.md](migration/DEFERRED_CORE_REGISTER.md) | Formal 34-entry register (`DEF-001`–`DEF-034`) tracking Stage 4 and Wave 1 fixes, empirical re-evaluation verdicts (`Wave 2`/`Wave 3`), frozen behaviors, and closed regressions |
| [LAB_LOG.md](migration/LAB_LOG.md) | Chronological scientific lab log of all stages, post-migration empirical re-evaluation, verification metrics, and local commits |
| [FINAL_REPORT.md](migration/FINAL_REPORT.md) | Executive summary of the 7-stage v4.0.2 migration, commit ledger, verification scorecard, and maintenance guide |

### Post-Migration Empirical Re-Evaluation Reports

First-principles mathematical audits and controlled large-scale benchmarks (`125,174` SLICES strings, `18,093` MP-20 CIFs, `3,883` GFN-FF topology evaluations, and CPU `NequIP-OAM-S/L` A/B runs) underpinning the 3-wave post-migration roadmap:

| Report | Scope |
|---|---|
| [REEVAL_SYNTHESIS.md](migration/reeval/REEVAL_SYNTHESIS.md) | Independent verifier stress-tests, cross-item coupling analysis, newly discovered defects (`DEF-028`–`DEF-034`), and actionable 3-wave execution roadmap |
| [REEVAL_MATH_OPT.md](migration/reeval/REEVAL_MATH_OPT.md) | Empirical re-evaluation of core math & ZL\* optimization items (`DEF-001`, `DEF-006`, `DEF-011`, `DEF-014`, `DEF-025`, `DEF-027`; discovered `DEF-028`, `DEF-029`, `DEF-032`, `DEF-034`) |
| [REEVAL_GRAPH_RELAX.md](migration/reeval/REEVAL_GRAPH_RELAX.md) | Empirical re-evaluation of quotient-net topology, GFN-FF targets & NequIP relaxation (`DEF-002`, `DEF-003`, `DEF-008`, `DEF-009`, `DEF-010`, `DEF-015`, `DEF-021`, `DEF-023`; discovered `DEF-030`, `DEF-031`) |
| [REEVAL_RUNTIME_PARSE.md](migration/reeval/REEVAL_RUNTIME_PARSE.md) | Empirical re-evaluation of runtime side effects, determinism, SLICES parsing & Stage 3 blocks (`DEF-004`, `DEF-005`, `DEF-012`, `DEF-016`–`DEF-020`, `DEF-022`, `DEF-024`, `DEF-026`; discovered `DEF-033`) |

---

## Visual Assets

- [SLICES Pipeline Overview](figure_intro.png)
- [Online SLICES / CIF Converter Demo](SLICES_demo.png)
- [Windows 11 WSL2 Docker Shell Setup](win11_wsl2.png)
