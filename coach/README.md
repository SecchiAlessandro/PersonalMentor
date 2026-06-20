# Personal Coach — web sub-app

The **Personal Coach** is section 2 of the PersonalMentor newspaper. It is a daily
~2-minute energy check-in → four energies on a single **energy wheel** →
warm, balance-focused coaching. Grounded in Loehr & Schwartz's *The Power of Full
Engagement*.

It is a web translation of the **Full Engagement** SwiftUI app
(`../../LifeCoach/FullEngagement`), trimmed for embedding here: the optional
on-device **AI coach** (WebLLM/WebGPU) has been removed, so **coaching is always
deterministic and rule-based**. It is **local-first and private**: all data stays
in the browser (IndexedDB), there is no server.

The newspaper embeds this app via an `<iframe>` in its "Personal Coach" tab, which
keeps the app's Tailwind styles isolated from the newspaper's hand-written CSS.

## Stack

- **React + Vite + TypeScript** (single-page app, no backend)
- **Tailwind CSS v4** with CSS-variable design tokens (light/dark follow the OS)
- **Dexie / IndexedDB** for on-device persistence
- **Recharts** for the history trend charts

## Build

The build is committed to `../output/web/coach/` (a deployed GitHub Pages artifact),
so it only needs rebuilding when this source changes:

```bash
cd coach
npm install        # first time only
npm run build      # → ../output/web/coach/
```

`vite.config.ts` sets `base: './'` and `build.outDir: ../output/web/coach` so the
output works under `alessandrosecchi.com/PersonalMentor/web/coach/`.

Other scripts: `npm run dev` (local dev server), `npm run preview` (serve the
build), `npm run typecheck`.

## Features

- **Onboarding** — 3-step intro (purpose → daily habits → ready).
- **Daily check-in** — the ~2-minute questionnaire producing the four energy scores.
- **Today (dashboard)** — energy wheel, balance/bottleneck, rule-based coaching text.
- **History** — trend charts and sparklines over time.
- **Settings** — purpose, ritual goals, data export (JSON/CSV), privacy note.

Starts **empty** — the wheel and charts populate from the user's own check-ins (no
mock-data seeding).

## Structure

```
src/
├── models/energy.ts        # Energy, EnergyScores, Scoring, QuestionBank
├── coach/ruleBasedCoach.ts # balance-band coaching templates (always used)
├── coach/index.ts          # coach factory — deterministic rule-based only
├── store/                  # Dexie schema + store ops + live hooks
├── theme/theme.ts          # JS color tokens for SVG/charts
├── index.css               # Tailwind + CSS-variable design tokens
├── components/             # Card, buttons, EnergyWheel, charts, Modal
└── views/                  # Onboarding, Dashboard, CheckIn, History, Settings
```

## Parity notes

The deterministic core (balance = `100 − (max − min)`, bottleneck with pyramid
tie-break, `physicalFloorCapping`, the 9-question bank, daily-set selection, and
the three coaching bands) is a line-for-line port of the SwiftUI app — same numbers,
same copy. The energy wheel uses the same screen-angle quadrant convention and hex
colors as SwiftUI (spiritual BR, emotional BL, physical TL, mental TR).
