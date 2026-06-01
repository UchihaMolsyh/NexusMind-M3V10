"""
Resource Monitor — Tracks latency, token usage, and system resources.
"""
import os
import time
import psutil
import logging
from typing import Dict, Any

logger = logging.getLogger("nexusmind.monitor")


class ResourceMonitor:
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {
            "total_tokens": 0,
            "total_requests": 0,
            "avg_latency": 0.0,
            "peak_latency": 0.0,
            "failed_interactions": 0,
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get CPU, Memory, and Disk usage (cross-platform)."""
        # Use the correct disk path based on OS
        disk_path = "C:\\" if os.name == "nt" else "/"
        try:
            disk_pct = psutil.disk_usage(disk_path).percent
        except Exception:
            disk_pct = 0.0
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "disk_percent": disk_pct,
            "uptime_seconds": int(time.time() - self.start_time),
        }

    def log_interaction(self, tokens: int, latency: float, success: bool = True):
        """Record metrics for an interaction."""
        self.metrics["total_requests"] += 1
        self.metrics["total_tokens"] += tokens
        
        # Update running average latency
        n = self.metrics["total_requests"]
        curr_avg = self.metrics["avg_latency"]
        self.metrics["avg_latency"] = round(((curr_avg * (n - 1)) + latency) / n, 3)
        
        # Track peak latency
        if latency > self.metrics["peak_latency"]:
            self.metrics["peak_latency"] = round(latency, 3)
        
        if not success:
            self.metrics["failed_interactions"] += 1

    def get_metrics(self) -> Dict[str, Any]:
        return {**self.metrics, **self.get_system_stats()}

monitor = ResourceMonitor()
