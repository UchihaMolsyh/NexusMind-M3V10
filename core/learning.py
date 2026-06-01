"""
Self-Learning Engine — Extracts patterns, learns from conversations, and self-modifies with permission.
"""
import json
import logging
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path
from core.llm import engine
from core.memory import MemorySystem
from core.tool_registry import registry

logger = logging.getLogger("nexusmind.learning")

class LearningEngine:
    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self.learning_db = Path("data/learning_patterns.json")
        self.learning_db.parent.mkdir(exist_ok=True)
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict:
        """Load existing learning patterns."""
        if self.learning_db.exists():
            try:
                with open(self.learning_db, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load learning patterns: {e}")
        return {
            "conversation_patterns": {},
            "code_patterns": {},
            "tool_usage": {},
            "knowledge_domains": {}
        }
    
    def _save_patterns(self):
        """Save learning patterns to disk."""
        try:
            with open(self.learning_db, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save learning patterns: {e}")
    
    async def extract_knowledge(self, text: str) -> Dict[str, Any]:
        """Extract and analyze knowledge from input text."""
        analysis_prompt = f"""
        Analyze the following text and extract:
        1. Key concepts and relationships
        2. Problem-solving patterns
        3. Code structures or algorithms
        4. Domain-specific knowledge
        5. Actionable insights
        
        Text: {text}
        
        Return as structured JSON:
        {{
            "concepts": [...],
            "patterns": [...],
            "code_snippets": [...],
            "domain": "...",
            "insights": [...]
        }}
        """
        
        try:
            result = await engine.generate_simple(analysis_prompt, max_tokens=1024)
            # Parse the JSON response
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # Fallback if not valid JSON
                return {
                    "concepts": [],
                    "patterns": [],
                    "code_snippets": [],
                    "domain": "general",
                    "insights": [result[:200]]  # Truncate if too long
                }
        except Exception as e:
            logger.error(f"Knowledge extraction failed: {e}")
            return {"error": str(e)}
    
    def integrate_pattern(self, pattern_type: str, pattern_data: Dict):
        """Integrate learned pattern into the knowledge base."""
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = {}
        
        # Create a unique key for the pattern
        pattern_key = hashlib.md5(
            json.dumps(pattern_data, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        self.patterns[pattern_type][pattern_key] = {
            "data": pattern_data,
            "timestamp": asyncio.get_event_loop().time(),
            "usage_count": 0
        }
        
        self._save_patterns()
        logger.info(f"Integrated {pattern_type} pattern: {pattern_key}")
    
    async def learn_from_conversation(self, user_input: str, ai_response: str):
        """Learn patterns from conversation interactions."""
        learning_prompt = f"""
        Analyze this conversation exchange and extract learning patterns:
        
        User: {user_input}
        AI: {ai_response}
        
        Focus on:
        1. Question types and effective response patterns
        2. Problem-solving approaches
        3. Tool usage patterns
        4. Knowledge domains
        
        Return JSON with patterns that could improve future responses.
        """
        
        try:
            patterns = await engine.extract_knowledge(learning_prompt)
            if patterns and "patterns" in patterns:
                for pattern in patterns["patterns"]:
                    self.integrate_pattern("conversation_patterns", {
                        "pattern": pattern,
                        "context": user_input[:100]
                    })
        except Exception as e:
            logger.error(f"Conversation learning failed: {e}")
    
    def get_relevant_patterns(self, context: str, limit: int = 5) -> List[Dict]:
        """Retrieve patterns relevant to current context."""
        relevant = []
        context_lower = context.lower()
        
        for pattern_type, patterns in self.patterns.items():
            for pattern_id, pattern_data in patterns.items():
                # Simple relevance check - can be enhanced with embeddings
                pattern_text = str(pattern_data.get("data", {})).lower()
                if any(word in pattern_text for word in context_lower.split()[:5]):
                    relevant.append({
                        "type": pattern_type,
                        "id": pattern_id,
                        "data": pattern_data["data"]
                    })
                    if len(relevant) >= limit:
                        break
        
        return relevant
    
    async def self_modify_request(self, modification_plan: Dict) -> Dict:
        """Process a self-modification request with safety checks."""
        # This is a simplified version - in production, would need extensive safety checks
        safety_prompt = f"""
        Review this self-modification plan for safety and feasibility:
        
        {json.dumps(modification_plan, indent=2)}
        
        Assess:
        1. Is this modification safe?
        2. Will it improve functionality?
        3. Are there any risks?
        
        Return JSON with: {{"safe": true/false, "risks": [...], "recommendation": "..."}}
        """
        
        try:
            safety_check = await engine.generate_simple(safety_prompt, max_tokens=500)
            return {"safety_analysis": safety_check, "status": "pending_approval"}
        except Exception as e:
            return {"error": str(e), "status": "failed"}

# Initialize learning engine
def create_learning_engine(memory: MemorySystem) -> LearningEngine:
    return LearningEngine(memory)
