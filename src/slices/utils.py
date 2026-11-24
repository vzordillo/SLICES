"""Batch job execution, result collection, dataset binning, and multiprocessing helpers.

Provides local and SLURM batch-splitting utilities (``splitRun``, ``splitRun_csv``,
``splitRun_sample``, ``show_progress``, ``cancel_all_jobs``), output collectors
(``collect_json``, ``collect_csv``, ``collect_csv_filter``), composition filtering
(``exclude_elements_json``), stratified regression binning (``determine_bin_count``,
``adaptive_dynamic_binning``), and single-thread-per-worker ``multiprocessing.Pool``
helpers (``parallel_process_json``, ``parallel_process_csv``).

Process tracking is strictly scoped to SLURM job IDs (``_SUBMITTED_SLURM_JOBS``) and
local ``subprocess.Popen`` handles (``_SUBMITTED_LOCAL_PROCS``) spawned by the current
Python session, never terminating unrelated user processes on the host.
"""

from __future__ import annotations

import configparser
import contextlib
import getpass
import glob
import json
import logging
import math
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Collection, Iterator, Sequence
from functools import partial
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, TypeVar

import numpy as np
import pandas as pd
from pymatgen.core.structure import Structure
from sklearn.model_selection import train_test_split
from tqdm import tqdm

_logger = logging.getLogger(__name__)

__all__ = [
    "adaptive_dynamic_binning",
    "cancel_all_jobs",
    "collect_csv",
    "collect_csv_filter",
    "collect_json",
    "determine_bin_count",
    "exclude_elements_json",
    "is_slurm_available",
    "parallel_process_csv",
    "parallel_process_json",
    "show_progress",
    "splitRun",
    "splitRun_csv",
    "splitRun_sample",
    "split_list",
    "temporaryWorkingDirectory",
]

_T = TypeVar("_T")

# SLURM job IDs and local Popen handles submitted by the most recent splitRun* call.
# show_progress and cancel_all_jobs act exclusively on these tracked jobs/processes.
_SUBMITTED_SLURM_JOBS: list[str] = []
_SUBMITTED_LOCAL_PROCS: dict[str, subprocess.Popen[bytes]] = {}


@contextlib.contextmanager
def temporaryWorkingDirectory(path: str | os.PathLike[str]) -> Iterator[None]:
    """Temporarily change the current working directory to ``path`` and restore on exit.

    Args:
        path: Target directory path.

    Yields:
        ``None`` with the process working directory set to ``os.path.abspath(path)``.
    """
    old_cwd = os.getcwd()
    os.chdir(os.path.abspath(path))
    try:
        yield
    finally:
        os.chdir(old_cwd)


def split_list(a: Sequence[_T], n: int) -> Iterator[Sequence[_T]]:
    """Partition sequence ``a`` into ``n`` contiguous chunks of nearly equal size.

    Args:
        a: Input sequence to partition.
        n: Number of partitions (must be ``>= 1``).

    Yields:
        Contiguous slices of ``a``.
    """
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))


def is_slurm_available() -> bool:
    """Check whether SLURM job submission commands are available and enabled.

    Setting ``SLICES_FORCE_LOCAL=1`` (or ``true`` / ``yes``) forces local process
    execution even when SLURM binaries exist on ``PATH``.

    Returns:
        ``True`` if SLURM should be used, ``False`` otherwise.
    """
    if os.environ.get("SLICES_FORCE_LOCAL", "").strip().lower() in ("1", "true", "yes"):
        return False
    return shutil.which("sinfo") is not None or shutil.which("squeue") is not None


def _submit_slurm_job(script: str = "0_run.sh") -> None:
    """Submit ``script`` via ``sbatch`` in the current directory and record its job ID."""
    env = dict(os.environ, SLICES_PYTHON=sys.executable)
    result = subprocess.run(
        ["sbatch", "--parsable", script],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    job_id = result.stdout.strip().split(";")[0]
    if result.returncode == 0 and job_id:
        _SUBMITTED_SLURM_JOBS.append(job_id)
    else:
        print(f"sbatch failed in {os.getcwd()}: {result.stderr.strip()}")


def _run_local_job(
    script: str = "0_run.py",
    job_name: str | None = None,
) -> subprocess.Popen[bytes]:
    """Start ``script`` in the background in the current directory and track its ``Popen``."""
    env = dict(os.environ, SLICES_PYTHON=sys.executable)
    key = job_name or os.path.basename(os.getcwd())
    with open("log.txt", "wb") as out, open("error.txt", "wb") as err:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=out,
            stderr=err,
            env=env,
            start_new_session=(os.name != "nt"),
        )
    _SUBMITTED_LOCAL_PROCS[key] = proc
    return proc


