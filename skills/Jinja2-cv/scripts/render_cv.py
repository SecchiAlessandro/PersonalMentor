#!/usr/bin/env python3
"""
CV Renderer using docxtpl (Jinja2 for Word documents)

Renders a CV from EZ_Template_docxtpl.docx using candidate data in JSON format.
The template uses Jinja2 syntax for placeholders ({{ field }}) and loops ({% for %}).

Features:
- Text placeholder replacement via Jinja2
- Loop rendering for experience, education, skills, etc.
- Optional profile photo replacement

Requirements:
    pip install docxtpl python-docx jinja2

Usage:
    python render_cv.py \\
        --template templates/EZ_Template_docxtpl.docx \\
        --data-json candidate.json \\
        --out results/output.docx

    With photo:
    python render_cv.py \\
        --template templates/EZ_Template_docxtpl.docx \\
        --data-json candidate.json \\
        --photo photo.png \\
        --out results/output.docx
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from docxtpl import DocxTemplate, RichText


# =============================================================================
# JSON I/O
# =============================================================================

def load_json(path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Dict[str, Any]) -> None:
    """Save data to a JSON file with pretty formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =============================================================================
# Data Normalization
# =============================================================================

def _as_list(value: Any) -> List[Any]:
    """
    Ensure value is a list.
    - None -> empty list
    - Already a list -> return as-is
    - Single value -> wrap in list
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def process_bold_text(text: str) -> RichText:
    """
    Convert markdown bold syntax (**text**) to RichText with bold formatting.
    Preserves Arial Narrow font from template.
    
    Args:
        text: String that may contain **bold** markers
    
    Returns:
        RichText object with proper bold formatting for Word
    """
    if not text or '**' not in text:
        return text
    
    rt = RichText()
    parts = text.split('**')
    
    # Odd indices are bold, even indices are normal
    for i, part in enumerate(parts):
        if part:  # Skip empty parts
            if i % 2 == 1:  # Bold text
                rt.add(part, bold=True, font='Arial Narrow')
            else:  # Normal text
                rt.add(part, font='Arial Narrow')
    
    return rt


def normalize_context(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize raw candidate data into the structure expected by the template.

    This handles missing fields, null values, and type coercion to ensure
    the template renders without errors.

    Expected template variables:
        - full_name, nationality, availability, languages, location (strings)
        - highlights (list of strings)
        - experience (list of dicts with period, company, location, title, summary, bullets)
        - education (list of dicts with period, degree, school, specialization)
        - skills, projects (lists of strings)
        - awards (list of dicts with year, title, description, url)
        - hobbies (string)
    """
    ctx = {}

    # ---------------------------------------------------------------------
    # Header fields (simple strings)
    # ---------------------------------------------------------------------
    ctx["full_name"] = raw.get("full_name", "")
    ctx["nationality"] = raw.get("nationality", "")
    ctx["availability"] = raw.get("availability", "")
    ctx["languages"] = raw.get("languages", "")
    ctx["location"] = raw.get("location", "")

    # ---------------------------------------------------------------------
    # Highlights (list of strings with bold formatting)
    # ---------------------------------------------------------------------
    ctx["highlights"] = [process_bold_text(str(x)) for x in _as_list(raw.get("highlights"))]

    # ---------------------------------------------------------------------
    # Experience (list of structured entries)
    # Each entry: period, company, location, title, summary, bullets[]
    # ---------------------------------------------------------------------
    exp_list = _as_list(raw.get("experience"))
    normalized_exp = []
    for e in exp_list:
        if not isinstance(e, dict):
            continue
        normalized_exp.append({
            "period": str(e.get("period", "")),
            "company": str(e.get("company", "")),
            "location": str(e.get("location", "")),
            "title": str(e.get("title", "")),
            "summary": str(e.get("summary", "")) if e.get("summary") else "",
            "bullets": [str(b) for b in _as_list(e.get("bullets"))],
        })
    ctx["experience"] = normalized_exp

    # ---------------------------------------------------------------------
    # Education (list of structured entries)
    # Each entry: period, degree, school, specialization
    # ---------------------------------------------------------------------
    edu_list = _as_list(raw.get("education"))
    normalized_edu = []
    for ed in edu_list:
        if not isinstance(ed, dict):
            continue
        normalized_edu.append({
            "period": str(ed.get("period", "")),
            "degree": str(ed.get("degree", "")),
            "school": str(ed.get("school", "")),
            "specialization": str(ed.get("specialization", "")) if ed.get("specialization") else "",
        })
    ctx["education"] = normalized_edu

    # ---------------------------------------------------------------------
    # Skills and Projects (lists of strings)
    # ---------------------------------------------------------------------
    ctx["skills"] = [str(x) for x in _as_list(raw.get("skills"))]
    ctx["projects"] = [str(x) for x in _as_list(raw.get("projects"))]

    # ---------------------------------------------------------------------
    # Awards (list of structured entries)
    # Each entry: year, title, description, url
    # ---------------------------------------------------------------------
    awards_list = _as_list(raw.get("awards"))
    normalized_awards = []
    for aw in awards_list:
        if not isinstance(aw, dict):
            continue
        normalized_awards.append({
            "year": str(aw.get("year", "")),
            "title": str(aw.get("title", "")),
            "description": str(aw.get("description", "")),
            "url": str(aw.get("url", "")),
        })
    ctx["awards"] = normalized_awards

    # ---------------------------------------------------------------------
    # Hobbies (single string)
    # ---------------------------------------------------------------------
    ctx["hobbies"] = raw.get("hobbies", "")

    return ctx


