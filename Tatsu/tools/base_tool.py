"""
Tatsu AI — Base Tool
=====================
Abstract base class for all tools. Every tool in Tatsu inherits from this.
Provides a consistent interface for the agent to discover, validate, and execute tools.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Risk classification for tool actions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolResult:
    """Standardized result from any tool execution."""
    success: bool
    output: str
    data: dict = field(default_factory=dict)
    error: str | None = None

    def to_message(self) -> str:
        """Format result for inclusion in LLM conversation."""
        if self.success:
            return self.output
        else:
            return f"Error: {self.error or self.output}"


@dataclass
class ToolParameter:
    """Describes a single parameter for a tool."""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array"
    description: str
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


class BaseTool(ABC):
    """
    Abstract base class for all Tatsu tools.

    Every tool must define:
      - name: Unique identifier (snake_case)
      - description: What the tool does (LLM reads this to decide when to use it)
      - parameters: List of ToolParameter objects
      - execute(): The actual implementation

    Optional overrides:
      - requires_confirmation: Whether to ask user before executing
      - risk_level: How dangerous this tool is
    """

    name: str = ""
    description: str = ""
    parameters: list[ToolParameter] = []
    requires_confirmation: bool = False
    risk_level: RiskLevel = RiskLevel.LOW

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given parameters.

        Args:
            **kwargs: Tool-specific parameters as defined in self.parameters.

        Returns:
            ToolResult with success/failure status and output.
        """
        pass

    def get_schema(self) -> dict:
        """
        Generate the JSON schema for LLM tool calling.
        This is the format Ollama/OpenAI expects for function definitions.
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

        return schema

    def validate_params(self, **kwargs) -> tuple[bool, str]:
        """
        Validate that required parameters are present and types are correct.

        Returns:
            Tuple of (is_valid, error_message).
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"

            if param.name in kwargs and param.enum:
                if kwargs[param.name] not in param.enum:
                    return False, (
                        f"Invalid value for {param.name}: {kwargs[param.name]}. "
                        f"Must be one of: {param.enum}"
                    )

        return True, ""

    def __repr__(self) -> str:
        return f"<Tool: {self.name} [{self.risk_level.value}]>"
