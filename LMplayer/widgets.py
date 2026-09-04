"""
Custom widgets for Nova's minimal Yaru-themed UI.
"""

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QTimer, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath, QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFrame,
    QSizePolicy
)

from theme import PALETTE


def _rounded(pixmap: QPixmap, size: int, radius: int = 8) -> QPixmap:
    """Scale a pixmap to a square and clip it to rounded corners."""
    scaled = pixmap.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    result = QPixmap(size, size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.setClipPath(path)

    x = (scaled.width() - size) // 2
    y = (scaled.height() - size) // 2
    painter.drawPixmap(-x, -y, scaled)
    painter.end()
    return result


class CoverArtLabel(QLabel):
    """Square, rounded-corner album art tile."""

    def __init__(self, size: int = 48, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setStyleSheet(f"border-radius: 8px; background-color: {PALETTE['aubergine_700']};")

    def setPixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            super().setPixmap(_rounded(pixmap, self._size))
        else:
            super().setPixmap(QPixmap())


class TrackRow(QWidget):
    """A single row in the track list: cover thumbnail, title/artist, album, duration."""

    def __init__(self, track, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 12, 4)
        layout.setSpacing(12)

        cover = CoverArtLabel(size=42)
        if track.cover_pixmap:
            cover.setPixmap(track.cover_pixmap)
        else:
            cover.setStyleSheet(
                f"border-radius: 8px; background-color: {PALETTE['aubergine_700']};"
            )
            cover.setText("\u266A")
            cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cover.setStyleSheet(
                f"border-radius: 8px; background-color: {PALETTE['aubergine_700']}; "
                f"color: {PALETTE['text_on_dark']}; font-size: 16px;"
            )
        layout.addWidget(cover)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title_lbl = QLabel(track.title)
        title_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {PALETTE['text_primary']};")
        artist_lbl = QLabel(track.artist)
        artist_lbl.setStyleSheet(f"font-size: 11px; color: {PALETTE['text_secondary']};")
        text_col.addWidget(title_lbl)
        text_col.addWidget(artist_lbl)

        text_wrap = QWidget()
        text_wrap.setLayout(text_col)
        layout.addWidget(text_wrap, 4)

        album_lbl = QLabel(track.album)
        album_lbl.setStyleSheet(f"font-size: 12px; color: {PALETTE['text_secondary']};")
        layout.addWidget(album_lbl, 3)

        m, s = divmod(track.duration_seconds, 60)
        dur_lbl = QLabel(f"{m}:{s:02d}")
        dur_lbl.setStyleSheet(f"font-size: 12px; color: {PALETTE['text_secondary']};")
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(dur_lbl, 1)


class SidebarButton(QPushButton):
    """Navigation button in the dark sidebar, with an active/inactive state."""

    ICONS = {
        "songs": "\u266A",
        "queue": "\u2630",
        "playlists": "\u25A4",
    }

    def __init__(self, text: str, icon_key: str, parent=None):
        icon = self.ICONS.get(icon_key, "")
        super().__init__(f"  {icon}   {text}", parent)
        self.setCheckable(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(38)
        self._active = False
        self._apply_style()

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()

    def _apply_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {PALETTE['orange']};
                    color: white;
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 600;
                    padding-left: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {PALETTE['text_on_dark']};
                    border: none;
                    border-radius: 10px;
                    text-align: left;
                    font-size: 13px;
                    font-weight: 500;
                    padding-left: 6px;
                }}
                QPushButton:hover {{
                    background-color: rgba(233, 84, 32, 0.18);
                }}
            """)


class TransportButton(QPushButton):
    """Play/pause/skip/shuffle/repeat button for the now-playing bar."""

    def __init__(self, symbol: str, tooltip: str = "", primary: bool = False, parent=None):
        super().__init__(symbol, parent)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            self.setObjectName("TransportButtonPrimary")
            self.setFixedSize(44, 44)
        else:
            self.setObjectName("TransportButton")
            self.setFixedSize(38, 38)


class MarqueeLabel(QLabel):
    """A label that behaves normally but elides long text cleanly."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setMaximumWidth(210)

    def setText(self, text: str):
        metrics = self.fontMetrics()
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideRight, 210)
        super().setText(elided)
        self.setToolTip(text)


class PlaylistCard(QFrame):
    """A clickable card representing a playlist, with cover collage + name."""

    clicked_play = pyqtSignal()

    def __init__(self, name: str, track_count: int, cover: QPixmap, parent=None):
        super().__init__(parent)
        self.setObjectName("PlaylistCard")
        self.setFixedSize(170, 210)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        cover_lbl = QLabel()
        cover_lbl.setFixedSize(146, 146)
        if cover and not cover.isNull():
            cover_lbl.setPixmap(_rounded(cover, 146, radius=10))
        layout.addWidget(cover_lbl)

        title_lbl = QLabel(name)
        title_lbl.setObjectName("PlaylistCardTitle")
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel(f"{track_count} track{'s' if track_count != 1 else ''}")
        sub_lbl.setObjectName("PlaylistCardSubtitle")
        layout.addWidget(sub_lbl)

    def mouseReleaseEvent(self, event):
        self.clicked_play.emit()
        super().mouseReleaseEvent(event)
