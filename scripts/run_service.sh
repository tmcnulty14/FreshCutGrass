#!/bin/bash
echo "Running Fresh Cut Grass"
nohup /usr/local/bin/python3.9 /home/ec2-user/fresh-cut-grass/main/main.py 1>/dev/null 2>/dev/null &