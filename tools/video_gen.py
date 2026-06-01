"""
Video Generation — generate videos via HuggingFace free Inference API.
"""
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="video_generate",
    description="Generate short videos from text prompts using HuggingFace free Inference API.",
    category="Image & Video",
    parameters=[
        ToolParam("prompt", "string", "Text description of the video to generate"),
        ToolParam("output", "string", "Output file path", required=False, default=""),
        ToolParam("model", "string", "Model to use", required=False, default="ali-vilab/text-to-video-ms-1.7b"),
    ],
)
def video_generate(prompt: str, output: str = "", model: str = "ali-vilab/text-to-video-ms-1.7b"):
    from config import HF_API_URL, HF_API_KEY, UPLOADS_DIR

    api_url = f"{HF_API_URL}/{model}"

    headers = {}
    if HF_API_KEY:
        headers["Authorization"] = f"Bearer {HF_API_KEY}"

    try:
        resp = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=180)

        if resp.status_code == 503:
            wait_time = 30
            time.sleep(wait_time)
            resp = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=180)

        if resp.status_code != 200:
            return {
                "error": resp.text[:500],
                "status": resp.status_code,
                "tip": "Video generation may not be available on free tier. Set HF_API_KEY for better access.",
            }

        if not output:
            timestamp = int(time.time())
            output = str(UPLOADS_DIR / f"video_{timestamp}.mp4")

        out_path = Path(output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)

        return {
            "output": str(out_path),
            "model": model,
            "prompt": prompt,
            "size_bytes": len(resp.content),
        }

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Video generation can take a while."}
    except Exception as e:
        return {"error": str(e)}
