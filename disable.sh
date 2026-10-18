#!/bin/bash

# make sure to run with root
if [ "$EUID" -ne 0 ]; then
    echo "run as sudo or root"
    exit 1
fi

systemctl stop frame
systemctl disable frame

systemctl stop trigger
systemctl disable trigger