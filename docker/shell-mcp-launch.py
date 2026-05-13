#!/usr/local/bin/python3
"""Stdio MCP server: one tool `execute_command`.

When started as root (the container's default), the launcher first appends
$BLOCKED_HOSTS to /etc/hosts as 127.0.0.1 entries and then setuid()s to the
mcp user before serving. Outside the container (non-root) the harden/drop
steps are skipped, so this script is also runnable directly for local tests.
"""
import argparse
import asyncio
import os

from mcp.server.fastmcp import FastMCP

TIMEOUT = 30
MCP_UID = 1000
MCP_GID = 1000
HOSTS_MARK_BEGIN = "# shell-mcp-blocked:begin"
HOSTS_MARK_END = "# shell-mcp-blocked:end"


def harden_hosts() -> None:
    blocked = [h.strip() for h in os.environ.get("BLOCKED_HOSTS", "").split(",") if h.strip()]
    if blocked:
        with open("/etc/hosts") as f:
            existing = f.read()
        if HOSTS_MARK_BEGIN not in existing:
            with open("/etc/hosts", "a") as f:
                f.write(f"\n{HOSTS_MARK_BEGIN}\n")
                for h in blocked:
                    f.write(f"127.0.0.1 {h}\n")
                f.write(f"{HOSTS_MARK_END}\n")
    os.chown("/etc/hosts", 0, 0)
    os.chmod("/etc/hosts", 0o644)


def drop_privs() -> None:
    os.initgroups("mcp", MCP_GID)
    os.setgid(MCP_GID)
    os.setuid(MCP_UID)


if os.geteuid() == 0:
    harden_hosts()
    drop_privs()

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
