#!/usr/bin/env python3
"""
pcatgif - render a source file as a "typing" animation and export it as a GIF.

Takes any text/code file, syntax-highlights it (via Pygments, same palette
as pcat.py), and renders an animated GIF that looks like the code is being
typed into a minimal dark terminal window, line by line / char by char.

Usage:
    pcatgif.py file.py
    pcatgif.py file.py -o output.gif
    pcatgif.py file.py --speed line          # reveal whole lines at a time (fast, short gif)
    pcatgif.py file.py --speed char          # reveal character by character (slower, "typing" feel)
    pcatgif.py file.py --fps 24 --hold 1.5   # tune frame rate / end-hold duration
    pcatgif.py file.py --font-size 18 --width 900

Requires: pygments, pillow
"""

import argparse
import os
import sys

from pygments import lex
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

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Palette - same "batlike" theme used by pcat.py, so GIFs and terminal output
# look consistent with each other.
# ---------------------------------------------------------------------------


class BatlikeStyle(Style):
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


BG_COLOR = (0x1a, 0x1a, 0x1a)
GUTTER_COLOR = (0x5a, 0x5a, 0x5a)
RULE_COLOR = (0x3a, 0x3a, 0x3a)
HEADER_ARROW_COLOR = (0xc8, 0xc8, 0xc8)
HEADER_CMD_COLOR = (0x9a, 0xd6, 0x8f)
HEADER_FILE_COLOR = (0xff, 0xff, 0xff)
CURSOR_COLOR = (0xf2, 0xf2, 0xf2)
DEFAULT_TEXT_COLOR = (0xf2, 0xf2, 0xf2)

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ],
    "italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf",
    ],
    "bold_italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-BoldOblique.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-BoldItalic.ttf",
    ],
}


def _load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_lexer(path: str, code: str):
    if path is None:
        return TextLexer(stripnl=False)
    try:
        return get_lexer_for_filename(path, code, stripnl=False)
    except ClassNotFound:
        return TextLexer(stripnl=False)


class StyledChar:
    __slots__ = ("char", "color", "bold", "italic")

    def __init__(self, char, color, bold, italic):
        self.char = char
        self.color = color
        self.bold = bold
        self.italic = italic


def tokenize_to_lines(code: str, lexer, style_cls):
    """Turn source code into a list of lines, each a list of StyledChar."""
    # StyleMeta makes the *class* itself iterable, already resolving
    # inheritance for every token subtype - no manual walk-up needed.
    style_map = dict(style_cls)

    def lookup(token_type):
        return style_map.get(token_type, {"color": None, "bold": False, "italic": False})

    lines = [[]]
    for token_type, value in lex(code, lexer):
        ndef = lookup(token_type)
        color = hex_to_rgb(ndef["color"]) if ndef["color"] else DEFAULT_TEXT_COLOR
        bold = bool(ndef["bold"])
        italic = bool(ndef["italic"])
        for ch in value:
            if ch == "\n":
                lines.append([])
            else:
                lines[-1].append(StyledChar(ch, color, bold, italic))
    if lines and not lines[-1]:
        lines.pop()
    return lines


class CodeGifRenderer:
    def __init__(
        self,
        lines,
        display_name: str,
        font_size: int = 16,
        width: int = 860,
        max_lines_visible: int = 24,
        gutter_digits: int = 3,
    ):
        self.lines = lines
        self.display_name = display_name
        self.font_size = font_size
        self.width = width
        self.max_lines_visible = max_lines_visible
        self.gutter_digits = gutter_digits

        self.font_regular = _load_font("regular", font_size)
        self.font_bold = _load_font("bold", font_size)
        self.font_italic = _load_font("italic", font_size)
        self.font_bold_italic = _load_font("bold_italic", font_size)
        self.font_header = _load_font("bold", font_size)

        bbox = self.font_regular.getbbox("Mg")
        self.char_w = self.font_regular.getlength("M")
        self.line_h = int((bbox[3] - bbox[1]) * 1.9)

        self.pad_x = 20
        self.pad_top = 14
        self.header_h = int(self.line_h * 1.7)
        self.gutter_w = int(self.char_w * (gutter_digits + 2))

        n_visible = min(len(self.lines), max_lines_visible) or 1
        self.body_h = self.line_h * n_visible + self.pad_top
        self.height = self.header_h + self.body_h + self.pad_top

    def _font_for(self, bold: bool, italic: bool):
        if bold and italic:
            return self.font_bold_italic
        if bold:
            return self.font_bold
        if italic:
            return self.font_italic
        return self.font_regular

    def _draw_header(self, draw: ImageDraw.ImageDraw):
        x = self.pad_x
        y = self.pad_top
        arrow = "\u25b6"
        draw.text((x, y), arrow, font=self.font_header, fill=HEADER_ARROW_COLOR)
        x += self.font_header.getlength(arrow + " ")
        draw.text((x, y), "pcat", font=self.font_header, fill=HEADER_CMD_COLOR)
        x += self.font_header.getlength("pcat ")
        draw.text((x, y), self.display_name, font=self.font_header, fill=HEADER_FILE_COLOR)
        underline_w = self.font_header.getlength(self.display_name)
        underline_y = y + self.font_header.size + 2
        draw.line(
            [(x, underline_y), (x + underline_w, underline_y)],
            fill=HEADER_FILE_COLOR,
            width=1,
        )
        rule_y = self.header_h - int(self.line_h * 0.3)
        draw.line(
            [(self.pad_x, rule_y), (self.width - self.pad_x, rule_y)],
            fill=RULE_COLOR,
            width=1,
        )

    def _draw_gutter(self, draw: ImageDraw.ImageDraw, row_idx: int, y: int):
        num_str = str(row_idx + 1).rjust(self.gutter_digits)
        draw.text((self.pad_x, y), num_str, font=self.font_regular, fill=GUTTER_COLOR)
        bar_x = self.pad_x + self.gutter_w - self.char_w
        draw.text((bar_x, y), "\u2502", font=self.font_regular, fill=RULE_COLOR)

    def render_frame(self, visible_lines, cursor_pos=None, scroll_offset=0):
        """visible_lines: list of rows (list[StyledChar]) already windowed to
        what should show this frame. cursor_pos: row index within that
        windowed list to draw a blinking cursor on, or None to hide it."""
        img = Image.new("RGB", (self.width, self.height), BG_COLOR)
        draw = ImageDraw.Draw(img)
        self._draw_header(draw)

        text_x0 = self.pad_x + self.gutter_w
        y = self.header_h + self.pad_top // 2

        for row_idx, row in enumerate(visible_lines):
            self._draw_gutter(draw, scroll_offset + row_idx, y)
            x = text_x0
            if row:
                for sc in row:
                    font = self._font_for(sc.bold, sc.italic)
                    draw.text((x, y), sc.char, font=font, fill=sc.color)
                    x += self.char_w
            if cursor_pos is not None and cursor_pos == row_idx:
                cx = text_x0 + len(row) * self.char_w if row else text_x0
                draw.rectangle(
                    [cx, y, cx + max(2, self.char_w * 0.55), y + self.line_h * 0.85],
                    fill=CURSOR_COLOR,
                )
            y += self.line_h

        return img


