"""
Model Tools — quantization, pruning, and distillation utilities.
"""
import json
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="model_quantize",
    description="Quantize GGUF models or analyze quantization options. Provides info about quantization methods and estimates sizes.",
    category="Model Tools",
    parameters=[
        ToolParam("action", "string", "Action: info, estimate, convert"),
        ToolParam("params", "string", "JSON params: model_path, method (q4_k_m, q5_k_m, q8_0, etc.), target_path"),
    ],
)
def model_quantize(action: str, params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    if action == "info":
        return {
            "quantization_methods": {
                "q2_k": {"bits": 2, "quality": "Low", "size_ratio": 0.25, "speed": "Fastest"},
                "q3_k_m": {"bits": 3, "quality": "Low-Medium", "size_ratio": 0.35, "speed": "Very Fast"},
                "q4_k_m": {"bits": 4, "quality": "Medium", "size_ratio": 0.45, "speed": "Fast"},
                "q5_k_m": {"bits": 5, "quality": "Medium-High", "size_ratio": 0.55, "speed": "Medium"},
                "q6_k": {"bits": 6, "quality": "High", "size_ratio": 0.65, "speed": "Medium-Slow"},
                "q8_0": {"bits": 8, "quality": "Very High", "size_ratio": 0.85, "speed": "Slow"},
                "f16": {"bits": 16, "quality": "Full", "size_ratio": 1.0, "speed": "Slowest"},
            },
            "recommendation": "q4_k_m offers the best quality/size balance for most use cases.",
        }

    elif action == "estimate":
        params_b = p.get("parameters_billions", 4)
        methods = ["q2_k", "q3_k_m", "q4_k_m", "q5_k_m", "q6_k", "q8_0", "f16"]
        ratios = [0.25, 0.35, 0.45, 0.55, 0.65, 0.85, 1.0]
        base_size_gb = params_b * 2  # FP16 baseline
        estimates = {}
        for m, r in zip(methods, ratios):
            size = base_size_gb * r
            ram = size * 1.3
            estimates[m] = {"file_size_gb": round(size, 2), "ram_required_gb": round(ram, 2)}
        return {"model_parameters_B": params_b, "estimates": estimates}

    elif action == "convert":
        return {
            "note": "GGUF quantization requires llama.cpp's quantize tool.",
            "command_example": f"./quantize {p.get('model_path', 'model.gguf')} {p.get('target_path', 'output.gguf')} {p.get('method', 'q4_k_m')}",
            "install": "Clone https://github.com/ggerganov/llama.cpp and build with cmake",
        }

    return {"error": f"Unknown action: {action}"}


@registry.tool(
    name="model_prune",
    description="Model pruning information and utilities. Explains pruning strategies and provides tools for analyzing model sparsity.",
    category="Model Tools",
    parameters=[
        ToolParam("action", "string", "Action: info, analyze"),
        ToolParam("params", "string", "JSON parameters", required=False, default="{}"),
    ],
)
def model_prune(action: str, params: str = "{}"):
    if action == "info":
        return {
            "pruning_methods": {
                "magnitude": "Remove weights with smallest absolute values",
                "structured": "Remove entire neurons/channels/heads",
                "unstructured": "Remove individual weights (requires sparse computation)",
                "lottery_ticket": "Find minimal subnetwork that trains to full accuracy",
                "movement": "Prune weights that move towards zero during fine-tuning",
            },
            "typical_sparsity": "50-90% of weights can often be removed with minimal accuracy loss",
            "recommendation": "Magnitude pruning at 50% sparsity is a safe starting point",
        }

    elif action == "analyze":
        p = json.loads(params) if isinstance(params, str) else params
        params_b = p.get("parameters_billions", 4)
        sparsity = p.get("target_sparsity", 0.5)
        remaining = params_b * (1 - sparsity)
        return {
            "original_params_B": params_b,
            "target_sparsity": sparsity,
            "remaining_params_B": round(remaining, 2),
            "estimated_speedup": f"{1 / (1 - sparsity * 0.7):.1f}x",
            "memory_savings": f"{sparsity * 100:.0f}%",
        }

    return {"error": f"Unknown action: {action}"}
