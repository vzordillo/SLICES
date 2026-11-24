"""Unit tests for SLICES decoding, unrelaxed short-circuiting, timeouts, and match checks."""

from __future__ import annotations

import signal
import threading
import time
from typing import Any

import numpy as np
import pytest
from pymatgen.core.lattice import Lattice
from pymatgen.core.structure import Structure

from slices.core import SLICES, function_timeout
from slices.exceptions import SLICESError, TimeoutException


@pytest.mark.unit
@pytest.mark.parametrize("strategy", [1, 3, 4])
def test_from_slices_parses_decodable_strategies(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
    strategy: int,
) -> None:
    """Parse Strategy 1, 3, and 4 SLICES strings and verify graph array recovery."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=strategy)
    parser = SLICES(relax_model=None)
    parser.from_SLICES(sli, strategy=strategy, fix_duplicate_edge=False)

    assert parser.atom_types is not None and len(parser.atom_types) == 6
    assert parser.edge_indices is not None and parser.edge_indices.shape[1] == 2
    assert parser.to_jimages is not None and parser.to_jimages.shape[1] == 3
    if strategy == 4:
        assert parser.space_group_num == 129
    else:
        assert parser.space_group_num is None


@pytest.mark.unit
def test_from_slices_fix_duplicate_edge_behavior() -> None:
    """Verify fix_duplicate_edge deduplicates flipped periodic edges when enabled."""
    dup_sli = "Si O 0 1 +oo 1 0 -oo 0 1 o+o 0 1 oo+"

    dedup = SLICES(relax_model=None)
    dedup.from_SLICES(dup_sli, strategy=4, fix_duplicate_edge=True)
    assert dedup.edge_indices is not None
    assert len(dedup.edge_indices) == 3

    raw = SLICES(relax_model=None)
    raw.from_SLICES(dup_sli, strategy=4, fix_duplicate_edge=False)
    assert raw.edge_indices is not None
    assert len(raw.edge_indices) == 4


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_slices",
    [
        "",
        "foo bar baz",
        "q q q Si O 0 1 ooo",
        "Si O 0 5 ooo",
        "Si O 0 1 oox",
    ],
)
def test_from_slices_rejects_malformed_inputs(
    slices_no_relax: SLICES,
    bad_slices: str,
) -> None:
    """Verify malformed Strategy 4 inputs raise an exception during parsing."""
    with pytest.raises(Exception):  # noqa: B017
        slices_no_relax.from_SLICES(bad_slices, strategy=4)


@pytest.mark.unit
def test_get_nbf_blist_and_inner_p_target(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify GFN-FF supercell topology and inner-product target matrix generation."""
    sli = slices_no_relax.structure2SLICES(ndsiru_structure, strategy=4)
    slices_no_relax.from_SLICES(sli, strategy=4)

    nbf, blist = slices_no_relax.get_nbf_blist()
    lines = nbf.strip().splitlines()
    assert len(lines) == 22
    assert blist.ndim == 2 and blist.shape[1] == 2

    inner_p_target, colattice_inds, colattice_weights = slices_no_relax.get_inner_p_target()
    num_edges = len(slices_no_relax.edge_indices)  # type: ignore[arg-type]
    assert inner_p_target.shape == (num_edges, num_edges)
    assert np.all(np.diag(inner_p_target) > 0.0)
    assert len(colattice_inds) == 2
    assert len(colattice_inds[0]) == len(colattice_weights)