def build_frames(lines, display_name, speed, font_size, width, max_lines_visible):
    renderer = CodeGifRenderer(
        lines,
        display_name,
        font_size=font_size,
        width=width,
        max_lines_visible=max_lines_visible,
    )

    frames = []
    total_lines = len(lines)
    window = max_lines_visible

    def windowed(up_to_row, partial_row=None):
        """Return (visible_rows, scroll_offset) for lines[0:up_to_row] plus
        an optional in-progress partial_row appended at the end."""
        start = max(0, up_to_row - window + 1)
        rows = list(lines[start:up_to_row])
        if partial_row is not None:
            rows.append(partial_row)
        return rows, start

    if speed == "line":
        for i in range(total_lines):
            rows, offset = windowed(i, lines[i])
            cursor_row = len(rows) - 1
            frames.append(renderer.render_frame(rows, cursor_pos=cursor_row, scroll_offset=offset))
    else:  # char-by-char
        for i in range(total_lines):
            line = lines[i]
            step = max(1, len(line) // 14) if len(line) > 28 else 1
            positions = list(range(0, len(line), step)) + [len(line)]
            for c in positions:
                partial = line[:c]
                rows, offset = windowed(i, partial)
                cursor_row = len(rows) - 1
                frames.append(renderer.render_frame(rows, cursor_pos=cursor_row, scroll_offset=offset))

    # Final resting frames: full file visible (windowed), cursor blinks twice
    rows, offset = windowed(total_lines)
    cursor_row = len(rows) - 1
    frames.append(renderer.render_frame(rows, cursor_pos=None, scroll_offset=offset))
    frames.append(renderer.render_frame(rows, cursor_pos=cursor_row, scroll_offset=offset))
    frames.append(renderer.render_frame(rows, cursor_pos=None, scroll_offset=offset))

    return frames


def save_gif(frames, out_path, fps, hold_seconds):
    if not frames:
        raise ValueError("No frames to render")

    frame_duration_ms = int(1000 / fps)
    durations = [frame_duration_ms] * len(frames)
    # Extend the last frame so the finished code stays on screen
    durations[-1] = int(hold_seconds * 1000)

    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="pcatgif",
        description="Render a source file as a typing animation exported to GIF.",
    )
    parser.add_argument("file", help="Path to the source/text file to animate")
    parser.add_argument("-o", "--output", default=None, help="Output GIF path (default: <file>.gif)")
    parser.add_argument(
        "--speed",
        choices=["line", "char"],
        default="line",
        help="'line': reveal one full line per frame (fast, compact gif). "
        "'char': reveal character by character (slower, real 'typing' feel). Default: line",
    )
    parser.add_argument("--fps", type=int, default=18, help="Frames per second (default: 18)")
    parser.add_argument("--hold", type=float, default=2.0, help="Seconds to hold the final frame (default: 2.0)")
    parser.add_argument("--font-size", type=int, default=16, help="Font size in px (default: 16)")
    parser.add_argument("--width", type=int, default=860, help="Image width in px (default: 860)")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=24,
        help="Max lines visible at once before the view starts scrolling (default: 24)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"pcatgif: {args.file}: No such file", file=sys.stderr)
        sys.exit(1)

    with open(args.file, "r", encoding="utf-8", errors="replace") as f:
        code = f.read()

    display_name = os.path.basename(args.file)
    lexer = get_lexer(args.file, code)
    lines = tokenize_to_lines(code, lexer, BatlikeStyle)

    if not lines:
        print("pcatgif: file is empty, nothing to animate", file=sys.stderr)
        sys.exit(1)

    gutter_digits = max(2, len(str(len(lines))))

    out_path = args.output or (os.path.splitext(args.file)[0] + ".gif")

    print(f"Rendering {len(lines)} lines ({args.speed} mode)...", file=sys.stderr)
    frames = build_frames(
        lines,
        display_name,
        speed=args.speed,
        font_size=args.font_size,
        width=args.width,
        max_lines_visible=args.max_lines,
    )
    print(f"Encoding {len(frames)} frames to GIF...", file=sys.stderr)
    save_gif(frames, out_path, fps=args.fps, hold_seconds=args.hold)
    print(f"Saved: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
