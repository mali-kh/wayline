#!/usr/bin/env bash
# K=3 with metrics polling: aggregate CPU/RSS/push.inflight while 3 concurrent ODAGs run.
set -uo pipefail
REPO=/home/anrg/wayline
NS=wl-system
TPL=wl-vemcmt-n4-d60-jpg-heft
OUT="$REPO/eval/_matched-rerun-20260528/k3-stress"
LOG="$OUT/k3-polled.log"
POLL="$OUT/k3-polled-metrics.csv"
RES="$OUT/k3-polled-results.csv"
mkdir -p "$OUT"
exec >>"$LOG" 2>&1
echo "[$(date '+%F %T')] START K=3 with polling"

wait_idle(){ for i in $(seq 1 60); do
  n=$(kubectl -n $NS get pods -l wl-odag --no-headers 2>/dev/null|grep -vcE 'Succeeded|Completed');
  [ "${n:-0}" = 0 ] && return; sleep 4; done; }
wait_idle

# launch poller (every 3s)
echo "ts,pod,cpu_m,working_set_mb,push_inflight,goroutines,mem_alloc_b" > "$POLL"
(
  while true; do
    ts=$(date +%s); top=$(kubectl -n $NS top pod -l app=data-agent --no-headers 2>/dev/null)
    for pod in $(kubectl -n $NS get pods -l app=data-agent --no-headers 2>/dev/null|awk '{print $1}'); do
      cpu=$(echo "$top"|awk -v p=$pod '$1==p{print $2}'|tr -d m); cpu=${cpu:-0}
      ws=$(echo "$top"|awk -v p=$pod '$1==p{print $3}'|tr -d Mi); ws=${ws:-0}
      m=$(kubectl -n $NS exec $pod -- wget -qO- http://localhost:8082/metrics 2>/dev/null)
      inf=$(echo "$m"|python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('push',{}).get('inflight',0))" 2>/dev/null)
      gr=$(echo "$m"|python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('goroutines',0))" 2>/dev/null)
      ab=$(echo "$m"|python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('memory',{}).get('alloc_bytes',0))" 2>/dev/null)
      echo "$ts,$pod,$cpu,$ws,${inf:-0},${gr:-0},${ab:-0}" >> "$POLL"
    done
    sleep 3
  done
) &
P=$!
sleep 3

# launch K=3
echo "K,run_idx,run_name,phase,makespan_s,wall_s" > "$RES"
S=$(date +%s); runs=()
for i in 1 2 3; do
  out=$("$REPO/bin/wayline" run "$TPL" -n $NS 2>&1); r=$(echo "$out"|sed -nE 's/Created run ([^ ]+).*/\1/p'); runs+=("$r")
done
echo "K=3 launched: ${runs[*]}"
while : ; do
  done_count=0
  for r in "${runs[@]}"; do p=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.phase}' 2>/dev/null); case "$p" in Succeeded|Failed) done_count=$((done_count+1));; esac; done
  [ $done_count -eq 3 ] && break
  sleep 5
done
W=$(( $(date +%s)-S ))
for i in 0 1 2; do r=${runs[$i]}
  p=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.phase}' 2>/dev/null)
  ms=$(kubectl -n $NS get odags.wl.io "$r" -o jsonpath='{.status.makespan}' 2>/dev/null)
  echo "K=3,run$((i+1)),$r,$p,${ms:-?},$W" >> "$RES"
  echo "  [K=3 run$((i+1))] $p ms=${ms}s wall=${W}s"
  kubectl -n $NS delete odags.wl.io "$r" --wait=false >/dev/null 2>&1
done

kill $P 2>/dev/null; sleep 2

# analyze polled metrics: peak aggregate CPU/WS, peak per-agent inflight
python3 - <<'PY'
import csv,collections
agg_cpu=collections.defaultdict(int); agg_ws=collections.defaultdict(int); peak_inf=0
for r in csv.DictReader(open("/home/anrg/wayline/eval/_matched-rerun-20260528/k3-stress/k3-polled-metrics.csv")):
    try:
        ts=r['ts']; cpu=int(r['cpu_m']); ws=int(r['working_set_mb']); inf=int(r['push_inflight'])
        agg_cpu[ts]+=cpu; agg_ws[ts]+=ws; peak_inf=max(peak_inf,inf)
    except: pass
print(f"peak aggregate CPU = {max(agg_cpu.values()) if agg_cpu else 0} m  ({(max(agg_cpu.values()) if agg_cpu else 0)/1000:.2f} cores)")
print(f"peak aggregate working-set = {max(agg_ws.values()) if agg_ws else 0} MB")
print(f"peak per-agent push.inflight = {peak_inf} (ceiling=4)")
PY
echo "[$(date '+%F %T')] DONE K=3 polled"
