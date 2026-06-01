"""
Image Generation — generate images via HuggingFace free Inference API.
Note: Free tier is slow. For faster generation, set HF_API_KEY with your personal key.
"""
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


HF_MODELS = {
    "sd-turbo": "stabilityai/sd-turbo",
    "sdxl-turbo": "stabilityai/sdxl-turbo",
    "flux-schnell": "black-forest-labs/FLUX.1-schnell",
    "default": "stabilityai/sd-turbo",
}


@registry.tool(
    name="image_generate",
    description="Generate images from text prompts using HuggingFace Inference API. ⚠️ Free tier ~30-120s. Add HF_API_KEY env var for private tier (~5s). Models: sd-turbo, sdxl-turbo, flux-schnell.",
    category="Image & Video",
    parameters=[
        ToolParam("prompt", "string", "Text description of the image to generate"),
        ToolParam("output", "string", "Output file path", required=False, default=""),
        ToolParam("model", "string", "Model: sd-turbo, sdxl-turbo, flux-schnell", required=False, default="default"),
        ToolParam("negative_prompt", "string", "What to avoid in the image", required=False, default=""),
    ],
)
def image_generate(prompt: str, output: str = "", model: str = "default", negative_prompt: str = ""):
    from config import HF_API_URL, HF_API_KEY, UPLOADS_DIR

    model_id = HF_MODELS.get(model, HF_MODELS["default"])
    api_url = f"{HF_API_URL}/{model_id}"

    headers = {}
    if HF_API_KEY and HF_API_KEY.startswith("hf_"):
        headers["Authorization"] = f"Bearer {HF_API_KEY}"
        tier_info = "Private tier (faster)"
    else:
        tier_info = "Free tier (slower, ~30-120s)"

    payload = {"inputs": prompt}
    if negative_prompt:
        payload["parameters"] = {"negative_prompt": negative_prompt}

    try:
        # First attempt with longer timeout for free tier
        wait_time = 5
        max_retries = 3
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            timeout = 180 if attempt == 1 else 90 + (wait_time * attempt)  # Progressive timeout
            
            try:
                resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
                
                if resp.status_code == 503:
                    # Model loading/busy
                    wait_msg = f"Model initializing... waiting {wait_time}s (attempt {attempt}/{max_retries}). Tier: {tier_info}"
                    print(wait_msg)
                    time.sleep(wait_time)
                    wait_time = min(wait_time + 5, 30)
                    continue
                    
                elif resp.status_code == 429:
                    # Rate limited
                    remaining = resp.headers.get('Retry-After', '60')
                    error_msg = f"Rate limited. Please wait {remaining} seconds. Tip: Set HF_API_KEY env var for higher limits"
                    return {
                        "error": error_msg,
                        "status": 429,
                        "tier": tier_info,
                        "retry_after": int(remaining) if remaining.isdigit() else 60
                    }
                    
                elif resp.status_code == 401:
                    return {
                        "error": "Invalid HF_API_KEY. Check your credentials at huggingface.co/settings/tokens",
                        "status": 401,
                        "tier": "Authentication failed"
                    }
                    
                elif resp.status_code == 400:
                    error_text = resp.text[:500]
                    return {
                        "error": f"Invalid request: {error_text}",
                        "status": 400,
                        "hint": "Check prompt for inappropriate content or formatting issues"
                    }
                    
                elif resp.status_code == 200:
                    # Success!
                    if not output:
                        timestamp = int(time.time())
                        output = str(UPLOADS_DIR / f"generated_{timestamp}.png")

                    out_path = Path(output).resolve()
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(resp.content)

                    return {
                        "output": str(out_path),
                        "model": model_id,
                        "prompt": prompt,
                        "size_bytes": len(resp.content),
                        "tier": tier_info,
                        "attempts": attempt,
                        "success": True
                    }
                else:
                    # Other error
                    return {
                        "error": f"Unexpected error: {resp.status_code} - {resp.text[:300]}",
                        "status": resp.status_code,
                        "tier": tier_info
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"Timeout on attempt {attempt}. Retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        "error": f"Request timeout after {attempt} attempts (~{timeout}s). Model may be overloaded.",
                        "status": 504,
                        "tier": tier_info,
                        "tip": "Try again in 1-2 minutes or use a smaller model"
                    }
        
        return {
            "error": f"Failed to generate image after {max_retries} attempts. Model may be busy.",
            "status": 503,
            "tier": tier_info,
            "tip": "Try again later or set HF_API_KEY for faster generation"
        }

    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "type": type(e).__name__}
