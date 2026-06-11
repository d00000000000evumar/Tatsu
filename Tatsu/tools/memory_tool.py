"""
Tatsu AI — Memory Tool
========================
Allows the agent to store and recall information from long-term memory.
Handles user preferences, learned facts, and frequently accessed data.
"""

import logging

from memory.long_term import LongTermMemory
from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.memory_tool")


class MemoryTool(BaseTool):
    """Tool for storing and recalling information from Tatsu's memory."""

    name = "memory"
    description = (
        "Store or recall information from memory. "
        "Use 'save' to remember something (e.g., user preferences, facts). "
        "Use 'recall' to retrieve a specific memory. "
        "Use 'search' to find memories by keyword. "
        "Use 'set_preference' to store a user preference. "
        "Use 'get_preference' to retrieve a user preference."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="The memory operation.",
            enum=["save", "recall", "search", "set_preference", "get_preference"],
        ),
        ToolParameter(
            name="category",
            type="string",
            description="Category for the memory (e.g., 'user_info', 'preferences', 'facts', 'workflows').",
            required=False,
        ),
        ToolParameter(
            name="key",
            type="string",
            description="The key/name for the memory item (e.g., 'favorite_editor', 'name').",
            required=False,
        ),
        ToolParameter(
            name="value",
            type="string",
            description="The value to store (for 'save' and 'set_preference' actions).",
            required=False,
        ),
        ToolParameter(
            name="query",
            type="string",
            description="Search query for 'search' action.",
            required=False,
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    def __init__(self, long_term_memory: LongTermMemory):
        self.ltm = long_term_memory

    async def execute(
        self,
        action: str,
        category: str = "general",
        key: str = "",
        value: str = "",
        query: str = "",
        **kwargs,
    ) -> ToolResult:
        """Execute a memory operation."""
        try:
            if action == "save":
                return await self._save(category, key, value)
            elif action == "recall":
                return await self._recall(category, key)
            elif action == "search":
                return await self._search(category, query)
            elif action == "set_preference":
                return await self._set_pref(key, value)
            elif action == "get_preference":
                return await self._get_pref(key)
            else:
                return ToolResult(success=False, output=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"Memory error: {e}")
            return ToolResult(success=False, output="Memory operation failed", error=str(e))

    async def _save(self, category: str, key: str, value: str) -> ToolResult:
        if not key or not value:
            return ToolResult(success=False, output="Both 'key' and 'value' are required to save a memory.")
        await self.ltm.save_memory(category, key, value)
        return ToolResult(
            success=True,
            output=f"💾 Remembered: [{category}] {key} = {value}",
            data={"category": category, "key": key, "value": value},
        )

    async def _recall(self, category: str, key: str) -> ToolResult:
        if not key:
            return ToolResult(success=False, output="'key' is required to recall a memory.")
        value = await self.ltm.recall_memory(category, key)
        if value:
            return ToolResult(
                success=True,
                output=f"🧠 [{category}] {key}: {value}",
                data={"category": category, "key": key, "value": value},
            )
        else:
            return ToolResult(
                success=True,
                output=f"No memory found for [{category}] {key}.",
                data={"found": False},
            )

    async def _search(self, category: str, query: str) -> ToolResult:
        results = await self.ltm.search_memories(category if category != "general" else None, query)
        if not results:
            return ToolResult(success=True, output=f"No memories found for query: '{query}'")

        lines = [f"🧠 Found {len(results)} memory/memories:\n"]
        for mem in results[:20]:
            lines.append(f"  [{mem['category']}] {mem['key']}: {mem['value']}")
        return ToolResult(success=True, output="\n".join(lines))

    async def _set_pref(self, key: str, value: str) -> ToolResult:
        if not key or not value:
            return ToolResult(success=False, output="Both 'key' and 'value' are required.")
        await self.ltm.set_preference(key, value)
        return ToolResult(
            success=True,
            output=f"⚙️ Preference saved: {key} = {value}",
        )

    async def _get_pref(self, key: str) -> ToolResult:
        if not key:
            # Return all preferences
            prefs = await self.ltm.get_all_preferences()
            if not prefs:
                return ToolResult(success=True, output="No preferences set yet.")
            lines = ["⚙️ User Preferences:\n"]
            for k, v in prefs.items():
                lines.append(f"  {k}: {v}")
            return ToolResult(success=True, output="\n".join(lines))

        value = await self.ltm.get_preference(key)
        if value:
            return ToolResult(success=True, output=f"⚙️ {key}: {value}")
        else:
            return ToolResult(success=True, output=f"No preference found for: {key}")
