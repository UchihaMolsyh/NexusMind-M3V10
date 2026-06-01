"""
System Tools — diagnostics and benchmarking for NexusMind.
"""
import os
import sys
import time
import platform
import logging
from typing import Dict, Any
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.system")


@registry.tool(
    name="system_diagnostics",
    description="Get detailed system information: CPU, RAM, disk, OS, Python version, model status, and loaded tools.",
    category="System",
    parameters=[],
)
def system_diagnostics():
    """Full system diagnostics report."""
    try:
        import psutil
        from config import MODELS_DIR, MODEL_PROFILES, MODEL_PROFILE, CURRENT_PROFILE
        from core.llm import engine
        from core.monitor import monitor
        
        # System info
        mem = psutil.virtual_memory()
        disk_path = "C:\\" if os.name == "nt" else "/"
        disk = psutil.disk_usage(disk_path)
        
        # Model info
        models_status = {}
        for pid, profile in MODEL_PROFILES.items():
            path = MODELS_DIR / profile["file"]
            models_status[pid] = {
                "name": profile["name"],
                "file": profile["file"],
                "exists": path.exists(),
                "size_mb": round(path.stat().st_size / (1024 * 1024), 1) if path.exists() else 0,
            }
        
        # Tool count
        tool_count = len(registry.list_names())
        
        return {
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "python": sys.version.split()[0],
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "ram_total_gb": round(mem.total / (1024**3), 2),
                "ram_used_gb": round(mem.used / (1024**3), 2),
                "ram_percent": mem.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_percent": disk.percent,
            },
            "model": {
                "active_profile": MODEL_PROFILE,
                "active_model": CURRENT_PROFILE["file"],
                "loaded": engine.is_loaded,
                "profiles": models_status,
            },
            "tools": {
                "registered": tool_count,
                "categories": registry.by_category(),
            },
            "metrics": monitor.get_metrics(),
            "success": True,
        }
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        return {"error": str(e), "success": False}


@registry.tool(
    name="benchmark",
    description="Run a quick benchmark to measure tokens per second for the current model.",
    category="System",
    parameters=[
        ToolParam("prompt", "string", "Prompt to benchmark with", required=False, default="Explain quantum computing in 3 sentences."),
        ToolParam("max_tokens", "string", "Max tokens to generate", required=False, default="100"),
    ],
)
def benchmark(prompt: str = "Explain quantum computing in 3 sentences.", max_tokens: str = "100"):
    """Benchmark the current model's speed."""
    try:
        from core.llm import engine
        
        if not engine.is_loaded:
            engine.load()
        
        messages = [{"role": "user", "content": prompt}]
        
        start = time.perf_counter()
        token_count = 0
        
        stream = engine.generate(
            messages=messages,
            max_tokens=int(max_tokens),
            temperature=0.7,
            stream=True,
        )
        
        output = ""
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {}).get("content", "")
            if delta:
                output += delta
                token_count += 1
        
        elapsed = time.perf_counter() - start
        tps = round(token_count / elapsed, 2) if elapsed > 0 else 0
        
        return {
            "tokens_generated": token_count,
            "elapsed_seconds": round(elapsed, 3),
            "tokens_per_second": tps,
            "output_preview": output[:200],
            "success": True,
        }
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return {"error": str(e), "success": False}
