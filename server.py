"""
NexusMind Server — FastAPI + WebSocket for streaming chat.
"""
import json
import re
import time
import uuid
import logging
import asyncio
import functools
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, ORJSONResponse
import uvicorn

from config import HOST, PORT, WEB_DIR, DATA_DIR, UPLOADS_DIR, SYSTEM_PROMPT, MAX_TOKENS, TEMPERATURE, TOP_P
from core.llm import engine as llm_engine
from core.tool_registry import registry, parse_tool_calls
from core.confidence import logprobs_to_confidence, format_confidence
from core.controller import Controller
from core.memory import MemorySystem
from core.reasoning_cache import ReasoningCache
from core.self_debug import SelfDebugger
from core.project import project_manager
from core.latex_converter import convert_latex_to_unicode
from core.auto_scout import scout

logger = logging.getLogger("nexusmind.server")

# ─── Initialize ──────────────────────────────────────────────
app = FastAPI(title="NexusMind", version="1.0.0", default_response_class=ORJSONResponse)
memory = MemorySystem()
cache = ReasoningCache()
debugger = SelfDebugger(llm_engine=llm_engine)
controller = Controller(memory)

# Register all tools
from tools import register_all_tools
register_all_tools()

# Serve static files
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


@app.on_event("startup")
async def startup_event():
    """Staggered startup — prevents 10 second crash."""
    from config import SCOUT_ENABLED, PRELOAD_ALL_MODELS, MODEL_PROFILE

    await asyncio.sleep(0.1)  # let FastAPI fully bind first

    # Step 1: load primary model first before anything else
    try:
        await asyncio.to_thread(llm_engine.load, MODEL_PROFILE)
        logger.info(f"Primary model loaded: {MODEL_PROFILE}")
    except Exception as e:
        logger.error(f"Primary model load failed: {e}")

    # Step 2: remaining models staggered in background
    if PRELOAD_ALL_MODELS:
        asyncio.create_task(_staggered_preload())

    # Step 3: scout starts last with a long delay
    if SCOUT_ENABLED:
        asyncio.create_task(_delayed_scout_start())


async def _staggered_preload():
    """Load remaining models one at a time with gaps."""
    from config import MODEL_PROFILE, MAX_LOADED_MODELS
    priority = [p for p in ["LIGHTWEIGHT", "BALANCED", "CHAT"] if p != MODEL_PROFILE]
    for i, pid in enumerate(priority[:MAX_LOADED_MODELS - 1]):
        await asyncio.sleep(3.0 * (i + 1))
        try:
            await asyncio.to_thread(llm_engine.load, pid)
            logger.info(f"Background loaded: {pid}")
        except Exception as e:
            logger.warning(f"Background load failed {pid}: {e}")


async def _delayed_scout_start():
    """Start scout after everything else is stable."""
    await asyncio.sleep(45)
    scout.start()
    logger.info("Scout started")


# ─── HTTP Endpoints ──────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    index_file = WEB_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status():
    from config import MODEL_PROFILES, MODEL_PROFILE
    from core.monitor import monitor
    tool_names = registry.list_names()
    return {
        "status": "running",
        "model_loaded": llm_engine.is_loaded,
        "current_profile": MODEL_PROFILE,
        "profiles": {k: v["name"] for k, v in MODEL_PROFILES.items()},
        "tools": tool_names,
        "tool_count": len(tool_names),
        "memory": memory.get_stats(),
        "cache": cache.stats(),
        "metrics": monitor.get_metrics()
    }


@app.get("/api/tools")
async def list_tools():
    return {"tools": registry.list_tools(), "categories": registry.by_category()}


@app.post("/api/tools/execute")
async def execute_tool(data: dict):
    """
    Execute a registered NexusMind tool directly.
    Body: {"name": "<tool_name>", "args": {...}}
    """
    name = data.get("name")
    args = data.get("args") or {}
    if not name:
        raise HTTPException(status_code=400, detail="Tool 'name' is required")
    result = await registry.execute(name, args)
    status = 200 if result.get("success", False) else 400
    return JSONResponse(content=result, status_code=status)

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    dest = UPLOADS_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return {"path": str(dest), "size": len(content), "name": file.filename}


