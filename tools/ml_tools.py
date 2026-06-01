"""
ML Tools — Hyperparameter tuning, AutoML, Synthetic Data, Continual Learning.
"""
import json
import time
import random
import logging
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.ml")


@registry.tool(
    name="hyperparameter_search",
    description="Perform grid or random search over hyperparameter space for the neural network.",
    category="Machine Learning",
    parameters=[
        ToolParam("param_space", "string", "JSON object of parameter ranges, e.g. {\"learning_rate\": [0.01, 0.1, 0.5], \"layers\": [[2,4,1], [2,8,4,1]]}"),
        ToolParam("method", "string", "Search method: 'grid' or 'random'", required=False, default="random"),
        ToolParam("max_trials", "integer", "Maximum number of trials for random search", required=False, default=5),
    ]
)
def hyperparameter_search(param_space: str, method: str = "random", max_trials: int = 5) -> Dict[str, Any]:
    try:
        space = json.loads(param_space)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON for param_space"}

    from core.neural_network import NeuralNetwork, get_demo_dataset
    X, y, _ = get_demo_dataset("xor")

    trials = []

    if method == "grid":
        # Simple grid search
        import itertools
        keys = list(space.keys())
        combos = list(itertools.product(*[space[k] for k in keys]))[:max_trials]
        for combo in combos:
            params = dict(zip(keys, combo))
            layers = params.get("layers", [2, 4, 1])
            lr = params.get("learning_rate", 0.1)
            nn = NeuralNetwork(layers, learning_rate=lr)
            nn.train(X, y, epochs=200)
            trials.append({
                "params": params,
                "final_loss": nn.loss_history[-1] if nn.loss_history else None,
                "final_accuracy": nn.accuracy_history[-1] if nn.accuracy_history else None,
            })
    else:
        # Random search
        for _ in range(max_trials):
            params = {}
            for k, v in space.items():
                params[k] = random.choice(v) if isinstance(v, list) else v
            layers = params.get("layers", [2, 4, 1])
            lr = params.get("learning_rate", 0.1)
            nn = NeuralNetwork(layers, learning_rate=lr)
            nn.train(X, y, epochs=200)
            trials.append({
                "params": params,
                "final_loss": nn.loss_history[-1] if nn.loss_history else None,
                "final_accuracy": nn.accuracy_history[-1] if nn.accuracy_history else None,
            })

    # Sort by loss
    trials.sort(key=lambda t: t["final_loss"] or float("inf"))
    return {
        "method": method,
        "total_trials": len(trials),
        "best_trial": trials[0] if trials else None,
        "all_trials": trials,
    }


@registry.tool(
    name="auto_ml_classify",
    description="Simple AutoML: automatically train and evaluate a neural network classifier on provided data.",
    category="Machine Learning",
    parameters=[
        ToolParam("data", "string", "JSON array of data points, each with 'features' (list) and 'label' (int)"),
    ]
)
def auto_ml_classify(data: str) -> Dict[str, Any]:
    try:
        dataset = json.loads(data)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON data"}

    import numpy as np
    from core.neural_network import NeuralNetwork

    features = [d["features"] for d in dataset]
    labels = [d["label"] for d in dataset]
    X = np.array(features, dtype=np.float64)
    num_classes = max(labels) + 1

    # One-hot encode labels
    y = np.zeros((len(labels), num_classes))
    for i, l in enumerate(labels):
        y[i][l] = 1

    input_dim = X.shape[1]
    layers = [input_dim, max(input_dim * 2, 8), max(input_dim, 4), num_classes]

    nn = NeuralNetwork(layers, learning_rate=0.1)
    nn.train(X, y, epochs=500)

    predictions = nn.predict(X)
    pred_labels = np.argmax(predictions, axis=1)
    true_labels = np.argmax(y, axis=1)
    accuracy = float(np.mean(pred_labels == true_labels))

    return {
        "architecture": layers,
        "epochs": 500,
        "accuracy": round(accuracy, 4),
        "num_classes": num_classes,
        "num_samples": len(dataset),
    }


@registry.tool(
    name="synthetic_data_gen",
    description="Generate synthetic training data from templates or distributions.",
    category="Machine Learning",
    parameters=[
        ToolParam("data_type", "string", "Type: 'classification', 'regression', 'text'"),
        ToolParam("num_samples", "integer", "Number of samples to generate", required=False, default=100),
        ToolParam("num_features", "integer", "Number of features (for classification/regression)", required=False, default=4),
    ]
)
def synthetic_data_gen(data_type: str, num_samples: int = 100, num_features: int = 4) -> Dict[str, Any]:
    import numpy as np

    if data_type == "classification":
        X = np.random.randn(num_samples, num_features)
        # Simple linear boundary + noise
        weights = np.random.randn(num_features)
        y = (X @ weights > 0).astype(int)
        return {
            "type": "classification",
            "samples": num_samples,
            "features": num_features,
            "data": [{"features": x.tolist(), "label": int(l)} for x, l in zip(X[:10], y[:10])],
            "preview": "Showing first 10 samples",
            "full_size": num_samples,
        }

    elif data_type == "regression":
        X = np.random.randn(num_samples, num_features)
        weights = np.random.randn(num_features)
        y = X @ weights + np.random.randn(num_samples) * 0.1
        return {
            "type": "regression",
            "samples": num_samples,
            "features": num_features,
            "data": [{"features": x.tolist(), "target": float(t)} for x, t in zip(X[:10], y[:10])],
            "preview": "Showing first 10 samples",
        }

    elif data_type == "text":
        templates = [
            "The {adj} {noun} {verb} the {noun2}.",
            "{noun} is a type of {category}.",
            "In {year}, the {noun} was {adj}.",
        ]
        adjs = ["quick", "lazy", "bright", "dark", "clever"]
        nouns = ["fox", "dog", "cat", "robot", "engine"]
        verbs = ["chased", "found", "built", "analyzed", "trained"]
        categories = ["animal", "tool", "concept", "system"]

        samples = []
        for _ in range(min(num_samples, 20)):
            t = random.choice(templates)
            text = t.format(
                adj=random.choice(adjs), noun=random.choice(nouns),
                verb=random.choice(verbs), noun2=random.choice(nouns),
                category=random.choice(categories), year=random.randint(2000, 2025)
            )
            samples.append(text)

        return {"type": "text", "samples": samples, "count": len(samples)}

    return {"error": f"Unknown data_type: {data_type}"}


@registry.tool(
    name="continual_learn",
    description="Add new knowledge to the system's long-term memory for continual learning without catastrophic forgetting.",
    category="Machine Learning",
    parameters=[
        ToolParam("knowledge", "string", "The new knowledge to learn"),
        ToolParam("category", "string", "Category for the knowledge", required=False, default="learned"),
        ToolParam("importance", "string", "Importance level: 'low', 'medium', 'high'", required=False, default="medium"),
    ]
)
def continual_learn(knowledge: str, category: str = "learned", importance: str = "medium") -> Dict[str, Any]:
    from core.vector_memory import vector_memory
    import hashlib

    importance_map = {"low": 0.3, "medium": 0.6, "high": 0.9}
    imp_score = importance_map.get(importance, 0.6)

    mem_id = hashlib.md5(knowledge[:50].encode()).hexdigest()
    vector_memory.add_memory(
        content=knowledge,
        metadata={
            "type": "continual_learning",
            "category": category,
            "importance": imp_score,
            "timestamp": time.time(),
        },
        memory_id=f"cl_{mem_id}"
    )

    return {
        "status": "learned",
        "category": category,
        "importance": importance,
        "knowledge_preview": knowledge[:100],
    }
