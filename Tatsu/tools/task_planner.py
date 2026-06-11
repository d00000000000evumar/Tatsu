"""
Tatsu AI — Task Planner Tool
===============================
Decomposes complex goals into multi-step execution plans.
The agent uses this to break down tasks before acting.
"""

import logging

from tools.base_tool import BaseTool, ToolParameter, ToolResult, RiskLevel

logger = logging.getLogger("tatsu.tools.task_planner")


class TaskPlannerTool(BaseTool):
    """Tool for creating and managing multi-step task plans."""

    name = "task_planner"
    description = (
        "Create and manage multi-step task plans. "
        "Use 'create' to break a complex goal into steps. "
        "Use 'status' to check the current plan progress."
    )
    parameters = [
        ToolParameter(
            name="action",
            type="string",
            description="The planning action: 'create' to make a new plan, 'status' to check progress.",
            enum=["create", "status"],
        ),
        ToolParameter(
            name="goal",
            type="string",
            description="The goal to plan for (for 'create' action).",
            required=False,
        ),
        ToolParameter(
            name="steps",
            type="string",
            description="Comma-separated list of steps (for 'create' action).",
            required=False,
        ),
    ]
    requires_confirmation = False
    risk_level = RiskLevel.LOW

    def __init__(self):
        self._current_plan: dict | None = None

    async def execute(
        self,
        action: str,
        goal: str = "",
        steps: str = "",
        **kwargs,
    ) -> ToolResult:
        """Execute a planning action."""
        if action == "create":
            return await self._create_plan(goal, steps)
        elif action == "status":
            return await self._get_status()
        else:
            return ToolResult(success=False, output=f"Unknown action: {action}")

    async def _create_plan(self, goal: str, steps_str: str) -> ToolResult:
        """Create a new execution plan."""
        if not goal:
            return ToolResult(success=False, output="A goal is required to create a plan.")

        if steps_str:
            steps = [s.strip() for s in steps_str.split(",") if s.strip()]
        else:
            steps = []

        self._current_plan = {
            "goal": goal,
            "steps": [{"description": s, "status": "pending"} for s in steps],
            "current_step": 0,
        }

        lines = [f"📋 Plan created: {goal}\n"]
        for i, step in enumerate(self._current_plan["steps"], 1):
            lines.append(f"  {i}. ⬜ {step['description']}")

        return ToolResult(
            success=True,
            output="\n".join(lines),
            data=self._current_plan,
        )

    async def _get_status(self) -> ToolResult:
        """Get current plan status."""
        if not self._current_plan:
            return ToolResult(success=True, output="No active plan. Create one with the 'create' action.")

        lines = [f"📋 Plan: {self._current_plan['goal']}\n"]
        for i, step in enumerate(self._current_plan["steps"], 1):
            icon = {"pending": "⬜", "in_progress": "🔄", "done": "✅", "failed": "❌"}.get(
                step["status"], "⬜"
            )
            lines.append(f"  {i}. {icon} {step['description']}")

        done = sum(1 for s in self._current_plan["steps"] if s["status"] == "done")
        total = len(self._current_plan["steps"])
        lines.append(f"\n  Progress: {done}/{total} steps completed")

        return ToolResult(success=True, output="\n".join(lines))
