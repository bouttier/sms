#!/bin/bash

let rand=$RANDOM*2048+10000000
wget http://127.0.0.1:13756/?phone=06$rand\&text=Hello%20guess%20$RANDOM\&moderate=yes -O - -q
let rand=$RANDOM*2048+10000000
wget http://127.0.0.1:13756/?phone=06$rand\&text=Hello%20guess%20$RANDOM\&moderate=no -O - -q
