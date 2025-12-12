# Changelog

All notable changes to SLICES will be documented in this file.

## [Unreleased]

### Added
- Cross-platform compatibility (Windows/macOS/Linux)
- Decoding enhancements module with cycle basis optimization
- References to LLL algorithm for lattice basis computation
- Test suite
- OS-agnostic path handling and file operations

### Changed
- Error handling with specific exception types
- Cycle basis selection implementation
- Subprocess calls updated for cross-platform compatibility

### Fixed
- Windows executable detection for XTB binary
- Path handling using os.path.join() instead of string concatenation
- File operations using shutil instead of Unix commands

## [2025-12-12]

### Added
- Benchmark documentation and plotting scripts
- OS-agnostic changes documentation
- Windows compatibility report

## [2025-12-04]

### Added
- Decoding enhancements module
- Cycle basis optimizer
- Adaptive timeout calculation

### Changed
- is_integral() method with tolerance support
- Error handling throughout codebase

## [2025-11-27]

### Added
- macOS compatibility
- MLIP integration (CHGNet, MatterSim, ORBv3)
- XTB binary support for macOS ARM64

### Changed
- M3GNet set as default MLIP model
- MatGL support removed (model download/cache issues)

### Changed
- Cross-platform timeout handling
- Error messages with more specific information

## [2025-03-01]

### Added
- Symmetry group encoding in SLICES strings
- SLICES-PLUS features
- Flash Attention support for MatterGPT

### Changed
- MatterGPT architecture updates
- Performance improvements

## [2024-08-09]

### Added
- Initial public release
- Core encoding/decoding functionality
- MatterGPT integration
- Documentation