def _cleanup_previous_run() -> None:
    """Remove stale ``job_*`` directories, ``structures_ori_opt``, and ``./result.csv``."""
    for job_path in glob.glob("job_*"):
        if os.path.isdir(job_path):
            shutil.rmtree(job_path, ignore_errors=True)
        elif os.path.isfile(job_path):
            Path(job_path).unlink(missing_ok=True)
    if os.path.isdir("structures_ori_opt"):
        shutil.rmtree("structures_ori_opt", ignore_errors=True)
    Path("result.csv").unlink(missing_ok=True)


def _cleanup_job_dirs(verbose: bool = False) -> None:
    """Remove all ``job_*`` subdirectories in the current working directory."""
    for job_dir in sorted(glob.glob("job_*")):
        try:
            if os.path.isdir(job_dir):
                shutil.rmtree(job_dir)
                if verbose:
                    msg = f"Removed job directory: {job_dir}"
                    print(msg)
                    _logger.info(msg)
        except FileNotFoundError:
            if verbose:
                msg = f"Job directory already absent: {job_dir}"
                print(msg)
                _logger.warning(msg)
        except OSError as exc:
            msg = f"Failed to remove job directory {job_dir}: {exc}"
            print(msg)
            _logger.error(msg)


def _signal_proc(proc: subprocess.Popen[bytes], sig: int) -> None:
    """Send signal ``sig`` to ``proc`` (and its process group on POSIX when session leader)."""
    if os.name != "nt":
        try:
            os.killpg(proc.pid, sig)
            return
        except (ProcessLookupError, PermissionError, OSError):
            pass
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        if sig == getattr(signal, "SIGKILL", signal.SIGTERM):
            proc.kill()
        else:
            proc.terminate()


def _terminate_tracked_local_procs(grace_seconds: float = 5.0) -> None:
    """Terminate only local background processes tracked in ``_SUBMITTED_LOCAL_PROCS``."""
    active = {name: proc for name, proc in _SUBMITTED_LOCAL_PROCS.items() if proc.poll() is None}
    if not active:
        msg = "No active tracked local SLICES worker processes found."
        print(msg)
        _logger.info(msg)
        _SUBMITTED_LOCAL_PROCS.clear()
        return

    pids_str = ", ".join(str(proc.pid) for proc in active.values())
    msg = f"Terminating tracked local worker PIDs: {pids_str}"
    print(msg)
    _logger.info(msg)

    for proc in active.values():
        _signal_proc(proc, signal.SIGTERM)

    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        if all(proc.poll() is not None for proc in active.values()):
            break
        time.sleep(0.1)

    remaining = [proc for proc in active.values() if proc.poll() is None]
    if remaining:
        rem_pids = ", ".join(str(proc.pid) for proc in remaining)
        kill_msg = f"Force-killing unresponsive tracked worker PIDs: {rem_pids}"
        print(kill_msg)
        _logger.info(kill_msg)
        sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
        for proc in remaining:
            _signal_proc(proc, sigkill)
        for proc in remaining:
            with contextlib.suppress(subprocess.TimeoutExpired, OSError):
                proc.wait(timeout=1.0)
        done_msg = "All tracked worker processes were force-terminated."
    else:
        done_msg = "All tracked worker processes terminated cleanly."
    print(done_msg)
    _logger.info(done_msg)
    _SUBMITTED_LOCAL_PROCS.clear()


