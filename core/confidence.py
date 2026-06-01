"""
Confidence Scoring — convert LLM logprobs into a 0-10 confidence score.
"""
import math
from typing import List, Optional


def logprobs_to_confidence(logprobs: List[float]) -> float:
    """
    Convert a list of token log-probabilities to a 0-10 confidence score.
    Higher logprobs → higher confidence.
    """
    if not logprobs:
        return 5.0  # neutral if no logprobs available

    # Average log probability
    avg_logprob = sum(logprobs) / len(logprobs)

    # Convert log-prob to probability (0-1)
    # logprob is typically negative; closer to 0 = more confident
    avg_prob = math.exp(avg_logprob)

    # Scale to 0-10
    # avg_prob in [0, 1] → score in [0, 10]
    score = avg_prob * 10.0

    # Clamp to [0, 10]
    return max(0.0, min(10.0, round(score, 1)))


def confidence_label(score: float) -> str:
    """Return a human-readable confidence label."""
    from config import CONFIDENCE_UNSURE, CONFIDENCE_SURE

    if score < CONFIDENCE_UNSURE:
        return "I'm not sure about this"
    elif score >= CONFIDENCE_SURE:
        return "I'm pretty sure about this"
    else:
        return "I'm reasonably confident"


def confidence_emoji(score: float) -> str:
    """Return an emoji indicator for the confidence level."""
    if score < 3:
        return "🔴"
    elif score < 5:
        return "🟠"
    elif score < 8:
        return "🟡"
    else:
        return "🟢"


def format_confidence(score: float) -> str:
    """Format confidence as a complete display string."""
    emoji = confidence_emoji(score)
    label = confidence_label(score)
    return f"{emoji} Confidence: {score}/10 — {label}"


class ConfidenceTracker:
    """Track confidence scores across a conversation."""

    def __init__(self):
        self.scores: List[float] = []

    def add(self, logprobs: List[float]) -> float:
        score = logprobs_to_confidence(logprobs)
        self.scores.append(score)
        return score

    def average(self) -> float:
        if not self.scores:
            return 5.0
        return round(sum(self.scores) / len(self.scores), 1)

    def last(self) -> Optional[float]:
        return self.scores[-1] if self.scores else None

    def reset(self):
        self.scores.clear()
