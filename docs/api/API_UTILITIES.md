# API Reference: Batch Workflow Utilities and CLI (`slices.utils`, `slices.cli`)

**Package Version:** `4.0.2`  
**Primary Sources:** [`src/slices/utils.py`](../../src/slices/utils.py), [`src/slices/cli.py`](../../src/slices/cli.py)

---

## 1. High-Throughput & Dataset Utilities (`slices.utils`)

`slices.utils` provides SLURM/local shard splitting, progress monitoring, safe job cancellation, shard collection, element filtering, adaptive stratified dataset splitting, and single-threaded multiprocessing helpers. All 16 public function names and signatures are backward-compatible with `HTS/`, `benchmark/`, and `data/` scripts.

### Workstation Safety Guarantee (`RUL-04`)

- All shell `os.system` calls have been replaced with `shutil` / `pathlib` and `subprocess` with `shell=False`.
- Job submissions execute inside `with temporaryWorkingDirectory(job_dir):` so CWD is always restored even on exception.
- On non-SLURM hosts, `_run_local_job` launches each shard with `subprocess.Popen([sys.executable, script], ..., start_new_session=(os.name != "nt"))` and records its handle in module-scoped `_SUBMITTED_LOCAL_PROCS` (mirroring upstream `_SUBMITTED_SLURM_JOBS`). Both `cancel_all_jobs()` and `show_progress()` `KeyboardInterrupt` terminate **only** processes tracked in `_SUBMITTED_LOCAL_PROCS` (never `pgrep -f python` or indiscriminate `kill -9`).

### Public Exports (`slices.utils.__all__`)

#### Directory, Partitioning & Environment Helpers

| Function | Signature | Description |
|---|---|---|
| `temporaryWorkingDirectory` | `(path: str | os.PathLike[str]) -> Iterator[None]` (`@contextmanager`) | Changes working directory to `path` for the duration of a `with` block and always restores the previous CWD on exit. |
| `split_list` | `(a: Sequence[_T], n: int) -> Iterator[Sequence[_T]]` | Partitions sequence `a` into `n` contiguous chunks of nearly equal size. |
| `is_slurm_available` | `() -> bool` | Returns `False` immediately if `SLICES_FORCE_LOCAL` is truthy (`"1"`, `"true"`, `"yes"`); otherwise checks `shutil.which("sinfo")` and `shutil.which("squeue")`. |

#### Job Submission, Monitoring & Cancellation

| Function | Signature | Description |
|---|---|---|
| `splitRun` | `(filename: str, threads: int, skip_header: bool = False) -> None` | Cleans prior `job_*` directories, splits JSON task list `filename` into `threads` shards copied from `./workflow`, and submits via SLURM (`0_run.sh`) or local `Popen` (`0_run.py`). |
| `splitRun_csv` | `(filename: str, threads: int, skip_header: bool = False) -> None` | Line/CSV variant of `splitRun` (optionally skipping header row when `skip_header=True`). |
| `splitRun_sample` | `(threads: int = 8, sample_size: int = 8000) -> None` | Legacy PBS sampling shard dispatcher updating `sample_size` in per-shard `settings.ini`. |
| `show_progress` | `(total_jobs: int | None = None, check_interval: float = 5) -> None` | Monitors submitted SLURM jobs (`_SUBMITTED_SLURM_JOBS`) or local jobs (`_SUBMITTED_LOCAL_PROCS`) with a `tqdm` progress bar until completion; on `KeyboardInterrupt`, cancels only tracked jobs. |
| `cancel_all_jobs` | `() -> None` | Cancels tracked SLURM jobs (or `scancel -u <user>` if no tracked IDs exist on SLURM) or sends `SIGTERM` -> 5 s wait -> `SIGKILL` strictly to tracked `_SUBMITTED_LOCAL_PROCS`, then removes `job_*` directories. |

#### Result Collection, Filtering, Stratified Binning & Multiprocessing

| Function | Signature | Description |
|---|---|---|
| `collect_json` | `(output: str, glob_target: str, cleanup: bool = True) -> None` | Concatenates JSON list shards matching `glob_target` into `output` and optionally removes `job_*` directories. |
| `collect_csv` | `(output: str, glob_target: str, header: str = "", index: bool = False, cleanup: bool = True) -> None` | Concatenates CSV shard files matching `glob_target` into `output`. |
| `collect_csv_filter` | `(output: str, glob_target: str, header: str, condition: Callable[[str], bool], cleanup: bool = True) -> None` | Writes all rows to `output` and rows matching `condition(line)` to `<stem>_filtered.<ext>`. |
| `exclude_elements_json` | `(input_json: Sequence[dict[str, Any]], exclude_elements: Collection[str]) -> list[dict[str, Any]]` | Filters out CIF JSON entries containing any element in `exclude_elements` or missing `material_id`. |
| `determine_bin_count` | `(data_size: int, target_values: np.ndarray | Sequence[float]) -> int` | Computes an adaptive bin count by averaging Sturges, Freedman-Diaconis, and Scott rules. |
| `adaptive_dynamic_binning` | `(data: pd.DataFrame, target_column: str, test_size: float = 0.2, random_state: int = 42) -> tuple[pd.DataFrame, pd.DataFrame, list[float]]` | Quantile-binned stratified train/test split returning `(train_df, test_df, bin_edges)` with zero `pandas` `SettingWithCopyWarning`/`FutureWarning`. |
| `parallel_process_json` | `(process_func: Callable[..., Any], data: Sequence[Any], n_processes: int = 16, output_file: str = "result.csv", **kwargs: Any) -> list[Any]` | Runs `process_func` over `data` using `multiprocessing.Pool` initialized with 1 BLAS/OpenMP thread per worker (`_init_single_thread_worker`). |
| `parallel_process_csv` | `(process_func: Callable[..., Any], filename: str, n_processes: int = 16, output_file: str = "result.csv", skip_header: bool = False, **kwargs: Any) -> list[Any]` | CSV line-processing counterpart to `parallel_process_json`. |

