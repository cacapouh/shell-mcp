#!/bin/sh
# Apply the baked-in /etc/hosts block list, then drop privileges to mcp
# and exec the MCP server (or whatever command was passed as CMD).
#
# Why this exists: Docker bind-mounts /etc/hosts read-only during `docker
# build`, so the block list has to be applied at container start. We do it
# here under root, lock the file down, then setpriv into uid 1000 — the
# shell the agent gets via MCP is unprivileged and cannot touch /etc/hosts.

set -eu

BLOCKED_LIST="/etc/blocked_hosts.list"

if [ ! -f "${BLOCKED_LIST}" ]; then
    echo "shell-mcp-blocked: ${BLOCKED_LIST} missing — refusing to start" >&2
    exit 1
fi

# Append the baked list to /etc/hosts (idempotent: if the marker is already
# there from a prior start in the same container, skip).
if ! grep -q "shell-mcp-blocked:begin" /etc/hosts 2>/dev/null; then
    cat "${BLOCKED_LIST}" >> /etc/hosts
fi
chown root:root /etc/hosts
chmod 0644 /etc/hosts

# Default command is the MCP server (via our launcher that wraps
# upstream's async main in asyncio.run — see docker/shell-mcp-launch.py).
# Tests / debugging can override by passing a CMD to `docker run`.
# Either way we drop privs first.
if [ "$#" -eq 0 ]; then
    set -- shell-mcp-launch /workspace --shell bash /bin/bash
fi

exec setpriv \
    --reuid=mcp --regid=mcp --init-groups \
    --inh-caps=-all \
    -- "$@"
