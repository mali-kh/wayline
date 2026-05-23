#!/usr/bin/env bash
# Experiment 1B: CDAG latency/throughput comparison (random vs locality)
#
# Usage: ./eval/run-cdag-eval.sh [INSTANCES=5] [DURATION=180]
#
# Prerequisites:
#   - tc shaping active
#   - camera-pipeline image built and pushed
#   - CDAGTemplate CRD applied (kubectl apply -f api/v1/cdagtemplate-crd.yml)
#   - Templates applied: kubectl apply -f eval/cdag-camera-pipeline/template-random.yml
#                         kubectl apply -f eval/cdag-camera-pipeline/template-locality.yml

set -euo pipefail
cd "$(dirname "$0")/../.."

INSTANCES=${1:-5}
DURATION=${2:-180}  # seconds per instance
NS="dsf-system"
DSF="go run ./cmd/cli/"
RESULTS="eval/network-aware/results"
OUT="$RESULTS/cdag-latency.csv"
mkdir -p "$RESULTS"

echo "instance,scheduler,template,cdag_name,avg_latency,p50_latency,p95_latency,throughput" > "$OUT"

run_instance() {
    local template=$1
    local scheduler=$2
    local inst_num=$3

    echo "[eval] Deploying $template (instance $inst_num/$INSTANCES, ${DURATION}s run)..."
    local cdag_name
    cdag_name=$($DSF cdag deploy "$template" -n "$NS" 2>&1 | grep -oP 'Created instance \K\S+')
    echo "[eval] Created $cdag_name"

    # Wait for all pods to be Running.
    echo "[eval] Waiting for pods..."
    sleep 30

    # Let it run for DURATION seconds.
    echo "[eval] Running for ${DURATION}s..."
    sleep "$DURATION"

    # Scrape latency from log-sink logs.
    local log_sink_pod="${cdag_name}-log-sink-0"
    local last_stats
    last_stats=$(kubectl logs -n "$NS" "$log_sink_pod" --tail=5 2>/dev/null | grep "THROUGHPUT" | tail -1 || echo "")

    local avg_lat="0" p50_lat="0" p95_lat="0" throughput="0"
    if [[ -n "$last_stats" ]]; then
        avg_lat=$(echo "$last_stats" | grep -oP 'avg=\K[0-9.]+' || echo "0")
        p50_lat=$(echo "$last_stats" | grep -oP 'p50=\K[0-9.]+' || echo "0")
        p95_lat=$(echo "$last_stats" | grep -oP 'p95=\K[0-9.]+' || echo "0")
        throughput=$(echo "$last_stats" | grep -oP 'rate=\K[0-9.]+' || echo "0")
    fi

    echo "[eval] $cdag_name: avg_lat=${avg_lat}s p50=${p50_lat}s p95=${p95_lat}s throughput=${throughput}msg/s"
    echo "$inst_num,$scheduler,$template,$cdag_name,$avg_lat,$p50_lat,$p95_lat,$throughput" >> "$OUT"

    # Also dump full log-sink output for detailed analysis.
    kubectl logs -n "$NS" "$log_sink_pod" > "$RESULTS/${cdag_name}-log-sink.log" 2>/dev/null || true
    kubectl logs -n "$NS" "${cdag_name}-alert-sink-0" > "$RESULTS/${cdag_name}-alert-sink.log" 2>/dev/null || true

    # Record placement.
    echo "[eval] Placement for $cdag_name:"
    kubectl get pods -n "$NS" -l dsf-cdag="$cdag_name" -o wide --no-headers 2>/dev/null | awk '{printf "  %-40s %s\n", $1, $7}'

    # Delete instance.
    kubectl delete cdag "$cdag_name" -n "$NS" --wait=false 2>/dev/null || true
    sleep 15  # let pods drain
}

echo "=== Experiment 1B: CDAG Random vs Locality ==="
echo "Instances per condition: $INSTANCES"
echo "Duration per instance: ${DURATION}s"
echo "Output: $OUT"
echo ""

# Random scheduler.
echo "--- Random scheduler ---"
for i in $(seq 1 "$INSTANCES"); do
    run_instance "camera-pipeline-random" "random" "$i"
done

# Locality scheduler.
echo "--- Locality scheduler ---"
for i in $(seq 1 "$INSTANCES"); do
    run_instance "camera-pipeline-locality" "locality" "$i"
done

echo ""
echo "=== Done. Results in $OUT ==="
echo ""
echo "Summary:"
awk -F, 'NR>1 && $5>0 {
    sum_lat[$2]+=$5; sum_tp[$2]+=$8; count[$2]++
} END {
    for(s in sum_lat) printf "  %s: avg_latency=%.3fs throughput=%.1fmsg/s (n=%d)\n", s, sum_lat[s]/count[s], sum_tp[s]/count[s], count[s]
}' "$OUT"
