#!/bin/sh
# Concatenate rendered segments and mux the score into out/agrobo-film.mp4
cd "$(dirname "$0")/../out" || exit 1
printf "file 'seg0.mp4'\nfile 'seg1.mp4'\nfile 'seg2.mp4'\nfile 'seg3.mp4'\n" > segs/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i segs/list.txt -i score.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -movflags +faststart -shortest agrobo-film.mp4
