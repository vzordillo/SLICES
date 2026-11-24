"""Command-line interface for encoding, decoding, validating, and canonicalizing SLICES.

Entry point registered as ``slices = "slices.cli:main"`` in ``pyproject.toml``
(and directly runnable via ``python -m slices.cli``).

Non-relaxing subcommands (``encode``, ``validate``, ``canonicalize``) instantiate
``SLICES(relax_model=None)`` so they execute without loading force-field weights.
The ``decode`` subcommand defaults to ``--relax-model auto`` (resolving to SLICES
v4.0.2 ``nequip-s+l`` on CPU unless ``SLICES_RELAX_MODEL`` / ``SLICES_DEVICE`` is
configured) and also accepts optional MLIP backends when installed.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING

from slices import __version__
from slices.exceptions import SLICESError
from slices.mlip_relaxer import OPTIONAL_MLIP_ALIASES, OPTIONAL_MLIP_MODELS
from slices.relax_backends import OPTIMIZERS, RELAX_MODELS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pymatgen.core.structure import Structure

__all__ = [
    "ALL_CLI_RELAX_MODELS",
    "build_parser",
    "canonicalize_slices",
    "decode_slices",
    "encode_structure",
    "main",
    "validate_slices",
]

ALL_CLI_RELAX_MODELS: tuple[str, ...] = (
    *RELAX_MODELS,
    *OPTIONAL_MLIP_MODELS,
)

_GRAPH_METHODS: tuple[str, ...] = ("econnn", "crystalnn", "brunnernn", "mininn")
_PATH_LIKE_SUFFIXES: tuple[str, ...] = (".slices", ".txt", ".sli", ".cif", ".vasp")


def _normalize_cli_relax_model(raw: str) -> str:
    """Normalize case and optional MLIP aliases for ``--relax-model``."""
    lowered = raw.strip().lower()
    return OPTIONAL_MLIP_ALIASES.get(lowered, lowered)


def _read_slices_input(source: str) -> str:
    """Read a SLICES string from ``"-"`` (stdin), an existing file path, or an inline string."""
    if source == "-":
        text = sys.stdin.read().strip()
        if not text:
            raise ValueError("No SLICES text received on stdin.")
        return text.splitlines()[0].strip()

    candidate = Path(source)
    if candidate.is_file():
        for line in candidate.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        raise ValueError(f"SLICES file is empty: {candidate}")

    # Distinguish a missing file path from an inline SLICES string (which has spaces).
    if " " not in source.strip() or source.strip().lower().endswith(_PATH_LIKE_SUFFIXES):
        raise FileNotFoundError(f"SLICES input file not found: {source}")
    return source.strip()


def _infer_structure_format(output_path: Path | None, explicit_fmt: str | None) -> str:
    """Infer pymatgen structure output format from ``explicit_fmt`` or ``output_path``."""
    if explicit_fmt:
        return explicit_fmt
    if output_path is None:
        return "cif"
    suffix = output_path.suffix.lower()
    if suffix in (".vasp", ".poscar") or output_path.name.upper().startswith("POSCAR"):
        return "poscar"
    if suffix == ".json":
        return "json"
    return "cif"


def encode_structure(
    input_file: str | Path,
    output_file: str | Path | None = None,
    strategy: int = 4,
    graph_method: str = "econnn",
) -> str:
    """Encode a crystal structure file (or ``"-"`` CIF stdin) into a SLICES string.

    Args:
        input_file: Path to input structure file (CIF, POSCAR, JSON) or ``"-"``
            for CIF text on standard input.
        output_file: Optional path where the encoded SLICES string is written.
        strategy: SLICES encoding strategy (1, 2, 3, or 4). Defaults to 4.
        graph_method: Local-environment graph builder. Defaults to ``"econnn"``.

    Returns:
        Encoded SLICES string.
    """
    from pymatgen.core.structure import Structure

    from slices.core import SLICES

    if str(input_file) == "-":
        cif_text = sys.stdin.read()
        if not cif_text.strip():
            raise ValueError("No structure data received on stdin.")
        structure = Structure.from_str(cif_text, fmt="cif")
    else:
        path = Path(input_file)
        if not path.is_file():
            raise FileNotFoundError(f"Input structure file not found: {path}")
        structure = Structure.from_file(str(path))

    backend = SLICES(relax_model=None, graph_method=graph_method)
    slices_string = backend.structure2SLICES(structure, strategy=strategy)

    if output_file is not None:
        out_path = Path(output_file)
        out_path.write_text(slices_string + "\n", encoding="utf-8")
        print(f"Saved SLICES string to {out_path}", file=sys.stderr)
    else:
        print(slices_string)

    return slices_string


def decode_slices(
    slices_input: str | Path,
    output_file: str | Path | None = None,
    relax_model: str | None = "auto",
    optimizer: str = "BFGS",
    fmax: float = 0.2,
    steps: int = 100,
    strategy: int = 4,
    use_robust: bool = False,
    seed: int = 0,
    fmt: str | None = None,
) -> tuple[Structure, float]:
    """Decode a SLICES file/string into a crystal structure and energy per atom.

    Args:
        slices_input: SLICES file path, ``"-"`` for stdin, or inline SLICES string.
        output_file: Optional output structure file path.
        relax_model: Force-field model identifier. Defaults to ``"auto"``.
        optimizer: Local optimizer name from ``OPTIMIZERS``. Defaults to ``"BFGS"``.
        fmax: Force convergence criterion in eV/Angstrom. Defaults to ``0.2``.
        steps: Maximum relaxation steps. Defaults to ``100``.
        strategy: SLICES encoding strategy (1, 3, or 4). Defaults to 4.
        use_robust: Whether to use opt-in :meth:`SLICES.robust_SLICES2structure`.
            Defaults to ``False``.
        seed: Random seed for ``--robust`` multi-start perturbations. Defaults to 0.
        fmt: Explicit output format (``"cif"``, ``"poscar"``, ``"json"``).

    Returns:
        Tuple ``(structure, energy_per_atom)``.
    """
    from slices.core import SLICES

    slices_string = _read_slices_input(str(slices_input))
    backend = SLICES(
        relax_model=relax_model,
        optimizer=optimizer,
        fmax=fmax,
        steps=steps,
    )
    if use_robust:
        structure, energy = backend.robust_SLICES2structure(
            slices_string,
            strategy=strategy,
            seed=seed,
        )
    else:
        structure, energy = backend.SLICES2structure(
            slices_string,
            strategy=strategy,
        )

    out_path = Path(output_file) if output_file is not None else None
    target_fmt = _infer_structure_format(out_path, fmt)
    rendered = structure.to(fmt=target_fmt)

    print(
        f"Decoded {structure.composition.reduced_formula} "
        f"(model={backend.relax_model}, E={energy:.6f} eV/atom)",
        file=sys.stderr,
    )
    if out_path is not None:
        out_path.write_text(rendered, encoding="utf-8")
        print(f"Saved structure to {out_path}", file=sys.stderr)
    else:
        print(rendered)

    return structure, float(energy)


def validate_slices(
    slices_input: str | Path,
    strategy: int = 4,
    basic: bool = False,
    check_duplicates: bool = False,
    graph_rank_check: bool = True,
) -> bool:
    """Validate syntax and quotient-graph topology of a SLICES file/string.

    Args:
        slices_input: SLICES file path, ``"-"`` for stdin, or inline SLICES string.
        strategy: SLICES encoding strategy (1, 3, or 4). Defaults to 4.
        basic: If ``True``, run syntax/node-coverage check only
            (``check_SLICES_basic``). Defaults to ``False``.
        check_duplicates: Reject duplicate edges when ``True``. Defaults to ``False``.
        graph_rank_check: Require ``H1(X, Z) >= 3`` when ``True``. Defaults to ``True``.

    Returns:
        ``True`` if valid, ``False`` otherwise.
    """
    from slices.core import SLICES

    slices_string = _read_slices_input(str(slices_input))
    backend = SLICES(relax_model=None)
    if basic:
        is_valid = backend.check_SLICES_basic(slices_string, strategy=strategy)
    else:
        is_valid = backend.check_SLICES(
            slices_string,
            strategy=strategy,
            dupli_check=check_duplicates,
            graph_rank_check=graph_rank_check,
        )
    print("VALID" if is_valid else "INVALID")
    return bool(is_valid)


def canonicalize_slices(
    slices_input: str | Path,
    output_file: str | Path | None = None,
    strategy: int = 4,
) -> str:
    """Convert a SLICES file/string into its canonical representation.

    Args:
        slices_input: SLICES file path, ``"-"`` for stdin, or inline SLICES string.
        output_file: Optional destination file path for the canonical SLICES string.
        strategy: SLICES encoding strategy (1, 3, or 4). Defaults to 4.

    Returns:
        Canonical SLICES string.
    """
    from slices.core import SLICES

    slices_string = _read_slices_input(str(slices_input))
    backend = SLICES(relax_model=None)
    canonical = backend.get_canonical_SLICES(slices_string, strategy=strategy)
    if output_file is not None:
        out_path = Path(output_file)
        out_path.write_text(canonical + "\n", encoding="utf-8")
        print(f"Saved canonical SLICES string to {out_path}", file=sys.stderr)
    else:
        print(canonical)
    return canonical


def build_parser() -> argparse.ArgumentParser:
    """Construct the ``slices`` ``ArgumentParser`` instance."""
    parser = argparse.ArgumentParser(
        prog="slices",
        description="SLICES: Simplified Line-Input Crystal-Encoding System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  slices encode examples/NdSiRu.cif -o NdSiRu.slices\n"
            "  slices validate NdSiRu.slices\n"
            "  slices canonicalize NdSiRu.slices -o NdSiRu.canon.slices\n"
            "  slices decode NdSiRu.slices -o reconstructed.cif --relax-model auto\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"slices {__version__}",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print full Python tracebacks on errors",
    )

    subparsers = parser.add_subparsers(dest="command", help="subcommand to execute")

    encode_p = subparsers.add_parser("encode", help="encode a crystal structure to SLICES")
    encode_p.add_argument(
        "input_file",
        help="input structure file (CIF, POSCAR, JSON) or '-' for CIF on stdin",
    )
    encode_p.add_argument("--output", "-o", help="output SLICES file path")
    encode_p.add_argument(
        "--strategy",
        type=int,
        default=4,
        choices=(1, 2, 3, 4),
        help="encoding strategy (default: 4)",
    )
    encode_p.add_argument(
        "--graph-method",
        default="econnn",
        choices=_GRAPH_METHODS,
        help="local-environment graph method (default: econnn)",
    )

    decode_p = subparsers.add_parser("decode", help="decode a SLICES string/file to a structure")
    decode_p.add_argument(
        "slices_input",
        help="input SLICES file path, '-' for stdin, or inline SLICES string",
    )
    decode_p.add_argument("--output", "-o", help="output structure file path")
    decode_p.add_argument(
        "--relax-model",
        "--model",
        "-m",
        dest="relax_model",
        type=_normalize_cli_relax_model,
        default="auto",
        choices=ALL_CLI_RELAX_MODELS,
        help="force-field model for final relaxation (default: auto -> nequip-s+l)",
    )
    decode_p.add_argument(
        "--optimizer",
        default="BFGS",
        choices=OPTIMIZERS,
        help="local relaxation optimizer (default: BFGS)",
    )
    decode_p.add_argument(
        "--fmax",
        type=float,
        default=0.2,
        help="force convergence threshold in eV/Angstrom (default: 0.2)",
    )
    decode_p.add_argument(
        "--steps",
        type=int,
        default=100,
        help="maximum relaxation steps (default: 100)",
    )
    decode_p.add_argument(
        "--strategy",
        type=int,
        default=4,
        choices=(1, 3, 4),
        help="SLICES format strategy (default: 4)",
    )
    decode_p.add_argument(
        "--fmt",
        choices=("cif", "poscar", "json"),
        default=None,
        help="explicit output structure format (inferred from --output by default)",
    )
    decode_p.add_argument(
        "--robust",
        action="store_true",
        help="enable opt-in multi-stage recovery decoding (robust_SLICES2structure)",
    )
    decode_p.add_argument(
        "--seed",
        type=int,
        default=0,
        help="random seed for --robust perturbations (default: 0)",
    )

    validate_p = subparsers.add_parser("validate", help="validate a SLICES string or file")
    validate_p.add_argument(
        "slices_input",
        help="SLICES file path, '-' for stdin, or inline SLICES string",
    )
    validate_p.add_argument(
        "--strategy",
        type=int,
        default=4,
        choices=(1, 3, 4),
        help="SLICES format strategy (default: 4)",
    )
    validate_p.add_argument(
        "--basic",
        action="store_true",
        help="run syntax and node-coverage validation only",
    )
    validate_p.add_argument(
        "--check-duplicates",
        action="store_true",
        help="reject SLICES strings containing duplicate edges",
    )
    validate_p.add_argument(
        "--no-graph-rank-check",
        action="store_true",
        help="skip H1(X, Z) >= 3 homology rank requirement",
    )

    canon_p = subparsers.add_parser(
        "canonicalize",
        help="convert a SLICES string or file into canonical form",
    )
    canon_p.add_argument(
        "slices_input",
        help="input SLICES file path, '-' for stdin, or inline SLICES string",
    )
    canon_p.add_argument("--output", "-o", help="output canonical SLICES file path")
    canon_p.add_argument(
        "--strategy",
        type=int,
        default=4,
        choices=(1, 3, 4),
        help="SLICES format strategy (default: 4)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the ``slices`` CLI and return a POSIX exit status code.

    Args:
        argv: Optional sequence of CLI arguments (defaults to ``sys.argv[1:]``).

    Returns:
        ``0`` on success, ``1`` on validation failure or runtime error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "encode":
            encode_structure(
                args.input_file,
                output_file=args.output,
                strategy=args.strategy,
                graph_method=args.graph_method,
            )
            return 0
        if args.command == "decode":
            decode_slices(
                args.slices_input,
                output_file=args.output,
                relax_model=args.relax_model,
                optimizer=args.optimizer,
                fmax=args.fmax,
                steps=args.steps,
                strategy=args.strategy,
                use_robust=args.robust,
                seed=args.seed,
                fmt=args.fmt,
            )
            return 0
        if args.command == "validate":
            ok = validate_slices(
                args.slices_input,
                strategy=args.strategy,
                basic=args.basic,
                check_duplicates=args.check_duplicates,
                graph_rank_check=not args.no_graph_rank_check,
            )
            return 0 if ok else 1
        if args.command == "canonicalize":
            canonicalize_slices(
                args.slices_input,
                output_file=args.output,
                strategy=args.strategy,
            )
            return 0
    except (SLICESError, FileNotFoundError, ValueError, ImportError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Unexpected failure: {exc}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
