"""
Data Tools — Structured output enforcement (JSON, XML, YAML), schema validation, serialization.
"""
import json
import csv
import io
import logging
from typing import Dict, Any
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.data")


@registry.tool(
    name="enforce_json_schema",
    description="Validate and coerce text into valid JSON matching a given schema.",
    category="Data & Serialization",
    parameters=[
        ToolParam("text", "string", "The text/LLM output to validate as JSON"),
        ToolParam("schema", "string", "JSON schema to validate against (JSON string)", required=False, default="{}"),
    ]
)
def enforce_json_schema(text: str, schema: str = "{}") -> Dict[str, Any]:
    # Try to extract JSON from text
    import re
    json_match = re.search(r'\{[\s\S]*\}', text)
    if not json_match:
        json_match = re.search(r'\[[\s\S]*\]', text)

    if not json_match:
        return {"valid": False, "error": "No JSON found in text", "raw": text[:200]}

    try:
        parsed = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"Invalid JSON: {e}", "raw": json_match.group()[:200]}

    # Basic schema validation
    try:
        schema_obj = json.loads(schema) if isinstance(schema, str) else schema
    except json.JSONDecodeError:
        schema_obj = {}

    if schema_obj:
        # Check required fields
        required = schema_obj.get("required", [])
        missing = [f for f in required if f not in parsed]
        if missing:
            return {"valid": False, "error": f"Missing required fields: {missing}", "data": parsed}

    return {"valid": True, "data": parsed}


@registry.tool(
    name="enforce_xml",
    description="Convert structured data to well-formed XML.",
    category="Data & Serialization",
    parameters=[
        ToolParam("data", "string", "JSON string of data to convert to XML"),
        ToolParam("root_tag", "string", "Root XML element name", required=False, default="root"),
    ]
)
def enforce_xml(data: str, root_tag: str = "root") -> Dict[str, Any]:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON input"}

    def to_xml(obj, tag="item"):
        if isinstance(obj, dict):
            inner = "".join(f"<{k}>{to_xml(v, k)}</{k}>" for k, v in obj.items())
            return inner
        elif isinstance(obj, list):
            return "".join(f"<{tag}>{to_xml(item, tag)}</{tag}>" for item in obj)
        else:
            return str(obj)

    xml = f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<{root_tag}>{to_xml(obj)}</{root_tag}>"
    return {"xml": xml, "valid": True}


@registry.tool(
    name="enforce_yaml",
    description="Convert structured data to YAML format.",
    category="Data & Serialization",
    parameters=[
        ToolParam("data", "string", "JSON string of data to convert to YAML"),
    ]
)
def enforce_yaml(data: str) -> Dict[str, Any]:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON input"}

    def to_yaml(obj, indent=0):
        prefix = "  " * indent
        if isinstance(obj, dict):
            lines = []
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{prefix}{k}:")
                    lines.append(to_yaml(v, indent + 1))
                else:
                    lines.append(f"{prefix}{k}: {v}")
            return "\n".join(lines)
        elif isinstance(obj, list):
            lines = []
            for item in obj:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(to_yaml(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {item}")
            return "\n".join(lines)
        else:
            return f"{prefix}{obj}"

    yaml_str = to_yaml(obj)
    return {"yaml": yaml_str, "valid": True}


@registry.tool(
    name="serialize_data",
    description="Convert data between formats: JSON, XML, YAML, CSV.",
    category="Data & Serialization",
    parameters=[
        ToolParam("data", "string", "Input data as JSON string"),
        ToolParam("from_format", "string", "Source format (json)", required=False, default="json"),
        ToolParam("to_format", "string", "Target format: json, xml, yaml, csv"),
    ]
)
def serialize_data(data: str, from_format: str = "json", to_format: str = "json") -> Dict[str, Any]:
    try:
        obj = json.loads(data)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON input"}

    if to_format == "json":
        return {"result": json.dumps(obj, indent=2), "format": "json"}
    elif to_format == "xml":
        return enforce_xml(data)
    elif to_format == "yaml":
        return enforce_yaml(data)
    elif to_format == "csv":
        if isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=obj[0].keys())
            writer.writeheader()
            writer.writerows(obj)
            return {"result": output.getvalue(), "format": "csv"}
        return {"error": "CSV requires a list of objects"}

    return {"error": f"Unsupported format: {to_format}"}
