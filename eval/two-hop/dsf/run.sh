#!/usr/bin/env bash
#
# E0 DSF sweep driver.
#
# For each cell defined in ../cells.txt:
#   1. Render the ODAGTemplate from odag.yml.tpl via envsubst.
#   2. kubectl apply.
#   3. For each of N reps:
#        a. ../preflight-idle.sh   (abort cell on failure)
#        b. dsf odag run <template-name>
#        c. wait for phase = Succeeded
#        d. harvest producer + consumer log lines and pod timestamps
#        e. write results/dsf/<cell>/<run-name>.json
#   4. Build per-cell summary.csv.
#
# Resumable: skips runs whose .json already exists in the cell dir.
#
# Env knobs:
#   N         reps per cell (default 20; SMOKE=1 overrides to 2)
#   TIMEOUT   per-run timeout in seconds (default 300)
#   ONLY      space-separated cell tags to run (e.g. ONLY="same-10mb")
#
set -euo pipefail

E0_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DSF="${REPO_ROOT:-$(cd "$E0_DIR/../.." && pwd)}/bin/dsf"
NS="${NS:-dsf-system}"
N="${N:-20}"
TIMEOUT="${TIMEOUT:-300}"
[[ "${SMOKE:-0}" == "1" ]] && N=2

CELLS_FILE="${E0_DIR}/cells.txt"
RESULTS_ROOT="${E0_DIR}/results/dsf"
mkdir -p "$RESULTS_ROOT"

red()   { printf '\033[31m%s\033[0m\n' "$*" >&2; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

if ! [[ -x "$DSF" ]]; then
  red "dsf CLI not found at $DSF — build it (make build) before running E0"
  exit 2
fi

render_template() {
  local cell_tag=$1 colocation=$2 label=$3 bytes=$4 pnode=$5 cnode=$6
  local out="${E0_DIR}/results/dsf/${cell_tag}/template.yml"
  mkdir -p "$(dirname "$out")"
  E0_TEMPLATE_NAME="e0-dsf-${cell_tag}" \
  E0_COLOCATION="$colocation" \
  E0_PAYLOAD_LABEL="$label" \
  E0_BYTES="$bytes" \
  E0_PRODUCER_NODE="$pnode" \
  E0_CONSUMER_NODE="$cnode" \
  envsubst < "${E0_DIR}/dsf/odag.yml.tpl" > "$out"
  echo "$out"
}

wait_for_phase() {
  local name=$1
  local end=$(( $(date +%s) + TIMEOUT ))
  while [[ $(date +%s) -lt $end ]]; do
    local phase
    phase=$(kubectl -n "$NS" get odag "$name" -o jsonpath='{.status.phase}' 2>/dev/null || true)
    case "$phase" in
      Succeeded) echo "$phase"; return 0 ;;
      Failed)    echo "$phase"; return 1 ;;
    esac
    sleep 1
  done
  echo "Timeout"
  return 1
}

harvest_run() {
  # Args: run_name cell_dir
  local name=$1 cell_dir=$2
  local out_json="${cell_dir}/${name}.json"

  # Pull pod names from the ODAG status.
  local odag_json prod_pod cons_pod
  odag_json="$(kubectl -n "$NS" get odag "$name" -o json 2>/dev/null || echo '{}')"
  prod_pod="$(python3 -c '
import json, sys
d = json.loads(sys.argv[1])
for t in (d.get("status") or {}).get("tasks", []):
    if t.get("name") == "producer":
        print(t.get("podName",""))
        break
' "$odag_json")"
  cons_pod="$(python3 -c '
import json, sys
d = json.loads(sys.argv[1])
for t in (d.get("status") or {}).get("tasks", []):
    if t.get("name") == "consumer":
        print(t.get("podName",""))
        break
' "$odag_json")"

  if [[ -z "$prod_pod" || -z "$cons_pod" ]]; then
    yellow "[harvest/$name] missing pod names (prod=$prod_pod cons=$cons_pod)"
    return 1
  fi

  # Logs (each pod emits one DSF_E0_TIMESTAMPS line).
  local prod_line cons_line
  prod_line="$(kubectl -n "$NS" logs "$prod_pod" 2>/dev/null | grep -F 'DSF_E0_TIMESTAMPS ' | tail -1 | sed 's/^DSF_E0_TIMESTAMPS //' || true)"
  cons_line="$(kubectl -n "$NS" logs "$cons_pod" 2>/dev/null | grep -F 'DSF_E0_TIMESTAMPS ' | tail -1 | sed 's/^DSF_E0_TIMESTAMPS //' || true)"

  # Pod API timestamps (RFC3339).
  local prod_started prod_finished cons_started cons_finished
  prod_started=$(kubectl -n "$NS" get pod "$prod_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}'  2>/dev/null || true)
  prod_finished=$(kubectl -n "$NS" get pod "$prod_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null || true)
  cons_started=$(kubectl -n "$NS" get pod "$cons_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}'  2>/dev/null || true)
  cons_finished=$(kubectl -n "$NS" get pod "$cons_pod" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null || true)

  python3 - "$out_json" <<EOF
import json, sys
out = sys.argv[1]
record = {
    "run_name": "$name",
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
  green " DSF cell: $cell_tag  bytes=$bytes  $pnode -> $cnode"
  green "==================================================="

  local tpl_path tpl_name
  tpl_path="$(render_template "$cell_tag" "$colocation" "$label" "$bytes" "$pnode" "$cnode")"
  tpl_name="e0-dsf-${cell_tag}"
  kubectl apply -f "$tpl_path" >/dev/null

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

    local submit_out name
    submit_out="$("$DSF" odag run "$tpl_name" -n "$NS" 2>&1)" || {
      red "submit failed:"
      echo "$submit_out"
      return 1
    }
    name=$(printf '%s\n' "$submit_out" | sed -nE 's/^Created run ([^ ]+).*/\1/p')
    if [[ -z "$name" ]]; then
      red "[$cell_tag/$i] could not parse run name from:"
      echo "$submit_out"
      return 1
    fi

    if [[ -f "${cell_dir}/${name}.json" ]]; then
      yellow "[$cell_tag/$i] $name already harvested, skipping"
      continue
    fi

    echo "[$cell_tag/$i] run=$name"
    local phase
    phase=$(wait_for_phase "$name") || true
    echo "[$cell_tag/$i] phase=$phase"

    # Brief grace for any straggling status updates.
    sleep 2

    harvest_run "$name" "$cell_dir" || yellow "[$cell_tag/$i] harvest had issues"

    # Do NOT delete the ODAG — the controller's run-counter is derived
    # from the count of existing runs, and manual deletion causes the
    # next run to collide with run-001. retention.maxRuns + data.policy:
    # immediate already cap on-disk storage; old terminal ODAG resources
    # are cheap.
  done
}

# Read cells, run each.
while IFS=, read -r colocation label bytes pnode cnode; do
  [[ "$colocation" =~ ^[[:space:]]*# ]] && continue
  [[ -z "$colocation" ]] && continue
  run_cell "$colocation" "$label" "$bytes" "$pnode" "$cnode" || red "cell failed: $colocation $label"
done < <(grep -v '^[[:space:]]*#' "$CELLS_FILE" | grep -v '^[[:space:]]*$')

green ""
green "DSF sweep done. Results under $RESULTS_ROOT"
