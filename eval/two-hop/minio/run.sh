#!/usr/bin/env bash
#
# E0 MinIO baseline sweep driver. Symmetric to dsf/run.sh.
#
# For each cell:
#   1. For each rep:
#      a. preflight-idle.sh
#      b. wipe the bucket object (idempotent fresh start)
#      c. kubectl apply paired Jobs (producer + consumer, both created
#         at once — consumer polls)
#      d. wait until both Jobs complete
#      e. harvest pod logs + pod API timestamps
#      f. delete the Jobs (TTL also reaps them)
#
# Env knobs:
#   N         reps per cell (default 20; SMOKE=1 overrides to 2)
#   TIMEOUT   per-run timeout in seconds (default 300)
#   ONLY      cell tag filter (e.g. ONLY="same-10mb")
#
set -euo pipefail

E0_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NS=e0-bench
N="${N:-20}"
TIMEOUT="${TIMEOUT:-300}"
[[ "${SMOKE:-0}" == "1" ]] && N=2

CELLS_FILE="${E0_DIR}/cells.txt"
RESULTS_ROOT="${E0_DIR}/results/minio"
mkdir -p "$RESULTS_ROOT"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

if ! kubectl -n "$NS" get deploy/minio >/dev/null 2>&1; then
  red "MinIO is not deployed in namespace $NS — run ./deploy-minio.sh first"
  exit 2
fi

render_jobs() {
  local run_name=$1 bytes=$2 pnode=$3 cnode=$4 cell_dir=$5
  local out="${cell_dir}/${run_name}.jobs.yml"
  E0_RUN_NAME="$run_name" \
  E0_BYTES="$bytes" \
  E0_PRODUCER_NODE="$pnode" \
  E0_CONSUMER_NODE="$cnode" \
  envsubst < "${E0_DIR}/minio/job.yml.tpl" > "$out"
  echo "$out"
}

wait_for_jobs() {
  local run_name=$1
  local end=$(( $(date +%s) + TIMEOUT ))
  while [[ $(date +%s) -lt $end ]]; do
    local p_done c_done
    p_done=$(kubectl -n "$NS" get job "${run_name}-producer" -o jsonpath='{.status.succeeded}' 2>/dev/null || echo 0)
    c_done=$(kubectl -n "$NS" get job "${run_name}-consumer" -o jsonpath='{.status.succeeded}' 2>/dev/null || echo 0)
    p_failed=$(kubectl -n "$NS" get job "${run_name}-producer" -o jsonpath='{.status.failed}' 2>/dev/null || echo 0)
    c_failed=$(kubectl -n "$NS" get job "${run_name}-consumer" -o jsonpath='{.status.failed}' 2>/dev/null || echo 0)
    if [[ "${p_failed:-0}" != "0" || "${c_failed:-0}" != "0" ]]; then
      echo "Failed"
      return 1
    fi
    if [[ "${p_done:-0}" == "1" && "${c_done:-0}" == "1" ]]; then
      echo "Succeeded"
      return 0
    fi
    sleep 1
  done
  echo "Timeout"
  return 1
}

