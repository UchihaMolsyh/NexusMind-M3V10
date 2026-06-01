"""
Tool Permission Layer — Safety and validation for tool execution.
"""
import logging
from typing import Dict, Any, List, Optional
from config import TOOL_ALLOWLIST, REQUIRE_CONFIRMATION

logger = logging.getLogger("nexusmind.permissions")

class PermissionLayer:
    def __init__(self):
        self.allowlist = TOOL_ALLOWLIST
        self.require_confirm = REQUIRE_CONFIRMATION

    def validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if a tool can be executed."""
        # 1. Check allowlist
        if tool_name not in self.allowlist and tool_name not in self.require_confirm:
            return {"allowed": False, "reason": f"Tool '{tool_name}' is not in the allowlist."}

        # 2. Check for dangerous arguments in shell/python
        if tool_name == "shell_access":
            cmd = args.get("command", "").lower()
            dangerous = ["rm -rf", "format", "> /dev/", "mkfs"]
            for d in dangerous:
                if d in cmd:
                    return {"allowed": False, "reason": f"Dangerous command detected: {d}"}

        # 3. Check if confirmation is needed
        if tool_name in self.require_confirm:
            return {"allowed": True, "needs_confirmation": True}

        return {"allowed": True, "needs_confirmation": False}

permission_layer = PermissionLayer()
