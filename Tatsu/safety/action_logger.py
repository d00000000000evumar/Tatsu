"""
Tatsu AI — Action Logger
==========================
Full audit trail for every tool execution.
Logs to both SQLite database and a local log file.
"""

import json
import logging
from datetime import datetime

from memory.long_term import LongTermMemory

logger = logging.getLogger("tatsu.safety.action_logger")


class ActionLogger:
    """
    Logs every tool execution with full context.
    Provides audit trail for security and debugging.
    """

    def __init__(self, long_term_memory: LongTermMemory):
        self.memory = long_term_memory

    async def log(
        self,
        conversation_id: str | None,
        tool_name: str,
        action: str,
        parameters: dict,
        result: str,
        status: str,
        required_confirmation: bool = False,
        was_approved: bool = False,
    ) -> None:
        """
        Log a tool execution.

        Args:
            conversation_id: Current conversation ID.
            tool_name: Name of the tool executed.
            action: Specific action performed.
            parameters: Parameters passed to the tool.
            result: Result or output of the tool.
            status: One of: success, failed, denied, cancelled, error.
            required_confirmation: Whether confirmation was needed.
            was_approved: Whether the user approved (if confirmation was needed).
        """
        # Log to database
        await self.memory.log_action(
            conversation_id=conversation_id,
            tool_name=tool_name,
            action=action,
            parameters=parameters,
            result=result[:1000],  # Truncate long results
            status=status,
            required_confirmation=required_confirmation,
            was_approved=was_approved,
        )

        # Log to file
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "tool": tool_name,
            "action": action,
            "params": parameters,
            "status": status,
            "confirmed": required_confirmation,
            "approved": was_approved,
        }

        if status in ("failed", "error", "denied"):
            logger.warning(f"Tool action: {json.dumps(log_entry)}")
        else:
            logger.info(f"Tool action: {json.dumps(log_entry)}")

    async def get_recent_actions(
        self, conversation_id: str | None = None, limit: int = 20
    ) -> list[dict]:
        """Get recent action logs."""
        return await self.memory.get_action_logs(conversation_id, limit)
