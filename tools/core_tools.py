import os
import requests
import logging
import subprocess
from bs4 import BeautifulSoup
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.core")

@registry.tool(
    name="web_search",
    description="Search the web for real-time information.",
    category="Search",
    parameters=[
        ToolParam("query", "string", "The search query")
    ]
)
def web_search(query: str):
    """Simple web search via DuckDuckGo (no-API version)."""
    try:
        url = f"https://duckduckgo.com/html/?q={query}"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for result in soup.find_all("div", class_="result__body")[:5]:
            title_tag = result.find("a", class_="result__a")
            snippet_tag = result.find("a", class_="result__snippet")
            if title_tag and snippet_tag:
                results.append({"title": title_tag.text, "snippet": snippet_tag.text})
            
        return {"results": results, "success": True}
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return {"error": str(e), "success": False}

@registry.tool(
    name="calculator",
    description="Perform mathematical calculations.",
    category="Math",
    parameters=[
        ToolParam("expression", "string", "The mathematical expression to evaluate")
    ]
)
def calculator(expression: str):
    """Safe math evaluator."""
    try:
        allowed_chars = "0123456789+-*/(). "
        if all(c in allowed_chars for c in expression):
            result = eval(expression, {"__builtins__": {}})
            return {"result": result, "success": True}
        return {"error": "Invalid characters in expression", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}

@registry.tool(
    name="shell_access",
    description="Execute shell commands on the local system (REQUIRES CONFIRMATION).",
    category="System",
    parameters=[
        ToolParam("command", "string", "The shell command to execute")
    ]
)
def shell_access(command: str):
    """Execute shell commands with local wrapper."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

@registry.tool(
    name="wikipedia_search",
    description="Search Wikipedia for information.",
    category="Search",
    parameters=[
        ToolParam("query", "string", "The search query")
    ]
)
def wikipedia_search(query: str):
    """Search Wikipedia using its API."""
    try:
        url = f"https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("query", {}).get("search", []):
            results.append({
                "title": item["title"],
                "snippet": item["snippet"],
                "pageid": item["pageid"]
            })
        return {"results": results, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

@registry.tool(
    name="github_search",
    description="Search GitHub for repositories.",
    category="Search",
    parameters=[
        ToolParam("query", "string", "The search query")
    ]
)
def github_search(query: str):
    """Search GitHub repositories."""
    try:
        url = f"https://api.github.com/search/repositories"
        params = {"q": query, "sort": "stars", "order": "desc"}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("items", [])[:5]:
            results.append({
                "full_name": item["full_name"],
                "description": item["description"],
                "stars": item["stargazers_count"],
                "url": item["html_url"]
            })
        return {"results": results, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

@registry.tool(
    name="optimize_performance",
    description="Optimize system performance for speed and efficiency.",
    category="System",
    parameters=[
        ToolParam("mode", "string", "Optimization mode: 'speed' or 'balanced'")
    ]
)
def optimize_performance(mode: str = "balanced"):
    """Optimize system performance."""
    try:
        if mode == "speed":
            optimizations = optimizer.optimize_for_speed()
        else:
            report = optimizer.get_optimization_report()
            optimizations = report["applied_optimizations"]
        
        return {
            "success": True,
            "optimizations": optimizations,
            "message": f"Performance optimization completed in {mode} mode"
        }
    except Exception as e:
        return {"error": str(e), "success": False}

@registry.tool(
    name="get_performance_report",
    description="Get detailed performance metrics and analysis.",
    category="System",
    parameters=[]
)
def get_performance_report():
    """Get performance report."""
    try:
        report = optimizer.get_optimization_report()
        return {"report": report, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}
@registry.tool(
    name="read_local_file",
    description="Read content from a local file.",
    category="File IO",
    parameters=[
        ToolParam("path", "string", "The absolute path to the file")
    ]
)
def read_local_file(path: str):
    """Read local file safely."""
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"content": content, "success": True}
        return {"error": f"File not found: {path}", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
