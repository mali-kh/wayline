#!/usr/bin/env bash
#
# Submit 5 ODAGs staggered over time to test HEFT scheduling
# under contention. Uses kubectl (or: wayline apply -f <file>).
#
# Usage:
#   ./submit.sh            # submit all 5 with default delays
#   ./submit.sh --dry-run  # print what would happen without applying
#
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

# Delays in seconds between submissions (cumulative wait from previous)
DELAYS=(0 2 4 6 8)
FILES=(
  odag-1-video-transcode.yml
  odag-2-ml-training.yml
  odag-3-etl-wide.yml
  odag-4-sensor-fusion.yml
  odag-5-image-batch.yml
)
NAMES=(
  video-transcode
  ml-training
  etl-wide
  sensor-fusion
  image-batch
)

# ── cleanup helper ──────────────────────────────────────────────
cleanup() {
  echo ""
  echo "=== Cleaning up previous runs ==="
  for name in "${NAMES[@]}"; do
    if kubectl get odag -n wl-system "$name" &>/dev/null; then
      echo "  deleting odag/$name ..."
      kubectl delete odag -n wl-system "$name" --ignore-not-found
    fi
  done
  # wait for pods to terminate
  echo "  waiting for leftover pods to terminate..."
  sleep 3
  echo "  cleanup done"
  echo ""
}

# ── main ────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════╗"
echo "║   Multi-ODAG HEFT Scheduling Test               ║"
echo "║   5 ODAGs submitted over ~55 seconds             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

if $DRY_RUN; then
  echo "[dry-run mode]"
  echo ""
fi

# clean previous runs unless dry-run
$DRY_RUN || cleanup

elapsed=0
for i in "${!FILES[@]}"; do
  delay=${DELAYS[$i]}
  file=${FILES[$i]}
  name=${NAMES[$i]}

  if (( delay > 0 )); then
    echo "⏳ waiting ${delay}s before next submission..."
    if ! $DRY_RUN; then
      sleep "$delay"
    fi
    elapsed=$((elapsed + delay))
  fi

  echo "[$elapsed s] Submitting $name  ($file)"
  if ! $DRY_RUN; then
    kubectl apply -f "$DIR/$file"
  fi
done

echo ""
echo "All 5 ODAGs submitted."
echo ""

if ! $DRY_RUN; then
  echo "=== Monitoring ==="
  echo "  kubectl get odags -n wl-system -w"
  echo "  kubectl get pods -n wl-system -l app=wl-odag -w"
  echo ""
  echo "=== Quick status loop (Ctrl-C to stop) ==="
  while true; do
    echo "--- $(date +%H:%M:%S) ---"
    kubectl get odags -n wl-system -o custom-columns=\
NAME:.metadata.name,PHASE:.status.phase,SCHEDULER:.spec.scheduler,MAKESPAN:.status.makespan,AGE:.metadata.creationTimestamp \
      2>/dev/null || true
    echo ""

    # check if all succeeded
    total=$(kubectl get odags -n wl-system --no-headers 2>/dev/null | wc -l)
    succeeded=$(kubectl get odags -n wl-system --no-headers 2>/dev/null | grep -c "Succeeded" || true)
    failed=$(kubectl get odags -n wl-system --no-headers 2>/dev/null | grep -c "Failed" || true)

    if (( succeeded + failed == total && total == 5 )); then
      echo "All ODAGs finished: $succeeded succeeded, $failed failed."
      break
    fi

    sleep 5
  done
fi
