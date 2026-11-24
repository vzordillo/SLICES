"""Unit tests for the SLICES command-line interface (slices.cli)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pymatgen.core import Structure

import slices.core as core_mod
import slices.relax_backends as rb
from slices import __version__
from slices.cli import main
from slices.core import SLICES

pytestmark = pytest.mark.unit

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")

# Compact 3-atom trigonal BaSn2 (G10) SLICES string for fast live CLI NequIP decode test.
BASN2_SLICES: str = (
    "+ x n OOO e OOO o Ba Sn Sn 0 1 o-o 0 1 -oo 0 1 ooo 0 2 ooo 0 2 o+o "
    "0 2 +oo 1 2 oo- 1 2 +o- 1 2 o+-"
)


class TestCLIVersionAndHelp:
    """Verify CLI entry-point invocation, --version, and missing-subcommand exit status."""

    def test_module_cli_version_subprocess(self) -> None:
        """Verify `python -m slices.cli --version` prints slices 4.0.2 and exits 0."""
        env = dict(os.environ)
        env["PYTHONPATH"] = REPO_SRC
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "slices.cli", "--version"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() == f"slices {__version__}"

    def test_no_subcommand_returns_exit_code_one(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify invoking main([]) prints usage help and returns exit status 1."""
        rc = main([])
        captured = capsys.readouterr()
        assert rc == 1
        assert "usage: slices" in captured.out


