#!/usr/local/bin/python3
"""Launcher for shell-mcp-server 0.1.0.

Upstream's console_scripts entry calls `sys.exit(main())` but `main` is an
async coroutine — the result is the process exits immediately without ever
serving stdio. We don't patch the package (per project scope), we just call
it correctly from out here.
"""
import asyncio
import sys

from shell_mcp_server.server import main


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
