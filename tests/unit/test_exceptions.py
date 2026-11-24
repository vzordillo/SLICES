"""Unit tests for the SLICES structured exception hierarchy and timeout decorator."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

import slices
from slices import exceptions as exc_mod
from slices.core import function_timeout
from slices.exceptions import (
    CocycleBasisError,
    GFNFFExecutionError,
    GraphTopologyError,
    LatticeBasisError,
    MLIPRelaxationError,
    ModelDownloadError,
    RelaxBackendError,
    SLICESDecodingError,
    SLICESEncodingError,
    SLICESError,
    TimeoutException,
    XTBExecutionError,
)

pytestmark = pytest.mark.unit

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")


class TestExceptionHierarchy:
    """Verify inheritance relationships across all SLICES exception classes."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            SLICESEncodingError,
            SLICESDecodingError,
            GraphTopologyError,
            LatticeBasisError,
            CocycleBasisError,
            GFNFFExecutionError,
            XTBExecutionError,
            MLIPRelaxationError,
            TimeoutException,
            RelaxBackendError,
            ModelDownloadError,
        ],
    )
    def test_all_exceptions_inherit_from_slices_error(
        self,
        exc_cls: type[BaseException],
    ) -> None:
        """Verify every domain exception inherits from SLICESError."""
        assert issubclass(exc_cls, SLICESError)
        instance = exc_cls("diagnostic message")
        assert isinstance(instance, SLICESError)
        assert "diagnostic message" in str(instance)

    def test_graph_topology_subclasses(self) -> None:
        """Verify LatticeBasisError and CocycleBasisError inherit from GraphTopologyError."""
        assert issubclass(LatticeBasisError, GraphTopologyError)
        assert issubclass(CocycleBasisError, GraphTopologyError)
        assert not issubclass(LatticeBasisError, CocycleBasisError)
        assert not issubclass(CocycleBasisError, LatticeBasisError)

    def test_xtb_execution_error_alias_identity(self) -> None:
        """Verify XTBExecutionError is an exact alias of GFNFFExecutionError."""
        assert XTBExecutionError is GFNFFExecutionError
        err = XTBExecutionError("helper failed")
        assert isinstance(err, GFNFFExecutionError)
        assert isinstance(err, SLICESError)

    def test_relax_backend_and_model_download_dual_inheritance_siblings(self) -> None:
        """Verify RelaxBackendError and ModelDownloadError are sibling RuntimeError subclasses."""
        assert issubclass(RelaxBackendError, SLICESError)
        assert issubclass(RelaxBackendError, RuntimeError)
        assert issubclass(ModelDownloadError, SLICESError)
        assert issubclass(ModelDownloadError, RuntimeError)

        # Network failures must NEVER match `except RelaxBackendError:` so they are not
        # written as permanent `.failed` compilation markers.
        assert not issubclass(ModelDownloadError, RelaxBackendError)
        assert not issubclass(RelaxBackendError, ModelDownloadError)

        with pytest.raises(RuntimeError):
            raise ModelDownloadError("network timeout")
        with pytest.raises(SLICESError):
            raise RelaxBackendError("compile error")


class TestPackageExportsAndLazyImports:
    """Verify top-level package re-exports and zero-side-effect lazy imports."""

    def test_top_level_version_and_exception_reexports(self) -> None:
        """Verify slices.__version__ and all exception classes are exported at top level."""
        assert slices.__version__ == "4.0.2"
        for symbol in exc_mod.__all__:
            assert symbol in slices.__all__
            assert getattr(slices, symbol) is getattr(exc_mod, symbol)

    def test_zero_side_effect_import_in_fresh_subprocess(self) -> None:
        """Verify importing slices and slices.exceptions avoids eager heavy imports."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("OMP_NUM_THREADS", "TF_USE_LEGACY_KERAS")
        }
        env["PYTHONPATH"] = _REPO_SRC
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        code = (
            "import os, sys\n"
            "import slices\n"
            "import slices.exceptions\n"
            "assert slices.__version__ == '4.0.2'\n"
            "assert 'OMP_NUM_THREADS' not in os.environ\n"
            "assert 'TF_USE_LEGACY_KERAS' not in os.environ\n"
            "for heavy in ('torch', 'tensorflow', 'slices.core'):\n"
            "    assert heavy not in sys.modules, heavy\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr


class TestFunctionTimeoutDecorator:
    """Verify POSIX main-thread timeout handling and worker-thread safety."""

    def test_main_thread_timeout_raises_timeout_exception_and_clears_alarm(self) -> None:
        """Verify function_timeout raises TimeoutException and resets signal.alarm(0)."""

        @function_timeout(seconds=1)
        def slow_operation() -> str:
            time.sleep(2.5)
            return "unreachable"

        with pytest.raises(TimeoutException, match="Timed out"):
            slow_operation()

        # Verify no pending SIGALRM remains scheduled after exit.
        assert signal.alarm(0) == 0

    def test_worker_thread_executes_without_signal_value_error(self) -> None:
        """Verify function_timeout runs cleanly inside a non-main Python thread."""

        @function_timeout(seconds=5)
        def compute_sum(a: int, b: int) -> int:
            return a + b

        outcome: dict[str, object] = {}

        def runner() -> None:
            try:
                outcome["value"] = compute_sum(19, 23)
            except BaseException as exc:  # noqa: BLE001
                outcome["error"] = exc

        worker = threading.Thread(target=runner)
        worker.start()
        worker.join(timeout=5.0)
        assert "error" not in outcome
        assert outcome.get("value") == 42
