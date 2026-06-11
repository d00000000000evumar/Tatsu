"""
Tatsu AI — App Launcher Tool
===============================
Discovers and launches installed applications on Windows.
Handles missing application detection and suggests downloads.
"""

import json
import logging
import os
import subprocess
import winreg
from pathlib import Path

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.app_launcher")

# Common application names → executable mappings
KNOWN_APPS = {
    # Browsers
    "chrome": {"exe": "chrome.exe", "names": ["google chrome", "chrome"]},
    "firefox": {"exe": "firefox.exe", "names": ["mozilla firefox", "firefox"]},
    "edge": {"exe": "msedge.exe", "names": ["microsoft edge", "edge"]},
    "brave": {"exe": "brave.exe", "names": ["brave browser", "brave"]},
    "opera": {"exe": "opera.exe", "names": ["opera browser", "opera"]},
    # Development
    "vscode": {"exe": "Code.exe", "names": ["visual studio code", "vscode", "vs code", "code"]},
    "notepad++": {"exe": "notepad++.exe", "names": ["notepad++", "notepadplusplus", "npp"]},
    "git": {"exe": "git.exe", "names": ["git"]},
    "python": {"exe": "python.exe", "names": ["python"]},
    "node": {"exe": "node.exe", "names": ["node", "nodejs", "node.js"]},
    "terminal": {"exe": "wt.exe", "names": ["windows terminal", "terminal", "wt"]},
    "powershell": {"exe": "powershell.exe", "names": ["powershell", "ps"]},
    "cmd": {"exe": "cmd.exe", "names": ["command prompt", "cmd", "command line"]},
    # Media
    "vlc": {"exe": "vlc.exe", "names": ["vlc", "vlc media player"]},
    "spotify": {"exe": "Spotify.exe", "names": ["spotify"]},
    # Communication
    "discord": {"exe": "Discord.exe", "names": ["discord"]},
    "slack": {"exe": "slack.exe", "names": ["slack"]},
    "teams": {"exe": "ms-teams.exe", "names": ["microsoft teams", "teams"]},
    "zoom": {"exe": "Zoom.exe", "names": ["zoom"]},
    "telegram": {"exe": "Telegram.exe", "names": ["telegram"]},
    # Productivity
    "word": {"exe": "WINWORD.EXE", "names": ["microsoft word", "word", "ms word"]},
    "excel": {"exe": "EXCEL.EXE", "names": ["microsoft excel", "excel", "ms excel"]},
    "powerpoint": {"exe": "POWERPNT.EXE", "names": ["microsoft powerpoint", "powerpoint", "ppt"]},
    "outlook": {"exe": "OUTLOOK.EXE", "names": ["microsoft outlook", "outlook"]},
    "onenote": {"exe": "ONENOTE.EXE", "names": ["onenote", "one note"]},
    # System
    "explorer": {"exe": "explorer.exe", "names": ["file explorer", "explorer", "this pc"]},
    "notepad": {"exe": "notepad.exe", "names": ["notepad"]},
    "calculator": {"exe": "calc.exe", "names": ["calculator", "calc"]},
    "paint": {"exe": "mspaint.exe", "names": ["paint", "ms paint"]},
    "snipping": {"exe": "SnippingTool.exe", "names": ["snipping tool", "screenshot"]},
    "task_manager": {"exe": "Taskmgr.exe", "names": ["task manager", "taskmgr"]},
    "settings": {"exe": "ms-settings:", "names": ["settings", "windows settings"]},
    "control_panel": {"exe": "control.exe", "names": ["control panel"]},
    # Gaming / Media
    "steam": {"exe": "steam.exe", "names": ["steam"]},
    "obs": {"exe": "obs64.exe", "names": ["obs", "obs studio"]},
    # Design
    "photoshop": {"exe": "Photoshop.exe", "names": ["photoshop", "adobe photoshop"]},
    "figma": {"exe": "Figma.exe", "names": ["figma"]},
    "blender": {"exe": "blender.exe", "names": ["blender"]},
}

# Official download URLs for common apps
DOWNLOAD_URLS = {
    "chrome": "https://www.google.com/chrome/",
    "firefox": "https://www.mozilla.org/firefox/",
    "vscode": "https://code.visualstudio.com/",
    "notepad++": "https://notepad-plus-plus.org/downloads/",
    "vlc": "https://www.videolan.org/vlc/",
    "spotify": "https://www.spotify.com/download/",
    "discord": "https://discord.com/download",
    "slack": "https://slack.com/downloads/windows",
    "zoom": "https://zoom.us/download",
    "telegram": "https://desktop.telegram.org/",
    "steam": "https://store.steampowered.com/about/",
    "obs": "https://obsproject.com/download",
    "git": "https://git-scm.com/downloads",
    "python": "https://www.python.org/downloads/",
    "node": "https://nodejs.org/",
    "blender": "https://www.blender.org/download/",
    "brave": "https://brave.com/download/",
}


