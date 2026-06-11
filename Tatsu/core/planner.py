"""
Tatsu AI — Task Planner (Core)
================================
High-level planner that decomposes complex goals into executable steps
using the LLM's reasoning capabilities.
"""

import logging
from dataclasses import dataclass, field

from core.llm_provider import LLMProvider

logger = logging.getLogger("tatsu.core.planner")


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    index: int
    description: str
    tool: str | None = None
    status: str = "pending"  # pending, in_progress, done, failed
    result: str = ""


@dataclass
class ExecutionPlan:
    """A multi-step execution plan."""
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    current_step: int = 0

    @property
    def is_complete(self) -> bool:
        return all(s.status == "done" for s in self.steps)

    @property
    def progress(self) -> str:
        done = sum(1 for s in self.steps if s.status == "done")
        return f"{done}/{len(self.steps)}"

    def format(self) -> str:
        lines = [f"📋 Plan: {self.goal}\n"]
        for step in self.steps:
            icon = {"pending": "⬜", "in_progress": "🔄", "done": "✅", "failed": "❌"}[step.status]
            tool_tag = f" [{step.tool}]" if step.tool else ""
            lines.append(f"  {step.index}. {icon} {step.description}{tool_tag}")
        lines.append(f"\n  Progress: {self.progress}")
        return "\n".join(lines)


class TaskPlanner:
    """
    Decomposes complex goals into step-by-step execution plans.
    Uses the LLM to analyze the goal and available tools.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def create_plan(
        self,
        goal: str,
        available_tools: list[str],
    ) -> ExecutionPlan:
        """
        Create an execution plan for a complex goal.

        Args:
            goal: The user's goal in natural language.
            available_tools: List of available tool names.

        Returns:
            An ExecutionPlan with ordered steps.
        """
        prompt = f"""Analyze this goal and break it into simple, actionable steps.
For each step, specify which tool to use if applicable.

Goal: {goal}

Available tools: {', '.join(available_tools)}

Respond with a numbered list of steps. Each step should be:
<step_number>. <description> [tool: <tool_name>]

Keep steps concise and actionable. Use 3-7 steps maximum."""

        try:
            response = await self.llm.chat([
                {"role": "system", "content": "You are a task planning assistant. Break goals into clear steps."},
                {"role": "user", "content": prompt},
            ])

            steps = self._parse_steps(response.content)
            plan = ExecutionPlan(goal=goal, steps=steps)
            logger.info(f"Created plan for '{goal}': {len(steps)} steps")
            return plan

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return ExecutionPlan(
                goal=goal,
                steps=[PlanStep(index=1, description=goal)],
            )

    def _parse_steps(self, text: str) -> list[PlanStep]:
        """Parse LLM response into PlanStep objects."""
        steps = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Try to match numbered steps
            if line[0].isdigit() and "." in line[:4]:
                desc = line.split(".", 1)[1].strip()
                tool = None
                if "[tool:" in desc.lower():
                    parts = desc.rsplit("[tool:", 1)
                    desc = parts[0].strip()
                    tool = parts[1].strip().rstrip("]").strip()
                steps.append(PlanStep(
                    index=len(steps) + 1,
                    description=desc,
                    tool=tool,
                ))
        return steps if steps else [PlanStep(index=1, description=text.strip())]
