#!/bin/bash
echo "Updating FreshCutGrass service daemon."
chmod 644 /lib/systemd/system/FreshCutGrass.service
systemctl daemon-reload
