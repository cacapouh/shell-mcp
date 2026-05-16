#!/usr/local/bin/python3
"""execute_command(command, shell, cwd) ツールを 1 つだけ公開する stdio MCP サーバー。

すでに非特権の mcp ユーザーとして実行される前提 — 権限降格と /etc/hosts の
ロックダウンは、本スクリプトが exec される前に entrypoint.py が済ませている。
"""
import argparse
import asyncio

from mcp.server.fastmcp import FastMCP

TIMEOUT = 30

ap = argparse.ArgumentParser(description="Shell MCP Server")
ap.add_argument("--shell", action="append", nargs=2, metavar=("name", "path"),
                default=[], help="Shell specification: name path")
args = ap.parse_args()

SHELLS = dict(args.shell) or {"bash": "/bin/bash", "sh": "/bin/sh"}

mcp = FastMCP("shell-mcp-server")


@mcp.tool(description=f"Execute a shell command in a specified directory using a specified shell. Available shells: {list(SHELLS)}")
async def execute_command(command: str, shell: str, cwd: str) -> dict:
    if shell not in SHELLS:
        raise ValueError(f"Shell '{shell}' is not allowed. Available shells: {list(SHELLS)}")

    p = await asyncio.create_subprocess_exec(
        SHELLS[shell], "-c", command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        try:
            p.kill()
            await p.wait()
        except ProcessLookupError:
            pass
        raise TimeoutError(f"Command execution timed out after {TIMEOUT} seconds")

    return {
        "stdout": out.decode(errors="replace"),
        "stderr": err.decode(errors="replace"),
        "exit_code": p.returncode,
        "command": command,
        "shell": shell,
        "cwd": cwd,
    }


if __name__ == "__main__":
    mcp.run()
