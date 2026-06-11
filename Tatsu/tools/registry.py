"""
Tatsu AI — Tool Registry
==========================
Discovers, registers, and manages all available tools.
Provides tool schemas to the agent for LLM binding.
"""

import logging
from tools.base_tool import BaseTool
import config

logger = logging.getLogger("tatsu.tools")


class ToolRegistry:
    """
    Central registry for all Tatsu tools.
    Tools register themselves here, and the agent queries this registry
    to know what tools are available and how to call them.
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        if config.DEPLOYMENT_MODE == "cloud" and tool.name in ["TerminalTool", "AppLauncherTool"]:
            logger.info(f"Skipping registration of restricted tool: {tool.name}")
            return

        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered. Overwriting.")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} [{tool.risk_level.value}]")

    def register_many(self, tools: list[BaseTool]) -> None:
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get_tool(self, name: str) -> BaseTool | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def get_all_tools(self) -> dict[str, BaseTool]:
        """Get all registered tools as a dict."""
        return dict(self._tools)

    def get_all_schemas(self) -> list[dict]:
        """
        Get JSON schemas for all registered tools.
        This is what gets passed to the LLM's `tools` parameter.
        """
        return [tool.get_schema() for tool in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        """Get a list of all registered tool names."""
        return list(self._tools.keys())

    def get_tool_descriptions(self) -> str:
        """Get a formatted string of all tools and descriptions (for system prompt)."""
        lines = []
        for tool in self._tools.values():
            confirm_tag = " [REQUIRES CONFIRMATION]" if tool.requires_confirmation else ""
            lines.append(f"  - {tool.name}: {tool.description}{confirm_tag}")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry: {self.count} tools>"
