"""Unit tests for GFN-FF topology generation and non-Linux external xtb fallback."""

from __future__ import annotations

import json
import os
import shutil
import stat
import sys
from pathlib import Path

import numpy as np
import pytest

from slices.core import SLICES
from slices.exceptions import GFNFFExecutionError, XTBExecutionError
from slices.gfnff_helper import (
    LEGACY86_PARAM_FILE,
    _env_default,
    _run_external_xtb_fallback,
    _selected_params,
    parse_nbf_text,
    run_gfnff_helper,
    write_debug_files,
)

pytestmark = pytest.mark.unit

METHANE_NBF: str = (
    "5\nC H H H H\n2 1 1 1 1\n3 0 0 0 0\n4 0 0 0 0\n5 0 0 0 0\n"
    + "0 0 0 0 0\n" * 15
    + "4 1 1 1 1\n"
)

NA3MNCONIO6_SLICES: str = (
    "o x a DDO j OOO o Na Na Na Mn Co Ni O O O O O O 0 8 oo- 0 10 o-o 0 10 -oo 0 6 o-- "
    "0 6 -o- 0 11 ooo 1 6 ooo 1 11 +o+ 1 11 o++ 1 7 +oo 1 7 o+o 1 9 +++ 2 7 ooo 2 9 +o+ "
    "2 9 o++ 2 8 +oo 2 8 o+o 2 10 oo+ 3 11 ooo 3 6 o-o 3 6 -oo 3 9 +oo 3 9 o+o 3 7 ooo "
    "4 10 ooo 4 8 +oo 4 8 o+o 4 11 +oo 4 11 o+o 4 6 ooo 5 9 ooo 5 7 o-o 5 7 -oo 5 10 o-o "
    "5 10 -oo 5 8 ooo"
)


