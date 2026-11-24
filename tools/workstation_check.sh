#!/bin/bash
# One-command SLICES v4.0.2 environment, model compilation, and relaxation benchmark checks
# on a CPU or GPU workstation. Everything is written to $OUT (default ~/slices_ws_test/<date_time>).
#
# Options (environment variables):
#   EXTRAS                  uv extras to install            (default: "--extra cu128 --extra oeq")
#   BENCH_N                 number of SLICES to benchmark   (default: 32)
#   OUT                     output folder
#   UV_PROJECT_ENVIRONMENT  environment location            (uv default: <repo>/.venv)
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
OUT=${OUT:-$HOME/slices_ws_test/$(date +%Y%m%d_%H%M%S)}
EXTRAS=${EXTRAS:-"--extra cu128 --extra oeq"}
BENCH_N=${BENCH_N:-32}
mkdir -p "$OUT"
exec > >(tee -a "$OUT/summary.log") 2>&1

log() { echo "[$(date +%T)] $*"; }

# Background monitors: GPU memory/utilization and host memory every 5 s.
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=timestamp,index,memory.used,memory.total,utilization.gpu \
             --format=csv -l 5 > "$OUT/gpu.csv" 2>/dev/null &
  GPU_MON=$!
fi
(
  while true; do
    echo "$(date +%T) $(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)MB_available"
    sleep 5
  done
) > "$OUT/host_mem.log" &
MEM_MON=$!
trap 'kill ${GPU_MON:-} $MEM_MON 2>/dev/null' EXIT

# step <name> <timeout seconds> <command...>: runs with a time limit, logs to $OUT/<name>.log.
step() {
  local name=$1 limit=$2
  shift 2
  log "START $name"
  local t0
  t0=$(date +%s)
  timeout "$limit" bash -c "$*" > "$OUT/$name.log" 2>&1
  local rc=$?
  log "END   $name: exit=$rc, $(( $(date +%s) - t0 )) s"
  return $rc
}

log "repo $REPO, branch $(git -C "$REPO" branch --show-current), commit $(git -C "$REPO" rev-parse --short HEAD)"
log "uv $(uv --version 2>&1)"
if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv 2>&1 | sed 's/^/    /'
else
  log "nvidia-smi not found (no NVIDIA driver visible)"
fi

# 1. Environment sync and PyTorch / OpenEquivariance inspection.
cd "$REPO" || exit 1
if ! step uv_sync 3600 "uv sync $EXTRAS --locked"; then
  log "uv sync with '$EXTRAS' failed; retrying without --extra oeq"
  EXTRAS=$(echo "$EXTRAS" | sed 's/--extra oeq//')
  step uv_sync_retry 3600 "uv sync $EXTRAS --locked" || { log "uv sync failed, see uv_sync*.log"; exit 1; }
fi
source "${UV_PROJECT_ENVIRONMENT:-$REPO/.venv}/bin/activate"
export PYTHONWARNINGS=ignore
step torch_info 300 "python -c \"
import importlib.util, torch
print('torch', torch.__version__, 'CUDA build', torch.version.cuda, 'cuda available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('GPU', torch.cuda.get_device_name(0), 'capability', torch.cuda.get_device_capability(0))
print('openequivariance importable', importlib.util.find_spec('openequivariance') is not None)
\""
sed 's/^/    /' "$OUT/torch_info.log"

# 2. Compile and cache NequIP models (default CPU path and opt-in GPU path).
step prepare_cpu 1800 "python -m slices.relax_backends --prepare"
step prepare_gpu 3600 "SLICES_DEVICE=cuda python -m slices.relax_backends --prepare --relax-model nequip-l"
grep -h -E "relax_model=|compiled|failed|falling back|test relaxation" "$OUT"/prepare_*.log | sed 's/^/    /'

# 3. Force-field decoding benchmark on real MP-20 non-metal SLICES (single process).
step bench_cpu 3600 "python examples/3.benchmark_relax_models.py --n $BENCH_N --models auto nequip-m+l"
step bench_gpu 3600 "SLICES_DEVICE=cuda python examples/3.benchmark_relax_models.py --n $BENCH_N --models nequip-l nequip-s+l"
grep -h -A4 "^summary" "$OUT"/bench_*.log | sed 's/^/    /'

# 4. Peak resource summary.
if [ -s "$OUT/gpu.csv" ]; then
  awk -F', ' 'NR>1 {gsub(/ MiB/,"",$3); if ($3+0>m) m=$3+0} END {print "    peak GPU memory used: " m " MiB"}' "$OUT/gpu.csv"
fi
awk '{gsub(/MB_available/,"",$2); if (min=="" || $2+0<min) min=$2+0} END {print "    lowest host MemAvailable: " min " MB"}' "$OUT/host_mem.log"
log "done; results in $OUT"
