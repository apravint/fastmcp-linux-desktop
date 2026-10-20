"""
CLI Entrypoint for fastmcp-linux-desktop
"""

import os
import sys
import argparse
from .server import create_server

def main():
    parser = argparse.ArgumentParser(
        prog="fastmcp-linux-desktop",
        description="FastMCP Linux Desktop Control Server (Hyprland, PipeWire, Systemd, Agent Memory)"
    )
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio", help="MCP transport mode (default: stdio)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8991, help="Port to listen on for sse/http (default: 8991)")
    parser.add_argument("--sse", action="store_true", help="Shortcut for --transport sse")
    parser.add_argument("--http", action="store_true", help="Shortcut for --transport http")

    args = parser.parse_args()

    transport = args.transport
    if args.sse:
        transport = "sse"
    elif args.http:
        transport = "http"

    server = create_server()

    if transport == "sse":
        print(f"Starting FastMCP Desktop server via SSE on http://{args.host}:{args.port}/sse ...", file=sys.stderr)
        server.run(transport="sse", host=args.host, port=args.port)
    elif transport == "http":
        print(f"Starting FastMCP Desktop server via HTTP on http://{args.host}:{args.port} ...", file=sys.stderr)
        server.run(transport="http", host=args.host, port=args.port)
    else:
        server.run()

if __name__ == "__main__":
    main()
