#!/usr/bin/env bash
# Experiment 2: Scalability — P2P (ZMQ) vs Centralized (MQTT)
#
# For each fan-out width (N workers), deploys both ZMQ and MQTT variants,
# runs for DURATION seconds, and collects throughput + latency from the sink.
#
# Usage: ./eval/scalability/run-scalability-eval.sh [DURATION=120] [INSTANCES=3]
#
# Prerequisites:
#   - MQTT broker deployed: kubectl apply -f eval/scalability/mqtt-broker.yml
#   - scalability-eval image built and pushed
#   - CDAGTemplate CRD applied
#   - Templates generated: python3 eval/scalability/gen-templates.py
#   - Templates applied: kubectl apply -f eval/scalability/templates/

set -euo pipefail
cd "$(dirname "$0")/../.."

DURATION=${1:-120}
INSTANCES=${2:-3}
NS="dsf-system"
DSF="go run ./cmd/cli/"
RESULTS="eval/scalability/results"
mkdir -p "$RESULTS"

CSV="$RESULTS/scalability.csv"
echo "instance,transport,workers,cdag_name,throughput,avg_latency,p50_latency,p95_latency,p99_latency" > "$CSV"

WORKER_COUNTS="2 4 6 8"

run_instance() {
    local template=$1
    local transport=$2
    local workers=$3
    local inst_num=$4

    echo ""
    echo "[eval] ── $transport / $workers workers / instance $inst_num ──"
    local cdag_name
    cdag_name=$($DSF cdag deploy "$template" -n "$NS" 2>&1 | grep -oP 'Created instance \K\S+')
    echo "[eval] Created: $cdag_name"

    # Wait for pods to be Running.
    echo "[eval] Waiting for pods to start..."
    sleep 30

    # Let it run for DURATION seconds.
    echo "[eval] Running for ${DURATION}s..."
    sleep "$DURATION"

    # Scrape metrics from sink logs.
    local sink_pod="${cdag_name}-sink-0"
    local last_line
    last_line=$(kubectl logs -n "$NS" "$sink_pod" --tail=10 2>/dev/null | grep "STATS" | tail -1 || echo "")

    local throughput="0" avg="0" p50="0" p95="0" p99="0"
    if [[ -n "$last_line" ]]; then
        throughput=$(echo "$last_line" | grep -oP 'rate=\K[0-9.]+' || echo "0")
        avg=$(echo "$last_line" | grep -oP 'lat_avg=\K[0-9.]+' || echo "0")
        p50=$(echo "$last_line" | grep -oP 'p50=\K[0-9.]+' || echo "0")
        p95=$(echo "$last_line" | grep -oP 'p95=\K[0-9.]+' || echo "0")
        p99=$(echo "$last_line" | grep -oP 'p99=\K[0-9.]+' || echo "0")
    fi

    echo "[eval] $cdag_name: throughput=${throughput}msg/s avg_lat=${avg}s p50=${p50}s p95=${p95}s"
    echo "$inst_num,$transport,$workers,$cdag_name,$throughput,$avg,$p50,$p95,$p99" >> "$CSV"

    # Save full sink log.
    kubectl logs -n "$NS" "$sink_pod" > "$RESULTS/${cdag_name}-sink.log" 2>/dev/null || true

    # Record placement.
    echo "[eval] Placement:"
    kubectl get pods -n "$NS" -l dsf-cdag="$cdag_name" -o wide --no-headers 2>/dev/null | \
        awk '{printf "  %-40s %s\n", $1, $7}'

    # Cleanup.
    kubectl delete cdag "$cdag_name" -n "$NS" --wait=false 2>/dev/null || true
    sleep 15
}

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment 2: Scalability — P2P (ZMQ) vs MQTT           ║"
echo "║  Fan-out widths: $WORKER_COUNTS                           "
echo "║  Instances per condition: $INSTANCES                      "
echo "║  Duration per instance: ${DURATION}s                      "
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

for n in $WORKER_COUNTS; do
    for transport in zmq mqtt; do
        template="scale-${transport}-w${n}"
        echo ""
        echo "═══ $transport / $n workers ═══"
        for i in $(seq 1 "$INSTANCES"); do
            run_instance "$template" "$transport" "$n" "$i"
        done
    done
done

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Experiment Complete                                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "Results: $CSV"
echo ""
echo "Summary:"
awk -F, 'NR>1 && $5>0 {
    key=$2"/"$3"w"
    sum_tp[key]+=$5; sum_lat[key]+=$6; count[key]++
} END {
    for(k in sum_tp) printf "  %-12s throughput=%.1fmsg/s  avg_lat=%.4fs  (n=%d)\n", k, sum_tp[k]/count[k], sum_lat[k]/count[k], count[k]
}' "$CSV" | sort
echo ""
echo "To generate plots: python3 eval/scalability/plot-scalability.py"
