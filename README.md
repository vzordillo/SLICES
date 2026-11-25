# SLICES

[![Tests](https://github.com/vzordillo/SLICES/actions/workflows/tests.yml/badge.svg)](https://github.com/vzordillo/SLICES/actions/workflows/tests.yml)
[![Release](https://img.shields.io/badge/release-v4.1.0-blue)](https://github.com/vzordillo/SLICES/releases/tag/v4.1.0)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: LGPL-2.1](https://img.shields.io/badge/license-LGPL--2.1-green)](LICENSE)

**SLICES v4.1** (*Simplified Line-Input Crystal-Encoding System*) is an invertible, translation-, rotation-, and permutation-invariant text representation for three-dimensional periodic crystal structures. It encodes crystals as labeled quotient-graph token sequences with space-group prefixes and reconstructs 3D atomic structures via bundled GFN-FF topology targets, ZL\* lattice optimization, and NequIP-OAM force-field relaxation.

[Paper (*Nat. Commun.* 2023)](https://www.nature.com/articles/s41467-023-42870-7) · [SLICES-PLUS (arXiv:2410.22828)](https://arxiv.org/abs/2410.22828) · [Online Converter (Hugging Face)](https://huggingface.co/spaces/xiaohang07/SLICES) · [Datasets (Figshare)](https://doi.org/10.6084/m9.figshare.22707472)

![SLICES Architecture Overview](docs/figure_intro.png)

## Highlights

- **Strategy-4 Space-Group Encoding:** Encodes CIF/POSCAR/JSON crystals across Strategies 1–4 (default Strategy 4 with 230 space-group tokens), primitive-cell pre-reduction, seeded permutation augmentation, and canonicalization.
- **Exact Topological Recovery & Validation:** Exact integer Smith Normal Form (SNF) lattice-basis fallback rescues unimodular 3D nets, tolerant ZL\* symmetry classification preserves crystallographic constraints, and `check_SLICES` enforces full-rank 3D lattice and cocycle bases.
- **Bundled GFN-FF & Multi-MLIP Relaxation:** Runs an in-memory open-source GFN-FF topology engine on Linux x86\_64 paired with `NequIP-OAM` (`auto` -> CPU `nequip-s+l`; CUDA `nequip-m+l` / `nequip-l`) plus optional adapters for `chgnet`, `mattersim`, `orbv3`, `mace`, and `m3gnet`.
- **Opt-In Lorentz Mixing & Robust Recovery:** `lj_mixing="lorentz"` boosts space-group preservation with zero speed penalty, and `robust_SLICES2structure` (`slices decode --robust`) adds multi-stage energy-selected recovery decoding.
- **Zero-Overhead `slices` CLI:** Subcommands for `encode`, `validate`, `canonicalize`, and `decode` with stdin/stdout piping and lazy force-field loading.

## Installation

Requires **Python 3.10+** (Linux x86\_64 recommended; includes bundled `libgfnff.so`). Install with [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/vzordillo/SLICES.git
cd SLICES

# Choose one PyTorch build: cpu, cu126 (up to RTX 40), or cu128 (RTX 50 / Blackwell)
# Add --extra oeq alongside cu126/cu128 for accelerated CUDA NequIP kernels
# Outside China, prefix with UV_DEFAULT_INDEX=https://pypi.org/simple if re-resolving
uv sync --extra cpu
source .venv/bin/activate

# Pre-compile and cache default NequIP-OAM weights (~/.cache/slices/nequip)
python -m slices.relax_backends --prepare

# Verify bundled GFN-FF, NequIP config, CLI, and quick round-trip
python tools/validate_installation.py --quick
```

<details>
<summary>Alternative installs (pip, non-Linux xtb fallback, legacy Docker / SLURM)</summary>

- **Editable / library install (`pip` or `uv pip`):** `uv pip install -e .` (or `uv pip install slices --torch-backend=auto`).
- **macOS / Windows native:** Encoding, validation, canonicalization, and optional MLIP adapters work natively. Decoding requires building `xtb_noring_nooutput_nostdout_noCN` and setting `SLICES_XTB_PATH`. Set `SLICES_FORCE_LOCAL=1` to bypass SLURM detection in batch helpers.
- **Legacy Docker / SLURM:** Older container files remain under [Dockerfile/](Dockerfile/Dockerfile) and [rundocker.sh](rundocker.sh) for reproducing pre-v4 PBS/SLURM workflows.

</details>

## Quickstart

### Python API

```python
from pymatgen.core.structure import Structure
from slices import SLICES, check_SLICES

original = Structure.from_file("examples/NdSiRu.cif")

# Default relax_model="auto" resolves to CPU nequip-s+l (pass relax_model=None for encode-only)
backend = SLICES()
slices_str = backend.structure2SLICES(original)
assert check_SLICES(slices_str, strategy=4)

reconstructed, energy_per_atom = backend.SLICES2structure(slices_str)
print(f"{reconstructed.composition.reduced_formula}: {energy_per_atom:.4f} eV/atom")

# Opt-in upgrades: Lorentz-Berthelot LJ mixing, multi-stage robust decode, and GPU / optional MLIPs
lorentz_backend = SLICES(lj_mixing="lorentz")
robust_struct, robust_e = backend.robust_SLICES2structure(slices_str, n_starts=3, seed=0)
# Set SLICES_DEVICE=cuda for GPU relaxation (e.g., relax_model="nequip-m+l", "nequip-l", "chgnet", "mace")
```

### Command-Line Interface (`slices`)

```bash
slices encode examples/NdSiRu.cif -o NdSiRu.slices --strategy 4 --graph-method econnn
slices validate NdSiRu.slices --check-duplicates
slices canonicalize NdSiRu.slices -o NdSiRu.canon.slices
slices decode NdSiRu.slices -o reconstructed.cif --relax-model auto
slices decode NdSiRu.slices -o reconstructed_robust.cif --robust --seed 0
```

## Benchmarks (`v4.1`)

Full evaluation across **MP-20** (`N = 2,383`, `econnn`), crystal-system-stratified **MP-21-40** (`N = 1,000 / 4,454`, `crystalnn`), and **QMOF-21-40** (`N = 339` MOFs, `econnn`). GPU runs executed on `2x RTX PRO 6000 Blackwell` (`aotinductor-oeq` for NequIP):

| Dataset (`N`) | Configuration | Decoded (`ok`) | Strict Match | Loose Match | SG Match | Med `\|E_form - DFT\|` | Wall Time |
|---|---|---:|---:|---:|---:|---:|---:|
| **MP-20** (`2,383`) | CPU `nequip-s+l` (`default`) | `99.92%` | `94.04%` | `96.22%` | `62.69%` | `0.0255 eV/at` | `193.6 s` |
| **MP-20** (`2,383`) | CPU `nequip-s+l` (`lorentz`) | `99.92%` | `93.96%` | `96.39%` | **`65.55%`** | `0.0256 eV/at` | `193.4 s` |
| **MP-20** (`2,383`) | CUDA `nequip-m+l` (`oeq`) | `99.92%` | **`95.09%`** | **`96.43%`** | `64.16%` | `0.0217 eV/at` | **`180.6 s`** |
| **MP-20** (`2,383`) | CUDA `chgnet 0.4.2` | `99.92%` | `94.17%` | `96.35%` | `60.76%` | **`0.0186 eV/at`**\* | `203.1 s` |
| **MP-21-40** (`1,000`) | CUDA `nequip-s+l` (`default`) | `99.40%` | **`90.10%`** | **`93.70%`** | `47.60%`† | `0.4024 eV/at` | `635.7 s` |
| **QMOF-21-40** (`339`) | CUDA `nequip-s+l` (`lorentz`) | `89.68%` | `3.54%` | `8.26%` | `9.73%` | — | `414.8 s` |

*\*`chgnet` achieves `0.0521 eV/atom` MAE (`0` outliers) due to MPtrj PBE+U alignment with `chemPotMP.json`. †`lorentz` raises MP-21-40 SG match to `48.80%` (`p = 0.058`).*  
See the full statistical analyses in [AB_COMPARISON_REPORT.md](benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md) and [EXTENDED_BENCHMARK_REPORT.md](benchmark/v4_1_extended/EXTENDED_BENCHMARK_REPORT.md).

## Testing & Documentation

The full suite currently passes **`297 passed, 5 skipped`** (the 5 skips are uninstalled optional MLIP packages):

```bash
ruff check src/ examples/ tools/ tests/
pytest tests/
```

| Resource | Description |
|---|---|
| [Documentation Index](docs/README.md) | Complete guide to docs, API references, and benchmark archives |
| [Technical Architecture](TECHNICAL.md) | Encoding strategies, quotient-net embedding, GFN-FF, ZL\*, and MLIP backends |
| [Changelog](CHANGELOG.md) | Release history from v1.0 through v4.1.0 and latest updates |
| [Core API Reference](docs/api/API_CORE.md) | `SLICES`, `check_SLICES`, exceptions, and module-by-module API docs |
| [v4.1 CPU A/B Report](benchmark/v4_1_experimental/AB_COMPARISON_REPORT.md) | Paired MP-20 (`2,383`) & cRNN (`39,244`) statistical comparison vs v4.0.2 |
| [v4.1 Extended GPU Report](benchmark/v4_1_extended/EXTENDED_BENCHMARK_REPORT.md) | Multi-model GPU MP-20, stage breakdown, QMOF-21-40, and MP-21-40 benchmarks |

## Citation & License

If you use SLICES or SLICES-PLUS in academic work, please cite:

```bibtex
@article{xiao2023invertible,
  title={An invertible, invariant crystal representation for inverse design of solid-state materials using generative deep learning},
  author={Xiao, Hang and Li, Rong and Shi, Xiaoyang and Chen, Yan and Zhu, Liangliang and Chen, Xi and Wang, Lei},
  journal={Nature Communications},
  volume={14},
  number={1},
  pages={7027},
  year={2023},
  publisher={Nature Publishing Group UK London}
}

@misc{wang2024slicespluscrystalrepresentationleveraging,
  title={SLICES-PLUS: A Crystal Representation Leveraging Spatial Symmetry},
  author={Baoning Wang and Zhiyuan Xu and Zhiyu Han and Qiwen Nie and Hang Xiao and Gang Yan},
  year={2024},
  eprint={2410.22828},
  archivePrefix={arXiv},
  primaryClass={physics.comp-ph},
  url={https://arxiv.org/abs/2410.22828}
}
```

Licensed under **LGPL-2.1** ([LICENSE](LICENSE)); the bundled GFN-FF library (`src/slices/_vendor/gfnff`) is licensed under **LGPL-3.0** ([src/slices/_vendor/gfnff_extra/LICENSE](src/slices/_vendor/gfnff_extra/LICENSE)). Originally authored by Hang Xiao ([xiaohang007/SLICES](https://github.com/xiaohang007/SLICES) · [Hugging Face Space](https://huggingface.co/spaces/xiaohang07/SLICES)).