---

## 2. Command-Line Interface (`slices.cli`)

Registered in `pyproject.toml` as console entry point `slices = "slices.cli:main"` and invocable directly as `python -m slices.cli`.

### Public Exports (`slices.cli.__all__`)

`ALL_CLI_RELAX_MODELS` (`(*RELAX_MODELS, *OPTIONAL_MLIP_MODELS)`), `build_parser`, `canonicalize_slices`, `decode_slices`, `encode_structure`, `main`, `validate_slices`.

### Programmatic API

| Function | Signature | Description |
|---|---|---|
| `encode_structure` | `(input_file: str | Path, output_file: str | Path | None = None, strategy: int = 4, graph_method: str = "econnn") -> str` | Encodes a CIF/POSCAR/JSON file (or `"-"` CIF on stdin) using `SLICES(relax_model=None, graph_method=graph_method)` (zero MLIP overhead). |
| `decode_slices` | `(slices_input: str | Path, output_file: str | Path | None = None, relax_model: str | None = "auto", optimizer: str = "BFGS", fmax: float = 0.2, steps: int = 100, strategy: int = 4, use_robust: bool = False, seed: int = 0, fmt: str | None = None) -> tuple[Structure, float]` | Decodes a SLICES file, `"-"` stdin, or inline string via `SLICES2structure` (or `robust_SLICES2structure` when `use_robust=True`). |
| `validate_slices` | `(slices_input: str | Path, strategy: int = 4, basic: bool = False, check_duplicates: bool = False, graph_rank_check: bool = True) -> bool` | Validates syntax and 3D quotient-graph topology using `SLICES(relax_model=None)`. |
| `canonicalize_slices` | `(slices_input: str | Path, output_file: str | Path | None = None, strategy: int = 4) -> str` | Canonicalizes a SLICES file, `"-"` stdin, or inline string using `SLICES(relax_model=None)`. |
| `build_parser` | `() -> argparse.ArgumentParser` | Constructs the CLI argument parser. |
| `main` | `(argv: Sequence[str] | None = None) -> int` | Executes the CLI and returns POSIX exit code `0` on success or `1` on invalid SLICES / errors. |

### Subcommands, Flags & Exit Codes

Global options: `--version` (prints `slices 4.0.2`, exits `0`), `--verbose` (prints full Python tracebacks on errors). Running with no subcommand prints help and exits `1`.

| Subcommand | Positional Input | Options & Defaults | Exit Codes |
|---|---|---|---|
| `encode` | `input_file` (CIF/POSCAR/JSON path or `"-"` for CIF stdin) | `-o/--output PATH`, `--strategy {1,2,3,4}` (`4`), `--graph-method {econnn,crystalnn,brunnernn,mininn}` (`econnn`) | `0` on success; `1` on error |
| `decode` | `slices_input` (file path, `"-"` stdin, or inline SLICES string) | `-o/--output PATH`, `--relax-model/--model/-m` (`"auto"`, normalizes aliases like `orb-v3` -> `orbv3`, `mace-mp` -> `mace`), `--optimizer {BFGS,LBFGS,FIRE,FIRE+BFGS}` (`BFGS`), `--fmax` (`0.2`), `--steps` (`100`), `--strategy {1,3,4}` (`4`), `--fmt {cif,poscar,json}` (inferred from `--output`), `--robust`, `--seed` (`0`) | `0` on success; `1` on decode failure or missing optional MLIP |
| `validate` | `slices_input` (file path, `"-"` stdin, or inline SLICES string) | `--strategy {1,3,4}` (`4`), `--basic`, `--check-duplicates`, `--no-graph-rank-check` | `0` if valid (`VALID`); `1` if invalid (`INVALID`) or error |
| `canonicalize` | `slices_input` (file path, `"-"` stdin, or inline SLICES string) | `-o/--output PATH`, `--strategy {1,3,4}` (`4`) | `0` on success; `1` on error |

### CLI Examples

```bash
slices --version
slices encode examples/NdSiRu.cif -o NdSiRu.slices
slices validate NdSiRu.slices
cat NdSiRu.slices | slices validate -
slices canonicalize NdSiRu.slices -o NdSiRu.canon.slices
slices decode NdSiRu.slices -o reconstructed.cif --relax-model auto
slices decode NdSiRu.slices -o reconstructed_zl.cif --relax-model none --robust --seed 0
```