harvest_run() {
  local run_name=$1 cell_dir=$2
  local out_json="${cell_dir}/${run_name}.json"

  # The Job's pod has labels { app=two-hop, component=producer|consumer, e0-run=<run> }.
  local prod_pod cons_pod
  prod_pod=$(kubectl -n "$NS" get pods -l "e0-run=${run_name},component=producer" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
  cons_pod=$(kubectl -n "$NS" get pods -l "e0-run=${run_name},component=consumer" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

  if [[ -z "$prod_pod" || -z "$cons_pod" ]]; then
    yellow "[harvest/$run_name] missing pod names"
    return 1
  fi

  local prod_line cons_line
  prod_line="$(kubectl -n "$NS" logs "$prod_pod" 2>/dev/null | grep -F 'DSF_E0_TIMESTAMPS ' | tail -1 | sed 's/^DSF_E0_TIMESTAMPS //' || true)"
  cons_line="$(kubectl -n "$NS" logs "$cons_pod" 2>/dev/null | grep -F 'DSF_E0_TIMESTAMPS ' | tail -1 | sed 's/^DSF_E0_TIMESTAMPS //' || true)"

  local prod_started prod_finished cons_started cons_finished
  prod_started=$(kubectl -n "$NS" get pod "$prod_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}'  2>/dev/null || true)
  prod_finished=$(kubectl -n "$NS" get pod "$prod_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null || true)
  cons_started=$(kubectl -n "$NS" get pod "$cons_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}'  2>/dev/null || true)
  cons_finished=$(kubectl -n "$NS" get pod "$cons_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null || true)

  python3 - "$out_json" <<EOF
import json, sys
out = sys.argv[1]
record = {
    "run_name": "$run_name",
    "producer_pod": "$prod_pod",
    "consumer_pod": "$cons_pod",
    "producer_log": json.loads('''$prod_line''') if '''$prod_line''' else None,
    "consumer_log": json.loads('''$cons_line''') if '''$cons_line''' else None,
    "pod_api": {
        "producer_started":  "$prod_started"  or None,
        "producer_finished": "$prod_finished" or None,
        "consumer_started":  "$cons_started"  or None,
        "consumer_finished": "$cons_finished" or None,
    },
}
with open(out, "w") as f:
    json.dump(record, f, indent=2, default=str)
print(f"[harvest] wrote {out}")
EOF
}

wipe_object() {
  local key=$1
  # Use the existing MinIO pod to issue an mc rm. Idempotent — ignores
  # "object not found".
  kubectl -n "$NS" exec deploy/minio -- sh -c "
    mc alias set local http://minio:9000 e0admin e0adminpw >/dev/null 2>&1
    mc rm --force local/e0-bench/${key} 2>/dev/null || true
  " >/dev/null 2>&1 || true
}

run_cell() {
  local colocation=$1 label=$2 bytes=$3 pnode=$4 cnode=$5
  local payload_tag
  payload_tag="$(echo "$label" | tr '[:upper:]' '[:lower:]')"
  local cell_tag="${colocation}-${payload_tag}"
  if [[ -n "${ONLY:-}" ]] && ! echo " ${ONLY} " | grep -qF " $cell_tag "; then
    yellow "[skip] $cell_tag (ONLY filter)"
    return 0
  fi

  local cell_dir="${RESULTS_ROOT}/${cell_tag}"
  mkdir -p "$cell_dir"

  green ""
  green "==================================================="
  green " MinIO cell: $cell_tag  bytes=$bytes  $pnode -> $cnode"
  green "==================================================="

  local existing
  existing=$(ls -1 "$cell_dir"/*.json 2>/dev/null | wc -l)
  if (( existing >= N )); then
    yellow "[$cell_tag] $existing runs already present, skipping"
    return 0
  fi

  for i in $(seq 1 "$N"); do
    if ! "${E0_DIR}/preflight-idle.sh"; then
      red "[$cell_tag] preflight failed before rep $i — aborting cell"
      return 1
    fi

    local run_name
    run_name="e0-minio-${cell_tag}-$(date +%s%N | tail -c 9)"
    if [[ -f "${cell_dir}/${run_name}.json" ]]; then
      yellow "[$cell_tag/$i] $run_name already harvested, skipping"
      continue
    fi

    wipe_object "${run_name}/payload"

    local jobs_yml
    jobs_yml="$(render_jobs "$run_name" "$bytes" "$pnode" "$cnode" "$cell_dir")"
    kubectl apply -f "$jobs_yml" >/dev/null

    echo "[$cell_tag/$i] run=$run_name"
    local phase
    phase=$(wait_for_jobs "$run_name") || true
    echo "[$cell_tag/$i] phase=$phase"

    sleep 1
    harvest_run "$run_name" "$cell_dir" || yellow "[$cell_tag/$i] harvest had issues"

    # Delete the Jobs so the next iteration starts clean. The TTL would
    # also reap them, but explicit delete keeps preflight clean.
    kubectl -n "$NS" delete jobs "${run_name}-producer" "${run_name}-consumer" --ignore-not-found --wait=false >/dev/null 2>&1 || true
  done
}

while IFS=, read -r colocation label bytes pnode cnode; do
  [[ "$colocation" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$colocation" ]] && continue
  run_cell "$colocation" "$label" "$bytes" "$pnode" "$cnode" || red "cell failed: $colocation $label"
done < <(grep -v '^[[:space:]]*#' "$CELLS_FILE" | grep -v '^[[:space:]]*$')

green ""
green "MinIO sweep done. Results under $RESULTS_ROOT"
