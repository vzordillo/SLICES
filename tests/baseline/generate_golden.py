r"""Deterministic golden fixture generator for the SLICES v4.0.2 baseline corpus.

Generates compact reference snapshots (`fixtures/golden_metadata.json` and
`fixtures/golden_arrays.npz`) strictly from the untouched upstream SLICES v4.0.2 tree
(`/home/ordillo/tests/SLICES-upstream-baseline/src` at commit `94ef8e0`).

Usage:
    PYTHONHASHSEED=0 PYTHONPATH=/home/ordillo/tests/SLICES-upstream-baseline/src \\
        python tests/baseline/generate_golden.py
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import io
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

EXPECTED_UPSTREAM_COMMIT = "94ef8e079b69c37138159805e3c701b8df87a5d7"
DEFAULT_BASELINE_WORKTREE = Path("/home/ordillo/tests/SLICES-upstream-baseline")
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
METADATA_PATH = FIXTURES_DIR / "golden_metadata.json"
ARRAYS_PATH = FIXTURES_DIR / "golden_arrays.npz"

FOUR_STRUCTURES_IDS = frozenset({"G10", "G12"})

CORPUS_SPEC: tuple[dict[str, Any], ...] = (
    {
        "id": "G01",
        "kind": "cif_file",
        "source": "examples/NdSiRu.cif",
        "note": "Tetragonal P (P4/nmm, SG 129), Z=60 Nd, CIF oxidation states",
    },
    {
        "id": "G02",
        "kind": "cif_file",
        "source": "examples/Sr3Ru2O7.cif",
        "note": "Tetragonal I (I4/mmm, SG 139), 12-atom cell",
    },
    {
        "id": "G03",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 473,
        "mid": "mp-1219249",
        "note": "Triclinic P (P1, SG 1), Si3P3Ir, lattice_type=3",
    },
    {
        "id": "G04",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 930,
        "mid": "mp-1287184",
        "note": "Triclinic P (P-1, SG 2), VO, 8->4 conv-to-prim reduction",
    },
    {
        "id": "G05",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 59,
        "mid": "mp-1077904",
        "note": "Monoclinic C (C2/m, SG 12), CdPb2(ClO)2, heavy Pb Z=82 & preoptimize",
    },
    {
        "id": "G06",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 5,
        "mid": "mp-1002572",
        "note": "Orthorhombic P (P2_12_12, SG 18), LiMnO2, 16->8 conv-to-prim reduction",
    },
    {
        "id": "G07",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 154,
        "mid": "mp-606711",
        "note": "Orthorhombic A (Amm2, SG 38), Cs3LiCl4, A-centering",
    },
    {
        "id": "G08",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 146,
        "mid": "mp-548469",
        "note": "Orthorhombic C (Cmcm, SG 63), BaZnSO, C-centering",
    },
    {
        "id": "G09",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 119,
        "mid": "mp-571461",
        "note": "Trigonal R (R-3m, SG 166), K4ZnAs2, R-centering",
    },
    {
        "id": "G10",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 77,
        "mid": "mp-567510",
        "note": "Trigonal P (P-3m1, SG 164), BaSn2, 3-atom to_4structures target",
    },
    {
        "id": "G11",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 63,
        "mid": "mp-34127",
        "note": "Hexagonal P (P6_3/mmc, SG 194), K2NaAs",
    },
    {
        "id": "G12",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 233,
        "mid": "mp-1094088",
        "note": "Cubic F (F-43m, SG 216), NbCoSn, lattice_type=1 & to_4structures",
    },
    {
        "id": "G13",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 38,
        "mid": "mp-568005",
        "note": "Cubic P (Pm-3m, SG 221), CsYbBr3, lanthanide Yb Z=70",
    },
    {
        "id": "G14",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 1667,
        "mid": "mp-127",
        "note": "Cubic I (Im-3m, SG 229), Na 1-atom primitive cell (cocycle_rep is None)",
    },
    {
        "id": "G15",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 262,
        "mid": "mp-545728",
        "note": "Tetragonal P (P4/mmm, SG 123), PrBi2IO4, high-CN=20 (>19) & Bi Z=83",
    },
    {
        "id": "G16",
        "kind": "mp20_cif",
        "source": "data/mp20/test.csv",
        "row": 1,
        "mid": "mp-1218989",
        "note": "Actinide SmThCN (Th Z=90 >= 87): check_element=False + GFN-FF modern",
    },
    {
        "id": "G17",
        "kind": "slices_csv",
        "source": "data/mp20_nonmetal/test_data_reduce_zero.csv",
        "row": 1249,
        "note": "ZrTi(PbO3)2: natural preoptimize trigger (closest_pair_ratio=0.2715 < 0.5)",
    },
    {
        "id": "G18",
        "kind": "slices_csv",
        "source": "data/mp20_nonmetal/test_data_reduce_zero.csv",
        "row": 394,
        "note": "YHO2: triggers unstable_graph=True branch",
    },
    {
        "id": "G19",
        "kind": "slices_literal",
        "source": "src/slices/gfnff_helper.py:120",
        "slices": (
            "o x a DDO j OOO o Na Na Na Mn Co Ni O O O O O O 0 8 oo- 0 10 o-o "
            "0 10 -oo 0 6 o-- 0 6 -o- 0 11 ooo 1 6 ooo 1 11 +o+ 1 11 o++ 1 7 +oo "
            "1 7 o+o 1 9 +++ 2 7 ooo 2 9 +o+ 2 9 o++ 2 8 +oo 2 8 o+o 2 10 oo+ "
            "3 11 ooo 3 6 o-o 3 6 -oo 3 9 +oo 3 9 o+o 3 7 ooo 4 10 ooo 4 8 +oo "
            "4 8 o+o 4 11 +oo 4 11 o+o 4 6 ooo 5 9 ooo 5 7 o-o 5 7 -oo 5 10 o-o "
            "5 10 -oo 5 8 ooo"
        ),
        "note": "Na3MnCoNiO6: gfnff_helper self-test reference (Monoclinic C1m1, SG 8)",
    },
)

HIGH_CN_TOPOLOGY_SPEC: dict[str, Any] = {
    "id": "G15b",
    "source": "data/mp20_nonmetal/test_data_reduce_zero.csv",
    "row": 1205,
    "note": "Cs2LiCoC6N6 (16 atoms): 24->19 supercell neighbor cap in get_nbf_blist",
}

EDGE_SLICES_SPEC: tuple[dict[str, Any], ...] = (
    {"id": "E01_empty", "slices": "", "strategy": 4},
    {"id": "E02_no_elem", "slices": "foo bar baz", "strategy": 4},
    {"id": "E03_bad_sg_prefix", "slices": "q q q Si O 0 1 ooo", "strategy": 4},
    {"id": "E04_oob_node_idx", "slices": "Si O 0 5 ooo", "strategy": 4},
    {"id": "E05_bad_jimage_label", "slices": "Si O 0 1 oox", "strategy": 4},
    {"id": "E06_rank_h1_lt_3_1d", "slices": "Si O 0 1 ooo 0 1 +oo", "strategy": 4},
    {
        "id": "E07_rank_h1_lt_3_2d",
        "slices": "Si O 0 1 ooo 0 1 +oo 0 1 o+o",
        "strategy": 4,
    },
    {
        "id": "E08_unconnected_atom",
        "slices": "Si O C 0 1 ooo 0 1 +oo 0 1 o+o 0 1 oo+",
        "strategy": 4,
    },
    {
        "id": "E09_duplicate_flipped_edge",
        "slices": "Si O 0 1 ooo 1 0 ooo 0 1 +oo 0 1 o+o 0 1 oo+",
        "strategy": 4,
    },
    {
        "id": "E10_collinear_labels",
        "slices": "Si O 0 1 ooo 0 1 +oo 0 1 -oo 0 1 ++o",
        "strategy": 4,
    },
)

CORPUS_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in CORPUS_SPEC}


@functools.lru_cache(maxsize=2)
def load_mp20_subset(data_root: Path) -> pd.DataFrame:
    """Load the first 1,700 rows of `data/mp20/test.csv` needed by the golden corpus."""
    csv_path = data_root / "data" / "mp20" / "test.csv"
    return pd.read_csv(csv_path, nrows=1700, usecols=["material_id", "cif"])


@functools.lru_cache(maxsize=2)
def load_mp20_nonmetal_subset(data_root: Path) -> pd.DataFrame:
    """Load the first 1,300 rows of `data/mp20_nonmetal/test_data_reduce_zero.csv`."""
    csv_path = data_root / "data" / "mp20_nonmetal" / "test_data_reduce_zero.csv"
    return pd.read_csv(csv_path, nrows=1300, usecols=["SLICES"])


def sha256_text(text: str) -> str:
    """Compute hex SHA-256 digest of a UTF-8 string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def evaluate_constants_and_wyckoff() -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate frozen `config.py` constants and `utils_wyckoff.py` 1..230 bijections."""
    from slices import config, utils_wyckoff

    periodic_csv = config.PERIODIC_DATA.to_csv(index=False, lineterminator="\n")
    sg_json = json.dumps(utils_wyckoff.sg_encoding, sort_keys=True)
    tokenized_map: dict[str, str] = {}
    for sg_num in range(1, 231):
        tok = utils_wyckoff.get_tokenized_enc(sg_num)
        recovered = utils_wyckoff.get_space_group_num_from_letter_enc("".join(tok.split()))
        if recovered != sg_num:
            raise AssertionError(f"Wyckoff round-trip failed for SG {sg_num}: {recovered}")
        tokenized_map[str(sg_num)] = tok

    meta = {
        "periodic_data_rows": len(config.PERIODIC_DATA),
        "periodic_data_columns": list(config.PERIODIC_DATA.columns),
        "periodic_data_sha256": sha256_text(periodic_csv),
        "sg_encoding_count": len(utils_wyckoff.sg_encoding),
        "sg_encoding_sha256": sha256_text(sg_json),
        "wyckoff_tokenized_1_to_230": tokenized_map,
    }
    arrays = {
        "CONST__OFFSET": np.asarray(config.OFFSET, dtype=np.int64),
        "CONST__LJ_PARAMS_LIST": np.asarray(config.LJ_PARAMS_LIST, dtype=np.float64),
    }
    return meta, arrays


def evaluate_corpus_entry(
    cid: str,
    data_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate a single Golden Corpus entry (`G01`-`G19`) in an isolated `SLICES` instance.

    Args:
        cid: Corpus identifier (`"G01"` through `"G19"`).
        data_root: Repository root containing `examples/` and `data/`.

    Returns:
        Tuple `(metadata_dict, arrays_dict)` for `cid`.
    """
    from pymatgen.core import Structure
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    from slices.core import SLICES
    from slices.relax_backends import closest_pair_ratio

    spec = CORPUS_BY_ID[cid]
    backend = SLICES(relax_model="auto")
    no_relax = SLICES(relax_model=None)

    meta: dict[str, Any] = {"kind": spec["kind"], "note": spec["note"]}
    arrays: dict[str, np.ndarray] = {}
    ori: Structure | None = None

    if spec["kind"] in ("cif_file", "mp20_cif"):
        if spec["kind"] == "cif_file":
            cif_str = (data_root / spec["source"]).read_text(encoding="utf-8")
        else:
            df_mp = load_mp20_subset(data_root)
            row = df_mp.iloc[spec["row"]]
            if row["material_id"] != spec["mid"]:
                raise ValueError(
                    f"Corpus {cid} material_id mismatch: {row['material_id']} != {spec['mid']}"
                )
            cif_str = str(row["cif"])

        ori = Structure.from_str(cif_str, fmt="cif")
        prim = SLICES.to_primitive_if_smaller(ori)
        sga = SpacegroupAnalyzer(ori)

        meta["natoms_in"] = len(ori)
        meta["natoms_prim"] = len(prim)
        meta["sg_num_in"] = int(sga.get_space_group_number())
        meta["sg_sym_in"] = str(sga.get_space_group_symbol())
        meta["crystal_system"] = str(sga.get_crystal_system())
        meta["check_element"] = bool(SLICES.check_element(ori))
        meta["check_3D"] = bool(no_relax.check_3D(prim))
        meta["check_2D"] = bool(no_relax.check_2D(prim))
        meta["dim"] = int(no_relax.get_dim(prim))
        meta["structural_validity_prim"] = bool(SLICES.check_structural_validity(prim))

        cif_probe = SLICES(relax_model=None)
        cif_probe.from_cif(cif_str)
        meta["from_cif_sg_num"] = cif_probe.space_group_num
        arrays[f"{cid}__from_cif_atom_types"] = np.asarray(cif_probe.atom_types, dtype=np.int64)
        arrays[f"{cid}__from_cif_edge_indices"] = np.asarray(
            cif_probe.edge_indices, dtype=np.int64
        )
        arrays[f"{cid}__from_cif_to_jimages"] = np.asarray(cif_probe.to_jimages, dtype=np.int64)

        meta["slices_by_strategy"] = {
            str(st): no_relax.structure2SLICES(ori, strategy=st) for st in (1, 2, 3, 4)
        }
        sl_str = meta["slices_by_strategy"]["4"]

        random.seed(42)
        with contextlib.redirect_stdout(io.StringIO()):
            meta["random_slices_5"] = no_relax.structure2randomSLICES(ori, strategy=4, num=5)
    elif spec["kind"] == "slices_csv":
        df_nm = load_mp20_nonmetal_subset(data_root)
        sl_str = str(df_nm.iloc[spec["row"]]["SLICES"])
        meta["slices_by_strategy"] = {"4": sl_str}
    else:
        sl_str = str(spec["slices"])
        meta["slices_by_strategy"] = {"4": sl_str}

    meta["check_SLICES"] = {
        "default": bool(
            no_relax.check_SLICES(sl_str, strategy=4, dupli_check=False, graph_rank_check=True)
        ),
        "dupli_true": bool(
            no_relax.check_SLICES(sl_str, strategy=4, dupli_check=True, graph_rank_check=True)
        ),
        "rank_false": bool(
            no_relax.check_SLICES(sl_str, strategy=4, dupli_check=False, graph_rank_check=False)
        ),
        "basic": bool(no_relax.check_SLICES_basic(sl_str, strategy=4)),
    }
    meta["canonical_s4"] = no_relax.get_canonical_SLICES(sl_str, strategy=4)
    meta["formula"] = no_relax.SLICES2formula(sl_str)
    meta["sg_recreated"] = SLICES(relax_model=None).SLICES2space_group_number(sl_str, strategy=4)

    backend.from_SLICES(sl_str, strategy=4, fix_duplicate_edge=True)
    meta["parsed_sg_num"] = backend.space_group_num
    arrays[f"{cid}__atom_types"] = np.asarray(backend.atom_types, dtype=np.int64)
    arrays[f"{cid}__edge_indices"] = np.asarray(backend.edge_indices, dtype=np.int64)
    arrays[f"{cid}__to_jimages"] = np.asarray(backend.to_jimages, dtype=np.int64)

    nbf, blist = backend.get_nbf_blist()
    meta["nbf"] = nbf
    nbf_last_row = [int(x) for x in nbf.strip().splitlines()[-1].split()]
    meta["nbf_max_listed_cn"] = max(nbf_last_row)
    arrays[f"{cid}__blist"] = np.asarray(blist, dtype=np.int64)

    inner_p, col_inds, col_weights = backend.get_inner_p_target()
    meta["colattice_inds"] = col_inds
    arrays[f"{cid}__inner_p_target"] = np.asarray(inner_p, dtype=np.float64)
    arrays[f"{cid}__colattice_weights"] = np.asarray(col_weights, dtype=np.float64)

    np.random.seed(0)
    structs, energy_per_atom = backend.to_structures()
    meta["num_returned_structs"] = len(structs)
    meta["unstable_graph"] = bool(backend.unstable_graph)
    meta["energy_per_atom"] = float(energy_per_atom)
    meta["energy_per_atom_hex"] = float(energy_per_atom).hex()
    meta["opt_closest_pair_ratio"] = (
        float(closest_pair_ratio(structs[1])) if len(structs[1]) > 1 else None
    )

    arrays[f"{cid}__std_lattice"] = np.asarray(structs[0].lattice.matrix, dtype=np.float64)
    arrays[f"{cid}__std_frac"] = np.asarray(structs[0].frac_coords, dtype=np.float64)
    arrays[f"{cid}__opt_lattice"] = np.asarray(structs[1].lattice.matrix, dtype=np.float64)
    arrays[f"{cid}__opt_frac"] = np.asarray(structs[1].frac_coords, dtype=np.float64)
    arrays[f"{cid}__opt2_lattice"] = np.asarray(structs[2].lattice.matrix, dtype=np.float64)
    arrays[f"{cid}__opt2_frac"] = np.asarray(structs[2].frac_coords, dtype=np.float64)
    arrays[f"{cid}__energy_per_atom"] = np.asarray(energy_per_atom, dtype=np.float64)

    if ori is not None:
        meta["match_check_strict"] = list(backend.match_check(ori, structs[1], structs[0]))
        meta["match_check3_strict"] = list(
            backend.match_check3(ori, structs[2], structs[1], structs[0])
        )
        meta["match_check3_loose"] = list(
            backend.match_check3(
                ori, structs[2], structs[1], structs[0], ltol=0.3, stol=0.5, angle_tol=10
            )
        )

    if cid in FOUR_STRUCTURES_IDS and ori is not None:
        four_backend = SLICES(relax_model="auto")
        four_backend.from_SLICES(sl_str, strategy=4, fix_duplicate_edge=True)
        np.random.seed(0)
        structs4, energy4 = four_backend.to_4structures()
        meta["energy4_per_atom"] = float(energy4)
        meta["match_check4_strict"] = list(
            four_backend.match_check4(ori, structs4[3], structs4[2], structs4[1], structs4[0])
        )
        arrays[f"{cid}__std2_lattice"] = np.asarray(structs4[1].lattice.matrix, dtype=np.float64)
        arrays[f"{cid}__std2_frac"] = np.asarray(structs4[1].frac_coords, dtype=np.float64)

    return meta, arrays


