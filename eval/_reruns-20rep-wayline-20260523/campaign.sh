#!/usr/bin/env bash
# Resumable, budget-capped campaign engine. Each invocation runs pending chunks
# until BUDGET seconds elapse, then exits cleanly (relaunch resumes from progress.tsv).
source /home/anrg/wayline/eval/_reruns-20rep-wayline-20260523/lib.sh
PROG="$CAMP/progress.tsv"; touch "$PROG"
BUDGET="${BUDGET:-3600}"
pgrep -f "disk-janitor.sh" >/dev/null 2>&1 || { setsid nohup bash "$CAMP/disk-janitor.sh" >/dev/null 2>&1 & disown; }
done_chunk(){ grep -qxF "$1	DONE" "$PROG"; }
mark_done(){ done_chunk "$1" || printf '%s\tDONE\n' "$1" >> "$PROG"; }
budget_left(){ [ "$SECONDS" -lt "$BUDGET" ]; }
E0C="$CAMP/02-e0/two-hop"

# ---------- EXP1: AI City MCMT fair 2x2 (per-cell chunks) ----------
exp1_cell(){  # $1=net(notc|tc)  $2="<d> <fmt>"
  local net="$1" spec="$2" d fmt; read d fmt <<<"$spec"; local cell="d${d}-${fmt}"
  local cid="exp1.$net.$cell"
  done_chunk "$cid" && { log "skip $cid (done)"; return 0; }
  budget_left || { log "BUDGET hit before $cid -> clean exit (relaunch resumes)"; exit 0; }
  log "CHUNK $cid START"; status "exp1 $net $cell START"; assert_governor
  if [ "$net" = tc ]; then tc_on || { log "ABORT $cid tc_on failed"; status "exp1 $net $cell SKIP(tc_on)"; return 0; }
  else tc_off || { log "ABORT $cid tc_off failed"; status "exp1 $net $cell SKIP(tc_off)"; return 0; }; fi
  wait_idle; disk_guard
  OUT="$CAMP/01-fair-mcmt/fair-results-20rep.csv" REPS=20 CELL_SPEC="$spec" \
    bash "$CAMP/fair-run-cell.sh" "$net" >> "$CAMP/01-fair-mcmt/${net}-${cell}.log" 2>&1
  local rc=$? got
  got=$(awk -F, -v n="$net" -v c="$cell" 'NR>1&&$1==n&&$2==c&&$5=="Succeeded"' "$CAMP/01-fair-mcmt/fair-results-20rep.csv"|wc -l)
  log "CHUNK $cid END rc=$rc succeeded=$got/40"; status "exp1 $net $cell DONE succeeded=$got/40"
  mark_done "$cid"; disk_guard
}

