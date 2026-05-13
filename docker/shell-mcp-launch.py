#!/usr/local/bin/python3
"""Minimal stdio MCP server with one tool: execute_command(command, shell, cwd).

Replaces the upstream shell-mcp-server with a direct FastMCP implementation —
same CLI surface (`directories... --shell name path`) and same tool schema,
but ~30 lines and no asyncio-wrapper workaround needed.
"""
import argparse
import asyncio
import os

from mcp.server.fastmcp import FastMCP

TIMEOUT = 30

ap = argparse.ArgumentParser(description="Shell MCP Server")
ap.add_argument("directories", nargs="+", help="Allowed directories for command execution")
ap.add_argument("--shell", action="append", nargs=2, metavar=("name", "path"),
                default=[], help="Shell specification: name path")
args = ap.parse_args()

ALLOWED = [os.path.abspath(d) for d in args.directories]
SHELLS = dict(args.shell) or {"bash": "/bin/bash", "sh": "/bin/sh"}

mcp = FastMCP("shell-mcp-server")


@mcp.tool(description=f"Execute a shell command in a specified directory using a specified shell. Available shells: {list(SHELLS)}")
async def execute_command(command: str, shell: str, cwd: str) -> dict:
    abs_cwd = os.path.abspath(cwd)
    if not any(abs_cwd == d or abs_cwd.startswith(d + os.sep) for d in ALLOWED):
        raise ValueError(f"Directory '{cwd}' is not in the allowed directories list")
    if shell not in SHELLS:
        raise ValueError(f"Shell '{shell}' is not allowed. Available shells: {list(SHELLS)}")

    p = await asyncio.create_subprocess_exec(
        SHELLS[shell], "-c", command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=abs_cwd,
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
        "cwd": abs_cwd,
    }


if __name__ == "__main__":
    mcp.run()