def evaluate_high_cn_topology(
    data_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate 24-neighbor `G15b` (`Cs2LiCoC6N6`) topology & GFN-FF targets."""
    from slices.core import SLICES

    df_nm = load_mp20_nonmetal_subset(data_root)
    sl_str = str(df_nm.iloc[HIGH_CN_TOPOLOGY_SPEC["row"]]["SLICES"])
    probe = SLICES(relax_model=None)
    probe.from_SLICES(sl_str, strategy=4, fix_duplicate_edge=True)
    nbf, blist = probe.get_nbf_blist()
    inner_p, col_inds, col_weights = probe.get_inner_p_target()
    nbf_last_row = [int(x) for x in nbf.strip().splitlines()[-1].split()]
    meta = {
        "note": HIGH_CN_TOPOLOGY_SPEC["note"],
        "slices": sl_str,
        "nbf": nbf,
        "nbf_max_listed_cn": max(nbf_last_row),
        "colattice_inds": col_inds,
    }
    arrays = {
        "G15b__blist": np.asarray(blist, dtype=np.int64),
        "G15b__inner_p_target": np.asarray(inner_p, dtype=np.float64),
        "G15b__colattice_weights": np.asarray(col_weights, dtype=np.float64),
    }
    return meta, arrays


def evaluate_synthetic_and_edges(
    data_root: Path = REPO_ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, np.ndarray]]:
    """Evaluate `S01` (`preoptimize`), `S03` (`check_element`), and `E01`-`E11` edge cases."""
    from pymatgen.core import Lattice, Structure

    from slices.core import SLICES
    from slices.relax_backends import preoptimize

    backend = SLICES(relax_model="auto")
    no_relax = SLICES(relax_model=None)

    s_syn = Structure(Lattice.cubic(3.6), ["Na", "Cl"], [[0.0, 0.0, 0.0], [0.12, 0.12, 0.12]])
    s_pre, pre_info = preoptimize(s_syn)
    syn_res = backend.relaxer.relax(s_syn, fmax=0.2, steps=100)

    s_rn = Structure(Lattice.cubic(4.5), ["Rn"], [[0.0, 0.0, 0.0]])
    s_fr = Structure(Lattice.cubic(4.5), ["Fr"], [[0.0, 0.0, 0.0]])
    s_mix = Structure(Lattice.cubic(4.5), ["Si", "Fr"], [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]])

    synthetic_meta = {
        "S01_overlap_preopt": {
            "applied": bool(pre_info["applied"]),
            "ratio_before": float(pre_info["ratio_before"]),
            "ratio_after": float(pre_info["ratio"]),
            "relax_preoptimized": bool(syn_res["preoptimized"]),
            "relax_retry": int(syn_res["retry"]),
            "relax_steps": int(syn_res["steps"]),
            "final_energy_total": float(syn_res["trajectory"].energies[-1]),
        },
        "S03_element_boundary": {
            "Rn_Z86": bool(SLICES.check_element(s_rn)),
            "Fr_Z87": bool(SLICES.check_element(s_fr)),
            "Si_Fr_mixed": bool(SLICES.check_element(s_mix)),
        },
    }
    arrays = {
        "S01__pre_lattice": np.asarray(s_pre.lattice.matrix, dtype=np.float64),
        "S01__pre_frac": np.asarray(s_pre.frac_coords, dtype=np.float64),
        "S01__final_lattice": np.asarray(
            syn_res["final_structure"].lattice.matrix, dtype=np.float64
        ),
        "S01__final_frac": np.asarray(
            syn_res["final_structure"].frac_coords, dtype=np.float64
        ),
        "S01__scalars": np.asarray(
            [
                pre_info["ratio_before"],
                pre_info["ratio"],
                syn_res["trajectory"].energies[-1],
            ],
            dtype=np.float64,
        ),
    }

    edges_meta: dict[str, Any] = {}
    for edge_item in EDGE_SLICES_SPEC:
        eid = edge_item["id"]
        sl = edge_item["slices"]
        st = edge_item["strategy"]
        rec: dict[str, Any] = {
            "slices": sl,
            "strategy": st,
            "check_default": bool(
                no_relax.check_SLICES(sl, strategy=st, dupli_check=False, graph_rank_check=True)
            ),
            "check_dupli": bool(
                no_relax.check_SLICES(sl, strategy=st, dupli_check=True, graph_rank_check=True)
            ),
            "check_norank": bool(
                no_relax.check_SLICES(sl, strategy=st, dupli_check=False, graph_rank_check=False)
            ),
            "check_basic": bool(no_relax.check_SLICES_basic(sl, strategy=st)),
        }
        try:
            SLICES(relax_model=None).from_SLICES(sl, strategy=st, fix_duplicate_edge=False)
            rec["from_slices_nofix"] = "ok"
        except Exception as exc:  # noqa: BLE001
            rec["from_slices_nofix"] = f"{type(exc).__name__}: {exc}"
        edges_meta[eid] = rec

    df_mp = load_mp20_subset(data_root)
    tibr3 = Structure.from_str(str(df_mp.iloc[464]["cif"]), fmt="cif")
    sl_tibr3 = no_relax.structure2SLICES(tibr3, strategy=4)
    with contextlib.redirect_stdout(io.StringIO()):
        sg_tibr3 = SLICES(relax_model=None).SLICES2space_group_number(sl_tibr3, strategy=4)
    edges_meta["E11_quasi1d_lattice_basis_neg1"] = {
        "slices": sl_tibr3,
        "strategy": 4,
        "check_3D": bool(no_relax.check_3D(tibr3)),
        "check_default": bool(no_relax.check_SLICES(sl_tibr3, strategy=4)),
        "check_dupli": bool(no_relax.check_SLICES(sl_tibr3, strategy=4, dupli_check=True)),
        "check_basic": bool(no_relax.check_SLICES_basic(sl_tibr3, strategy=4)),
        "sg_recreated": sg_tibr3,
    }
    return synthetic_meta, edges_meta, arrays


def _verify_baseline_worktree(baseline_worktree: Path) -> tuple[str, str]:
    """Verify the baseline git worktree is clean and checked out at `94ef8e0`."""
    commit = subprocess.check_output(
        ["git", "-C", str(baseline_worktree), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if commit != EXPECTED_UPSTREAM_COMMIT:
        raise RuntimeError(
            f"Baseline worktree commit mismatch: {commit} != {EXPECTED_UPSTREAM_COMMIT}"
        )
    status = subprocess.check_output(
        ["git", "-C", str(baseline_worktree), "status", "--porcelain"],
        text=True,
    ).strip()
    if status:
        raise RuntimeError(f"Baseline worktree is not clean:\n{status}")
    tree = subprocess.check_output(
        ["git", "-C", str(baseline_worktree), "rev-parse", "HEAD^{tree}"],
        text=True,
    ).strip()
    return commit, tree


def _collect_package_versions() -> dict[str, str]:
    """Collect exact versions of core scientific and MLIP packages."""
    import importlib.metadata

    pkgs = ("torch", "nequip", "pymatgen", "ase", "scipy", "numpy", "spglib", "networkx")
    return {pkg: importlib.metadata.version(pkg) for pkg in pkgs}


def generate_all_fixtures(baseline_worktree: Path) -> None:
    """Generate `golden_metadata.json` and `golden_arrays.npz` from `baseline_worktree`."""
    import slices.core

    expected_src = (baseline_worktree / "src" / "slices").resolve()
    actual_src = Path(slices.core.__file__).resolve().parent
    if actual_src != expected_src:
        raise RuntimeError(
            f"slices imported from {actual_src}, expected baseline {expected_src}"
        )
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("PYTHONHASHSEED=0 is required when generating golden fixtures.")

    commit, tree = _verify_baseline_worktree(baseline_worktree)
    t0 = time.perf_counter()

    const_meta, all_arrays = evaluate_constants_and_wyckoff()
    corpus_meta: dict[str, Any] = {}
    for spec in CORPUS_SPEC:
        cid = spec["id"]
        t_item = time.perf_counter()
        c_meta, c_arrays = evaluate_corpus_entry(cid, data_root=baseline_worktree)
        corpus_meta[cid] = c_meta
        all_arrays.update(c_arrays)
        elapsed = time.perf_counter() - t_item
        print(
            f"  [golden] {cid}: natoms={len(c_arrays[f'{cid}__atom_types']):2d}, "
            f"E={c_meta['energy_per_atom']:10.6f} eV/atom ({elapsed:.2f}s)",
            flush=True,
        )

    g15b_meta, g15b_arrays = evaluate_high_cn_topology(data_root=baseline_worktree)
    all_arrays.update(g15b_arrays)

    syn_meta, edges_meta, syn_arrays = evaluate_synthetic_and_edges(data_root=baseline_worktree)
    all_arrays.update(syn_arrays)

    total_elapsed = round(time.perf_counter() - t0, 3)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    metadata = {
        "schema_version": "1.0.0",
        "upstream_baseline": {
            "worktree": str(baseline_worktree),
            "git_commit": commit,
            "git_tree": tree,
            "python": sys.version.split()[0],
            "packages": _collect_package_versions(),
            "env": {
                "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED", ""),
                "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
            },
            "generation_wall_clock_s": total_elapsed,
        },
        "constants": const_meta,
        "corpus": corpus_meta,
        "high_cn_topology": {"G15b": g15b_meta},
        "synthetic": syn_meta,
        "edges": edges_meta,
    }

    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(ARRAYS_PATH, **all_arrays)

    meta_kb = METADATA_PATH.stat().st_size / 1024.0
    npz_kb = ARRAYS_PATH.stat().st_size / 1024.0
    print(
        f"[golden] Generated fixtures in {total_elapsed:.2f}s: "
        f"{METADATA_PATH.name}={meta_kb:.1f} KiB, {ARRAYS_PATH.name}={npz_kb:.1f} KiB "
        f"(total={meta_kb + npz_kb:.1f} KiB)",
        flush=True,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for generating golden baseline fixtures."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--baseline-worktree",
        type=Path,
        default=DEFAULT_BASELINE_WORKTREE,
        help="Path to immutable SLICES-upstream-baseline worktree.",
    )
    args = parser.parse_args(argv)
    baseline_worktree = args.baseline_worktree.resolve()
    baseline_src = str(baseline_worktree / "src")

    if os.environ.get("PYTHONHASHSEED") != "0" or os.environ.get("OMP_NUM_THREADS") != "1":
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        env["OMP_NUM_THREADS"] = "1"
        env["SLICES_TORCH_THREADS"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = baseline_src
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--baseline-worktree",
            str(baseline_worktree),
        ]
        return subprocess.run(cmd, env=env, check=False).returncode

    if sys.path[0] != baseline_src:
        sys.path.insert(0, baseline_src)

    generate_all_fixtures(baseline_worktree)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
