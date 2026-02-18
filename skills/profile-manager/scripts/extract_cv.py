#!/usr/bin/env python3
"""Extract structured data from a CV/resume (PDF or DOCX) using heuristics.

No LLM required — uses regex patterns and section-header detection to
produce a JSON structure matching the PersonalMentor profile schema.

Usage:
    python3 extract_cv.py --input cv.pdf --output extracted.json

Importable:
    from extract_cv import extract_cv
"""

import argparse
import json
import os
import re
import sys


def _read_pdf(path):
    """Extract text from a PDF file."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("ERROR: pypdf not installed. Run: pip install pypdf>=4.0", file=sys.stderr)
        return ""
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _read_docx(path):
    """Extract text from a DOCX file."""
    try:
        from docx import Document
    except ImportError:
        print("ERROR: python-docx not installed. Run: pip install python-docx>=1.1", file=sys.stderr)
        return ""
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _extract_email(text):
    m = re.search(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return m.group(0) if m else ""


def _extract_linkedin(text):
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_\-/]+", text)
    return m.group(0) if m else ""


def _extract_github(text):
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_\-]+", text)
    return m.group(0) if m else ""


def _extract_website(text):
    """Extract a personal website URL (not LinkedIn/GitHub)."""
    urls = re.findall(r"https?://[a-zA-Z0-9.\-/]+\.[a-zA-Z]{2,}[a-zA-Z0-9.\-/]*", text)
    for url in urls:
        lower = url.lower()
        if "linkedin.com" not in lower and "github.com" not in lower:
            return url
    return ""


# Patterns for section headers
_SECTION_PATTERNS = {
    "education": re.compile(r"^(?:education|academic|studies|qualifications)", re.I),
    "experience": re.compile(r"^(?:experience|work\s*history|employment|professional\s*experience|career)", re.I),
    "skills": re.compile(r"^(?:skills|technical\s*skills|competencies|technologies|tools)", re.I),
    "projects": re.compile(r"^(?:projects|portfolio|personal\s*projects|selected\s*projects)", re.I),
    "languages": re.compile(r"^(?:languages|language\s*skills)", re.I),
}

# Degree keywords
_DEGREE_PATTERNS = [
    re.compile(r"(?:Ph\.?D|Doctor)", re.I),
    re.compile(r"(?:M\.?Sc|Master|MAS|M\.?Eng|MBA|M\.A\.?)", re.I),
    re.compile(r"(?:B\.?Sc|Bachelor|B\.?Eng|B\.A\.?)", re.I),
    re.compile(r"(?:Exchange|Erasmus|Visiting)", re.I),
]


def _classify_line(line):
    """Return section name if line is a section header, else None."""
    stripped = line.strip().rstrip(":").strip()
    if not stripped or len(stripped) > 60:
        return None
    for section, pattern in _SECTION_PATTERNS.items():
        if pattern.match(stripped):
            return section
    return None


def _split_sections(text):
    """Split text into sections based on detected headers."""
    lines = text.split("\n")
    sections = {}
    current = "header"
    sections[current] = []

    for line in lines:
        sect = _classify_line(line)
        if sect:
            current = sect
            if current not in sections:
                sections[current] = []
        else:
            sections.setdefault(current, []).append(line)

    return sections


def _parse_education(lines):
    """Extract education entries from section lines."""
    entries = []
    current = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line has a degree keyword
        has_degree = any(p.search(stripped) for p in _DEGREE_PATTERNS)
        # Check for institution-like line (often title-case, no bullet)
        is_bullet = stripped.startswith(("-", "•", "·", "*"))

        if has_degree or (not is_bullet and len(stripped) > 5 and not stripped[0].isdigit()):
            if current and not current.get("degree"):
                # Previous entry was just institution, this might be degree
                current["degree"] = stripped
            else:
                current = {
                    "institution": stripped,
                    "degree": "",
                    "field": "",
                    "year": "",
                }
                entries.append(current)
        elif current and is_bullet:
            detail = stripped.lstrip("-•·* ").strip()
            if not current["field"]:
                current["field"] = detail
            elif not current["year"]:
                current["year"] = detail

    # Try to extract year info from institution/degree strings
    year_pattern = re.compile(r"((?:19|20)\d{2})\s*[-–]\s*((?:19|20)\d{2}|present|current)?", re.I)
    for entry in entries:
        for field in ["institution", "degree", "field"]:
            m = year_pattern.search(entry.get(field, ""))
            if m and not entry["year"]:
                entry["year"] = m.group(0)

    return entries


def _parse_experience(lines):
    """Extract work history entries from section lines."""
    entries = []
    current = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        is_bullet = stripped.startswith(("-", "•", "·", "*"))

        if not is_bullet and len(stripped) > 3:
            # Potential company/role line
            # Try to split "Role at Company" or "Company — Role"
            parts = re.split(r"\s+(?:at|@|—|–|-|,)\s+", stripped, maxsplit=1)
            if len(parts) == 2:
                current = {
                    "company": parts[1].strip(),
                    "role": parts[0].strip(),
                    "period": "",
                    "highlights": [],
                }
            else:
                current = {
                    "company": stripped,
                    "role": "",
                    "period": "",
                    "highlights": [],
                }
            entries.append(current)
        elif current and is_bullet:
            detail = stripped.lstrip("-•·* ").strip()
            if detail:
                current["highlights"].append(detail)

    # Try to extract periods
    period_pattern = re.compile(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(?:19|20)\d{2})"
        r"\s*[-–]\s*"
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*(?:19|20)\d{2}|present|current)",
        re.I,
    )
    for entry in entries:
        for field in ["company", "role"]:
            m = period_pattern.search(entry.get(field, ""))
            if m and not entry["period"]:
                entry["period"] = m.group(0)

    return entries


def _parse_skills(lines):
    """Extract skills from section lines."""
    skills = []
    for line in lines:
        stripped = line.strip().lstrip("-•·* ").strip()
        if not stripped:
            continue
        # Skills are often comma-separated or pipe-separated
        if "," in stripped or "|" in stripped:
            parts = re.split(r"[,|]", stripped)
            skills.extend(p.strip() for p in parts if p.strip())
        elif len(stripped) < 50:
            skills.append(stripped)
    return skills


def _extract_name(text):
    """Try to extract name from first non-empty lines."""
    lines = text.strip().split("\n")
    for line in lines[:5]:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip lines that look like contact info
        if "@" in stripped or "http" in stripped or "+" in stripped:
            continue
        # Skip lines that are too long (likely a summary)
        if len(stripped) > 40:
            continue
        # First short line is likely the name
        return stripped
    return ""


def extract_cv(path):
    """Extract structured data from a CV file.

    Args:
        path: Path to PDF or DOCX file.

    Returns:
        dict matching PersonalMentor profile schema structure.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = _read_pdf(path)
    elif ext in (".docx", ".doc"):
        text = _read_docx(path)
    else:
        print(f"ERROR: Unsupported file type: {ext}", file=sys.stderr)
        return {}

    if not text.strip():
        return {"error": "Could not extract text from file"}

    sections = _split_sections(text)

    # Extract contact info from full text
    name = _extract_name(text)
    email = _extract_email(text)
    linkedin = _extract_linkedin(text)
    github = _extract_github(text)
    website = _extract_website(text)

    # Parse structured sections
    education = _parse_education(sections.get("education", []))
    work_history = _parse_experience(sections.get("experience", []))
    skills = _parse_skills(sections.get("skills", []))

    result = {
        "identity": {
            "name": name,
            "contact": {
                "email": email,
                "linkedin": linkedin,
                "github": github,
                "website": website,
            },
        },
        "experience": {
            "work_history": work_history,
            "education": education,
            "skills": {"technical": skills},
        },
        "raw_text": text[:5000],  # Keep first 5k chars for reference
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Extract structured data from a CV (PDF/DOCX)")
    parser.add_argument("--input", required=True, help="Path to CV file (PDF or DOCX)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracting: {args.input}")
    data = extract_cv(args.input)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Extracted → {args.output}")
    if data.get("identity", {}).get("name"):
        print(f"  Name: {data['identity']['name']}")
    if data.get("experience", {}).get("education"):
        print(f"  Education entries: {len(data['experience']['education'])}")
    if data.get("experience", {}).get("work_history"):
        print(f"  Work history entries: {len(data['experience']['work_history'])}")
    if data.get("experience", {}).get("skills", {}).get("technical"):
        print(f"  Skills: {len(data['experience']['skills']['technical'])}")


if __name__ == "__main__":
    main()
