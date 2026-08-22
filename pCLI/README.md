# pcat

A minimal, `bat`-like syntax-highlighting file viewer for the terminal — written in Python with [Pygments](https://pygments.org/).

```
▶ pcat sample.py
──────────────────────────────────────────────
   1 │ # Simple network scanner example
   2 │ import socket
   3 │
   4 │
   5 │ class PortScanner:
   6 │     """Scans a host for open TCP ports."""
   7 │
   8 │     def __init__(self, host: str, timeout: float = 0.5):
   9 │         self.host = host
  10 │         self.timeout = timeout
──────────────────────────────────────────────
```

## Features

- **Line numbers** in a dim gutter, separated by a vertical bar
- **Syntax highlighting** for 500+ languages via Pygments — including fenced code blocks *inside* Markdown files (Python, Ruby, etc. get highlighted even when nested in a `.md` file)
- **Minimal header** showing the file name, no clutter
- **Custom `batlike` theme** by default — dark background, orange headings, pink keywords/operators, cyan builtins, muted comments
- Works with **any Pygments style** (`dracula`, `nord`, `one-dark`, `gruvbox-dark`, ...)
- Reads from **stdin** for use in pipelines
- Graceful fallback to plain text for unknown file types

## Requirements

- Python 3.8+
- [Pygments](https://pygments.org/)

## Installation

```bash
pip install pygments
```

Then just drop `pcat.py` somewhere on your `PATH`, or run it directly:

```bash
git clone https://github.com/Rwin-x/Devforge.git
cd Devforge-/pCLI
python3 pcat.py --help
```

### Optional: use it as `pcat`

```bash
chmod +x pcat.py
sudo cp pcat.py /usr/local/bin/pcat
```

## Usage

```bash
# View a single file
pcat.py file.py

# View multiple files
pcat.py main.py utils.py

# Pipe input in
cat file.py | pcat.py -

# Use a different theme
pcat.py --theme=dracula file.py

# Just numbered lines, no header
pcat.py --no-header file.py

# Start line numbering from a custom offset
pcat.py -n 100 file.py
```

## Options

| Flag | Description |
|---|---|
| `--theme THEME` | Style to use. Default: `batlike`. Also accepts any [Pygments style](https://pygments.org/styles/) name (`dracula`, `native`, `one-dark`, `nord`, `gruvbox-dark`, ...) |
| `--no-header` | Skip the filename header/footer and print only numbered lines |
| `-n, --start-line N` | Line number to start counting from (default: `1`) |
| `-h, --help` | Show help and exit |

## How it works

`pcat` uses Pygments to lex and tokenize the input file, then renders it through a `Terminal256Formatter` for 256-color ANSI output. Markdown files are handled specially: Pygments' `MarkdownLexer` recursively highlights fenced code blocks using the language tagged after the triple backticks, so a Python snippet inside a `.md` file gets real Python highlighting rather than being treated as plain text.

## License

MIT
