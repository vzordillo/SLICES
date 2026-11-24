# SLICES Documentation Index

Central navigation hub for **SLICES v4.0.2** documentation, API references, benchmarks, and migration audit records.

---

## Primary Guides

| Document | Scope |
|---|---|
| [README](../README.md) | Overview, `uv` installation, Python API & `slices` CLI quickstart, MP-20 benchmark summary, and testing commands |
| [Technical Architecture Guide](../TECHNICAL.md) | Detailed design of Strategies 1–4, primitive-cell pre-reduction, periodic net embedding, bundled GFN-FF + non-Linux fallback, ZL\* optimization, NequIP relaxers, optional MLIPs, opt-in robust decoding, and baseline freeze invariant |
| [Changelog](../CHANGELOG.md) | Chronological release history from upstream v1.0 through v4.0.2 and `slices-4-personal` migration commits |
| [Benchmarks Reproduction Guide](../benchmark/benchmarks.md) | Historical MP-20, MP-21-40, QMOF-21-40, and RNN validity/success benchmark workflows |
| [License](../LICENSE) | GNU Lesser General Public License v2.1 (plus LGPL-3.0 for vendored GFN-FF in `src/slices/_vendor/gfnff_extra/LICENSE`) |

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
| [DEFERRED_CORE_REGISTER.md](migration/DEFERRED_CORE_REGISTER.md) | Formal 27-entry register (`DEF-001`–`DEF-027`) tracking resolved non-math fixes, frozen deferred math behaviors, and blocked regressions |
| [LAB_LOG.md](migration/LAB_LOG.md) | Chronological scientific lab log of all stages, verification metrics, and local commits |

---

## Visual Assets

- [SLICES Pipeline Overview](figure_intro.png)
- [Online SLICES / CIF Converter Demo](SLICES_demo.png)
- [Windows 11 WSL2 Docker Shell Setup](win11_wsl2.png)