class TestCLIEncodeValidateAndCanonicalize:
    """Verify non-relaxing CLI subcommands execute without loading force-field weights."""

    def test_encode_file_and_stdin_use_relax_model_none(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify encode writes SLICES strings and passes relax_model=None to make_relaxer."""
        requested_models: list[str | None] = []
        orig_make_relaxer = rb.make_relaxer

        def spy_make_relaxer(
            relax_model: str | None = "auto",
            optimizer: str = "BFGS",
        ) -> tuple[object, str]:
            requested_models.append(relax_model)
            return orig_make_relaxer(relax_model, optimizer=optimizer)

        monkeypatch.setattr(core_mod, "make_relaxer", spy_make_relaxer)
        monkeypatch.setattr(rb, "make_relaxer", spy_make_relaxer)

        out_file = tmp_path / "ndsiru.slices"
        rc = main(["encode", str(EXAMPLES_DIR / "NdSiRu.cif"), "-o", str(out_file)])
        assert rc == 0
        assert requested_models == [None]
        encoded = out_file.read_text(encoding="utf-8").strip()
        assert "Nd" in encoded and "Si" in encoded and "Ru" in encoded

        # Also test CIF via stdin ("-") writing to stdout.
        cif_text = (EXAMPLES_DIR / "NdSiRu.cif").read_text(encoding="utf-8")
        monkeypatch.setattr(sys, "stdin", io.StringIO(cif_text))
        capsys.readouterr()
        rc_stdin = main(["encode", "-"])
        captured = capsys.readouterr()
        assert rc_stdin == 0
        assert captured.out.strip() == encoded

        # Missing input file exits cleanly with code 1.
        assert main(["encode", str(tmp_path / "nonexistent.cif")]) == 1

    def test_validate_valid_invalid_stdin_and_flags(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Verify validate returns 0 on valid SLICES and 1 on invalid or duplicate inputs."""
        slices_file = tmp_path / "nd.slices"
        assert main(["encode", str(EXAMPLES_DIR / "NdSiRu.cif"), "-o", str(slices_file)]) == 0
        capsys.readouterr()

        # Valid file -> exit 0, stdout VALID.
        assert main(["validate", str(slices_file)]) == 0
        assert capsys.readouterr().out.strip() == "VALID"

        # Valid stdin ("-") -> exit 0, stdout VALID.
        monkeypatch.setattr(
            sys,
            "stdin",
            io.StringIO(slices_file.read_text(encoding="utf-8")),
        )
        assert main(["validate", "-"]) == 0
        assert capsys.readouterr().out.strip() == "VALID"

        # Invalid space-group prefix (E03) -> exit 1, stdout INVALID.
        assert main(["validate", "q q q Si O 0 1 ooo"]) == 1
        assert capsys.readouterr().out.strip() == "INVALID"

        # 1D rank-deficient string (E06): fails full validate (1), passes --basic (0).
        rank_def = "Si O 0 1 ooo 0 1 +oo"
        assert main(["validate", rank_def]) == 1
        assert capsys.readouterr().out.strip() == "INVALID"
        assert main(["validate", "--basic", rank_def]) == 0
        assert capsys.readouterr().out.strip() == "VALID"

        # Duplicate flipped edge (E09): passes default (0), fails --check-duplicates (1).
        dupli = "Si O 0 1 ooo 1 0 ooo 0 1 +oo 0 1 o+o 0 1 oo+"
        assert main(["validate", dupli]) == 0
        capsys.readouterr()
        assert main(["validate", "--check-duplicates", dupli]) == 1
        assert capsys.readouterr().out.strip() == "INVALID"

    def test_canonicalize_matches_backend_canonical_slices(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify canonicalize writes the exact string produced by get_canonical_SLICES."""
        raw_path = tmp_path / "raw.slices"
        canon_path = tmp_path / "canon.slices"
        assert main(["encode", str(EXAMPLES_DIR / "NdSiRu.cif"), "-o", str(raw_path)]) == 0
        assert main(["canonicalize", str(raw_path), "-o", str(canon_path)]) == 0

        expected = SLICES(relax_model=None).get_canonical_SLICES(
            raw_path.read_text(encoding="utf-8").strip()
        )
        assert canon_path.read_text(encoding="utf-8").strip() == expected.strip()


class TestCLIDecodeAndOptionalMLIPErrorHandling:
    """Verify decode formats, --robust, --relax-model auto, and uninstalled MLIP errors."""

    def test_decode_no_relax_cif_json_and_robust_modes(
        self,
        tmp_path: Path,
    ) -> None:
        """Verify decode --relax-model none writes valid CIF and JSON structures."""
        slices_file = tmp_path / "nd.slices"
        cif_out = tmp_path / "nd_none.cif"
        json_out = tmp_path / "nd_robust.json"

        assert main(["encode", str(EXAMPLES_DIR / "NdSiRu.cif"), "-o", str(slices_file)]) == 0
        assert (
            main(["decode", str(slices_file), "-o", str(cif_out), "--relax-model", "none"]) == 0
        )
        assert cif_out.is_file()
        parsed_cif = Structure.from_file(str(cif_out))
        assert len(parsed_cif) == 6

        assert (
            main(
                [
                    "decode",
                    str(slices_file),
                    "-o",
                    str(json_out),
                    "--relax-model",
                    "none",
                    "--robust",
                    "--seed",
                    "42",
                ]
            )
            == 0
        )
        parsed_json = json.loads(json_out.read_text(encoding="utf-8"))
        assert len(parsed_json["sites"]) == 6

    def test_decode_auto_nequip_on_compact_basn2_slices(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Verify decode defaults to --relax-model auto (nequip-s+l) and writes a CIF."""
        monkeypatch.setenv("SLICES_DEVICE", "cpu")
        out_cif = tmp_path / "basn2_auto.cif"
        assert main(["decode", BASN2_SLICES, "-o", str(out_cif)]) == 0
        rec = Structure.from_file(str(out_cif))
        assert len(rec) == 3

    @pytest.mark.parametrize("flag_val", ["chgnet", "orb-v3"])
    def test_decode_uninstalled_optional_mlip_exits_cleanly_with_code_one(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        flag_val: str,
    ) -> None:
        """Verify uninstalled optional --relax-model values print ERROR and return exit code 1."""
        monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
        rc = main(["decode", BASN2_SLICES, "--relax-model", flag_val])
        captured = capsys.readouterr()
        assert rc == 1
        assert "ERROR:" in captured.err
        assert "Traceback" not in captured.err

        # With --verbose, traceback is also emitted to stderr while still returning 1.
        rc_verbose = main(["--verbose", "decode", BASN2_SLICES, "--relax-model", flag_val])
        captured_verbose = capsys.readouterr()
        assert rc_verbose == 1
        assert "Traceback" in captured_verbose.err
