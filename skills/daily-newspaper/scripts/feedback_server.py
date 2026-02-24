#!/usr/bin/env python3
"""Minimal HTTP server for receiving daily newspaper feedback.

Listens on localhost:9847. Accepts POST /api/feedback with JSON body.
Appends entries to memory/feedback.jsonl and logs via log_action.py.
Auto-shuts down after 2 hours of inactivity.
"""

import atexit
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 9847
PID_FILE = os.path.join(tempfile.gettempdir(), "pm_feedback_server.pid")
INACTIVITY_TIMEOUT = 2 * 60 * 60  # 2 hours in seconds

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
FEEDBACK_FILE = os.path.join(PROJECT_ROOT, "memory", "feedback.jsonl")
LOG_ACTION = os.path.join(PROJECT_ROOT, "skills", "memory-manager", "scripts", "log_action.py")

from onboard_handler import handle_onboard, handle_scrape_website, handle_generate, serve_welcome_page

# Global timer for auto-shutdown
_shutdown_timer = None
_timer_lock = threading.Lock()


def reset_inactivity_timer():
    """Reset the auto-shutdown timer on activity."""
    global _shutdown_timer
    with _timer_lock:
        if _shutdown_timer is not None:
            _shutdown_timer.cancel()
        _shutdown_timer = threading.Timer(INACTIVITY_TIMEOUT, auto_shutdown)
        _shutdown_timer.daemon = True
        _shutdown_timer.start()


def auto_shutdown():
    """Shut down the server after inactivity timeout."""
    print(f"[{datetime.now().isoformat()}] No activity for {INACTIVITY_TIMEOUT}s, shutting down.")
    # os._exit bypasses atexit handlers; use it here since we're in a daemon
    # thread and sys.exit() would only raise SystemExit in this thread.
    cleanup_pid()
    os._exit(0)


def _is_process_alive(pid: int) -> bool:
    """Check if a process is still running (cross-platform)."""
    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def write_pid():
    """Write PID file, exit if another instance is running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if _is_process_alive(old_pid):
                print(f"ERROR: Feedback server already running (PID {old_pid})")
                sys.exit(1)
        except (OSError, ValueError):
            # Process not running or invalid PID, clean up stale file
            pass
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def cleanup_pid():
    """Remove PID file."""
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


class FeedbackHandler(BaseHTTPRequestHandler):
    """Handle feedback API requests."""

    def log_message(self, format, *args):
        """Suppress default request logging."""
        pass

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _handle_profile_status(self):
        """Check if a profile exists and return name + delivery time."""
        identity_path = os.path.join(PROJECT_ROOT, "profile", "identity.yaml")
        try:
            import yaml
            with open(identity_path) as f:
                data = yaml.safe_load(f) or {}
            name = (data.get("name") or "").strip()
            if name:
                prefs_path = os.path.join(PROJECT_ROOT, "profile", "preferences.yaml")
                delivery = "07:00"
                try:
                    with open(prefs_path) as f:
                        prefs = yaml.safe_load(f) or {}
                    delivery = prefs.get("daily_artifact", {}).get("delivery_time", delivery)
                except Exception:
                    pass
                self._send_json(200, {"exists": True, "name": name, "delivery_time": delivery})
                return
        except Exception:
            pass
        self._send_json(200, {"exists": False})

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Route GET requests."""
        if self.path == "/" or self.path == "/welcome":
            serve_welcome_page(self)
        elif self.path == "/health":
            self._send_json(200, {"status": "ok", "pid": os.getpid()})
        elif self.path == "/api/profile-status":
            self._handle_profile_status()
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        """Route POST requests."""
        reset_inactivity_timer()

        if self.path == "/api/onboard":
            handle_onboard(self)
            return
        elif self.path == "/api/scrape-website":
            handle_scrape_website(self)
            return
        elif self.path == "/api/generate":
            handle_generate(self)
            return
        elif self.path != "/api/feedback":
            self._send_json(404, {"error": "not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self._send_json(400, {"error": "invalid JSON"})
            return

        # Validate required fields
        rating = data.get("rating")
        if rating is not None and (not isinstance(rating, (int, float)) or not 1 <= rating <= 5):
            self._send_json(400, {"error": "rating must be 1-5"})
            return

        # Build feedback entry
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
            "rating": rating,
            "section_ratings": data.get("section_ratings", {}),
            "comment": data.get("comment", ""),
        }

        # Append to feedback.jsonl
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        with open(FEEDBACK_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Log via log_action.py
        try:
            subprocess.run(
                [
                    sys.executable, LOG_ACTION,
                    "--action", "feedback_received",
                    "--detail", f"Rating {rating}/5 for {entry['date']}",
                ],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass  # Don't fail the request if logging fails

        print(f"[{entry['timestamp']}] Feedback received: {rating}/5 for {entry['date']}")
        self._send_json(200, {"status": "ok"})


def main():
    write_pid()

    # Clean up on exit (atexit works cross-platform)
    atexit.register(cleanup_pid)
    # SIGINT is available on all platforms; SIGTERM only on Unix
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    reset_inactivity_timer()

    server = HTTPServer(("127.0.0.1", PORT), FeedbackHandler)
    print(f"Feedback server listening on http://localhost:{PORT}")
    print(f"PID: {os.getpid()} (file: {PID_FILE})")
    print(f"Auto-shutdown after {INACTIVITY_TIMEOUT // 3600}h of inactivity")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup_pid()
        server.server_close()


if __name__ == "__main__":
    main()
