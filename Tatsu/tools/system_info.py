"""
Tatsu AI — System Info Tool
==============================
Reports system information: CPU, RAM, disk, battery, uptime, and running processes.
"""

import logging
import platform
import time
from datetime import datetime, timedelta

import psutil

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.system_info")


class SystemInfoTool(BaseTool):
    """System information tool for monitoring hardware and processes."""

    name = "system_info"
    description = (
        "Get system information and monitor resources. "
        "Actions: 'overview' for a full summary, 'cpu' for CPU info, "
        "'memory' for RAM details, 'disk' for storage info, "
        "'battery' for battery status, 'processes' to list running processes, "
        "'uptime' for system uptime."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="What info to retrieve.",
            enum=["overview", "cpu", "memory", "disk", "battery", "processes", "uptime"],
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    async def execute(self, action: str, **kwargs) -> ToolResult:
        """Get system information."""
        try:
            if action == "overview":
                return await self._overview()
            elif action == "cpu":
                return await self._cpu_info()
            elif action == "memory":
                return await self._memory_info()
            elif action == "disk":
                return await self._disk_info()
            elif action == "battery":
                return await self._battery_info()
            elif action == "processes":
                return await self._process_list()
            elif action == "uptime":
                return await self._uptime()
            else:
                return ToolResult(success=False, output=f"Unknown action: {action}")
        except Exception as e:
            logger.exception(f"System info error: {e}")
            return ToolResult(success=False, output="Failed to get system info", error=str(e))

    async def _overview(self) -> ToolResult:
        """Get a full system overview."""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot

        info = (
            f"🖥️ System Overview\n"
            f"  Platform: {platform.system()} {platform.release()}\n"
            f"  Machine: {platform.machine()}\n"
            f"  Processor: {platform.processor()}\n\n"
            f"⚡ CPU: {cpu_percent}% ({cpu_count} cores)\n"
            f"🧠 RAM: {mem.percent}% used ({self._fmt_bytes(mem.used)} / {self._fmt_bytes(mem.total)})\n"
            f"💾 Disk: {disk.percent}% used ({self._fmt_bytes(disk.used)} / {self._fmt_bytes(disk.total)})\n"
            f"⏱️ Uptime: {str(uptime).split('.')[0]}\n"
            f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return ToolResult(
            success=True,
            output=info,
            data={
                "cpu_percent": cpu_percent,
                "ram_percent": mem.percent,
                "disk_percent": disk.percent,
                "uptime_hours": round(uptime.total_seconds() / 3600, 1),
            },
        )

    async def _cpu_info(self) -> ToolResult:
        """Get detailed CPU info."""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        cpu_freq = psutil.cpu_freq()
        avg = sum(cpu_percent) / len(cpu_percent)

        lines = [f"⚡ CPU Usage: {avg:.1f}% average"]
        for i, pct in enumerate(cpu_percent):
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            lines.append(f"  Core {i}: [{bar}] {pct}%")

        if cpu_freq:
            lines.append(f"  Frequency: {cpu_freq.current:.0f} MHz / {cpu_freq.max:.0f} MHz")

        return ToolResult(success=True, output="\n".join(lines))

    async def _memory_info(self) -> ToolResult:
        """Get RAM details."""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        info = (
            f"🧠 Memory:\n"
            f"  Total: {self._fmt_bytes(mem.total)}\n"
            f"  Used: {self._fmt_bytes(mem.used)} ({mem.percent}%)\n"
            f"  Available: {self._fmt_bytes(mem.available)}\n"
            f"  Swap: {self._fmt_bytes(swap.used)} / {self._fmt_bytes(swap.total)} ({swap.percent}%)"
        )

        return ToolResult(success=True, output=info)

    async def _disk_info(self) -> ToolResult:
        """Get disk usage for all partitions."""
        partitions = psutil.disk_partitions()
        lines = ["💾 Disk Partitions:"]

        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                lines.append(
                    f"  {part.device} ({part.mountpoint}): "
                    f"{self._fmt_bytes(usage.used)} / {self._fmt_bytes(usage.total)} "
                    f"({usage.percent}%)"
                )
            except (PermissionError, OSError):
                lines.append(f"  {part.device} ({part.mountpoint}): Access denied")

        return ToolResult(success=True, output="\n".join(lines))

    async def _battery_info(self) -> ToolResult:
        """Get battery status."""
        battery = psutil.sensors_battery()
        if not battery:
            return ToolResult(success=True, output="🔌 No battery detected (desktop system).")

        status = "🔌 Charging" if battery.power_plugged else "🔋 On Battery"
        time_left = ""
        if battery.secsleft > 0:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            time_left = f"\n  Time Remaining: {hours}h {minutes}m"

        return ToolResult(
            success=True,
            output=f"{status}\n  Battery: {battery.percent}%{time_left}",
        )

    async def _process_list(self) -> ToolResult:
        """List top processes by memory usage."""
        processes = []
        for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                info = proc.info
                if info["memory_percent"] and info["memory_percent"] > 0.1:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage
        processes.sort(key=lambda p: p.get("memory_percent", 0), reverse=True)
        top = processes[:15]

        lines = ["📋 Top Processes (by memory):"]
        lines.append(f"  {'Name':<30} {'PID':<8} {'RAM %':<8} {'CPU %':<8}")
        lines.append("  " + "-" * 54)
        for proc in top:
            lines.append(
                f"  {proc['name'][:29]:<30} {proc['pid']:<8} "
                f"{proc.get('memory_percent', 0):<8.1f} {proc.get('cpu_percent', 0):<8.1f}"
            )

        lines.append(f"\n  Total processes: {len(processes)}")

        return ToolResult(success=True, output="\n".join(lines))

    async def _uptime(self) -> ToolResult:
        """Get system uptime."""
        boot = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot
        return ToolResult(
            success=True,
            output=(
                f"⏱️ System Uptime: {str(uptime).split('.')[0]}\n"
                f"  Boot Time: {boot.strftime('%Y-%m-%d %H:%M:%S')}"
            ),
        )

    @staticmethod
    def _fmt_bytes(bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
