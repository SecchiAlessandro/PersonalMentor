#!/usr/bin/env python3
"""Render the PersonalMentor daily newspaper HTML from collected content."""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "..", "assets", "template.html")
LEARNED_PREFS_PATH = os.path.join(PROJECT_ROOT, "memory", "learned-preferences.yaml")

# Day-over-day novelty: news/event items shown on a previous day within this
# window are pushed to the back, so each edition differs from recent ones.
SEEN_PATH = os.path.join(PROJECT_ROOT, "memory", "seen-items.json")
NOVELTY_WINDOW_DAYS = 7   # suppress repeats shown in the last N days
SEEN_RETENTION_DAYS = 45  # forget shown-history older than this

# Default theme (Modern Minimalist) — overridden by user preference
DEFAULT_THEME = {
    "bg": "#ffffff",
    "surface": "#f8f9fa",
    "primary": "#2d2d2d",
    "secondary": "#555555",
    "accent": "#0066cc",
    "text": "#1a1a1a",
    "text_muted": "#6b7280",
    "border": "#e5e7eb",
    "font_heading": "'Georgia', serif",
    "font_body": "'Helvetica Neue', 'Arial', sans-serif",
}

# Theme-factory color mappings (subset for common themes)
THEMES = {
    "ocean-depths": {
        "bg": "#f1faee", "surface": "#ffffff", "primary": "#1a2332",
        "secondary": "#2d8b8b", "accent": "#2d8b8b", "text": "#1a2332",
        "text_muted": "#5a6b7a", "border": "#d1dce5",
        "font_heading": "'Georgia', serif", "font_body": "'Source Sans Pro', sans-serif",
    },
    "sunset-boulevard": {
        "bg": "#fffaf5", "surface": "#ffffff", "primary": "#8b2500",
        "secondary": "#d4652f", "accent": "#e8943a", "text": "#2d1810",
        "text_muted": "#8b6f60", "border": "#f0ddd0",
        "font_heading": "'Playfair Display', serif", "font_body": "'Lato', sans-serif",
    },
    "forest-canopy": {
        "bg": "#f5f7f2", "surface": "#ffffff", "primary": "#2d5016",
        "secondary": "#5a8a3c", "accent": "#7ab648", "text": "#1a2e0d",
        "text_muted": "#6b7a60", "border": "#d5e0cc",
        "font_heading": "'Merriweather', serif", "font_body": "'Open Sans', sans-serif",
    },
    "modern-minimalist": DEFAULT_THEME,
    "golden-hour": {
        "bg": "#faf6f0", "surface": "#ffffff", "primary": "#5c4033",
        "secondary": "#b8860b", "accent": "#daa520", "text": "#2d2017",
        "text_muted": "#8b7355", "border": "#e8dcc8",
        "font_heading": "'Libre Baskerville', serif", "font_body": "'Nunito', sans-serif",
    },
    "arctic-frost": {
        "bg": "#f0f4f8", "surface": "#ffffff", "primary": "#1e3a5f",
        "secondary": "#4a90d9", "accent": "#7eb8da", "text": "#1a2a3a",
        "text_muted": "#6b8299", "border": "#d0dce8",
        "font_heading": "'Raleway', serif", "font_body": "'Roboto', sans-serif",
    },
    "desert-rose": {
        "bg": "#faf5f2", "surface": "#ffffff", "primary": "#8b5e6b",
        "secondary": "#c4868f", "accent": "#d4a0a7", "text": "#3d2830",
        "text_muted": "#9b7a82", "border": "#e8d5d8",
        "font_heading": "'Cormorant Garamond', serif", "font_body": "'Poppins', sans-serif",
    },
    "tech-innovation": {
        "bg": "#0d1117", "surface": "#161b22", "primary": "#58a6ff",
        "secondary": "#3fb950", "accent": "#58a6ff", "text": "#e6edf3",
        "text_muted": "#8b949e", "border": "#30363d",
        "font_heading": "'JetBrains Mono', monospace", "font_body": "'Inter', sans-serif",
    },
    "botanical-garden": {
        "bg": "#f7faf5", "surface": "#ffffff", "primary": "#2e6b3e",
        "secondary": "#5ba06e", "accent": "#88c999", "text": "#1a3320",
        "text_muted": "#6b8b72", "border": "#cde0d2",
        "font_heading": "'DM Serif Display', serif", "font_body": "'Work Sans', sans-serif",
    },
    "midnight-galaxy": {
        "bg": "#0f0f23", "surface": "#1a1a3e", "primary": "#9b59b6",
        "secondary": "#6c5ce7", "accent": "#a29bfe", "text": "#e8e0f0",
        "text_muted": "#8a82a6", "border": "#2d2d5e",
        "font_heading": "'Cinzel', serif", "font_body": "'Quicksand', sans-serif",
    },
    "clean-modern": {
        "bg": "#f9fafb", "surface": "#ffffff", "primary": "#1e293b",
        "secondary": "#0ea5e9", "accent": "#6366f1", "text": "#1e293b",
        "text_muted": "#64748b", "border": "#e2e8f0",
        "font_heading": "'Inter', sans-serif", "font_body": "'Inter', sans-serif",
    },
}

