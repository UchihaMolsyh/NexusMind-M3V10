"""
Performance Optimizer — Dynamic performance tuning and optimization.
"""
import logging
import psutil
import time
from typing import Dict, Any, List
from pathlib import Path
import json

logger = logging.getLogger("nexusmind.optimizer")

class PerformanceOptimizer:
    def __init__(self):
        self.metrics_history = []
        self.optimization_rules = self._load_optimization_rules()
        self.last_optimization = 0
        
    def _load_optimization_rules(self) -> Dict:
        """Load optimization rules from config."""
        return {
            "memory_threshold": 80,  # %
            "cpu_threshold": 90,     # %
            "latency_threshold": 5.0, # seconds
            "tps_threshold": 10,     # tokens per second minimum
            "auto_optimize": True
        }
    
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect current system and performance metrics."""
        metrics = {
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {},
        }
        
        # Add AI-specific metrics if available
        try:
            from core.monitor import monitor
            ai_metrics = monitor.get_metrics()
            metrics.update(ai_metrics)
        except:
            pass
            
        self.metrics_history.append(metrics)
        
        # Keep only last 100 entries
        if len(self.metrics_history) > 100:
            self.metrics_history = self.metrics_history[-100:]
            
        return metrics
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance and suggest optimizations."""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        current = self.metrics_history[-1]
        analysis = {
            "status": "optimal",
            "issues": [],
            "recommendations": []
        }
        
        # Check CPU usage
        if current["cpu_percent"] > self.optimization_rules["cpu_threshold"]:
            analysis["issues"].append(f"High CPU usage: {current['cpu_percent']:.1f}%")
            analysis["recommendations"].append("Consider reducing model threads or enabling GPU offloading")
            analysis["status"] = "degraded"
        
        # Check memory usage
        if current["memory_percent"] > self.optimization_rules["memory_threshold"]:
            analysis["issues"].append(f"High memory usage: {current['memory_percent']:.1f}%")
            analysis["recommendations"].append("Enable mmap, reduce context size, or clear memory cache")
            analysis["status"] = "degraded"
        
        # Check latency
        if "avg_latency" in current and current["avg_latency"] > self.optimization_rules["latency_threshold"]:
            analysis["issues"].append(f"High latency: {current['avg_latency']:.2f}s")
            analysis["recommendations"].append("Switch to lightweight model or enable speculative decoding")
            analysis["status"] = "degraded"
        
        # Check TPS
        if "avg_tps" in current and current["avg_tps"] < self.optimization_rules["tps_threshold"]:
            analysis["issues"].append(f"Low tokens/sec: {current['avg_tps']:.1f}")
            analysis["recommendations"].append("Increase batch size or use faster model")
            analysis["status"] = "suboptimal"
        
        return analysis
    
    def apply_optimizations(self, analysis: Dict[str, Any]) -> List[str]:
        """Apply automatic optimizations based on analysis."""
        applied = []
        
        if not self.optimization_rules["auto_optimize"]:
            return applied
        
        # Memory optimizations
        if "High memory usage" in str(analysis["issues"]):
            # Clear caches
            try:
                from core.memory import MemorySystem
                memory = MemorySystem()
                memory.clear_short_term()
                applied.append("Cleared short-term memory cache")
            except:
                pass
        
        # Model optimizations
        if "High latency" in str(analysis["issues"]):
            # Suggest model switch
            try:
                from config import MODEL_PROFILES
                lightweight = MODEL_PROFILES.get("LIGHTWEIGHT")
                if lightweight:
                    applied.append(f"Consider switching to {lightweight['name']} for faster responses")
            except:
                pass
        
        return applied
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate a comprehensive optimization report."""
        metrics = self.collect_metrics()
        analysis = self.analyze_performance()
        optimizations = self.apply_optimizations(analysis)
        
        return {
            "current_metrics": metrics,
            "performance_analysis": analysis,
            "applied_optimizations": optimizations,
            "recommendations": analysis["recommendations"],
            "trends": self._calculate_trends()
        }
    
    def _calculate_trends(self) -> Dict[str, str]:
        """Calculate performance trends from history."""
        if len(self.metrics_history) < 10:
            return {"status": "insufficient_data"}
        
        recent = self.metrics_history[-10:]
        older = self.metrics_history[-20:-10] if len(self.metrics_history) >= 20 else self.metrics_history[:10]
        
        trends = {}
        
        # CPU trend
        recent_cpu = sum(m["cpu_percent"] for m in recent) / len(recent)
        older_cpu = sum(m["cpu_percent"] for m in older) / len(older)
        trends["cpu"] = "increasing" if recent_cpu > older_cpu + 5 else "stable"
        
        # Memory trend
        recent_mem = sum(m["memory_percent"] for m in recent) / len(recent)
        older_mem = sum(m["memory_percent"] for m in older) / len(older)
        trends["memory"] = "increasing" if recent_mem > older_mem + 5 else "stable"
        
        # Latency trend (if available)
        if "avg_latency" in recent[-1] and "avg_latency" in older[-1]:
            recent_lat = recent[-1]["avg_latency"]
            older_lat = older[-1]["avg_latency"]
            trends["latency"] = "improving" if recent_lat < older_lat else "degrading"
        
        return trends
    
    def optimize_for_speed(self) -> Dict[str, Any]:
        """Apply aggressive speed optimizations."""
        optimizations = {
            "model_switch": None,
            "context_reduction": False,
            "cache_cleared": False,
            "threads_adjusted": False
        }
        
        # Switch to lightweight model
        try:
            from config import MODEL_PROFILES, MODEL_PROFILE
            if MODEL_PROFILE != "LIGHTWEIGHT":
                lightweight = MODEL_PROFILES.get("LIGHTWEIGHT")
                if lightweight:
                    optimizations["model_switch"] = lightweight["name"]
                    # Note: Actual model switching would need to be implemented in LLMEngine
        except:
            pass
        
        # Reduce context size
        try:
            from config import CONTEXT_LENGTH
            if CONTEXT_LENGTH > 2048:
                optimizations["context_reduction"] = True
                # Note: Actual reduction would need to update config
        except:
            pass
        
        # Clear caches
        try:
            from core.memory import MemorySystem
            memory = MemorySystem()
            memory.clear_short_term()
            optimizations["cache_cleared"] = True
        except:
            pass
        
        return optimizations

# Global optimizer instance
optimizer = PerformanceOptimizer()
