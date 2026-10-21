#!/bin/bash
# Renders every photoreal shot in sequence. Log: v3/frames/queue.log
cd /mnt/project-files/agrobo-film/v3/scenes
PY=/tmp/claude-0/bvenv/bin/python
LOG=/mnt/project-files/agrobo-film/v3/frames/queue.log
run() { echo "$(date +%T) start $*" >> $LOG; $PY shots.py "$@" > /tmp/claude-0/b3d/q_$1.log 2>&1; echo "$(date +%T) done $1 rc=$?" >> $LOG; }
run dawn 1 84 8 1280 720
run harvest 1 120 8 1280 720
run cultivate 1 144 8 1280 720
run till 1 108 8 1280 720
run pack 1 120 8 1280 720
echo "$(date +%T) ALL DONE" >> $LOG