MAX_ITEMS = 3  # show the top 3 most relevant items per section (per topic track)

# Keyword sets used to classify a news article or event into one of two tracks:
# "energy" vs "ai" (AI & Tech). Matched whole-word, case-insensitive.
ENERGY_TERMS = [
    "energy", "power", "grid", "renewable", "renewables", "electricity",
    "electric", "hvdc", "statcom", "substation", "converter", "transmission",
    "battery", "storage", "solar", "wind", "hydro", "nuclear", "decarbonization",
    "decarbonisation", "energy transition", "power systems", "smart grid",
    "utility", "utilities", "entso-e", "entsoe", "iea", "irena", "iaee",
    "epex", "montel", "watt", "megawatt", "gigawatt", "emissions", "carbon",
]
AI_TECH_TERMS = [
    "ai", "artificial intelligence", "machine learning", "ml", "llm", "llms",
    "agent", "agents", "agentic", "gpt", "model", "models", "foundation model",
    "deep learning", "neural", "software", "startup", "startups", "chip",
    "chips", "gpu", "cloud", "data", "algorithm", "robot", "robotics",
    "openai", "anthropic", "deepmind", "nvidia", "developer", "app", "saas",
]

# Minimum distinct ENERGY_TERMS an event must hit to earn a spot in the energy
# events track. The word "energy" (or "power") alone appears incidentally in
# wellness and networking blurbs ("Energizing yoga flow", "CEO Energy Break"),
# so a single hit is too weak a signal. Genuine energy events mention several
# ("energy", "grid", "power", "utilities", ...). Requiring 2+ drops the false
# positives; a thin day then shows fewer real events instead of noise padding.
MIN_ENERGY_TERMS_FOR_EVENT = 2


def energy_term_count(item):
    """Count distinct ENERGY_TERMS whole-word-matched across an item's text."""
    text = " ".join(str(item.get(k, "")) for k in
                    ("title", "summary", "description", "location", "source")).lower()
    return sum(1 for t in ENERGY_TERMS if _word_match(t, text))


