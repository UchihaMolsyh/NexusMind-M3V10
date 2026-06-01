"""
Static Analysis — code analysis using pylint/bandit or built-in checkers.
"""
import json
import subprocess
import ast
import re
from pathlib import Path
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam


def _builtin_python_check(code: str) -> List[Dict]:
    """Basic Python code analysis without external tools."""
    issues = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [{"type": "error", "line": e.lineno, "message": f"Syntax error: {e.msg}"}]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id == "eval":
                    issues.append({"type": "security", "line": node.lineno, "message": "Use of eval() — potential code injection"})
                elif node.func.id == "exec":
                    issues.append({"type": "security", "line": node.lineno, "message": "Use of exec() — potential code injection"})
                elif node.func.id == "input":
                    issues.append({"type": "info", "line": node.lineno, "message": "Use of input() — user input not validated"})

        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            module = getattr(node, 'module', None) or (node.names[0].name if node.names else '')
            if module in ('os', 'subprocess', 'shutil'):
                issues.append({"type": "warning", "line": node.lineno, "message": f"Import of system module: {module}"})

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                issues.append({"type": "warning", "line": node.lineno, "message": "Bare except clause — catches all exceptions"})

    # Check for common issues via regex
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        if "password" in line.lower() and "=" in line and ("'" in line or '"' in line):
            issues.append({"type": "security", "line": i, "message": "Possible hardcoded password"})
        if re.search(r'TODO|FIXME|HACK|XXX', line, re.IGNORECASE):
            issues.append({"type": "info", "line": i, "message": f"TODO/FIXME found: {line.strip()[:80]}"})

    return issues


@registry.tool(
    name="static_analyze",
    description="Analyze code for bugs, security issues, and style problems. Supports Python with built-in checker, or pylint/bandit if installed.",
    category="Code Analysis",
    parameters=[
        ToolParam("code_or_path", "string", "Python code string or file path to analyze"),
        ToolParam("tool", "string", "Analysis tool: builtin, pylint, bandit", required=False, default="builtin"),
    ],
)
def static_analyze(code_or_path: str, tool: str = "builtin"):
    # Determine if it's a file path or inline code
    p = Path(code_or_path)
    if p.exists() and p.is_file():
        code = p.read_text(encoding="utf-8", errors="replace")
        file_path = str(p)
    else:
        code = code_or_path
        file_path = None

    if tool == "builtin":
        issues = _builtin_python_check(code)
        return {
            "tool": "builtin",
            "issues": issues,
            "total": len(issues),
            "security": sum(1 for i in issues if i["type"] == "security"),
            "warnings": sum(1 for i in issues if i["type"] == "warning"),
        }

    elif tool == "pylint" and file_path:
        try:
            result = subprocess.run(
                ["pylint", file_path, "--output-format=json", "--disable=C"],
                capture_output=True, text=True, timeout=30,
            )
            issues = json.loads(result.stdout) if result.stdout else []
            return {"tool": "pylint", "issues": issues[:50], "total": len(issues)}
        except FileNotFoundError:
            return {"error": "pylint not installed. pip install pylint"}
        except Exception as e:
            return {"error": str(e)}

    elif tool == "bandit" and file_path:
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", file_path],
                capture_output=True, text=True, timeout=30,
            )
            data = json.loads(result.stdout) if result.stdout else {}
            return {"tool": "bandit", "results": data.get("results", [])[:50]}
        except FileNotFoundError:
            return {"error": "bandit not installed. pip install bandit"}
        except Exception as e:
            return {"error": str(e)}

    return {"error": f"Unsupported tool or missing file path for: {tool}"}
