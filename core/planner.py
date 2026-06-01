"""
Planner — break complex tasks into steps, track execution, handle dependencies.
"""
import json
import time
import uuid
import logging
from enum import Enum
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("nexusmind.planner")


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    id: str
    description: str
    tool: Optional[str] = None
    args: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 2

    def to_dict(self):
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class Plan:
    id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: str = "active"

    def to_dict(self):
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "status": self.status,
        }

    def progress(self) -> str:
        done = sum(1 for s in self.steps if s.status == StepStatus.DONE)
        total = len(self.steps)
        return f"{done}/{total} steps complete"


class Planner:
    """Task planning system with dependency tracking."""

    def __init__(self):
        self.plans: Dict[str, Plan] = {}
        self.current_plan: Optional[str] = None

    def create_plan(self, goal: str, steps: List[Dict[str, Any]]) -> Plan:
        """Create a new execution plan."""
        plan_id = str(uuid.uuid4())[:8]
        plan_steps = []
        for i, step_data in enumerate(steps):
            step = PlanStep(
                id=step_data.get("id", f"step_{i}"),
                description=step_data["description"],
                tool=step_data.get("tool"),
                args=step_data.get("args", {}),
                depends_on=step_data.get("depends_on", []),
            )
            plan_steps.append(step)

        plan = Plan(id=plan_id, goal=goal, steps=plan_steps)
        self.plans[plan_id] = plan
        self.current_plan = plan_id
        logger.info(f"Created plan '{plan_id}': {goal} ({len(plan_steps)} steps)")
        return plan

    def get_next_steps(self, plan_id: Optional[str] = None) -> List[PlanStep]:
        """Get steps that are ready to execute (all dependencies met)."""
        plan = self.plans.get(plan_id or self.current_plan)
        if not plan:
            return []

        ready = []
        done_ids = {s.id for s in plan.steps if s.status == StepStatus.DONE}

        for step in plan.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in done_ids for dep in step.depends_on):
                ready.append(step)

        return ready

    def mark_step(self, plan_id: str, step_id: str, status: StepStatus,
                  result: Any = None, error: str = None):
        """Update a step's status."""
        plan = self.plans.get(plan_id)
        if not plan:
            return
        for step in plan.steps:
            if step.id == step_id:
                step.status = status
                step.result = result
                step.error = error
                break

        # Check if plan is complete
        if all(s.status in (StepStatus.DONE, StepStatus.SKIPPED) for s in plan.steps):
            plan.status = "completed"
        elif any(s.status == StepStatus.FAILED and s.retries >= s.max_retries for s in plan.steps):
            plan.status = "failed"

    async def execute_plan(self, plan_id: str, tool_registry) -> Dict[str, Any]:
        """Execute all steps in a plan respecting dependencies."""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        results = {}
        max_iterations = len(plan.steps) * 3  # safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            next_steps = self.get_next_steps(plan_id)

            if not next_steps:
                break

            for step in next_steps:
                step.status = StepStatus.RUNNING

                if step.tool:
                    result = await tool_registry.execute(step.tool, step.args)
                    if result.get("success"):
                        self.mark_step(plan_id, step.id, StepStatus.DONE, result=result["result"])
                    else:
                        step.retries += 1
                        if step.retries >= step.max_retries:
                            self.mark_step(plan_id, step.id, StepStatus.FAILED, error=result.get("error"))
                        else:
                            step.status = StepStatus.PENDING
                else:
                    # No tool — just mark as done (informational step)
                    self.mark_step(plan_id, step.id, StepStatus.DONE, result="Informational step")

                results[step.id] = step.to_dict()

        return {
            "plan_id": plan_id,
            "status": plan.status,
            "progress": plan.progress(),
            "results": results,
        }

    def get_plan_summary(self, plan_id: Optional[str] = None) -> str:
        """Get a human-readable plan summary."""
        plan = self.plans.get(plan_id or self.current_plan)
        if not plan:
            return "No active plan."

        lines = [f"📋 Plan: {plan.goal}", f"   Status: {plan.status} | {plan.progress()}", ""]
        for step in plan.steps:
            icons = {
                StepStatus.PENDING: "⬜",
                StepStatus.RUNNING: "🔄",
                StepStatus.DONE: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
            }
            icon = icons.get(step.status, "❓")
            tool_str = f" [{step.tool}]" if step.tool else ""
            lines.append(f"   {icon} {step.id}: {step.description}{tool_str}")
            if step.error:
                lines.append(f"      ⚠️ Error: {step.error}")
        return "\n".join(lines)

    def list_plans(self) -> List[Dict]:
        return [p.to_dict() for p in self.plans.values()]
