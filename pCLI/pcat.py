#!/usr/bin/env python3
"""
pcat - a minimal, bat-like syntax-highlighting file viewer for the terminal.

Usage:
    pcat.py <file> [file ...]
    pcat.py --theme=monokai <file>
    cat file.py | pcat.py -

Features:
    - Line numbers in a dim gutter, separated by a vertical bar
    - Header showing the file name
    - Syntax highlighting for the whole file, including fenced code
      blocks *inside* Markdown files (like the bat screenshot)
    - Falls back to plain text if the file type is unknown
"""

import argparse
import os
import sys

from pygments import highlight
from pygments.formatters import Terminal256Formatter
from pygments.lexers import TextLexer, get_lexer_for_filename
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Token,
)
from pygments.util import ClassNotFound


class BatlikeStyle(Style):
    """A minimal dark style matching the reference bat/terminal screenshot:
    orange headings, pink keywords/interpolation, soft green for identifiers
    used as builtins, muted gray comments and gutter text.
    """

    background_color = "#1a1a1a"
    styles = {
        Token: "#f2f2f2",
        Text: "#f2f2f2",
        Comment: "italic #6a6a6a",
        Keyword: "#ff6ac1",
        Keyword.Constant: "#ff6ac1",
        Keyword.Declaration: "#ff6ac1",
        Keyword.Namespace: "#ff6ac1",
        Name: "#f2f2f2",
        Name.Builtin: "#8be9fd",
        Name.Function: "#8be9fd",
        Name.Class: "#8be9fd",
        Name.Decorator: "#ff6ac1",
        Name.Variable: "#f2f2f2",
        String: "#e6db74",
        String.Interpol: "#ff6ac1",
        String.Backtick: "#7a7a7a",
        Number: "#bd93f9",
        Operator: "#ff6ac1",
        Punctuation: "#f2f2f2",
        Generic.Heading: "bold #f5a962",
        Generic.Subheading: "bold #f5a962",
        Generic.Emph: "italic #ff6ac1",
        Generic.Strong: "bold #f2f2f2",
        Generic.Deleted: "#ff5555",
        Generic.Inserted: "#50fa7b",
        Error: "#ff5555",
    }

# ---------------------------------------------------------------------------
# Palette (kept close to the reference screenshot: dark background,
# muted gutter, orange headings, pink keywords/strings)
# ---------------------------------------------------------------------------

RESET = "\x1b[0m"
DIM = "\x1b[38;5;240m"          # gutter numbers / separators
HEADER_ARROW = "\x1b[38;5;250m"  # ▶
HEADER_CMD = "\x1b[38;5;150m"    # "bat" style green for the command name
HEADER_FILE = "\x1b[4m\x1b[1m"   # bold underline filename

GUTTER_WIDTH = 4  # matches the screenshot's right-aligned numbers

ARROW_CHAR = "\u25b6"    # ▶
RULE_CHAR = "\u2500"     # ─
BAR_CHAR = "\u2502"      # │


def make_formatter(theme: str) -> Terminal256Formatter:
    style = BatlikeStyle if theme == "batlike" else theme
    return Terminal256Formatter(style=style, bg="dark")


def get_lexer(path: str, code: str):
    """Resolve a Pygments lexer for the given path, falling back to plain text."""
    if path == "-" or path is None:
        return TextLexer(stripnl=False)
    try:
        return get_lexer_for_filename(path, code, stripnl=False)
    except ClassNotFound:
        # Unknown extension: try to sniff Markdown-ish content, else plain text
        return TextLexer(stripnl=False)


def highlight_code(code: str, lexer, formatter) -> str:
    """Highlight code and return a list of ANSI-colored lines (no trailing newline)."""
    rendered = highlight(code, lexer, formatter)
    # pygments adds a single trailing newline; strip it, then split into lines
    return rendered.rstrip("\n").split("\n")


def print_header(display_name: str, term_width: int):
    rule = RULE_CHAR * term_width
    print(f"{HEADER_ARROW}{ARROW_CHAR}{RESET} {HEADER_CMD}pcat{RESET} {HEADER_FILE}{display_name}{RESET}")
    print(f"{DIM}{rule}{RESET}")


def print_footer(term_width: int):
    rule = RULE_CHAR * term_width
    print(f"{DIM}{rule}{RESET}")


def render_file(path: str, theme: str, show_header: bool = True, number_from: int = 1):
    if path == "-":
        code = sys.stdin.read()
        display_name = "(stdin)"
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        display_name = os.path.basename(path)

    lexer = get_lexer(path, code)
    formatter = make_formatter(theme)

    lines = highlight_code(code, lexer, formatter)

    term_width = min(shutil_width(), 100)

    if show_header:
        print_header(display_name, term_width)

    for i, line in enumerate(lines, start=number_from):
        num = f"{i:>{GUTTER_WIDTH}}"
        print(f"{DIM}{num}{RESET} {DIM}{BAR_CHAR}{RESET} {line}")

    if show_header:
        print_footer(term_width)


def shutil_width(default: int = 80) -> int:
    try:
        import shutil
        return shutil.get_terminal_size((default, 24)).columns
    except Exception:
        return default


def main():
    parser = argparse.ArgumentParser(
        prog="pcat",
        description="A minimal, bat-like syntax-highlighting file viewer.",
    )
    parser.add_argument("files", nargs="*", default=["-"], help="Files to display ('-' for stdin)")
    parser.add_argument(
        "--theme",
        default="batlike",
        help="Style name (default: batlike, matches the reference screenshot). "
        "Also try any Pygments style: dracula, native, one-dark, nord, gruvbox-dark",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="Don't print the file name header/footer, just numbered lines",
    )
    parser.add_argument(
        "-n",
        "--start-line",
        type=int,
        default=1,
        help="Line number to start counting from (default: 1)",
    )
    args = parser.parse_args()

    for path in args.files:
        try:
            render_file(
                path,
                theme=args.theme,
                show_header=not args.no_header,
                number_from=args.start_line,
            )
        except FileNotFoundError:
            print(f"pcat: {path}: No such file or directory", file=sys.stderr)
            sys.exit(1)
        except IsADirectoryError:
            print(f"pcat: {path}: Is a directory", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
