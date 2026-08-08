
# QR Live

A minimal, live-updating QR code generator. Type on the left, watch the QR code render on the right — no button, no delay.

Available as a single-file **web app** (HTML/CSS/JS) and a **desktop app** (Python + PyQt6).

<div align="center">
<sub>status: stable &nbsp;·&nbsp; python 3.9+ &nbsp;·&nbsp; license: MIT</sub>
</div>

---

## Layout

A two-pane window split straight down the middle. The left pane holds a text field labeled `TEXT`; the right pane holds the QR code with a character count beneath it. No buttons, no menus — the QR code simply reflects whatever is typed.

## Features

- **Live rendering** — the QR code updates on every keystroke, no submit button
- **Minimal UI** — flat dark theme, no clutter, one job done well
- **Two flavors** — a zero-dependency HTML page or a native PyQt6 desktop app
- **Empty state** — a quiet placeholder instead of a blank or broken QR when the field is empty
- **Zero network calls** — QR codes are generated fully client-side / locally

## Getting started

### Web version

No build step, no server. Just open the file.

```bash
open qr-live.html
```

Or double-click it in your file browser. Works fully offline after the first load (QR rendering library is loaded from a CDN).

### Desktop version

```bash
pip install PyQt6 qrcode Pillow
python3 qr_live.py
```

## Project structure

```
qr-live/
├── qr-live.html    # Web version — HTML, CSS, JS in a single file
├── qr_live.py      # Desktop version — PyQt6
└── README.md
```

## How it works

| Layer | Web | Desktop |
|---|---|---|
| UI | Flexbox layout, split left/right | `QHBoxLayout` with two panels |
| Input | `<textarea>` + `input` event | `QTextEdit` + `textChanged` signal |
| QR engine | [`qrcodejs`](https://github.com/davidshimjs/qrcodejs) (CDN) | [`qrcode`](https://pypi.org/project/qrcode/) (PyPI) |
| Rendering | Canvas/table injected into the DOM | PNG generated in-memory, converted to `QPixmap` |

Both versions share the same visual language: a near-black background, a hairline border splitting the two panes, and a monospace font throughout.

## Roadmap

- [ ] Export QR as PNG / SVG
- [ ] Adjustable error-correction level (L / M / Q / H)
- [ ] Custom foreground/background colors
- [ ] Drag-and-drop text/URL input

## License

MIT — use it, fork it, ship it.

---

<div align="center">
<sub>Built by <a href="https://github.com/black8arch">black8arch</a></sub>
</div>
