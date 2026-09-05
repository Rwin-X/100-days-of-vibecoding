"""
Theme system for Vedit.

Each theme provides:
  - a UI palette (chrome: sidebar, status bar, tabs, gutter, etc.)
  - an editor palette (text background/foreground, selection, cursor line)
  - a Pygments-style token color map for syntax highlighting

Themes are plain dictionaries so new ones are trivial to add.
"""

THEMES = {
    "Obsidian": {
        "description": "Dark, desaturated, terminal-inspired. The default.",
        "bg": "#1B1D23",
        "bg_alt": "#20232B",
        "bg_elevated": "#262932",
        "fg": "#D4D7DE",
        "fg_muted": "#7A7F8C",
        "accent": "#7AA2F7",
        "accent_alt": "#9ECE6A",
        "border": "#2E313C",
        "selection": "#3B4261",
        "cursor_line": "#242732",
        "gutter_fg": "#4B4F5C",
        "gutter_fg_active": "#C0C4CC",
        "error": "#F7768E",
        "warning": "#E0AF68",
        "mode_normal": "#7AA2F7",
        "mode_insert": "#9ECE6A",
        "mode_visual": "#BB9AF7",
        "mode_command": "#E0AF68",
        "mode_replace": "#F7768E",
        "syntax": {
            "keyword": "#BB9AF7",
            "string": "#9ECE6A",
            "comment": "#5B6072",
            "number": "#FF9E64",
            "function": "#7AA2F7",
            "class": "#E0AF68",
            "operator": "#89DDFF",
            "builtin": "#2AC3DE",
            "variable": "#D4D7DE",
            "constant": "#FF9E64",
            "tag": "#F7768E",
            "attribute": "#BB9AF7",
        },
    },
    "Paper Light": {
        "description": "Clean light theme, high contrast for daytime work.",
        "bg": "#FAF9F7",
        "bg_alt": "#F1EFEB",
        "bg_elevated": "#FFFFFF",
        "fg": "#2B2A28",
        "fg_muted": "#8A857C",
        "accent": "#2563EB",
        "accent_alt": "#15803D",
        "border": "#E3E0D9",
        "selection": "#D9E4FB",
        "cursor_line": "#F1EFEB",
        "gutter_fg": "#B8B2A6",
        "gutter_fg_active": "#4A463F",
        "error": "#C0362C",
        "warning": "#B0740A",
        "mode_normal": "#2563EB",
        "mode_insert": "#15803D",
        "mode_visual": "#7C3AED",
        "mode_command": "#B0740A",
        "mode_replace": "#C0362C",
        "syntax": {
            "keyword": "#7C3AED",
            "string": "#15803D",
            "comment": "#9C9689",
            "number": "#B0540A",
            "function": "#2563EB",
            "class": "#B0740A",
            "operator": "#0E7490",
            "builtin": "#0E7490",
            "variable": "#2B2A28",
            "constant": "#B0540A",
            "tag": "#C0362C",
            "attribute": "#7C3AED",
        },
    },
    "Nord Deep": {
        "description": "Cold blue-grey palette, low glare for long sessions.",
        "bg": "#2E3440",
        "bg_alt": "#333A48",
        "bg_elevated": "#3B4252",
        "fg": "#E5E9F0",
        "fg_muted": "#7B87A1",
        "accent": "#88C0D0",
        "accent_alt": "#A3BE8C",
        "border": "#434C5E",
        "selection": "#434C5E",
        "cursor_line": "#333A48",
        "gutter_fg": "#4C566A",
        "gutter_fg_active": "#D8DEE9",
        "error": "#BF616A",
        "warning": "#EBCB8B",
        "mode_normal": "#88C0D0",
        "mode_insert": "#A3BE8C",
        "mode_visual": "#B48EAD",
        "mode_command": "#EBCB8B",
        "mode_replace": "#BF616A",
        "syntax": {
            "keyword": "#81A1C1",
            "string": "#A3BE8C",
            "comment": "#4C566A",
            "number": "#B48EAD",
            "function": "#88C0D0",
            "class": "#EBCB8B",
            "operator": "#81A1C1",
            "builtin": "#8FBCBB",
            "variable": "#E5E9F0",
            "constant": "#B48EAD",
            "tag": "#BF616A",
            "attribute": "#88C0D0",
        },
    },
    "Amber Terminal": {
        "description": "Warm amber-on-black, phosphor CRT inspired.",
        "bg": "#161311",
        "bg_alt": "#1C1815",
        "bg_elevated": "#211D19",
        "fg": "#E8C088",
        "fg_muted": "#8A6E4A",
        "accent": "#FFB454",
        "accent_alt": "#D4A24C",
        "border": "#33291F",
        "selection": "#4A3A22",
        "cursor_line": "#221C15",
        "gutter_fg": "#5C4A32",
        "gutter_fg_active": "#E8C088",
        "error": "#E0654A",
        "warning": "#FFB454",
        "mode_normal": "#FFB454",
        "mode_insert": "#D4A24C",
        "mode_visual": "#E8956B",
        "mode_command": "#FFB454",
        "mode_replace": "#E0654A",
        "syntax": {
            "keyword": "#FFB454",
            "string": "#D4A24C",
            "comment": "#6B5738",
            "number": "#E8956B",
            "function": "#F0C878",
            "class": "#FFB454",
            "operator": "#E8C088",
            "builtin": "#F0C878",
            "variable": "#E8C088",
            "constant": "#E8956B",
            "tag": "#E0654A",
            "attribute": "#FFB454",
        },
    },
    "Midnight Violet": {
        "description": "Deep violet-black, cool accent colors.",
        "bg": "#181425",
        "bg_alt": "#1E1A2E",
        "bg_elevated": "#252038",
        "fg": "#D8D3E8",
        "fg_muted": "#756F8C",
        "accent": "#C792EA",
        "accent_alt": "#89DDFF",
        "border": "#2E2846",
        "selection": "#3A3159",
        "cursor_line": "#211C33",
        "gutter_fg": "#4A4266",
        "gutter_fg_active": "#C7C2D9",
        "error": "#FF6B81",
        "warning": "#FFCB6B",
        "mode_normal": "#C792EA",
        "mode_insert": "#89DDFF",
        "mode_visual": "#F78FB3",
        "mode_command": "#FFCB6B",
        "mode_replace": "#FF6B81",
        "syntax": {
            "keyword": "#C792EA",
            "string": "#89DDFF",
            "comment": "#5C567A",
            "number": "#F78FB3",
            "function": "#82AAFF",
            "class": "#FFCB6B",
            "operator": "#89DDFF",
            "builtin": "#82AAFF",
            "variable": "#D8D3E8",
            "constant": "#F78FB3",
            "tag": "#FF6B81",
            "attribute": "#C792EA",
        },
    },
}

