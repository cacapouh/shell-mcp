#!/usr/local/bin/python3
"""コンテナの起動エントリポイント: root として $BLOCKED_HOSTS を /etc/hosts に
追記し、mcp ユーザー (uid=1000) に setuid してから sys.argv[1:] を非特権で
exec する。

MCP サーバー本体と切り出してあるのは、特権境界を Dockerfile から一目で読める
ようにするため — `ENTRYPOINT ["shell-mcp-entrypoint", "shell-mcp-launch", ...]`
がそのまま「固める → 非 root で serve」という流れを表す。
"""
import os
import sys

# /etc/hosts は `docker build` 中は read-only でバインドマウントされるため、
# ブロック追記は起動時にしか行えず、その操作には root が必要。下の setuid()
# こそがブロックを意味のあるものにしている — これを忘れると serve 側の
# シェルが `echo` や `sed` で書き戻せてしまい、BLOCKED_HOSTS は飾りになる。
for h in filter(None, (s.strip() for s in os.environ.get("BLOCKED_HOSTS", "").split(","))):
    with open("/etc/hosts", "a") as f:
        f.write(f"127.0.0.1 {h}\n")

os.setgroups([])
os.setgid(1000)
os.setuid(1000)

os.execv(sys.argv[1], sys.argv[1:])
