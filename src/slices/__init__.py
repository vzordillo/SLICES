"""SLICES: Simplified Line-Input Crystal-Encoding System.

Provides invertible crystal-structure encoding and decoding via labeled quotient
graphs, topology-only GFN-FF geometry targets, ZL* optimization, and NequIP /
optional MLIP cell relaxation.

Heavy scientific modules (:mod:`slices.core`) are loaded lazily via PEP 562
``__getattr__`` so importing lightweight submodules such as
:mod:`slices.exceptions` or :mod:`slices.relax_backends` introduces no startup
overhead or environment-variable side effects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from slices.core import SLICES

__version__ = "4.1.0"

__all__ = [
    "SLICES",
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
    "__version__",
    "check_SLICES",
]


def check_SLICES(
    slices_str: str,
    strategy: int = 4,
    dupli_check: bool = False,
    graph_rank_check: bool = True,
) -> bool:
    """Validate whether a SLICES string is syntactically and topologically valid.

    Lazily instantiates ``SLICES(relax_model=None)`` so validation runs without
    loading force-field models.

    Args:
        slices_str: Input SLICES representation string.
        strategy: Encoding strategy used by ``slices_str`` (1, 3, or 4).
            Defaults to 4.
        dupli_check: Whether to reject duplicate quotient-graph edges rather
            than deduplicating them. Defaults to False.
        graph_rank_check: Whether to require first homology group rank
            ``H1(X, Z) >= 3`` for 3D periodicity. Defaults to True.

    Returns:
        ``True`` if ``slices_str`` passes syntax and graph-topology checks;
        ``False`` otherwise.
    """
    from slices.core import SLICES as _SLICES

    return _SLICES(relax_model=None).check_SLICES(
        slices_str,
        strategy=strategy,
        dupli_check=dupli_check,
        graph_rank_check=graph_rank_check,
    )


def __getattr__(name: str) -> Any:
    """Lazily import :class:`slices.core.SLICES` on first attribute access."""
    if name == "SLICES":
        from slices.core import SLICES as _SLICES

        globals()["SLICES"] = _SLICES
        return _SLICES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Return module attributes including lazily loaded public symbols."""
    return sorted(set(globals()) | set(__all__))