class AppLauncherTool(BaseTool):
    """Application launcher for discovering and opening installed programs."""

    name = "app_launcher"
    description = (
        "Launch an installed application on this Windows computer. "
        "Provide the app name (e.g., 'Chrome', 'VS Code', 'Discord'). "
        "If the app is not found, I'll suggest where to download it."
    )
    parameters = [
        ToolParameter(
            name="app_name",
            type="string",
            description="Name of the application to launch (e.g., 'Chrome', 'VS Code', 'Spotify').",
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.MEDIUM

    async def execute(self, app_name: str, **kwargs) -> ToolResult:
        """Find and launch an application."""
        app_lower = app_name.lower().strip()

        # 1. Try known apps mapping
        app_key = self._find_known_app(app_lower)

        if app_key:
            app_info = KNOWN_APPS[app_key]
            exe_name = app_info["exe"]

            # Handle special protocol URLs (like ms-settings:)
            if exe_name.endswith(":"):
                return await self._launch_protocol(exe_name, app_name)

            # Try to find and launch the executable
            exe_path = self._find_executable(exe_name)
            if exe_path:
                return await self._launch(exe_path, app_name)

        # 2. Try searching the system PATH
        path_result = self._find_in_path(app_lower)
        if path_result:
            return await self._launch(path_result, app_name)

        # 3. Try searching Start Menu shortcuts
        start_result = self._find_in_start_menu(app_lower)
        if start_result:
            return await self._launch(start_result, app_name)

        # 4. Not found — suggest download
        return self._suggest_download(app_name, app_key or app_lower)

    def _find_known_app(self, query: str) -> str | None:
        """Match user query to a known application key."""
        for key, info in KNOWN_APPS.items():
            if query in info["names"] or query == key:
                return key
        # Partial match
        for key, info in KNOWN_APPS.items():
            for name in info["names"]:
                if query in name or name in query:
                    return key
        return None

    def _find_executable(self, exe_name: str) -> str | None:
        """Search common installation directories for an executable."""
        search_dirs = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
            os.path.join(os.environ.get("APPDATA", ""), ".."),
            os.environ.get("USERPROFILE", ""),
        ]

        for base_dir in search_dirs:
            if not base_dir:
                continue
            base_path = Path(base_dir)
            if not base_path.exists():
                continue
            # Search up to 3 levels deep
            for depth_pattern in [f"*/{exe_name}", f"*/*/{exe_name}", f"*/*/*/{exe_name}"]:
                results = list(base_path.glob(depth_pattern))
                if results:
                    return str(results[0])

        # Also try Windows registry
        return self._find_in_registry(exe_name)

    def _find_in_registry(self, exe_name: str) -> str | None:
        """Search Windows registry for installed application paths."""
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
        ]

        for hkey, reg_path in registry_paths:
            try:
                key = winreg.OpenKey(hkey, f"{reg_path}\\{exe_name}")
                value, _ = winreg.QueryValueEx(key, "")
                winreg.CloseKey(key)
                if os.path.exists(value):
                    return value
            except (FileNotFoundError, OSError):
                continue

        return None

    def _find_in_path(self, name: str) -> str | None:
        """Search system PATH for an executable."""
        import shutil
        result = shutil.which(name)
        if result:
            return result
        # Try common variations
        for ext in [".exe", ".cmd", ".bat", ".com"]:
            result = shutil.which(name + ext)
            if result:
                return result
        return None

    def _find_in_start_menu(self, query: str) -> str | None:
        """Search Start Menu shortcuts for matching applications."""
        start_menu_dirs = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft/Windows/Start Menu/Programs",
        ]

        for start_dir in start_menu_dirs:
            if not start_dir.exists():
                continue
            for lnk in start_dir.rglob("*.lnk"):
                if query in lnk.stem.lower():
                    return str(lnk)

        return None

    async def _launch(self, path: str, display_name: str) -> ToolResult:
        """Launch an application by path."""
        try:
            if path.endswith(".lnk"):
                os.startfile(path)
            else:
                subprocess.Popen(
                    [path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.DETACHED_PROCESS,
                )

            logger.info(f"Launched: {display_name} ({path})")
            return ToolResult(
                success=True,
                output=f"✅ Launched {display_name} successfully.",
                data={"app": display_name, "path": path},
            )
        except Exception as e:
            logger.error(f"Failed to launch {display_name}: {e}")
            return ToolResult(
                success=False,
                output=f"Failed to launch {display_name}.",
                error=str(e),
            )

    async def _launch_protocol(self, protocol: str, display_name: str) -> ToolResult:
        """Launch a Windows protocol URL (e.g., ms-settings:)."""
        try:
            os.startfile(protocol)
            return ToolResult(
                success=True,
                output=f"✅ Opened {display_name}.",
                data={"protocol": protocol},
            )
        except Exception as e:
            return ToolResult(success=False, output=f"Failed to open {display_name}.", error=str(e))

    def _suggest_download(self, app_name: str, app_key: str) -> ToolResult:
        """Suggest downloading a missing application."""
        download_url = DOWNLOAD_URLS.get(app_key, None)

        if download_url:
            return ToolResult(
                success=False,
                output=(
                    f"❌ {app_name} doesn't appear to be installed on this system.\n\n"
                    f"You can download it from the official website:\n"
                    f"🔗 {download_url}\n\n"
                    f"Would you like me to open the download page for you?"
                ),
                data={"missing_app": app_name, "download_url": download_url},
                error="Application not found",
            )
        else:
            return ToolResult(
                success=False,
                output=(
                    f"❌ {app_name} doesn't appear to be installed on this system.\n"
                    f"I couldn't find an official download source. "
                    f"Would you like me to search the web for it?"
                ),
                data={"missing_app": app_name},
                error="Application not found",
            )
