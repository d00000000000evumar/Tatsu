"""
Tatsu AI — Browser Tool
=========================
Opens URLs in the default web browser and performs web searches.
"""

import logging
import webbrowser
import urllib.parse

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.browser")


class BrowserTool(BaseTool):
    """Browser tool for opening websites and performing web searches."""

    name = "browser"
    description = (
        "Open a website URL in the default browser or search the web. "
        "Use action 'open' to open a specific URL, or 'search' to search the web."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="The action to perform: 'open' to open a URL, 'search' to search the web.",
            enum=["open", "search"],
        ),
        ToolParameter(
            name="query",
            type="string",
            description="The URL to open (for 'open') or the search query (for 'search').",
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    # Common site shortcuts
    SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "github": "https://github.com",
        "reddit": "https://www.reddit.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "facebook": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "linkedin": "https://www.linkedin.com",
        "stackoverflow": "https://stackoverflow.com",
        "wikipedia": "https://www.wikipedia.org",
        "amazon": "https://www.amazon.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "twitch": "https://www.twitch.tv",
        "discord": "https://discord.com",
        "chatgpt": "https://chat.openai.com",
        "whatsapp": "https://web.whatsapp.com",
    }

    async def execute(self, action: str, query: str, **kwargs) -> ToolResult:
        """Open a URL or search the web."""
        if action == "open":
            return await self._open_url(query)
        elif action == "search":
            return await self._search_web(query)
        else:
            return ToolResult(
                success=False,
                output=f"Unknown action: {action}",
                error="Action must be 'open' or 'search'.",
            )

    async def _open_url(self, url: str) -> ToolResult:
        """Open a URL in the default browser."""
        # Check shortcuts first
        shortcut = url.lower().strip().rstrip("/")
        if shortcut in self.SHORTCUTS:
            url = self.SHORTCUTS[shortcut]

        # Ensure URL has a scheme
        if not url.startswith(("http://", "https://")):
            # Check if it looks like a domain
            if "." in url and " " not in url:
                url = f"https://{url}"
            else:
                # Treat as a search query
                return await self._search_web(url)

        try:
            webbrowser.open(url)
            logger.info(f"Opened URL: {url}")
            return ToolResult(
                success=True,
                output=f"Opened {url} in your default browser.",
                data={"url": url},
            )
        except Exception as e:
            logger.error(f"Failed to open URL: {e}")
            return ToolResult(
                success=False,
                output=f"Failed to open {url}",
                error=str(e),
            )

    async def _search_web(self, query: str) -> ToolResult:
        """Search the web using Google."""
        encoded = urllib.parse.quote_plus(query)
        search_url = f"https://www.google.com/search?q={encoded}"

        try:
            webbrowser.open(search_url)
            logger.info(f"Web search: {query}")
            return ToolResult(
                success=True,
                output=f"Searching the web for: \"{query}\"",
                data={"query": query, "url": search_url},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=f"Failed to search for: {query}",
                error=str(e),
            )