def first_sentence(text, max_len=160):
    """Return a single-sentence summary, trimmed to max_len characters."""
    if not text:
        return ""
    text = str(text)
    # Strip markdown emphasis/heading markers (common in Luma descriptions)
    text = re.sub(r"[*_`#]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"(.+?[.!?])(\s|$)", text)
    sentence = match.group(1) if match else text
    if len(sentence) > max_len:
        sentence = sentence[:max_len].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return sentence


def dedupe_by_title(items):
    """Drop items with duplicate titles, keeping first occurrence.

    Normalizes by lowercasing and stripping trailing parenthetical/bracketed
    suffixes so 'Product Academy SUMMIT (Zurich)' and 'Product Academy SUMMIT'
    collapse to one entry.
    """
    seen = set()
    result = []
    for item in items:
        title = item.get("title", "").lower().strip()
        title = re.sub(r"[\(\[].*?[\)\]]", "", title)  # drop (...) and [...]
        key = re.sub(r"\s+", " ", title).strip()
        if key and key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def diversify_by_source(items, source_key):
    """Reorder items so each distinct source appears once before any repeats.

    The input is assumed already ranked (by relevance or match score). A greedy
    first pass keeps the highest-ranked item from each distinct source, in rank
    order; remaining items (repeat sources) are appended afterwards. Slicing the
    result to the top N therefore prefers one-item-per-source, and only falls
    back to a repeated source when there aren't enough distinct ones to fill the
    section.
    """
    first_pass = []
    leftovers = []
    seen = set()
    for item in items:
        key = str(source_key(item) or "").lower().strip()
        if key and key in seen:
            leftovers.append(item)
            continue
        if key:
            seen.add(key)
        first_pass.append(item)
    return first_pass + leftovers


def _source_host(item):
    """Source host for an event (matches the label shown in render_events_html)."""
    source_url = item.get("source", "") or ""
    host = source_url.split("/")[2] if source_url.startswith("http") else source_url
    return host.replace("www.", "")


def _word_match(term, text):
    """True if term appears as a whole word in text (case-insensitive).

    Word-boundary matching avoids false positives like 'ai' inside
    'available'/'training' that naive substring matching would count.
    """
    term = str(term).strip().lower()
    if not term:
        return False
    return re.search(r"\b" + re.escape(term) + r"\b", text) is not None


def classify_topic(item):
    """Classify a news article or event into the "energy" or "ai" track.

    Articles carry a `category` field, which is the strongest signal:
    "energy" -> energy; "ai"/"tech" -> ai. Anything else (e.g. "news") and
    events (which have no category) fall through to whole-word keyword scoring
    over the item's text. Ties default to "ai".
    """
    category = str(item.get("category", "")).strip().lower()
    if category == "energy":
        return "energy"
    if category in ("ai", "tech"):
        return "ai"

    text = " ".join(str(item.get(k, "")) for k in
                    ("title", "summary", "description", "location", "source")).lower()
    energy_hits = sum(1 for t in ENERGY_TERMS if _word_match(t, text))
    ai_hits = sum(1 for t in AI_TECH_TERMS if _word_match(t, text))
    return "energy" if energy_hits > ai_hits else "ai"


def split_by_topic(items):
    """Split items into (energy_items, ai_items), preserving input order."""
    energy_items, ai_items = [], []
    for item in items:
        (energy_items if classify_topic(item) == "energy" else ai_items).append(item)
    return energy_items, ai_items


def relevance_score(text, interests, learned=None):
    """Score how relevant a piece of text is to the user's profile.

    Whole-word, case-insensitive matching against the profile's weighted
    topics, industries, target roles, and relevance keywords. A score of 0
    means the text matched no profile signal and is treated as off-profile.

    `learned` (content_preferences from learned-preferences.yaml, distilled
    from written feedback) additionally boosts liked topics and penalises
    disliked ones — a penalty can push an item to 0 and out of the edition.
    """
    text_l = text.lower()
    score = 0
    if learned:
        for topic in learned.get("liked_topics", []) or []:
            if _word_match(topic, text_l):
                score += 2
        for topic in learned.get("disliked_topics", []) or []:
            if _word_match(topic, text_l):
                score -= 3
    for t in interests.get("professional", []) or []:
        if _word_match(t.get("topic", ""), text_l):
            score += int(t.get("weight", 1))
    for ind in interests.get("industries", []) or []:
        if _word_match(ind, text_l):
            score += 2
    job_search = interests.get("job_search", {}) or {}
    for role in job_search.get("target_roles", []) or []:
        if _word_match(role, text_l):
            score += 3
    for kw in interests.get("relevance_keywords", []) or []:
        # Support either bare strings or {term, weight} mappings.
        if isinstance(kw, dict):
            term, weight = kw.get("term", ""), int(kw.get("weight", 2))
        else:
            term, weight = kw, 2
        if _word_match(term, text_l):
            score += weight
    return score


def _source_pref_adjust(source_text, learned):
    """Score adjustment from learned source preferences.

    Sources learned from feedback are free-form names ("techcrunch") while
    items carry hosts or URLs ("techcrunch.com"), so this matches by
    case-insensitive containment rather than whole words.
    """
    if not learned or not source_text:
        return 0
    source_l = str(source_text).lower()
    adjust = 0
    for src in learned.get("preferred_sources", []) or []:
        if src and str(src).lower() in source_l:
            adjust += 1
    for src in learned.get("ignored_sources", []) or []:
        if src and str(src).lower() in source_l:
            adjust -= 2
    return adjust


def rank_by_relevance(items, text_fn, interests, learned=None, source_fn=None):
    """Sort items by profile relevance and drop off-profile ones (score 0).

    Falls back to the relevance-ranked full list when nothing matches the
    profile, so a section is never left blank on a quiet news day.
    """
    def score(it):
        s = relevance_score(text_fn(it), interests, learned)
        if source_fn is not None:
            s += _source_pref_adjust(source_fn(it), learned)
        return s

    scored = sorted(items, key=score, reverse=True)
    relevant = [it for it in scored if score(it) > 0]
    return relevant if relevant else scored


def load_learned_preferences():
    """Load learned-preferences.yaml.

    Returns (section_item_counts, content_preferences) — the per-section
    item counts driven by ratings, and the topic/source preferences
    distilled from written feedback.
    """
    if not os.path.exists(LEARNED_PREFS_PATH):
        return {}, {}
    with open(LEARNED_PREFS_PATH, "r", encoding="utf-8") as f:
        prefs = yaml.safe_load(f) or {}
    return (
        prefs.get("reading_patterns", {}).get("section_item_counts", {}),
        prefs.get("content_preferences", {}) or {},
    )


def get_max_items(section, section_item_counts):
    """Get max items for a section, using learned preference or default."""
    return section_item_counts.get(section, MAX_ITEMS)


def _item_key(item):
    """Stable identity for an article/event, used to suppress day-over-day repeats."""
    url = str(item.get("url", "") or "").strip().lower()
    if url and url != "#":
        return url
    title = str(item.get("title", "") or "").lower()
    title = re.sub(r"[\(\[].*?[\)\]]", "", title)  # drop (...) / [...] suffixes
    return re.sub(r"\s+", " ", title).strip()


def load_seen(path=SEEN_PATH):
    """Load the shown-history map {item_key: 'YYYY-MM-DD' last shown}."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_seen(seen, path=SEEN_PATH):
    """Persist the shown-history map."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(seen, f, sort_keys=True)


def _days_between(d_from, d_to):
    """Whole days from ISO date d_from to d_to; None if unparseable."""
    try:
        a = datetime.strptime(d_from, "%Y-%m-%d").date()
        b = datetime.strptime(d_to, "%Y-%m-%d").date()
        return (b - a).days
    except (ValueError, TypeError):
        return None


def prioritize_unseen(items, seen, today, days=NOVELTY_WINDOW_DAYS):
    """Reorder so items not shown on a previous day (within `days`) come first.

    Stable within each group, so the existing relevance/source ordering is kept.
    Items shown earlier *today* (a same-day re-run) are not penalised, so
    re-running the pipeline reproduces the same edition rather than churning it.
    A track is therefore never blanked: fresh items lead, repeats only fill in.
    """
    fresh, repeats = [], []
    for it in items:
        last = seen.get(_item_key(it))
        gap = _days_between(last, today) if last else None
        if gap is not None and 1 <= gap <= days:
            repeats.append(it)
        else:
            fresh.append(it)
    return fresh + repeats


def record_shown(seen, items, today):
    """Mark items as shown today in the history map."""
    for it in items:
        seen[_item_key(it)] = today


def prune_seen(seen, today, retention=SEEN_RETENTION_DAYS):
    """Drop history entries older than the retention window."""
    return {k: v for k, v in seen.items()
            if (_days_between(v, today) if _days_between(v, today) is not None else 0) <= retention}


def load_yaml(filepath):
    """Load a YAML file, return empty dict if missing."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_json(filepath):
    """Load a JSON file, return empty list if missing."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def get_theme(preferences):
    """Get theme colors from preferences."""
    theme_name = preferences.get("design", {}).get("theme", "modern-minimalist")
    return THEMES.get(theme_name, DEFAULT_THEME)


def render_news_html(articles, max_items=MAX_ITEMS):
    """Render RSS articles to HTML."""
    if not articles:
        return '<p class="empty-state">No news available today.</p>'

    html_parts = []
    for item in articles[:max_items]:
        url = item.get("url", "#")
        title = item.get("title", "Untitled")
        source = item.get("source", "Unknown")
        category = item.get("category", "")
        summary = item.get("summary", "")

        tag_html = f'<span class="tag">{category}</span>' if category else ""
        desc = first_sentence(summary)
        desc_html = f'<div class="item-summary">{desc}</div>' if desc else ""

        html_parts.append(f'''    <div class="item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        <span class="source">{source}</span>
        {tag_html}
      </div>
      {desc_html}
    </div>''')

    return "\n".join(html_parts)


def render_jobs_html(jobs, max_items=MAX_ITEMS):
    """Render job listings to HTML."""
    if not jobs:
        return '<p class="empty-state">No matching jobs today.</p>'

    html_parts = []
    for job in jobs[:max_items]:
        url = job.get("url", "#")
        title = job.get("title", "Untitled")
        company = job.get("company", "Unknown")
        location = job.get("location", "")
        score = min(100, int(job.get("match_score", 0) * 100))

        meta_company = f'<span class="source">{company}</span>' if company else ""
        meta_sep = " · " if company and location else ""
        desc = first_sentence(job.get("description", ""))
        if not desc:
            where = f" in {location}" if location else ""
            at = f" at {company}" if company else ""
            desc = f"{title}{at}{where}.".strip()
        desc_html = f'<div class="item-summary">{desc}</div>'

        html_parts.append(f'''    <div class="job-item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        {meta_company}{meta_sep}{location}
        <span class="match-score">{score}% match</span>
      </div>
      {desc_html}
    </div>''')

    return "\n".join(html_parts)


def render_events_html(events, max_items=MAX_ITEMS):
    """Render events to HTML."""
    if not events:
        return '<p class="empty-state">No upcoming events found.</p>'

    html_parts = []
    for event in events[:max_items]:
        url = event.get("url", "#")
        title = event.get("title", "Untitled")
        date = event.get("date", "TBD")
        location = event.get("location", "TBD")
        etype = event.get("type", "event")

        source_url = event.get("source", "")
        source_host = source_url.split("/")[2] if source_url.startswith("http") else source_url
        source_label = source_host.replace("www.", "")
        desc = first_sentence(event.get("description", ""))
        if not desc:
            where = f" in {location}" if location and location != "TBD" else ""
            when = f" on {date}" if date and date != "TBD" else ""
            desc = f"{etype.title()}{where}{when}.".strip()
        desc_html = f'<div class="item-summary">{desc}</div>'
        html_parts.append(f'''    <div class="item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        <span class="source">{date}</span> · {location}
        <span class="tag">{etype}</span>
        <a class="source-link" href="{source_url}" target="_blank">{source_label}</a>
      </div>
      {desc_html}
    </div>''')

    return "\n".join(html_parts)


def render_section_split(energy_items, ai_items, render_fn, max_items):
    """Render a section as two labelled tracks: Energy, then AI & Tech.

    Each track shows up to `max_items`, rendered by `render_fn` (which already
    handles its own empty-state line, so a quiet track degrades gracefully).
    """
    return (
        '    <h3 class="subsection-title">⚡ Energy</h3>\n'
        + render_fn(energy_items, max_items)
        + '\n    <h3 class="subsection-title">🤖 AI &amp; Tech</h3>\n'
        + render_fn(ai_items, max_items)
    )


def render_feedback_html():
    """Render the feedback section — a single free-text comment box.

    There is no star rating: the written comment is the only input. It is
    distilled by analyze_feedback.py into topic/source preferences that
    automatically reweight the next edition, so the card tells the reader
    their comment is taken into account for tomorrow.
    """
    return '''  <section class="section" id="feedback">
    <h2 class="section-title">Today's Feedback</h2>
    <div class="feedback-card">
      <p class="feedback-note">Your comment is automatically analyzed and shapes what tomorrow's edition shows.</p>
      <textarea class="feedback-comment" placeholder="What did you think of today's edition? What should change tomorrow?"></textarea>
      <button class="feedback-submit">Send Feedback</button>
      <div class="feedback-status"></div>
      <div class="feedback-settings"></div>
    </div>
  </section>'''


def build_html(template, profile, content, theme):
    """Build the final HTML by replacing template placeholders."""
    identity = profile.get("identity", {})
    preferences = profile.get("preferences", {})

    user_name = identity.get("name", "there")
    language = preferences.get("writing", {}).get("language", "en")
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    date_formatted = now.strftime("%A, %B %d, %Y")

    interests = profile.get("interests", {})
    articles = dedupe_by_title(content.get("articles", []))
    jobs = content.get("jobs", [])
    events = dedupe_by_title(content.get("events", []))

    # Learned preferences: rating-driven item counts plus topic/source
    # preferences distilled from written feedback by analyze_feedback.py.
    section_item_counts, learned_prefs = load_learned_preferences()

    # Rank news and events by relevance, dropping off-profile items
    # (jobs arrive pre-scored and pre-filtered from fetch_jobs.py; learned
    # preferences don't apply there — match quality matters more).
    articles = rank_by_relevance(
        articles,
        lambda a: f"{a.get('title','')} {a.get('summary','')} {a.get('category','')}",
        interests,
        learned=learned_prefs,
        source_fn=lambda a: a.get("source", ""),
    )
    events = rank_by_relevance(
        events,
        lambda e: f"{e.get('title','')} {e.get('description','')} {e.get('location','')}",
        interests,
        learned=learned_prefs,
        source_fn=_source_host,
    )

    # Split news and events into two tracks (Energy / AI & Tech), preserving
    # relevance order within each. Jobs stay a single ranked list.
    news_energy, news_ai = split_by_topic(articles)
    events_energy, events_ai = split_by_topic(events)

    # Keep only events with a genuine energy signal (see MIN_ENERGY_TERMS_FOR_EVENT)
    # so the energy track isn't padded with one-word false positives; on a thin
    # day it simply shows fewer real events (the template renders a graceful
    # "no upcoming events" when a track is empty).
    events_energy = [e for e in events_energy
                     if energy_term_count(e) >= MIN_ENERGY_TERMS_FOR_EVENT]

    # Diversify by source so each shown item comes from a different reference.
    # Repeated sources fall to the back and only surface if there aren't enough
    # distinct sources to fill a track.
    news_energy = diversify_by_source(news_energy, lambda a: a.get("source", ""))
    news_ai = diversify_by_source(news_ai, lambda a: a.get("source", ""))
    jobs = diversify_by_source(jobs, lambda j: j.get("source", ""))
    events_energy = diversify_by_source(events_energy, _source_host)
    events_ai = diversify_by_source(events_ai, _source_host)

    # Day-over-day novelty: prefer news/events not shown on a recent previous
    # day, so each edition differs from the last. Repeats only fill a track when
    # there aren't enough fresh items, so a section is never left blank.
    seen = load_seen()
    news_energy = prioritize_unseen(news_energy, seen, date_str)
    news_ai = prioritize_unseen(news_ai, seen, date_str)
    events_energy = prioritize_unseen(events_energy, seen, date_str)
    events_ai = prioritize_unseen(events_ai, seen, date_str)

    # Per-section item counts from learned preferences (loaded above)
    max_news = get_max_items("news", section_item_counts)
    max_events = get_max_items("events", section_item_counts)

    # Render section content — top N most relevant items per topic track
    news_html = render_section_split(news_energy, news_ai, render_news_html, max_news)
    jobs_html = render_jobs_html(jobs, get_max_items("jobs", section_item_counts))
    events_html = render_section_split(events_energy, events_ai, render_events_html, max_events)

    # Record what was actually displayed so future editions avoid repeating it.
    record_shown(seen, news_energy[:max_news] + news_ai[:max_news], date_str)
    record_shown(seen, events_energy[:max_events] + events_ai[:max_events], date_str)
    save_seen(prune_seen(seen, date_str))

    feedback_html = render_feedback_html()

    # Replace all placeholders
    html = template
    html = html.replace("{{language}}", language)
    html = html.replace("{{date}}", date_str)
    html = html.replace("{{theme_bg}}", theme["bg"])
    html = html.replace("{{theme_surface}}", theme["surface"])
    html = html.replace("{{theme_primary}}", theme["primary"])
    html = html.replace("{{theme_secondary}}", theme["secondary"])
    html = html.replace("{{theme_accent}}", theme["accent"])
    html = html.replace("{{theme_text}}", theme["text"])
    html = html.replace("{{theme_text_muted}}", theme["text_muted"])
    html = html.replace("{{theme_border}}", theme["border"])
    html = html.replace("{{theme_font_heading}}", theme["font_heading"])
    html = html.replace("{{theme_font_body}}", theme["font_body"])
    html = html.replace("{{user_name}}", user_name)
    html = html.replace("{{date_formatted}}", date_formatted)
    html = html.replace("{{generated_at}}", now.strftime("%Y-%m-%d %H:%M UTC"))
    html = html.replace("{{archive_url}}", "../daily/")
    # Personal Coach sub-app (built separately into output/web/coach/). Relative
    # path from output/daily/DATE.html → output/web/coach/index.html.
    html = html.replace("{{coach_url}}", "../web/coach/index.html")

    # Replace section content placeholders
    html = html.replace("{{news_content}}", news_html)
    html = html.replace("{{jobs_content}}", jobs_html)
    html = html.replace("{{events_content}}", events_html)
    html = html.replace("{{feedback_content}}", feedback_html)

    return html


def main():
    parser = argparse.ArgumentParser(description="Render PersonalMentor daily newspaper HTML")
    parser.add_argument("--profile-dir", required=True, help="Path to profile/ directory")
    parser.add_argument("--content-dir", required=True, help="Path to content JSON files directory")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    args = parser.parse_args()

    # Load profile
    profile = {
        "identity": load_yaml(os.path.join(args.profile_dir, "identity.yaml")),
        "experience": load_yaml(os.path.join(args.profile_dir, "experience.yaml")),
        "interests": load_yaml(os.path.join(args.profile_dir, "interests.yaml")),
        "preferences": load_yaml(os.path.join(args.profile_dir, "preferences.yaml")),
        "sources": load_yaml(os.path.join(args.profile_dir, "sources.yaml")),
    }

    # Load content
    content = {
        "articles": load_json(os.path.join(args.content_dir, "rss.json")),
        "jobs": load_json(os.path.join(args.content_dir, "jobs.json")),
        "events": load_json(os.path.join(args.content_dir, "events.json")),
    }

    # Get theme
    theme = get_theme(profile.get("preferences", {}))

    # Load template
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Build HTML
    html = build_html(template, profile, content, theme)

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    total_items = len(content["articles"]) + len(content["jobs"]) + len(content["events"])
    print(f"Generated daily newspaper: {args.output}")
    print(f"  Theme: {profile['preferences'].get('design', {}).get('theme', 'modern-minimalist')}")
    print(f"  Total content items: {total_items}")
    print(f"  Articles: {len(content['articles'])} (showing max {MAX_ITEMS})")
    print(f"  Jobs: {len(content['jobs'])} (showing max {MAX_ITEMS})")
    print(f"  Events: {len(content['events'])} (showing max {MAX_ITEMS})")


if __name__ == "__main__":
    main()
