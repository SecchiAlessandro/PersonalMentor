---
name: Jinja2-cv
description: Renders CVs from EZ_Template_docxtpl.docx using Jinja2/docxtpl. Use when converting candidate data into a formatted CV document.
tools: Read, Write, Bash
context: fork
---

# Jinja2-cv Skill

Renders CVs from `templates/EZ_Template_docxtpl.docx` using Jinja2/docxtpl. This skill uses Claude Code's native file reading capability to extract data from source CVs and generate formatted output.

## Workflow

### Step 1: Read the Source CV

Use the Read tool to read the source CV file. Claude Code natively supports:
- **PDF files** - Reads and extracts text and visual content
- **DOCX files** - Reads Word documents with formatting
- **TXT files** - Plain text files

```
Read the source CV file provided by the user.
```

### Step 2: Extract and Write Candidate JSON

After reading the source CV, extract all relevant information and write it to `results/candidate_data.json` following the structure and rules below.

**Output file:** `results/candidate_data.json`

#### Required JSON Structure

```json
{
  "full_name": "string (required)",
  "nationality": "string (nationality and work permit if mentioned)",
  "availability": "string (when can start, e.g., 'Immediately', '1 month notice')",
  "languages": "string (e.g., 'English (C1), German (B2), Spanish (Native)')",
  "location": "string (current location/city)",
  "highlights": ["array of 2-4 key career highlights as brief bullet points"],
  "experience": [
    {
      "period": "string (e.g., 'Jan 2020 - Dec 2022')",
      "company": "string",
      "location": "string",
      "title": "string (job title)",
      "summary": "string (optional brief summary)",
      "bullets": ["array of achievement bullet points"]
    }
  ],
  "education": [
    {
      "period": "string (e.g., '2015 - 2019')",
      "degree": "string (e.g., 'Bachelor of Computer Science')",
      "school": "string (institution name)",
      "specialization": "string (optional)"
    }
  ],
  "skills": ["array of technical skills"],
  "projects": ["array of notable projects - optional"],
  "awards": [
    {
      "year": "string",
      "title": "string",
      "description": "string",
      "url": "string (optional)"
    }
  ],
  "hobbies": "string (personal interests)"
}
```

#### Extraction Rules

1. **Extract ALL information** available in the CV
2. **Missing fields**: Use empty strings `""` or empty arrays `[]`
3. **Dates**: Convert all dates to readable format (e.g., "Jan 2020 - Dec 2022")
4. **Highlights**: Create 2-4 concise, impactful highlights from the most impressive achievements
5. **Bold formatting in highlights**: Wrap important keywords (skills, achievements, roles, awards) in `**double asterisks**` for bold formatting
   - Example: `"**Lead Engineer** managing **$2M budget** projects"`
   - Example: `"Built **microservices architecture** reducing latency by **40%**"`
6. **Skills**: Preserve all technical skills mentioned
7. **Experience order**: Most recent first
8. **Bullets**: Write achievement-focused bullet points (quantify when possible)

### Step 3: Render the CV

Run the render script (do not read it, just execute):

```bash
python ".claude/skills/Jinja2-cv/scripts/render_cv.py" \
  --template "templates/EZ_Template_docxtpl.docx" \
  --data-json "results/candidate_data.json" \
  --out "results/<candidate_name>_CV.docx"
```

**With profile photo:**
```bash
python ".claude/skills/Jinja2-cv/scripts/render_cv.py" \
  --template "templates/EZ_Template_docxtpl.docx" \
  --data-json "results/candidate_data.json" \
  --photo "path/to/photo.png" \
  --out "results/<candidate_name>_CV.docx"
```

### Step 4: Verify Output

Confirm the output file was created. The script prints a success message with the output path.

## Script Options

| Option | Required | Description |
|--------|----------|-------------|
| `--template` | Yes | Path to the docxtpl template |
| `--data-json` | Yes | Path to candidate JSON data |
| `--out` | Yes | Output .docx file path |
| `--photo` | No | Path to profile photo (png/jpg) |
| `--dump-normalized` | No | Save normalized context to JSON (debugging) |
| `--profile-pic-tag` | No | Alt text tag for photo replacement (default: "profile_pic") |

## Example Candidate JSON in .claude\skills\Jinja2-cv\candidate_schema.json

## Additional Resources

- For complete schema reference, see [candidate_schema.json](candidate_schema.json)
- For Jinja2 template syntax, see [Jinja2 Template Documentation](https://jinja.palletsprojects.com/en/stable/templates/)

## Dependencies

```
pip install docxtpl python-docx jinja2
```
