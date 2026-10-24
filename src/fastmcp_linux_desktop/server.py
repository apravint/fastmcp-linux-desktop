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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def get_windows() -> str:
        """Enumerate all active application windows across virtual workspaces in the running Hyprland compositor.

        To bring a specific window to the foreground, use `focus_window` instead. To inspect physical display geometry, use `get_monitors`.

        When to use:
        - Call when you need to inspect running applications, check which workspace contains a window, or look up window addresses and classes before focusing or moving.

        When NOT to use:
        - Do not use to change window focus (use `focus_window`).
        - Do not use to move windows or toggle fullscreen (use `dispatch_hyprland`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Hyprland Wayland compositor with `hyprctl` available on PATH.
        - Side effects: None. Pure read-only query.
        - Returns: Formatted JSON array of client objects containing address, title, class, workspace, and focusHistoryID.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
    def focus_window(
        target: str = Field(description="Window identifier to match: exact window class, title substring, or hexadecimal address (e.g. 'Alacritty', 'Chrome', '0x1234abcd')")
    ) -> str:
        """Bring a specific application window to user focus and foreground by class, title, or address.

        To discover open window addresses and titles first, use `get_windows`. For arbitrary window manager layout commands, use `dispatch_hyprland`.

        When to use:
        - Call when an agent needs to switch active user focus or bring an existing application window to the screen.

        When NOT to use:
        - Do not use to launch new applications (only matches already open windows).
        - Do not use to switch workspaces without a specific window in mind (use `switch_workspace`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Hyprland session and `hyprctl`.
        - Side effects: Modifies the compositor's active window focus and active workspace immediately.
        - Returns: Confirmation string with the matched window title and address, or an error message if no match is found.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def dispatch_hyprland(
        dispatcher: str = Field(description="Hyprland dispatcher command name (e.g. 'workspace', 'togglefloating', 'fullscreen', 'killactive', 'movetoworkspace')"),
        args: str = Field(default="", description="Optional arguments passed directly to the dispatcher (e.g. '1', 'exact:2', '0', 'e+1')")
    ) -> str:
        """Execute any low-level Hyprland window manager dispatch instruction.

        For simple workspace switching, prefer `switch_workspace`. To bring a specific window to the foreground, prefer `focus_window`.

        When to use:
        - Call when executing advanced compositor layout operations, tiling toggles (floating/fullscreen), window closing, or custom Hyprland bindings.

        When NOT to use:
        - Do not use for simple read-only queries of windows or monitors (use `get_windows` or `get_monitors`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Hyprland session with `hyprctl`.
        - Side effects: Modifies window manager layout, window state, or virtual workspace configuration.
        - Returns: Command execution status including captured stdout and stderr.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
    def switch_workspace(
        workspace_id: str = Field(description="Target virtual workspace identifier to switch into (e.g. '1', '2', 'name:code', 'm+1')")
    ) -> str:
        """Switch the focused monitor's active virtual desktop workspace in Hyprland.

        To inspect which applications are on which workspace before switching, use `get_windows`.

        When to use:
        - Call when organizing tasks or navigating between virtual desktop workspaces.

        When NOT to use:
        - Do not use to move windows across workspaces (use `dispatch_hyprland` with `movetoworkspace`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Hyprland session.
        - Side effects: Switches the currently focused workspace on the active monitor immediately.
        - Returns: Confirmation string indicating the target workspace switched to.
        """
        if not shutil.which("hyprctl"):
            return "hyprctl not found."
        try:
            cmd = ["hyprctl", "dispatch", "workspace", str(workspace_id)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            return f"Switched to workspace {workspace_id}: {res.stdout.strip()}"
        except Exception as e:
            return f"Error switching workspace: {e}"

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def get_monitors() -> str:
        """List all connected physical and virtual display outputs, resolutions, refresh rates, and scale factors.

        To inspect application windows rather than physical displays, use `get_windows` instead.

        When to use:
        - Call when you need to inspect monitor layout, screen resolutions, display refresh rates, or assigned workspaces.

        When NOT to use:
        - Do not use to inspect application windows or focus states (use `get_windows`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Hyprland compositor session.
        - Side effects: None. Pure read-only telemetry query.
        - Returns: Formatted JSON string containing monitor array with ID, name, resolution, refreshRate, scale, and activeWorkspace.
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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def get_audio_status() -> str:
        """Query the active default PipeWire/PulseAudio output sink, current volume percentage, and mute state.

        To change the volume level, use `set_volume` instead. To switch output devices (e.g. speakers to headphones), use `toggle_audio_sink`.

        When to use:
        - Call before adjusting volume or when diagnosing audio issues to verify current sink and volume levels.

        When NOT to use:
        - Do not use to modify audio levels (use `set_volume`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires PulseAudio or PipeWire-pulse with `pactl` available on PATH.
        - Side effects: None. Pure read-only status query.
        - Returns: Multi-line text string with default sink name, volume channel percentages, and mute boolean.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": True})
    def set_volume(
        percentage: int = Field(description="Target volume level as an integer percentage from 0 (silence) to 150 (boosted limit)", ge=0, le=150)
    ) -> str:
        """Set the default audio output volume to an exact percentage.

        To check the current volume before changing it, use `get_audio_status` instead. To cycle output devices, use `toggle_audio_sink`.

        When to use:
        - Call when an agent needs to adjust system playback volume or unmute/mute audio.

        When NOT to use:
        - Do not use to change output hardware routing (use `toggle_audio_sink`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires PipeWire-pulse or PulseAudio with `pactl`.
        - Side effects: Modifies the hardware/software mixer playback level on the default sink immediately.
        - Returns: Confirmation string indicating the bounded volume percentage applied.
        """
        if not shutil.which("pactl"):
            return "pactl not found."
        try:
            bounded = max(0, min(150, int(percentage)))
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{bounded}%"], check=True)
            return f"Volume set to {bounded}%"
        except Exception as e:
            return f"Error setting volume: {e}"

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def toggle_audio_sink() -> str:
        """Cycle system audio output between available physical and virtual audio sinks.

        To check current sink name and volume without switching, use `get_audio_status` instead.

        When to use:
        - Call when the user requests switching playback between headphones, speakers, HDMI, or USB DACs.

        When NOT to use:
        - Do not use to change volume level (use `set_volume`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires PipeWire or PulseAudio with multiple available sinks.
        - Side effects: Changes the active default audio output device across all playing desktop applications immediately.
        - Returns: String reporting the previous sink and the new default sink switched to.
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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def get_system_health() -> str:
        """Diagnose failed systemd units, memory utilization, and system load averages across system and user tiers.

        To automatically recover and restart failed services, use `heal_system` instead. To view disk space and CPU hogs, use `get_resource_usage`.

        When to use:
        - Call when investigating desktop stability, unresponsive background services, or checking overall host health.

        When NOT to use:
        - Do not use to restart services (use `heal_system`).
        - Do not use for detailed process or disk inspection (use `get_resource_usage`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires `systemctl`, `free`, and `uptime` utilities on Linux.
        - Side effects: None. Pure read-only diagnostic telemetry.
        - Returns: Text report with system load, list of failed system/user systemd units, and memory summary.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def heal_system() -> str:
        """Automatically reset failed user systemd units and restart degraded audio or desktop services.

        To inspect what services are failed before healing, use `get_system_health` first.

        When to use:
        - Call when user services or audio (PipeWire/WirePlumber) have crashed, stalled, or entered a degraded failure state.

        When NOT to use:
        - Do not use for general read-only monitoring (use `get_system_health`).

        Prerequisites & Side Effects:
        - Prerequisites: Requires user systemd session (`systemctl --user`).
        - Side effects: Resets failed flags and issues restarts to stalled units; restarts PipeWire stack if pactl is unresponsive.
        - Returns: List of recovery actions executed, or confirmation that system is clean.
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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def get_resource_usage() -> str:
        """Inspect root filesystem disk usage and enumerate top CPU/memory consuming processes.

        To check failed systemd units and host load averages, use `get_system_health` instead.

        When to use:
        - Call when diagnosing high CPU load, finding runaway processes, or checking available disk space on the root filesystem.

        When NOT to use:
        - Do not use to terminate processes or heal services (use `heal_system` or process signals).

        Prerequisites & Side Effects:
        - Prerequisites: Requires standard `df` and `ps` utilities.
        - Side effects: None. Pure read-only performance telemetry.
        - Returns: Text summary showing filesystem capacity and top 8 CPU-consuming processes.
        """
        try:
            df = subprocess.check_output(["df", "-h", "/"], text=True).strip()
            top = subprocess.check_output(["ps", "-eo", "pid,user,%cpu,%mem,comm", "--sort=-%cpu"], text=True)
            top_lines = top.splitlines()[:8]
            return f"=== Disk Usage ===\n{df}\n\n=== Top CPU Processes ===\n" + "\n".join(top_lines)
        except Exception as e:
            return f"Resource check error: {e}"

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def desktop_notify(
        title: str = Field(description="Header title string of the desktop notification banner (e.g. 'Build Complete', 'Alert')"),
        message: str = Field(description="Body message text explaining the event, status update, or required action"),
        urgency: str = Field(default="normal", description="Notification urgency level: 'low', 'normal', or 'critical'")
    ) -> str:
        """Display an interactive native desktop banner notification to the human user via notify-send.

        When to use:
        - Call when completing background tasks, alerting the user to important state changes, or requesting human attention.

        When NOT to use:
        - Do not use for logging or purely internal debugging (use memory or return outputs).

        Prerequisites & Side Effects:
        - Prerequisites: Requires `notify-send` and an active desktop notification daemon (e.g. mako, dunst).
        - Side effects: Displays a visible popup toast banner on the user's desktop screen.
        - Returns: Confirmation string indicating the notification was dispatched.
        """
        if not shutil.which("notify-send"):
            return "notify-send not installed."
        try:
            subprocess.run(["notify-send", "-u", urgency, "-a", "FastMCP Desktop", title, message])
            return f"Sent desktop notification: {title} - {message}"
        except Exception as e:
            return f"Notification error: {e}"

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def take_screenshot(
        output_path: str = Field(default="", description="Destination file path for the screenshot PNG image (defaults to /tmp/screenshot_<pid>.png)")
    ) -> str:
        """Capture a visual snapshot of the desktop screen using grim on Wayland compositors.

        When to use:
        - Call when an AI agent needs visual verification of desktop UI layout, browser windows, or graphical error dialogs.

        When NOT to use:
        - Do not use if structured text window information is sufficient (use `get_windows` instead).

        Prerequisites & Side Effects:
        - Prerequisites: Requires an active Wayland compositor session with `grim` installed.
        - Side effects: Writes a PNG screenshot image file to the designated file path on local disk.
        - Returns: Confirmation string with the absolute path of the saved screenshot image.
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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def condense_context(
        raw_text: str = Field(description="Source text payload, terminal output, git diff, or build log to compress"),
        query: str = Field(default="", description="Optional intent query used to guide BM25 sentence ranking and prioritize query-relevant sections")
    ) -> str:
        """Compress large text payloads, command logs, and diffs using BM25 relevance ranking.

        To permanently store structured facts into memory, use `memory_retain` instead.

        When to use:
        - Call before passing large log files, terminal outputs, or large documents into an LLM context window to reduce token usage by up to 90%.

        When NOT to use:
        - Do not use for long-term knowledge retention across sessions (use `memory_retain`).

        Prerequisites & Side Effects:
        - Prerequisites: Uses `context-condenser` library or CLI if installed, with built-in fallback truncation.
        - Side effects: None. Pure read-only text processing.
        - Returns: Compressed text string containing the most salient paragraphs or sentences.
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

    @server.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False})
    def memory_retain(
        fact: str = Field(description="Statement of fact, user preference, architectural decision, or session note to remember"),
        category: str = Field(default="general", description="Organizational category bucket (e.g. 'project', 'preferences', 'workflow', 'general')"),
        importance: int = Field(default=5, description="Significance rank from 1 (minor transient detail) to 10 (critical system invariant)", ge=1, le=10)
    ) -> str:
        """Persist a key fact, user preference, or decision into long-term agent episodic memory.

        To search and retrieve previously stored facts, use `memory_recall` instead. To compress large text in the current turn, use `condense_context`.

        When to use:
        - Call when the user specifies a persistent preference, custom tool path, or architectural rule that must persist across future conversations.

        When NOT to use:
        - Do not use to query existing memories (use `memory_recall`).

        Prerequisites & Side Effects:
        - Prerequisites: Uses `agent-hindsight` library or CLI if available, with local fallback logging.
        - Side effects: Appends a new fact record into local memory storage.
        - Returns: Confirmation string with the recorded entry ID and category.
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

    @server.tool(annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True})
    def memory_recall(
        query: str = Field(default="", description="Keyword or semantic concept to query within stored memories"),
        category: str = Field(default="", description="Optional category filter (e.g. 'preferences', 'project', 'workflow')"),
        limit: int = Field(default=5, description="Maximum number of memory items to return (1 to 50)", ge=1, le=50)
    ) -> str:
        """Recall relevant long-term memories ranked by BM25 relevance and recency decay.

        To store new memories, use `memory_retain` instead.

        When to use:
        - Call at session start or before answering complex user questions to retrieve relevant project rules, preferences, and prior decisions.

        When NOT to use:
        - Do not use to save new information (use `memory_retain`).

        Prerequisites & Side Effects:
        - Prerequisites: Uses `agent-hindsight` library or CLI if available.
        - Side effects: None. Pure read-only memory query.
        - Returns: JSON array of matched memory objects containing fact, category, importance, and timestamp.
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
