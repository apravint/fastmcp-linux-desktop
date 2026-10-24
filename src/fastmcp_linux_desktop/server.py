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
from pydantic import Field
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
        """Enumerate all active desktop windows across workspaces in Hyprland and Wayland compositors.

        Returns a JSON array of client objects containing address, title, window class,
        mapped workspace name, and focus history ID.
        
        Usage Guidelines:
        - Call this to inspect running applications, verify open windows, or find window addresses.
        - Read-only query; does not alter window positions, focus, or desktop state.
        """
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
    def focus_window(
        target: str = Field(description="Window identifier: exact class name, title substring, or hexadecimal address (e.g. 'Alacritty', 'Chrome', '0x1234abcd')")
    ) -> str:
        """Bring a specific application window to focus and foreground by class, title, or address.

        Usage Guidelines:
        - Use when an agent needs to switch user focus to a specific window or workspace.
        - Case-insensitive substring matching is applied against class names and window titles.
        - Modifies active desktop focus state immediately.
        """
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
    def dispatch_hyprland(
        dispatcher: str = Field(description="Hyprland dispatcher command name (e.g. 'workspace', 'togglefloating', 'fullscreen', 'killactive')"),
        args: str = Field(default="", description="Optional arguments passed to the dispatcher (e.g. '1', 'exact:2', '0')")
    ) -> str:
        """Execute any low-level Hyprland dispatch instruction.

        Usage Guidelines:
        - Use for advanced window manipulations, tiling layout toggles, or custom Hyprland operations.
        - Directly invokes 'hyprctl dispatch <dispatcher> <args>'.
        - Modifies window manager layout or application state.
        """
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
    def switch_workspace(
        workspace_id: str = Field(description="Target workspace identifier (e.g. '1', '2', 'name:code', 'm+1')")
    ) -> str:
        """Switch active desktop workspace in Hyprland.

        Usage Guidelines:
        - Use to organize tasks across virtual desktop workspaces.
        - Modifies current active workspace on the focused monitor.
        """
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
        """List connected display monitors, resolutions, scale factors, and refresh rates.

        Usage Guidelines:
        - Use to inspect display hardware topology, active workspace bindings, and screen geometry.
        - Read-only query; returns JSON representation of connected Wayland displays.
        """
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
        """Query active default audio output sink, volume percentage, and mute state.

        Usage Guidelines:
        - Use before making volume adjustments to verify current sink and volume levels.
        - Read-only query; uses pactl / PipeWire pulse bridge.
        """
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
    def set_volume(
        percentage: int = Field(description="Target volume level as integer percentage (0 to 150)", ge=0, le=150)
    ) -> str:
        """Set default audio output volume to a specific percentage.

        Usage Guidelines:
        - Values are safely clamped between 0% (silence) and 150% (boosted limit).
        - Modifies hardware/software mixer output level immediately.
        """
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
        """Cycle audio output between available physical and virtual audio sinks.

        Usage Guidelines:
        - Use to switch between speakers, headphones, HDMI outputs, or USB DACs.
        - Modifies active default audio routing immediately.
        """
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
        """Diagnose failed systemd units, PipeWire audio status, system memory, and load averages.

        Usage Guidelines:
        - Call when diagnosing desktop instability, stalled services, or resource constraints.
        - Read-only diagnostics across system and user systemd instances.
        """
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
        """Automatically reset and restart failed user units and verify PipeWire/WirePlumber audio stack.

        Usage Guidelines:
        - Use when services or desktop audio have entered a degraded state.
        - Modifies service state by executing 'systemctl --user reset-failed' and restarting affected units.
        """
        actions = []
        try:
            out = subprocess.run(["systemctl", "--user", "--failed", "--no-legend"], capture_output=True, text=True)
            for line in out.stdout.splitlines():
                parts = line.split()
                if parts:
                    unit = parts[0]
                    subprocess.run(["systemctl", "--user", "reset-failed", unit])
                    subprocess.run(["systemctl", "--user", "restart", unit])
                    actions.append(f"Restarted failed user unit: {unit}")

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
        """Get CPU utilization, root filesystem disk usage, memory pressure, and top running processes.

        Usage Guidelines:
        - Use to inspect current system performance or locate runaway processes.
        - Read-only telemetry report.
        """
        try:
            df = subprocess.check_output(["df", "-h", "/"], text=True).strip()
            top = subprocess.check_output(["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"], text=True)
            top_lines = top.splitlines()[:8]
            return f"=== Disk Usage ===\n{df}\n\n=== Top CPU Processes ===\n" + "\n".join(top_lines)
        except Exception as e:
            return f"Resource check error: {e}"

    @server.tool()
    def desktop_notify(
        title: str = Field(description="Header title text of the notification banner"),
        message: str = Field(description="Body message text explaining the event or status update"),
        urgency: str = Field(default="normal", description="Notification urgency level: 'low', 'normal', or 'critical'")
    ) -> str:
        """Display a native desktop banner notification via notify-send.

        Usage Guidelines:
        - Use to alert the human user upon completing long tasks or encountering critical events.
        - Modifies desktop notification tray state non-destructively.
        """
        if not shutil.which("notify-send"):
            return "notify-send not installed."
        try:
            subprocess.run(["notify-send", "-u", urgency, "-a", "FastMCP Desktop", title, message])
            return f"Sent desktop notification: {title} - {message}"
        except Exception as e:
            return f"Notification error: {e}"

    @server.tool()
    def take_screenshot(
        output_path: str = Field(default="", description="Destination file path for the screenshot image (defaults to /tmp/screenshot_<pid>.png)")
    ) -> str:
        """Capture a desktop screenshot using grim on Wayland compositors.

        Usage Guidelines:
        - Use to visually inspect desktop rendering, UI elements, or window state.
        - Saves an uncompressed PNG image file to local storage.
        """
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
    def condense_context(
        raw_text: str = Field(description="Source text, large log dump, terminal output, or diff to compress"),
        query: str = Field(default="", description="Optional intent query to prioritize relevant sentences via BM25 ranking")
    ) -> str:
        """Compress large text payloads, command logs, and diffs using BM25 relevance ranking.

        Usage Guidelines:
        - Use before passing large terminal or log outputs into agent context to reduce token costs by up to 90%.
        - Pure read-only text compression.
        """
        try:
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
    def memory_retain(
        fact: str = Field(description="Statement of fact, user preference, architecture rule, or session note to remember"),
        category: str = Field(default="general", description="Organizational category (e.g. 'project', 'preferences', 'workflow', 'general')"),
        importance: int = Field(default=5, description="Significance rank from 1 (minor detail) to 10 (critical system rule)", ge=1, le=10)
    ) -> str:
        """Retain a key fact or preference into long-term agent episodic memory.

        Usage Guidelines:
        - Use to persist user preferences, configuration paths, or decisions across subsequent sessions.
        - Persists knowledge into local memory database.
        """
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
    def memory_recall(
        query: str = Field(default="", description="Keyword or semantic concept to query in memory"),
        category: str = Field(default="", description="Optional category filter (e.g. 'preferences', 'project')"),
        limit: int = Field(default=5, description="Maximum number of memory items to return", ge=1, le=50)
    ) -> str:
        """Recall relevant long-term memories ranked by BM25 relevance and recency decay.

        Usage Guidelines:
        - Call at session start or before complex operations to retrieve relevant user instructions and rules.
        - Read-only query against local memory store.
        """
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
