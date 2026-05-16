# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ARG BLOCKED_HOSTS="bastion.example.com,vault.example.com"

ENV BLOCKED_HOSTS=${BLOCKED_HOSTS} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir mcp \
    && groupadd --system --gid 1000 mcp \
    && useradd --system --uid 1000 --gid 1000 \
        --home-dir /home/mcp --create-home --shell /bin/bash mcp \
    && mkdir -p /workspace \
    && chown mcp:mcp /workspace

COPY docker/entrypoint.py     /usr/local/bin/shell-mcp-entrypoint
COPY docker/shell-mcp-launch.py /usr/local/bin/shell-mcp-launch
RUN chmod 0755 /usr/local/bin/shell-mcp-entrypoint /usr/local/bin/shell-mcp-launch

WORKDIR /workspace

# 2 段構成のエントリポイント (上から「固める → serve」と読める):
#   1. shell-mcp-entrypoint が root で起動 → $BLOCKED_HOSTS を /etc/hosts に追記
#      → setuid(1000) → argv[1:] を exec
#   2. その先で shell-mcp-launch が非特権 mcp ユーザーとして MCP stdio を serve
ENTRYPOINT ["/usr/local/bin/shell-mcp-entrypoint", \
            "/usr/local/bin/shell-mcp-launch", "--shell", "bash", "/bin/bash"]
