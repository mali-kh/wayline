#!/usr/bin/env bash
#
# Warm-only DSF check: run K back-to-back DSF runs to let the profiler/HEFT
# converge on the cell, then hand off to pilot-paired.sh for the recorded
# reps. The motivating question — does the DSF win at D=120 PNG survive
# once cold-start placement noise is gone?
#
#   ./warmup-then-paired.sh [N=4] [D=120] [FMT=png] [WARMUPS=3] [REPS=3]
#
# Warmup makespans are appended to OUT/warmups.csv but excluded from the
# paired-rep summary.
set -euo pipefail

N=${1:-4}
D=${2:-120}
FMT=${3:-png}
WARMUPS=${4:-3}
REPS=${5:-3}
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"

CELL="n${N}-d${D}-${FMT}"
DSF_TPL="vemcmt-${CELL}-heft"
OUT="$ROOT/results/${CELL}-warm-pilot"
mkdir -p "$OUT"

# Render+apply DSF template once.
python3 "$ROOT/dsf/render.py" --cameras "$N" --duration "$D" --scheduler heft \
    --preprocess-fmt "$FMT" --name "$DSF_TPL" -o "/tmp/${DSF_TPL}.yml"
kubectl apply -f "/tmp/${DSF_TPL}.yml" >/dev/null

WARM_LOG="$OUT/warmups.csv"
[[ -f "$WARM_LOG" ]] || echo "warmup_idx,run_name,phase,makespan_s,wall_s,bytes_in_total,bytes_out_total" > "$WARM_LOG"

run_dsf_once() {
    local idx=$1
    # No delete-before-run: CLI uses generateName so every invocation
    # produces a uniquely-named ODAG; the SQL counter assigns dsf.io/run.
    local start=$(date +%s)
    local out
    out=$("$REPO/bin/dsf" odag run $DSF_TPL -n dsf-system 2>&1)
    echo "$out" | tail -1
    local run
    run=$(echo "$out" | sed -nE 's|Created run ([^ ]+).*|\1|p')
    if [ -z "$run" ]; then
        echo "  ERROR: could not parse run name from CLI output: $out"
        echo "$idx,?,Failed,?,?,?,?" >> "$WARM_LOG"
        return 1
    fi
    for i in $(seq 1 90); do
        sleep 15
        local p=$(kubectl -n dsf-system get odag "$run" -o jsonpath='{.status.phase}' 2>/dev/null || echo "")
        [ "$p" = "Succeeded" ] || [ "$p" = "Failed" ] && break
    done
    local end=$(date +%s)
    local wall=$((end - start))
    local ms=$(kubectl -n dsf-system get odag "$run" -o jsonpath='{.status.makespan}' 2>/dev/null)
    local phase=$(kubectl -n dsf-system get odag "$run" -o jsonpath='{.status.phase}' 2>/dev/null)
    # Aggregate bytes from data-agent metrics
    local bi=0 bo=0
    for n in 1 3 4 5 6 7 8 9; do
        local da=$(kubectl -n dsf-system get pod -l app=data-agent -o jsonpath="{.items[?(@.spec.nodeName==\"anrg-$n\")].metadata.name}")
        [ -z "$da" ] && continue
        local m=$(kubectl -n dsf-system exec "$da" -- wget -qO- "http://localhost:8081/metrics" 2>/dev/null)
        [ -z "$m" ] && continue
        local pbi=$(echo "$m" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['transfers']['bytes_in'])" 2>/dev/null || echo 0)
        local pbo=$(echo "$m" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['push']['bytes_out'])"     2>/dev/null || echo 0)
        bi=$((bi + pbi)); bo=$((bo + pbo))
    done
    echo "$idx,$run,$phase,$ms,$wall,$bi,$bo" >> "$WARM_LOG"
    echo "  -> warmup $idx: phase=$phase makespan=${ms}s wall=${wall}s"
}

echo "##############################################"
echo "## warmup phase  WARMUPS=$WARMUPS  cell=$CELL"
echo "##############################################"
for w in $(seq 1 "$WARMUPS"); do
    echo
    echo "==================== warmup $w ===================="
    run_dsf_once "$w"
done

echo
echo "##############################################"
echo "## paired reps  REPS=$REPS  (after warmup)"
echo "##############################################"
"$HERE/pilot-paired.sh" "$N" "$D" "$FMT" "$REPS" "$OUT/paired"

echo
echo "##############################################"
echo "## WARM-ONLY SUMMARY  $OUT/"
echo "##############################################"
echo
echo "warmups:"
column -t -s, < "$WARM_LOG"
echo
echo "paired reps (after warmup):"
column -t -s, < "$OUT/paired/summary.csv"
