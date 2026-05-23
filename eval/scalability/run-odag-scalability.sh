#!/usr/bin/env bash
# Experiment 2A: ODAG Scalability — P2P (data-agent) vs NFS (shared storage)
#
# Runs fan-out ODAGs at varying widths with two storage modes:
#   p2p: normal local disk + data-agent push (default DSF)
#   nfs: NFS overlay on /data/dsf-outputs (centralized storage bottleneck)
#
# Usage: ./eval/scalability/run-odag-scalability.sh [RUNS=5]
#
# Prerequisites:
#   - NFS server: kubectl apply -f eval/scalability/nfs-server.yml
#   - scalability-eval image built and pushed
#   - ODAGTemplates applied (use P2P templates for both — storage mode is
#     controlled by whether NFS overlay is active)
#   - For NFS mode: ./eval/scalability/setup-nfs-overlay.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

RUNS=${1:-5}
NS="dsf-system"
DSF="go run ./cmd/cli/"
RESULTS="eval/scalability/results"
mkdir -p "$RESULTS"

CSV="$RESULTS/odag-scalability.csv"
echo "run,transport,workers,odag_name,phase,makespan" > "$CSV"

WORKER_COUNTS="2 4 6 8"

run_template() {
    local template=$1
    local transport=$2
    local workers=$3
    local run_num=$4

    echo ""
    echo "[eval] ── $transport / $workers workers / run $run_num ──"
    local odag_name
    odag_name=$($DSF odag run "$template" -n "$NS" 2>&1 | grep -oP 'Created run \K\S+')
    echo "[eval] Created: $odag_name"

    local elapsed=0
    while true; do
        phase=$(kubectl get odag "$odag_name" -n "$NS" -o jsonpath='{.status.phase}' 2>/dev/null || echo "Pending")
        if [[ "$phase" == "Succeeded" || "$phase" == "Failed" ]]; then
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        if (( elapsed >= 300 )); then
            echo "[eval] TIMEOUT: $odag_name"
            phase="Timeout"
            break
        fi
    done

    local makespan
    makespan=$(kubectl get odag "$odag_name" -n "$NS" -o jsonpath='{.status.makespan}' 2>/dev/null || echo "0")
    echo "[eval] $odag_name: phase=$phase makespan=${makespan}s"
    echo "$run_num,$transport,$workers,$odag_name,$phase,$makespan" >> "$CSV"

    kubectl get pods -n "$NS" -l dsf-odag="$odag_name" -o wide --no-headers 2>/dev/null | \
        awk '{printf "%-40s %s\n", $1, $7}' > "$RESULTS/${odag_name}-placement.txt" 2>/dev/null || true

    sleep 5
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment 2A: ODAG Scalability — P2P vs NFS            ║"
echo "║  Fan-out widths: $WORKER_COUNTS                           "
echo "║  Runs per condition: $RUNS                                "
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Phase 1: P2P (normal local disk + data-agent) ──────────────────────
echo "═══ Phase 1: P2P (local disk) ═══"
echo "[eval] Ensuring NFS overlay is NOT active..."
./eval/scalability/teardown-nfs-overlay.sh 2>/dev/null || true
sleep 5

for n in $WORKER_COUNTS; do
    echo ""
    echo "── p2p / $n workers ──"
    for i in $(seq 1 "$RUNS"); do
        run_template "scale-odag-p2p-w${n}" "p2p" "$n" "$i"
    done
done

# ── Phase 2: NFS (centralized storage overlay) ─────────────────────────
echo ""
echo "═══ Phase 2: NFS (centralized storage) ═══"
echo "[eval] Activating NFS overlay..."
./eval/scalability/setup-nfs-overlay.sh
sleep 10

for n in $WORKER_COUNTS; do
    echo ""
    echo "── nfs / $n workers ──"
    for i in $(seq 1 "$RUNS"); do
        run_template "scale-odag-p2p-w${n}" "nfs" "$n" "$i"
    done
done

# ── Teardown NFS ──
echo ""
echo "[eval] Tearing down NFS overlay..."
./eval/scalability/teardown-nfs-overlay.sh 2>/dev/null || true

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment Complete                                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Results: $CSV"
echo ""
echo "Summary:"
awk -F, 'NR>1 && $6>0 {
    key=$2"/"$3"w"
    sum[key]+=$6; count[key]++
} END {
    for(k in sum) printf "  %-12s mean=%.1fs (n=%d)\n", k, sum[k]/count[k], count[k]
}' "$CSV" | sort
