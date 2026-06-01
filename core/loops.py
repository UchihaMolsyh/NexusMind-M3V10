"""
Logic Loops — Reflection, Re-answer, and Self-critique.
"""
import logging
from typing import Dict, Any, List, Optional
from core.llm import engine
from core.prompts import OUTPUT_FORMAT_ENFORCEMENT

logger = logging.getLogger("nexusmind.loops")

class LogicLoops:
    def __init__(self):
        pass

    async def reflect(self, question: str, answer: str) -> str:
        """Self-critique and reflection on the generated answer."""
        prompt = f"""
        Question: {question}
        Answer: {answer}
        
        Critique the answer above for accuracy, depth, and potential hallucinations. 
        If the answer is incorrect or incomplete, provide specific points for improvement.
        Otherwise, say 'CORRECT'.
        """
        critique = await engine.generate_simple(prompt, max_tokens=300)
        return critique

    async def re_answer(self, question: str, original_answer: str, critique: str) -> str:
        """Improve the answer based on reflection/critique."""
        if "CORRECT" in critique.upper() and len(critique) < 20:
            return original_answer

        prompt = f"""
        Question: {question}
        Original Answer: {original_answer}
        Critique: {critique}
        
        Based on the critique, provide a refined and more accurate version of the answer.
        {OUTPUT_FORMAT_ENFORCEMENT}
        """
        refined_answer = await engine.generate_simple(prompt, max_tokens=1024)
        return refined_answer

logic_loops = LogicLoops()
