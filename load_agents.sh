#!/bin/bash

# start 100 instances of the program in background
for i in {1..100}
do
    ./agent &
done

# wait a little
sleep 180

# get the PIDs of all running instances of the program
pids=$(pgrep -f agent)

# kill all instances of the program as fail safe
for pid in $pids
do
    kill -9 $pid
done