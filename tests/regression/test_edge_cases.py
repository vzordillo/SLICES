"""Regression tests for SLICES v4.0.2 migration rules (RUL-01..08, CA-01..09) and edge cases."""

from __future__ import annotations

import ast
import csv
import inspect
import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from slices.core import SLICES
from slices.exceptions import (
    ModelDownloadError,
    RelaxBackendError,
    SLICESError,
)
from slices.gfnff_helper import run_gfnff_helper
from slices.mlip_relaxer import mlip_available
from slices.relax_backends import resolve_relax_model


@pytest.mark.regression
def test_rul07_lazy_import_leaves_omp_and_keras_env_untouched(repo_root: Path) -> None:
    """Verify importing slices and lightweight submodules does not load slices.core or mutate env."""
    env = dict(os.environ)
    env.pop("OMP_NUM_THREADS", None)
    env.pop("TF_USE_LEGACY_KERAS", None)
    env["PYTHONPATH"] = str(repo_root / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    probe = (
        "import json, os, sys\n"
        "import slices\n"
        "import slices.exceptions\n"
        "import slices.relax_backends\n"
        "from slices import check_SLICES\n"
        "payload = {\n"
        "    'version': slices.__version__,\n"
        "    'omp': os.environ.get('OMP_NUM_THREADS'),\n"
        "    'keras': os.environ.get('TF_USE_LEGACY_KERAS'),\n"
        "    'core_loaded': 'slices.core' in sys.modules,\n"
        "    'callable_check': callable(check_SLICES),\n"
        "}\n"
        "print(json.dumps(payload))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", probe],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(proc.stdout.strip())
    assert result["version"] == "4.1.0"
    assert result["omp"] is None
    assert result["keras"] is None
    assert result["core_loaded"] is False
    assert result["callable_check"] is True


@pytest.mark.regression
def test_ndsiru_oxidation_state_element_comparator_handling(
    slices_nequip: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify NdSiRu.cif oxidation-state sites require ElementComparator after decoding."""
    assert any(
        getattr(sp, "oxi_state", None) is not None for sp in ndsiru_structure.species
    )

    sli = slices_nequip.structure2SLICES(ndsiru_structure, strategy=4)
    decoded, _ = slices_nequip.SLICES2structure(sli, strategy=4)

    raw_matcher = StructureMatcher()
    elem_matcher = StructureMatcher(comparator=ElementComparator())
    assert bool(raw_matcher.fit(ndsiru_structure, decoded)) is False
    assert bool(elem_matcher.fit(ndsiru_structure, decoded)) is True


@pytest.mark.regression
def test_rul05_relocated_v4_benchmark_and_untouched_mp20_datasets(
    repo_root: Path,
    data_dir: Path,
) -> None:
    """Verify relocated 2,383-row v4 benchmark, untouched 14,303-row MP20 CSV, and no MatterGPT."""
    assert not (repo_root / "MatterGPT").exists()
    assert not (data_dir / "test_data.csv").exists()

    v4_bench = data_dir / "mp20_nonmetal" / "mp20_v4_benchmark_2383.csv"
    assert v4_bench.is_file()
    with v4_bench.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        row_count = sum(1 for _ in reader)
    assert "formation_energy_per_atom" in header
    assert row_count == 2383

    legacy_mp20 = data_dir / "mp20_nonmetal" / "mp20_eform_bandgap_nonmetal.csv"
    assert legacy_mp20.is_file()
    with legacy_mp20.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        mp20_header = next(reader)
        mp20_count = sum(1 for _ in reader)
    assert "eform" in mp20_header
    assert mp20_count == 14303

    chempot_path = data_dir / "mp20_nonmetal" / "chemPotMP.json"
    assert chempot_path.is_file()
    chempot = json.loads(chempot_path.read_text(encoding="utf-8"))
    assert isinstance(chempot, dict) and "O" in chempot


@pytest.mark.regression
def test_rul04_utils_contains_zero_os_system_or_pgrep_process_kills(repo_root: Path) -> None:
    """Verify src/slices/utils.py contains zero os.system calls or broad pgrep/pkill strings."""
    utils_path = repo_root / "src" / "slices" / "utils.py"
    source = utils_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(utils_path))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "system"
        ):
            pytest.fail("Forbidden os.system call found in src/slices/utils.py")

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            for forbidden in ("pgrep", "pkill", "pt_main_thread"):
                assert forbidden not in lowered


@pytest.mark.regression
def test_high_coordination_over_19_neighbor_cap_in_get_nbf_blist(
    slices_no_relax: SLICES,
    data_dir: Path,
) -> None:
    """Verify get_nbf_blist caps supercell neighbor counts at <= 19 on >19-CN topology (G15b)."""
    csv_path = data_dir / "mp20_nonmetal" / "test_data_reduce_zero.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        row_1205 = next(itertools.islice(reader, 1205, 1206))
    high_cn_slices = row_1205["SLICES"]

    slices_no_relax.from_SLICES(high_cn_slices, strategy=4)
    nbf, blist = slices_no_relax.get_nbf_blist()
    lines = nbf.strip().splitlines()
    assert len(lines) == 22

    neighbor_counts = [int(x) for x in lines[-1].split()]
    assert max(neighbor_counts) == 19
    assert len(blist) > 0

    gfnff_out = run_gfnff_helper(nbf)
    assert len(gfnff_out["blist"]) > 0


@pytest.mark.regression
def test_single_atom_primitive_cell_cocycle_none_branch(slices_nequip: SLICES) -> None:
    """Verify 1-atom primitive cell exercises cocycle_rep is None cleanly in to_structures."""
    na_prim = Structure(
        Lattice.from_parameters(3.66, 3.66, 3.66, 109.47122, 109.47122, 109.47122),
        ["Na"],
        [[0.0, 0.0, 0.0]],
    )
    sli = slices_nequip.structure2SLICES(na_prim, strategy=4)
    slices_nequip.from_SLICES(sli, strategy=4)

    structures, energy = slices_nequip.to_structures()
    assert len(structures) == 3
    assert structures[0] == structures[1]
    assert len(structures[2]) == 1
    assert np.isfinite(energy) and energy < 0.0


@pytest.mark.regression
def test_public_api_defaults_m3gnet_guidance_and_sibling_exceptions(
    slices_nequip: SLICES,
) -> None:
    """Verify SLICES.__init__ defaults, m3gnet ImportError guidance, and exception hierarchy."""
    sig = inspect.signature(SLICES.__init__)
    assert sig.parameters["graph_method"].default == "econnn"
    assert sig.parameters["check_results"].default is False
    assert sig.parameters["optimizer"].default == "BFGS"
    assert sig.parameters["fmax"].default == 0.2
    assert sig.parameters["steps"].default == 100
    assert sig.parameters["relax_model"].default == "auto"

    assert slices_nequip.relax_model == "nequip-s+l"
    assert slices_nequip.relaxer.optimizer == "BFGS"

    if not mlip_available("m3gnet"):
        with pytest.raises(ImportError, match="NequIP-OAM"):
            resolve_relax_model("m3gnet")

    with pytest.raises(ValueError, match="Unknown relax_model"):
        resolve_relax_model("nonexistent_backend_xyz")

    assert issubclass(RelaxBackendError, SLICESError)
    assert issubclass(RelaxBackendError, RuntimeError)
    assert issubclass(ModelDownloadError, SLICESError)
    assert issubclass(ModelDownloadError, RuntimeError)
    assert not issubclass(ModelDownloadError, RelaxBackendError)
