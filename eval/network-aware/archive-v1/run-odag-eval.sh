#!/usr/bin/env bash
# Experiment 1A: ODAG makespan comparison (random vs HEFT)
#
# Runs the IoBT template N times with each scheduler, collecting:
#   - Makespan per run
#   - Task-to-node placement per run
#   - Per-task start/completion times
#   - Profiler state (for HEFT convergence analysis)
#
# Usage: ./eval/network-aware/run-odag-eval.sh [RUNS=15]
#
# Prerequisites:
#   - tc shaping active (./benchmarks/multi-odag-heft/setup-tc.sh)
#   - IoBT task images built and pushed to registry
#   - Templates applied:
#       kubectl apply -f eval/network-aware/odag-iobt/template-random.yml
#       kubectl apply -f eval/network-aware/odag-iobt/template-heft.yml

set -euo pipefail
cd "$(dirname "$0")/../.."

RUNS=${1:-15}
NS="dsf-system"
DSF="go run ./cmd/cli/"
RESULTS="eval/network-aware/results"
mkdir -p "$RESULTS"

CSV="$RESULTS/odag-makespan.csv"
echo "run,scheduler,odag_name,phase,makespan" > "$CSV"

run_template() {
    local template=$1
    local scheduler=$2
    local run_num=$3

    echo ""
    echo "[eval] ── $scheduler run $run_num/$RUNS ──────────────────────────"
    local odag_name
    odag_name=$($DSF odag run "$template" -n "$NS" 2>&1 | grep -oP 'Created run \K\S+')
    echo "[eval] Created: $odag_name"

    # Wait for completion (poll every 5s, timeout 10 min).
    local elapsed=0
    while true; do
        phase=$(kubectl get odag "$odag_name" -n "$NS" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
        if [[ "$phase" == "Succeeded" || "$phase" == "Failed" ]]; then
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        if (( elapsed % 30 == 0 )); then
            echo "[eval] ... waiting ($elapsed s, phase=$phase)"
        fi
        if (( elapsed >= 600 )); then
            echo "[eval] TIMEOUT: $odag_name"
            phase="Timeout"
            break
        fi
    done

    # Read makespan.
    local makespan
    makespan=$(kubectl get odag "$odag_name" -n "$NS" -o jsonpath='{.status.makespan}' 2>/dev/null || echo "0")
    echo "[eval] Result: phase=$phase makespan=${makespan}s"
    echo "$run_num,$scheduler,$odag_name,$phase,$makespan" >> "$CSV"

    # Save placement (task → node mapping).
    local placement_file="$RESULTS/${odag_name}-placement.txt"
    echo "# Placement for $odag_name ($scheduler, run $run_num)" > "$placement_file"
    kubectl get odag "$odag_name" -n "$NS" -o json 2>/dev/null | \
        python3 -c "
import json, sys
d = json.load(sys.stdin)
tasks = d.get('status', {}).get('tasks', [])
for t in tasks:
    name = t.get('name', '?')
    node = t.get('node', '?')
    phase = t.get('phase', '?')
    start = t.get('startTime', '')
    end = t.get('completionTime', '')
    print(f'{name:25s} {node:12s} {phase:12s} {start}  {end}')
" >> "$placement_file" 2>/dev/null || true

    # Save full ODAG status as JSON (for detailed post-analysis).
    kubectl get odag "$odag_name" -n "$NS" -o json > "$RESULTS/${odag_name}-status.json" 2>/dev/null || true

    # Brief pause between runs.
    sleep 5
}

save_profiler_snapshot() {
    local label=$1
    local template=$2

    # Save the template's profileSummary (EMA runtimes per task per node).
    echo "[eval] Saving profiler snapshot: $label"
    kubectl get odagtemplate "$template" -n "$NS" -o json 2>/dev/null | \
        python3 -c "
import json, sys
d = json.load(sys.stdin)
status = d.get('status', {})
print(json.dumps({
    'runCount': status.get('runCount', 0),
    'lastRunMakespan': status.get('lastRunMakespan'),
    'profileSummary': status.get('profileSummary', {})
}, indent=2))
" > "$RESULTS/profiler-${label}.json" 2>/dev/null || true
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment 1A: ODAG Network-Aware Scheduling            ║"
echo "║  Random (baseline) vs HEFT (network-aware)               ║"
echo "║  Template: IoBT Mission Snapshot (14 tasks, 5 layers)    ║"
echo "║  Runs per condition: $RUNS                                "
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Results directory: $RESULTS"
echo "CSV output: $CSV"
echo ""

# ── Random scheduler ────────────────────────────────────────────────────
echo "═══ Random Scheduler ═══"
for i in $(seq 1 "$RUNS"); do
    run_template "iobt-eval-random" "random" "$i"
done
save_profiler_snapshot "random-final" "iobt-eval-random"

# ── HEFT scheduler ─────────────────────────────────────────────────────
echo ""
echo "═══ HEFT Scheduler ═══"
for i in $(seq 1 "$RUNS"); do
    run_template "iobt-eval-heft" "heft" "$i"
    # Save profiler state after each HEFT run (for convergence plot).
    save_profiler_snapshot "heft-run-$(printf '%02d' $i)" "iobt-eval-heft"
done

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment Complete                                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Results:"
echo "  CSV: $CSV"
echo "  Placement files: $RESULTS/*-placement.txt"
echo "  Profiler snapshots: $RESULTS/profiler-*.json"
echo ""
echo "Summary:"
awk -F, 'NR>1 && $5>0 {
    sum[$2]+=$5; count[$2]++
    if(!min[$2] || $5<min[$2]) min[$2]=$5
    if($5>max[$2]) max[$2]=$5
} END {
    for(s in sum) printf "  %-8s mean=%.1fs  min=%.1fs  max=%.1fs  (n=%d)\n", s, sum[s]/count[s], min[s], max[s], count[s]
}' "$CSV"
echo ""
echo "To generate plots: python3 eval/network-aware/plot-experiment-1.py"
