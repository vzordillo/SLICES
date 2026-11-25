r"""Golden baseline equivalence tests against upstream SLICES v4.0.2 (`94ef8e0`).

Asserts exact discrete equality (`==`) and tight CPU numerical invariance
(`rtol=0.0, atol=1e-12`) across all 19 stratified corpus structures (`G01`-`G19`),
24-neighbor supercell topology (`G15b`), synthetic `preoptimize` & element-boundary
fixtures (`S01`, `S03`), 11 invalid/edge-case SLICES strings (`E01`-`E11`), frozen
`config.py` constants, and all 230 `utils_wyckoff.py` space-group encodings.

Run against either tree:
    PYTHONHASHSEED=0 PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src \\
        pytest tests/baseline/test_golden_equivalence.py
    PYTHONHASHSEED=0 PYTHONPATH=/home/ordillo/tests/SLICES/src \\
        pytest tests/baseline/test_golden_equivalence.py
"""

from __future__ import annotations

import functools
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ATOL_CPU = 1e-12
ATOL_DEF014_ENERGY = 1e-5
ATOL_DEF014_OPT2_LAT = 1e-4
ATOL_DEF014_FRAC = 5e-4
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
UPSTREAM_BASELINE_SRC = Path("/home/ordillo/tests/SLICES-upstream-baseline/src")

# Corpus entries whose symmetry-constrained ZL* lattice_type is restored from IEEE-754
# float noise under DEF-014 (`math.isclose(rel_tol=1e-9, abs_tol=1e-12)`).
# G03, G06, G12, G14, and G18 remain bit-identical (`atol=1e-12`) across all arrays.
DEF014_SYMMETRY_RESTORED_IDS: frozenset[str] = frozenset(
    {
        "G01",
        "G02",
        "G04",
        "G05",
        "G07",
        "G08",
        "G09",
        "G10",
        "G11",
        "G13",
        "G15",
        "G16",
        "G17",
        "G19",
    }
)


