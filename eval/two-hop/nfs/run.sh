#!/usr/bin/env bash
# E0 shared-FS (RWX NFS) baseline sweep driver. Symmetric to minio/run.sh.
#   N      reps per cell (default 10; SMOKE=1 -> 2)
#   ONLY   cell tag filter (e.g. ONLY="same-100mb cross-100mb")
set -uo pipefail
E0_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NS=e0-bench
N="${N:-10}"; TIMEOUT="${TIMEOUT:-300}"
[[ "${SMOKE:-0}" == "1" ]] && N=2
CELLS_FILE="${E0_DIR}/cells.txt"
RESULTS_ROOT="${E0_DIR}/results/nfs"; mkdir -p "$RESULTS_ROOT"

if ! kubectl -n "$NS" get pvc e0-nfs-pvc >/dev/null 2>&1; then
  echo "NFS PVC missing -- run ./nfs/deploy-nfs.sh first" >&2; exit 2
fi

render_jobs(){ local run=$1 bytes=$2 pn=$3 cn=$4 dir=$5; local out="${dir}/${run}.jobs.yml"
  E0_RUN_NAME="$run" E0_BYTES="$bytes" E0_PRODUCER_NODE="$pn" E0_CONSUMER_NODE="$cn" \
    envsubst < "${E0_DIR}/nfs/job.yml.tpl" > "$out"; echo "$out"; }
wait_for_jobs(){ local run=$1 end=$(( $(date +%s) + TIMEOUT ))
  while [[ $(date +%s) -lt $end ]]; do
    local pd cd pf cf
    pd=$(kubectl -n "$NS" get job "${run}-producer" -o jsonpath='{.status.succeeded}' 2>/dev/null||echo 0)
    cd=$(kubectl -n "$NS" get job "${run}-consumer" -o jsonpath='{.status.succeeded}' 2>/dev/null||echo 0)
    pf=$(kubectl -n "$NS" get job "${run}-producer" -o jsonpath='{.status.failed}' 2>/dev/null||echo 0)
    cf=$(kubectl -n "$NS" get job "${run}-consumer" -o jsonpath='{.status.failed}' 2>/dev/null||echo 0)
    [[ "${pf:-0}" != 0 || "${cf:-0}" != 0 ]] && { echo Failed; return 1; }
    [[ "${pd:-0}" == 1 && "${cd:-0}" == 1 ]] && { echo Succeeded; return 0; }
    sleep 1
  done; echo Timeout; return 1; }
harvest_run(){ local run=$1 dir=$2; local out="${dir}/${run}.json"
  local pp cp; pp=$(kubectl -n "$NS" get pods -l "e0-run=${run},component=producer" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null||true)
  cp=$(kubectl -n "$NS" get pods -l "e0-run=${run},component=consumer" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null||true)
  [[ -z "$pp" || -z "$cp" ]] && { echo "[harvest/$run] missing pods" >&2; return 1; }
  local pl cl; pl="$(kubectl -n "$NS" logs "$pp" 2>/dev/null|grep -F 'DSF_E0_TIMESTAMPS '|tail -1|sed 's/^DSF_E0_TIMESTAMPS //'||true)"
  cl="$(kubectl -n "$NS" logs "$cp" 2>/dev/null|grep -F 'DSF_E0_TIMESTAMPS '|tail -1|sed 's/^DSF_E0_TIMESTAMPS //'||true)"
  local ps pf2 cs cf2
  ps=$(kubectl -n "$NS" get pod "$pp" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}' 2>/dev/null||true)
  pf2=$(kubectl -n "$NS" get pod "$pp" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null||true)
  cs=$(kubectl -n "$NS" get pod "$cp" -o jsonpath='{.status.containerStatuses[0].state.terminated.startedAt}' 2>/dev/null||true)
  cf2=$(kubectl -n "$NS" get pod "$cp" -o jsonpath='{.status.containerStatuses[0].state.terminated.finishedAt}' 2>/dev/null||true)
  python3 - "$out" "$run" "$pp" "$cp" "$pl" "$cl" "$ps" "$pf2" "$cs" "$cf2" <<'PY'
import json,sys
out,run,pp,cp,pl,cl,ps,pf,cs,cf=sys.argv[1:11]
json.dump({"run_name":run,"producer_pod":pp,"consumer_pod":cp,
  "producer_log":json.loads(pl) if pl else None,
  "consumer_log":json.loads(cl) if cl else None,
  "pod_api":{"producer_started":ps or None,"producer_finished":pf or None,
             "consumer_started":cs or None,"consumer_finished":cf or None}},
  open(out,"w"),indent=2,default=str)
print(f"[harvest] wrote {out}")
PY
}
while IFS=, read -r coloc label bytes pn cn; do
  [[ "$coloc" =~ ^#|^$ ]] && continue
  tag="${coloc}-$(echo "$label"|tr A-Z a-z)"
  [[ -n "${ONLY:-}" ]] && ! echo " ${ONLY} "|grep -qF " $tag " && { echo "[skip] $tag"; continue; }
  dir="${RESULTS_ROOT}/${tag}"; mkdir -p "$dir"
  echo "==== NFS cell $tag (N=$N) ===="
  for i in $(seq 1 "$N"); do
    run="e0-nfs-${tag}-run-$(printf '%03d' "$i")"
    kubectl -n "$NS" delete job "${run}-producer" "${run}-consumer" --ignore-not-found >/dev/null 2>&1
    f=$(render_jobs "$run" "$bytes" "$pn" "$cn" "$dir"); kubectl apply -f "$f" >/dev/null 2>&1
    st=$(wait_for_jobs "$run"); harvest_run "$run" "$dir" >/dev/null 2>&1
    ms=$(python3 -c "import json;d=json.load(open('${dir}/${run}.json'));c=d.get('consumer_log') or {};p=d.get('producer_log') or {};print(f\"e2e={ (c.get('t4_wall') or 0)-(p.get('t0_wall') or 0):.1f}s dl={ (c.get('t4_wall') or 0)-(c.get('t_found_wall') or 0):.2f}s\")" 2>/dev/null)
    echo "  [$tag rep$i] $st $ms"
    kubectl -n "$NS" delete job "${run}-producer" "${run}-consumer" --ignore-not-found --wait=false >/dev/null 2>&1
    kubectl -n "$NS" exec deploy/e0-nfs -- rm -rf "/nfsshare/${run}" >/dev/null 2>&1 || true
  done
done < "$CELLS_FILE"
echo "NFS SWEEP DONE -> $RESULTS_ROOT"
