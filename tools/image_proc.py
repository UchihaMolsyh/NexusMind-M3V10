"""
Image Processing — resize, crop, filter, convert, and analyze images using Pillow & OpenCV.
"""
import json
import base64
from pathlib import Path
from io import BytesIO
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="image_process",
    description="Process images: resize, crop, rotate, filter, convert format, get info, thumbnail, grayscale, blur, sharpen, edge detect.",
    category="Image & Video",
    parameters=[
        ToolParam("path", "string", "Input image path"),
        ToolParam("action", "string", "Action: info, resize, crop, rotate, flip, grayscale, blur, sharpen, edge, brightness, contrast, thumbnail, convert"),
        ToolParam("output", "string", "Output path (optional, defaults to overwrite)", required=False, default=""),
        ToolParam("params", "string", "JSON params for action", required=False, default="{}"),
    ],
)
def image_process(path: str, action: str, output: str = "", params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    try:
        from PIL import Image, ImageFilter, ImageEnhance, ImageOps
    except ImportError:
        return {"error": "Pillow not installed. pip install Pillow"}

    input_path = Path(path).resolve()
    if not input_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        img = Image.open(str(input_path))
        out_path = Path(output).resolve() if output else input_path

        if action == "info":
            return {
                "path": str(input_path), "format": img.format,
                "size": list(img.size), "mode": img.mode,
                "has_alpha": img.mode in ("RGBA", "LA", "PA"),
            }

        elif action == "resize":
            w, h = p.get("width", img.width), p.get("height", img.height)
            img = img.resize((int(w), int(h)), Image.LANCZOS)

        elif action == "crop":
            box = (p.get("left", 0), p.get("top", 0), p.get("right", img.width), p.get("bottom", img.height))
            img = img.crop(box)

        elif action == "rotate":
            angle = p.get("angle", 90)
            img = img.rotate(angle, expand=True)

        elif action == "flip":
            direction = p.get("direction", "horizontal")
            img = ImageOps.mirror(img) if direction == "horizontal" else ImageOps.flip(img)

        elif action == "grayscale":
            img = ImageOps.grayscale(img)

        elif action == "blur":
            radius = p.get("radius", 5)
            img = img.filter(ImageFilter.GaussianBlur(radius=radius))

        elif action == "sharpen":
            factor = p.get("factor", 2.0)
            img = ImageEnhance.Sharpness(img).enhance(factor)

        elif action == "edge":
            img = img.filter(ImageFilter.FIND_EDGES)

        elif action == "brightness":
            factor = p.get("factor", 1.5)
            img = ImageEnhance.Brightness(img).enhance(factor)

        elif action == "contrast":
            factor = p.get("factor", 1.5)
            img = ImageEnhance.Contrast(img).enhance(factor)

        elif action == "thumbnail":
            size = (p.get("width", 256), p.get("height", 256))
            img.thumbnail(size, Image.LANCZOS)

        elif action == "convert":
            fmt = p.get("format", "PNG")
            out_path = out_path.with_suffix(f".{fmt.lower()}")

        else:
            return {"error": f"Unknown action: {action}"}

        if action != "info":
            if img.mode == "RGBA" and out_path.suffix.lower() in (".jpg", ".jpeg"):
                img = img.convert("RGB")
            img.save(str(out_path))
            return {"output": str(out_path), "size": list(img.size), "action": action}

    except Exception as e:
        return {"error": str(e)}


@registry.tool(
    name="image_upscale",
    description="Upscale an image using interpolation (OpenCV). Lightweight CPU-based upscaling.",
    category="Image & Video",
    parameters=[
        ToolParam("path", "string", "Input image path"),
        ToolParam("scale", "string", "Scale factor (2, 3, 4)", required=False, default="2"),
        ToolParam("output", "string", "Output path", required=False, default=""),
        ToolParam("method", "string", "Interpolation: lanczos, cubic, linear", required=False, default="lanczos"),
    ],
)
def image_upscale(path: str, scale: str = "2", output: str = "", method: str = "lanczos"):
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"error": "OpenCV not installed. pip install opencv-python-headless"}

    input_path = Path(path).resolve()
    if not input_path.exists():
        return {"error": f"File not found: {path}"}

    s = int(scale)
    methods = {
        "lanczos": cv2.INTER_LANCZOS4,
        "cubic": cv2.INTER_CUBIC,
        "linear": cv2.INTER_LINEAR,
    }
    interp = methods.get(method, cv2.INTER_LANCZOS4)

    try:
        img = cv2.imread(str(input_path))
        if img is None:
            return {"error": "Failed to read image"}

        h, w = img.shape[:2]
        new_w, new_h = w * s, h * s
        upscaled = cv2.resize(img, (new_w, new_h), interpolation=interp)

        out_path = Path(output).resolve() if output else input_path.with_stem(f"{input_path.stem}_upscaled_{s}x")
        cv2.imwrite(str(out_path), upscaled)

        return {
            "output": str(out_path),
            "original_size": [w, h],
            "new_size": [new_w, new_h],
            "scale": s,
            "method": method,
        }
    except Exception as e:
        return {"error": str(e)}