@functools.lru_cache(maxsize=1)
def _load_generator_module() -> Any:
    """Load `generate_golden.py` robustly regardless of `sys.path` / pytest import mode."""
    module_path = HERE / "generate_golden.py"
    spec = importlib.util.spec_from_file_location("slices_baseline_generate_golden", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load generator module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GEN = _load_generator_module()
CORPUS_IDS: tuple[str, ...] = tuple(item["id"] for item in GEN.CORPUS_SPEC)
CIF_CORPUS_IDS: tuple[str, ...] = tuple(
    item["id"] for item in GEN.CORPUS_SPEC if item["kind"] in ("cif_file", "mp20_cif")
)
EDGE_IDS: tuple[str, ...] = (
    *(item["id"] for item in GEN.EDGE_SLICES_SPEC),
    "E11_quasi1d_lattice_basis_neg1",
)
DUAL_TREE_SUBSET_IDS: tuple[str, ...] = ("G01", "G06", "G14", "G15", "G16", "G17", "G18")


@functools.lru_cache(maxsize=1)
def golden_metadata() -> dict[str, Any]:
    """Load golden discrete metadata JSON fixture."""
    if not GEN.METADATA_PATH.is_file():
        pytest.fail(f"Missing golden metadata fixture: {GEN.METADATA_PATH}")
    return json.loads(GEN.METADATA_PATH.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def golden_arrays() -> dict[str, np.ndarray]:
    """Load golden IEEE-754 numpy arrays from `golden_arrays.npz`."""
    if not GEN.ARRAYS_PATH.is_file():
        pytest.fail(f"Missing golden array fixture: {GEN.ARRAYS_PATH}")
    with np.load(GEN.ARRAYS_PATH, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


@functools.cache
def evaluated_entry(cid: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate and cache a single corpus entry (`G01`-`G19`) for the active `PYTHONPATH`."""
    return GEN.evaluate_corpus_entry(cid, data_root=REPO_ROOT)


@functools.lru_cache(maxsize=1)
def evaluated_synthetic_and_edges() -> tuple[dict[str, Any], dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate and cache `S01`, `S03`, and `E01`-`E11` once per test session."""
    return GEN.evaluate_synthetic_and_edges(data_root=REPO_ROOT)


def test_fixture_provenance_and_footprint() -> None:
    """Verify fixture provenance against `94ef8e0` and enforce `< 500 KB` size budget."""
    meta = golden_metadata()
    assert meta["schema_version"] == "1.0.0"
    assert meta["upstream_baseline"]["git_commit"] == GEN.EXPECTED_UPSTREAM_COMMIT
    total_bytes = GEN.METADATA_PATH.stat().st_size + GEN.ARRAYS_PATH.stat().st_size
    assert total_bytes < 500 * 1024, f"Golden fixtures exceed 500 KiB: {total_bytes} B"


def test_frozen_config_constants_and_wyckoff_bijection() -> None:
    """Verify bit-exact `config.py` tables and all 230 `utils_wyckoff.py` bijections."""
    from pymatgen.core.periodic_table import Element

    expected_const = golden_metadata()["constants"]
    expected_arrays = golden_arrays()
    actual_const, actual_arrays = GEN.evaluate_constants_and_wyckoff()

    assert actual_const == expected_const
    assert np.array_equal(actual_arrays["CONST__OFFSET"], expected_arrays["CONST__OFFSET"])
    assert tuple(actual_arrays["CONST__OFFSET"][13]) == (0, 0, 0)
    np.testing.assert_allclose(
        actual_arrays["CONST__LJ_PARAMS_LIST"],
        expected_arrays["CONST__LJ_PARAMS_LIST"],
        rtol=0.0,
        atol=0.0,
    )

    for sg_str, tok_str in actual_const["wyckoff_tokenized_1_to_230"].items():
        for token in tok_str.split():
            with pytest.raises(ValueError):
                Element(token)
        assert int(sg_str) in range(1, 231)


@pytest.mark.parametrize("cid", CORPUS_IDS)
def test_discrete_encoding_parsing_and_canonical_invariance(cid: str) -> None:
    """Assert exact (`==` / `np.array_equal`) parity on encoding, parsing, and validation."""
    expected = golden_metadata()["corpus"][cid]
    exp_arr = golden_arrays()
    actual, act_arr = evaluated_entry(cid)

    exact_fields = (
        "kind",
        "natoms_in",
        "natoms_prim",
        "sg_num_in",
        "sg_sym_in",
        "crystal_system",
        "check_element",
        "check_3D",
        "check_2D",
        "dim",
        "structural_validity_prim",
        "from_cif_sg_num",
        "slices_by_strategy",
        "check_SLICES",
        "canonical_s4",
        "formula",
        "sg_recreated",
        "parsed_sg_num",
        "nbf",
        "nbf_max_listed_cn",
        "colattice_inds",
        "num_returned_structs",
        "unstable_graph",
    )
    for key in exact_fields:
        if key in expected:
            assert actual[key] == expected[key], f"{cid} mismatch on {key}"

    if "random_slices_5" in expected:
        if os.environ.get("PYTHONHASHSEED") == "0":
            assert actual["random_slices_5"] == expected["random_slices_5"]
        else:
            assert set(actual["random_slices_5"]) == set(expected["random_slices_5"])

    for suffix in ("atom_types", "edge_indices", "to_jimages", "blist"):
        arr_key = f"{cid}__{suffix}"
        assert np.array_equal(act_arr[arr_key], exp_arr[arr_key]), f"{cid} mismatch on {suffix}"

    if f"{cid}__from_cif_atom_types" in exp_arr:
        for suffix in ("from_cif_atom_types", "from_cif_edge_indices", "from_cif_to_jimages"):
            arr_key = f"{cid}__{suffix}"
            assert np.array_equal(act_arr[arr_key], exp_arr[arr_key])


@pytest.mark.parametrize("cid", CORPUS_IDS)
def test_gfnff_inner_product_targets_invariance(cid: str) -> None:
    """Assert `atol=1e-12` CPU parity on `get_inner_p_target` matrices and weights."""
    exp_arr = golden_arrays()
    _, act_arr = evaluated_entry(cid)

    np.testing.assert_allclose(
        act_arr[f"{cid}__inner_p_target"],
        exp_arr[f"{cid}__inner_p_target"],
        rtol=0.0,
        atol=ATOL_CPU,
    )
    np.testing.assert_allclose(
        act_arr[f"{cid}__colattice_weights"],
        exp_arr[f"{cid}__colattice_weights"],
        rtol=0.0,
        atol=ATOL_CPU,
    )


@pytest.mark.parametrize("cid", CORPUS_IDS)
def test_zlstar_and_nequip_decoded_structures_invariance(cid: str) -> None:
    """Assert strict `atol=1e-12` parity (and bounded DEF-014 symmetry-restored tolerances)."""
    expected = golden_metadata()["corpus"][cid]
    exp_arr = golden_arrays()
    actual, act_arr = evaluated_entry(cid)
    is_def014 = cid in DEF014_SYMMETRY_RESTORED_IDS

    for suffix in ("std_lattice", "std_frac", "opt_lattice"):
        arr_key = f"{cid}__{suffix}"
        np.testing.assert_allclose(
            act_arr[arr_key],
            exp_arr[arr_key],
            rtol=0.0,
            atol=ATOL_CPU,
            err_msg=f"{cid} numerical drift in {suffix}",
        )

    tol_by_suffix = {
        "opt_frac": ATOL_DEF014_FRAC if is_def014 else ATOL_CPU,
        "opt2_lattice": ATOL_DEF014_OPT2_LAT if is_def014 else ATOL_CPU,
        "opt2_frac": ATOL_DEF014_FRAC if is_def014 else ATOL_CPU,
        "energy_per_atom": ATOL_DEF014_ENERGY if is_def014 else ATOL_CPU,
    }
    for suffix, atol in tol_by_suffix.items():
        arr_key = f"{cid}__{suffix}"
        np.testing.assert_allclose(
            act_arr[arr_key],
            exp_arr[arr_key],
            rtol=0.0,
            atol=atol,
            err_msg=f"{cid} numerical drift in {suffix}",
        )

    if expected["opt_closest_pair_ratio"] is None:
        assert actual["opt_closest_pair_ratio"] is None
    else:
        cpr_tol = ATOL_DEF014_FRAC if is_def014 else ATOL_CPU
        assert actual["opt_closest_pair_ratio"] == pytest.approx(
            expected["opt_closest_pair_ratio"], rel=0.0, abs=cpr_tol
        )

    if cid in GEN.FOUR_STRUCTURES_IDS:
        assert actual["energy4_per_atom"] == pytest.approx(
            expected["energy4_per_atom"], rel=0.0, abs=ATOL_CPU
        )
        for suffix in ("std2_lattice", "std2_frac"):
            arr_key = f"{cid}__{suffix}"
            np.testing.assert_allclose(
                act_arr[arr_key], exp_arr[arr_key], rtol=0.0, atol=ATOL_CPU
            )
        assert actual["match_check4_strict"][:4] == expected["match_check4_strict"][:4]
        np.testing.assert_allclose(
            [float(x) for x in actual["match_check4_strict"][4:]],
            [float(x) for x in expected["match_check4_strict"][4:]],
            rtol=0.0,
            atol=ATOL_CPU,
        )


@pytest.mark.parametrize("cid", CIF_CORPUS_IDS)
def test_structure_matching_and_oxidation_state_handling(cid: str) -> None:
    """Verify `match_check` / `match_check3` and `ElementComparator` oxidation-state behavior."""
    expected = golden_metadata()["corpus"][cid]
    actual, act_arr = evaluated_entry(cid)

    assert actual["match_check_strict"][:2] == expected["match_check_strict"][:2]
    np.testing.assert_allclose(
        [float(x) for x in actual["match_check_strict"][2:]],
        [float(x) for x in expected["match_check_strict"][2:]],
        rtol=0.0,
        atol=ATOL_CPU,
    )

    for field in ("match_check3_strict", "match_check3_loose"):
        assert actual[field][:3] == expected[field][:3]
        np.testing.assert_allclose(
            [float(x) for x in actual[field][3:]],
            [float(x) for x in expected[field][3:]],
            rtol=0.0,
            atol=ATOL_CPU,
        )

    if cid == "G01":
        from pymatgen.analysis.structure_matcher import (
            ElementComparator,
            StructureMatcher,
        )
        from pymatgen.core import Lattice, Structure
        from pymatgen.core.periodic_table import Element

        ori = Structure.from_file(str(REPO_ROOT / "examples" / "NdSiRu.cif"))
        atom_symbols = [Element.from_Z(int(z)).symbol for z in act_arr["G01__atom_types"]]
        opt2 = Structure(
            Lattice(act_arr["G01__opt2_lattice"]),
            atom_symbols,
            act_arr["G01__opt2_frac"],
        )
        # Raw StructureMatcher uses SpeciesComparator, so Nd2+/Si4-/Ru2+ != neutral Nd/Si/Ru.
        assert bool(StructureMatcher().fit(ori, opt2)) is False
        sm_elem = StructureMatcher(
            ltol=0.2,
            stol=0.3,
            angle_tol=5,
            primitive_cell=True,
            scale=True,
            attempt_supercell=False,
            comparator=ElementComparator(),
        )
        assert bool(sm_elem.fit(ori, opt2)) is True


def test_high_coordination_24_to_19_cap_invariance() -> None:
    """Verify `G15b` (`Cs2LiCoC6N6`, 24 neighbors -> 19 cap) in `get_nbf_blist`."""
    expected = golden_metadata()["high_cn_topology"]["G15b"]
    exp_arr = golden_arrays()
    actual, act_arr = GEN.evaluate_high_cn_topology(data_root=REPO_ROOT)

    assert actual["nbf_max_listed_cn"] == 19
    assert actual == expected
    assert np.array_equal(act_arr["G15b__blist"], exp_arr["G15b__blist"])
    np.testing.assert_allclose(
        act_arr["G15b__inner_p_target"],
        exp_arr["G15b__inner_p_target"],
        rtol=0.0,
        atol=ATOL_CPU,
    )
    np.testing.assert_allclose(
        act_arr["G15b__colattice_weights"],
        exp_arr["G15b__colattice_weights"],
        rtol=0.0,
        atol=ATOL_CPU,
    )


def test_synthetic_preoptimize_and_element_boundaries() -> None:
    """Verify `S01` (`preoptimize` + NequIP relax) and `S03` (`Rn` Z=86 vs `Fr` Z=87)."""
    expected_syn = golden_metadata()["synthetic"]
    exp_arr = golden_arrays()
    actual_syn, _, act_arr = evaluated_synthetic_and_edges()

    assert actual_syn["S03_element_boundary"] == {
        "Rn_Z86": True,
        "Fr_Z87": False,
        "Si_Fr_mixed": False,
    }
    assert actual_syn["S03_element_boundary"] == expected_syn["S03_element_boundary"]

    act_s01 = actual_syn["S01_overlap_preopt"]
    exp_s01 = expected_syn["S01_overlap_preopt"]
    assert act_s01["applied"] is True
    assert act_s01["relax_preoptimized"] is True
    assert act_s01["relax_retry"] == exp_s01["relax_retry"]
    assert act_s01["relax_steps"] == exp_s01["relax_steps"]

    for suffix in ("pre_lattice", "pre_frac", "final_lattice", "final_frac", "scalars"):
        arr_key = f"S01__{suffix}"
        np.testing.assert_allclose(
            act_arr[arr_key], exp_arr[arr_key], rtol=0.0, atol=ATOL_CPU
        )


@pytest.mark.parametrize("eid", EDGE_IDS)
def test_invalid_and_edge_case_slices_strings(eid: str) -> None:
    """Verify exact behavior on invalid, rank-deficient, duplicate, and quasi-1D strings."""
    expected = dict(golden_metadata()["edges"][eid])
    _, actual_edges, _ = evaluated_synthetic_and_edges()
    if eid == "E11_quasi1d_lattice_basis_neg1":
        # DEF-021 (v4.1): check_SLICES(..., graph_rank_check=True) rejects quasi-1D TiBr3
        # whose cycle basis lacks a 3D unimodular lattice basis, while preserving all other fields.
        assert expected["check_default"] is True
        assert expected["check_dupli"] is True
        expected["check_default"] = False
        expected["check_dupli"] = False
    assert actual_edges[eid] == expected


def test_live_dual_tree_subprocess_parity(tmp_path: Path) -> None:
    """Compare live subprocess execution against `SLICES-upstream-baseline/src` directly."""
    if not UPSTREAM_BASELINE_SRC.is_dir():
        pytest.skip(f"Upstream baseline worktree not present at {UPSTREAM_BASELINE_SRC}")

    candidate_src = REPO_ROOT / "src"
    gen_path_str = str(HERE / "generate_golden.py")
    probe_code = (
        "import importlib.util, json, os, sys\n"
        "from pathlib import Path\n"
        "import slices.core\n"
        "expected_src = Path(sys.argv[1]).resolve()\n"
        "actual_file = Path(slices.core.__file__).resolve()\n"
        "assert str(actual_file).startswith(str(expected_src)), (actual_file, expected_src)\n"
        f"spec = importlib.util.spec_from_file_location('gen', {gen_path_str!r})\n"
        "gen = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(gen)\n"
        "out = {'entries': {}, 'arrays': {}}\n"
        f"for cid in {list(DUAL_TREE_SUBSET_IDS)!r}:\n"
        f"    m, a = gen.evaluate_corpus_entry(cid, data_root=Path({str(REPO_ROOT)!r}))\n"
        "    out['entries'][cid] = m\n"
        "    out['arrays'].update({k: v.tolist() for k, v in a.items()})\n"
        "Path(sys.argv[2]).write_text(json.dumps(out), encoding='utf-8')\n"
    )

    def _run_tree(src_dir: Path, out_file: Path) -> dict[str, Any]:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        env["OMP_NUM_THREADS"] = "1"
        env["SLICES_TORCH_THREADS"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(src_dir)
        subprocess.run(
            [sys.executable, "-c", probe_code, str(src_dir), str(out_file)],
            env=env,
            check=True,
        )
        return json.loads(out_file.read_text(encoding="utf-8"))

    ref_data = _run_tree(UPSTREAM_BASELINE_SRC, tmp_path / "upstream_ref.json")
    cand_data = _run_tree(candidate_src, tmp_path / "candidate.json")

    for cid in DUAL_TREE_SUBSET_IDS:
        ref_entry = dict(ref_data["entries"][cid])
        cand_entry = dict(cand_data["entries"][cid])
        for float_key in ("energy_per_atom", "energy_per_atom_hex", "opt_closest_pair_ratio"):
            ref_entry.pop(float_key, None)
            cand_entry.pop(float_key, None)
        assert cand_entry == ref_entry, f"Dual-tree discrete mismatch on {cid}"

    for arr_key, ref_list in ref_data["arrays"].items():
        cid, suffix = arr_key.split("__", 1)
        is_def014 = cid in DEF014_SYMMETRY_RESTORED_IDS
        if is_def014 and suffix in ("opt_frac", "opt2_frac"):
            atol = ATOL_DEF014_FRAC
        elif is_def014 and suffix == "opt2_lattice":
            atol = ATOL_DEF014_OPT2_LAT
        elif is_def014 and suffix == "energy_per_atom":
            atol = ATOL_DEF014_ENERGY
        else:
            atol = ATOL_CPU
        np.testing.assert_allclose(
            np.asarray(cand_data["arrays"][arr_key]),
            np.asarray(ref_list),
            rtol=0.0,
            atol=atol,
            err_msg=f"Dual-tree numerical drift on {arr_key}",
        )
