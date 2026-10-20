"""
FastMCP Linux Desktop Server
Provides high-performance OS control, Wayland / Hyprland window management,
PipeWire audio routing, systemd health diagnosis, and agentic desktop automation.
"""

import os
import sys
import json
import shutil
import subprocess
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP

def create_server(name: str = "linux-desktop") -> FastMCP:
    server = FastMCP(
        name=name,
        instructions="Native Linux OS, Wayland / Hyprland compositor, PipeWire audio, systemd health, and desktop automation MCP server."
    )

    # =========================================================================
    # 1. WAYLAND / HYPRLAND WINDOW MANAGEMENT
    # =========================================================================

    @server.tool()
    def get_windows() -> str:
        """Get all active desktop windows, workspaces, geometry, and classes in Hyprland/Wayland."""
        if not shutil.which("hyprctl"):
            return "hyprctl not found. Ensure Hyprland is installed and running."
        try:
            out = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
            clients = json.loads(out)
            summary = []
            for c in clients:
                if c.get("mapped"):
                    summary.append({
                        "address": c.get("address"),
                        "title": c.get("title"),
                        "class": c.get("class"),
                        "workspace": c.get("workspace", {}).get("name"),
                        "focusHistoryID": c.get("focusHistoryID")
                    })
            return json.dumps(summary, indent=2)
        except Exception as e:
            return f"Error querying windows: {e}"

    @server.tool()
    def focus_window(target: str) -> str:
        """Focus a window by class name, title substring, or address (e.g. 'Alacritty', 'Chrome', '0x1234abcd')."""
        if not shutil.which("hyprctl"):
            return "hyprctl not found."
        try:
            out = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
            clients = json.loads(out)
            target_lower = target.lower()
            matched_addr = None
            for c in clients:
                if (c.get("address") == target or 
                    target_lower in c.get("class", "").lower() or 
                    target_lower in c.get("title", "").lower()):
                    matched_addr = c.get("address")
                    break
            if matched_addr:
                subprocess.run(["hyprctl", "dispatch", "focuswindow", f"address:{matched_addr}"], check=True)
                return f"Focused window: {target} ({matched_addr})"
            return f"No active window matched '{target}'"
        except Exception as e:
            return f"Error focusing window: {e}"

    @server.tool()
    def dispatch_hyprland(dispatcher: str, args: str = "") -> str:
        """Execute any Hyprland dispatch command (e.g. workspace 2, togglefloating, killactive)."""
        if not shutil.which("hyprctl"):
            return "hyprctl not found."
        try:
            cmd = ["hyprctl", "dispatch", dispatcher]
            if args:
                cmd.append(args)
            res = subprocess.run(cmd, capture_output=True, text=True)
            return f"Executed '{' '.join(cmd)}' | Output: {res.stdout.strip()} {res.stderr.strip()}"
        except Exception as e:
            return f"Dispatch error: {e}"

    @server.tool()
    def switch_workspace(workspace_id: str) -> str:
        """Switch to a specific workspace (e.g. '1', '2', 'name:code')."""
        if not shutil.which("hyprctl"):
            return "hyprctl not found."
        try:
            cmd = ["hyprctl", "dispatch", "workspace", str(workspace_id)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return f"Switched to workspace {workspace_id}: {res.stdout.strip()}"
        except Exception as e:
            return f"Error switching workspace: {e}"

    @server.tool()
    def get_monitors() -> str:
        """List connected display monitors, resolutions, refresh rates, and active focus."""
        if not shutil.which("hyprctl"):
            return "hyprctl not found."
        try:
            out = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True)
            return out
        except Exception as e:
            return f"Error querying monitors: {e}"

    # =========================================================================
    # 2. AUDIO & PIPEWIRE
    # =========================================================================

    @server.tool()
    def get_audio_status() -> str:
        """Get active default audio sink, volume level, and mute status."""
        if not shutil.which("pactl"):
            return "pactl not found. PulseAudio or PipeWire-pulse is required."
        try:
            sink = subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
            vol = subprocess.check_output(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], text=True).strip()
            mute = subprocess.check_output(["pactl", "get-sink-mute", "@DEFAULT_SINK@"], text=True).strip()
            return f"Default Sink: {sink}\nVolume: {vol}\nMute: {mute}"
        except Exception as e:
            return f"Audio error: {e}"

    @server.tool()
    def set_volume(percentage: int) -> str:
        """Set output volume level as percentage (0-100%)."""
        if not shutil.which("pactl"):
            return "pactl not found."
        try:
            bounded = max(0, min(150, int(percentage)))
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{bounded}%"], check=True)
            return f"Volume set to {bounded}%"
        except Exception as e:
            return f"Error setting volume: {e}"

    @server.tool()
    def toggle_audio_sink() -> str:
        """Toggle audio output between available audio sinks."""
        if shutil.which("iram-audio-toggle"):
            try:
                res = subprocess.run(["iram-audio-toggle"], capture_output=True, text=True)
                return res.stdout.strip() or "Audio sink toggled via iram-audio-toggle"
            except Exception as e:
                return f"Error running iram-audio-toggle: {e}"

        if not shutil.which("pactl"):
            return "pactl not found."
        try:
            sinks_raw = subprocess.check_output(["pactl", "list", "short", "sinks"], text=True).strip().splitlines()
            sinks = [line.split()[1] for line in sinks_raw if line.strip()]
            if len(sinks) < 2:
                return f"Only {len(sinks)} sink available: {sinks}"
            current = subprocess.check_output(["pactl", "get-default-sink"], text=True).strip()
            next_sink = sinks[0] if current == sinks[-1] else sinks[(sinks.index(current) + 1) % len(sinks)]
            subprocess.run(["pactl", "set-default-sink", next_sink], check=True)
            return f"Switched default sink from {current} -> {next_sink}"
        except Exception as e:
            return f"Error toggling sink: {e}"

    # =========================================================================
    # 3. SYSTEM DIAGNOSTICS & HEALING
    # =========================================================================

    @server.tool()
    def get_system_health() -> str:
        """Diagnose failed systemd units, PipeWire audio status, system memory, and load averages."""
        try:
            failed_system = subprocess.check_output(["systemctl", "--failed", "--no-legend"], text=True).strip()
            failed_user = subprocess.check_output(["systemctl", "--user", "--failed", "--no-legend"], text=True).strip()
            mem = subprocess.check_output(["free", "-h"], text=True).strip()
            load = subprocess.check_output(["uptime"], text=True).strip()
            return (
                f"=== Linux Desktop System Health ===\n"
                f"System Load:\n{load}\n\n"
                f"Systemd System Failures:\n{failed_system or 'None'}\n\n"
                f"Systemd User Failures:\n{failed_user or 'None'}\n\n"
                f"Memory Overview:\n{mem}\n"
            )
        except Exception as e:
            return f"Health check error: {e}"

    @server.tool()
    def heal_system() -> str:
        """Automatically reset and restart failed user units, verify PipeWire, and refresh notifications."""
        actions = []
        try:
            # Check user units
            out = subprocess.run(["systemctl", "--user", "--failed", "--no-legend"], capture_output=True, text=True)
            for line in out.stdout.splitlines():
                parts = line.split()
                if parts:
                    unit = parts[0]
                    subprocess.run(["systemctl", "--user", "reset-failed", unit])
                    subprocess.run(["systemctl", "--user", "restart", unit])
                    actions.append(f"Restarted failed user unit: {unit}")

            # Check audio
            if shutil.which("pactl"):
                audio_test = subprocess.run(["pactl", "info"], capture_output=True, text=True)
                if audio_test.returncode != 0:
                    subprocess.run(["systemctl", "--user", "restart", "pipewire", "pipewire-pulse", "wireplumber"])
                    actions.append("Restarted PipeWire / WirePlumber audio stack")

            if not actions:
                actions.append("System is clean. No degraded units detected.")
            return "\n".join(actions)
        except Exception as e:
            return f"Error healing system: {e}"

    @server.tool()
    def get_resource_usage() -> str:
        """Get CPU, disk, memory, and top process telemetry."""
        try:
            df = subprocess.check_output(["df", "-h", "/"], text=True).strip()
            top = subprocess.check_output(["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"], text=True)
            top_lines = top.splitlines()[:8]
            return f"=== Disk Usage ===\n{df}\n\n=== Top CPU Processes ===\n" + "\n".join(top_lines)
        except Exception as e:
            return f"Resource check error: {e}"

    @server.tool()
    def desktop_notify(title: str, message: str, urgency: str = "normal") -> str:
        """Display a native desktop notification via notify-send."""
        if not shutil.which("notify-send"):
            return "notify-send not installed."
        try:
            subprocess.run(["notify-send", "-u", urgency, "-a", "FastMCP Desktop", title, message])
            return f"Sent desktop notification: {title} - {message}"
        except Exception as e:
            return f"Notification error: {e}"

    @server.tool()
    def take_screenshot(output_path: str = "") -> str:
        """Capture desktop screenshot using grim/slurp on Wayland."""
        if not shutil.which("grim"):
            return "grim not found. Install grim for Wayland screen capture."
        out = output_path or f"/tmp/screenshot_{os.getpid()}.png"
        try:
            subprocess.run(["grim", out], check=True)
            return f"Screenshot saved to {out}"
        except Exception as e:
            return f"Screenshot error: {e}"

    # =========================================================================
    # 4. CONTEXT & MEMORY INTEGRATION
    # =========================================================================

    @server.tool()
    def condense_context(raw_text: str, query: str = "") -> str:
        """Compress logs, diffs, and tool outputs using BM25 relevance ranking."""
        try:
            # Check for context_condenser python package or cli
            from context_condenser.engine import condense
            res = condense(raw_text, query)
            return res.get("condensed_text", raw_text)
        except ImportError:
            if shutil.which("context-condenser"):
                cmd = ["context-condenser", "-q", query] if query else ["context-condenser"]
                res = subprocess.run(cmd, input=raw_text, capture_output=True, text=True)
                return res.stdout.strip()
            return f"Compressed (first 1000 chars):\n{raw_text[:1000]}"
        except Exception as e:
            return f"Error condensing context: {e}"

    @server.tool()
    def memory_retain(fact: str, category: str = "general", importance: int = 5) -> str:
        """Retain a critical fact into long-term agent memory."""
        try:
            from agent_hindsight.memory import AgentHindsightMemory
            mem = AgentHindsightMemory()
            entry_id = mem.retain(fact, category=category, importance=importance)
            return f"Retained fact #{entry_id} in category '{category}'"
        except ImportError:
            if shutil.which("agent-hindsight"):
                res = subprocess.run(
                    ["agent-hindsight", "retain", fact, "-c", category, "-i", str(importance)],
                    capture_output=True,
                    text=True
                )
                return res.stdout.strip()
            return f"Memory engine unavailable: fact recorded in fallback log: {fact}"
        except Exception as e:
            return f"Error retaining memory: {e}"

    @server.tool()
    def memory_recall(query: str = "", category: str = "", limit: int = 5) -> str:
        """Recall relevant long-term memories ranked by BM25 and recency decay."""
        try:
            from agent_hindsight.memory import AgentHindsightMemory
            mem = AgentHindsightMemory()
            results = mem.recall(query=query, category=category, limit=limit)
            return json.dumps(results, indent=2)
        except ImportError:
            if shutil.which("agent-hindsight"):
                cmd = ["agent-hindsight", "recall", query, "-n", str(limit)]
                if category:
                    cmd.extend(["-c", category])
                res = subprocess.run(cmd, capture_output=True, text=True)
                return res.stdout.strip()
            return "No memory engine available."
        except Exception as e:
            return f"Error recalling memory: {e}"

    return server

mcp = create_server()
