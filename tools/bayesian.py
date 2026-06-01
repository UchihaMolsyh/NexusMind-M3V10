"""
Bayesian Inference — Bayesian updating, probability calculations, and statistical reasoning.
"""
import json
import math
import random
from typing import Dict, List, Any, Optional
from core.tool_registry import registry, ToolParam


class BayesianEngine:
    """Lightweight Bayesian inference without heavy dependencies."""

    @staticmethod
    def bayes_update(prior: float, likelihood: float, evidence: float) -> float:
        """P(H|E) = P(E|H) * P(H) / P(E)"""
        if evidence == 0:
            return 0.0
        return (likelihood * prior) / evidence

    @staticmethod
    def bayes_update_full(prior: float, likelihood: float, likelihood_not: float) -> Dict[str, float]:
        """Full Bayesian update with complement."""
        evidence = likelihood * prior + likelihood_not * (1 - prior)
        posterior = (likelihood * prior) / evidence if evidence > 0 else 0
        return {
            "prior": prior,
            "likelihood": likelihood,
            "likelihood_given_not_h": likelihood_not,
            "evidence": round(evidence, 6),
            "posterior": round(posterior, 6),
            "bayes_factor": round(likelihood / likelihood_not, 4) if likelihood_not > 0 else float("inf"),
        }

    @staticmethod
    def sequential_update(prior: float, observations: List[Dict[str, float]]) -> Dict[str, Any]:
        """Sequential Bayesian updating with multiple observations."""
        current = prior
        history = [{"step": 0, "posterior": prior}]

        for i, obs in enumerate(observations):
            lk = obs.get("likelihood", 0.5)
            lk_not = obs.get("likelihood_not", 0.5)
            evidence = lk * current + lk_not * (1 - current)
            current = (lk * current) / evidence if evidence > 0 else 0
            history.append({
                "step": i + 1,
                "observation": obs.get("name", f"obs_{i+1}"),
                "posterior": round(current, 6),
            })

        return {
            "initial_prior": prior,
            "final_posterior": round(current, 6),
            "num_observations": len(observations),
            "history": history,
        }

    @staticmethod
    def beta_binomial(successes: int, failures: int, prior_alpha: float = 1, prior_beta: float = 1) -> Dict[str, Any]:
        """Beta-Binomial model for estimating probability from data."""
        alpha = prior_alpha + successes
        beta_param = prior_beta + failures
        mean = alpha / (alpha + beta_param)
        variance = (alpha * beta_param) / ((alpha + beta_param)**2 * (alpha + beta_param + 1))
        mode = (alpha - 1) / (alpha + beta_param - 2) if alpha > 1 and beta_param > 1 else mean

        # 95% credible interval (approximation)
        std = math.sqrt(variance)
        ci_low = max(0, mean - 1.96 * std)
        ci_high = min(1, mean + 1.96 * std)

        return {
            "posterior_alpha": alpha,
            "posterior_beta": beta_param,
            "mean": round(mean, 6),
            "mode": round(mode, 6),
            "variance": round(variance, 8),
            "std": round(std, 6),
            "ci_95": [round(ci_low, 4), round(ci_high, 4)],
            "successes": successes,
            "failures": failures,
        }

    @staticmethod
    def naive_bayes_classify(features: Dict[str, Any], classes: Dict[str, Dict]) -> Dict[str, Any]:
        """Naive Bayes classification."""
        scores = {}
        for class_name, class_data in classes.items():
            prior = class_data.get("prior", 1 / len(classes))
            log_prob = math.log(prior)
            for feat_name, feat_val in features.items():
                if feat_name in class_data.get("likelihoods", {}):
                    lk = class_data["likelihoods"][feat_name].get(str(feat_val), 0.01)
                    log_prob += math.log(max(lk, 1e-10))
            scores[class_name] = log_prob

        # Normalize to probabilities
        max_score = max(scores.values())
        exp_scores = {k: math.exp(v - max_score) for k, v in scores.items()}
        total = sum(exp_scores.values())
        probs = {k: round(v / total, 6) for k, v in exp_scores.items()}

        best_class = max(probs, key=probs.get)
        return {
            "prediction": best_class,
            "probabilities": probs,
            "confidence": round(probs[best_class], 4),
        }

    @staticmethod
    def monte_carlo_inference(
        prior_samples: int = 10000,
        prior_dist: str = "uniform",
        prior_params: Dict = None,
        likelihood_fn: str = "bernoulli",
        data: List = None,
    ) -> Dict[str, Any]:
        """Simple Monte Carlo inference via rejection sampling."""
        params = prior_params or {}
        data = data or []

        # Generate prior samples
        if prior_dist == "uniform":
            samples = [random.uniform(params.get("low", 0), params.get("high", 1)) for _ in range(prior_samples)]
        elif prior_dist == "normal":
            samples = [random.gauss(params.get("mean", 0), params.get("std", 1)) for _ in range(prior_samples)]
        elif prior_dist == "beta":
            samples = [random.betavariate(params.get("alpha", 2), params.get("beta", 2)) for _ in range(prior_samples)]
        else:
            samples = [random.random() for _ in range(prior_samples)]

        # Compute weights based on likelihood
        weights = []
        for theta in samples:
            w = 1.0
            for d in data:
                if likelihood_fn == "bernoulli":
                    p = max(min(theta, 0.999), 0.001)
                    w *= p if d == 1 else (1 - p)
                elif likelihood_fn == "normal":
                    w *= math.exp(-0.5 * ((d - theta) / params.get("data_std", 1))**2)
                else:
                    w *= 1.0
            weights.append(w)

        # Normalize
        total_w = sum(weights)
        if total_w == 0:
            return {"error": "All samples had zero likelihood"}

        weights = [w / total_w for w in weights]

        # Compute posterior statistics
        mean = sum(s * w for s, w in zip(samples, weights))
        var = sum(w * (s - mean)**2 for s, w in zip(samples, weights))

        return {
            "posterior_mean": round(mean, 6),
            "posterior_std": round(math.sqrt(var), 6),
            "effective_samples": round(1 / sum(w**2 for w in weights), 1),
            "num_data_points": len(data),
        }


