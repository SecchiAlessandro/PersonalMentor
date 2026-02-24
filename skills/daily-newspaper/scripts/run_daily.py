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
from datetime import datetime, timedelta
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


def fetch_calendar(content_dir: Path, today: str, tomorrow: str) -> str | None:
    """Fetch Google Calendar via gog CLI. Returns render arg or None."""
    print("[4/10] Fetching calendar (gog)...")
    gog = shutil.which("gog")
    if not gog:
        install_hint = (
            "brew install steipete/tap/gogcli" if platform.system() == "Darwin"
            else "See https://github.com/steipete/gogcli for install instructions"
        )
        print(f"  gog not installed — skipping. Install: {install_hint}")
        return None

    gog_out = content_dir / "gog_calendar.json"
    try:
        result = _run(
            [gog, "calendar", "events", "primary",
             "--from", f"{today}T00:00:00Z",
             "--to", f"{tomorrow}T23:59:59Z",
             "--json"],
            capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError("gog returned non-zero")
        gog_out.write_bytes(result.stdout)
        size = gog_out.stat().st_size
        print(f"  Calendar fetched ({size} bytes).")
        # Debug: first 500 chars
        preview = result.stdout[:500].decode(errors="replace")
        for line in preview.splitlines():
            print(f"    {line}")
    except Exception:
        print("  WARNING: gog calendar fetch failed (OAuth not configured?)")
        if gog_out.exists():
            gog_out.unlink()
        return None

    # Parse gog output
    parsed = content_dir / "calendar.json"
    try:
        _run(
            [_python(), str(SCRIPT_DIR / "parse_gog.py"),
             "--calendar-in", str(gog_out),
             "--calendar-out", str(parsed)],
            check=True, capture_output=True,
        )
    except Exception:
        print("  WARNING: gog parse failed")
        return None

    if parsed.is_file():
        return str(parsed)
    return None


def generate_german(content_dir: Path, today: str) -> str | None:
    """Generate German Sentence of the Day. Returns render arg or None."""
    print("[5/10] Generating German Sentence of the Day...")
    german_out = content_dir / "german.json"
    try:
        _run(
            [_python(), str(SCRIPT_DIR / "generate_german.py"),
             "--output", str(german_out),
             "--date", today],
            check=True, timeout=60,
        )
        return str(german_out)
    except Exception:
        print("  WARNING: German sentence generation failed (GEMINI_API_KEY set?)")
        return None


def ingest_github_feedback():
    print("[6/10] Ingesting GitHub feedback issues...")
    try:
        _run([_python(), str(SCRIPT_DIR / "ingest_github_feedback.py")],
             check=True, capture_output=True, timeout=30)
    except Exception:
        print("  WARNING: GitHub feedback ingestion failed, continuing")


def analyze_feedback():
    print("[7/10] Analyzing feedback...")
    feedback_file = PROJECT_ROOT / "memory" / "feedback.jsonl"
    if feedback_file.is_file():
        try:
            _run([_python(), str(SCRIPT_DIR / "analyze_feedback.py")],
                 check=True, capture_output=True, timeout=30)
        except Exception:
            print("  WARNING: Feedback analysis failed, using defaults")
    else:
        print("  No feedback yet — skipping.")


def render_newspaper(content_dir: Path, output_file: Path,
                     calendar_json: str | None, german_json: str | None):
    print("[8/10] Rendering newspaper...")
    args = [
        _python(),
        str(PROJECT_ROOT / "skills" / "daily-newspaper" / "scripts" / "render_newspaper.py"),
        "--profile-dir", str(PROJECT_ROOT / "profile"),
        "--content-dir", str(content_dir),
        "--output", str(output_file),
    ]
    if calendar_json:
        args += ["--calendar-json", calendar_json]
    if german_json:
        args += ["--german-json", german_json]
    _run(args, check=True)


def start_feedback_server():
    print("[9/10] Starting feedback server...")
    if _health_check():
        print("  Feedback server already running.")
    else:
        proc = subprocess.Popen(
            [_python(), str(SCRIPT_DIR / "feedback_server.py")],
            cwd=str(PROJECT_ROOT),
        )
        print(f"  Feedback server started (PID {proc.pid}).")


def register_artifact(today: str):
    print("[10/10] Registering artifact...")
    _run([
        _python(),
        str(PROJECT_ROOT / "skills" / "memory-manager" / "scripts" / "register_artifact.py"),
        "--type", "daily-newspaper",
        "--path", f"output/daily/{today}.html",
        "--sections", "news,jobs,events,calendar-events,german-sentence",
        "--item-count", "0",
        "--sources", "rss,jobs,events,calendar,gemini",
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
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
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

    # Step 5: Calendar
    calendar_json = fetch_calendar(content_dir, today, tomorrow)

    # Step 6: German sentence
    german_json = generate_german(content_dir, today)

    # Step 7: GitHub feedback
    ingest_github_feedback()

    # Step 8: Analyze feedback
    analyze_feedback()

    # Step 9: Render
    render_newspaper(content_dir, output_file, calendar_json, german_json)

    # Step 10: Feedback server
    start_feedback_server()

    # Step 11: Register artifact
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
