# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ARG BLOCKED_HOSTS="bastion.example.com,vault.example.com"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# bash for the actual shell, util-linux for setpriv (privilege drop in
# entrypoint), ca-certificates so anything the agent legitimately reaches
# out to over TLS still works.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir shell-mcp-server

# Bake the block list into the image. Docker bind-mounts /etc/hosts
# read-only during build, so we can't write to it here — we stash the
# entries in /etc/blocked_hosts.list and the entrypoint applies them at
# container start.
RUN set -eu; \
    { \
        echo "# shell-mcp-blocked:begin"; \
        IFS=','; \
        for host in ${BLOCKED_HOSTS}; do \
            trimmed="$(echo "$host" | tr -d '[:space:]')"; \
            if [ -n "$trimmed" ]; then \
                echo "127.0.0.1 $trimmed"; \
            fi; \
        done; \
        echo "# shell-mcp-blocked:end"; \
    } > /etc/blocked_hosts.list \
    && chown root:root /etc/blocked_hosts.list \
    && chmod 0644 /etc/blocked_hosts.list

RUN groupadd --system --gid 1000 mcp \
    && useradd --system --uid 1000 --gid 1000 \
        --home-dir /home/mcp --create-home \
        --shell /bin/bash mcp \
    && mkdir -p /workspace \
    && chown -R mcp:mcp /workspace

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY docker/shell-mcp-launch.py /usr/local/bin/shell-mcp-launch
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/shell-mcp-launch \
    && chown root:root /usr/local/bin/entrypoint.sh /usr/local/bin/shell-mcp-launch

WORKDIR /workspace

# Entrypoint runs as root just long enough to lock down /etc/hosts, then
# setprivs into uid=1000 before exec-ing the MCP server. The shell the
# agent gets is always unprivileged.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
