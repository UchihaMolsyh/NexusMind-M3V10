"""
Evaluation Tools — BLEU, ROUGE, F1, benchmarking.
"""
import time
import logging
import math
from collections import Counter
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.eval")


def _tokenize(text: str) -> List[str]:
    """Simple whitespace + punctuation tokenizer."""
    import re
    return re.findall(r'\w+', text.lower())


def _ngrams(tokens: List[str], n: int) -> List[tuple]:
    """Generate n-grams from token list."""
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


@registry.tool(
    name="bleu_score",
    description="Calculate BLEU score between a reference and candidate text. Used for evaluating text generation quality.",
    category="Evaluation & Metrics",
    parameters=[
        ToolParam("reference", "string", "The reference (ground truth) text"),
        ToolParam("candidate", "string", "The candidate (generated) text"),
        ToolParam("max_n", "integer", "Maximum n-gram size (1-4)", required=False, default=4),
    ]
)
def bleu_score(reference: str, candidate: str, max_n: int = 4) -> Dict[str, Any]:
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)

    if not cand_tokens:
        return {"bleu": 0.0, "details": "Empty candidate"}

    # Brevity penalty
    bp = min(1.0, math.exp(1 - len(ref_tokens) / max(len(cand_tokens), 1)))

    # N-gram precisions
    precisions = []
    for n in range(1, min(max_n + 1, len(cand_tokens) + 1)):
        ref_ngrams = Counter(_ngrams(ref_tokens, n))
        cand_ngrams = Counter(_ngrams(cand_tokens, n))

        clipped = sum(min(count, ref_ngrams.get(ng, 0)) for ng, count in cand_ngrams.items())
        total = max(sum(cand_ngrams.values()), 1)
        precisions.append(clipped / total)

    if not precisions or any(p == 0 for p in precisions):
        return {"bleu": 0.0, "brevity_penalty": bp, "precisions": precisions}

    # Geometric mean of precisions
    log_avg = sum(math.log(p) for p in precisions) / len(precisions)
    bleu = bp * math.exp(log_avg)

    return {
        "bleu": round(bleu, 4),
        "brevity_penalty": round(bp, 4),
        "precisions": [round(p, 4) for p in precisions],
    }


@registry.tool(
    name="rouge_score",
    description="Calculate ROUGE-1, ROUGE-2, and ROUGE-L scores for text evaluation.",
    category="Evaluation & Metrics",
    parameters=[
        ToolParam("reference", "string", "The reference text"),
        ToolParam("candidate", "string", "The candidate text"),
    ]
)
def rouge_score(reference: str, candidate: str) -> Dict[str, Any]:
    ref_tokens = _tokenize(reference)
    cand_tokens = _tokenize(candidate)

    def f1_from_counts(matches, ref_len, cand_len):
        if ref_len == 0 or cand_len == 0:
            return {"precision": 0, "recall": 0, "f1": 0}
        precision = matches / max(cand_len, 1)
        recall = matches / max(ref_len, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-8)
        return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}

    # ROUGE-1 (unigram)
    ref_1 = Counter(ref_tokens)
    cand_1 = Counter(cand_tokens)
    matches_1 = sum(min(ref_1[w], cand_1[w]) for w in cand_1)
    rouge1 = f1_from_counts(matches_1, len(ref_tokens), len(cand_tokens))

    # ROUGE-2 (bigram)
    ref_2 = Counter(_ngrams(ref_tokens, 2))
    cand_2 = Counter(_ngrams(cand_tokens, 2))
    matches_2 = sum(min(ref_2[ng], cand_2[ng]) for ng in cand_2)
    rouge2 = f1_from_counts(matches_2, max(len(ref_tokens) - 1, 0), max(len(cand_tokens) - 1, 0))

    # ROUGE-L (Longest Common Subsequence)
    def lcs_length(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    lcs = lcs_length(ref_tokens, cand_tokens)
    rouge_l = f1_from_counts(lcs, len(ref_tokens), len(cand_tokens))

    return {
        "rouge_1": rouge1,
        "rouge_2": rouge2,
        "rouge_l": rouge_l,
    }


@registry.tool(
    name="f1_score",
    description="Calculate token-level F1 score between reference and candidate texts.",
    category="Evaluation & Metrics",
    parameters=[
        ToolParam("reference", "string", "The reference text"),
        ToolParam("candidate", "string", "The candidate text"),
    ]
)
def f1_score(reference: str, candidate: str) -> Dict[str, Any]:
    ref_tokens = set(_tokenize(reference))
    cand_tokens = set(_tokenize(candidate))

    if not ref_tokens or not cand_tokens:
        return {"f1": 0.0, "precision": 0.0, "recall": 0.0}

    common = ref_tokens & cand_tokens
    precision = len(common) / len(cand_tokens)
    recall = len(common) / len(ref_tokens)

    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "common_tokens": len(common),
    }


@registry.tool(
    name="benchmark_model",
    description="Run a speed and accuracy benchmark on the current LLM model.",
    category="Evaluation & Metrics",
    parameters=[
        ToolParam("num_prompts", "integer", "Number of test prompts to run", required=False, default=3),
    ]
)
def benchmark_model(num_prompts: int = 3) -> Dict[str, Any]:
    from core.llm import engine

    test_prompts = [
        "What is 2+2?",
        "Name three colors.",
        "What is the capital of France?",
        "Explain gravity in one sentence.",
        "What does CPU stand for?",
    ][:num_prompts]

    results = []
    total_tokens = 0
    total_time = 0

    for prompt in test_prompts:
        start = time.time()
        response = engine.generate_simple(prompt, max_tokens=64)
        elapsed = time.time() - start
        tokens = len(response.split())
        total_tokens += tokens
        total_time += elapsed

        results.append({
            "prompt": prompt,
            "response_length": tokens,
            "latency_s": round(elapsed, 3),
        })

    avg_latency = total_time / max(len(results), 1)
    tps = total_tokens / max(total_time, 0.001)

    return {
        "model_loaded": engine.is_loaded(),
        "num_prompts": len(results),
        "total_tokens": total_tokens,
        "total_time_s": round(total_time, 3),
        "avg_latency_s": round(avg_latency, 3),
        "tokens_per_second": round(tps, 2),
        "results": results,
    }
