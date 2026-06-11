"""
Tatsu AI — Short-Term Memory
==============================
In-memory conversation buffer with sliding window.
Holds the current conversation context for the LLM.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime

import config

logger = logging.getLogger("tatsu.memory.short_term")


@dataclass
class Message:
    """A single message in the conversation."""
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: list[dict] | None = None
    tool_name: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ShortTermMemory:
    """
    In-memory conversation buffer.
    Maintains a sliding window of the most recent messages
    to keep within the LLM's context limit.
    """

    def __init__(self, max_messages: int | None = None):
        self.max_messages = max_messages or config.SHORT_TERM_MEMORY_LIMIT
        self._messages: list[Message] = []
        self._current_task: str | None = None

    def add_message(
        self,
        role: str,
        content: str,
        tool_calls: list[dict] | None = None,
        tool_name: str | None = None,
    ) -> None:
        """Add a message to the conversation buffer."""
        msg = Message(
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_name=tool_name,
        )
        self._messages.append(msg)

        # Trim to window size (keep system messages)
        if len(self._messages) > self.max_messages:
            # Preserve the system message at index 0 if it exists
            system_msgs = [m for m in self._messages if m.role == "system"]
            other_msgs = [m for m in self._messages if m.role != "system"]
            trimmed = other_msgs[-(self.max_messages - len(system_msgs)):]
            self._messages = system_msgs + trimmed

    def get_history(self, limit: int | None = None) -> list[Message]:
        """Get conversation history, optionally limited."""
        if limit:
            return self._messages[-limit:]
        return list(self._messages)

    def get_context_window(self) -> list[dict]:
        """
        Format the conversation history for the LLM.
        Returns messages in the format expected by Ollama/OpenAI.
        """
        window_size = config.CONVERSATION_CONTEXT_WINDOW
        messages = self._messages[-window_size:]

        formatted = []
        for msg in messages:
            entry: dict = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                entry["tool_calls"] = msg.tool_calls
            if msg.tool_name:
                entry["tool_name"] = msg.tool_name
            formatted.append(entry)

        return formatted

    def set_current_task(self, task: str) -> None:
        """Set the current active task description."""
        self._current_task = task
        logger.debug(f"Current task set: {task}")

    def get_current_task(self) -> str | None:
        """Get the current active task."""
        return self._current_task

    def clear_task(self) -> None:
        """Clear the current task."""
        self._current_task = None

    def clear(self) -> None:
        """Clear all conversation history."""
        self._messages.clear()
        self._current_task = None
        logger.info("Short-term memory cleared.")

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def __repr__(self) -> str:
        return f"<ShortTermMemory: {self.message_count} messages>"
