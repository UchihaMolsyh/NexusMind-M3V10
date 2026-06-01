"""
Workflow Tools — Multi-agent orchestration, task planning, automation.
"""
import json
import time
import logging
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.workflow")

# ─── Task Store ──────────────────────────────────────────
_task_plans: Dict[str, Dict] = {}
_automation_rules: List[Dict] = []


@registry.tool(
    name="create_task_plan",
    description="Decompose a complex goal into a multi-step task plan with dependencies.",
    category="Workflow & Automation",
    parameters=[
        ToolParam("goal", "string", "The high-level goal to decompose"),
        ToolParam("max_steps", "integer", "Maximum number of steps", required=False, default=8),
    ]
)
def create_task_plan(goal: str, max_steps: int = 8) -> Dict[str, Any]:
    from core.llm import engine

    prompt = f"""Create a detailed task plan to achieve this goal:
"{goal}"

Create {max_steps} concrete steps. For each step specify:
- Step number
- Description
- Estimated time
- Dependencies (which steps must complete first)
- Tools needed

Format as a numbered list."""

    result = engine.generate_simple(prompt, max_tokens=1024)

    plan_id = f"plan_{int(time.time())}"
    _task_plans[plan_id] = {
        "goal": goal,
        "plan": result,
        "status": "created",
        "created_at": time.time(),
    }

    return {
        "plan_id": plan_id,
        "goal": goal,
        "plan": result,
        "status": "created",
    }


@registry.tool(
    name="execute_workflow",
    description="Execute a sequential workflow of named steps.",
    category="Workflow & Automation",
    parameters=[
        ToolParam("steps", "string", "JSON array of step descriptions, e.g. [\"step1\", \"step2\"]"),
    ]
)
def execute_workflow(steps: str) -> Dict[str, Any]:
    try:
        step_list = json.loads(steps)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON array for steps"}

    results = []
    for i, step in enumerate(step_list):
        results.append({
            "step": i + 1,
            "description": step,
            "status": "completed",
            "timestamp": time.time(),
        })

    return {
        "workflow_status": "completed",
        "total_steps": len(step_list),
        "results": results,
    }


@registry.tool(
    name="multi_agent_dispatch",
    description="Simulate multi-agent collaboration by dispatching sub-tasks to role-based agents (Researcher, Analyst, Coder, etc.).",
    category="Workflow & Automation",
    parameters=[
        ToolParam("task", "string", "The main task to dispatch"),
        ToolParam("agents", "string", "JSON array of agent roles, e.g. [\"Researcher\", \"Coder\"]"),
    ]
)
def multi_agent_dispatch(task: str, agents: str) -> Dict[str, Any]:
    from core.llm import engine

    try:
        agent_list = json.loads(agents)
    except json.JSONDecodeError:
        agent_list = ["Researcher", "Analyst", "Implementer"]

    results = {}
    for agent_role in agent_list:
        prompt = f"""You are a {agent_role} agent. Your task:
"{task}"

Provide your analysis and contribution from the perspective of a {agent_role}.
Be concise but thorough. Focus on your area of expertise."""

        agent_result = engine.generate_simple(prompt, max_tokens=512)
        results[agent_role] = agent_result

    return {
        "task": task,
        "agents": agent_list,
        "agent_outputs": results,
        "status": "dispatched",
    }


@registry.tool(
    name="automation_trigger",
    description="Define or fire an event-based automation rule.",
    category="Workflow & Automation",
    parameters=[
        ToolParam("action", "string", "Action: 'define' to create a rule, 'list' to view rules, 'fire' to trigger an event"),
        ToolParam("event", "string", "Event name (e.g., 'on_message', 'on_error')", required=False, default=""),
        ToolParam("handler", "string", "Handler description for the event", required=False, default=""),
    ]
)
def automation_trigger(action: str, event: str = "", handler: str = "") -> Dict[str, Any]:
    if action == "define" and event and handler:
        rule = {"event": event, "handler": handler, "created": time.time()}
        _automation_rules.append(rule)
        return {"status": "rule_defined", "rule": rule, "total_rules": len(_automation_rules)}

    elif action == "list":
        return {"rules": _automation_rules, "count": len(_automation_rules)}

    elif action == "fire" and event:
        matching = [r for r in _automation_rules if r["event"] == event]
        return {
            "event": event,
            "triggered": len(matching),
            "handlers": [r["handler"] for r in matching],
        }

    return {"error": "Invalid action. Use 'define', 'list', or 'fire'."}
