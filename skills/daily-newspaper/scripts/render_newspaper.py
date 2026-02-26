#!/usr/bin/env python3
"""Render the PersonalMentor daily newspaper HTML from collected content."""

import argparse
import json
import os
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

MAX_ITEMS = 3  # default, overridden by learned-preferences per section


def load_learned_preferences():
    """Load learned-preferences.yaml and return section item counts."""
    if not os.path.exists(LEARNED_PREFS_PATH):
        return {}
    with open(LEARNED_PREFS_PATH, "r", encoding="utf-8") as f:
        prefs = yaml.safe_load(f) or {}
    return prefs.get("reading_patterns", {}).get("section_item_counts", {})


def get_max_items(section, section_item_counts):
    """Get max items for a section, using learned preference or default."""
    return section_item_counts.get(section, MAX_ITEMS)


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


def load_json_obj(filepath):
    """Load a JSON file, return empty dict if missing."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


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

        html_parts.append(f'''    <div class="item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        <span class="source">{source}</span>
        {tag_html}
      </div>
      <div class="item-summary">{summary}</div>
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
        score = int(job.get("match_score", 0) * 100)

        html_parts.append(f'''    <div class="job-item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        <span class="source">{company}</span> · {location}
        <span class="match-score">{score}% match</span>
      </div>
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

        html_parts.append(f'''    <div class="item">
      <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="item-meta">
        <span class="source">{date}</span> · {location}
        <span class="tag">{etype}</span>
      </div>
    </div>''')

    return "\n".join(html_parts)


def render_calendar_html(events, max_items=MAX_ITEMS):
    """Render calendar events to HTML."""
    if not events:
        return '<p class="empty-state">No events on your calendar today.</p>'

    html_parts = []
    for event in events[:max_items]:
        time_str = event.get("time", "")
        title = event.get("title", "Untitled")
        html_parts.append(f'''    <div class="calendar-item">
      <span class="calendar-time">{time_str}</span> {title}
    </div>''')

    return "\n".join(html_parts)


def render_german_html(german_data):
    """Render German Quote of the Day to HTML."""
    if not german_data:
        return '<p class="empty-state">No German quote today.</p>'

    german = german_data.get("german", "")
    english = german_data.get("english", "")
    author = german_data.get("author", "")
    image_b64 = german_data.get("image_base64")

    image_html = ""
    if image_b64:
        mime = german_data.get("image_mime", "image/png")
        image_html = f'<img class="german-card-image" src="data:{mime};base64,{image_b64}" alt="Illustration">'

    author_html = f'\n        <div class="german-author">— {author}</div>' if author else ""

    return f'''    <div class="german-card">
      {image_html}
      <div class="german-card-text">
        <div class="german-sentence">„{german}“</div>
        <div class="german-translation">“{english}”</div>{author_html}
      </div>
    </div>'''


def render_feedback_html(active_sections):
    """Render the feedback section with per-section thumb rows for active sections.

    active_sections: list of (key, label) for sections that have content.
    """
    section_rows = []
    for key, label in active_sections:
        section_rows.append(
            f'      <div class="feedback-section-row" data-section="{key}">'
            f'<span>{label}</span> '
            f'<button class="thumb up">&#128077;</button> '
            f'<button class="thumb down">&#128078;</button>'
            f'</div>'
        )

    rows_html = "\n".join(section_rows) if section_rows else ""

    return f'''  <section class="section" id="feedback">
    <h2 class="section-title">Rate Today's Edition</h2>
    <div class="feedback-card">
      <div class="feedback-overall">
        <span class="feedback-label">Overall</span>
        <div class="star-rating" data-target="overall">
          <span class="star">&#9733;</span><span class="star">&#9733;</span><span class="star">&#9733;</span><span class="star">&#9733;</span><span class="star">&#9733;</span>
        </div>
      </div>
      <div class="feedback-sections">
{rows_html}
      </div>
      <textarea class="feedback-comment" placeholder="Any thoughts? (optional)"></textarea>
      <button class="feedback-submit">Submit Feedback</button>
      <div class="feedback-status"></div>
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

    articles = content.get("articles", [])
    jobs = content.get("jobs", [])
    events = content.get("events", [])
    calendar = content.get("calendar", [])
    german = content.get("german", {})

    # Load learned preferences for per-section item counts
    section_item_counts = load_learned_preferences()

    # Render section content with per-section max items
    news_html = render_news_html(articles, get_max_items("news", section_item_counts))
    jobs_html = render_jobs_html(jobs, get_max_items("jobs", section_item_counts))
    events_html = render_events_html(events, get_max_items("events", section_item_counts))
    calendar_html = render_calendar_html(calendar, get_max_items("calendar", section_item_counts))
    german_html = render_german_html(german)

    # Determine which sections have content (for feedback thumbs)
    active_sections = []
    if articles:
        active_sections.append(("news", "News"))
    if jobs:
        active_sections.append(("jobs", "Jobs"))
    if events:
        active_sections.append(("events", "Events"))
    if calendar:
        active_sections.append(("calendar", "Calendar"))
    if german:
        active_sections.append(("german", "German"))
    feedback_html = render_feedback_html(active_sections)

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

    # Replace section content placeholders
    html = html.replace("{{news_content}}", news_html)
    html = html.replace("{{jobs_content}}", jobs_html)
    html = html.replace("{{events_content}}", events_html)
    html = html.replace("{{calendar_content}}", calendar_html)
    html = html.replace("{{german_content}}", german_html)
    html = html.replace("{{feedback_content}}", feedback_html)

    return html


def main():
    parser = argparse.ArgumentParser(description="Render PersonalMentor daily newspaper HTML")
    parser.add_argument("--profile-dir", required=True, help="Path to profile/ directory")
    parser.add_argument("--content-dir", required=True, help="Path to content JSON files directory")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--calendar-json", default="", help="Optional: calendar events JSON file")
    parser.add_argument("--german-json", default="", help="Optional: German sentence JSON file")
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
        "calendar": load_json(args.calendar_json) if args.calendar_json else [],
        "german": load_json_obj(args.german_json) if args.german_json else {},
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

    total_items = (
        len(content["articles"]) + len(content["jobs"]) +
        len(content["events"]) + len(content["calendar"]) +
        (1 if content["german"] else 0)
    )
    print(f"Generated daily newspaper: {args.output}")
    print(f"  Theme: {profile['preferences'].get('design', {}).get('theme', 'modern-minimalist')}")
    print(f"  Total content items: {total_items}")
    print(f"  Articles: {len(content['articles'])} (showing max {MAX_ITEMS})")
    print(f"  Jobs: {len(content['jobs'])} (showing max {MAX_ITEMS})")
    print(f"  Events: {len(content['events'])} (showing max {MAX_ITEMS})")
    print(f"  Calendar: {len(content['calendar'])}")
    print(f"  German: {'yes' if content['german'] else 'no'}")


if __name__ == "__main__":
    main()
