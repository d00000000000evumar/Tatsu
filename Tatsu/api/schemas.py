"""
Tatsu AI — Pydantic Schemas
=============================
Request/response models for the API layer.
Ensures type safety across WebSocket and REST endpoints.
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any


# ── Enums ──────────────────────────────────────────────────────────────────────

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class EventType(str, Enum):
    """WebSocket event types sent to the client."""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE = "response"
    STREAM_TOKEN = "stream_token"
    STREAM_END = "stream_end"
    CONFIRMATION = "confirmation"
    ERROR = "error"
    STATUS = "status"
    SYSTEM_INFO = "system_info"


class ClientEventType(str, Enum):
    """WebSocket event types received from the client."""
    MESSAGE = "message"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    SYSTEM_REQUEST = "system_request"


# ── WebSocket Messages ────────────────────────────────────────────────────────

class WSClientMessage(BaseModel):
    """Message received from the client via WebSocket."""
    type: ClientEventType
    content: str = ""
    action_id: str = ""
    approved: bool = False
    conversation_id: str | None = None


class WSServerEvent(BaseModel):
    """Event sent to the client via WebSocket."""
    type: EventType
    content: str = ""
    tool: str = ""
    args: dict = Field(default_factory=dict)
    result: str = ""
    action_id: str = ""
    details: dict = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    def to_json(self) -> str:
        return self.model_dump_json()


# ── REST Models ────────────────────────────────────────────────────────────────

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class MessageResponse(BaseModel):
    id: str
    role: MessageRole
    content: str
    tool_calls: list[dict] | None = None
    created_at: str


class MemoryRequest(BaseModel):
    category: str
    key: str
    value: str
    importance: int = Field(default=5, ge=1, le=10)


class ToolInfo(BaseModel):
    name: str
    description: str
    risk_level: str
    requires_confirmation: bool
    parameters: list[dict]


class SystemInfoResponse(BaseModel):
    cpu_percent: float
    ram_percent: float
    ram_total_gb: float
    ram_used_gb: float
    disk_percent: float
    disk_total_gb: float
    uptime_hours: float
    time: str
    platform: str


class StatusResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    model: str = ""
    tools_count: int = 0
    llm_connected: bool = False