def _detect_external_running_jobs() -> set[str]:
    """Fallback ``ps``/``pwdx`` probe when monitoring jobs not launched in this session."""
    running_jobs: set[str] = set()
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.splitlines():
            if "python" in line and "0_run.py" in line:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[1]
                    pwd_result = subprocess.run(
                        ["pwdx", pid],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if pwd_result.returncode == 0 and ":" in pwd_result.stdout:
                        job_path = pwd_result.stdout.strip().split(":", 1)[1].strip()
                        job_dir_name = os.path.basename(job_path)
                        if job_dir_name.startswith("job_"):
                            running_jobs.add(job_dir_name)
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.debug("External process check skipped: %s", exc)
    return running_jobs


def splitRun(filename: str, threads: int, skip_header: bool = False) -> None:
    """Split a JSON task list across ``job_*`` directories and submit to SLURM or locally.

    Automatically caps worker count to avoid empty shards when ``threads`` exceeds
    the number of tasks.

    Args:
        filename: Path to the JSON file containing the list of task items.
        threads: Desired number of parallel job shards.
        skip_header: Whether to skip the first element of the loaded JSON list.
    """
    _cleanup_previous_run()

    with open(filename, encoding="utf-8") as handle:
        try:
            cifs = json.load(handle)
        except json.JSONDecodeError as exc:
            print(f"JSON decode error in {filename}: {exc}")
            return

    tasks = cifs[1:] if skip_header else cifs
    tasks = [task for task in tasks if task]
    total_tasks = len(tasks)

    actual_threads = min(threads, total_tasks) if total_tasks > 0 else 1
    if actual_threads < threads:
        print(
            f"Task count ({total_tasks}) is smaller than requested threads ({threads}); "
            f"using {actual_threads} worker(s)."
        )

    cifs_split = list(split_list(tasks, actual_threads))
    use_slurm = is_slurm_available()
    _SUBMITTED_SLURM_JOBS.clear()
    _SUBMITTED_LOCAL_PROCS.clear()

    for i, shard in enumerate(cifs_split):
        job_dir = f"job_{i}"
        os.mkdir(job_dir)
        if os.path.isdir("./workflow"):
            shutil.copytree("./workflow", job_dir, dirs_exist_ok=True)
        temp_json_path = os.path.join(job_dir, "temp.json")
        with open(temp_json_path, "w", encoding="utf-8") as handle:
            json.dump(shard, handle)

        with temporaryWorkingDirectory(job_dir):
            if use_slurm:
                _submit_slurm_job()
            else:
                _run_local_job(job_name=job_dir)

    print("Computation tasks have been submitted.")


def splitRun_csv(filename: str, threads: int, skip_header: bool = False) -> None:
    """Split a CSV/line-based task file across ``job_*`` directories and submit jobs.

    Args:
        filename: Path to the input CSV file.
        threads: Desired number of parallel job shards.
        skip_header: Whether to skip the header line of ``filename``.
    """
    _cleanup_previous_run()

    with open(filename, encoding="utf-8") as handle:
        lines = handle.readlines()

    if skip_header:
        lines = lines[1:]

    cifs = [line for line in lines if line.strip()]
    total_tasks = len(cifs)

    actual_threads = min(threads, total_tasks) if total_tasks > 0 else 1
    if actual_threads < threads:
        print(
            f"Task count ({total_tasks}) is smaller than requested threads ({threads}); "
            f"using {actual_threads} worker(s)."
        )

    cifs_split = list(split_list(cifs, actual_threads))
    use_slurm = is_slurm_available()
    _SUBMITTED_SLURM_JOBS.clear()
    _SUBMITTED_LOCAL_PROCS.clear()

    for i, shard in enumerate(cifs_split):
        job_dir = f"job_{i}"
        os.mkdir(job_dir)
        if os.path.isdir("./workflow"):
            shutil.copytree("./workflow", job_dir, dirs_exist_ok=True)
        temp_csv_path = os.path.join(job_dir, "temp.csv")
        with open(temp_csv_path, "w", encoding="utf-8") as handle:
            handle.writelines(shard)

        with temporaryWorkingDirectory(job_dir):
            if use_slurm:
                _submit_slurm_job()
            else:
                _run_local_job(job_name=job_dir)

    print("Computation tasks have been submitted.")


def splitRun_sample(threads: int = 8, sample_size: int = 8000) -> None:
    """Configure per-shard ``sample_size`` in ``settings.ini`` and submit PBS sampling jobs.

    Args:
        threads: Number of parallel ``job_*`` directories to create.
        sample_size: Total number of samples across all shards.
    """
    config = configparser.ConfigParser()
    _cleanup_previous_run()
    config["Settings"] = {"sample_size": str(int(sample_size / threads))}
    with open("./workflow/settings.ini", "w", encoding="utf-8") as configfile:
        config.write(configfile)
    for i in range(threads):
        job_dir = f"job_{i}"
        os.mkdir(job_dir)
        if os.path.isdir("./workflow"):
            shutil.copytree("./workflow", job_dir, dirs_exist_ok=True)
        with temporaryWorkingDirectory(job_dir):
            if len(sys.argv) == 2 and sys.argv[1] == "test":
                subprocess.run(["qsub", "0_test.pbs"], check=False)
            else:
                subprocess.run(
                    ["qsub", "0_run.pbs"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
    print("Sampling tasks have been submitted.")


def show_progress(total_jobs: int | None = None, check_interval: float = 5) -> None:
    """Monitor submitted SLURM or local ``job_*`` shards with a progress bar until completion.

    On ``KeyboardInterrupt``, cancels only the SLURM jobs or local ``Popen`` processes
    submitted by this session rather than unrelated user processes.

    Args:
        total_jobs: Expected number of local ``job_*`` directories (auto-detected if ``None``).
        check_interval: Polling interval in seconds.
    """
    use_slurm = is_slurm_available()
    if use_slurm:
        print("SLURM system detected. Using SLURM-based processing.")
        current_user = getpass.getuser()
        try:
            count_task = 0
            total_task = 0
            with tqdm(
                total=100,
                position=0,
                leave=True,
                bar_format="{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}",
            ) as pbar:
                pbar.set_description("Progress")
                while True:
                    count_task_prev = count_task
                    try:
                        result = subprocess.run(
                            ["squeue", "-u", current_user, "-h", "-o", "%i %T"],
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        tracked = set(_SUBMITTED_SLURM_JOBS)
                        states = [
                            state
                            for job_id, _, state in (
                                line.partition(" ") for line in result.stdout.splitlines()
                            )
                            if not tracked or job_id.split("_")[0] in tracked
                        ]
                    except subprocess.CalledProcessError as exc:
                        print(f"Error executing squeue: {exc.stderr}")
                        break

                    count_task = sum(
                        1
                        for state in states
                        if state in ("RUNNING", "PENDING", "CONFIGURING", "SUSPENDED")
                    )
                    if count_task_prev < count_task:
                        total_task = count_task
                        pbar.reset(total=100)
                        pbar.set_description("Progress")
                    if count_task_prev > count_task and total_task > 0:
                        completed_pct = (total_task - count_task) / total_task * 100
                        pbar.update(completed_pct - pbar.n)
                    if count_task == 0 and total_task > 0:
                        pbar.n = pbar.total
                        pbar.refresh()
                        break
                    time.sleep(check_interval)
        except KeyboardInterrupt:
            try:
                if _SUBMITTED_SLURM_JOBS:
                    subprocess.run(["scancel", *_SUBMITTED_SLURM_JOBS], check=True)
                    print(f"\n{len(_SUBMITTED_SLURM_JOBS)} submitted jobs have been canceled")
                else:
                    subprocess.run(["scancel", "-u", current_user], check=True)
                    print("\nAll jobs have been canceled")
            except subprocess.CalledProcessError as exc:
                print(f"\nError canceling jobs: {exc.stderr}")
        except OSError as env_err:
            print(env_err)
        return

    print("No SLURM system detected. Falling back to local processing.")
    try:
        if total_jobs is None:
            total_jobs = len(glob.glob("job_*"))

        if total_jobs == 0:
            msg = "No job directories detected to monitor."
            print(msg)
            _logger.info(msg)
            return

        with tqdm(
            total=total_jobs,
            position=0,
            leave=True,
            bar_format="{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}",
        ) as pbar:
            completed = 0
            while completed < total_jobs:
                completed = 0
                if _SUBMITTED_LOCAL_PROCS:
                    running_jobs = {
                        name
                        for name, proc in _SUBMITTED_LOCAL_PROCS.items()
                        if proc.poll() is None
                    }
                else:
                    running_jobs = _detect_external_running_jobs()

                for i in range(total_jobs):
                    job_dir = f"job_{i}"
                    is_completed = False
                    if job_dir not in running_jobs:
                        output_json = os.path.join(job_dir, "output.json")
                        output_csv = os.path.join(job_dir, "result.csv")
                        if os.path.exists(output_json):
                            with contextlib.suppress(OSError):
                                if os.path.getsize(output_json) > 10:
                                    is_completed = True
                        if not is_completed and os.path.exists(output_csv):
                            with contextlib.suppress(OSError):
                                if os.path.getsize(output_csv) > 20:
                                    is_completed = True
                    if is_completed:
                        completed += 1

                pbar.n = completed
                pbar.refresh()
                if completed >= total_jobs:
                    break
                time.sleep(check_interval)

            pbar.n = pbar.total
            pbar.refresh()
    except KeyboardInterrupt:
        print("\nCancellation requested. Terminating tracked local worker processes...")
        _logger.info("Cancellation requested. Terminating tracked local worker processes.")
        _terminate_tracked_local_procs()
        print("Cleaning up job directories...")
        _logger.info("Cleaning up job directories.")
        _cleanup_job_dirs(verbose=True)
    print("Task monitoring finished.")
    _logger.info("Task monitoring finished.")


def cancel_all_jobs() -> None:
    """Cancel tracked SLURM jobs or tracked local ``job_*`` worker processes and clean up."""
    if is_slurm_available():
        current_user = getpass.getuser()
        if _SUBMITTED_SLURM_JOBS:
            subprocess.run(["scancel", *_SUBMITTED_SLURM_JOBS], check=True)
            print(f"{len(_SUBMITTED_SLURM_JOBS)} submitted jobs have been canceled")
            _SUBMITTED_SLURM_JOBS.clear()
        else:
            subprocess.run(["scancel", "-u", current_user], check=True)
            print("All jobs have been canceled")
        return

    _terminate_tracked_local_procs()
    print("Cleaning up job directories...")
    _logger.info("Cleaning up job directories.")
    _cleanup_job_dirs(verbose=True)


def collect_json(output: str, glob_target: str, cleanup: bool = True) -> None:
    """Concatenate JSON list files matching ``glob_target`` into ``output``.

    Args:
        output: Destination JSON file path.
        glob_target: Glob pattern for per-shard JSON files.
        cleanup: Whether to remove ``job_*`` directories after collection.
    """
    data: list[Any] = []
    for path in glob.glob(glob_target, recursive=True):
        with open(path, encoding="utf-8") as infile:
            temp = json.load(infile)
            data.extend(temp)
    with open(output, "w", encoding="utf-8") as outfile:
        json.dump(data, outfile)
    if cleanup:
        _cleanup_job_dirs(verbose=False)
    print(f"Results have been collected into: {output}")


def collect_csv(
    output: str,
    glob_target: str,
    header: str = "",
    index: bool = False,
    cleanup: bool = True,
) -> None:
    """Concatenate CSV shard files matching ``glob_target`` into ``output``.

    Args:
        output: Destination CSV file path.
        glob_target: Glob pattern for per-shard CSV files.
        header: Optional CSV header string (including trailing newline if needed).
        index: Whether to prepend a sequential 0-based row index column.
        cleanup: Whether to remove ``job_*`` directories after collection.
    """
    result_sli = ""
    if index:
        row_idx = 0
        for path in glob.glob(glob_target):
            with open(path, encoding="utf-8") as infile:
                for line in infile:
                    result_sli += f"{row_idx},{line}"
                    row_idx += 1
    else:
        for path in glob.glob(glob_target, recursive=True):
            with open(path, encoding="utf-8") as infile:
                result_sli += infile.read()
    with open(output, "w", encoding="utf-8") as outfile:
        if header != "":
            outfile.write(header)
        outfile.write(result_sli)
    if cleanup:
        _cleanup_job_dirs(verbose=False)
    print(f"Results have been collected into: {output}")


def collect_csv_filter(
    output: str,
    glob_target: str,
    header: str,
    condition: Callable[[str], bool],
    cleanup: bool = True,
) -> None:
    """Collect all CSV rows into ``output`` and filtered rows into ``<stem>_filtered.<ext>``.

    Args:
        output: Destination CSV file path for unfiltered rows.
        glob_target: Glob pattern for per-shard CSV files.
        header: Optional CSV header string.
        condition: Predicate receiving each raw CSV line and returning ``True`` to retain.
        cleanup: Whether to remove ``job_*`` directories after collection.
    """
    result_csv = ""
    result_filtered_csv = ""
    for path in glob.glob(glob_target):
        with open(path, encoding="utf-8") as infile:
            for line in infile:
                result_csv += line
                if condition(line):
                    result_filtered_csv += line
    with open(output, "w", encoding="utf-8") as outfile:
        if header != "":
            outfile.write(header)
        outfile.write(result_csv)
    stem, ext = output.split(".", 1)
    filtered_output = f"{stem}_filtered.{ext}"
    with open(filtered_output, "w", encoding="utf-8") as outfile:
        if header != "":
            outfile.write(header)
        outfile.write(result_filtered_csv)
    if cleanup:
        _cleanup_job_dirs(verbose=False)
    print(f"Results have been collected into: {output}")


def exclude_elements_json(
    input_json: Sequence[dict[str, Any]],
    exclude_elements: Collection[str],
) -> list[dict[str, Any]]:
    """Filter out CIF entries containing excluded elements or missing ``material_id``.

    Args:
        input_json: Sequence of dictionaries with ``"cif"`` and ``"material_id"`` keys.
        exclude_elements: Element symbols to exclude.

    Returns:
        Filtered list of material dictionaries.
    """
    print("excluding materials containing elements not supported")
    filtered_json: list[dict[str, Any]] = []
    for item in tqdm(
        input_json,
        position=0,
        leave=True,
        bar_format="{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}",
    ):
        ori = Structure.from_str(item["cif"], fmt="cif")
        species = [str(sp) for sp in ori.species]
        has_excluded = any(sp in exclude_elements for sp in species)
        if not has_excluded and item["material_id"] is not None:
            filtered_json.append(item)
    excluded_pct = round((len(input_json) - len(filtered_json)) / len(input_json) * 100, 1)
    print(f"{excluded_pct}% materials excluded")
    return filtered_json


def determine_bin_count(data_size: int, target_values: np.ndarray | Sequence[float]) -> int:
    """Compute an adaptive histogram bin count averaging Sturges, Freedman-Diaconis, and Scott.

    Args:
        data_size: Number of non-null samples.
        target_values: Numeric array of target property values.

    Returns:
        Integer bin count clamped to ``[5, max(5, data_size // 20)]``.
    """
    sturges_bins = math.ceil(math.log2(data_size)) + 1

    q75, q25 = np.percentile(target_values, [75, 25])
    iqr = q75 - q25
    bin_width = 2 * iqr * (len(target_values) ** (-1 / 3))
    fd_bins = math.ceil((max(target_values) - min(target_values)) / bin_width)

    scott_denom = 3.5 * float(np.std(target_values)) * (len(target_values) ** (-1 / 3))
    scott_bins = math.ceil((max(target_values) - min(target_values)) / scott_denom)

    avg_bins = int(np.mean([sturges_bins, fd_bins, scott_bins]))
    return max(min(avg_bins, data_size // 20), 5)


def adaptive_dynamic_binning(
    data: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, list[float]]:
    """Perform quantile-binned stratified train/test splitting on a continuous target column.

    Args:
        data: Input DataFrame containing ``target_column``.
        target_column: Name of the numeric regression column to stratify on.
        test_size: Fraction of each bin assigned to the test split.
        random_state: Random seed for reproducible per-bin splits and shuffles.

    Returns:
        Tuple ``(train_data, test_data, bin_edges)``.
    """
    working = data.copy()
    working[target_column] = pd.to_numeric(working[target_column], errors="coerce")
    data_cleaned = working.dropna(subset=[target_column]).copy()

    print(f"\nOriginal row count: {len(data)}")
    print(f"Cleaned row count: {len(data_cleaned)}")

    target_values = data_cleaned[target_column].to_numpy()
    n_bins = determine_bin_count(len(data_cleaned), target_values)
    print(f"Automatically selected bin count: {n_bins}")

    percentiles = [i * 100 / n_bins for i in range(n_bins + 1)]
    bins = sorted(set(data_cleaned[target_column].quantile([p / 100 for p in percentiles])))
    labels = [f"Bin{i + 1}" for i in range(len(bins) - 1)]

    data_cleaned["bin"] = pd.cut(
        data_cleaned[target_column], bins=bins, labels=labels, include_lowest=True
    )

    train_parts: list[pd.DataFrame] = []
    test_parts: list[pd.DataFrame] = []
    for bin_label in data_cleaned["bin"].unique():
        bin_data = data_cleaned[data_cleaned["bin"] == bin_label]
        if len(bin_data) > 1:
            bin_train, bin_test = train_test_split(
                bin_data, test_size=test_size, random_state=random_state
            )
            train_parts.append(bin_train)
            test_parts.append(bin_test)
        else:
            train_parts.append(bin_data)

    empty = pd.DataFrame(columns=data_cleaned.columns)
    train_data = pd.concat(train_parts, ignore_index=False) if train_parts else empty.copy()
    test_data = pd.concat(test_parts, ignore_index=False) if test_parts else empty.copy()

    train_data = train_data.drop("bin", axis=1)
    test_data = test_data.drop("bin", axis=1)

    train_data = train_data.sample(frac=1, random_state=random_state).reset_index(drop=True)
    test_data = test_data.sample(frac=1, random_state=random_state).reset_index(drop=True)
    return train_data, test_data, [float(b) for b in bins]


def _init_single_thread_worker() -> None:
    """Configure single-threaded BLAS/OpenMP execution inside ``Pool`` workers."""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"


def parallel_process_json(
    process_func: Callable[..., Any],
    data: Sequence[Any],
    n_processes: int = 16,
    output_file: str = "result.csv",
    **kwargs: Any,
) -> list[Any]:
    """Process a sequence of items in parallel with ``multiprocessing.Pool`` (1 CPU/worker).

    Args:
        process_func: Worker callable accepting a single item from ``data`` and ``**kwargs``.
        data: Sequence of items (typically loaded from JSON) to process.
        n_processes: Maximum number of worker processes (capped to ``len(data)`` and CPUs).
        output_file: Output file path for non-``None`` line results (empty string disables).
        **kwargs: Additional keyword arguments bound via ``functools.partial``.

    Returns:
        List of non-``None`` results returned by ``process_func``.
    """
    _init_single_thread_worker()
    if not data:
        return []
    n_processes = min(n_processes, len(data), cpu_count())
    print(f"Processing in parallel with {n_processes} worker process(es)...")

    func_with_kwargs = partial(process_func, **kwargs)
    results: list[Any] = []
    with (
        Pool(processes=n_processes, initializer=_init_single_thread_worker) as pool,
        tqdm(
            total=len(data),
            position=0,
            leave=True,
            bar_format="{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}",
        ) as pbar,
    ):
        for result in pool.imap_unordered(func_with_kwargs, data, chunksize=1):
            if result is not None:
                results.append(result)
            pbar.update(1)

    if results and output_file:
        with open(output_file, "w", encoding="utf-8") as handle:
            for result in results:
                handle.write(f"{result}\n")
        print(f"Results saved to: {output_file}")

    return results


def parallel_process_csv(
    process_func: Callable[..., Any],
    filename: str,
    n_processes: int = 16,
    output_file: str = "result.csv",
    skip_header: bool = False,
    **kwargs: Any,
) -> list[Any]:
    """Process lines of a CSV file in parallel with ``multiprocessing.Pool`` (1 CPU/worker).

    Args:
        process_func: Worker callable accepting a single text line and ``**kwargs``.
        filename: Input CSV file path.
        n_processes: Maximum number of worker processes (capped to line count and CPUs).
        output_file: Output file path for non-``None`` line results (empty string disables).
        skip_header: Whether to skip the first line of ``filename``.
        **kwargs: Additional keyword arguments bound via ``functools.partial``.

    Returns:
        List of non-``None`` results returned by ``process_func``.
    """
    _init_single_thread_worker()
    with open(filename, encoding="utf-8") as handle:
        lines = handle.readlines()

    if skip_header:
        lines = lines[1:]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return []

    n_processes = min(n_processes, len(lines), cpu_count())
    print(f"Processing in parallel with {n_processes} worker process(es)...")

    func_with_kwargs = partial(process_func, **kwargs)
    results: list[Any] = []
    with (
        Pool(processes=n_processes, initializer=_init_single_thread_worker) as pool,
        tqdm(
            total=len(lines),
            position=0,
            leave=True,
            bar_format="{desc:<5.5}{percentage:3.0f}%|{bar:15}{r_bar}",
        ) as pbar,
    ):
        for result in pool.imap_unordered(func_with_kwargs, lines, chunksize=1):
            if result is not None:
                results.append(result)
            pbar.update(1)

    if results and output_file:
        with open(output_file, "w", encoding="utf-8") as handle:
            for result in results:
                handle.write(f"{result}\n")
        print(f"Results saved to: {output_file}")

    return results
