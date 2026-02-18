#!/usr/bin/env python3
"""Onboarding handler for the PersonalMentor welcome wizard.

Processes form submissions from welcome.html and generates the 5 profile
YAML files. Plugs into feedback_server.py as route handlers.
"""

import base64
import json
import os
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
PROFILE_DIR = os.path.join(PROJECT_ROOT, "profile")
WELCOME_PAGE = os.path.join(PROJECT_ROOT, "output", "welcome.html")

# Paths to other skill scripts
EXTRACT_CV = os.path.join(PROJECT_ROOT, "skills", "profile-manager", "scripts", "extract_cv.py")
PARSE_PAGE = os.path.join(PROJECT_ROOT, "skills", "web-scraper", "scripts", "parse_page.py")
VALIDATE_PROFILE = os.path.join(PROJECT_ROOT, "skills", "profile-manager", "scripts", "validate_profile.py")
LOG_ACTION = os.path.join(PROJECT_ROOT, "skills", "memory-manager", "scripts", "log_action.py")

# Add skill script dirs to path for direct import
sys.path.insert(0, os.path.join(PROJECT_ROOT, "skills", "profile-manager", "scripts"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "skills", "web-scraper", "scripts"))


def _deep_merge(base, override):
    """Merge override into base, preferring non-empty override values."""
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        elif val not in (None, "", [], {}):
            base[key] = val
    return base


def _extract_cv_data(file_bytes, filename):
    """Decode base64 CV file, extract structured data."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in (".pdf", ".docx", ".doc"):
        return {}

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        from extract_cv import extract_cv
        data = extract_cv(tmp_path)
        # Remove raw_text before returning
        data.pop("raw_text", None)
        return data
    except Exception as e:
        print(f"CV extraction error: {e}", file=sys.stderr)
        return {}
    finally:
        os.unlink(tmp_path)


def _scrape_website(url):
    """Scrape a website URL and return structured data."""
    try:
        from parse_page import parse_page
        return parse_page(url)
    except Exception as e:
        print(f"Website scrape error: {e}", file=sys.stderr)
        return {"error": str(e)}


def _build_identity(data, cv_data):
    """Build identity.yaml content from form data + CV extraction."""
    identity = {
        "name": "",
        "title": "",
        "location": "",
        "bio": "",
        "contact": {
            "email": "",
            "linkedin": "",
            "website": "",
            "github": "",
        },
    }

    # Layer CV-extracted data first
    cv_identity = cv_data.get("identity", {})
    _deep_merge(identity, cv_identity)

    # Form data overrides everything
    if data.get("name"):
        identity["name"] = data["name"]
    if data.get("title"):
        identity["title"] = data["title"]
    if data.get("location"):
        identity["location"] = data["location"]
    if data.get("email"):
        identity["contact"]["email"] = data["email"]
    if data.get("bio"):
        identity["bio"] = data["bio"]
    if data.get("website"):
        identity["contact"]["website"] = data["website"]
    if data.get("linkedin"):
        identity["contact"]["linkedin"] = data["linkedin"]
    if data.get("github"):
        identity["contact"]["github"] = data["github"]

    return identity


def _build_experience(data, cv_data):
    """Build experience.yaml content."""
    experience = {
        "work_history": [],
        "education": [],
        "projects": [],
        "skills": {
            "technical": [],
            "languages": [],
            "tools": [],
            "soft_skills": [],
        },
    }

    # Use CV-extracted data as base
    cv_exp = cv_data.get("experience", {})
    if cv_exp.get("work_history"):
        experience["work_history"] = cv_exp["work_history"]
    if cv_exp.get("education"):
        experience["education"] = cv_exp["education"]
    if cv_exp.get("skills", {}).get("technical"):
        experience["skills"]["technical"] = cv_exp["skills"]["technical"]

    return experience


def _build_interests(data):
    """Build interests.yaml content from form data."""
    topics = data.get("topics", [])
    industries = data.get("industries", [])

    professional = []
    for i, topic in enumerate(topics):
        professional.append({"topic": topic, "weight": max(10 - i, 5)})

    job_search = {
        "active": data.get("job_search_active", False),
        "target_roles": data.get("target_roles", []),
        "preferred_companies": data.get("preferred_companies", []),
        "target_locations": data.get("target_locations", []),
        "salary_range": "",
    }

    return {
        "professional": professional,
        "industries": industries,
        "personal": data.get("personal_interests", []),
        "job_search": job_search,
    }


def _build_preferences(data):
    """Build preferences.yaml content from form data."""
    return {
        "design": {
            "theme": data.get("theme", "modern-minimalist"),
            "colors": [],
        },
        "writing": {
            "tone": data.get("tone", "conversational"),
            "length": "concise",
            "language": data.get("language", "en"),
        },
        "daily_artifact": {
            "delivery_time": data.get("delivery_time", "07:00"),
            "sections_enabled": [
                "top-stories",
                "jobs-for-you",
                "todays-calendar",
                "german-sentence",
                "events-near-you",
                "skill-spotlight",
                "industry-pulse",
                "reading-list",
            ],
            "max_items_per_section": 5,
        },
    }


def _build_sources(data):
    """Build sources.yaml content from form data."""
    # Start with defaults if user selected them
    rss_feeds = []
    job_boards = []
    event_sources = []

    for feed in data.get("rss_feeds", []):
        rss_feeds.append({"url": feed["url"], "category": feed.get("category", "general")})

    for board in data.get("job_boards", []):
        entry = {"url": board["url"], "type": board.get("type", "html"), "site": board.get("site", "")}
        if board.get("search_terms"):
            entry["search_terms"] = board["search_terms"]
        if board.get("filter_keywords"):
            entry["filter_keywords"] = board["filter_keywords"]
        job_boards.append(entry)

    for source in data.get("event_sources", []):
        event_sources.append({"url": source["url"], "location_filter": source.get("location_filter", "")})

    return {
        "rss_feeds": rss_feeds,
        "job_boards": job_boards,
        "event_sources": event_sources,
    }


def _write_yaml(filepath, data, comment=""):
    """Write data to a YAML file with an optional header comment."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        if comment:
            f.write(f"# {comment}\n\n")
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


