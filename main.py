
"""
NexusMind — Entry Point
Checks model availability and starts the server.
"""
import sys
import os
import logging
import webbrowser
import threading
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexusmind")


BANNER = r"""
    _   __                    __  __ _           __
   / | / /__  _  ____  _____ /  |/  (_)___  ____/ /
  /  |/ / _ \| |/_/ / / / __/ /|_/ / / __ \/ __  / 
 / /|  /  __/>  </ /_/ /\__ / /  / / / / / / /_/ /  
/_/ |_/\___/_/|_|\__,_//___/_/  /_/_/_/ /_/\__,_/   
                                                      
    🧠 Local AI Tool — Unfiltered & Unrestricted
    ──────────────────────────────────────────────
"""


def check_dependencies():
    """Check if required packages are installed."""
    required = ["fastapi", "uvicorn", "llama_cpp"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print(f"   Run: pip install -r requirements.txt\n")
        return False
    return True


def check_models():
    """Check if model files exist for all profiles. Does NOT download anything."""
    from config import MODELS_DIR, MODEL_PROFILES
    
    all_ok = True
    for profile_id, profile in MODEL_PROFILES.items():
        target_path = MODELS_DIR / profile["file"]
        if target_path.exists():
            size_mb = target_path.stat().st_size / (1024 * 1024)
            logger.info(f"  ✅ [{profile_id}] {profile['name']} — {profile['file']} ({size_mb:.0f} MB)")
        else:
            logger.warning(f"  ❌ [{profile_id}] {profile['name']} — MISSING: {profile['file']}")
            all_ok = False
        
        # Check draft models
        for draft in profile.get("drafts", []):
            draft_path = MODELS_DIR / draft["file"]
            if draft_path.exists():
                size_mb = draft_path.stat().st_size / (1024 * 1024)
                logger.info(f"      ✅ Draft: {draft['file']} ({size_mb:.0f} MB)")
            else:
                logger.warning(f"      ⚠️  Draft missing: {draft['file']} (speculative decoding disabled for this profile)")
    
    if all_ok:
        logger.info("✅ All models verified.")
    else:
        logger.warning("⚠️  Some models are missing. Place them in the 'models' folder.")
        logger.warning("   The server will still start, but missing profiles won't work.")
    
    return True  # Always allow startup


def open_browser():
    """Open browser immediately."""
    from config import HOST, PORT
    url = f"http://{HOST}:{PORT}"
    logger.info(f"🌐 Opening browser at {url}")
    webbrowser.open(url)


def main():
    try:
        print(BANNER)
    except UnicodeEncodeError:
        print(BANNER.encode('utf-8').decode('cp1252', 'ignore'))

    # Check dependencies
    if not check_dependencies():
        logger.error("Please install dependencies first: pip install -r requirements.txt")
        sys.exit(1)

    # Check model availability (no downloads)
    logger.info("📂 Checking model files...")
    check_models()

    # Open browser in background thread
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # Start server
    from config import HOST, PORT
    logger.info(f"🚀 Starting NexusMind on http://{HOST}:{PORT}")
    logger.info("   Press Ctrl+C to stop.\n")

    from server import start_server
    start_server()


if __name__ == "__main__":
    main()
