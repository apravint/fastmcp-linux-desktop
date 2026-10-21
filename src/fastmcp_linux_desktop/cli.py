"""
CLI Entrypoint for fastmcp-linux-desktop
"""

import os
import sys
import json
import argparse
from .server import create_server


def get_default_config_path(client: str) -> str:
    """Return default client configuration file path for Linux / macOS."""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        if client == "claude":
            return os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json")
        elif client == "cursor":
            return os.path.join(home, ".cursor", "mcp.json")
    elif sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA", home)
        if client == "claude":
            return os.path.join(appdata, "Claude", "claude_desktop_config.json")
        elif client == "cursor":
            return os.path.join(home, ".cursor", "mcp.json")
    else:  # Linux / Unix
        if client == "claude":
            return os.path.join(home, ".config", "Claude", "claude_desktop_config.json")
        elif client == "cursor":
            return os.path.join(home, ".cursor", "mcp.json")
    return os.path.join(home, f"{client}_mcp_config.json")


def generate_config(
    client: str = "claude",
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8991,
    server_name: str = "linux-desktop"
) -> dict:
    """Generate MCP client configuration dictionary."""
    if transport == "sse":
        server_entry = {
            "url": f"http://{host}:{port}/sse"
        }
    else:
        server_entry = {
            "command": "fastmcp-linux-desktop",
            "args": ["--transport", "stdio"]
        }

    return {
        "mcpServers": {
            server_name: server_entry
        }
    }


def install_config(client: str, config_dict: dict, target_path: str = None) -> tuple[str, str | None]:
    """Install or merge configuration into client config file."""
    if not target_path:
        target_path = get_default_config_path(client)

    target_path = os.path.abspath(os.path.expanduser(target_path))
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    backup_path = None
    existing = {}
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

        backup_path = f"{target_path}.bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

    if "mcpServers" not in existing:
        existing["mcpServers"] = {}

    existing["mcpServers"].update(config_dict["mcpServers"])

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return target_path, backup_path


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

    subparsers = parser.add_subparsers(dest="subcommand", help="Optional subcommands")

    # config subcommand
    config_parser = subparsers.add_parser("config", help="Generate or install MCP configuration for Claude, Cursor, etc.")
    config_parser.add_argument("--claude", action="store_true", help="Format configuration for Claude Desktop")
    config_parser.add_argument("--cursor", action="store_true", help="Format configuration for Cursor")
    config_parser.add_argument("--json", action="store_true", help="Format configuration as generic JSON")
    config_parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio", help="MCP transport mode (default: stdio)")
    config_parser.add_argument("--sse", action="store_true", help="Shortcut for --transport sse")
    config_parser.add_argument("--host", default="127.0.0.1", help="SSE host (default: 127.0.0.1)")
    config_parser.add_argument("--port", type=int, default=8991, help="SSE port (default: 8991)")
    config_parser.add_argument("--name", default="linux-desktop", help="Server identifier key (default: linux-desktop)")
    config_parser.add_argument("-w", "--write", action="store_true", help="Safely write or merge into client config file")
    config_parser.add_argument("--path", default=None, help="Custom destination config file path when using --write")

    args = parser.parse_args()

    if args.subcommand == "config":
        client = "claude"
        if args.cursor:
            client = "cursor"
        elif args.json:
            client = "json"

        transport = "sse" if args.sse else args.transport
        config_data = generate_config(
            client=client,
            transport=transport,
            host=args.host,
            port=args.port,
            server_name=args.name
        )

        formatted_json = json.dumps(config_data, indent=2)

        if args.write:
            saved_path, bak_path = install_config(client, config_data, args.path)
            print(f"Successfully configured FastMCP for {client.capitalize()}!", file=sys.stderr)
            print(f"Target: {saved_path}", file=sys.stderr)
            if bak_path:
                print(f"Backup created: {bak_path}", file=sys.stderr)
        else:
            print(formatted_json)
        return

    # Server execution mode
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
