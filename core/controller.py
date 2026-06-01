"""
Controller — Orchestrates LLM, tools, and memory.
"""
import time
import logging
import asyncio
from typing import Dict, Any, List, Optional
from core.llm import engine
from core.router import router
from core.memory import MemorySystem
from core.tool_registry import registry, parse_tool_calls
from core.loops import logic_loops
from core.permissions import permission_layer
from core.enforcer import enforcer
from core.research import research_mode
from core.learning import create_learning_engine
from core.self_mod import create_self_mod_engine
from core.prompts import SYSTEM_TEMPLATE, TASK_TEMPLATE
from core.monitor import monitor
from core.optimizer import optimizer

logger = logging.getLogger("nexusmind.controller")

# Toggle for reflection loop (set False for faster responses)
ENABLE_REFLECTION = False


class Controller:
    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self.learning_engine = create_learning_engine(memory)
        self.self_mod_engine = create_self_mod_engine(memory)

    async def handle_request(self, session_id: str, user_input: str, websocket=None):
        """Main entry point for handling a user request with reflection and tool validation."""
        start_time = time.time()
        token_count = 0
        # Manual profile override commands
        profile_force = None
        if user_input.startswith("!think "):
            user_input = user_input[7:]
            profile_force = "THINKING"
        elif user_input.startswith("!fast "):
            user_input = user_input[6:]
            profile_force = "CHAT"
        
        # 1. Check for /LEARN command
        if user_input.startswith("/LEARN:"):
            learn_content = user_input[7:].strip()
            return await self._handle_learn_command(learn_content, websocket)
        
        # 2. Check for self-modification request
        if user_input.startswith("/MODIFY:"):
            mod_request = user_input[8:].strip()
            return await self._handle_modify_request(mod_request, websocket)
        
        # 3. Check for approval/cancel commands
        if user_input.startswith("/APPROVE:"):
            mod_id = user_input[9:].strip()
            return await self._handle_approve_modification(mod_id, websocket)
        
        if user_input.startswith("/CANCEL:"):
            mod_id = user_input[8:].strip()
            return await self._handle_cancel_modification(mod_id, websocket)
        
        # 4. Check for GitHub integration
        if user_input.startswith("/INTEGRATE:"):
            repo_url = user_input[11:].strip()
            return await self._handle_github_integration(repo_url, websocket)
        
        # 5. Routing (fast keyword-based)
        profile = await router.route(user_input, self.memory.get_history(5))
        logger.info(f"Routed request to profile: {profile}")
        
        # 5. Memory Retrieval (Context)
        self.memory.add_message("user", user_input)
        context = self.memory.get_context_string(user_input)
    
        
        # 6. Research Mode (if needed)
        is_research = "research" in user_input.lower() or profile == "RESEARCH"
        if is_research:
            full_response = await research_mode.perform_research(user_input, websocket)
        else:
            # 7. Build Structured Prompt
            from config import PROFILE_SYSTEM_PROMPTS
            system_rules = PROFILE_SYSTEM_PROMPTS.get(profile, PROFILE_SYSTEM_PROMPTS["CHAT"])
            
            system_p = SYSTEM_TEMPLATE.format(
                role_description="NexusMind AI Assistant",
                system_rules=system_rules,
                tool_definitions=registry.tools_prompt(),
                memory_context=context
            )
            
            # Trim history to fit context — start with 10, reduce if needed
            from config import CONTEXT_LENGTH, MAX_TOKENS
            history_limit = 10
            while history_limit >= 0:
                messages = engine.build_messages(
                    user_input,
                    self.memory.get_history(history_limit),
                    system_p
                )
                # Estimate token count (~4 chars per token)
                prompt_chars = sum(len(m.get("content", "")) for m in messages)
                estimated_prompt_tokens = prompt_chars // 3  # conservative estimate
                available_tokens = CONTEXT_LENGTH - estimated_prompt_tokens - 64
                if available_tokens >= 128:
                    break
                history_limit -= 2
            
            # Cap max_tokens to what's actually available
            effective_max_tokens = max(128, min(MAX_TOKENS, available_tokens))
            
            # 7. Generate Initial Response
            full_response = ""
            
            def get_stream():
                return engine.generate(
                    messages=messages,
                    max_tokens=effective_max_tokens,
                    profile_override=profile_force or profile,
                    stream=True
                )
            
            # Since engine.generate returns a synchronus generator, we can't just await it with to_thread and iterate over it directly in the async loop without blocking or buffering.
            # Instead we iterate over the synchronous generator in a thread that sends messages back to the async loop via a queue.
            
            queue = asyncio.Queue()
            
            def consume_stream(q, loop):
                try:
                    for chunk in get_stream():
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            asyncio.run_coroutine_threadsafe(q.put(delta), loop)
                except Exception as e:
                    logger.error(f"Stream consumption error: {e}")
                finally:
                    asyncio.run_coroutine_threadsafe(q.put(None), loop) # EOF marker
            
            loop = asyncio.get_running_loop()
            await asyncio.to_thread(consume_stream, queue, loop)
            
            while True:
                delta = await queue.get()
                if delta is None: # EOF
                    break
                full_response += delta
                token_count += len(delta.split()) or 1
                if websocket:
                    try:
                        await websocket.send_json({"type": "chunk", "content": delta})
                    except Exception as e:
                        logger.error(f"Failed to send chunk: {e}")
                        break
            
            # 8. Tool Check & Validation
            tool_calls = parse_tool_calls(full_response)
            if tool_calls:
                for tc in tool_calls:
                    val = permission_layer.validate_tool_call(tc["tool"], tc["args"])
                    if not val["allowed"]:
                        full_response += f"\n\n[Permission Denied: {val['reason']}]"
                    elif val.get("needs_confirmation"):
                        if websocket:
                            await websocket.send_json({"type": "confirmation_required", "tool": tc["tool"], "args": tc["args"]})
                    else:
                        if websocket:
                            await websocket.send_json({"type": "chunk", "content": f"\n\n*(Executing tool `{tc['tool']}`...)*\n\n"})
                        result = await registry.execute(tc["tool"], tc["args"])
                        full_response += f"\n\n[Tool Result: {result}]"
                        if websocket:
                            await websocket.send_json({"type": "chunk", "content": f"*(Tool finished)*\n\n"})

        # 9. Reflection Loop (optional, configurable)
        if ENABLE_REFLECTION:
            try:
                critique = await logic_loops.reflect(user_input, full_response)
                if "CORRECT" not in critique.upper():
                    full_response = await logic_loops.re_answer(user_input, full_response, critique)
                    
                    final_critique = await logic_loops.reflect(user_input, full_response)
                    if "CORRECT" not in final_critique.upper():
                        full_response += "\n\n[Warning: Answer may require additional verification.]"
            except Exception as e:
                logger.error(f"Reflection loop error: {e}")
        
        # 10. Output Format Enforcement
        enforcement = enforcer.enforce_sections(full_response, ["<think>", "</think>"])
        if not enforcement["success"]:
            logger.debug(f"Response missing think sections (normal for simple responses)")
        # Add low confidence warning if needed
        from config import CONFIDENCE_UNSURE
        if token_count > 0:
            rough_confidence = min(10.0, (token_count / max(1, len(user_input.split()))) * 3)
            if rough_confidence < CONFIDENCE_UNSURE:
                full_response += "\n\n*(low confidence on this — worth double checking)*"
        latency = time.time() - start_time
        tps = round(token_count / latency, 2) if latency > 0 else 0
        
        # 11. Learning from conversation
        self.memory.add_message("assistant", full_response)
        self.memory.store_long_term("assistant", full_response, importance=0.8)
        await self.learning_engine.learn_from_conversation(user_input, full_response)
        
        # 12. Performance Optimization
        perf_report = optimizer.get_optimization_report()
        if perf_report["performance_analysis"]["status"] != "optimal":
            logger.info(f"Performance issues detected: {perf_report['performance_analysis']['issues']}")
        
        # 13. Monitor & Logging
        monitor.log_interaction(tokens=token_count, latency=latency)
        
        # 14. Update Memory (single insertion point — no duplication)
        self.memory.store_long_term("assistant", full_response, importance=0.8)
        
        return {
            "content": full_response,
            "profile": profile,
            "gen_time": round(latency, 2),
            "tps": tps,
            "tokens": token_count,
        }

    async def _handle_learn_command(self, learn_content: str, websocket=None):
        """Handle /LEARN command to extract and integrate knowledge."""
        if websocket:
            await websocket.send_json({"type": "status", "content": "🧠 Extracting knowledge..."})
        
        # Extract knowledge from the content
        knowledge = await self.learning_engine.extract_knowledge(learn_content)
        
        if "error" in knowledge:
            response = f"❌ Error extracting knowledge: {knowledge['error']}"
        else:
            # Integrate patterns
            if knowledge.get("patterns"):
                for pattern in knowledge["patterns"]:
                    self.learning_engine.integrate_pattern("user_patterns", {
                        "pattern": pattern,
                        "source": learn_content[:100]
                    })
            
            # Store in memory
            self.memory.store_long_term(
                "user",
                f"Learned: {learn_content}",
                tags="learning",
                category="preference"
            )
            
            # Format response
            response = "✅ **Knowledge Integrated**\n\n"
            
            if knowledge.get("concepts"):
                response += f"📚 **Concepts**: {', '.join(knowledge['concepts'][:3])}\n\n"
            
            if knowledge.get("domain"):
                response += f"🏷️ **Domain**: {knowledge['domain']}\n\n"
            
            if knowledge.get("insights"):
                response += f"💡 **Insights**: {knowledge['insights'][0] if knowledge['insights'] else 'None'}\n\n"
            
            response += "I've integrated this knowledge into my pattern database."
        
        return {
            "content": response,
            "profile": "LEARNING",
            "gen_time": 0.1,
            "tps": 0,
            "tokens": 0
        }

    async def _handle_modify_request(self, mod_request: str, websocket=None):
        """Handle /MODIFY command for self-modification with permission."""
        if websocket:
            await websocket.send_json({"type": "status", "content": "🔧 Analyzing modification request..."})
        
        # Analyze the modification request
        analysis = await self.self_mod_engine.analyze_modification_request(mod_request)
        
        if "error" in analysis:
            response = f"❌ Error analyzing modification: {analysis['error']}"
        else:
            # Create a modification ID and store it
            import uuid
            mod_id = str(uuid.uuid4())[:8]
            self.self_mod_engine.pending_modifications[mod_id] = analysis
            
            response = f"⚠️ **Modification Request Analyzed**\n\n"
            response += f"**ID**: `{mod_id}`\n\n"
            response += f"**Files to modify**: {len(analysis.get('target_files', []))}\n\n"
            response += f"**Changes**: {len(analysis.get('changes', []))}\n\n"
            
            if analysis.get('risks'):
                response += f"⚠️ **Risks**: {', '.join(analysis['risks'][:2])}\n\n"
            
            response += "\nTo proceed, use: `/APPROVE:{mod_id}`\n"
            response += "To cancel, use: `/CANCEL:{mod_id}`"
        
        return {
            "content": response,
            "profile": "SELF_MOD",
            "gen_time": 0.2,
            "tps": 0,
            "tokens": 0
        }

    async def _handle_approve_modification(self, mod_id: str, websocket=None):
        """Handle approval of a self-modification request."""
        if websocket:
            await websocket.send_json({"type": "status", "content": "🔧 Applying modification..."})
        
        result = await self.self_mod_engine.implement_modification(mod_id, user_approved=True)
        
        if result["status"] == "completed":
            response = "✅ **Modification Applied Successfully**\n\n"
            response += f"**Files modified**: {len(result.get('results', []))}\n\n"
            
            for res in result.get('results', []):
                status_icon = "✅" if res['status'] == 'success' else "❌"
                response += f"{status_icon} {res['file']}: {res.get('change', 'N/A')}\n"
            
            if result.get('backups'):
                response += "\n📦 Backups created for rollback\n"
        else:
            response = f"❌ Modification failed: {result.get('error', 'Unknown error')}"
        
        return {
            "content": response,
            "profile": "SELF_MOD",
            "gen_time": 0.5,
            "tps": 0,
            "tokens": 0
        }
    
    async def _handle_cancel_modification(self, mod_id: str, websocket=None):
        """Handle cancellation of a self-modification request."""
        if mod_id in self.self_mod_engine.pending_modifications:
            del self.self_mod_engine.pending_modifications[mod_id]
            response = f"✅ Modification `{mod_id}` cancelled."
        else:
            response = f"❌ Modification `{mod_id}` not found."
        
        return {
            "content": response,
            "profile": "SELF_MOD",
            "gen_time": 0.1,
            "tps": 0,
            "tokens": 0
        }
    
    async def _handle_github_integration(self, repo_url: str, websocket=None):
        """Handle GitHub repository integration."""
        if websocket:
            await websocket.send_json({"type": "status", "content": "📦 Integrating repository..."})
        
        result = self.self_mod_engine.integrate_github_repo(repo_url)
        
        if result["status"] == "recorded":
            integration = result["integration"]
            response = "✅ **Repository Integration Recorded**\n\n"
            response += f"📚 **Name**: {integration['repo_info']['name']}\n"
            response += f"⭐ **Stars**: {integration['repo_info']['stars']}\n"
            response += f"💻 **Language**: {integration['repo_info']['language']}\n"
            response += f"📝 **Description**: {integration['repo_info']['description'][:100]}...\n\n"
            response += "Repository information has been stored. Full code integration to be implemented."
        else:
            response = f"❌ Integration failed: {result.get('error', 'Unknown error')}"
        
        return {
            "content": response,
            "profile": "INTEGRATION",
            "gen_time": 0.3,
            "tps": 0,
            "tokens": 0
        }

# Initialized in server.py
