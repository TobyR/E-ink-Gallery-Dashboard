#!/bin/bash

set -e

FRAME_SOURCE="./frame"
FRAME_TARGET="/opt/frame"
FRAME_SERVICE="./services/frame.service"

TRIGGER_SOURCE="./trigger"
TRIGGER_TARGET="/opt/trigger"
TRIGGER_SERVICE_TIMER="./services/trigger.timer"
TRIGGER_SERVICE="./services/trigger.service"

# make sure to run with root
if [ "$EUID" -ne 0 ]; then
    echo "run as sudo or root"
    exit 1
fi

# 1 source, 2 target, 3 service location, 4 service timer (optional)
setup() {
    # mkdir if not exist
    mkdir -p "$2"

    # copy from source to target, excluding config files if they exist
    rsync -av --exclude='config.json' --exclude='config.json.bak' "$1/" "$2/"

    # ensure permissions are correct
    chown -R root:root "$2"
    chmod -R 755 "$2"

    # copy timer if exists
    if [ -n "$4" ]; then
        cp "$3" "/etc/systemd/system/"
        cp "$4" "/etc/systemd/system/"
        systemctl daemon-reload
        systemctl enable --now "$(basename "$4")"
    else
        # copy and enable service
        cp "$3" "/etc/systemd/system/"
        systemctl daemon-reload
        systemctl enable --now "$(basename "$3")"
    fi

    echo "$3 started"
}

setup "${FRAME_SOURCE}" "${FRAME_TARGET}" "${FRAME_SERVICE}"
setup "${TRIGGER_SOURCE}" "${TRIGGER_TARGET}" "${TRIGGER_SERVICE}" "${TRIGGER_SERVICE_TIMER}"

echo "done."
