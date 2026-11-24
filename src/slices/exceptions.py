"""Structured exception hierarchy for the SLICES crystal representation package.

All package-specific exceptions inherit from :class:`SLICESError`. Force-field
backend exceptions (:class:`RelaxBackendError` and :class:`ModelDownloadError`)
additionally inherit from :class:`RuntimeError` as sibling classes so callers
catching either ``RuntimeError`` or ``SLICESError`` behave consistently while
preventing network download failures from being recorded as compilation failures.
"""

from __future__ import annotations

__all__ = [
    "CocycleBasisError",
    "GFNFFExecutionError",
    "GraphTopologyError",
    "LatticeBasisError",
    "MLIPRelaxationError",
    "ModelDownloadError",
    "RelaxBackendError",
    "SLICESDecodingError",
    "SLICESEncodingError",
    "SLICESError",
    "TimeoutException",
    "XTBExecutionError",
]


class SLICESError(Exception):
    """Base exception for all SLICES encoding, decoding, and backend errors."""


class SLICESEncodingError(SLICESError):
    """Raised when converting a crystal structure into a SLICES string fails."""


class SLICESDecodingError(SLICESError):
    """Raised when reconstructing a crystal structure from a SLICES string fails."""


class GraphTopologyError(SLICESError):
    """Base exception for periodic quotient-graph or net topology failures."""


class LatticeBasisError(GraphTopologyError):
    """Raised when a 3D lattice basis cannot be obtained from cycle vectors."""


class CocycleBasisError(GraphTopologyError):
    """Raised when a linearly independent cocycle basis cannot be constructed."""


class GFNFFExecutionError(SLICESError):
    """Raised when GFN-FF topology generation or external xtb fallback fails."""


# Backward-compatible alias used in pre-v4.0 scripts and tests.
XTBExecutionError = GFNFFExecutionError


class MLIPRelaxationError(SLICESError):
    """Raised when machine-learning interatomic potential relaxation fails."""


class TimeoutException(SLICESError):
    """Raised when a decorated function exceeds its ``function_timeout`` limit."""


class RelaxBackendError(SLICESError, RuntimeError):
    """Raised when a force-field model fails to compile, load, or evaluate."""


class ModelDownloadError(SLICESError, RuntimeError):
    """Raised when force-field model weights cannot be downloaded.

    Deliberately a sibling of :class:`RelaxBackendError` (not a subclass) so
    transient network failures never write permanent ``.failed`` cache markers.
    """
