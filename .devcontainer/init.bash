#!/bin/bash

if [ ! -f /var/lib/apt/periodic/update-success-stamp ] || [ $(($(date +%s) - $(date +%s -r /var/lib/apt/periodic/update-success-stamp))) -gt 86400 ]; then
    sudo apt-get update
fi

sudo apt-get install -y entr

[ -d env ] || python3 -m venv env && ./env/bin/pip install -U pip

./env/bin/pip install -e ".[dev,test]"
