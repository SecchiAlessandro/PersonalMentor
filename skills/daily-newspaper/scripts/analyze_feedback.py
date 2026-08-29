#!/usr/bin/env python3
"""Analyze accumulated feedback and update learned-preferences.yaml.

Reads memory/feedback.jsonl and distills two signals into
memory/learned-preferences.yaml so the next render reflects user preferences:
the free-text comment on each edition, and the per-item 👍/👎 the reader
clicked while reading. Both are generalised by Gemini into topic and source
weights — a thumbs-down lowers a score, it never blocks a URL outright.
"""

import concurrent.futures
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
FEEDBACK_FILE = os.path.join(PROJECT_ROOT, "memory", "feedback.jsonl")
PREFS_FILE = os.path.join(PROJECT_ROOT, "memory", "learned-preferences.yaml")

# Items shown per section: 2-7, scaled by ratings (see determine_item_counts)
DEFAULT_ITEM_COUNT = 3
MIN_ITEM_COUNT = 2
MAX_ITEM_COUNT = 7

# Gemini comment analysis (same conventions as generate_german.py)
TEXT_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite"]
API_TIMEOUT = 60  # seconds per API call

# Thresholds
HIGH_RATING_THRESHOLD = 4.0  # sections rated >= this get more items
LOW_RATING_THRESHOLD = 2.0   # sections rated <= this get fewer items

ALL_SECTIONS = ["news", "events"]


FEEDBACK_WINDOW_DAYS = 30
MAX_RECENT_VOTES = 40  # voted items carried into the distillation prompt


def load_feedback():
    """Load feedback entries from the last FEEDBACK_WINDOW_DAYS days."""
    entries = []
    if not os.path.exists(FEEDBACK_FILE):
        return entries
    cutoff = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    from datetime import timedelta
    cutoff = cutoff - timedelta(days=FEEDBACK_WINDOW_DAYS)
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", "")
                if ts:
                    try:
                        entry_dt = datetime.fromisoformat(ts)
                        if entry_dt.tzinfo is None:
                            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
                        if entry_dt < cutoff:
                            continue
                    except ValueError:
                        pass
                entries.append(entry)
            except json.JSONDecodeError:
                continue
    return entries


