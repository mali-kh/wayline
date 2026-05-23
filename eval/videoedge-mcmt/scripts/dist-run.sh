#!/usr/bin/env bash
set -uo pipefail
H=/home/anrg/dsf/eval/videoedge-mcmt/scripts
for spec in "120 png" "30 jpg"; do read d fmt <<<"$spec"
  echo "######## DIST-MINIO cell d${d}-${fmt} ########"
  "$H/argo-distributed-minio.sh" vemcmt-n4-d${d}-${fmt}-argo-dist \
    /home/anrg/dsf/eval/videoedge-mcmt/results/distributed-minio-fair-d${d}-${fmt} 8 e0-bench-dist 2>&1 \
    | grep -E 'rep|Succeeded|Failed|makespan|mean|SUMMARY'
done
echo "DIST-MINIO DONE"
