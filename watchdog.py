"""
NexusMind Watchdog — Automatically restarts the server on crash.
"""
import time
import subprocess
import sys
import os

def run_server():
    """Run the main.py entry point and restart on failure."""
    while True:
        print("🚀 Starting NexusMind Watchdog...")
        try:
            # Run main.py as a subprocess
            process = subprocess.Popen([sys.executable, "main.py"])
            process.wait()
            
            if process.returncode != 0:
                print(f"⚠️  NexusMind crashed with exit code {process.returncode}. Restarting in 5 seconds...")
                time.sleep(5)
            else:
                print("🛑 NexusMind stopped normally.")
                break
        except KeyboardInterrupt:
            print("\n👋 Stopping Watchdog.")
            break
        except Exception as e:
            print(f"❌ Watchdog error: {e}. Restarting...")
            time.sleep(5)

if __name__ == "__main__":
    run_server()
