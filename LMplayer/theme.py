"""
Yaru-inspired theme for Nova.

Colors are pulled from Ubuntu's actual Yaru design language:
  - Ubuntu Orange   #E95420  (primary accent, buttons, active states)
  - Aubergine dark  #2C001E  (deepest background / sidebar)
  - Aubergine mid   #5E2750  (secondary surface)
  - Warm grey       #333333  (text on light, dark surfaces)
  - Cool white      #F7F7F7  (light surface / main content backdrop)
  - Ubuntu terminal purple #77216F (hover accents)
"""

PALETTE = {
    "orange": "#E95420",
    "orange_hover": "#F2652B",
    "orange_dark": "#C34113",
    "aubergine_950": "#1E0A17",
    "aubergine_900": "#2C001E",
    "aubergine_800": "#3B0A2A",
    "aubergine_700": "#5E2750",
    "aubergine_600": "#77216F",
    "surface": "#FBF8F7",
    "surface_alt": "#F2EEEC",
    "border": "#E4DEDB",
    "text_primary": "#2C001E",
    "text_secondary": "#6E6259",
    "text_on_dark": "#F7F4F2",
    "text_on_dark_muted": "#C9B8C4",
    "warning": "#C7162B",
    "success": "#0E8420",
}

YARU_QSS = f"""
* {{
    font-family: "Ubuntu", "Noto Sans", "Cantarell", "Segoe UI", sans-serif;
    outline: none;
}}

QMainWindow, QWidget {{
    background-color: {PALETTE['surface']};
    color: {PALETTE['text_primary']};
}}

/* ---------------- Top bar ---------------- */
#TopBar {{
    background-color: {PALETTE['surface']};
    border-bottom: 1px solid {PALETTE['border']};
}}

#Logo {{
    font-size: 20px;
    font-weight: 700;
    color: {PALETTE['orange']};
    letter-spacing: 0.5px;
}}

#SearchBox {{
    background-color: {PALETTE['surface_alt']};
    border: 1px solid {PALETTE['border']};
    border-radius: 16px;
    padding: 7px 16px;
    font-size: 13px;
    color: {PALETTE['text_primary']};
}}
#SearchBox:focus {{
    border: 1px solid {PALETTE['orange']};
    background-color: #FFFFFF;
}}

/* ---------------- Buttons ---------------- */
#AccentButton {{
    background-color: {PALETTE['orange']};
    color: white;
    border: none;
    border-radius: 18px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}}
#AccentButton:hover {{ background-color: {PALETTE['orange_hover']}; }}
#AccentButton:pressed {{ background-color: {PALETTE['orange_dark']}; }}

#AccentButtonSmall {{
    background-color: {PALETTE['orange']};
    color: white;
    border: none;
    border-radius: 14px;
    padding: 6px 16px;
    font-size: 12px;
    font-weight: 600;
}}
#AccentButtonSmall:hover {{ background-color: {PALETTE['orange_hover']}; }}

#GhostButton {{
    background-color: transparent;
    color: {PALETTE['aubergine_600']};
    border: 1px dashed {PALETTE['aubergine_600']};
    border-radius: 12px;
    padding: 7px 10px;
    font-size: 12px;
    font-weight: 600;
    text-align: left;
}}
#GhostButton:hover {{
    background-color: rgba(119, 33, 111, 0.08);
}}

/* ---------------- Sidebar ---------------- */
#Sidebar {{
    background-color: {PALETTE['aubergine_900']};
    border-right: none;
}}

#SectionLabel {{
    color: {PALETTE['text_on_dark_muted']};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 8px 8px 4px 8px;
}}

#SidebarFooter {{
    color: {PALETTE['text_on_dark_muted']};
    font-size: 10px;
    padding-top: 10px;
}}

#PlaylistNavList {{
    background: transparent;
    border: none;
    color: {PALETTE['text_on_dark']};
    font-size: 13px;
}}
#PlaylistNavList::item {{
    padding: 7px 10px;
    border-radius: 8px;
}}
#PlaylistNavList::item:hover {{
    background-color: rgba(233, 84, 32, 0.18);
}}
#PlaylistNavList::item:selected {{
    background-color: {PALETTE['orange']};
    color: white;
}}

/* ---------------- Page content ---------------- */
#PageTitle {{
    font-size: 24px;
    font-weight: 700;
    color: {PALETTE['text_primary']};
}}

#MutedLabel {{
    color: {PALETTE['text_secondary']};
    font-size: 12px;
}}

#ColumnHeader {{
    color: {PALETTE['text_secondary']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}}

#HeaderSeparator {{
    background-color: {PALETTE['border']};
}}

#TrackList {{
    background: transparent;
    border: none;
}}
#TrackList::item {{
    border-radius: 10px;
    margin: 1px 0px;
}}
#TrackList::item:hover {{
    background-color: {PALETTE['surface_alt']};
}}
#TrackList::item:selected {{
    background-color: rgba(233, 84, 32, 0.12);
}}

/* ---------------- Empty state ---------------- */
#EmptyState {{
    background: transparent;
}}
#EmptyIcon {{
    font-size: 48px;
    color: {PALETTE['aubergine_600']};
}}
#EmptyTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {PALETTE['text_primary']};
}}
#EmptySubtitle {{
    font-size: 12px;
    color: {PALETTE['text_secondary']};
}}

/* ---------------- Playlist cards ---------------- */
#PlaylistScroll {{
    border: none;
    background: transparent;
}}
#PlaylistCard {{
    background-color: {PALETTE['surface_alt']};
    border-radius: 14px;
}}
#PlaylistCard:hover {{
    background-color: {PALETTE['border']};
}}
#PlaylistCardTitle {{
    font-size: 13px;
    font-weight: 700;
    color: {PALETTE['text_primary']};
}}
#PlaylistCardSubtitle {{
    font-size: 11px;
    color: {PALETTE['text_secondary']};
}}

/* ---------------- Now playing bar ---------------- */
#NowPlayingBar {{
    background-color: {PALETTE['aubergine_950']};
    border-top: 1px solid {PALETTE['aubergine_800']};
}}

#NowTitle {{
    color: {PALETTE['text_on_dark']};
    font-size: 13px;
    font-weight: 700;
}}
#NowArtist {{
    color: {PALETTE['text_on_dark_muted']};
    font-size: 11px;
}}

#TimeLabel {{
    color: {PALETTE['text_on_dark_muted']};
    font-size: 10px;
}}

#VolIcon {{
    font-size: 12px;
}}

/* ---------------- Transport buttons ---------------- */
QPushButton#TransportButton {{
    background-color: transparent;
    color: {PALETTE['text_on_dark']};
    border: none;
    border-radius: 20px;
    font-size: 15px;
}}
QPushButton#TransportButton:hover {{
    background-color: rgba(255, 255, 255, 0.08);
}}
QPushButton#TransportButton:checked {{
    color: {PALETTE['orange']};
}}

QPushButton#TransportButtonPrimary {{
    background-color: {PALETTE['orange']};
    color: white;
    border: none;
    border-radius: 22px;
    font-size: 16px;
}}
QPushButton#TransportButtonPrimary:hover {{
    background-color: {PALETTE['orange_hover']};
}}

/* ---------------- Sliders ---------------- */
QSlider#SeekSlider::groove:horizontal {{
    height: 4px;
    background: {PALETTE['aubergine_700']};
    border-radius: 2px;
}}
QSlider#SeekSlider::sub-page:horizontal {{
    height: 4px;
    background: {PALETTE['orange']};
    border-radius: 2px;
}}
QSlider#SeekSlider::handle:horizontal {{
    background: {PALETTE['orange']};
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider#SeekSlider::handle:horizontal:hover {{
    background: {PALETTE['orange_hover']};
}}

QSlider#VolumeSlider::groove:horizontal {{
    height: 4px;
    background: {PALETTE['aubergine_700']};
    border-radius: 2px;
}}
QSlider#VolumeSlider::sub-page:horizontal {{
    height: 4px;
    background: {PALETTE['text_on_dark_muted']};
    border-radius: 2px;
}}
QSlider#VolumeSlider::handle:horizontal {{
    background: {PALETTE['text_on_dark']};
    width: 10px;
    height: 10px;
    margin: -3px 0;
    border-radius: 5px;
}}

/* ---------------- Scrollbars (Yaru style: thin, overlay-ish) --------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {PALETTE['orange']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {PALETTE['border']};
    border-radius: 4px;
    min-width: 30px;
}}

/* ---------------- Menus ---------------- */
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 20px;
    border-radius: 6px;
    color: {PALETTE['text_primary']};
    font-size: 13px;
}}
QMenu::item:selected {{
    background-color: {PALETTE['orange']};
    color: white;
}}
"""
