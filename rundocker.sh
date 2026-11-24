#!/bin/bash
# Launch the SLICES Docker container with SLURM initialized via entrypoint_set_cpus.sh.
# Override defaults via environment variables:
#   SLICES_DATA_DIR  Host directory mounted at /crystal (default: current directory)
#   SLICES_IMAGE     Docker image to run (default: xiaohang07/slices:v12)
#   SLICES_SHM_SIZE  Shared memory size (default: 0.5gb)

set -euo pipefail

SLICES_DATA_DIR="${SLICES_DATA_DIR:-${PWD}}"
SLICES_IMAGE="${SLICES_IMAGE:-xiaohang07/slices:v12}"
SLICES_SHM_SIZE="${SLICES_SHM_SIZE:-0.5gb}"

docker run -it -h workq --shm-size="${SLICES_SHM_SIZE}" --gpus all \
    -v "${SLICES_DATA_DIR}:/crystal" -w /crystal \
    "${SLICES_IMAGE}" /crystal/entrypoint_set_cpus.sh
