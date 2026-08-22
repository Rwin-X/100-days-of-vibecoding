# pcatgif

Render any source file as a "typing" animation and export it as a GIF — built as a companion to [`pcat`](./README.md), sharing the same syntax-highlighting palette so terminal output and GIFs look consistent.

## Features

- **Typing animation** — code appears line by line (fast) or character by character (real typing feel), with a blinking cursor
- **Same theme as `pcat`** — the custom `batlike` palette: dark background, orange headings, pink keywords/operators, cyan builtins, muted italic comments
- **Syntax highlighting** for 500+ languages via Pygments, including fenced code blocks *inside* Markdown files
- **Auto-scrolling** — long files scroll like a real editor once they exceed the visible window instead of producing a giant image
- **Minimal terminal-style header** with the file name, matching `pcat`'s look
- Fully configurable: font size, image width, frame rate, end-hold duration, visible line count

## Requirements

- Python 3.8+
- [Pygments](https://pygments.org/)
- [Pillow](https://python-pillow.org/)

## Installation

```bash
pip install pygments pillow
```

Then run it directly, or drop it next to `pcat.py`:

```bash
git clone https://github.com/black8arch/devforge.git
cd devforge/pcat
python3 pcatgif.py --help
```

## Usage

```bash
# Basic: animate a file, saved as file.gif next to it
python3 pcatgif.py file.py

# Custom output path
python3 pcatgif.py file.py -o demo.gif

# Character-by-character typing instead of line-by-line
python3 pcatgif.py file.py --speed char

# Tune frame rate and how long the finished code stays on screen
python3 pcatgif.py file.py --fps 24 --hold 1.5

# Bigger canvas / larger font
python3 pcatgif.py file.py --font-size 18 --width 900

# Show fewer lines at once before it starts scrolling
python3 pcatgif.py file.py --max-lines 15
```

## Options

| Flag | Description |
|---|---|
| `-o, --output PATH` | Output GIF path. Default: `<file>.gif` next to the source file |
| `--speed {line,char}` | `line`: reveal one full line per frame — fast, compact GIF. `char`: reveal character by character — slower, real typing feel. Default: `line` |
| `--fps N` | Frames per second (default: `18`) |
| `--hold SECONDS` | How long the finished, fully-typed file stays on screen at the end (default: `2.0`) |
| `--font-size PX` | Font size in pixels (default: `16`) |
| `--width PX` | Image width in pixels (default: `860`) |
| `--max-lines N` | Max lines visible at once before the view scrolls, like a real editor (default: `24`) |
| `-h, --help` | Show help and exit |

## How it works

The source file is tokenized with the same Pygments lexer and `batlike` style used by `pcat.py`, turning it into a grid of styled characters (color, bold, italic) rather than plain text. Each animation frame is drawn with Pillow (`DejaVu Sans Mono` in regular/bold/italic/bold-italic) onto a fixed-size dark canvas, revealing more of the file per frame. Once the number of typed lines exceeds `--max-lines`, the window scrolls forward, keeping the frame size constant regardless of file length. All frames are then encoded into a single looping GIF.

## Tips

- `--speed line` is the better default for longer files — a `--speed char` GIF grows roughly one frame per few characters, so file size and render time scale up quickly on big files
- For a "code snippet for social media" look, keep `--max-lines` around `10-15` and `--width` around `700-800`
- Combine with `pcat.py` in the same repo folder so both tools stay in sync if you tweak the color palette — the `BatlikeStyle` class is duplicated in each file on purpose, to keep both scripts dependency-free of each other

## License

MIT
