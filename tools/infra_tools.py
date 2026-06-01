"""
Infrastructure Tools — Model router status, cost tracking, performance APM, load balancer.
"""
import time
import logging
from typing import Dict, Any
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.infra")

# ─── Cost Tracking Store ─────────────────────────────────
_cost_log = []
_perf_log = []


@registry.tool(
    name="model_router_status",
    description="Get the current model routing configuration and statistics.",
    category="Infrastructure",
    parameters=[]
)
def model_router_status() -> Dict[str, Any]:
    from config import MODEL_PROFILES, MODEL_PROFILE
    from core.router import ROUTE_PATTERNS

    profiles = {}
    for pid, profile in MODEL_PROFILES.items():
        profiles[pid] = {
            "name": profile["name"],
            "file": profile["file"],
            "threads": profile["threads"],
            "has_drafts": bool(profile.get("drafts")),
        }

    return {
        "active_profile": MODEL_PROFILE,
        "available_profiles": profiles,
        "routing_patterns": list(ROUTE_PATTERNS.keys()),
        "total_profiles": len(profiles),
    }


@registry.tool(
    name="cost_tracker",
    description="Track token usage and estimate computational costs. Use action 'log' to record usage, 'summary' to view totals.",
    category="Infrastructure",
    parameters=[
        ToolParam("action", "string", "Action: 'log' to record, 'summary' to view, 'reset' to clear"),
        ToolParam("tokens", "integer", "Number of tokens used (for 'log' action)", required=False, default=0),
        ToolParam("model", "string", "Model used (for 'log' action)", required=False, default="default"),
    ]
)
def cost_tracker(action: str, tokens: int = 0, model: str = "default") -> Dict[str, Any]:
    if action == "log" and tokens > 0:
        entry = {
            "tokens": tokens,
            "model": model,
            "timestamp": time.time(),
            "estimated_cost_usd": tokens * 0.000002,  # Approximate local compute cost
        }
        _cost_log.append(entry)
        return {"status": "logged", "entry": entry}

    elif action == "summary":
        total_tokens = sum(e["tokens"] for e in _cost_log)
        total_cost = sum(e["estimated_cost_usd"] for e in _cost_log)
        return {
            "total_requests": len(_cost_log),
            "total_tokens": total_tokens,
            "estimated_total_cost_usd": round(total_cost, 6),
            "avg_tokens_per_request": total_tokens // max(len(_cost_log), 1),
        }

    elif action == "reset":
        _cost_log.clear()
        return {"status": "reset", "entries_cleared": True}

    return {"error": "Invalid action. Use 'log', 'summary', or 'reset'."}


@registry.tool(
    name="performance_apm",
    description="Application Performance Monitoring — track and analyze response latencies, throughput, and error rates.",
    category="Infrastructure",
    parameters=[
        ToolParam("action", "string", "Action: 'record' to log a metric, 'report' to view stats"),
        ToolParam("latency_ms", "integer", "Response latency in ms (for 'record')", required=False, default=0),
        ToolParam("success", "string", "Whether the request succeeded: 'true' or 'false'", required=False, default="true"),
    ]
)
def performance_apm(action: str, latency_ms: int = 0, success: str = "true") -> Dict[str, Any]:
    if action == "record":
        entry = {
            "latency_ms": latency_ms,
            "success": success == "true",
            "timestamp": time.time(),
        }
        _perf_log.append(entry)
        return {"status": "recorded"}

    elif action == "report":
        if not _perf_log:
            return {"message": "No performance data recorded yet."}

        latencies = [e["latency_ms"] for e in _perf_log]
        successes = [e for e in _perf_log if e["success"]]
        failures = [e for e in _perf_log if not e["success"]]

        return {
            "total_requests": len(_perf_log),
            "success_rate": round(len(successes) / len(_perf_log) * 100, 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
            "error_count": len(failures),
        }

    return {"error": "Invalid action. Use 'record' or 'report'."}


@registry.tool(
    name="load_balancer_info",
    description="Show the current model load distribution and resource usage.",
    category="Infrastructure",
    parameters=[]
)
def load_balancer_info() -> Dict[str, Any]:
    from core.llm import engine
    from core.monitor import monitor
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    stats = monitor.get_stats() if hasattr(monitor, 'get_stats') else {}

    return {
        "model_loaded": engine.is_loaded(),
        "system": {
            "cpu_percent": cpu_percent,
            "memory_used_gb": round(memory.used / (1024 ** 3), 2),
            "memory_total_gb": round(memory.total / (1024 ** 3), 2),
            "memory_percent": memory.percent,
        },
        "monitor_stats": stats,
    }