class TestParseNbfAndParamSelection:
    """Verify NBF text parsing, parameter mode selection, and debug file output."""

    def test_parse_valid_methane_nbf(self) -> None:
        """Verify parse_nbf_text returns int32 atomic numbers and a (20, nat) table."""
        numbers, nbf = parse_nbf_text(METHANE_NBF)
        assert numbers.dtype == np.int32
        assert nbf.dtype == np.int32
        assert list(numbers) == [6, 1, 1, 1, 1]
        assert nbf.shape == (20, 5)
        assert list(nbf[-1]) == [4, 1, 1, 1, 1]

    def test_parse_nbf_text_validation_errors(self) -> None:
        """Verify malformed NBF inputs raise ValueError with informative messages."""
        with pytest.raises(ValueError, match="got 3 lines"):
            parse_nbf_text("5\nC H H H H\n2 1 1 1 1\n")

        bad_symbols = "5\nC H H\n" + "0 0 0 0 0\n" * 20
        with pytest.raises(ValueError, match="symbol row"):
            parse_nbf_text(bad_symbols)

        bad_width = "2\nC H\n" + "0 0 0\n" * 20
        with pytest.raises(ValueError, match="shape"):
            parse_nbf_text(bad_width)

    def test_selected_params_and_env_default_restoration(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Verify parameter mode aliases, missing-file error, and _env_default cleanup."""
        monkeypatch.delenv("SLICES_VENDOR_GFNFF_PARAM_MODE", raising=False)
        monkeypatch.delenv("SLICES_VENDOR_GFNFF_PARAM_FILE", raising=False)
        mode, path = _selected_params()
        assert mode == "legacy86_overlay"
        assert Path(path) == LEGACY86_PARAM_FILE
        assert Path(path).is_file()

        monkeypatch.setenv("SLICES_VENDOR_GFNFF_PARAM_MODE", "modern")
        assert _selected_params() == ("modern", "")

        monkeypatch.setenv("SLICES_VENDOR_GFNFF_PARAM_MODE", "invalid_mode")
        with pytest.raises(ValueError, match="SLICES_VENDOR_GFNFF_PARAM_MODE"):
            _selected_params()

        monkeypatch.setenv("SLICES_VENDOR_GFNFF_PARAM_MODE", "legacy86")
        monkeypatch.setenv("SLICES_VENDOR_GFNFF_PARAM_FILE", str(tmp_path / "missing.xtb"))
        with pytest.raises(FileNotFoundError, match="not found"):
            _selected_params()

        key = "SLICES_TEST_TEMP_ENV_VAR"
        monkeypatch.delenv(key, raising=False)
        with _env_default(key, "alpha"):
            assert os.environ[key] == "alpha"
        assert key not in os.environ

        monkeypatch.setenv(key, "preexisting")
        with pytest.raises(RuntimeError), _env_default(key, "ignored"):
            assert os.environ[key] == "preexisting"
            raise RuntimeError("boom")
        assert os.environ[key] == "preexisting"

    def test_write_debug_files(self, tmp_path: Path) -> None:
        """Verify write_debug_files writes testBonds_cut.top and gfnff_lists.json."""
        payload = {"blist": [[2, 1]], "vbond": [[1.0, 2.0]], "alist": [], "vangl": []}
        write_debug_files(METHANE_NBF, payload, directory=tmp_path)
        assert (tmp_path / "testBonds_cut.top").read_text(encoding="utf-8") == METHANE_NBF
        loaded = json.loads((tmp_path / "gfnff_lists.json").read_text(encoding="utf-8"))
        assert loaded["blist"] == [[2, 1]]


@pytest.mark.gfnff
class TestLiveBundledGfnffHelper:
    """Verify bundled Linux x86_64 libgfnff topology evaluation on reference molecules."""

    def test_methane_and_actinide_topology(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify methane produces 4 bonds and 6 angles and actinide Th evaluates finitely."""
        monkeypatch.delenv("SLICES_VENDOR_GFNFF_PARAM_MODE", raising=False)
        data = run_gfnff_helper(METHANE_NBF)
        assert sorted(map(tuple, data["blist"])) == [(2, 1), (3, 1), (4, 1), (5, 1)]
        assert len(data["alist"]) == 6
        assert data["metadata"]["param_mode"] == "legacy86_overlay"

        # Actinide Z=90 (Th) neighbor table evaluates finitely via Z=87..103 parameters.
        th_nbf = "2\nTh C\n2 1\n" + "0 0\n" * 18 + "1 1\n"
        th_data = run_gfnff_helper(th_nbf)
        assert len(th_data["blist"]) == 1
        assert np.all(np.isfinite(np.asarray(th_data["vbond"], dtype=float)))

    def test_na3mnconio6_reference_inner_p_target(self) -> None:
        """Verify Na3MnCoNiO6 reconstruction targets match the stored reference values."""
        backend = SLICES(relax_model=None)
        backend.from_SLICES(NA3MNCONIO6_SLICES)
        inner_p, inds, weights = backend.get_inner_p_target()
        got = (
            float(np.trace(inner_p)),
            float(np.abs(inner_p).sum()),
            len(inds[0]),
            float(sum(weights)),
        )
        want = (178.74144, 178.74144, 126, 61.23)
        np.testing.assert_allclose(got, want, rtol=1e-6)


class TestMockedExternalXtbFallback:
    """Verify non-Linux (ImportError, OSError) fallback to an external xtb binary."""

    def test_missing_binary_raises_gfnff_execution_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify missing xtb binary raises GFNFFExecutionError with SLICES_XTB_PATH hint."""
        import slices._vendor as vendor_pkg

        monkeypatch.delenv("SLICES_XTB_PATH", raising=False)
        monkeypatch.delenv("XTB_MOD_PATH", raising=False)
        monkeypatch.setattr(shutil, "which", lambda _: None)
        monkeypatch.delattr(vendor_pkg, "gfnff", raising=False)
        monkeypatch.setitem(sys.modules, "slices._vendor.gfnff", None)

        with pytest.raises(GFNFFExecutionError, match="SLICES_XTB_PATH") as exc_info:
            run_gfnff_helper(METHANE_NBF)
        assert isinstance(exc_info.value, XTBExecutionError)

    def test_mock_xtb_script_sanitizes_fortran_asterisks_and_returns_lists(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Verify SLICES_XTB_PATH fallback executes cleanly and sanitizes '********' tokens."""
        import slices._vendor as vendor_pkg

        raw_json = '{"blist": [[2, 1]], "vbond": [[2.05, ********]], "alist": [], "vangl": []}'
        fake_xtb = tmp_path / "mock_xtb.py"
        fake_xtb.write_text(
            f"#!{sys.executable}\n"
            "from pathlib import Path\n"
            "assert Path('testBonds_cut.top').is_file()\n"
            f"Path('gfnff_lists.json').write_text({raw_json!r}, encoding='utf-8')\n",
            encoding="utf-8",
        )
        fake_xtb.chmod(fake_xtb.stat().st_mode | stat.S_IXUSR)

        monkeypatch.setenv("SLICES_XTB_PATH", str(fake_xtb))
        monkeypatch.delattr(vendor_pkg, "gfnff", raising=False)
        monkeypatch.setitem(sys.modules, "slices._vendor.gfnff", None)

        out = run_gfnff_helper(METHANE_NBF)
        assert out["blist"] == [[2, 1]]
        assert out["vbond"] == [[2.05, 0]]
        assert out["metadata"]["param_mode"] == "external_xtb"
        assert out["metadata"]["xtb_binary"] == str(fake_xtb)

    def test_failing_mock_xtb_script_raises_gfnff_execution_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Verify non-zero exit without gfnff_lists.json raises GFNFFExecutionError."""
        bad_xtb = tmp_path / "bad_xtb.py"
        bad_xtb.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "sys.stderr.write('fatal topo error\\n')\n"
            "sys.exit(2)\n",
            encoding="utf-8",
        )
        bad_xtb.chmod(bad_xtb.stat().st_mode | stat.S_IXUSR)

        monkeypatch.setenv("SLICES_XTB_PATH", str(bad_xtb))
        with pytest.raises(GFNFFExecutionError, match="fatal topo error"):
            _run_external_xtb_fallback(METHANE_NBF, reason=OSError("dlopen failed"))
