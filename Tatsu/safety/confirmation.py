"""
Tatsu AI — Confirmation Gate
===============================
Human-in-the-loop safety system.
Pauses tool execution for high-risk actions and requests user approval via WebSocket.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import config

logger = logging.getLogger("tatsu.safety.confirmation")


@dataclass
class PendingConfirmation:
    """A pending confirmation request awaiting user response."""
    id: str
    tool_name: str
    action: str
    details: dict
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _approved: bool = False

    @property
    def approved(self) -> bool:
        return self._approved


class ConfirmationGate:
    """
    Manages human-in-the-loop confirmations.
    When a high-risk action is detected, this gate pauses execution
    and sends a confirmation request to the UI via WebSocket.
    """

    def __init__(self):
        self._pending: dict[str, PendingConfirmation] = {}
        self._send_callback = None  # Set by the WebSocket handler

    def set_send_callback(self, callback):
        """
        Set the callback function for sending confirmation requests to the UI.
        Called by the WebSocket handler during initialization.
        """
        self._send_callback = callback

    def requires_confirmation(self, tool_name: str, action: str = "") -> bool:
        """Check if a tool/action requires user confirmation."""
        # Check explicit action list
        if action in config.CONFIRMATION_REQUIRED_ACTIONS:
            return True

        # Check tool-level flag (tools can set requires_confirmation=True)
        high_risk_tools = ["terminal", "file_manager"]
        high_risk_actions = ["delete", "remove", "install", "modify_system"]

        if tool_name in high_risk_tools:
            for risk_action in high_risk_actions:
                if risk_action in action.lower():
                    return True

        return False

    async def request_confirmation(
        self,
        tool_name: str,
        action: str,
        details: dict,
        timeout: float = 60.0,
    ) -> bool:
        """
        Request confirmation from the user.
        Sends a confirmation event via WebSocket and waits for the response.

        Args:
            tool_name: Name of the tool requesting confirmation.
            action: Description of the action to be performed.
            details: Additional context about the action.
            timeout: Max seconds to wait for user response.

        Returns:
            True if approved, False if denied or timed out.
        """
        confirmation_id = str(uuid.uuid4())[:8]
        pending = PendingConfirmation(
            id=confirmation_id,
            tool_name=tool_name,
            action=action,
            details=details,
        )
        self._pending[confirmation_id] = pending

        logger.info(
            f"Confirmation requested: [{confirmation_id}] {tool_name}.{action} — "
            f"Details: {details}"
        )

        # Send confirmation request to UI
        if self._send_callback:
            await self._send_callback({
                "type": "confirmation",
                "action_id": confirmation_id,
                "content": f"⚠️ {tool_name} wants to: {action}",
                "details": details,
            })

        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(pending._event.wait(), timeout=timeout)
            approved = pending.approved
        except asyncio.TimeoutError:
            logger.warning(f"Confirmation timed out: [{confirmation_id}]")
            approved = False
        finally:
            self._pending.pop(confirmation_id, None)

        logger.info(
            f"Confirmation result: [{confirmation_id}] "
            f"{'APPROVED' if approved else 'DENIED'}"
        )
        return approved

    def resolve(self, confirmation_id: str, approved: bool) -> bool:
        """
        Resolve a pending confirmation (called when user responds).

        Returns True if the confirmation was found and resolved.
        """
        pending = self._pending.get(confirmation_id)
        if not pending:
            logger.warning(f"No pending confirmation with ID: {confirmation_id}")
            return False

        pending._approved = approved
        pending._event.set()
        return True

    @property
    def pending_count(self) -> int:
        return len(self._pending)
