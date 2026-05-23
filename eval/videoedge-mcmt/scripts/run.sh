#!/usr/bin/env bash
#
# Drive one paired (DSF, Argo) videoedge-mcmt cell.
#
#   ./run.sh <cameras> <duration_s> <reps>
#
# For each rep, submits a DSF run and an Argo run sequentially (cluster
# idle between each — preflight enforced), waits for completion, harvests
# their report.json files, runs the correctness diff, and appends a row
# to results/<cell>/summary.csv.
#
# CSV columns: rep, system, run_name, phase, makespan_s, wall_s, report_ok
set -euo pipefail

CAM="${1:-4}"
DUR="${2:-60}"
REPS="${3:-3}"
TIMEOUT_S="${TIMEOUT_S:-1200}"

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"

CELL="n${CAM}-d${DUR}"
OUTDIR="$ROOT/results/$CELL"
mkdir -p "$OUTDIR"
SUM="$OUTDIR/summary.csv"
[[ -f "$SUM" ]] || echo "rep,system,run_name,phase,makespan_s,wall_s,report_ok" > "$SUM"

green(){ printf '\033[32m%s\033[0m\n' "$*"; }
red()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }

# Render+apply both templates once.
python3 "$ROOT/dsf/render.py" --cameras "$CAM" --duration "$DUR" --scheduler heft \
    --name "vemcmt-n${CAM}-d${DUR}-heft" -o "/tmp/dsf-${CELL}.yml"
python3 "$ROOT/argo/render.py" --cameras "$CAM" --duration "$DUR" \
    --name "vemcmt-n${CAM}-d${DUR}-argo" -o "/tmp/argo-${CELL}.yml"
kubectl apply -f "/tmp/dsf-${CELL}.yml" >/dev/null
kubectl apply -f "/tmp/argo-${CELL}.yml" >/dev/null

# Preflight: cluster idle. Reuse two-hop's check.
PREFLIGHT="$REPO/eval/two-hop/preflight-idle.sh"

wait_dsf() {
    local name="$1"; local end=$(( $(date +%s) + TIMEOUT_S ))
    while [[ $(date +%s) -lt $end ]]; do
        local phase
        phase=$(kubectl -n dsf-system get odag "$name" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        case "$phase" in Succeeded|Failed) echo "$phase"; return ;; esac
        sleep 3
    done
    echo "Timeout"
}
wait_argo() {
    local name="$1"; local end=$(( $(date +%s) + TIMEOUT_S ))
    while [[ $(date +%s) -lt $end ]]; do
        local phase
        phase=$(kubectl -n argo get workflow "$name" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        case "$phase" in Succeeded|Failed|Error) echo "$phase"; return ;; esac
        sleep 3
    done
    echo "Timeout"
}

for r in $(seq 1 "$REPS"); do
    green "==> cell $CELL rep $r/$REPS"
    "$PREFLIGHT" || { red "preflight not idle, skipping rep $r"; continue; }

    # --- DSF leg ---
    start=$(date +%s)
    dsf_name=$("$REPO/bin/dsf" odag run "vemcmt-n${CAM}-d${DUR}-heft" -n dsf-system \
        | sed -nE 's/^Created run ([^ ]+).*/\1/p')
    dsf_phase=$(wait_dsf "$dsf_name")
    dsf_wall=$(( $(date +%s) - start ))
    dsf_makespan=$(kubectl -n dsf-system get odag "$dsf_name" -o jsonpath='{.status.makespan}' 2>/dev/null || echo "")
    cp -f /var/lib/dsf-workloads/reports/$dsf_name/report.json "$OUTDIR/dsf-rep${r}.json" 2>/dev/null \
        || cp -f /shared/dsf-outputs/reports/$dsf_name/report.json "$OUTDIR/dsf-rep${r}.json" 2>/dev/null \
        || true

    # --- Argo leg ---
    start=$(date +%s)
    argo_name=$(kubectl -n argo create -f <(cat <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: vemcmt-n${CAM}-d${DUR}-argo-
  namespace: argo
spec:
  workflowTemplateRef:
    name: vemcmt-n${CAM}-d${DUR}-argo
EOF
) | awk '{print $1}' | sed 's|workflow.argoproj.io/||')
    argo_phase=$(wait_argo "$argo_name")
    argo_wall=$(( $(date +%s) - start ))
    cp -f /var/lib/dsf-workloads/reports/$argo_name/report.json "$OUTDIR/argo-rep${r}.json" 2>/dev/null || true

    # --- Correctness diff ---
    report_ok="?"
    if [[ -f "$OUTDIR/dsf-rep${r}.json" && -f "$OUTDIR/argo-rep${r}.json" ]]; then
        if python3 "$HERE/verify_reports.py" \
                "$OUTDIR/dsf-rep${r}.json" "$OUTDIR/argo-rep${r}.json" > "$OUTDIR/diff-rep${r}.log" 2>&1; then
            report_ok=true
        else
            report_ok=false
        fi
    fi

    echo "${r},dsf,${dsf_name},${dsf_phase},${dsf_makespan:-?},${dsf_wall},${report_ok}" >> "$SUM"
    echo "${r},argo,${argo_name},${argo_phase},?,${argo_wall},${report_ok}" >> "$SUM"
    green "rep $r done: dsf=${dsf_phase}/${dsf_makespan:-?}s argo=${argo_phase}/${argo_wall}s diff=${report_ok}"
done

green "Done. Summary in $SUM"