@pytest.mark.unit
@pytest.mark.parametrize("relax_model", [None, "none"])
def test_def013_no_relax_short_circuit_zero_stdout(
    ndsiru_structure: Structure,
    capsys: pytest.CaptureFixture[str],
    relax_model: str | None,
) -> None:
    """Verify relax_model=None/'none' returns ([std, opt], 0) with zero stdout noise."""
    backend = SLICES(relax_model=relax_model)
    assert backend.relaxer is None
    assert backend.relax_model == "none"

    sli = backend.structure2SLICES(ndsiru_structure, strategy=4)
    backend.from_SLICES(sli, strategy=4)
    capsys.readouterr()

    structures, energy = backend.to_structures()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert len(structures) == 2
    assert energy == 0

    structures4, energy4 = backend.to_4structures()
    captured4 = capsys.readouterr()
    assert captured4.out == ""
    assert len(structures4) == 2
    assert energy4 == 0

    with pytest.raises(Exception, match="relax failed"):
        backend.to_relaxed_structure()


@pytest.mark.unit
def test_nequip_to_structures_4structures_and_slices2structure(
    slices_nequip: SLICES,
) -> None:
    """Verify to_structures, to_4structures, to_relaxed_structure, and SLICES2structure."""
    bcc_na = Structure(
        Lattice.cubic(4.23),
        ["Na", "Na"],
        [[0.0, 0.0, 0.0], [0.5, 0.5, 0.5]],
    )
    sli = slices_nequip.structure2SLICES(bcc_na, strategy=4)
    slices_nequip.from_SLICES(sli, strategy=4)

    structures, energy = slices_nequip.to_structures()
    assert len(structures) == 3
    assert np.isfinite(energy) and energy < 0.0

    structures4, energy4 = slices_nequip.to_4structures()
    assert len(structures4) == 4
    assert np.isfinite(energy4)

    relaxed, energy_rel = slices_nequip.to_relaxed_structure()
    assert isinstance(relaxed, Structure) and len(relaxed) == 1
    assert np.isfinite(energy_rel)

    decoded, energy_dec = slices_nequip.SLICES2structure(sli, strategy=4)
    assert isinstance(decoded, Structure) and len(decoded) == 1
    assert np.isclose(energy_dec, energy, atol=1e-12)


@pytest.mark.unit
def test_def007_function_timeout_main_and_worker_thread() -> None:
    """Verify function_timeout raises TimeoutException on main thread and runs in threads."""

    @function_timeout(2)
    def fast_add(a: int, b: int) -> int:
        return a + b

    assert fast_add(3, 4) == 7
    assert signal.alarm(0) == 0

    @function_timeout(1)
    def slow_op() -> None:
        time.sleep(2.5)

    with pytest.raises(TimeoutException) as exc_info:
        slow_op()
    assert isinstance(exc_info.value, SLICESError)
    assert signal.alarm(0) == 0

    thread_out: dict[str, Any] = {}

    def worker() -> None:
        try:
            thread_out["result"] = fast_add(10, 20)
        except BaseException as exc:  # noqa: BLE001
            thread_out["error"] = exc

    worker_thread = threading.Thread(target=worker)
    worker_thread.start()
    worker_thread.join(timeout=5.0)
    assert "error" not in thread_out
    assert thread_out.get("result") == 30


@pytest.mark.unit
def test_match_check_variants_return_expected_tuples(
    slices_no_relax: SLICES,
    ndsiru_structure: Structure,
) -> None:
    """Verify match_check, match_check3, and match_check4 return stringified match tuples."""
    neutral = Structure(
        ndsiru_structure.lattice,
        [sp.element for sp in ndsiru_structure.species],  # type: ignore[union-attr]
        ndsiru_structure.frac_coords,
    )
    res2 = slices_no_relax.match_check(ndsiru_structure, neutral, neutral)
    assert len(res2) == 4
    assert res2[:2] == ("1", "1")
    assert float(res2[2]) == 0.0

    res3 = slices_no_relax.match_check3(ndsiru_structure, neutral, neutral, neutral)
    assert len(res3) == 6
    assert res3[:3] == ("1", "1", "1")

    res4 = slices_no_relax.match_check4(
        ndsiru_structure, neutral, neutral, neutral, neutral
    )
    assert len(res4) == 8
    assert res4[:4] == ("1", "1", "1", "1")
