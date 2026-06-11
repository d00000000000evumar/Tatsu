"""
Tatsu AI — Permission Manager
================================
File system sandboxing and command safety checks.
Prevents the agent from accessing restricted paths or running dangerous commands.
"""

import logging
from pathlib import Path

import config

logger = logging.getLogger("tatsu.safety.permissions")


class PermissionManager:
    """
    Manages file system sandboxing and command safety.
    Ensures the agent only operates within allowed directories
    and blocks dangerous shell commands.
    """

    def __init__(
        self,
        allowed_paths: list[str] | None = None,
        blocked_commands: list[str] | None = None,
    ):
        self.allowed_paths = [
            Path(p).resolve() for p in (allowed_paths or config.ALLOWED_PATHS)
        ]
        self.blocked_commands = [
            cmd.lower() for cmd in (blocked_commands or config.BLOCKED_COMMANDS)
        ]

    def is_path_allowed(self, path: str) -> bool:
        """
        Check if a file path is within the allowed directories.

        Args:
            path: The file/folder path to check.

        Returns:
            True if the path is within an allowed directory.
        """
        try:
            target = Path(path).resolve()
        except (ValueError, OSError):
            return False

        for allowed in self.allowed_paths:
            try:
                # Check if target is inside the allowed path
                target.relative_to(allowed)
                return True
            except ValueError:
                continue

        logger.warning(f"Path access denied: {path}")
        return False

    def is_command_allowed(self, command: str) -> bool:
        """
        Check if a shell command is safe to execute.

        Args:
            command: The full command string.

        Returns:
            True if the command is not in the blocklist.
        """
        cmd_lower = command.lower().strip()

        for blocked in self.blocked_commands:
            if blocked in cmd_lower:
                logger.warning(f"Command blocked: {command} (matched: {blocked})")
                return False

        return True

    def get_blocked_commands(self) -> list[str]:
        """Get the list of blocked command patterns."""
        return list(self.blocked_commands)

    def get_allowed_paths(self) -> list[str]:
        """Get the list of allowed paths."""
        return [str(p) for p in self.allowed_paths]

    def add_allowed_path(self, path: str) -> None:
        """Add a path to the allowed list."""
        resolved = Path(path).resolve()
        if resolved not in self.allowed_paths:
            self.allowed_paths.append(resolved)
            logger.info(f"Added allowed path: {resolved}")

    def remove_allowed_path(self, path: str) -> None:
        """Remove a path from the allowed list."""
        resolved = Path(path).resolve()
        if resolved in self.allowed_paths:
            self.allowed_paths.remove(resolved)
            logger.info(f"Removed allowed path: {resolved}")