# ---------- EXP2: E0 two-hop data-plane microbench (tc ON, fresh copy) ----------
exp2_sweep(){  # $1=sub (dsf|minio|nfs)
  local sub="$1"; local cid="exp2.e0.$sub"
  done_chunk "$cid" && { log "skip $cid (done)"; return 0; }
  budget_left || { log "BUDGET hit before $cid -> clean exit"; exit 0; }
  log "CHUNK $cid START"; status "exp2 e0 $sub START"; assert_governor
  tc_on || { log "ABORT $cid tc_on failed"; status "exp2 e0 $sub SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard
  REPO_ROOT=/home/anrg/wayline N=20 bash "$E0C/$sub/run.sh" >> "$CAMP/02-e0/${sub}.log" 2>&1; local rc=$?
  local cells full got
  got=$(find "$E0C/results/$sub" -name '*.json' 2>/dev/null | wc -l)
  cells=$(ls -d "$E0C/results/$sub"/*/ 2>/dev/null | wc -l)
  full=$(for cd in "$E0C/results/$sub"/*/; do [ -d "$cd" ] && [ "$(ls "$cd"*.json 2>/dev/null|wc -l)" -ge 20 ] && echo 1; done | wc -l)
  log "CHUNK $cid END rc=$rc json=$got cells=$cells full_cells=$full"
  if [ "$cells" -ge 8 ] && [ "$full" -eq "$cells" ]; then mark_done "$cid"; status "exp2 e0 $sub DONE json=$got ($full/$cells cells full)"
  else log "WARN $cid incomplete ($full/$cells cells full) -> left pending; relaunch resumes"; status "exp2 e0 $sub PARTIAL $full/$cells cells full"; fi
  disk_guard
}
exp2_harvest(){
  local cid="exp2.e0.harvest"; done_chunk "$cid" && return 0
  budget_left || exit 0
  log "CHUNK $cid START (harvest only; plot skipped to protect paper figures)"
  python3 "$E0C/harvest.py" "$E0C/results" >> "$CAMP/02-e0/harvest.log" 2>&1 || true
  log "CHUNK $cid END"; status "exp2 e0 harvest DONE -> 02-e0/two-hop/results/all.csv"
  mark_done "$cid"
}


# ---------- EXP2: E0 two-hop data-plane microbench (tc on, wl-native two-hop) ----------
E0DIR="$REPO/eval/two-hop"
exp2_e0(){ local sub="$1"; local cid="exp2.e0.$sub"
  done_chunk "$cid" && { log "skip $cid (done)"; return 0; }
  budget_left || { log "BUDGET before $cid -> clean exit"; exit 0; }
  log "CHUNK $cid START"; status "exp2 e0 $sub START"; assert_governor
  tc_on || { log "ABORT $cid tc_on failed"; status "exp2 e0 $sub SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/02-e0"
  REPO_ROOT="$REPO" N=20 bash "$E0DIR/$sub/run.sh" >> "$CAMP/02-e0/${sub}.log" 2>&1; local rc=$?
  local cells full; cells=$(ls -d "$E0DIR/results/$sub"/*/ 2>/dev/null|wc -l)
  full=$(for cd in "$E0DIR/results/$sub"/*/; do [ -d "$cd" ]&&[ "$(ls "$cd"*.json 2>/dev/null|wc -l)" -ge 20 ]&&echo 1; done|wc -l)
  log "CHUNK $cid END rc=$rc cells=$cells full=$full"
  if [ "$cells" -ge 8 ]&&[ "$full" -eq "$cells" ]; then mark_done "$cid"; status "exp2 e0 $sub DONE ($full/$cells)"; else log "WARN $cid partial $full/$cells -> resume"; status "exp2 e0 $sub PARTIAL $full/$cells"; fi
  disk_guard
}

# ---------- generic MCMT-baseline harness chunk (tc on, /tmp csv output) ----------
run_tmpcsv(){ local cid="$1" harness="$2" tmpout="$3" envv="$4" minrows="$5"
  done_chunk "$cid" && { log "skip $cid (done)"; return 0; }
  budget_left || { log "BUDGET before $cid -> clean exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor
  tc_on || { log "ABORT $cid tc_on failed"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/$cid"; rm -f "$tmpout"
  env $envv bash "$REPO/$harness" >> "$CAMP/$cid/run.log" 2>&1; local rc=$?
  [ -f "$tmpout" ] && cp -f "$tmpout" "$CAMP/$cid/results.csv"
  local rows; rows=$(grep -c 'Succeeded' "$CAMP/$cid/results.csv" 2>/dev/null||echo 0)
  log "CHUNK $cid END rc=$rc succeeded=$rows (need >=$minrows)"
  if [ "$rows" -ge "$minrows" ]; then mark_done "$cid"; status "$cid DONE rows=$rows"; else log "WARN $cid only $rows/$minrows -> resume"; status "$cid PARTIAL rows=$rows"; fi
  disk_guard
}


# ---------- EXP4: distributed-MinIO baseline (tc on) ----------
exp4_dist(){ local cid="exp4.dist"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_on || { log "ABORT $cid tc_on"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/04-dist"
  bash "$REPO/eval/videoedge-mcmt/scripts/dist-run.sh" >> "$CAMP/04-dist/run.log" 2>&1; local rc=$? ok=0
  for d in 120-png 30-jpg; do local r; r=$(grep -c Succeeded "$REPO/eval/videoedge-mcmt/results/distributed-minio-fair-d$d/summary.csv" 2>/dev/null||echo 0); [ "$r" -ge 18 ] && ok=$((ok+1)); done
  log "CHUNK $cid END rc=$rc cells_ok=$ok/2"
  if [ "$ok" -eq 2 ]; then cp -r "$REPO/eval/videoedge-mcmt/results/distributed-minio-fair-"* "$CAMP/04-dist/" 2>/dev/null; mark_done "$cid"; status "$cid DONE"; else log "WARN $cid partial $ok/2"; status "$cid PARTIAL"; fi; disk_guard; }

# ---------- EXP6: network-aware HEFT scheduling (per-ODAG, tc on) ----------
exp6_na(){ local odag="$1"; local cid="exp6.na.$odag"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_on || { log "ABORT $cid tc_on"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/06-na"
  bash "$REPO/eval/network-aware/sweep-scheduler.sh" "$odag" 20 >> "$CAMP/06-na/$odag.log" 2>&1; local rc=$?
  local cfgs full; cfgs=$(ls -d "$REPO/eval/network-aware/results/$odag"/*/ 2>/dev/null|wc -l)
  full=$(for c in "$REPO/eval/network-aware/results/$odag"/*/; do [ -d "$c" ]&&[ "$(grep -c Succeeded "$c/summary.csv" 2>/dev/null||echo 0)" -ge 18 ]&&echo 1; done|wc -l)
  log "CHUNK $cid END rc=$rc cfgs=$cfgs full=$full"
  if [ "$cfgs" -ge 3 ]&&[ "$full" -eq "$cfgs" ]; then mark_done "$cid"; status "$cid DONE"; else log "WARN $cid partial $full/$cfgs"; status "$cid PARTIAL"; fi; disk_guard; }

# ---------- EXP9: Argo head-to-head E1 (tc on) ----------
exp9_e1(){ local cid="exp9.e1"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_on || { log "ABORT $cid tc_on"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/09-e1"
  bash "$REPO/eval/argo-headtohead/sweep.sh" >> "$CAMP/09-e1/run.log" 2>&1; local rc=$?
  log "CHUNK $cid END rc=$rc"
  if [ "$rc" -eq 0 ]; then mark_done "$cid"; status "$cid DONE"; else log "WARN $cid rc=$rc"; status "$cid PARTIAL"; fi; disk_guard; }

# ---------- EXP10: network-overhead E2 (tc on; setup once) ----------
exp10_e2(){ local cid="exp10.e2"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_on || { log "ABORT $cid tc_on"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/10-e2"
  bash "$REPO/eval/networkoverhead-headtohead/setup.sh" >> "$CAMP/10-e2/setup.log" 2>&1
  bash "$REPO/eval/networkoverhead-headtohead/sweep.sh" >> "$CAMP/10-e2/run.log" 2>&1; local rc=$?
  log "CHUNK $cid END rc=$rc"
  if [ "$rc" -eq 0 ]; then mark_done "$cid"; status "$cid DONE"; else log "WARN $cid rc=$rc"; status "$cid PARTIAL"; fi; disk_guard; }

# ---------- EXP11: Ray microbench (tc OFF) ----------
exp11_ray(){ local cid="exp11.ray"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_off || { log "ABORT $cid tc_off"; status "$cid SKIP(tc_off)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/11-ray"
  bash "$REPO/eval/ray-microbench/notc-ray-run.sh" >> "$CAMP/11-ray/run.log" 2>&1; local rc=$?
  local rows; rows=$(grep -c ',' "$REPO/eval/ray-microbench/ray-e0-notc.csv" 2>/dev/null||echo 0)
  log "CHUNK $cid END rc=$rc rows=$rows"
  if [ "$rows" -ge 10 ]; then cp -f "$REPO/eval/ray-microbench/ray-e0-notc.csv" "$CAMP/11-ray/" 2>/dev/null; mark_done "$cid"; status "$cid DONE rows=$rows"; else log "WARN $cid rows=$rows"; status "$cid PARTIAL"; fi; disk_guard; }

# ---------- EXP12: concurrent-ODAG stress + overhead (tc on) ----------
exp12_stress(){ local cid="exp12.stress"; done_chunk "$cid" && { log "skip $cid"; return 0; }
  budget_left || { log "BUDGET before $cid -> exit"; exit 0; }
  log "CHUNK $cid START"; status "$cid START"; assert_governor; tc_on || { log "ABORT $cid tc_on"; status "$cid SKIP(tc_on)"; return 0; }
  wait_idle; disk_guard; mkdir -p "$CAMP/12-stress"
  bash "$REPO/eval/overhead-stress/run-stress.sh" >> "$CAMP/12-stress/run.log" 2>&1; local rc=$?
  log "CHUNK $cid END rc=$rc"
  if [ "$rc" -eq 0 ]; then cp -r "$REPO/eval/overhead-stress/results"/* "$CAMP/12-stress/" 2>/dev/null; mark_done "$cid"; status "$cid DONE"; else log "WARN $cid rc=$rc"; status "$cid PARTIAL"; fi; disk_guard; }

log "===== campaign invocation START (budget=${BUDGET}s) ====="
# ===== EXP1 =====
exp1_cell notc "30 jpg"; exp1_cell notc "60 jpg"; exp1_cell notc "120 jpg"; exp1_cell notc "120 png"
exp1_cell tc "30 jpg"; exp1_cell tc "60 jpg"; exp1_cell tc "120 jpg"; exp1_cell tc "120 png"
# ===== EXP2: E0 =====
exp2_e0 wayline; exp2_e0 minio; exp2_e0 nfs
# ===== EXP3: static-placement ablation (3 configs x 20 reps @ d120-png) =====
run_tmpcsv exp3.ablation eval/videoedge-mcmt/scripts/ablation-run.sh /tmp/ablation-results.csv "N=20" 54
# ===== EXP4-12 =====
exp4_dist
run_tmpcsv exp5.nfs eval/videoedge-mcmt/scripts/nfs-mcmt-run.sh /tmp/nfs-mcmt-results.csv "N=20" 18
exp6_na iobt; exp6_na hetero-compute; exp6_na wide-pipeline-flex
exp9_e1; exp10_e2; exp11_ray; exp12_stress
# ===== exp4..13 appended after porting/wiring =====
ALL="exp1.notc.d30-jpg exp1.notc.d60-jpg exp1.notc.d120-jpg exp1.notc.d120-png exp1.tc.d30-jpg exp1.tc.d60-jpg exp1.tc.d120-jpg exp1.tc.d120-png exp2.e0.wayline exp2.e0.minio exp2.e0.nfs exp3.ablation exp4.dist exp5.nfs exp6.na.iobt exp6.na.hetero-compute exp6.na.wide-pipeline-flex exp9.e1 exp10.e2 exp11.ray exp12.stress"
P=0; for c in $ALL; do done_chunk "$c" || P=$((P+1)); done
log "===== invocation END — pending(exp1+exp2): $P ====="
