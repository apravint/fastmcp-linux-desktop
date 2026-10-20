import asyncio
import unittest
from fastmcp_linux_desktop.server import create_server

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
                "condense_context", "memory_retain", "memory_recall"
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

if __name__ == "__main__":
    unittest.main()
