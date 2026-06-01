"""
Stochastic Analysis — statistical analysis, time series, Monte Carlo simulations.
"""
import json
import math
import random
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="stoch_analyze",
    description="Stochastic analysis: descriptive statistics, correlation, regression, Monte Carlo simulation, random walks, probability distributions.",
    category="Analysis",
    parameters=[
        ToolParam("method", "string", "Method: describe, correlation, regression, monte_carlo_sim, random_walk, distribution"),
        ToolParam("data", "string", "JSON data (list of numbers or dict of lists)"),
        ToolParam("params", "string", "Additional parameters", required=False, default="{}"),
    ],
)
def stoch_analyze(method: str, data: str, params: str = "{}"):
    import numpy as np
    d = json.loads(data) if isinstance(data, str) else data
    p = json.loads(params) if isinstance(params, str) else params

    if method == "describe":
        arr = np.array(d, dtype=float)
        return {
            "count": len(arr), "mean": float(np.mean(arr)),
            "std": float(np.std(arr)), "min": float(np.min(arr)),
            "max": float(np.max(arr)), "median": float(np.median(arr)),
            "q25": float(np.percentile(arr, 25)),
            "q75": float(np.percentile(arr, 75)),
            "skewness": float(((arr - np.mean(arr)) ** 3).mean() / np.std(arr) ** 3) if np.std(arr) > 0 else 0,
            "variance": float(np.var(arr)),
        }

    elif method == "correlation":
        if isinstance(d, dict) and len(d) >= 2:
            keys = list(d.keys())
            x, y = np.array(d[keys[0]], dtype=float), np.array(d[keys[1]], dtype=float)
            corr = float(np.corrcoef(x, y)[0, 1])
            return {"variables": keys[:2], "correlation": corr, "r_squared": corr ** 2}
        return {"error": "Provide dict with at least 2 arrays"}

    elif method == "regression":
        if isinstance(d, dict) and len(d) >= 2:
            keys = list(d.keys())
            x, y = np.array(d[keys[0]], dtype=float), np.array(d[keys[1]], dtype=float)
            n = len(x)
            slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x ** 2) - np.sum(x) ** 2)
            intercept = (np.sum(y) - slope * np.sum(x)) / n
            y_pred = slope * x + intercept
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            return {
                "slope": float(slope), "intercept": float(intercept),
                "r_squared": float(r_squared), "equation": f"y = {slope:.4f}x + {intercept:.4f}",
            }
        return {"error": "Provide dict with at least 2 arrays (x, y)"}

    elif method == "monte_carlo_sim":
        n_sim = p.get("simulations", 10000)
        model = p.get("model", "normal")
        params_dist = p.get("dist_params", {"mean": 0, "std": 1})

        if model == "normal":
            samples = np.random.normal(params_dist.get("mean", 0), params_dist.get("std", 1), n_sim)
        elif model == "uniform":
            samples = np.random.uniform(params_dist.get("low", 0), params_dist.get("high", 1), n_sim)
        elif model == "lognormal":
            samples = np.random.lognormal(params_dist.get("mean", 0), params_dist.get("sigma", 1), n_sim)
        else:
            samples = np.random.normal(0, 1, n_sim)

        return {
            "simulations": n_sim, "model": model,
            "mean": float(np.mean(samples)), "std": float(np.std(samples)),
            "ci_95": [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))],
            "min": float(np.min(samples)), "max": float(np.max(samples)),
            "percentiles": {str(q): float(np.percentile(samples, q)) for q in [5, 25, 50, 75, 95]},
        }

    elif method == "random_walk":
        steps = p.get("steps", 100)
        n_walks = p.get("walks", 5)
        step_size = p.get("step_size", 1.0)

        walks = []
        for _ in range(n_walks):
            steps_arr = np.random.choice([-step_size, step_size], size=steps)
            walk = np.cumsum(steps_arr).tolist()
            walks.append({"final": walk[-1], "max": max(walk), "min": min(walk)})

        return {"walks": n_walks, "steps": steps, "results": walks}

    elif method == "distribution":
        arr = np.array(d, dtype=float)
        hist, edges = np.histogram(arr, bins=p.get("bins", 20))
        return {
            "histogram": hist.tolist(),
            "bin_edges": [float(e) for e in edges],
            "count": len(arr),
        }

    return {"error": f"Unknown method: {method}"}
