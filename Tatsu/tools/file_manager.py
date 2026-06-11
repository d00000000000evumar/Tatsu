"""
Tatsu AI — File Manager Tool
===============================
File and folder CRUD operations with safety checks.
Destructive actions (delete) require user confirmation.
"""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import config
from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.file_manager")


class FileManagerTool(BaseTool):
    """File management tool for creating, reading, moving, renaming, and deleting files/folders."""

    name = "file_manager"
    description = (
        "Manage files and folders. Actions: "
        "'list' (list directory contents), "
        "'create_folder' (create a new folder), "
        "'read' (read a text file's contents), "
        "'move' (move a file/folder), "
        "'rename' (rename a file/folder), "
        "'copy' (copy a file/folder), "
        "'delete' (delete a file/folder — requires confirmation), "
        "'info' (get file/folder information)."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="The file operation to perform.",
            enum=["list", "create_folder", "read", "move", "rename", "copy", "delete", "info"],
        ),
        ToolParameter(
            name="path",
            type="string",
            description="The file or folder path to operate on.",
        ),
        ToolParameter(
            name="destination",
            type="string",
            description="Destination path (for 'move', 'rename', 'copy' actions).",
            required=False,
        ),
    ]
    requires_confirmation = False  # Set per-action in agent
    risk_level = RiskLevel.MEDIUM

    async def execute(self, action: str, path: str, destination: str = "", **kwargs) -> ToolResult:
        """Execute a file management operation."""
        try:
            path = self._resolve_path(path)
            if destination:
                destination = self._resolve_path(destination)
        except PermissionError as e:
            return ToolResult(success=False, output=str(e), error="Path access denied")

        if action == "list":
            return await self._list_dir(path)
        elif action == "create_folder":
            return await self._create_folder(path)
        elif action == "read":
            return await self._read_file(path)
        elif action == "move":
            return await self._move(path, destination)
        elif action == "rename":
            return await self._rename(path, destination)
        elif action == "copy":
            return await self._copy(path, destination)
        elif action == "delete":
            return await self._delete(path)
        elif action == "info":
            return await self._info(path)
        else:
            return ToolResult(success=False, output=f"Unknown action: {action}")

    async def _list_dir(self, path: str) -> ToolResult:
        """List contents of a directory."""
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"Path does not exist: {path}", error="Path not found")
        if not p.is_dir():
            return ToolResult(success=False, output=f"Not a directory: {path}", error="Not a directory")

        try:
            entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            lines = [f"📁 Contents of: {path}\n"]

            for entry in entries[:50]:  # Limit to 50 entries
                if entry.is_dir():
                    lines.append(f"  📂 {entry.name}/")
                else:
                    size = self._fmt_size(entry.stat().st_size)
                    lines.append(f"  📄 {entry.name} ({size})")

            if len(entries) > 50:
                lines.append(f"\n  ... and {len(entries) - 50} more items")

            lines.append(f"\n  Total: {len(entries)} items")

            return ToolResult(
                success=True,
                output="\n".join(lines),
                data={"path": path, "count": len(entries)},
            )
        except PermissionError:
            return ToolResult(success=False, output=f"Permission denied: {path}", error="Permission denied")

    async def _create_folder(self, path: str) -> ToolResult:
        """Create a new folder."""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return ToolResult(
                success=True,
                output=f"✅ Created folder: {path}",
                data={"path": path},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to create folder: {path}", error=str(e))

    async def _read_file(self, path: str) -> ToolResult:
        """Read the contents of a text file."""
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"File not found: {path}", error="File not found")
        if not p.is_file():
            return ToolResult(success=False, output=f"Not a file: {path}", error="Not a file")

        # Check file size (limit to 100KB for safety)
        if p.stat().st_size > 100 * 1024:
            return ToolResult(
                success=False,
                output=f"File too large to read ({self._fmt_size(p.stat().st_size)}). Max: 100 KB.",
                error="File too large",
            )

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            lines = content.count("\n") + 1
            return ToolResult(
                success=True,
                output=f"📄 {p.name} ({lines} lines, {self._fmt_size(p.stat().st_size)}):\n\n{content}",
                data={"path": path, "lines": lines, "size": p.stat().st_size},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to read file: {path}", error=str(e))

    async def _move(self, src: str, dst: str) -> ToolResult:
        """Move a file or folder."""
        if not dst:
            return ToolResult(success=False, output="Destination path is required for move.", error="Missing destination")

        src_path = Path(src)
        if not src_path.exists():
            return ToolResult(success=False, output=f"Source not found: {src}", error="Source not found")

        try:
            shutil.move(src, dst)
            return ToolResult(
                success=True,
                output=f"✅ Moved: {src} → {dst}",
                data={"source": src, "destination": dst},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to move {src}", error=str(e))

    async def _rename(self, src: str, new_name: str) -> ToolResult:
        """Rename a file or folder."""
        if not new_name:
            return ToolResult(success=False, output="New name is required.", error="Missing new name")

        src_path = Path(src)
        if not src_path.exists():
            return ToolResult(success=False, output=f"Not found: {src}", error="Source not found")

        # If new_name is just a name (not a path), rename in same directory
        if os.sep not in new_name and "/" not in new_name:
            dst_path = src_path.parent / new_name
        else:
            dst_path = Path(new_name)

        try:
            src_path.rename(dst_path)
            return ToolResult(
                success=True,
                output=f"✅ Renamed: {src_path.name} → {dst_path.name}",
                data={"source": src, "new_name": str(dst_path)},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to rename {src}", error=str(e))

    async def _copy(self, src: str, dst: str) -> ToolResult:
        """Copy a file or folder."""
        if not dst:
            return ToolResult(success=False, output="Destination is required for copy.", error="Missing destination")

        src_path = Path(src)
        if not src_path.exists():
            return ToolResult(success=False, output=f"Source not found: {src}", error="Source not found")

        try:
            if src_path.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

            return ToolResult(
                success=True,
                output=f"✅ Copied: {src} → {dst}",
                data={"source": src, "destination": dst},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to copy {src}", error=str(e))

    async def _delete(self, path: str) -> ToolResult:
        """Delete a file or folder. This action requires confirmation from the agent's safety gate."""
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"Not found: {path}", error="Path not found")

        try:
            if p.is_dir():
                shutil.rmtree(path)
                return ToolResult(
                    success=True,
                    output=f"🗑️ Deleted folder: {path}",
                    data={"path": path, "type": "folder"},
                )
            else:
                p.unlink()
                return ToolResult(
                    success=True,
                    output=f"🗑️ Deleted file: {path}",
                    data={"path": path, "type": "file"},
                )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to delete {path}", error=str(e))

    async def _info(self, path: str) -> ToolResult:
        """Get detailed info about a file or folder."""
        p = Path(path)
        if not p.exists():
            return ToolResult(success=False, output=f"Not found: {path}", error="Path not found")

        stat = p.stat()
        is_dir = p.is_dir()

        info_lines = [
            f"{'📂' if is_dir else '📄'} {p.name}",
            f"  Type: {'Directory' if is_dir else 'File'}",
            f"  Path: {p.resolve()}",
            f"  Size: {self._fmt_size(stat.st_size)}",
            f"  Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if is_dir:
            try:
                items = list(p.iterdir())
                info_lines.append(f"  Contents: {len(items)} items")
            except PermissionError:
                info_lines.append("  Contents: Permission denied")

        if not is_dir:
            info_lines.append(f"  Extension: {p.suffix or 'None'}")

        return ToolResult(success=True, output="\n".join(info_lines))

    @staticmethod
    def _fmt_size(size: int) -> str:
        """Format file size to human-readable."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def _resolve_path(self, target_path: str) -> str:
        """Resolve and validate a path to ensure it is sandboxed in cloud mode."""
        p = Path(os.path.expanduser(target_path)).resolve()
        
        if config.DEPLOYMENT_MODE == "cloud":
            workspace_dir = (config.DATA_DIR / "workspace").resolve()
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure the resolved path starts with the workspace directory
            if not str(p).startswith(str(workspace_dir)):
                raise PermissionError(f"Cloud Mode Sandbox: Cannot access path outside of {workspace_dir}")
                
        return str(p)
