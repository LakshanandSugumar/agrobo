#!/bin/bash
# Interpolate 12 fps shots to 24 fps at 1080p, composite overlays, mux score -> out/agrobo-film-v3.mp4
set -e
cd /mnt/project-files/agrobo-film
for s in dawn till cultivate harvest pack; do
  mkdir -p v3/frames/${s}24; rm -f v3/frames/${s}24/f_*.png
  ffmpeg -loglevel error -y -framerate 12 -start_number 1 -i v3/frames/$s/f_%04d.png \
    -vf "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1920:1080:flags=lanczos,unsharp=5:5:0.35" v3/frames/${s}24/f_%04d.png
  echo "$s -> $(ls v3/frames/${s}24 | wc -l) frames"
done
python3 v3/build.py
mkdir -p v3/segs
for w in 0 1 2 3; do node v3/composite.mjs video $w 4 > v3/segs/log$w.txt 2>&1 & done; wait
printf "file 'seg0.mp4'\nfile 'seg1.mp4'\nfile 'seg2.mp4'\nfile 'seg3.mp4'\n" > v3/segs/list.txt
ffmpeg -loglevel error -y -f concat -safe 0 -i v3/segs/list.txt -i out/score.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -movflags +faststart -shortest out/agrobo-film-v3.mp4
ffprobe -v error -show_entries format=duration,size out/agrobo-film-v3.mp4
