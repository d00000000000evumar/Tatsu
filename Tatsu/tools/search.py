"""
Tatsu AI — Search Tool
========================
Recursive file and folder search with glob patterns and content search.
"""

import logging
import os
from pathlib import Path

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.search")


class SearchTool(BaseTool):
    """Search for files and folders on the local filesystem."""

    name = "search"
    description = (
        "Search for files and folders on this computer. "
        "Use 'find' to search by filename pattern (supports wildcards like *.py, *.txt). "
        "Use 'find_content' to search inside text files for specific text."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="Search type: 'find' for filename search, 'find_content' for text content search.",
            enum=["find", "find_content"],
        ),
        ToolParameter(
            name="query",
            type="string",
            description="The search query: a filename pattern (e.g., '*.py', 'report*') or text to find inside files.",
        ),
        ToolParameter(
            name="directory",
            type="string",
            description="Directory to search in (e.g., '~/Desktop', '~/Documents'). Defaults to user home.",
            required=False,
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            description="Maximum number of results to return. Default: 20.",
            required=False,
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    async def execute(
        self,
        action: str,
        query: str,
        directory: str = "",
        max_results: int = 20,
        **kwargs,
    ) -> ToolResult:
        """Execute a search."""
        search_dir = os.path.expanduser(directory) if directory else str(Path.home())

        if not Path(search_dir).exists():
            return ToolResult(
                success=False,
                output=f"Directory not found: {search_dir}",
                error="Directory not found",
            )

        if action == "find":
            return await self._find_files(query, search_dir, max_results)
        elif action == "find_content":
            return await self._find_content(query, search_dir, max_results)
        else:
            return ToolResult(success=False, output=f"Unknown action: {action}")

    async def _find_files(self, pattern: str, directory: str, max_results: int) -> ToolResult:
        """Search for files matching a glob pattern."""
        search_path = Path(directory)
        results = []

        # If pattern doesn't have wildcards, add them
        if "*" not in pattern and "?" not in pattern:
            pattern = f"*{pattern}*"

        try:
            for match in search_path.rglob(pattern):
                if len(results) >= max_results:
                    break

                try:
                    stat = match.stat()
                    results.append({
                        "path": str(match),
                        "name": match.name,
                        "is_dir": match.is_dir(),
                        "size": stat.st_size,
                    })
                except (PermissionError, OSError):
                    continue

        except Exception as e:
            logger.error(f"Search error: {e}")

        if not results:
            return ToolResult(
                success=True,
                output=f"🔍 No files matching '{pattern}' found in {directory}.",
                data={"query": pattern, "directory": directory, "count": 0},
            )

        lines = [f"🔍 Found {len(results)} result(s) for '{pattern}' in {directory}:\n"]
        for r in results:
            icon = "📂" if r["is_dir"] else "📄"
            size = self._fmt_size(r["size"]) if not r["is_dir"] else ""
            lines.append(f"  {icon} {r['path']}" + (f" ({size})" if size else ""))

        return ToolResult(
            success=True,
            output="\n".join(lines),
            data={"query": pattern, "directory": directory, "count": len(results), "results": results},
        )

    async def _find_content(self, text: str, directory: str, max_results: int) -> ToolResult:
        """Search for text content inside files."""
        search_path = Path(directory)
        results = []

        # Only search text-like files
        text_extensions = {
            ".txt", ".py", ".js", ".html", ".css", ".json", ".md", ".csv",
            ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".log", ".bat", ".ps1", ".sh", ".java", ".cpp", ".c", ".h",
            ".ts", ".jsx", ".tsx", ".sql", ".env", ".gitignore",
        }

        try:
            for file_path in search_path.rglob("*"):
                if len(results) >= max_results:
                    break

                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in text_extensions:
                    continue
                if file_path.stat().st_size > 1_000_000:  # Skip files > 1MB
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if text.lower() in content.lower():
                        # Find the line containing the match
                        for i, line in enumerate(content.splitlines(), 1):
                            if text.lower() in line.lower():
                                results.append({
                                    "path": str(file_path),
                                    "line": i,
                                    "content": line.strip()[:100],
                                })
                                break
                except (PermissionError, OSError):
                    continue

        except Exception as e:
            logger.error(f"Content search error: {e}")

        if not results:
            return ToolResult(
                success=True,
                output=f"🔍 No files containing '{text}' found in {directory}.",
                data={"query": text, "directory": directory, "count": 0},
            )

        lines = [f"🔍 Found '{text}' in {len(results)} file(s):\n"]
        for r in results:
            lines.append(f"  📄 {r['path']} (line {r['line']})")
            lines.append(f"     → {r['content']}")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            data={"query": text, "directory": directory, "count": len(results)},
        )

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