def _log_action(action, detail):
    """Log via log_action.py (best-effort)."""
    try:
        subprocess.run(
            [sys.executable, LOG_ACTION, "--action", action, "--detail", detail],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def _validate_profile():
    """Run validate_profile.py and return (ok, errors)."""
    try:
        result = subprocess.run(
            [sys.executable, VALIDATE_PROFILE],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)


def handle_onboard(handler):
    """Process POST /api/onboard — create all 5 profile YAML files."""
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(length)
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        handler._send_json(400, {"error": "invalid JSON"})
        return

    # Validate required field
    if not data.get("name", "").strip():
        handler._send_json(400, {"error": "Name is required"})
        return

    # Extract CV data if provided
    cv_data = {}
    if data.get("cv_file") and data.get("cv_filename"):
        try:
            file_bytes = base64.b64decode(data["cv_file"])
            cv_data = _extract_cv_data(file_bytes, data["cv_filename"])
        except Exception as e:
            print(f"CV decode error: {e}", file=sys.stderr)

    # Scrape website if provided
    website_data = {}
    if data.get("website"):
        website_data = _scrape_website(data["website"])

    # Enrich bio from website if not provided by user
    if not data.get("bio") and website_data.get("description"):
        data["bio"] = website_data["description"]

    # Build all 5 profile files
    identity = _build_identity(data, cv_data)
    experience = _build_experience(data, cv_data)
    interests = _build_interests(data)
    preferences = _build_preferences(data)
    sources = _build_sources(data)

    # Write YAML files
    _write_yaml(os.path.join(PROFILE_DIR, "identity.yaml"), identity, "PersonalMentor — User Identity")
    _write_yaml(os.path.join(PROFILE_DIR, "experience.yaml"), experience, "PersonalMentor — Experience & Skills")
    _write_yaml(os.path.join(PROFILE_DIR, "interests.yaml"), interests, "PersonalMentor — Interests & Topics")
    _write_yaml(os.path.join(PROFILE_DIR, "preferences.yaml"), preferences, "PersonalMentor — User Preferences")
    _write_yaml(os.path.join(PROFILE_DIR, "sources.yaml"), sources, "PersonalMentor — Content Sources")

    # Validate
    valid, output = _validate_profile()

    # Log action
    _log_action("onboarding", f"Profile created for {identity['name']}")

    delivery = preferences["daily_artifact"]["delivery_time"]
    handler._send_json(200, {
        "status": "ok",
        "message": f"Profile created for {identity['name']}",
        "delivery_time": delivery,
        "valid": valid,
        "validation_output": output,
    })


def handle_scrape_website(handler):
    """Process POST /api/scrape-website — return scraped website data."""
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(length)
        data = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        handler._send_json(400, {"error": "invalid JSON"})
        return

    url = data.get("url", "").strip()
    if not url:
        handler._send_json(400, {"error": "URL is required"})
        return

    result = _scrape_website(url)
    if result.get("error"):
        handler._send_json(502, {"error": f"Failed to fetch: {result['error']}"})
    else:
        handler._send_json(200, {"status": "ok", "data": result})


RUN_DAILY = os.path.join(PROJECT_ROOT, "skills", "daily-newspaper", "scripts", "run_daily.sh")


def handle_generate(handler):
    """Process POST /api/generate — trigger newspaper generation in background."""
    try:
        proc = subprocess.Popen(
            ["bash", RUN_DAILY],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=PROJECT_ROOT,
        )
        # Wait up to 300s for it to finish
        try:
            output, _ = proc.communicate(timeout=480)
        except subprocess.TimeoutExpired:
            proc.kill()
            handler._send_json(504, {"error": "Generation timed out after 480s"})
            return

        if proc.returncode == 0:
            # Find today's newspaper file
            from datetime import date
            today = date.today().isoformat()
            newspaper_path = f"output/daily/{today}.html"
            handler._send_json(200, {
                "status": "ok",
                "message": f"Newspaper generated for {today}",
                "path": newspaper_path,
            })
        else:
            handler._send_json(500, {
                "error": "Generation failed",
                "output": output[-2000:] if output else "",
            })
    except Exception as e:
        handler._send_json(500, {"error": str(e)})


def serve_welcome_page(handler):
    """Serve GET / — the welcome/onboarding page."""
    if not os.path.exists(WELCOME_PAGE):
        handler._send_json(404, {"error": "welcome.html not found"})
        return

    with open(WELCOME_PAGE, "r") as f:
        html = f.read()

    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(html.encode("utf-8"))
