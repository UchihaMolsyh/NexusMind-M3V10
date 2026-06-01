"""
Reasoning Tools — Chain-of-Thought, Tree-of-Thought, Scratchpad, Debate, Dynamic Prompts.
"""
import json
import logging
import time
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.reasoning")

# ─── Persistent Scratchpad ───────────────────────────────
_scratchpad: Dict[str, str] = {}

# ─── Prompt Templates ───────────────────────────────────
_prompt_templates: Dict[str, str] = {
    "explain": "Explain {topic} in simple terms, suitable for a {audience}.",
    "compare": "Compare and contrast {item_a} and {item_b}. List pros and cons of each.",
    "summarize": "Summarize the following text in {length} sentences:\n\n{text}",
    "analyze": "Perform a detailed analysis of {subject}. Consider multiple perspectives.",
    "debug": "Debug the following code. Identify the bug and provide a fix:\n\n```{language}\n{code}\n```",
}


@registry.tool(
    name="chain_of_thought",
    description="Structured step-by-step Chain-of-Thought reasoning. Breaks a problem into logical steps with a scratchpad.",
    category="Reasoning",
    parameters=[
        ToolParam("problem", "string", "The problem or question to reason about"),
        ToolParam("num_steps", "integer", "Number of reasoning steps", required=False, default=5),
    ]
)
def chain_of_thought(problem: str, num_steps: int = 5) -> Dict[str, Any]:
    from core.llm import engine

    steps = []
    prompt = f"""Solve this problem using exactly {num_steps} clear, logical steps.
Problem: {problem}

Format each step as:
Step 1: [reasoning]
Step 2: [reasoning]
...
Final Answer: [answer]"""

    result = engine.generate_simple(prompt, max_tokens=1024)

    return {
        "problem": problem,
        "reasoning": result,
        "method": "chain_of_thought",
        "num_steps": num_steps,
    }


@registry.tool(
    name="tree_of_thought",
    description="Tree-of-Thought reasoning: explore multiple solution paths, evaluate each, and select the best.",
    category="Reasoning",
    parameters=[
        ToolParam("problem", "string", "The problem to solve via tree exploration"),
        ToolParam("branches", "integer", "Number of solution branches to explore", required=False, default=3),
    ]
)
def tree_of_thought(problem: str, branches: int = 3) -> Dict[str, Any]:
    from core.llm import engine

    prompt = f"""Solve this problem using Tree-of-Thought reasoning.

Problem: {problem}

Generate exactly {branches} different solution approaches:

For each approach:
1. Describe the approach
2. Work through it step by step
3. Rate its quality (1-10)
4. Note any issues

Then select the BEST approach and provide the final answer.

Format:
=== Approach 1 ===
[approach details]
Quality: X/10

=== Approach 2 ===
...

=== BEST SOLUTION ===
[final answer from best approach]"""

    result = engine.generate_simple(prompt, max_tokens=2048)

    return {
        "problem": problem,
        "reasoning": result,
        "method": "tree_of_thought",
        "branches": branches,
    }


@registry.tool(
    name="debate_critique",
    description="Self-debate: generate arguments FOR and AGAINST a position, then synthesize a balanced conclusion.",
    category="Reasoning",
    parameters=[
        ToolParam("topic", "string", "The topic or claim to debate"),
    ]
)
def debate_critique(topic: str) -> Dict[str, Any]:
    from core.llm import engine

    prompt = f"""Conduct a rigorous self-debate on:
"{topic}"

Structure:
🟢 **Arguments FOR:**
1. [strong argument]
2. [strong argument]
3. [strong argument]

🔴 **Arguments AGAINST:**
1. [strong counter-argument]
2. [strong counter-argument]
3. [strong counter-argument]

⚖️ **Balanced Conclusion:**
[synthesize both sides into a nuanced conclusion]"""

    result = engine.generate_simple(prompt, max_tokens=1024)

    return {
        "topic": topic,
        "debate": result,
        "method": "debate_critique",
    }


@registry.tool(
    name="scratchpad_write",
    description="Write to the internal scratchpad memory. Used for storing intermediate reasoning results.",
    category="Reasoning",
    parameters=[
        ToolParam("key", "string", "Key/name for the scratchpad entry"),
        ToolParam("value", "string", "Content to store"),
    ]
)
def scratchpad_write(key: str, value: str) -> Dict[str, Any]:
    _scratchpad[key] = value
    return {
        "status": "written",
        "key": key,
        "total_entries": len(_scratchpad),
    }


@registry.tool(
    name="scratchpad_read",
    description="Read from the internal scratchpad memory.",
    category="Reasoning",
    parameters=[
        ToolParam("key", "string", "Key to read (use '__all__' to read everything)", required=False, default="__all__"),
    ]
)
def scratchpad_read(key: str = "__all__") -> Dict[str, Any]:
    if key == "__all__":
        return {"entries": _scratchpad, "count": len(_scratchpad)}
    value = _scratchpad.get(key)
    return {
        "key": key,
        "value": value,
        "found": value is not None,
    }


@registry.tool(
    name="dynamic_prompt",
    description="Apply a prompt template with variable substitution. Built-in templates: explain, compare, summarize, analyze, debug.",
    category="Reasoning",
    parameters=[
        ToolParam("template_name", "string", "Name of the template to use"),
        ToolParam("variables", "string", "JSON object of variable substitutions, e.g. {\"topic\": \"AI\"}"),
    ]
)
def dynamic_prompt(template_name: str, variables: str) -> Dict[str, Any]:
    template = _prompt_templates.get(template_name)
    if not template:
        return {
            "error": f"Unknown template: {template_name}",
            "available": list(_prompt_templates.keys()),
        }

    try:
        vars_dict = json.loads(variables)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON for variables"}

    try:
        result = template.format(**vars_dict)
    except KeyError as e:
        return {"error": f"Missing variable: {e}", "template": template}

    return {
        "template": template_name,
        "prompt": result,
        "variables": vars_dict,
    }
