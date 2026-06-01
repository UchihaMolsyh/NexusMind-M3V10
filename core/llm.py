"""
LLM Engine — Qwen3 with speculative decoding via llama-cpp-python.
"""
import os
import sys
import logging
import asyncio
from pathlib import Path
from typing import Optional, Generator, Dict, Any, List, Union

logger = logging.getLogger("nexusmind.llm")


class LLMEngine:
    """Manages multi-model caching for instant switching and background pre-loading."""

    def __init__(self):
        self._model_cache: Dict[str, Dict[str, Any]] = {}  # {profile_id: {"target": Llama, "draft": Llama}}
        self.active_profile: Optional[str] = None
        self._loading_lock = asyncio.Lock()
        self._loaded_order: List[str] = []

    def load(self, profile_id: Optional[str] = None):
        """Load a specific profile into the cache."""
        from config import MODEL_PROFILE, MODEL_PROFILES, MODELS_DIR, CONTEXT_LENGTH, N_THREADS, N_GPU_LAYERS, ENABLE_SPECULATIVE_DECODING, MAX_LOADED_MODELS
        from llama_cpp import Llama

        pid = profile_id or MODEL_PROFILE
        if pid in self._model_cache:
            return self._model_cache[pid]

        profile = MODEL_PROFILES.get(pid)
        if not profile:
            logger.error(f"Profile {pid} not found.")
            return None

        # Manage cache size
        while len(self._model_cache) >= MAX_LOADED_MODELS:
            oldest = self._loaded_order.pop(0)
            if oldest in self._model_cache:
                logger.info(f"Evicting model {oldest} from cache to free memory.")
                del self._model_cache[oldest]

        target_path = MODELS_DIR / profile["file"]
        if not target_path.exists():
            logger.error(f"Model file not found: {target_path}")
            return None

        logger.info(f"🚀 Loading profile: {profile['name']} ({pid})...")
        
        # Load draft if enabled
        draft_model = None
        if ENABLE_SPECULATIVE_DECODING:
            for draft_cfg in profile.get("drafts", []):
                d_path = MODELS_DIR / draft_cfg["file"]
                if d_path.exists():
                    try:
                        draft_model = Llama(
                            model_path=str(d_path),
                            n_ctx=CONTEXT_LENGTH,
                            n_threads=N_THREADS,
                            n_gpu_layers=N_GPU_LAYERS,
                            verbose=False,
                        )
                        break
                    except Exception as e:
                        logger.warning(f"Draft fallback failed: {e}")
                        # Clean up if partially loaded
                        try:
                            if 'draft_model' in locals() and draft_model:
                                draft_model.close()
                        except:
                            pass
                        draft_model = None

        # Load target
        target_kwargs: Dict[str, Any] = dict(
            model_path=str(target_path),
            n_ctx=CONTEXT_LENGTH,
            n_threads=profile.get("threads", N_THREADS),
            n_gpu_layers=N_GPU_LAYERS,
            n_batch=512,
            use_mlock=True,
            use_mmap=True,
            logits_all=True,
            verbose=False,
        )
        if draft_model:
            target_kwargs["draft_model"] = draft_model  # type: ignore

        try:
            target_model = Llama(**target_kwargs)  # type: ignore
            self._model_cache[pid] = {"target": target_model, "draft": draft_model}
            self._loaded_order.append(pid)
            if not self.active_profile:
                self.active_profile = pid
            logger.info(f"✅ Profile {pid} loaded successfully.")
            return self._model_cache[pid]
        except Exception as e:
            logger.error(f"Failed to load model {pid}: {e}")
            # Clean up draft model if it exists
            if draft_model:
                try:
                    draft_model.close()
                except:
                    pass
            return None

    async def preload_all(self):
        """Background task to preload all profiles (up to MAX_LOADED_MODELS)."""
        from config import MODEL_PROFILES, MAX_LOADED_MODELS, PRELOAD_ALL_MODELS
        if not PRELOAD_ALL_MODELS:
            return

        logger.info("🔭 Starting background model preloading...")
        # Sort profiles: current first, then by size or name
        from config import MODEL_PROFILE
        priority = [MODEL_PROFILE] + [p for p in MODEL_PROFILES.keys() if p != MODEL_PROFILE]
        
        for pid in priority[:MAX_LOADED_MODELS]:
            await asyncio.to_thread(self.load, pid)
            await asyncio.sleep(0.5) # Cooperate with other startup tasks
        
        logger.info("✅ Preloading complete.")

    def _inject_thinking_control(self, messages, profile):
        """Inject thinking budget controls into messages."""
        from config import THINKING_BUDGET
        budget = THINKING_BUDGET.get(profile, 0)
        messages = list(messages)

        if budget == 0:
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    messages[i] = {
                        "role": "system",
                        "content": msg["content"] + "\n\nCRITICAL INSTRUCTION: DO NOT think. Answer directly without any thinking process or <think> tags. Provide your final answer immediately."
                    }
                    return messages
            return [{"role": "system", "content": "CRITICAL INSTRUCTION: DO NOT think. Answer directly without any thinking process or <think> tags."}] + messages
        else:
            for i, msg in enumerate(messages):
                if msg["role"] == "system":
                    messages[i] = {
                        "role": "system",
                        "content": msg["content"] + (
                            f"\n\nKeep your <think> section under {budget} tokens. "
                            f"Stop thinking when you have enough to answer."
                        )
                    }
                    return messages
            return messages

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False,
        profile_override: Optional[str] = None
    ):
        """Generate response handling caching and fallbacks."""
        from config import MODEL_PROFILE
        pid = profile_override or self.active_profile or MODEL_PROFILE
        
        model_data = self._model_cache.get(pid)
        if not model_data:
            model_data = self.load(pid)
        
        if not model_data:
            # Fallback to CHAT profile if requested profile fails
            if pid != "CHAT":
                logger.warning(f"Falling back to CHAT profile due to {pid} load failure")
                model_data = self.load("CHAT")
                if not model_data:
                    raise RuntimeError(f"Could not load model profile {pid} or fallback CHAT")
            else:
                raise RuntimeError(f"Could not load model profile {pid}")
        messages = self._inject_thinking_control(messages, pid)
        target = model_data["target"]
        kwargs = dict(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=stream,
            repeat_penalty=1.1,
        )

        if stream:
            return self._stream_with_fallback(target, kwargs, pid)
        else:
            try:
                return target.create_chat_completion(**kwargs)
            except ValueError as e:
                if "could not be broadcast together" in str(e):
                    self._reload_without_drafts(pid)
                    # Get fresh target after reload
                    target = self._model_cache[pid]["target"]
                    return target.create_chat_completion(**kwargs)
                raise

    def _stream_with_fallback(self, target, kwargs, pid):
        """Stream handles speculative decoding fallbacks."""
        try:
            for chunk in target.create_chat_completion(**kwargs):
                yield chunk
        except ValueError as e:
            if "could not be broadcast together" in str(e) or "speculative" in str(e).lower():
                logger.warning(f"Speculative mismatch in {pid}, reloading without drafts...")
                self._reload_without_drafts(pid)
                new_target = self._model_cache[pid]["target"]
                
                # Yield a friendly notice chunk to the frontend so it doesn't look like a random duplicate
                notice = "\\n\\n*[Speculative Decoding Fallback — Restarting]*\\n\\n"
                yield {"choices": [{"delta": {"content": notice}}]}
                
                for chunk in new_target.create_chat_completion(**kwargs):
                    yield chunk
            else:
                logger.error(f"Stream error in {pid}: {e}")
                yield {"choices": [{"delta": {"content": f"\\n\\n*[Generation Error: {str(e)}]*"}}]}

    def _reload_without_drafts(self, pid: str):
        """Emergency reload of a specific profile without drafts."""
        if pid in self._model_cache:
            del self._model_cache[pid]
            if pid in self._loaded_order:
                self._loaded_order.remove(pid)
        
        # Override config temporarily to disable draft for this load
        from config import ENABLE_SPECULATIVE_DECODING
        import config
        old_val = config.ENABLE_SPECULATIVE_DECODING
        config.ENABLE_SPECULATIVE_DECODING = False
        self.load(pid)
        config.ENABLE_SPECULATIVE_DECODING = old_val

    def switch_to_profile(self, profile_id: str):
        """Switch active profile instantly if cached, else load."""
        import config
        if profile_id not in config.MODEL_PROFILES:
            return
        
        logger.info(f"Switching to profile: {profile_id}")
        config.MODEL_PROFILE = profile_id
        self.active_profile = profile_id
        
        if profile_id not in self._model_cache:
            self.load(profile_id)

    def generate_simple(self, prompt: str, max_tokens: int = 512) -> str:
        """Simple completion for titles/tool logic."""
        profile_id = self.active_profile or "CHAT"
        model_data = self._model_cache.get(profile_id)
        if not model_data:
            model_data = self.load(profile_id)
        
        if not model_data:
            raise RuntimeError(f"Failed to load model profile {profile_id}")
        
        target = model_data["target"]
        messages = [{"role": "user", "content": prompt}]
        result = target.create_chat_completion(messages=messages, max_tokens=max_tokens)
        return str(result["choices"][0]["message"]["content"] or "")

    def unload(self):
        """Clear entire cache."""
        self._model_cache.clear()
        self._loaded_order.clear()
        self.active_profile = None
        logger.info("All models evicted from cache.")

    @property
    def is_loaded(self) -> bool:
        return self.active_profile in self._model_cache

    # Rest of the helper methods...
    def get_logprobs(self, completion: Dict) -> List[float]:
        logprobs = []
        try:
            choice = completion["choices"][0]
            if "logprobs" in choice and choice["logprobs"]:
                content_logprobs = choice["logprobs"].get("content", [])
                for token_info in content_logprobs:
                    if "logprob" in token_info:
                        logprobs.append(token_info["logprob"])
        except:
            pass
        return logprobs

    def build_messages(self, user_message, conversation_history, system_prompt, tool_results=None, memory_context=None):
        messages = [{"role": "system", "content": system_prompt}]
        if memory_context:
            messages.append({"role": "system", "content": f"Context:\n{memory_context}"})
        for msg in conversation_history:
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        if tool_results:
            for tr in tool_results:
                messages.append({"role": "assistant", "content": f"Result ({tr['tool']}): {tr.get('result', 'Error')}"})
        return messages

    

# Global engine instance
engine = LLMEngine()
