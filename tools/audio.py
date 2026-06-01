"""
Audio Enhancement — noise reduction, normalization, effects.
"""
import json
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="audio_enhance",
    description="Enhance audio files: normalize volume, change speed, trim, merge, convert format.",
    category="Audio",
    parameters=[
        ToolParam("path", "string", "Input audio file path"),
        ToolParam("action", "string", "Action: normalize, speed, trim, merge, convert, info"),
        ToolParam("output", "string", "Output file path", required=False, default=""),
        ToolParam("params", "string", "JSON parameters", required=False, default="{}"),
    ],
)
def audio_enhance(path: str, action: str, output: str = "", params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    try:
        from pydub import AudioSegment
    except ImportError:
        return {"error": "pydub not installed. pip install pydub"}

    from config import UPLOADS_DIR
    import time

    input_path = Path(path).resolve()
    if not input_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        audio = AudioSegment.from_file(str(input_path))

        if action == "info":
            return {
                "duration_ms": len(audio), "channels": audio.channels,
                "sample_width": audio.sample_width, "frame_rate": audio.frame_rate,
                "dBFS": round(audio.dBFS, 2), "max_dBFS": round(audio.max_dBFS, 2),
            }

        if not output:
            timestamp = int(time.time())
            output = str(UPLOADS_DIR / f"audio_{action}_{timestamp}{input_path.suffix}")

        out_path = Path(output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if action == "normalize":
            target_dBFS = p.get("target_dBFS", -20.0)
            change = target_dBFS - audio.dBFS
            audio = audio.apply_gain(change)

        elif action == "speed":
            factor = p.get("factor", 1.5)
            audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": int(audio.frame_rate * factor)
            }).set_frame_rate(audio.frame_rate)

        elif action == "trim":
            start = p.get("start_ms", 0)
            end = p.get("end_ms", len(audio))
            audio = audio[start:end]

        elif action == "merge":
            files = p.get("files", [])
            for f in files:
                other = AudioSegment.from_file(str(Path(f).resolve()))
                audio = audio + other

        elif action == "convert":
            fmt = p.get("format", "mp3")
            out_path = out_path.with_suffix(f".{fmt}")

        else:
            return {"error": f"Unknown action: {action}"}

        fmt = out_path.suffix.lstrip(".") or "wav"
        audio.export(str(out_path), format=fmt)

        return {
            "output": str(out_path),
            "duration_ms": len(audio),
            "action": action,
        }
    except Exception as e:
        return {"error": str(e)}
