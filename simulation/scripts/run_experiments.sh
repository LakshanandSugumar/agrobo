#!/usr/bin/env bash
# Run the full-season simulation for twin-guided vs no-twin across seeds, 2 at a time.
# Usage: scripts/run_experiments.sh [out_dir] [seeds...]
set -euo pipefail
OUT=${1:-results/runs}; shift || true
SEEDS=${*:-7 11 23}
mkdir -p "$OUT"
export ROS_LOG_DIR="$OUT/log"
dom=40
for s in $SEEDS; do
  pids=()
  for mode in true false; do
    name=$([ "$mode" = true ] && echo "twin_s$s" || echo "notwin_s$s")
    dom=$((dom + 1))
    ROS_DOMAIN_ID=$dom timeout 1500 ros2 launch agrobo_sim season.launch.py \
      twin_guided:=$mode seed:=$s run_name:=$name output_dir:="$OUT" > "$OUT/$name.log" 2>&1 &
    pids+=($!)
  done
  wait "${pids[@]}"
  echo "seed $s done"
done
