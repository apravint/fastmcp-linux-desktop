# 🖥️ fastmcp-linux-desktop

[![CI](https://github.com/apravint/fastmcp-linux-desktop/actions/workflows/ci.yml/badge.svg)](https://github.com/apravint/fastmcp-linux-desktop/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0+-purple.svg)](https://github.com/jlowin/fastmcp)
[![Glama Score](https://glama.ai/mcp/servers/apravint/fastmcp-linux-desktop/badges/score.svg)](https://glama.ai/mcp/servers/apravint/fastmcp-linux-desktop)

> **High-performance FastMCP Server empowering AI Agents (Claude Desktop, Cursor, Antigravity, OpenRig) with native Linux desktop and compositor control.**  
> Provides deep primitives for Hyprland/Wayland window management, PipeWire audio routing, systemd health diagnosis and self-healing, notifications, and long-term agent memory.

---

## ⚡ Features & MCP Tool Catalog

### 🪟 Wayland & Hyprland Window Management
- `get_windows()`: Enumerate all active windows, classes, floating status, and workspace geometry.
- `focus_window(target)`: Focus window by title, class, or hex address (e.g. `Alacritty`, `Chrome`).
- `dispatch_hyprland(dispatcher, args)`: Run any arbitrary `hyprctl dispatch` instruction.
- `switch_workspace(workspace_id)`: Switch workspace dynamically.
- `get_monitors()`: List connected outputs, resolutions, scale factors, and refresh rates.

### 🔊 Audio & DSP Routing
- `get_audio_status()`: Query default sink volume, mute state, and driver.
- `set_volume(percentage)`: Smoothly adjust sink volume (0-150%).
- `toggle_audio_sink()`: Cycle audio output between HDMI, line-out, headphones, or Bluetooth.

### 🩺 System Diagnostics & Self-Healing
- `get_system_health()`: Instant diagnosis of failed system/user systemd units, load, and RAM.
- `heal_system()`: Automatically reset-failed and restart degraded units, recovering audio if stalled.
- `get_resource_usage()`: View filesystem disk usage and top CPU/memory consuming processes.
- `desktop_notify(title, message, urgency)`: Trigger native desktop notifications via `notify-send`.
- `take_screenshot(output_path)`: Capture Wayland screenshots using `grim`.

### 🧠 Agentic Memory & Context (Optional)
- `condense_context(raw_text, query)`: Real-time BM25 context compression (up to 98% token reduction) via `context-condenser`.
- `memory_retain(fact, category, importance)`: Long-term episodic memory storage via `agent-hindsight`.
- `memory_recall(query, category, limit)`: Fast memory retrieval with recency decay.

---

## 🚀 Installation & Usage

### 1. Install via pip

```bash
pip install fastmcp-linux-desktop
```

### 2. Connect to Claude Desktop / Cursor / Antigravity

Generate configuration or install automatically with one command:

```bash
# Print configuration JSON
fastmcp-linux-desktop config --claude
fastmcp-linux-desktop config --cursor --sse

# Automatically merge into client config file with safe timestamped backup:
fastmcp-linux-desktop config --claude --write
```

Manual configuration block for `claude_desktop_config.json` or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "linux-desktop": {
      "command": "fastmcp-linux-desktop",
      "args": ["--transport", "stdio"]
    }
  }
}
```

### 3. Run as a Persistent Daemon (SSE / HTTP)

```bash
# Run over SSE on port 8991
fastmcp-linux-desktop --sse --port 8991

# Or run as a systemd user service
systemctl --user enable --now fastmcp-linux-desktop.service
```

---

## 🔧 Systemd User Unit Example

Create `~/.config/systemd/user/fastmcp-linux-desktop.service`:

```ini
[Unit]
Description=FastMCP Linux Desktop MCP Server
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/fastmcp-linux-desktop --sse --port 8991
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

---

## 🧪 Testing

```bash
python3 -m unittest discover tests
```

---

## 📄 License

MIT License. Designed and maintained by [apravint](https://github.com/apravint).
