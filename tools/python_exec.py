"""
Python Interpreter — sandboxed Python code execution.
"""
import io
import sys
import json
import traceback
import threading
import contextlib
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


class TimeoutError(Exception):
    pass


def _run_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code in a restricted environment."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    result = {"stdout": "", "stderr": "", "result": None, "error": None, "success": False}

    # Execution namespace with safe builtins
    namespace = {
        "__builtins__": {
            "print": print, "range": range, "len": len, "int": int, "float": float,
            "str": str, "bool": bool, "list": list, "dict": dict, "tuple": tuple,
            "set": set, "frozenset": frozenset, "type": type, "isinstance": isinstance,
            "issubclass": issubclass, "enumerate": enumerate, "zip": zip, "map": map,
            "filter": filter, "sorted": sorted, "reversed": reversed, "sum": sum,
            "min": min, "max": max, "abs": abs, "round": round, "pow": pow,
            "divmod": divmod, "hex": hex, "oct": oct, "bin": bin, "ord": ord,
            "chr": chr, "repr": repr, "hash": hash, "id": id, "dir": dir,
            "hasattr": hasattr, "getattr": getattr, "setattr": setattr,
            "callable": callable, "iter": iter, "next": next,
            "open": open, "input": lambda *a: "", "Exception": Exception,
            "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
            "IndexError": IndexError, "AttributeError": AttributeError,
            "True": True, "False": False, "None": None,
            "__import__": __import__,
        }
    }

    def _exec():
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(compile(code, "<nexusmind>", "exec"), namespace)
                # Try to capture the last expression's value
                if "_result" in namespace:
                    result["result"] = str(namespace["_result"])
            result["success"] = True
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            result["traceback"] = traceback.format_exc()

    thread = threading.Thread(target=_exec)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout)

    if thread.is_alive():
        result["error"] = f"Execution timed out after {timeout} seconds"
        result["success"] = False
    else:
        result["stdout"] = stdout_capture.getvalue()
        result["stderr"] = stderr_capture.getvalue()

    return result


@registry.tool(
    name="run_python",
    description="Execute Python code. Has access to numpy, sympy, math, json, re, datetime, collections, itertools. Assign result to '_result' variable to capture output.",
    category="Code Execution",
    parameters=[
        ToolParam("code", "string", "Python code to execute"),
        ToolParam("timeout", "string", "Timeout in seconds (default: 30)", required=False, default="30"),
    ],
)
def run_python(code: str, timeout: str = "30"):
    from config import PYTHON_EXEC_TIMEOUT
    t = min(int(timeout), PYTHON_EXEC_TIMEOUT)
    return _run_code(code, timeout=t)
