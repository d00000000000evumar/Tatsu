"""
Tatsu AI — Terminal Tool
==========================
Safe command execution with blocklist filtering.
High-risk commands require user confirmation via the safety gate.
"""

import asyncio
import logging
import os

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel
import config

logger = logging.getLogger("tatsu.tools.terminal")


class TerminalTool(BaseTool):
    """Terminal command execution tool with safety guardrails."""

    name = "terminal"
    description = (
        "Execute a shell command on this Windows computer. "
        "Use this for system tasks like checking installed software, "
        "getting network info, listing processes, etc. "
        "Dangerous commands are blocked. Sensitive commands require user confirmation."
    )
    parameters = [
        ToolParameter(
            name="command",
            type="string",
            description="The shell command to execute (e.g., 'dir', 'ipconfig', 'pip list').",
        ),
        ToolParameter(
            name="working_directory",
            type="string",
            description="Working directory for the command. Defaults to user home.",
            required=False,
        ),
    ]
    requires_confirmation = True  # Always confirm shell commands
    risk_level = RiskLevel.HIGH

    # Commands considered safe (don't need confirmation override)
    SAFE_COMMANDS = [
        "dir", "ls", "pwd", "cd", "echo", "type", "find", "findstr",
        "where", "whoami", "hostname", "ipconfig", "systeminfo",
        "tasklist", "wmic", "ver", "date", "time", "tree",
        "pip list", "pip show", "python --version", "node --version",
        "git status", "git log", "git branch", "git remote",
    ]

    async def execute(self, command: str, working_directory: str = "", **kwargs) -> ToolResult:
        """Execute a shell command safely."""
        # Check blocklist
        cmd_lower = command.lower().strip()
        for blocked in config.BLOCKED_COMMANDS:
            if blocked.lower() in cmd_lower:
                return ToolResult(
                    success=False,
                    output=f"🚫 Command blocked for safety: '{command}'\nBlocked pattern: '{blocked}'",
                    error=f"Blocked command: {blocked}",
                )

        # Set working directory
        cwd = working_directory if working_directory else str(os.path.expanduser("~"))

        try:
            # Run command with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=30.0,  # 30-second timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return ToolResult(
                    success=False,
                    output=f"⏱️ Command timed out after 30 seconds: {command}",
                    error="Command timed out",
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()

            # Truncate long output
            if len(output) > 3000:
                output = output[:3000] + f"\n\n... (truncated, {len(output)} chars total)"

            if process.returncode == 0:
                result_text = f"✅ Command: {command}\n\n{output}"
                if errors:
                    result_text += f"\n\n⚠️ Warnings:\n{errors}"
                return ToolResult(
                    success=True,
                    output=result_text,
                    data={"command": command, "exit_code": 0},
                )
            else:
                return ToolResult(
                    success=False,
                    output=f"❌ Command failed (exit code {process.returncode}): {command}\n\n{errors or output}",
                    error=f"Exit code: {process.returncode}",
                    data={"command": command, "exit_code": process.returncode},
                )

        except Exception as e:
            logger.exception(f"Terminal error: {e}")
            return ToolResult(
                success=False,
                output=f"Failed to execute command: {command}",
                error=str(e),
            )

    def is_safe_command(self, command: str) -> bool:
        """Check if a command is in the safe list (for skipping confirmation)."""
        cmd_lower = command.lower().strip()
        return any(cmd_lower.startswith(safe) for safe in self.SAFE_COMMANDS)