@app.get("/api/memory")
async def get_memory():
    return memory.get_stats()


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """Retrieve history for a session."""
    history = memory.get_session_messages(session_id)
    if not history:
        # Fallback to current short-term if no session found
        return {"history": memory.get_history()}
    return {"history": history}

@app.get("/api/export/{session_id}")
async def export_chat(session_id: str):
    """Export chat history as JSON."""
    history = memory.get_session_messages(session_id)
    if not history:
        history = memory.get_history()
    
    export_dir = DATA_DIR / "exports"
    export_dir.mkdir(exist_ok=True)
    file_path = export_dir / f"nexusmind_chat_{session_id}_{int(time.time())}.json"
    
    def _save_file():
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
            
    await asyncio.to_thread(_save_file)
    
    return FileResponse(path=file_path, filename=file_path.name, media_type="application/json")

@app.post("/api/memory/clear")
async def clear_memory():
    memory.clear_short_term()
    cache.clear()
    return {"status": "cleared"}


@app.get("/api/sessions")
async def list_sessions():
    """List all available chat sessions. Instant via pre-built titles."""
    return {"sessions": memory.list_sessions()}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Load a specific chat session's history."""
    messages = memory.get_session_messages(session_id)
    return {"messages": messages}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a specific chat session."""
    memory.delete_session(session_id)
    return {"status": "success"}

# ─── Workspace Endpoints ─────────────────────────────────────

@app.post("/api/workspace")
async def set_workspace(data: dict):
    """Set the current workspace root."""
    path = data.get("path")
    if not path:
        raise HTTPException(status_code=400, detail="Path is required")
    result = project_manager.set_workspace(path)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.get("/api/workspace/files")
async def get_workspace_files():
    """Get the file tree of the current workspace."""
    return {"files": project_manager.get_file_tree()}

@app.post("/api/workspace/init")
async def init_project(data: dict):
    """Bootstrap a project template."""
    template = data.get("template")
    if not template:
        raise HTTPException(status_code=400, detail="Template is required")
    result = project_manager.initialize_project(template)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/model/switch")
async def switch_model(data: dict):
    """Switch the active model profile."""
    profile = data.get("profile")
    try:
        llm_engine.switch_to_profile(profile)
        return {"status": "success", "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Scout Endpoints ──────────────────────────────────────────

@app.get("/api/scout/findings")
async def get_scout_findings(include_dismissed: bool = False):
    """Retrieve background scout findings."""
    return {"findings": scout.get_findings(include_dismissed), "total": len(scout.findings)}


@app.post("/api/scout/dismiss")
async def dismiss_scout_finding(data: dict):
    """Dismiss a specific finding."""
    repo_id = data.get("id")
    if not repo_id:
        raise HTTPException(status_code=400, detail="ID is required")
    scout.dismiss(repo_id)
    return {"status": "success"}


@app.post("/api/scout/scan")
async def trigger_scout_scan():
    """Manually trigger an optimization scan."""
    new = await scout.force_scan()
    return {"status": "success", "new_count": len(new)}

@app.post("/api/scout/implement")
async def implement_scout_finding(data: dict):
    """Trigger the self-improvement protocol to implement a finding."""
    repo_url = data.get("url")
    if not repo_url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Hand off to auto_scout
    # Save as proposal for user review — never auto-execute
    proposals_file = DATA_DIR / "scout_proposals.json"
    proposals = []
    if proposals_file.exists():
        proposals = json.loads(proposals_file.read_text())
    proposals.append({
        "url": repo_url,
        "proposed_at": time.time(),
        "status": "pending_review"
    })
    proposals_file.write_text(json.dumps(proposals, indent=2))
    return {"status": "saved", "message": "Saved for your review — check data/scout_proposals.json"}

# ─── Neural Network Endpoints ────────────────────────────────

@app.post("/api/neural/create")
async def neural_create(data: dict):
    """Create a neural network with given layer configuration."""
    from core.neural_network import create_network
    layers = data.get("layers", [2, 8, 4, 1])
    lr = data.get("learning_rate", 0.1)
    activation = data.get("activation", "sigmoid")
    nn = create_network(layers, lr, activation)
    return {"status": "created", "layers": layers, "state": nn.get_state()}


@app.post("/api/neural/train")
async def neural_train(data: dict):
    """Train the neural network on a demo dataset. Non-blocking with background thread."""
    from core.neural_network import get_network, create_network, get_demo_dataset
    import numpy as np

    dataset_name = data.get("dataset", "xor")
    epochs = min(data.get("epochs", 500), 5000)
    lr = data.get("learning_rate", 0.1)

    X, y, recommended_layers = get_demo_dataset(dataset_name)
    layers = data.get("layers", recommended_layers)

    # Use existing network or create new one
    nn = get_network()
    if not nn or nn.layer_sizes != layers:
        nn = create_network(layers, lr)
    else:
        nn.learning_rate = lr

    # Start training in background
    nn.train_async(X, y, epochs=epochs)

    return {
        "status": "started",
        "dataset": dataset_name,
        "epochs": epochs,
        "state": nn.get_state(),
    }


@app.post("/api/neural/reset")
async def neural_reset():
    """Reset the current neural network."""
    from core.neural_network import get_network
    nn = get_network()
    if nn:
        nn.reset()
        return {"status": "reset", "state": nn.get_state()}
    return {"status": "no_network"}


@app.post("/api/neural/predict")
async def neural_predict(data: dict):
    """Run prediction on the current neural network."""
    from core.neural_network import get_network
    import numpy as np

    nn = get_network()
    if not nn:
        raise HTTPException(status_code=400, detail="No neural network created. Call /api/neural/create first.")

    inputs = data.get("inputs", [])
    if not inputs:
        raise HTTPException(status_code=400, detail="No inputs provided")

    X = np.array([inputs], dtype=np.float64)
    output = nn.predict(X)

    return {
        "inputs": inputs,
        "output": output[0].tolist(),
        "state": nn.get_state(),
    }


@app.get("/api/neural/state")
async def neural_state():
    """Get the current neural network state for visualization."""
    from core.neural_network import get_network

    nn = get_network()
    if not nn:
        return {"status": "no_network", "state": None}

    return {"status": "ok", "state": nn.get_state()}



@app.get("/api/neural/datasets")
async def neural_datasets():
    """List available demo datasets."""
    from config import NN_DEMO_DATASETS
    return {
        "datasets": [
            {"name": "xor", "description": "XOR logic gate (2 inputs → 1 output)", "layers": [2, 8, 4, 1]},
            {"name": "circles", "description": "Concentric circles classification", "layers": [2, 16, 8, 1]},
            {"name": "spiral", "description": "Spiral pattern classification", "layers": [2, 32, 16, 8, 1]},
            {"name": "digits", "description": "3×5 digit recognition (0-3)", "layers": [15, 32, 16, 4]},
        ]
    }


# ─── User Settings Endpoints ────────────────────────────────

@app.get("/api/user/settings")
async def get_user_settings():
    """Get user personalization settings."""
    from config import USER_SETTINGS_FILE, DEFAULT_USERNAME, DEFAULT_THEME
    defaults = {
        "username": DEFAULT_USERNAME,
        "avatar": "🧑‍💻",
        "theme": DEFAULT_THEME,
        "custom_instructions": "",
        "show_thinking": True,
        "auto_scroll": True,
    }
    try:
        if USER_SETTINGS_FILE.exists():
            with open(USER_SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                defaults.update(saved)
    except Exception:
        pass
    return defaults


@app.post("/api/user/settings")
async def save_user_settings(data: dict):
    """Save user personalization settings."""
    from config import USER_SETTINGS_FILE
    try:
        with open(USER_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def sanitize_response(text: str) -> str:
    """Consolidated sanitization for LaTeX, math symbols, and tool-call residue."""
    # Remove $, \[, \], \(, \)
    text = re.sub(r'[\$]|\\\[|\\\]|\\\(|\\\)', '', text)
    # Strip residual tool calls
    text = re.sub(r'\{[^{}]*"tool"\s*:\s*"[^"]+?"[^{}]*\}', '', text, flags=re.DOTALL)
    # Convert LaTeX math to Unicode symbols
    text = convert_latex_to_unicode(text)
    return text.strip()

# ─── WebSocket Chat ──────────────────────────────────────────

@app.websocket("/ws/chat/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str = "default"):
    """WebSocket endpoint for real-time chat with session-based memory."""
    await websocket.accept()
    logger.info(f"WebSocket connected: {session_id}")

    # Register with auto-scout for live alerts
    scout.register_websocket(websocket)
    
    # Send current pending findings immediately
    pending = scout.get_findings(include_dismissed=False)
    if pending:
        await websocket.send_json({
            "type": "scout_alert",
            "findings": pending,
            "total_pending": len(pending),
            "initial": True
        })
    
    # Always reset and load the specific session history to prevent bleeding
    memory.clear_short_term()
    session_history = memory.get_session_messages(session_id)
    for msg in session_history:
        memory.add_message(msg["role"], msg["content"])
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") != "message":
                continue
                
            user_text = data.get("content", "")
            if not user_text.strip():
                continue


            # ─── Neural Cache / Reasoning Visualization ───
            reasoning_steps = [
                f"Analyzing input: {user_text[:30]}...",
                "Retrieving context from long-term memory...",
                "Routing to Smart Tutor profile...",
                "Generating structured response plan..."
            ]
            
            for step in reasoning_steps:
                await websocket.send_json({
                    "type": "reasoning_step",
                    "step": step
                })
                await asyncio.sleep(0.2) 

            # Check reasoning cache — return instantly if fresh and confident
            cached = cache.lookup(user_text)
            if cached:
                age_hours = (time.time() - cached.get("timestamp", time.time())) / 3600
                if cached.get("confidence", 0) >= 7.5 and age_hours < 24:
                    # High confidence + fresh = zero LLM call
                    await websocket.send_json({
                        "type": "message",
                        "content": cached["answer"],
                        "confidence": format_confidence(cached["confidence"]),
                        "confidence_score": cached["confidence"],
                        "cached": True,
                        "tools_used": cached.get("tools_used", []),
                        "gen_time": 0,
                        "tps": 0,
                    })
                    memory.add_message("assistant", cached["answer"])
                    continue
                # Low confidence or stale — fall through to normal generation

            try:
                # Use Controller to handle request
                result = await controller.handle_request(session_id, user_text, websocket)
                
                # Send final completed message to client
                if result and isinstance(result, dict):
                    final_content = sanitize_response(result.get("content", ""))
                    await websocket.send_json({
                        "type": "message",
                        "content": final_content,
                        "profile": result.get("profile", "CHAT"),
                        "gen_time": result.get("gen_time", 0),
                        "tps": result.get("tps", 0),
                    })
                
                # Save session after each response
                memory.save_session(session_id)
                
                # Title generation if first message
                if len(memory.short_term) <= 2:
                    asyncio.create_task(generate_dynamic_title(session_id, user_text))

            except Exception as e:
                logger.error(f"Generation error: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "content": f"Error: {str(e)}",
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        scout.unregister_websocket(websocket)
        memory.save_session(session_id)


async def generate_dynamic_title(session_id: str, first_message: str):
    """Generate a 3-5 word summary title for the chat session."""
    try:
        prompt = f"Summarize this AI chat request into exactly 3-5 words for a sidebar title. DO NOT use quotes or 'Title:'.\n\nRequest: {first_message}"
        title = await asyncio.to_thread(llm_engine.generate_simple, prompt, 20)
        title = title.strip().replace('"', '').replace("'", "")
        if len(title) > 40:
            title = title[:37] + "..."
        memory.update_session_title(session_id, title)
        logger.info(f"Generated title for {session_id}: {title}")
    except Exception as e:
        logger.error(f"Failed to generate title: {e}")
        # Fallback to truncated user message
        fallback = (first_message[:30] + "...") if len(first_message) > 30 else first_message
        memory.update_session_title(session_id, fallback)

def start_server():
    """Start the NexusMind server."""
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    start_server()