def load_prefs():
    """Load existing learned-preferences.yaml."""
    if not os.path.exists(PREFS_FILE):
        return {}
    with open(PREFS_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _format_votes(votes):
    """Group voted items into LIKED / DISLIKED blocks for the prompt."""
    lines = []
    for label, wanted in (("LIKED", "like"), ("DISLIKED", "dislike")):
        picked = [v for v in votes if v.get("vote") == wanted]
        if not picked:
            continue
        lines.append(f"{label}:")
        for v in picked:
            where = f"{v.get('section', '')}/{v.get('track', '')}".strip("/")
            source = v.get("source", "")
            suffix = f" — {source}" if source else ""
            lines.append(f"- [{where}] {v.get('title', '')}{suffix}")
    return "\n".join(lines)


def analyze_feedback_with_gemini(comments, votes):
    """Distill written feedback and per-item 👍/👎 into content preferences.

    `votes` are the items the reader gave a thumbs up/down while reading. They
    are handed to the model as *examples of the kind of item* wanted more or
    less of — never as a blocklist: the output is topic and source weights, so
    a disliked article can still appear tomorrow if it is genuinely the most
    relevant thing available.

    Returns a dict with liked_topics / disliked_topics / preferred_sources /
    ignored_sources lists, or None when analysis is unavailable (no API key,
    SDK missing, or all models failed). Callers must treat None as "leave
    existing preferences untouched" — the pipeline stays non-fatal.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("  WARNING: GEMINI_API_KEY not set — skipping comment analysis.")
        return None
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("  WARNING: google-genai not installed — skipping comment analysis.")
        return None

    client = genai.Client(api_key=api_key)

    sections = []
    if comments:
        comment_block = "\n".join(
            f"- [{c.get('date', '')}] {c.get('comment', '')}" for c in comments
        )
        sections.append(
            "Their recent written feedback, newest last:\n\n" + comment_block
        )
    if votes:
        sections.append(
            "They also gave a thumbs up or down on individual items:\n\n"
            + _format_votes(votes)
        )
    feedback_block = "\n\n".join(sections)

    prompt = f"""You curate a personal daily newspaper for one reader. It has two sections, news and events, each split into an energy track and an AI & tech track.

{feedback_block}

Distill this into content preferences. Respond in EXACTLY this JSON format (no markdown, no code fences):
{{"liked_topics": [], "disliked_topics": [], "preferred_sources": [], "ignored_sources": []}}

Rules:
- Topics are short lowercase keyword phrases (1-3 words) suitable for whole-word matching against article titles, e.g. "hvdc", "grid", "energy storage" — not full sentences
- For thumbed items, generalise to the KIND of item — its topic, theme or format — never the specific article. A thumbs-down on one funding announcement means "less funding news", not "block that headline"
- Only include a source when the reader named a publication in writing, or when SEVERAL thumbed-down items came from that same source. One bad item is not enough to ignore a whole source
- Only extract preferences the reader actually expressed; leave lists empty rather than guessing
- Newer feedback overrides older feedback if they conflict"""

    last_error = None
    for model in TEXT_MODELS:
        try:
            print(f"  Trying model: {model}")
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(
                client.models.generate_content,
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    temperature=0.2,
                ),
            )
            try:
                response = future.result(timeout=API_TIMEOUT)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)

            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                if text.endswith("```"):
                    text = text[:-3].strip()

            data = json.loads(text)
            result = {}
            for key in ("liked_topics", "disliked_topics",
                        "preferred_sources", "ignored_sources"):
                values = data.get(key, [])
                if not isinstance(values, list):
                    values = []
                result[key] = [str(v).strip().lower() for v in values if str(v).strip()]
            return result
        except concurrent.futures.TimeoutError:
            last_error = TimeoutError(f"API call timed out after {API_TIMEOUT}s")
            print(f"  WARNING: {model} timed out after {API_TIMEOUT}s", file=sys.stderr)
            continue
        except Exception as e:
            last_error = e
            print(f"  WARNING: {model} failed: {e}", file=sys.stderr)
            continue

    print(f"  WARNING: all models failed for comment analysis. Last error: {last_error}",
          file=sys.stderr)
    return None


def compute_averages(entries):
    """Compute per-section and overall averages from feedback entries."""
    section_totals = defaultdict(list)
    overall_ratings = []

    for entry in entries:
        rating = entry.get("rating")
        if rating is not None:
            overall_ratings.append(float(rating))

        section_ratings = entry.get("section_ratings", {})
        for section, value in section_ratings.items():
            if value is not None:
                section_totals[section].append(float(value))

    section_avgs = {}
    for section, values in section_totals.items():
        section_avgs[section] = round(sum(values) / len(values), 2)

    overall_avg = round(sum(overall_ratings) / len(overall_ratings), 2) if overall_ratings else None

    return overall_avg, section_avgs


def determine_item_counts(section_avgs, overall_avg=None):
    """Determine per-section item counts based on average ratings.

    The feedback form collects a single overall rating (no per-section
    stars), so sections without their own average fall back to the overall
    average rather than the static default.
    """
    counts = {}
    for section in ALL_SECTIONS:
        avg = section_avgs.get(section)
        if avg is None:
            avg = overall_avg
        if avg is None:
            counts[section] = DEFAULT_ITEM_COUNT
        elif avg >= HIGH_RATING_THRESHOLD:
            # Scale: 4.0 -> 4 items, 5.0 -> 5 items
            counts[section] = min(MAX_ITEM_COUNT, DEFAULT_ITEM_COUNT + int(avg - 3))
        elif avg <= LOW_RATING_THRESHOLD:
            # Scale: 2.0 -> 2 items, 1.0 -> 1 item
            counts[section] = max(MIN_ITEM_COUNT, int(avg))
        else:
            counts[section] = DEFAULT_ITEM_COUNT
    return counts


def determine_section_preferences(section_avgs):
    """Determine preferred and skipped sections (only considers active sections)."""
    preferred = []
    skipped = []
    for section, avg in section_avgs.items():
        if section not in ALL_SECTIONS:
            continue
        if avg >= HIGH_RATING_THRESHOLD:
            preferred.append(section)
        elif avg <= LOW_RATING_THRESHOLD:
            skipped.append(section)
    return sorted(preferred), sorted(skipped)


def update_preferences(entries, overall_avg, section_avgs):
    """Update learned-preferences.yaml with computed values."""
    prefs = load_prefs()

    item_counts = determine_item_counts(section_avgs, overall_avg)
    preferred, skipped = determine_section_preferences(section_avgs)

    # Update content_preferences (preserve existing liked/disliked topics)
    if "content_preferences" not in prefs:
        prefs["content_preferences"] = {}
    cp = prefs["content_preferences"]
    cp.setdefault("liked_topics", [])
    cp.setdefault("disliked_topics", [])
    cp.setdefault("preferred_sources", [])
    cp.setdefault("ignored_sources", [])
    cp.setdefault("recent_votes", [])

    # Collect recent written feedback so it is considered going forward
    recent_comments = [
        {"date": e.get("date", ""), "comment": e.get("comment", "").strip()}
        for e in entries
        if e.get("comment", "").strip()
    ]
    cp["recent_comments"] = recent_comments[-10:]

    # Collect the per-item 👍/👎 the reader clicked while reading. These are
    # examples of the kind of item wanted more or less of, not a blocklist.
    recent_votes = [
        {
            "vote": v.get("vote", ""),
            "section": v.get("section", ""),
            "track": v.get("track", ""),
            "source": v.get("source", ""),
            "title": v.get("title", ""),
        }
        for e in entries
        for v in (e.get("item_votes") or [])
        if v.get("vote") in ("like", "dislike") and v.get("title", "").strip()
    ]
    cp["recent_votes"] = recent_votes[-MAX_RECENT_VOTES:]

    # Distill comments and votes into topic/source preferences via Gemini. The
    # hash skips the API call when neither has changed since the last
    # successful analysis; on failure the hash is left stale so the next run
    # retries. No feedback at all → leave existing preferences untouched
    # (a quiet week shouldn't wipe what was learned).
    if cp["recent_comments"] or cp["recent_votes"]:
        digest = "\n".join(
            [c["comment"] for c in cp["recent_comments"]]
            + [f"{v['vote']}|{v['source']}|{v['title']}" for v in cp["recent_votes"]]
        )
        comments_hash = hashlib.sha256(digest.encode("utf-8")).hexdigest()
        if cp.get("comments_hash") == comments_hash:
            print("  Feedback unchanged since last analysis — skipping Gemini call.")
        else:
            derived = analyze_feedback_with_gemini(
                cp["recent_comments"], cp["recent_votes"]
            )
            if derived is not None:
                cp["liked_topics"] = derived["liked_topics"]
                cp["disliked_topics"] = derived["disliked_topics"]
                cp["preferred_sources"] = derived["preferred_sources"]
                cp["ignored_sources"] = derived["ignored_sources"]
                cp["comments_hash"] = comments_hash
                print(f"  Learned from feedback: liked={cp['liked_topics']} "
                      f"disliked={cp['disliked_topics']}")

    # Update reading_patterns
    if "reading_patterns" not in prefs:
        prefs["reading_patterns"] = {}
    rp = prefs["reading_patterns"]
    rp["preferred_sections"] = preferred
    rp["skipped_sections"] = skipped
    rp["section_item_counts"] = item_counts

    # Update feedback stats
    if overall_avg is not None:
        prefs["overall_avg_rating"] = overall_avg
    prefs["total_feedback_count"] = len(entries)
    prefs["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Write back
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(prefs, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return prefs


def main():
    entries = load_feedback()

    if not entries:
        print("No feedback entries found. Nothing to analyze.")
        return

    overall_avg, section_avgs = compute_averages(entries)

    vote_count = sum(len(e.get("item_votes") or []) for e in entries)
    print(f"Analyzing {len(entries)} feedback entries ({vote_count} item votes)...")
    if overall_avg is not None:
        print(f"  Overall average rating: {overall_avg}/5")
    for section, avg in sorted(section_avgs.items()):
        print(f"  {section}: {avg}/5")

    prefs = update_preferences(entries, overall_avg, section_avgs)

    item_counts = prefs.get("reading_patterns", {}).get("section_item_counts", {})
    print(f"\nUpdated {PREFS_FILE}")
    print(f"  Section item counts: {item_counts}")
    print(f"  Preferred sections: {prefs.get('reading_patterns', {}).get('preferred_sections', [])}")
    print(f"  Skipped sections: {prefs.get('reading_patterns', {}).get('skipped_sections', [])}")


if __name__ == "__main__":
    main()
