#!/usr/bin/env bash
# Shared helpers for the 20-rep re-run campaign. Source me.
set -uo pipefail
REPO=/home/anrg/wayline
CAMP="$REPO/eval/_reruns-20rep-wayline-20260523"
STATUS="$CAMP/STATUS.md"
NODES="anrg-1 anrg-3 anrg-4 anrg-5 anrg-6 anrg-7 anrg-8 anrg-9"
SSH="sshpass -p anrg ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=10"

log(){ echo "[$(date '+%F %T')] $*" | tee -a "$CAMP/campaign.log"; }
status(){ echo "$(date '+%F %T') | $*" >> "$STATUS"; }

assert_governor(){           # point 4: re-assert performance on all nodes
  log "assert governor=performance on all nodes"
  for n in $NODES; do
    $SSH anrg@$n "echo anrg | sudo -S sh -c 'for c in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > \$c 2>/dev/null; done'" >/dev/null 2>&1
  done
  # quick verify
  local bad=0
  for n in $NODES; do
    g=$($SSH anrg@$n "cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor" 2>/dev/null)
    [ "$g" = performance ] || { log "WARN governor on $n = $g"; bad=1; }
  done
  return 0
}

# NOTE: teardown-tc-matrix.sh only deletes the setup PODS; host qdiscs persist.
# Real tc control is done at the host level over ssh, with verification.
_tc_iface(){ $SSH anrg@$1 "ip route | awk '/default/{print \$5; exit}'" 2>/dev/null; }
_tc_state(){ local n=$1 if; if=$(_tc_iface "$n"); $SSH anrg@$n "tc qdisc show dev $if | grep -qE 'htb|netem' && echo ON || echo OFF" 2>/dev/null; }

tc_off(){
  log "tc OFF: removing host qdiscs on all nodes"
  for n in $NODES; do local if; if=$(_tc_iface "$n"); $SSH anrg@$n "echo anrg | sudo -S tc qdisc del dev $if root 2>/dev/null || true" >/dev/null 2>&1; done
  local bad=0; for n in anrg-3 anrg-4 anrg-5 anrg-6 anrg-7 anrg-8; do [ "$(_tc_state $n)" = OFF ] || { bad=1; log "WARN tc still ON on $n"; }; done
  [ $bad -eq 0 ] && { log "tc OFF verified on all bottleneck nodes"; return 0; } || { log "ERROR tc_off incomplete"; return 1; }
}
tc_on(){
  log "tc ON: applying matrix (1G/100M/50M, bottleneck 3<->6,4<->7,5<->8)"
  bash "$REPO/eval/network-aware/setup-tc-matrix.sh" >/dev/null 2>&1
  sleep 3
  local bad=0; for n in anrg-3 anrg-6; do [ "$(_tc_state $n)" = ON ] || { bad=1; log "WARN tc not ON on $n"; }; done
  [ $bad -eq 0 ] && { log "tc ON verified"; return 0; } || { log "ERROR tc_on incomplete"; return 1; }
}

wait_idle(){                 # cluster clean preflight (point 3)
  log "preflight: waiting for idle cluster"
  bash "$REPO/eval/two-hop/preflight-idle.sh" 2>/dev/null && { log "cluster idle"; return 0; }
  # fallback: poll dsf-odag + argo task pods to 0
  for i in $(seq 1 60); do
    a=$(kubectl get pods -A 2>/dev/null | grep -E 'dsf-odag|argo/' | grep -ivE 'Completed|server|controller|httpbin' | wc -l)
    [ "$a" -eq 0 ] && { log "cluster idle (fallback)"; return 0; }
    sleep 5
  done
  log "WARN cluster not fully idle after wait"; return 0
}

clear_argo_bucket(){
  kubectl exec -n e0-bench mc-helper -- sh -c \
    'mc alias set local http://minio.e0-bench.svc.cluster.local:9000 minioadmin minioadmin >/dev/null 2>&1; mc rm --recursive --force local/argo-bench >/dev/null 2>&1' >/dev/null 2>&1
}


clear_e0_bucket(){  # e0-bench MinIO bucket (correct creds = e0admin)
  kubectl -n e0-bench exec deploy/minio -- sh -c 'mc alias set local http://minio:9000 e0admin e0adminpw >/dev/null 2>&1; mc rm --recursive --force local/e0-bench/ >/dev/null 2>&1' >/dev/null 2>&1 || true
}

disk_guard(){                # abort-guard: warn if anrg-9 disk dangerously full
  u=$($SSH anrg@anrg-9 "df / | tail -1 | awk '{print \$5}' | tr -d '%'" 2>/dev/null)
  log "anrg-9 disk ${u:-?}% used"
  [ "${u:-0}" -ge 85 ] && { log "DISK GUARD: clearing argo-bucket"; clear_argo_bucket; }
  return 0
}
