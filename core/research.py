"""
Research Mode — Deep research capability with multi-step tool synthesis.
"""
import logging
import asyncio
from typing import List, Dict, Any
from core.llm import engine
from core.tool_registry import registry

logger = logging.getLogger("nexusmind.research")


class ResearchMode:
    def __init__(self):
        self.max_steps = 3  # Reduced for performance; increase for deeper research

    async def perform_research(self, query: str, websocket=None) -> str:
        """Execute deep research by iteratively using tools and synthesizing results."""
        findings = []
        
        for step in range(self.max_steps):
            if websocket:
                await websocket.send_json({
                    "type": "status",
                    "content": f"🔍 Researching (Step {step + 1}/{self.max_steps})..."
                })
            
            # Step 1: Web search with refined queries
            search_query = query if step == 0 else f"{query} {' '.join(findings[-1:][:50])}"
            search_result = await registry.execute("web_search", {"query": search_query})
            
            if search_result.get("success") and search_result.get("result"):
                result_data = search_result["result"]
                if isinstance(result_data, dict) and result_data.get("results"):
                    for r in result_data["results"]:
                        findings.append(f"- {r.get('title', '')}: {r.get('snippet', '')}")
            
            # Check if we have enough information to synthesize
            if len(findings) >= 5:
                break
        
        # If no findings, return a note
        if not findings:
            return "I couldn't find specific research results. Please try rephrasing your query or check your internet connection."
        
        # Final synthesis using LLM
        if websocket:
            await websocket.send_json({"type": "status", "content": "📝 Synthesizing research report..."})
        
        findings_text = "\n".join(findings[:20])  # Cap at 20 findings
        final_prompt = (
            f"Based on the following research findings, write a comprehensive, well-structured report "
            f"answering: {query}\n\nFindings:\n{findings_text}\n\n"
            f"Write a clear, organized report with sections. Use **bold** for key points."
        )
        report = await engine.generate_simple(final_prompt, max_tokens=2048)
        return report

research_mode = ResearchMode()
