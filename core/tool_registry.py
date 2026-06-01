"""
Tool Registry — register, discover, and dispatch tools for LLM function calling.
"""
import json
import re
import traceback
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field


@dataclass
class ToolParam:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class Tool:
    name: str
    description: str
    category: str
    parameters: List[ToolParam] = field(default_factory=list)
    handler: Optional[Callable] = None

    def schema(self) -> Dict:
        props = {}
        required = []
        for p in self.parameters:
            props[p.name] = {"type": p.type, "description": p.description}
            if p.default is not None:
                props[p.name]["default"] = p.default
            if p.required:
                required.append(p.name)
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
        }


class ToolRegistry:
    """Central registry for all NexusMind tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def tool(self, name: str, description: str, category: str, parameters: List[ToolParam] = None):
        """Decorator to register a function as a tool."""
        def decorator(func):
            t = Tool(
                name=name,
                description=description,
                category=category,
                parameters=parameters or [],
                handler=func,
            )
            self._tools[name] = t
            return func
        return decorator

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict]:
        return [t.schema() for t in self._tools.values()]

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def by_category(self) -> Dict[str, List[str]]:
        cats: Dict[str, List[str]] = {}
        for t in self._tools.values():
            cats.setdefault(t.category, []).append(t.name)
        return cats

    async def execute(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}", "success": False}
        if not tool.handler:
            return {"error": f"Tool '{name}' has no handler", "success": False}
        try:
            import inspect
            import asyncio
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(**args)
            else:
                result = await asyncio.to_thread(tool.handler, **args)
            return {"result": result, "success": True, "tool": name}
        except Exception as e:
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "success": False,
                "tool": name,
            }

    def tools_prompt(self) -> str:
        lines = ["Available tools:\n"]
        for cat, names in self.by_category().items():
            lines.append(f"### {cat}")
            for n in names:
                t = self._tools[n]
                params = ", ".join(
                    f"{p.name}: {p.type}" for p in t.parameters
                )
                lines.append(f"- **{n}**({params}): {t.description}")
            lines.append("")
        return "\n".join(lines)


def parse_tool_calls(text: str) -> List[Dict[str, Any]]:
    """Extract tool calls from LLM output. Looks for JSON objects with 'tool' key."""
    calls = []
    # Match JSON objects in the text
    pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+?"[^{}]*\}'
    matches = re.findall(pattern, text, re.DOTALL)
    for m in matches:
        try:
            obj = json.loads(m)
            if "tool" in obj:
                calls.append({
                    "tool": obj["tool"],
                    "args": obj.get("args", obj.get("arguments", {})),
                })
        except json.JSONDecodeError:
            continue
    return calls


# Global registry instance
registry = ToolRegistry()
