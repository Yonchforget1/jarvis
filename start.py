#!/usr/bin/env python3
"""Jarvis AI Agent Platform — One-command launcher.

Usage:
    python start.py              Start API server on port 3000
    python start.py --port 8000  Custom port
    python start.py --whatsapp   Also start WhatsApp bridge
    python start.py --desktop    Launch Electron desktop app
"""

import argparse
import os
import signal
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# Ensure project root is importable
sys.path.insert(0, PROJECT_ROOT)


def check_ollama():
    """Check if Ollama is running when config uses ollama backend."""
    try:
        from jarvis.config import Config
        config = Config.load()
        if config.backend != "ollama":
            return True
        import urllib.request
        base_url = getattr(config, "ollama_base_url", "http://localhost:11434")
        req = urllib.request.urlopen(f"{base_url}/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


def start_api(port: int) -> subprocess.Popen:
    """Start the FastAPI backend server."""
    print(f"[jarvis] Starting API server on port {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app",
         "--host", "0.0.0.0", "--port", str(port), "--log-level", "info"],
        cwd=PROJECT_ROOT,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=2)
            print(f"[jarvis] API server ready at http://localhost:{port}")
            return proc
        except Exception:
            time.sleep(1)
    print("[jarvis] WARNING: API server may not be ready yet")
    return proc


def start_whatsapp(api_port: int) -> subprocess.Popen | None:
    """Start the WhatsApp bridge."""
    bridge_dir = os.path.join(PROJECT_ROOT, "jarvis", "integrations")
    bridge_js = os.path.join(bridge_dir, "whatsapp_bridge.js")
    if not os.path.isfile(bridge_js):
        print("[jarvis] WhatsApp bridge not found, skipping")
        return None
    if not os.path.isdir(os.path.join(bridge_dir, "node_modules")):
        print("[jarvis] Installing WhatsApp bridge dependencies...")
        subprocess.run(["npm", "install"], cwd=bridge_dir, check=True)
    print("[jarvis] Starting WhatsApp bridge...")
    proc = subprocess.Popen(
        ["node", "whatsapp_bridge.js", "--api", f"http://localhost:{api_port}"],
        cwd=bridge_dir,
    )
    return proc


def start_desktop() -> subprocess.Popen | None:
    """Launch the Electron desktop app."""
    desktop_dir = os.path.join(PROJECT_ROOT, "desktop")
    if not os.path.isdir(desktop_dir):
        print("[jarvis] Desktop app not found, skipping")
        return None
    if not os.path.isdir(os.path.join(desktop_dir, "node_modules")):
        print("[jarvis] Installing desktop app dependencies...")
        subprocess.run(["npm", "install"], cwd=desktop_dir, check=True)
    print("[jarvis] Launching desktop app...")
    proc = subprocess.Popen(
        ["npx", "electron", ".", "--dev"],
        cwd=desktop_dir,
    )
    return proc


def main():
    parser = argparse.ArgumentParser(description="Jarvis AI Agent Platform Launcher")
    parser.add_argument("--port", type=int, default=3000, help="API server port (default: 3000)")
    parser.add_argument("--whatsapp", action="store_true", help="Also start WhatsApp bridge")
    parser.add_argument("--desktop", action="store_true", help="Launch Electron desktop app")
    args = parser.parse_args()

    procs = []

    # Check Ollama
    if not check_ollama():
        print("[jarvis] WARNING: Ollama not running. Start it with: ollama serve")
        print("[jarvis] Then pull the model: ollama pull llama3.1:8b")

    # Start API
    api_proc = start_api(args.port)
    procs.append(api_proc)

    # Start WhatsApp bridge
    if args.whatsapp:
        wa_proc = start_whatsapp(args.port)
        if wa_proc:
            procs.append(wa_proc)

    # Launch desktop app
    if args.desktop:
        desk_proc = start_desktop()
        if desk_proc:
            procs.append(desk_proc)

    print(f"\n[jarvis] All services running. Press Ctrl+C to stop.\n")
    print(f"  Web UI:    http://localhost:{args.port}")
    print(f"  API Docs:  http://localhost:{args.port}/docs")
    print(f"  Health:    http://localhost:{args.port}/api/health")
    if args.whatsapp:
        print(f"  WhatsApp:  Bridge active (scan QR on first run)")
    print()

    # Wait for Ctrl+C
    def shutdown(sig, frame):
        print("\n[jarvis] Shutting down all services...")
        for proc in reversed(procs):
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("[jarvis] All services stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for any process to exit
    try:
        while True:
            for proc in procs:
                if proc.poll() is not None:
                    print(f"[jarvis] Process {proc.pid} exited with code {proc.returncode}")
                    procs.remove(proc)
                    if not procs:
                        return
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
