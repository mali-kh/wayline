#!/usr/bin/env bash
# K=1 baseline (3 reps) + K=3 concurrent stress (2 reps), wayline-only.
set -uo pipefail
REPO=/home/anrg/wayline
NS=wl-system
TPL=wl-vemcmt-n4-d60-jpg-heft
OUT="$REPO/eval/_matched-rerun-20260528/k3-stress"
LOG="$OUT/run.log"
mkdir -p "$OUT"
exec >>"$LOG" 2>&1
echo "[$(date '+%F %T')] START k3-stress rerun on wayline"

wait_idle(){ for i in $(seq 1 60); do
  n=$(kubectl -n $NS get pods -l wl-odag --no-headers 2>/dev/null|grep -vcE 'Succeeded|Completed');
  [ "${n:-0}" = 0 ] && return; sleep 4; done; }

run_solo(){ local r=$1 s=$(date +%s) out run p ms
  out=$("$REPO/bin/wayline" run "$TPL" -n $NS 2>&1); run=$(echo "$out"|sed -nE 's/Created run ([^ ]+).*/\1/p')
  for i in $(seq 1 120); do p=$(kubectl -n $NS get odags.wl.io "$run" -o jsonpath='{.status.phase}' 2>/dev/null); case "$p" in Succeeded|Failed) break;; esac; sleep 5; done
  ms=$(kubectl -n $NS get odags.wl.io "$run" -o jsonpath='{.status.makespan}' 2>/dev/null); local w=$(( $(date +%s)-s ))
  echo "K=1,rep$r,$run,$p,${ms:-?},$w" >> "$OUT/k1-baseline.csv"
  echo "  [K=1 rep$r] $p ms=${ms}s wall=${w}s"
  kubectl -n $NS delete odags.wl.io "$run" --wait=false >/dev/null 2>&1; }

run_k3(){ local rep=$1 s=$(date +%s) runs=()
  for i in 1 2 3; do
    out=$("$REPO/bin/wayline" run "$TPL" -n $NS 2>&1); r=$(echo "$out"|sed -nE 's/Created run ([^ ]+).*/\1/p'); runs+=("$r")
  done
  echo "  [K=3 rep$rep] launched: ${runs[*]}"
  # wait for all 3 to finish
  while : ; do done_count=0
    for r in "${runs[@]}"; do p=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.phase}' 2>/dev/null); case "$p" in Succeeded|Failed) done_count=$((done_count+1));; esac; done
    [ $done_count -eq 3 ] && break
    sleep 5
  done
  local wall=$(( $(date +%s)-s ))
  for i in 0 1 2; do r=${runs[$i]}
    p=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.phase}' 2>/dev/null)
    ms=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.makespan}' 2>/dev/null)
    echo "K=3,rep$rep,run$((i+1)),$r,$p,${ms:-?},$wall" >> "$OUT/k3-stress.csv"
    echo "  [K=3 rep$rep run$((i+1))] $p ms=${ms}s wall=${wall}s"
    kubectl -n $NS delete odags.wl.io "$r" --wait=false >/dev/null 2>&1
  done
}

echo "K,rep,run_name,phase,makespan_s,wall_s" > "$OUT/k1-baseline.csv"
echo "K,rep,run_idx,run_name,phase,makespan_s,wall_s" > "$OUT/k3-stress.csv"

echo "[$(date '+%F %T')] === K=1 BASELINE (3 reps solo) ==="
for r in 1 2 3; do wait_idle; run_solo $r; done

echo "[$(date '+%F %T')] === K=3 STRESS (2 reps concurrent) ==="
for r in 1 2; do wait_idle; run_k3 $r; done

echo "[$(date '+%F %T')] DONE k3-stress"
