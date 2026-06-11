"""
Tatsu AI — Agent (ReAct Loop)
===============================
The brain of Tatsu. Implements the Reason-Act-Observe loop
with tool calling, safety gates, and streaming responses.
"""

import json
import logging
from dataclasses import dataclass
from typing import AsyncGenerator

import config
from core.llm_provider import LLMProvider
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from tools.registry import ToolRegistry
from safety.confirmation import ConfirmationGate
from safety.action_logger import ActionLogger
from safety.permissions import PermissionManager

logger = logging.getLogger("tatsu.agent")


@dataclass
class AgentEvent:
    """An event emitted by the agent during processing."""
    type: str   # "thinking", "tool_call", "tool_result", "response", "error", "confirmation"
    content: str = ""
    tool: str = ""
    args: dict | None = None
    result: str = ""
    action_id: str = ""
    details: dict | None = None


class TatsuAgent:
    """
    Main agent implementing the ReAct (Reason + Act) loop.

    Flow:
    1. Receive user message
    2. Build context (system prompt + history + tools)
    3. Enter ReAct loop:
       a. Send to LLM with tool schemas
       b. If LLM returns tool_calls → check safety → execute → observe → loop
       c. If LLM returns text → stream to user → break
    4. Save everything to memory
    """

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        short_term_memory: ShortTermMemory,
        long_term_memory: LongTermMemory,
        confirmation_gate: ConfirmationGate,
        action_logger: ActionLogger,
        permission_manager: PermissionManager,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.stm = short_term_memory
        self.ltm = long_term_memory
        self.confirmation = confirmation_gate
        self.logger = action_logger
        self.permissions = permission_manager
        self._conversation_id: str | None = None

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    async def start_conversation(self, conversation_id: str | None = None) -> str:
        """Start or resume a conversation."""
        if conversation_id:
            self._conversation_id = conversation_id
            # Load history from long-term memory
            messages = await self.ltm.load_conversation_messages(conversation_id)
            self.stm.clear()
            for msg in messages:
                self.stm.add_message(
                    role=msg["role"],
                    content=msg["content"],
                    tool_calls=msg.get("tool_calls"),
                    tool_name=msg.get("tool_name"),
                )
            logger.info(f"Resumed conversation: {conversation_id} ({len(messages)} messages)")
        else:
            self._conversation_id = await self.ltm.create_conversation()
            self.stm.clear()
            logger.info(f"Started new conversation: {self._conversation_id}")

        return self._conversation_id

    async def run(self, user_message: str) -> AsyncGenerator[AgentEvent, None]:
        """
        Process a user message through the ReAct loop.

        Yields AgentEvent objects for each step:
        - thinking: Agent is reasoning
        - tool_call: Agent is calling a tool
        - tool_result: Tool returned a result
        - response: Final text response (may be streamed)
        - error: Something went wrong
        - confirmation: Awaiting user confirmation
        """
        if not self._conversation_id:
            await self.start_conversation()

        # Add user message to memory
        self.stm.add_message("user", user_message)
        await self.ltm.save_message(self._conversation_id, "user", user_message)

        # Build system prompt with tool info
        system_prompt = self._build_system_prompt()

        # Build messages for LLM
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self.stm.get_context_window())

        # Get tool schemas
        tool_schemas = self.tools.get_all_schemas()

        # ReAct loop
        iteration = 0
        while iteration < config.MAX_AGENT_ITERATIONS:
            iteration += 1
            logger.info(f"Agent iteration {iteration}/{config.MAX_AGENT_ITERATIONS}")

            yield AgentEvent(type="thinking", content=f"Reasoning (step {iteration})...")

            try:
                response = await self.llm.chat(messages, tools=tool_schemas if tool_schemas else None)
            except RuntimeError as e:
                yield AgentEvent(type="error", content=str(e))
                return

            # ── Tool Calls ─────────────────────────────────────────────────
            if response.has_tool_calls:
                for tc in response.tool_calls:
                    yield AgentEvent(
                        type="tool_call",
                        tool=tc.name,
                        args=tc.arguments,
                        content=f"Using tool: {tc.name}",
                    )

                    # Execute the tool
                    tool_result = await self._execute_tool(tc.name, tc.arguments)

                    yield AgentEvent(
                        type="tool_result",
                        tool=tc.name,
                        result=tool_result,
                        content=tool_result,
                    )

                    # Add tool call and result to message history
                    # Add assistant message with tool call
                    assistant_msg = {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [{
                            "function": {
                                "name": tc.name,
                                "arguments": tc.arguments,
                            }
                        }],
                    }
                    messages.append(assistant_msg)

                    # Add tool result
                    tool_msg = {
                        "role": "tool",
                        "content": tool_result,
                    }
                    messages.append(tool_msg)

                    # Save to memory
                    self.stm.add_message(
                        "assistant", response.content or f"[Called {tc.name}]",
                        tool_calls=[{"name": tc.name, "arguments": tc.arguments}],
                    )
                    self.stm.add_message("tool", tool_result, tool_name=tc.name)

                # Continue the loop — LLM needs to process tool results
                continue

            # ── Final Response ─────────────────────────────────────────────
            else:
                final_response = response.content

                if final_response:
                    yield AgentEvent(type="response", content=final_response)

                    # Save to memory
                    self.stm.add_message("assistant", final_response)
                    await self.ltm.save_message(
                        self._conversation_id, "assistant", final_response
                    )

                    # Auto-generate title for new conversations
                    if self.stm.message_count <= 3:
                        await self._auto_title(user_message)

                break  # Exit the ReAct loop
        else:
            # Max iterations reached
            yield AgentEvent(
                type="error",
                content="I've reached the maximum number of reasoning steps. "
                        "Let me try a different approach — could you rephrase your request?",
            )

    async def _execute_tool(self, tool_name: str, arguments: dict) -> str:
        """
        Execute a tool with safety checks.

        Returns the tool result as a string.
        """
        tool = self.tools.get_tool(tool_name)
        if not tool:
            error_msg = f"Tool '{tool_name}' not found."
            logger.error(error_msg)
            await self.logger.log(
                self._conversation_id, tool_name, "unknown",
                arguments, error_msg, "error",
            )
            return error_msg

        # Check if confirmation is needed
        action_desc = arguments.get("action", tool_name)
        needs_confirm = (
            tool.requires_confirmation
            or self.confirmation.requires_confirmation(tool_name, str(action_desc))
        )

        if needs_confirm:
            approved = await self.confirmation.request_confirmation(
                tool_name=tool_name,
                action=str(action_desc),
                details=arguments,
            )
            if not approved:
                denied_msg = f"Action '{action_desc}' was denied by the user."
                await self.logger.log(
                    self._conversation_id, tool_name, str(action_desc),
                    arguments, denied_msg, "denied",
                    required_confirmation=True, was_approved=False,
                )
                return denied_msg

        # Validate parameters
        valid, error = tool.validate_params(**arguments)
        if not valid:
            await self.logger.log(
                self._conversation_id, tool_name, str(action_desc),
                arguments, error, "error",
            )
            return f"Invalid parameters: {error}"

        # Execute
        try:
            result = await tool.execute(**arguments)
            await self.logger.log(
                self._conversation_id, tool_name, str(action_desc),
                arguments, result.output[:500], result.success and "success" or "failed",
                required_confirmation=needs_confirm, was_approved=True,
            )
            return result.to_message()

        except Exception as e:
            error_msg = f"Tool execution error: {str(e)}"
            logger.exception(f"Tool '{tool_name}' failed: {e}")
            await self.logger.log(
                self._conversation_id, tool_name, str(action_desc),
                arguments, error_msg, "error",
            )
            return error_msg

    def _build_system_prompt(self) -> str:
        """Build the system prompt with available tools and user context."""
        tools_desc = self.tools.get_tool_descriptions()

        prompt = config.AGENT_SYSTEM_PROMPT

        if tools_desc:
            prompt += f"\n\nAvailable tools:\n{tools_desc}"

        prompt += "\n\nAlways use the most appropriate tool for the task. If no tool is needed, respond directly."

        return prompt

    async def _auto_title(self, first_message: str) -> None:
        """Auto-generate a conversation title from the first message."""
        title = first_message[:60].strip()
        if len(first_message) > 60:
            title += "..."
        await self.ltm.update_conversation_title(self._conversation_id, title)
