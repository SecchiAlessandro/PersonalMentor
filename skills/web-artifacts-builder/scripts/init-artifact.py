#!/usr/bin/env python3
"""Initialize a React + Vite + Tailwind + shadcn/ui project (cross-platform).

Drop-in replacement for init-artifact.sh that works on macOS, Linux, and Windows.

Usage:
    python skills/web-artifacts-builder/scripts/init-artifact.py <project-name>
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
COMPONENTS_TARBALL = SCRIPT_DIR / "shadcn-components.tar.gz"

# ---------------------------------------------------------------------------
# CSS / config content (inlined from the shell script)
# ---------------------------------------------------------------------------

INDEX_CSS = """\
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    --card: 0 0% 3.9%;
    --card-foreground: 0 0% 98%;
    --popover: 0 0% 3.9%;
    --popover-foreground: 0 0% 98%;
    --primary: 0 0% 98%;
    --primary-foreground: 0 0% 9%;
    --secondary: 0 0% 14.9%;
    --secondary-foreground: 0 0% 98%;
    --muted: 0 0% 14.9%;
    --muted-foreground: 0 0% 63.9%;
    --accent: 0 0% 14.9%;
    --accent-foreground: 0 0% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 14.9%;
    --input: 0 0% 14.9%;
    --ring: 0 0% 83.1%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
"""

POSTCSS_CONFIG = """\
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
"""

TAILWIND_CONFIG = r"""/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
"""

VITE_CONFIG = """\
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
"""

COMPONENTS_JSON = """\
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.js",
    "css": "src/index.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
"""


def _run(args, **kwargs):
    kwargs.setdefault("check", True)
    return subprocess.run(args, **kwargs)


def _patch_json_file(path: Path, patch: dict):
    """Read a JSON file (stripping // comments), deep-merge patch, and write back."""
    text = path.read_text()
    # Strip single-line comments
    text = re.sub(r'//.*', '', text)
    # Strip trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    data = json.loads(text)
    compiler_opts = data.setdefault("compilerOptions", {})
    compiler_opts.update(patch)
    path.write_text(json.dumps(data, indent=2))


def main():
    if len(sys.argv) < 2:
        print("Usage: python init-artifact.py <project-name>")
        sys.exit(1)

    project_name = sys.argv[1]

    # Detect Node version
    node_ver_raw = subprocess.run(
        ["node", "-v"], capture_output=True, text=True, check=True
    ).stdout.strip()
    node_major = int(node_ver_raw.lstrip("v").split(".")[0])
    print(f"Detected Node.js version: {node_major}")

    if node_major < 18:
        print(f"Error: Node.js 18 or higher is required (current: {node_ver_raw})")
        sys.exit(1)

    vite_version = "latest" if node_major >= 20 else "5.4.11"
    print(f"Using Vite {vite_version} (Node {node_major})")

    # Check pnpm
    if not shutil.which("pnpm"):
        print("pnpm not found. Installing pnpm...")
        _run(["npm", "install", "-g", "pnpm"])

    # Check components tarball
    if not COMPONENTS_TARBALL.is_file():
        print(f"Error: shadcn-components.tar.gz not found at {COMPONENTS_TARBALL}")
        sys.exit(1)

    print(f"Creating new React + Vite project: {project_name}")
    _run(["pnpm", "create", "vite", project_name, "--template", "react-ts"])

    # Work inside the project directory
    project_dir = Path.cwd() / project_name
    os.chdir(project_dir)

    # Clean up Vite template index.html
    print("Cleaning up Vite template...")
    index_html = Path("index.html")
    html = index_html.read_text()
    html = re.sub(r'<link rel="icon"[^>]*vite\.svg[^>]*/?\>', '', html)
    html = re.sub(r'<title>.*?</title>', f'<title>{project_name}</title>', html)
    index_html.write_text(html)

    print("Installing base dependencies...")
    _run(["pnpm", "install"])

    if node_major < 20:
        print(f"Pinning Vite to {vite_version} for Node 18 compatibility...")
        _run(["pnpm", "add", "-D", f"vite@{vite_version}"])

    print("Installing Tailwind CSS and dependencies...")
    _run(["pnpm", "install", "-D",
          "tailwindcss@3.4.1", "postcss", "autoprefixer", "@types/node", "tailwindcss-animate"])
    _run(["pnpm", "install",
          "class-variance-authority", "clsx", "tailwind-merge", "lucide-react", "next-themes"])

    print("Creating Tailwind and PostCSS configuration...")
    Path("postcss.config.js").write_text(POSTCSS_CONFIG)
    Path("tailwind.config.js").write_text(TAILWIND_CONFIG)
    Path("src/index.css").write_text(INDEX_CSS)

    # Path aliases
    print("Adding path aliases to tsconfig.json...")
    patch = {"baseUrl": ".", "paths": {"@/*": ["./src/*"]}}
    for tsconf in ["tsconfig.json", "tsconfig.app.json"]:
        p = Path(tsconf)
        if p.is_file():
            _patch_json_file(p, patch)

    print("Updating Vite configuration...")
    Path("vite.config.ts").write_text(VITE_CONFIG)

    # Install all shadcn/ui dependencies
    print("Installing shadcn/ui dependencies...")
    _run(["pnpm", "install",
          "@radix-ui/react-accordion", "@radix-ui/react-aspect-ratio",
          "@radix-ui/react-avatar", "@radix-ui/react-checkbox",
          "@radix-ui/react-collapsible", "@radix-ui/react-context-menu",
          "@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu",
          "@radix-ui/react-hover-card", "@radix-ui/react-label",
          "@radix-ui/react-menubar", "@radix-ui/react-navigation-menu",
          "@radix-ui/react-popover", "@radix-ui/react-progress",
          "@radix-ui/react-radio-group", "@radix-ui/react-scroll-area",
          "@radix-ui/react-select", "@radix-ui/react-separator",
          "@radix-ui/react-slider", "@radix-ui/react-slot",
          "@radix-ui/react-switch", "@radix-ui/react-tabs",
          "@radix-ui/react-toast", "@radix-ui/react-toggle",
          "@radix-ui/react-toggle-group", "@radix-ui/react-tooltip"])
    _run(["pnpm", "install",
          "sonner", "cmdk", "vaul", "embla-carousel-react",
          "react-day-picker", "react-resizable-panels", "date-fns",
          "react-hook-form", "@hookform/resolvers", "zod"])

    # Extract shadcn components
    print("Extracting shadcn/ui components...")
    import tarfile
    with tarfile.open(COMPONENTS_TARBALL, "r:gz") as tar:
        tar.extractall(path="src")

    # components.json
    print("Creating components.json config...")
    Path("components.json").write_text(COMPONENTS_JSON)

    print()
    print("Setup complete! You can now use Tailwind CSS and shadcn/ui in your project.")
    print()
    print("Included components (40+ total):")
    print("  accordion, alert, aspect-ratio, avatar, badge, breadcrumb, button,")
    print("  calendar, card, carousel, checkbox, collapsible, command, context-menu,")
    print("  dialog, drawer, dropdown-menu, form, hover-card, input, label, menubar,")
    print("  navigation-menu, popover, progress, radio-group, resizable, scroll-area,")
    print("  select, separator, sheet, skeleton, slider, sonner, switch, table, tabs,")
    print("  textarea, toast, toggle, toggle-group, tooltip")
    print()
    print("To start developing:")
    print(f"  cd {project_name}")
    print("  pnpm dev")
    print()
    print("Import components like:")
    print("  import { Button } from '@/components/ui/button'")
    print("  import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'")
    print("  import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog'")


if __name__ == "__main__":
    main()
