"""
Output Enforcer — Ensures LLM responses follow specific formats and JSON schemas.
"""
import json
import jsonschema
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("nexusmind.enforcer")

class OutputEnforcer:
    def __init__(self):
        pass

    def validate_json(self, text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate if text contains a valid JSON matching the schema."""
        try:
            # Extract JSON if it's wrapped in markers
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]
            
            data = json.loads(text)
            jsonschema.validate(instance=data, schema=schema)
            return {"success": True, "data": data}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}
        except jsonschema.ValidationError as e:
            return {"success": False, "error": f"Schema mismatch: {e.message}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def enforce_sections(self, text: str, required_sections: list) -> Dict[str, Any]:
        """Ensure specific sections (like <think>) are present."""
        missing = []
        for section in required_sections:
            if section not in text:
                missing.append(section)
        
        if missing:
            return {"success": False, "error": f"Missing required sections: {', '.join(missing)}"}
        return {"success": True}

enforcer = OutputEnforcer()
