#!/bin/bash

while true; do
    let rand=$RANDOM*2048+10000000
    wget http://127.0.0.1:13756/?phone=06$rand\&text=Hello%20guess%20$RANDOM\&moderate=yes -O - -q
    sleep 1
    let rand=$RANDOM*2048+10000000
    wget http://127.0.0.1:13756/?phone=06$rand\&text=Hello%20guess%20$RANDOM\&moderate=no -O - -q
    sleep 1
done
