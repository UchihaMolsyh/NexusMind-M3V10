"""
Router — Fast keyword-based routing (no LLM call overhead).
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("nexusmind.router")

# Keyword patterns for each profile (checked in priority order)
ROUTE_PATTERNS = {
    "CODER": re.compile(
        r"\b(write\s+(code|script|function|class)|debug|compile|syntax|python|javascript|"
        r"html|css|java|rust|golang|api|endpoint|refactor|bug|error|traceback|exception|"
        r"algorithm|data\s*structure|regex|import\s+module|git\s+repo)\b",
        re.IGNORECASE
    ),
    "MATH": re.compile(
        r"\b(calculate|solve\s+equation|formula|integral|derivative|matrix\s+calc|algebra|"
        r"geometry|trigonometry|calculus|factorial|logarithm|"
        r"exponent|sqrt\b|root\s+of|graph\s+function|polynomial|fraction\b|"
        r"\d+\s*[\+\-\*\/\^]\s*\d+\s*[=\?]?)\b",
        re.IGNORECASE
    ),
    "THINKING": re.compile(
        r"\b(deep\s+reason|analyze\s+logic|philosophical\s+debate|pros\s+and\s+cons|"
        r"critique\s+argument|hypothesis|chain.of.thought|tree.of.thought|"
        r"step\s+by\s+step\s+reasoning|deep\s+dive|complex\s+analysis)\b",
        re.IGNORECASE
    ),
    "SEARCH": re.compile(
        r"\b(search\s+for|look\s+up\s+on\s+internet|google\s+search|latest\s+news|"
        r"browse\s+web|wikipedia\s+search|wiki\s+lookup|scrape\s+site|crawl\s+url)\b",
        re.IGNORECASE
    ),
    "RESEARCH": re.compile(
        r"\b(research\s+paper|rag\s+system|knowledge\s+graph\s+query|"
        r"vector\s+database|semantic\s+search\s+engine|knowledge\s+base\s+lookup)\b",
        re.IGNORECASE
    ),
    "REASONING": re.compile(
        r"\b(logic\s+puzzle|deductive\s+reasoning|syllogism|logical\s+fallacy|"
        r"premise\s+and\s+conclusion|formal\s+proof|theorem\s+verification)\b",
        re.IGNORECASE
    ),
}


class Router:
    def __init__(self):
        self.routes = {
            "CHAT": "chat_controller",
            "CODER": "code_controller",
            "MATH": "math_controller",
            "THINKING": "reasoning_controller",
            "SEARCH": "search_controller",
            "RESEARCH": "research_controller",
            "REASONING": "logic_controller"
        }

    async def route(self, user_input: str, history: List[Dict]) -> str:
        """Fast keyword-based routing — no LLM overhead."""
        # Score each profile by number of keyword matches
        best_profile = "CHAT"
        best_score = 0
        
        for profile, pattern in ROUTE_PATTERNS.items():
            matches = pattern.findall(user_input)
            score = len(matches)
            if score > best_score:
                best_score = score
                best_profile = profile
        
        if best_score > 0:
            logger.info(f"Routed to {best_profile} (score: {best_score})")
        
        return best_profile

router = Router()