engine = BayesianEngine()


@registry.tool(
    name="bayesian_infer",
    description="Bayesian inference: update beliefs, beta-binomial models, naive Bayes classification, Monte Carlo inference. For probabilistic reasoning and decision making.",
    category="Probabilistic Reasoning",
    parameters=[
        ToolParam("method", "string", "Method: update, sequential, beta_binomial, classify, monte_carlo"),
        ToolParam("params", "string", "JSON parameters for the method"),
    ],
)
def bayesian_infer(method: str, params: str):
    p = json.loads(params) if isinstance(params, str) else params

    if method == "update":
        return engine.bayes_update_full(
            prior=p.get("prior", 0.5),
            likelihood=p.get("likelihood", 0.8),
            likelihood_not=p.get("likelihood_not", 0.2),
        )

    elif method == "sequential":
        return engine.sequential_update(
            prior=p.get("prior", 0.5),
            observations=p.get("observations", []),
        )

    elif method == "beta_binomial":
        return engine.beta_binomial(
            successes=p.get("successes", 0),
            failures=p.get("failures", 0),
            prior_alpha=p.get("prior_alpha", 1),
            prior_beta=p.get("prior_beta", 1),
        )

    elif method == "classify":
        return engine.naive_bayes_classify(
            features=p.get("features", {}),
            classes=p.get("classes", {}),
        )

    elif method == "monte_carlo":
        return engine.monte_carlo_inference(
            prior_samples=p.get("samples", 10000),
            prior_dist=p.get("prior_dist", "uniform"),
            prior_params=p.get("prior_params", {}),
            likelihood_fn=p.get("likelihood", "bernoulli"),
            data=p.get("data", []),
        )

    return {"error": f"Unknown method: {method}", "available": ["update", "sequential", "beta_binomial", "classify", "monte_carlo"]}
