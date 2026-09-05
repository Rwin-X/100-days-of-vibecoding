"""
Ex-command parsing for Vedit's command line (the ':' prompt).

Supports the commands people actually reach for day to day:
  :w [file]        write (save)
  :w!              force write
  :q                quit current tab
  :q!               force quit, discard changes
  :wq / :x          write then quit
  :qa / :qa!        quit all tabs
  :wqa              write and quit all tabs
  :e <file>         open a file in a new tab
  :tabnew [file]    open a new tab
  :bn / :bp         next / previous tab
  :set nu / nonu    toggle line numbers (line numbers are always on here,
                    kept for familiarity / no-op)
  :theme <name>     switch color theme
  :%s/pat/rep/g     substitute (whole buffer or a line range)
  :<N>              jump to line N
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedCommand:
    name: str
    args: str = ""
    force: bool = False
    range_spec: str = ""


RANGE_RE = re.compile(r"^(%|'<,'>|\d+(,\d+)?)?")
SUBSTITUTE_RE = re.compile(r"^s/(.*?)(?<!\\)/(.*?)(?<!\\)/([a-zA-Z]*)$")


def parse(raw: str) -> ParsedCommand:
    raw = raw.strip()
    m = RANGE_RE.match(raw)
    range_spec = m.group(0) if m else ""
    rest = raw[len(range_spec):].strip()

    if not rest:
        if range_spec:
            return ParsedCommand(name="goto", args=range_spec, range_spec=range_spec)
        return ParsedCommand(name="")

    if rest.startswith("s/") or rest.startswith("s,"):
        return ParsedCommand(name="substitute", args=rest[1:], range_spec=range_spec)

    force = rest.endswith("!")
    body = rest[:-1] if force else rest
    parts = body.split(None, 1)
    name = parts[0] if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    return ParsedCommand(name=name, args=args, force=force, range_spec=range_spec)


def parse_substitute(args: str):
    """Parse 'pat/rep/flags' (the 's' has already been stripped)."""
    m = SUBSTITUTE_RE.match("s" + args) if not args.startswith("s") else None
    # args passed in is already without leading 's', formatted like /pat/rep/flags
    body = "s" + args
    m = SUBSTITUTE_RE.match(body)
    if not m:
        return None
    pattern, replacement, flags = m.groups()
    pattern = pattern.replace(r"\/", "/")
    replacement = replacement.replace(r"\/", "/")
    return pattern, replacement, flags