DEFAULT_THEME = "Obsidian"


def build_qss(theme: dict) -> str:
    """Build the application-chrome stylesheet for a given theme dict."""
    return f"""
* {{
    font-family: "JetBrains Mono", "Cascadia Code", "Consolas", "DejaVu Sans Mono", monospace;
    outline: none;
}}

QMainWindow, QWidget {{
    background-color: {theme['bg']};
    color: {theme['fg']};
}}

/* ---------------- Tab bar ---------------- */
QTabWidget::pane {{
    border: none;
    background-color: {theme['bg']};
}}
QTabBar {{
    background-color: {theme['bg_alt']};
}}
QTabBar::tab {{
    background-color: {theme['bg_alt']};
    color: {theme['fg_muted']};
    padding: 7px 18px;
    border: none;
    border-right: 1px solid {theme['border']};
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {theme['bg']};
    color: {theme['fg']};
    border-top: 2px solid {theme['accent']};
}}
QTabBar::tab:hover:!selected {{
    background-color: {theme['bg_elevated']};
    color: {theme['fg']};
}}
QTabBar::close-button {{
    subcontrol-position: right;
}}

/* ---------------- Status bar ---------------- */
#StatusBar {{
    background-color: {theme['bg_elevated']};
    border-top: 1px solid {theme['border']};
}}
#ModeLabel {{
    font-size: 11px;
    font-weight: 700;
    padding: 2px 12px;
    border-radius: 3px;
    color: {theme['bg']};
}}
#FileLabel {{
    font-size: 11px;
    color: {theme['fg_muted']};
}}
#PosLabel {{
    font-size: 11px;
    color: {theme['fg_muted']};
}}

/* ---------------- Command line ---------------- */
#CommandLine {{
    background-color: {theme['bg_elevated']};
    color: {theme['fg']};
    border: none;
    border-top: 1px solid {theme['border']};
    padding: 4px 10px;
    font-size: 12px;
}}

/* ---------------- Sidebar (file tree) ---------------- */
#Sidebar {{
    background-color: {theme['bg_alt']};
    border-right: 1px solid {theme['border']};
}}
QTreeView {{
    background-color: {theme['bg_alt']};
    color: {theme['fg']};
    border: none;
    font-size: 12px;
}}
QTreeView::item {{
    padding: 3px 2px;
}}
QTreeView::item:hover {{
    background-color: {theme['bg_elevated']};
}}
QTreeView::item:selected {{
    background-color: {theme['selection']};
    color: {theme['fg']};
}}
QHeaderView::section {{
    background-color: {theme['bg_alt']};
    color: {theme['fg_muted']};
    border: none;
    padding: 4px;
    font-size: 10px;
}}

/* ---------------- Theme picker menu ---------------- */
QMenu {{
    background-color: {theme['bg_elevated']};
    border: 1px solid {theme['border']};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 22px;
    color: {theme['fg']};
    font-size: 12px;
}}
QMenu::item:selected {{
    background-color: {theme['selection']};
}}

/* ---------------- Scrollbars ---------------- */
QScrollBar:vertical {{
    background: {theme['bg']};
    width: 12px;
}}
QScrollBar::handle:vertical {{
    background: {theme['border']};
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {theme['fg_muted']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}

QScrollBar:horizontal {{
    background: {theme['bg']};
    height: 12px;
}}
QScrollBar::handle:horizontal {{
    background: {theme['border']};
    border-radius: 3px;
    min-width: 24px;
}}

/* ---------------- Dialogs / misc ---------------- */
QToolTip {{
    background-color: {theme['bg_elevated']};
    color: {theme['fg']};
    border: 1px solid {theme['border']};
    padding: 4px 8px;
}}
"""
