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
TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "..", "assets", "template.html")

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
}


def load_yaml(filepath):
    """Load a YAML file, return empty dict if missing."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r") as f:
        return yaml.safe_load(f) or {}


def load_json(filepath):
    """Load a JSON file, return empty list if missing."""
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def get_theme(preferences):
    """Get theme colors from preferences."""
    theme_name = preferences.get("design", {}).get("theme", "modern-minimalist")
    return THEMES.get(theme_name, DEFAULT_THEME)


def categorize_articles(articles, interests):
    """Split articles into sections based on category and topic relevance."""
    professional_topics = [t.get("topic", "").lower() for t in (interests.get("professional") or [])]
    industries = [i.lower() for i in (interests.get("industries") or [])]

    top_stories = []
    skill_items = []
    pulse_items = []
    reading_items = []

    for article in articles:
        cat = article.get("category", "").lower()
        title_lower = article.get("title", "").lower()
        summary_lower = article.get("summary", "").lower()
        combined = f"{title_lower} {summary_lower}"

        # Categorize based on keywords and category
        if any(kw in combined for kw in ["learn", "course", "tutorial", "skill", "certification"]):
            skill_items.append(article)
        elif any(kw in combined for kw in ["funding", "launch", "startup", "market", "ipo", "acquisition"]):
            pulse_items.append(article)
        elif cat in ("research", "longread", "opinion", "essay"):
            reading_items.append(article)
        else:
            top_stories.append(article)

    return {
        "top_stories": top_stories,
        "skill_items": skill_items,
        "pulse_items": pulse_items,
        "reading_items": reading_items,
    }


def render_items_html(items, max_items=5):
    """Render a list of article items to HTML."""
    if not items:
        return '<p class="empty-state">No content available today.</p>'

    html_parts = []
    for item in items[:max_items]:
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


def render_jobs_html(jobs, max_items=5):
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

        html_parts.append(f'''      <div class="job-item">
        <div class="item-title"><a href="{url}" target="_blank">{title}</a></div>
        <div class="item-meta">
          <span class="source">{company}</span> · {location}
          <span class="match-score">{score}% match</span>
        </div>
      </div>''')

    return "\n".join(html_parts)


def render_events_html(events, max_items=5):
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


def render_calendar_html(events):
    """Render calendar events to HTML."""
    if not events:
        return '<p class="empty-state">No events on your calendar.</p>'

    html_parts = []
    for event in events:
        time_str = event.get("time", "")
        title = event.get("title", "Untitled")
        html_parts.append(f'''        <div class="calendar-item">
          <span class="calendar-time">{time_str}</span> {title}
        </div>''')

    return "\n".join(html_parts)


def render_birthdays_html(birthdays):
    """Render birthdays to HTML."""
    if not birthdays:
        return '<p class="empty-state">No birthdays this week.</p>'

    html_parts = []
    for b in birthdays:
        name = b.get("name", "")
        note = b.get("note", "")
        html_parts.append(f'        <div class="birthday-item">{name} {note}</div>')

    return "\n".join(html_parts)


def build_html(template, profile, content, theme):
    """Build the final HTML by replacing template placeholders."""
    identity = profile.get("identity", {})
    preferences = profile.get("preferences", {})
    interests = profile.get("interests", {})

    user_name = identity.get("name", "there")
    language = preferences.get("writing", {}).get("language", "en")
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    date_formatted = now.strftime("%A, %B %d, %Y")
    max_items = preferences.get("daily_artifact", {}).get("max_items_per_section", 5)
    enabled = preferences.get("daily_artifact", {}).get("sections_enabled", [])

    # Categorize RSS articles into sections
    articles = content.get("articles", [])
    categorized = categorize_articles(articles, interests)

    jobs = content.get("jobs", [])
    events = content.get("events", [])
    calendar = content.get("calendar", [])
    birthdays = content.get("birthdays", [])

    # Build section HTML blocks
    top_stories_html = render_items_html(categorized["top_stories"], max_items)
    jobs_html = render_jobs_html(jobs, max_items)
    calendar_html = render_calendar_html(calendar)
    birthdays_html = render_birthdays_html(birthdays)
    events_html = render_events_html(events, max_items)
    skills_html = render_items_html(categorized["skill_items"], max_items)
    pulse_html = render_items_html(categorized["pulse_items"], max_items)
    reading_html = render_items_html(categorized["reading_items"], max_items)

    # Replace theme variables
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

    # Replace section blocks — use simple conditional replacement
    def replace_section(html, section_id, enabled_list, content_html):
        """Replace mustache-style section blocks."""
        pattern = r'\{\{#section_' + section_id + r'\}\}(.*?)\{\{/section_' + section_id + r'\}\}'
        if not enabled_list or section_id_to_slug(section_id) in enabled_list:
            # Keep section, inject content
            match = re.search(pattern, html, re.DOTALL)
            if match:
                section_template = match.group(1)
                # Replace item placeholders with rendered HTML
                return html[:match.start()] + inject_content(section_template, section_id, content_html) + html[match.end():]
        else:
            # Remove section
            return re.sub(pattern, "", html, flags=re.DOTALL)
        return html

    def section_id_to_slug(sid):
        mapping = {
            "top_stories": "top-stories",
            "jobs_calendar": "jobs-for-you",
            "events": "events-near-you",
            "skills": "skill-spotlight",
            "pulse": "industry-pulse",
            "reading": "reading-list",
        }
        return mapping.get(sid, sid)

    def inject_content(template_block, section_id, content_html):
        """Replace mustache item loops with rendered HTML."""
        # Remove mustache loop markers and replace with rendered content
        # Clean up mustache syntax and inject HTML
        result = template_block
        # Remove all mustache tags and replace the section content area
        result = re.sub(r'\{\{#\w+\}\}.*?\{\{/\w+\}\}', '', result, flags=re.DOTALL)
        result = re.sub(r'\{\{\^\w+\}\}.*?\{\{/\w+\}\}', '', result, flags=re.DOTALL)
        result = re.sub(r'\{\{[^}]+\}\}', '', result)

        # Find the section body and inject content
        # Insert content after section-title
        title_end = result.find("</h2>")
        if title_end != -1:
            result = result[:title_end + 5] + "\n" + content_html + "\n" + result[title_end + 5:]

        return result

    # For the two-column jobs+calendar section, handle specially
    jobs_cal_pattern = r'\{\{#section_jobs_calendar\}\}(.*?)\{\{/section_jobs_calendar\}\}'
    jobs_cal_match = re.search(jobs_cal_pattern, html, re.DOTALL)
    if jobs_cal_match:
        jobs_cal_block = f'''  <div class="two-column">
    <section class="section" id="jobs">
      <h2 class="section-title">Jobs For You</h2>
{jobs_html}
    </section>
    <div>
      <section class="section" id="calendar">
        <h2 class="section-title">Today\'s Calendar</h2>
{calendar_html}
      </section>
      <section class="section" id="birthdays">
        <h2 class="section-title">Birthdays</h2>
{birthdays_html}
      </section>
    </div>
  </div>'''
        html = html[:jobs_cal_match.start()] + jobs_cal_block + html[jobs_cal_match.end():]

    # Replace remaining sections
    html = replace_section(html, "top_stories", enabled, top_stories_html)
    html = replace_section(html, "events", enabled, events_html)
    html = replace_section(html, "skills", enabled, skills_html)
    html = replace_section(html, "pulse", enabled, pulse_html)
    html = replace_section(html, "reading", enabled, reading_html)

    return html


def main():
    parser = argparse.ArgumentParser(description="Render PersonalMentor daily newspaper HTML")
    parser.add_argument("--profile-dir", required=True, help="Path to profile/ directory")
    parser.add_argument("--content-dir", required=True, help="Path to content JSON files directory")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--calendar-json", default="", help="Optional: calendar events JSON file")
    parser.add_argument("--birthdays-json", default="", help="Optional: birthdays JSON file")
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
        "birthdays": load_json(args.birthdays_json) if args.birthdays_json else [],
    }

    # Get theme
    theme = get_theme(profile.get("preferences", {}))

    # Load template
    with open(TEMPLATE_PATH, "r") as f:
        template = f.read()

    # Build HTML
    html = build_html(template, profile, content, theme)

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        f.write(html)

    total_items = (
        len(content["articles"]) + len(content["jobs"]) +
        len(content["events"]) + len(content["calendar"]) +
        len(content["birthdays"])
    )
    print(f"Generated daily newspaper: {args.output}")
    print(f"  Theme: {profile['preferences'].get('design', {}).get('theme', 'modern-minimalist')}")
    print(f"  Total content items: {total_items}")
    print(f"  Articles: {len(content['articles'])}")
    print(f"  Jobs: {len(content['jobs'])}")
    print(f"  Events: {len(content['events'])}")


if __name__ == "__main__":
    main()
