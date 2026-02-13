---
name: nano-banana-pro
description: Generate or edit images via Gemini image generation API. Use when the user asks to generate, create, or edit images using AI.
tools: Bash, Read, Write
context: fork
---

# Nano Banana Pro (Gemini Image Generation)

Use the bundled script to generate or edit images via the Gemini API.

## Prerequisites

- **uv** must be installed (`brew install uv`)
- **GEMINI_API_KEY** environment variable must be set

## Generate an image from a text prompt

```bash
uv run .claude/skills/nano-banana-pro/scripts/generate_image.py --prompt "your image description" --filename "output.png"
```

## Edit a single image

```bash
uv run .claude/skills/nano-banana-pro/scripts/generate_image.py --prompt "edit instructions" --filename "output.png" -i "/path/to/input.png"
```

## Multi-image composition (up to 14 input images)

```bash
uv run .claude/skills/nano-banana-pro/scripts/generate_image.py --prompt "combine these into one scene" --filename "output.png" -i img1.png -i img2.png -i img3.png
```

## Options

| Option | Required | Description |
|--------|----------|-------------|
| `--prompt` | Yes | Text prompt describing the image to generate or edit |
| `--filename` | Yes | Output filename (saved to `results/` by default) |
| `-i` / `--input` | No | Input image path(s) for editing. Repeat for multiple images |
| `--output-dir` | No | Output directory (default: `results/`) |
| `--model` | No | Gemini model to use (default: `gemini-2.5-flash-preview-image-generation`) |

## Notes

- Use timestamps in filenames when generating multiple images: `yyyy-mm-dd-hh-mm-ss-name.png`.
- The script prints the saved file path on success.
- Do not read the generated image back; just report the saved path to the user.
- If the generation fails, check that `GEMINI_API_KEY` is set correctly.
