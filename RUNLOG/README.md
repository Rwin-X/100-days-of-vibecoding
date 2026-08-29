# RUN LOG

A minimal, premium, fully client-side running dashboard. Log every run, and let the app automatically compute weekly totals, trends, and rule-based training feedback — no backend, no account, no tracking.

![No Backend](https://img.shields.io/badge/backend-none-black) ![Storage](https://img.shields.io/badge/storage-localStorage-black) ![Dependencies](https://img.shields.io/badge/dependencies-zero-black) ![License](https://img.shields.io/badge/license-MIT-black)

---

## Overview

RUN LOG is a single-file web app for runners who want a clean, private place to track sessions and understand their training load week over week — without a fitness-app account, ads, or a server.

Every run is entered manually. From that raw data, the app derives pace, weekly aggregates, multi-week trends, and short, rule-based feedback (e.g. *"Weekly distance increased"*, *"Consider prioritizing recovery"*). All data lives in the browser's `localStorage` — nothing leaves the device unless you export it yourself.

## Features

### Data entry
- Log **date, distance (km), duration, average heart rate, calories, run type, RPE (1–10), and notes** for every session.
- **Pace is always calculated automatically** from distance + duration — never entered manually — with a live preview while typing.
- Edit or delete any past entry.

### Dashboard
- **Today** — today's run at a glance (distance, duration, pace, RPE), or a prompt to log one.
- **This Week** — total distance, total time, run count, longest run, average pace, and average RPE.
- A per-day distance bar chart for the current week.
- Auto-generated training feedback for the week in progress.

### Weekly Report
- Full breakdown for any week, with **Prev / Next** navigation to review past weeks:
  - Distance per day
  - 6-week distance trend (line chart)
  - 6-week pace trend (line chart)
  - Run-type distribution (Easy / Tempo / Interval / Long Run)
  - Long run distance & training consistency
  - Side-by-side **comparison with the previous week** (distance, time, run count, pace — with up/down deltas)
  - Rule-based training feedback for that week

### Training feedback (rule-based, not medical)
Generated from real week-over-week deltas — distance change, pace change, session count, and average RPE — for example:
- *"Weekly distance increased by X% compared to last week."*
- *"Your average pace improved by ~X seconds per km."*
- *"Distance is up and perceived effort is high at the same time. Consider prioritizing recovery this week."*

The app never makes medical claims or diagnoses — feedback is limited to training-load observations.

### History
- Full run log in a sortable table (click any column header).
- Filter by run type.
- Inline edit and delete.

### Data & backup
- **Export** all runs as a timestamped JSON backup.
- **Import** a JSON backup — merges with existing data and skips duplicate entries by ID.
- **Clear all data** with a double confirmation.

### Interface
- Minimal, monochrome, Swiss/Apple-inspired design — black, white, and gray only.
- **Light / Dark mode**, remembered across visits.
- Fully responsive: desktop, tablet, and mobile (with a bottom tab bar on small screens).
- Subtle motion only — chart bars, reveal-on-scroll, and toast confirmations.

## Tech stack

- HTML5
- CSS3 (custom properties, CSS Grid/Flexbox, no framework)
- Vanilla JavaScript (no build step, no dependencies)
- `localStorage` for all persistence
- Inline SVG for line charts — no charting library

There is no backend, no database, no authentication, and no external network calls. The entire app is one HTML file.

## Getting started

No installation or build step required.

1. Download [`run-log.html`](./run-log.html).
2. Open it in any modern browser (Chrome, Firefox, Safari, Edge).
3. Start logging runs with **+ Add Run**.

To use it like an app, you can also host the single file on any static host (GitHub Pages, Netlify, Vercel, or a personal server) — it needs nothing but static file serving.

## Data & privacy

- All data is stored **only** in your browser's `localStorage`, under the key `runlog_runs_v1` (theme preference under `runlog_theme`).
- Nothing is sent to any server — the app makes no network requests.
- Data is local to a single browser profile on a single device. Use **Export** regularly to back up your log, and **Import** to move it to another browser or device.
- Clearing your browser's site data, or using a different browser/device, will not carry your history over unless you've exported and re-imported it.

## Project structure

```
run-log.html   # the entire application — markup, styles, and logic in one file
```

## Roadmap ideas

Not implemented, but natural next steps if this grows beyond a single file:

- GPS route import (GPX/TCX)
- Custom weekly goals and target-based feedback
- Multi-device sync (would require a backend)
- Additional chart types (elevation, cadence)

## License

MIT — use, modify, and share freely.