# =============================================================================
# Document Rendering
# =============================================================================

def render_doc(
    template_path: str,
    context: Dict[str, Any],
    out_path: str,
    photo_path: str = None,
    profile_pic_tag: str = "profile_pic",
) -> None:
    """
    Render the CV document from template and context data.

    Args:
        template_path: Path to the .docx template with Jinja2 placeholders
        context: Dictionary of template variables (from normalize_context)
        out_path: Where to save the rendered document
        photo_path: Optional path to profile photo (replaces image in template)
        profile_pic_tag: Alt text tag identifying the photo placeholder in template
    """
    doc = DocxTemplate(template_path)

    # Replace profile photo if provided
    # The template image must have Alt Text/Description set to profile_pic_tag
    if photo_path:
        if not os.path.exists(photo_path):
            raise FileNotFoundError(f"Photo not found: {photo_path}")
        doc.replace_pic(profile_pic_tag, photo_path)

    # Render all Jinja2 placeholders and loops
    doc.render(context)

    # Save the final document
    doc.save(out_path)


# =============================================================================
# CLI Interface
# =============================================================================

def parse_args():
    """Parse command line arguments."""
    ap = argparse.ArgumentParser(
        description="Render CV from docxtpl template + JSON candidate data"
    )
    ap.add_argument(
        "--template",
        required=True,
        help="Path to DOCX template (docxtpl format)"
    )
    ap.add_argument(
        "--data-json",
        required=True,
        help="Path to candidate data JSON file"
    )
    ap.add_argument(
        "--photo",
        default=None,
        help="Path to profile image (png/jpg) - optional"
    )
    ap.add_argument(
        "--out",
        required=True,
        help="Output .docx file path"
    )
    ap.add_argument(
        "--dump-normalized",
        default=None,
        help="Save normalized context to JSON (for debugging)"
    )
    ap.add_argument(
        "--profile-pic-tag",
        default="profile_pic",
        help="Alt text tag for photo replacement (default: profile_pic)"
    )
    return ap.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Validate template exists
    if not os.path.exists(args.template):
        print(f"Error: Template not found: {args.template}", file=sys.stderr)
        sys.exit(2)

    # Validate data JSON exists
    if not os.path.exists(args.data_json):
        print(f"Error: Data JSON not found: {args.data_json}", file=sys.stderr)
        sys.exit(2)

    # Load candidate data
    raw = load_json(args.data_json)

    # Normalize data for template
    context = normalize_context(raw)

    # Optionally dump normalized context for debugging
    if args.dump_normalized:
        save_json(args.dump_normalized, context)

    # Render the document
    render_doc(
        template_path=args.template,
        context=context,
        out_path=args.out,
        photo_path=args.photo,
        profile_pic_tag=args.profile_pic_tag,
    )

    print(f"CV generated successfully: {args.out}")


if __name__ == "__main__":
    main()
