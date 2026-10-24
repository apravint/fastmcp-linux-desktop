import asyncio
import os
import json
import tempfile
import unittest
from fastmcp_linux_desktop.server import create_server
from fastmcp_linux_desktop.cli import generate_config, install_config

class TestFastMCPDesktop(unittest.TestCase):
    def setUp(self):
        self.server = create_server("test-server")

    def test_server_creation(self):
        self.assertEqual(self.server.name, "test-server")

    def test_tools_registered(self):
        async def run_check():
            tools = await self.server.list_tools()
            tool_names = [t.name for t in tools]
            expected_tools = [
                "get_windows", "focus_window", "dispatch_hyprland",
                "switch_workspace", "get_monitors", "get_audio_status",
                "set_volume", "toggle_audio_sink", "get_system_health",
                "heal_system", "get_resource_usage", "desktop_notify",
                "take_screenshot", "condense_context", "memory_retain", "memory_recall"
            ]
            for t in expected_tools:
                self.assertIn(t, tool_names, f"Missing tool: {t}")

        asyncio.run(run_check())

    def test_system_health_execution(self):
        async def run_tool():
            res = await self.server.call_tool("get_system_health", {})
            self.assertFalse(res.is_error)
            text = res.content[0].text
            self.assertIn("Linux Desktop System Health", text)

        asyncio.run(run_tool())

    def test_generate_config_stdio(self):
        cfg = generate_config(client="claude", transport="stdio")
        self.assertIn("mcpServers", cfg)
        self.assertIn("linux-desktop", cfg["mcpServers"])
        entry = cfg["mcpServers"]["linux-desktop"]
        self.assertEqual(entry["command"], "fastmcp-linux-desktop")
        self.assertEqual(entry["args"], ["--transport", "stdio"])

    def test_generate_config_sse(self):
        cfg = generate_config(client="cursor", transport="sse", host="127.0.0.1", port=9000)
        self.assertIn("mcpServers", cfg)
        entry = cfg["mcpServers"]["linux-desktop"]
        self.assertEqual(entry["url"], "http://127.0.0.1:9000/sse")

    def test_install_config_merge_and_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = os.path.join(tmpdir, "claude_desktop_config.json")
            initial_data = {
                "mcpServers": {
                    "other-tool": {"command": "echo", "args": ["hello"]}
                }
            }
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f)

            new_cfg = generate_config(client="claude", transport="stdio")
            saved_path, bak_path = install_config("claude", new_cfg, target_path=cfg_file)

            self.assertEqual(saved_path, cfg_file)
            self.assertTrue(os.path.exists(bak_path))

            with open(cfg_file, "r", encoding="utf-8") as f:
                merged = json.load(f)

            self.assertIn("other-tool", merged["mcpServers"])
            self.assertIn("linux-desktop", merged["mcpServers"])

if __name__ == "__main__":
    unittest.main()
