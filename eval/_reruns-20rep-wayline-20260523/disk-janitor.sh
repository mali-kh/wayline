#!/usr/bin/env bash
# Continuous disk reclaimer: every 120s deletes /data/wl-outputs dirs whose ODAG
# is gone (and not written in last 2min, so the in-flight rep is safe), and clears
# the MinIO argo bucket if anrg-9 gets tight. Runs alongside the campaign.
source /home/anrg/wayline/eval/_reruns-20rep-wayline-20260523/lib.sh
JLOG="$CAMP/janitor.log"; echo "[$(date '+%F %T')] janitor START pid=$$" >> "$JLOG"
while true; do
  ACTIVE=$(kubectl get odags.wl.io -n wl-system -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
  for n in $NODES; do
    $SSH anrg@$n "echo anrg | sudo -S sh -c '
      for d in /data/wl-outputs/*/; do [ -d \"\$d\" ] || continue; b=\$(basename \"\$d\");
        case \" $ACTIVE \" in *\" \$b \"*) continue;; esac;
        find \"\$d\" -maxdepth 0 -mmin +2 >/dev/null 2>&1 && rm -rf \"\$d\"; done'" >/dev/null 2>&1
  done
  u=$($SSH anrg@anrg-9 "df / | tail -1 | awk '{print \$5}' | tr -d '%'" 2>/dev/null)
  if [ "${u:-0}" -ge 78 ]; then clear_argo_bucket; clear_e0_bucket; echo "[$(date '+%F %T')] anrg-9 ${u}% -> cleared argo+e0 buckets" >> "$JLOG"; fi
  hi=$(for x in anrg-3 anrg-6 anrg-7 anrg-8; do $SSH anrg@$x "df / | tail -1 | awk '{print \$5}' | tr -d '%'" 2>/dev/null; done | sort -rn | head -1)
  echo "[$(date '+%F %T')] sweep done; anrg-9=${u}% worker-max=${hi}%" >> "$JLOG"
  sleep 120
done
