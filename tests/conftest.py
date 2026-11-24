"""Shared pytest fixtures for the SLICES v4.0.2 test suite.

Provides lightweight, side-effect-free fixtures for structures, data directories,
and ``SLICES`` encoder/decoder instances without mutating global environment
variables or eagerly importing ``slices.core`` at collection time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from pymatgen.core.structure import Structure

if TYPE_CHECKING:
    from slices.core import SLICES


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the root directory of the SLICES repository."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def examples_dir(repo_root: Path) -> Path:
    """Return the path to the repository ``examples/`` directory."""
    return repo_root / "examples"


@pytest.fixture(scope="session")
def data_dir(repo_root: Path) -> Path:
    """Return the path to the repository ``data/`` directory."""
    return repo_root / "data"


@pytest.fixture(scope="session")
def ndsiru_structure(examples_dir: Path) -> Structure:
    """Load the reference ``NdSiRu.cif`` crystal structure (P4/nmm, SG 129)."""
    return Structure.from_file(examples_dir / "NdSiRu.cif")


@pytest.fixture(scope="session")
def sr3ru2o7_structure(examples_dir: Path) -> Structure:
    """Load the reference ``Sr3Ru2O7.cif`` crystal structure (I4/mmm, SG 139)."""
    return Structure.from_file(examples_dir / "Sr3Ru2O7.cif")


@pytest.fixture
def slices_no_relax() -> SLICES:
    """Create a fresh ``SLICES`` instance with force-field relaxation disabled."""
    from slices.core import SLICES

    return SLICES(relax_model=None)


@pytest.fixture
def slices_nequip() -> SLICES:
    """Create a fresh ``SLICES`` instance backed by the cached default NequIP relaxer."""
    from slices.core import SLICES

    return SLICES(relax_model="auto")
