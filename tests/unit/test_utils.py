"""Unit tests for batch execution, safe process tracking, collection, and binning utilities."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from slices import utils


@pytest.mark.unit
def test_split_list_partitioning() -> None:
    """Verify split_list partitions sequences evenly and preserves element order."""
    even = [list(chunk) for chunk in utils.split_list(list(range(10)), 5)]
    assert [len(c) for c in even] == [2, 2, 2, 2, 2]
    assert [x for c in even for x in c] == list(range(10))

    uneven = [list(chunk) for chunk in utils.split_list(list(range(10)), 3)]
    assert [len(c) for c in uneven] == [4, 3, 3]
    assert [x for c in uneven for x in c] == list(range(10))

    oversharded = [list(chunk) for chunk in utils.split_list([10, 20], 4)]
    assert oversharded == [[10], [20], [], []]


@pytest.mark.unit
def test_temporary_working_directory_restores_cwd_on_error(tmp_path: Path) -> None:
    """Verify temporaryWorkingDirectory switches CWD and restores it even on exception."""
    original_cwd = os.getcwd()
    sub = tmp_path / "nested"
    sub.mkdir()

    with utils.temporaryWorkingDirectory(sub):
        assert Path(os.getcwd()).resolve() == sub.resolve()
    assert os.getcwd() == original_cwd

    with pytest.raises(RuntimeError, match="boom"), utils.temporaryWorkingDirectory(sub):
        assert Path(os.getcwd()).resolve() == sub.resolve()
        raise RuntimeError("boom")
    assert os.getcwd() == original_cwd


@pytest.mark.unit
def test_is_slurm_available_respects_force_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify SLICES_FORCE_LOCAL overrides SLURM binary detection on PATH."""
    monkeypatch.setattr(shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
    monkeypatch.delenv("SLICES_FORCE_LOCAL", raising=False)
    assert utils.is_slurm_available() is True

    for val in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv("SLICES_FORCE_LOCAL", val)
        assert utils.is_slurm_available() is False

    monkeypatch.delenv("SLICES_FORCE_LOCAL", raising=False)
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    assert utils.is_slurm_available() is False


@pytest.mark.unit
def test_split_run_json_progress_and_collect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify splitRun spawns tracked local workers, caps threads, and collects JSON."""
    monkeypatch.setenv("SLICES_FORCE_LOCAL", "1")
    workflow = tmp_path / "workflow"
    workflow.mkdir()
    (workflow / "0_run.py").write_text(
        "import json\n"
        "items = json.load(open('temp.json', encoding='utf-8'))\n"
        "out = [{'item': x, 'doubled': x * 2} for x in items]\n"
        "json.dump(out, open('output.json', 'w', encoding='utf-8'))\n",
        encoding="utf-8",
    )
    input_json = tmp_path / "tasks.json"
    input_json.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with utils.temporaryWorkingDirectory(tmp_path):
        utils.splitRun("tasks.json", threads=5)
        assert sorted(utils._SUBMITTED_LOCAL_PROCS.keys()) == ["job_0", "job_1", "job_2"]
        utils.show_progress(check_interval=0.05)
        utils.collect_json("merged.json", "job_*/output.json", cleanup=True)
        utils._SUBMITTED_LOCAL_PROCS.clear()

    merged = json.loads((tmp_path / "merged.json").read_text(encoding="utf-8"))
    assert sorted(entry["doubled"] for entry in merged) == [2, 4, 6]
    assert list(tmp_path.glob("job_*")) == []


@pytest.mark.unit
def test_split_run_csv_and_collect_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify splitRun_csv, show_progress, collect_csv, and collect_csv_filter."""
    monkeypatch.setenv("SLICES_FORCE_LOCAL", "1")
    workflow = tmp_path / "workflow"
    workflow.mkdir()
    (workflow / "0_run.py").write_text(
        "lines = open('temp.csv', encoding='utf-8').readlines()\n"
        "with open('result.csv', 'w', encoding='utf-8') as out:\n"
        "    for line in lines:\n"
        "        out.write(line.strip() + ',processed_row_padding\\n')\n",
        encoding="utf-8",
    )
    (tmp_path / "input.csv").write_text(
        "id,tag\n0,keep\n1,drop\n2,keep\n",
        encoding="utf-8",
    )

    with utils.temporaryWorkingDirectory(tmp_path):
        utils.splitRun_csv("input.csv", threads=2, skip_header=True)
        utils.show_progress(check_interval=0.05)
        utils.collect_csv(
            "indexed.csv",
            "job_*/result.csv",
            header="idx,id,tag,status\n",
            index=True,
            cleanup=False,
        )
        utils.collect_csv_filter(
            "all_rows.csv",
            "job_*/result.csv",
            header="id,tag,status\n",
            condition=lambda line: ",keep," in line,
            cleanup=True,
        )
        utils._SUBMITTED_LOCAL_PROCS.clear()

    indexed_lines = (tmp_path / "indexed.csv").read_text(encoding="utf-8").splitlines()
    assert indexed_lines[0] == "idx,id,tag,status"
    assert len(indexed_lines) == 4

    all_lines = (tmp_path / "all_rows.csv").read_text(encoding="utf-8").splitlines()
    filtered_lines = (tmp_path / "all_rows_filtered.csv").read_text(encoding="utf-8").splitlines()
    assert len(all_lines) == 4
    assert len(filtered_lines) == 3
    assert list(tmp_path.glob("job_*")) == []


@pytest.mark.unit
def test_cancel_all_jobs_terminates_only_tracked_workers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify cancel_all_jobs kills tracked job_* Popen workers while sparing other PIDs."""
    monkeypatch.setenv("SLICES_FORCE_LOCAL", "1")
    workflow = tmp_path / "workflow"
    workflow.mkdir()
    (workflow / "0_run.py").write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
    (tmp_path / "tasks.json").write_text(json.dumps(["a", "b"]), encoding="utf-8")

    bystander = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        start_new_session=True,
    )
    try:
        with utils.temporaryWorkingDirectory(tmp_path):
            utils.splitRun("tasks.json", threads=2)
            tracked_procs = list(utils._SUBMITTED_LOCAL_PROCS.values())
            assert len(tracked_procs) == 2
            assert all(proc.poll() is None for proc in tracked_procs)

            utils.cancel_all_jobs()

            assert utils._SUBMITTED_LOCAL_PROCS == {}
            assert all(proc.poll() is not None for proc in tracked_procs)
            assert list(tmp_path.glob("job_*")) == []
            assert bystander.poll() is None
    finally:
        bystander.terminate()
        bystander.wait(timeout=5.0)


@pytest.mark.unit
def test_exclude_elements_json_filters_forbidden_elements_and_null_ids() -> None:
    """Verify exclude_elements_json drops excluded species and null material_id entries."""
    si_cif = Structure(Lattice.cubic(5.43), ["Si"], [[0.0, 0.0, 0.0]]).to(fmt="cif")
    fr_cif = Structure(Lattice.cubic(5.00), ["Fr"], [[0.0, 0.0, 0.0]]).to(fmt="cif")
    entries = [
        {"material_id": "mp-1", "cif": si_cif},
        {"material_id": "mp-2", "cif": fr_cif},
        {"material_id": None, "cif": si_cif},
    ]
    kept = utils.exclude_elements_json(entries, exclude_elements={"Fr"})
    assert len(kept) == 1
    assert kept[0]["material_id"] == "mp-1"


@pytest.mark.unit
def test_determine_bin_count_and_adaptive_dynamic_binning_zero_warnings() -> None:
    """Verify adaptive_dynamic_binning splits data cleanly with zero pandas warnings."""
    rng = np.random.default_rng(42)
    values = rng.normal(loc=-1.5, scale=0.8, size=200)
    bins = utils.determine_bin_count(len(values), values)
    assert 5 <= bins <= len(values) // 20

    raw_targets = [str(v) for v in values] + ["not_a_number", None]
    df = pd.DataFrame({"id": range(len(raw_targets)), "eform": raw_targets})

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        train_df, test_df, bin_edges = utils.adaptive_dynamic_binning(
            df, target_column="eform", test_size=0.2, random_state=42
        )

    bad_warnings = [
        w
        for w in caught
        if issubclass(w.category, FutureWarning) or "SettingWithCopy" in w.category.__name__
    ]
    assert bad_warnings == []
    assert len(train_df) + len(test_df) == 200
    assert "bin" not in train_df.columns
    assert "bin" not in test_df.columns
    assert len(bin_edges) >= 2
