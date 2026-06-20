#!/usr/bin/env python3
"""PersonalMentor — Daily Newspaper Pipeline (cross-platform).

Drop-in replacement for run_daily.sh that works on macOS, Linux, and Windows.

Usage:
    python skills/daily-newspaper/scripts/run_daily.py
"""

import glob
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

# ---------------------------------------------------------------------------
# Resolve project root (relative to this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent


def _activate_venv():
    """Prepend the venv's bin/Scripts dir to PATH so child processes use it."""
    if platform.system() == "Windows":
        venv_bin = PROJECT_ROOT / ".venv" / "Scripts"
    else:
        venv_bin = PROJECT_ROOT / ".venv" / "bin"
    if venv_bin.is_dir():
        os.environ["PATH"] = str(venv_bin) + os.pathsep + os.environ.get("PATH", "")
        os.environ["VIRTUAL_ENV"] = str(PROJECT_ROOT / ".venv")


def _load_dotenv():
    """Load .env file into os.environ (portable, no bash 'source')."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # Fallback: simple key=value parser (handles KEY=VALUE and KEY="VALUE")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)


def _python() -> str:
    """Return the Python executable to use for sub-processes."""
    return sys.executable


def _run(args, **kwargs):
    """Run a subprocess, returning CompletedProcess."""
    kwargs.setdefault("cwd", str(PROJECT_ROOT))
    return subprocess.run(args, **kwargs)


def _health_check(port=9847) -> bool:
    """Return True if a service responds on localhost:<port>/health."""
    try:
        resp = urlopen(f"http://localhost:{port}/health", timeout=2)
        return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def check_profile() -> bool:
    """Return True if a valid profile/identity.yaml exists."""
    try:
        import yaml
        identity = PROJECT_ROOT / "profile" / "identity.yaml"
        data = yaml.safe_load(identity.read_text())
        return bool(data and data.get("name", "").strip())
    except Exception:
        return False


def launch_onboarding():
    """Start the feedback server and open the onboarding wizard."""
    print("No profile found. Starting onboarding wizard...\n")
    if not _health_check():
        subprocess.Popen(
            [_python(), str(SCRIPT_DIR / "feedback_server.py")],
            cwd=str(PROJECT_ROOT),
        )
        time.sleep(1)

    url = "http://localhost:9847/"
    webbrowser.open(url)
    print(f"Complete the onboarding wizard at: {url}")
    print("Then re-run this script to generate your first newspaper.")
    sys.exit(0)


def fetch_content(content_dir: Path, script: str, extra_args: list[str] | None = None):
    """Run a fetcher script. Returns (name, success)."""
    name = Path(script).stem
    args = [_python(), script] + (extra_args or [])
    try:
        _run(args, capture_output=True, timeout=120)
        return name, True
    except Exception as exc:
        print(f"  WARNING: {name} failed ({exc}), continuing with empty data")
        return name, False


def fetch_all_parallel(content_dir: Path):
    """Fetch RSS, jobs, and events in parallel."""
    print("[1-3/10] Fetching RSS feeds, job listings, and events in parallel...")
    tasks = [
        (
            str(PROJECT_ROOT / "skills" / "web-scraper" / "scripts" / "fetch_rss.py"),
            ["--config", str(PROJECT_ROOT / "profile" / "sources.yaml"),
             "--output", str(content_dir / "rss.json")],
        ),
        (
            str(PROJECT_ROOT / "skills" / "web-scraper" / "scripts" / "fetch_jobs.py"),
            ["--config", str(PROJECT_ROOT / "profile" / "sources.yaml"),
             "--interests", str(PROJECT_ROOT / "profile" / "interests.yaml"),
             "--output", str(content_dir / "jobs.json")],
        ),
        (
            str(PROJECT_ROOT / "skills" / "web-scraper" / "scripts" / "fetch_events.py"),
            ["--config", str(PROJECT_ROOT / "profile" / "sources.yaml"),
             "--output", str(content_dir / "events.json")],
        ),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fetch_content, content_dir, s, a): s for s, a in tasks}
        for future in as_completed(futures):
            name, ok = future.result()
    print("  All fetchers complete.")


def ingest_github_feedback():
    print("[5/8] Ingesting GitHub feedback issues...")
    try:
        _run([_python(), str(SCRIPT_DIR / "ingest_github_feedback.py")],
             check=True, capture_output=True, timeout=30)
    except Exception:
        print("  WARNING: GitHub feedback ingestion failed, continuing")


def analyze_feedback():
    print("[6/8] Analyzing feedback...")
    feedback_file = PROJECT_ROOT / "memory" / "feedback.jsonl"
    if feedback_file.is_file():
        try:
            _run([_python(), str(SCRIPT_DIR / "analyze_feedback.py")],
                 check=True, capture_output=True, timeout=30)
        except Exception:
            print("  WARNING: Feedback analysis failed, using defaults")
    else:
        print("  No feedback yet — skipping.")


def render_newspaper(content_dir: Path, output_file: Path):
    print("[6/8] Rendering newspaper...")
    _run([
        _python(),
        str(PROJECT_ROOT / "skills" / "daily-newspaper" / "scripts" / "render_newspaper.py"),
        "--profile-dir", str(PROJECT_ROOT / "profile"),
        "--content-dir", str(content_dir),
        "--output", str(output_file),
    ], check=True)


def start_feedback_server():
    print("[7/8] Starting feedback server...")
    if _health_check():
        print("  Feedback server already running.")
    else:
        proc = subprocess.Popen(
            [_python(), str(SCRIPT_DIR / "feedback_server.py")],
            cwd=str(PROJECT_ROOT),
        )
        print(f"  Feedback server started (PID {proc.pid}).")


def register_artifact(today: str):
    print("[8/8] Registering artifact...")
    _run([
        _python(),
        str(PROJECT_ROOT / "skills" / "memory-manager" / "scripts" / "register_artifact.py"),
        "--type", "daily-newspaper",
        "--path", f"output/daily/{today}.html",
        "--sections", "news,jobs,events",
        "--item-count", "0",
        "--sources", "rss,jobs,events",
    ])
    _run([
        _python(),
        str(PROJECT_ROOT / "skills" / "memory-manager" / "scripts" / "log_action.py"),
        "--action", "artifact_generated",
        "--detail", f"Daily newspaper for {today}",
    ])


def cleanup_old_temp(today: str):
    """Remove temp content dirs older than 3 days (best-effort)."""
    tmp = Path(tempfile.gettempdir())
    cutoff = time.time() - 3 * 86400
    for entry in tmp.glob("pm_daily_*"):
        if entry.name == f"pm_daily_{today}":
            continue
        if not entry.is_dir():
            continue
        try:
            if entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            pass


def git_push(today: str):
    """Commit and push today's newspaper (if inside a git repo)."""
    print("[10] Pushing to GitHub...")
    try:
        _run(["git", "rev-parse", "--is-inside-work-tree"],
             check=True, capture_output=True)
    except Exception:
        print("  Not a git repo — skipping.")
        return

    _run(["git", "add", f"output/daily/{today}.html"])
    result = _run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("  No new changes to push.")
        return

    _run(["git", "commit", "-m", f"Daily newspaper {today}"])
    # Rebase on the remote first so a remote that is ahead (e.g. a push from
    # another machine) doesn't reject the push with "fetch first". --autostash
    # protects any unrelated uncommitted changes in the working tree.
    pull = _run(["git", "pull", "--rebase", "--autostash", "origin", "main"])
    if pull.returncode != 0:
        print("  WARNING: git pull --rebase failed")
    result = _run(["git", "push", "origin", "main"])
    if result.returncode == 0:
        print("  Pushed to GitHub.")
    else:
        print("  WARNING: git push failed.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    _activate_venv()
    _load_dotenv()

    if not check_profile():
        launch_onboarding()

    today = datetime.now().strftime("%Y-%m-%d")
    content_dir = Path(tempfile.gettempdir()) / f"pm_daily_{today}"
    output_file = PROJECT_ROOT / "output" / "daily" / f"{today}.html"

    print("=== PersonalMentor Daily Newspaper ===")
    print(f"Date: {today}")
    print(f"Project: {PROJECT_ROOT}")
    print()

    # Step 1: Create working directories
    content_dir.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "output" / "daily").mkdir(parents=True, exist_ok=True)

    # Steps 2-4: Parallel fetchers
    fetch_all_parallel(content_dir)

    # Step 5: GitHub feedback
    ingest_github_feedback()

    # Step 6: Analyze feedback
    analyze_feedback()

    # Step 7: Render
    render_newspaper(content_dir, output_file)

    # Step 8: Feedback server
    start_feedback_server()

    # Step 9: Register artifact
    register_artifact(today)

    # Cleanup old temp dirs
    cleanup_old_temp(today)
    print(f"DEBUG: Content dir preserved at {content_dir}")

    # Push to GitHub
    git_push(today)

    print()
    print("=== Done ===")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
