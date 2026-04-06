#!/bin/bash
# Health-check wait script for Inspect sandbox setup.
# Polls the bridge service until it reports ready, or times out after 3 minutes.

for i in $(seq 1 90); do
    if /opt/fle-venv/bin/python3 /opt/fle/bridge_client.py health 2>/dev/null | grep -q '"status"'; then
        echo "Bridge service ready."
        exit 0
    fi
    sleep 2
done

echo "ERROR: Bridge service did not become ready within 3 minutes."
exit 1
