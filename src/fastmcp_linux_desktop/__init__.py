"""
fastmcp-linux-desktop: FastMCP Model Context Protocol Server for Linux Desktops (Hyprland, Wayland, PipeWire, Systemd).
"""

__version__ = "0.1.0"

from .server import mcp, create_server

__all__ = ["mcp", "create_server", "__version__"]
