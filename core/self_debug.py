"""
Self-Debugging Loop — catch errors, feed back to LLM, retry automatically.
"""
import logging
import traceback
from typing import Any, Dict, Optional, Callable

logger = logging.getLogger("nexusmind.debug")

MAX_RETRIES = 3


class SelfDebugger:
    """Catch tool/execution errors and retry with LLM-guided fixes."""

    def __init__(self, llm_engine=None):
        self.llm = llm_engine
        self.error_log = []

    async def run_with_retry(
        self,
        func: Callable,
        args: Dict[str, Any],
        tool_name: str,
        max_retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """Execute a function with automatic error recovery."""
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = func(**args)
                if hasattr(result, "__await__"):
                    result = await result

                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                }

            except Exception as e:
                last_error = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "attempt": attempt + 1,
                    "tool": tool_name,
                    "args": str(args)[:500],
                }
                self.error_log.append(last_error)
                logger.warning(
                    f"Tool '{tool_name}' failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )

                if attempt < max_retries and self.llm:
                    # Ask LLM to suggest a fix
                    fixed_args = await self._get_llm_fix(tool_name, args, last_error)
                    if fixed_args:
                        args = fixed_args
                        logger.info(f"LLM suggested fix, retrying with modified args")

        return {
            "success": False,
            "error": last_error["error"] if last_error else "Unknown error",
            "traceback": last_error["traceback"] if last_error else "",
            "attempts": max_retries + 1,
        }

    async def _get_llm_fix(
        self, tool_name: str, args: Dict, error: Dict
    ) -> Optional[Dict]:
        """Ask the LLM to suggest fixed arguments for a failed tool call."""
        if not self.llm or not self.llm.is_loaded:
            return None

        try:
            prompt = f"""A tool call failed. Suggest fixed arguments.

Tool: {tool_name}
Original args: {args}
Error: {error['error']}
Traceback: {error['traceback'][:500]}

Respond with ONLY the fixed arguments as a JSON object, nothing else.
If the error cannot be fixed by changing arguments, respond with "UNFIXABLE"."""

            response = await self.llm.generate_simple(prompt, max_tokens=256)

            if "UNFIXABLE" in response:
                return None

            import json
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith("{"):
                return json.loads(response)
        except Exception as e:
            logger.error(f"LLM fix suggestion failed: {e}")

        return None

    def get_error_summary(self) -> str:
        """Get a summary of all errors encountered."""
        if not self.error_log:
            return "No errors recorded."
        lines = [f"Total errors: {len(self.error_log)}\n"]
        for i, err in enumerate(self.error_log[-10:], 1):
            lines.append(f"{i}. [{err['tool']}] Attempt {err['attempt']}: {err['error']}")
        return "\n".join(lines)

    def clear_log(self):
        self.error_log.clear()
