#!/usr/bin/env bash
# Single-cell matched-placement rerun: n4-d120-png tc, 20 paired reps.
# Wayline = wl-vemcmt-n4-d120-png-spread-matched (NEW, per-task pin = Argo's pin)
# Argo    = wl-vemcmt-n4-d120-png-spread-argo (unchanged)
set -uo pipefail
REPO=/home/anrg/wayline
OUTDIR="$REPO/eval/_matched-rerun-20260528/fair-d120-png-tc"
OUT="$OUTDIR/results.csv"
LOG="$OUTDIR/run.log"
REPS=20
CELL=d120-png
WL_TPL=wl-vemcmt-n4-d120-png-spread-matched
AR_TPL=wl-vemcmt-n4-d120-png-spread-argo

mkdir -p "$OUTDIR"
[ -f "$OUT" ] || echo "net,cell,rep,system,phase,makespan_s,wall_s" > "$OUT"
exec >>"$LOG" 2>&1
echo "[$(date '+%F %T')] START matched-placement rerun: $CELL tc, $REPS paired reps"

clearbucket(){ kubectl -n e0-bench exec mc-helper -- sh -c 'mc rm --recursive --force local/argo-bench/ >/dev/null 2>&1' >/dev/null 2>&1 || true; }
wait_idle(){ for i in $(seq 1 60); do
  n=$(kubectl -n wl-system get pods -l wl-odag --no-headers 2>/dev/null|grep -vcE 'Succeeded|Completed');
  m=$(kubectl -n argo get pods --no-headers 2>/dev/null|grep -ivE 'argo-server|workflow-controller|httpbin'|grep -vcE 'Succeeded|Completed');
  [ "${n:-0}" = 0 ] && [ "${m:-0}" = 0 ] && return; sleep 4; done; }

run_wl(){ local r=$1 s=$(date +%s) out run p ms
  out=$("$REPO/bin/wayline" run "$WL_TPL" -n wl-system 2>&1); run=$(echo "$out"|sed -nE 's/Created run ([^ ]+).*/\1/p')
  for i in $(seq 1 120); do p=$(kubectl -n wl-system get odags.wl.io "$run" -o jsonpath='{.status.phase}' 2>/dev/null); case "$p" in Succeeded|Failed) break;; esac; sleep 5; done
  ms=$(kubectl -n wl-system get odags.wl.io "$run" -o jsonpath='{.status.makespan}' 2>/dev/null); local w=$(( $(date +%s)-s ))
  echo "tc,$CELL,$r,wayline,$p,${ms:-?},$w" >> "$OUT"
  echo "  [tc $CELL] wayline rep$r: $p ms=${ms}s wall=${w}s"
  kubectl -n wl-system delete odags.wl.io "$run" --wait=false >/dev/null 2>&1; }

run_ar(){ local r=$1 s=$(date +%s) out wf p ms
  out=$(kubectl -n argo create -f <(printf 'apiVersion: argoproj.io/v1alpha1\nkind: Workflow\nmetadata: { generateName: %s-, namespace: argo }\nspec: { workflowTemplateRef: { name: %s } }\n' "$AR_TPL" "$AR_TPL") 2>&1)
  wf=$(echo "$out"|sed -nE 's|workflow.argoproj.io/(.+) created.*|\1|p')
  for i in $(seq 1 150); do p=$(kubectl -n argo get workflow "$wf" -o jsonpath='{.status.phase}' 2>/dev/null); case "$p" in Succeeded|Failed|Error) break;; esac; sleep 5; done
  ms=$(kubectl -n argo get workflow "$wf" -o json 2>/dev/null|python3 -c "import json,sys,datetime as dt;d=json.load(sys.stdin)['status'];a=dt.datetime.fromisoformat(d['startedAt'].replace('Z','+00:00'));b=dt.datetime.fromisoformat(d['finishedAt'].replace('Z','+00:00'));print(int((b-a).total_seconds()))" 2>/dev/null); local w=$(( $(date +%s)-s ))
  echo "tc,$CELL,$r,argo,$p,${ms:-?},$w" >> "$OUT"
  echo "  [tc $CELL] argo    rep$r: $p ms=${ms}s wall=${w}s"
  kubectl -n argo delete workflow "$wf" --wait=false >/dev/null 2>&1
  clearbucket; }

for r in $(seq 1 $REPS); do
  wait_idle
  if (( r % 2 == 1 )); then run_wl "$r"; wait_idle; run_ar "$r"
  else                      run_ar "$r"; wait_idle; run_wl "$r"; fi
done
echo "[$(date '+%F %T')] DONE matched-placement rerun"
