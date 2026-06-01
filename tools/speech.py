"""
Speech — speech-to-text and text-to-speech.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


@registry.tool(
    name="speech_to_text",
    description="Convert speech audio to text. Uses SpeechRecognition library with Google free API or Whisper.",
    category="Audio",
    parameters=[
        ToolParam("path", "string", "Path to audio file (WAV, MP3, FLAC, etc.)"),
        ToolParam("engine", "string", "Engine: google (free), whisper (local)", required=False, default="google"),
        ToolParam("language", "string", "Language code (e.g., en-US, zh-CN)", required=False, default="en-US"),
    ],
)
def speech_to_text(path: str, engine: str = "google", language: str = "en-US"):
    audio_path = Path(path).resolve()
    if not audio_path.exists():
        return {"error": f"File not found: {path}"}

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        # Convert to WAV if needed
        if audio_path.suffix.lower() != ".wav":
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(audio_path))
                wav_path = audio_path.with_suffix(".wav")
                audio.export(str(wav_path), format="wav")
                audio_path = wav_path
            except ImportError:
                return {"error": "pydub needed for non-WAV files. pip install pydub"}

        with sr.AudioFile(str(audio_path)) as source:
            audio_data = recognizer.record(source)

        if engine == "google":
            text = recognizer.recognize_google(audio_data, language=language)
        elif engine == "whisper":
            try:
                text = recognizer.recognize_whisper(audio_data, language=language[:2])
            except AttributeError:
                return {"error": "Whisper not available. pip install openai-whisper"}
        else:
            text = recognizer.recognize_google(audio_data, language=language)

        return {"text": text, "engine": engine, "language": language}

    except ImportError:
        return {"error": "SpeechRecognition not installed. pip install SpeechRecognition"}
    except sr.UnknownValueError:
        return {"error": "Could not understand the audio"}
    except sr.RequestError as e:
        return {"error": f"Recognition service error: {e}"}
    except Exception as e:
        return {"error": str(e)}


@registry.tool(
    name="text_to_speech",
    description="Convert text to speech audio. Uses pyttsx3 (offline, lightweight).",
    category="Audio",
    parameters=[
        ToolParam("text", "string", "Text to convert to speech"),
        ToolParam("output", "string", "Output file path (WAV)", required=False, default=""),
        ToolParam("rate", "string", "Speech rate (default: 150 wpm)", required=False, default="150"),
        ToolParam("volume", "string", "Volume 0.0-1.0 (default: 0.9)", required=False, default="0.9"),
    ],
)
def text_to_speech(text: str, output: str = "", rate: str = "150", volume: str = "0.9"):
    try:
        import pyttsx3
    except ImportError:
        return {"error": "pyttsx3 not installed. pip install pyttsx3"}

    from config import UPLOADS_DIR
    import time

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", int(rate))
        engine.setProperty("volume", float(volume))

        if not output:
            timestamp = int(time.time())
            output = str(UPLOADS_DIR / f"speech_{timestamp}.wav")

        out_path = Path(output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        engine.stop()

        return {
            "output": str(out_path),
            "text_length": len(text),
            "rate": int(rate),
        }
    except Exception as e:
        return {"error": str(e)}
