#!/usr/bin/env python3
"""
Nova — a minimal, Ubuntu-themed desktop music player.

Design goals:
  - Visually minimal, generous whitespace, no clutter
  - Feature set inspired by Spotify: library, playlists, queue, search,
    now-playing bar with seek/volume, shuffle/repeat
  - Ubuntu / Yaru visual language: Ubuntu Orange (#E95420) + Aubergine
    (#2C001E / #77216F), rounded corners, Ubuntu font stack
  - Shows embedded album art (falls back to a generated placeholder)

Author: black8arch / devforge
"""

import sys
import os
import random
from pathlib import Path

from PyQt6.QtCore import (
    Qt, QUrl, QTimer, QSize, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QByteArray, QRectF
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QColor, QFont, QFontDatabase,
    QLinearGradient, QPainterPath, QAction, QPen
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QSlider,
    QFileDialog, QLineEdit, QStackedWidget, QScrollArea, QFrame,
    QSizePolicy, QMenu, QToolButton, QSplitter, QGraphicsDropShadowEffect
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from mutagen import File as MutagenFile

from theme import YARU_QSS, PALETTE
from library import Track, LibraryScanner, extract_cover_art
from widgets import (
    CoverArtLabel, TrackRow, SidebarButton, TransportButton,
    MarqueeLabel, PlaylistCard
)


APP_NAME = "Nova"
ORG_NAME = "devforge"


# --------------------------------------------------------------------------
# Generated fallback cover art (drawn, not fetched) — a soft Yaru-style
# gradient tile with a musical-note glyph, so every track looks intentional
# even without embedded artwork.
# --------------------------------------------------------------------------
def generate_placeholder_cover(seed_text: str, size: int = 300) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)

    random.seed(hash(seed_text) & 0xFFFFFFFF)
    palettes = [
        ("#E95420", "#772953"),
        ("#77216F", "#2C001E"),
        ("#5E2750", "#E95420"),
        ("#333333", "#77216F"),
        ("#C7162B", "#2C001E"),
    ]
    c1, c2 = random.choice(palettes)

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size, size), 18, 18)
    painter.setClipPath(path)

    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0, QColor(c1))
    grad.setColorAt(1, QColor(c2))
    painter.fillRect(0, 0, size, size, grad)

    # subtle diagonal texture
    painter.setPen(QPen(QColor(255, 255, 255, 18), 2))
    for i in range(-size, size, 14):
        painter.drawLine(i, 0, i + size, size)

    # musical note glyph, centered
    painter.setPen(QPen(QColor(255, 255, 255, 235)))
    font = QFont("Ubuntu", int(size * 0.34))
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, "\u266A")

    painter.end()
    return pix


# --------------------------------------------------------------------------
# Main Window
# --------------------------------------------------------------------------
class NovaPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1180, 760)
        self.setMinimumSize(920, 600)

        # --- playback engine ---
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.8)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        # --- library state ---
        self.library: list[Track] = []
        self.queue: list[Track] = []
        self.current_index: int = -1
        self.shuffle_on = False
        self.repeat_mode = 0  # 0=off, 1=repeat-all, 2=repeat-one
        self.playlists: dict[str, list[Track]] = {}
        self._seeking = False

        self._build_ui()
        self._apply_theme()

    # ---------------------------------------------------------------- UI --
    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top titlebar-ish strip (search + window actions area)
        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # Body: sidebar | main content
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        body_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.home_page = self._build_library_page()
        self.queue_page = self._build_queue_page()
        self.playlists_page = self._build_playlists_page()
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.queue_page)
        self.stack.addWidget(self.playlists_page)
        body_layout.addWidget(self.stack, 1)

        root_layout.addWidget(body, 1)

        # Now-playing bar (bottom, Spotify-style)
        self.now_playing_bar = self._build_now_playing_bar()
        root_layout.addWidget(self.now_playing_bar)

        self.setCentralWidget(root)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(64)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(14)

        logo = QLabel("Nova")
        logo.setObjectName("Logo")
        layout.addWidget(logo)

        layout.addSpacing(12)

        self.search_box = QLineEdit()
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Search your library…")
        self.search_box.setFixedWidth(360)
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        layout.addStretch(1)

        add_folder_btn = QPushButton("  Add Music Folder")
        add_folder_btn.setObjectName("AccentButton")
        add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_folder_btn.clicked.connect(self._add_folder)
        layout.addWidget(add_folder_btn)

        return bar

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Sidebar")
        panel.setFixedWidth(230)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 18, 14, 18)
        layout.setSpacing(4)

        section_label = QLabel("LIBRARY")
        section_label.setObjectName("SectionLabel")
        layout.addWidget(section_label)

        self.btn_home = SidebarButton("Songs", "songs")
        self.btn_queue = SidebarButton("Queue", "queue")
        self.btn_playlists = SidebarButton("Playlists", "playlists")

        self.btn_home.clicked.connect(lambda: self._switch_page(0, self.btn_home))
        self.btn_queue.clicked.connect(lambda: self._switch_page(1, self.btn_queue))
        self.btn_playlists.clicked.connect(lambda: self._switch_page(2, self.btn_playlists))

        for b in (self.btn_home, self.btn_queue, self.btn_playlists):
            layout.addWidget(b)

        self.btn_home.set_active(True)

        layout.addSpacing(22)
        pl_label = QLabel("PLAYLISTS")
        pl_label.setObjectName("SectionLabel")
        layout.addWidget(pl_label)

        new_pl_btn = QPushButton("+  New Playlist")
        new_pl_btn.setObjectName("GhostButton")
        new_pl_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_pl_btn.setFixedHeight(34)
        new_pl_btn.clicked.connect(self._create_playlist)
        layout.addWidget(new_pl_btn)
        layout.addSpacing(6)

        self.playlist_list = QListWidget()
        self.playlist_list.setObjectName("PlaylistNavList")
        self.playlist_list.itemClicked.connect(self._open_playlist_from_sidebar)
        layout.addWidget(self.playlist_list, 1)

        # Ubuntu-flavored footer badge
        footer = QLabel("Ubuntu-themed  ·  Nova")
        footer.setObjectName("SidebarFooter")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

        return panel

    def _build_library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 10)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Your Songs")
        title.setObjectName("PageTitle")
        header.addWidget(title)
        header.addStretch(1)

        self.track_count_label = QLabel("0 tracks")
        self.track_count_label.setObjectName("MutedLabel")
        header.addWidget(self.track_count_label)

        shuffle_all_btn = QPushButton("Shuffle Play")
        shuffle_all_btn.setObjectName("AccentButtonSmall")
        shuffle_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        shuffle_all_btn.clicked.connect(self._shuffle_play_all)
        header.addWidget(shuffle_all_btn)

        layout.addLayout(header)

        # column headers
        col_header = QHBoxLayout()
        col_header.setContentsMargins(58, 0, 16, 0)
        for text, stretch in (("TITLE", 4), ("ALBUM", 3), ("DURATION", 1)):
            lbl = QLabel(text)
            lbl.setObjectName("ColumnHeader")
            col_header.addWidget(lbl, stretch)
        layout.addLayout(col_header)

        sep = QFrame()
        sep.setObjectName("HeaderSeparator")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        self.track_list = QListWidget()
        self.track_list.setObjectName("TrackList")
        self.track_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.track_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.track_list.itemDoubleClicked.connect(self._on_track_double_clicked)
        self.track_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.track_list.customContextMenuRequested.connect(self._track_context_menu)
        layout.addWidget(self.track_list, 1)

        self.empty_state = self._build_empty_state()
        layout.addWidget(self.empty_state)
        self.empty_state.setVisible(True)
        self.track_list.setVisible(False)

        return page

    def _build_empty_state(self) -> QWidget:
        box = QFrame()
        box.setObjectName("EmptyState")
        layout = QVBoxLayout(box)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icon = QLabel("\u266B")
        icon.setObjectName("EmptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        msg = QLabel("No music yet")
        msg.setObjectName("EmptyTitle")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        sub = QLabel("Add a folder to build your library.\nMP3, FLAC, WAV, OGG, and M4A are supported.")
        sub.setObjectName("EmptySubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        btn = QPushButton("Add Music Folder")
        btn.setObjectName("AccentButton")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._add_folder)
        btn.setFixedWidth(200)
        layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)

        return box

    def _build_queue_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 10)
        layout.setSpacing(14)

        title = QLabel("Play Queue")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.queue_list = QListWidget()
        self.queue_list.setObjectName("TrackList")
        self.queue_list.itemDoubleClicked.connect(self._on_queue_item_double_clicked)
        layout.addWidget(self.queue_list, 1)

        return page

    def _build_playlists_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 22, 28, 10)
        layout.setSpacing(14)

        title = QLabel("Playlists")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("PlaylistScroll")
        inner = QWidget()
        self.playlists_grid = QHBoxLayout(inner)
        self.playlists_grid.setSpacing(16)
        self.playlists_grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.playlists_grid.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        return page

    def _build_now_playing_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("NowPlayingBar")
        bar.setFixedHeight(96)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 20, 10)
        layout.setSpacing(16)

        # left: cover + track info
        left = QHBoxLayout()
        left.setSpacing(12)
        self.now_cover = CoverArtLabel(size=72)
        left.addWidget(self.now_cover)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        self.now_title = MarqueeLabel("Nothing playing")
        self.now_title.setObjectName("NowTitle")
        self.now_artist = QLabel("Add music to get started")
        self.now_artist.setObjectName("NowArtist")
        info_col.addWidget(self.now_title)
        info_col.addWidget(self.now_artist)
        left.addLayout(info_col)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(320)
        layout.addWidget(left_widget)

        # center: transport controls + seek bar
        center = QVBoxLayout()
        center.setSpacing(4)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(14)
        controls_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.shuffle_btn = TransportButton("\u21c4", tooltip="Shuffle")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)

        self.prev_btn = TransportButton("\u23ee", tooltip="Previous")
        self.prev_btn.clicked.connect(self._play_previous)

        self.play_btn = TransportButton("\u25b6", tooltip="Play", primary=True)
        self.play_btn.clicked.connect(self._toggle_play)

        self.next_btn = TransportButton("\u23ed", tooltip="Next")
        self.next_btn.clicked.connect(self._play_next)

        self.repeat_btn = TransportButton("\u21bb", tooltip="Repeat")
        self.repeat_btn.setCheckable(True)
        self.repeat_btn.clicked.connect(self._toggle_repeat)

        for b in (self.shuffle_btn, self.prev_btn, self.play_btn, self.next_btn, self.repeat_btn):
            controls_row.addWidget(b)

        center.addLayout(controls_row)

        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)
        self.time_current = QLabel("0:00")
        self.time_current.setObjectName("TimeLabel")
        self.time_current.setFixedWidth(40)
        self.time_current.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setObjectName("SeekSlider")
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_start)
        self.seek_slider.sliderReleased.connect(self._on_seek_end)

        self.time_total = QLabel("0:00")
        self.time_total.setObjectName("TimeLabel")
        self.time_total.setFixedWidth(40)

        seek_row.addWidget(self.time_current)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.time_total)
        center.addLayout(seek_row)

        layout.addLayout(center, 1)

        # right: volume
        right = QHBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignmentFlag.AlignRight)

        vol_icon = QLabel("\U0001F50A")
        vol_icon.setObjectName("VolIcon")
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("VolumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(110)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

        right.addWidget(vol_icon)
        right.addWidget(self.volume_slider)

        right_widget = QWidget()
        right_widget.setLayout(right)
        right_widget.setFixedWidth(220)
        layout.addWidget(right_widget)

        return bar

    # ------------------------------------------------------------ theme --
    def _apply_theme(self):
        self.setStyleSheet(YARU_QSS)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, -3)
        self.now_playing_bar.setGraphicsEffect(shadow)

    # ------------------------------------------------------------- nav ---
    def _switch_page(self, index: int, active_btn: SidebarButton):
        self.stack.setCurrentIndex(index)
        for b in (self.btn_home, self.btn_queue, self.btn_playlists):
            b.set_active(b is active_btn)

    # --------------------------------------------------------- library ---
    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Music Folder")
        if not folder:
            return
        scanner = LibraryScanner()
        new_tracks = scanner.scan(folder)
        if not new_tracks:
            return
        self.library.extend(new_tracks)
        self._refresh_track_list()

    def _refresh_track_list(self):
        self.track_list.clear()
        for track in self.library:
            self._add_track_row(track)

        has_tracks = len(self.library) > 0
        self.track_list.setVisible(has_tracks)
        self.empty_state.setVisible(not has_tracks)
        self.track_count_label.setText(f"{len(self.library)} track{'s' if len(self.library) != 1 else ''}")

    def _add_track_row(self, track: Track):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, track)
        item.setSizeHint(QSize(0, 60))
        row = TrackRow(track)
        self.track_list.addItem(item)
        self.track_list.setItemWidget(item, row)

    def _on_search(self, text: str):
        text = text.strip().lower()
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            track: Track = item.data(Qt.ItemDataRole.UserRole)
            match = (
                not text
                or text in track.title.lower()
                or text in track.artist.lower()
                or text in track.album.lower()
            )
            item.setHidden(not match)

    def _track_context_menu(self, pos):
        item = self.track_list.itemAt(pos)
        if item is None:
            return
        track: Track = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        play_action = QAction("Play", self)
        play_action.triggered.connect(lambda: self._play_track(track, self.library))
        menu.addAction(play_action)

        queue_action = QAction("Add to Queue", self)
        queue_action.triggered.connect(lambda: self._add_to_queue(track))
        menu.addAction(queue_action)

        if self.playlists:
            submenu = menu.addMenu("Add to Playlist")
            for name in self.playlists:
                act = QAction(name, self)
                act.triggered.connect(lambda checked, n=name, t=track: self._add_to_playlist(n, t))
                submenu.addAction(act)

        menu.exec(self.track_list.mapToGlobal(pos))

    # ---------------------------------------------------------- queue ---
    def _add_to_queue(self, track: Track):
        self.queue.append(track)
        self._refresh_queue_list()

    def _refresh_queue_list(self):
        self.queue_list.clear()
        for track in self.queue:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, track)
            item.setSizeHint(QSize(0, 60))
            row = TrackRow(track)
            self.queue_list.addItem(item)
            self.queue_list.setItemWidget(item, row)

    def _on_queue_item_double_clicked(self, item: QListWidgetItem):
        track: Track = item.data(Qt.ItemDataRole.UserRole)
        self._play_track(track, self.queue)

    # ------------------------------------------------------- playlists --
    def _create_playlist(self):
        base_name = "New Playlist"
        name = base_name
        n = 1
        while name in self.playlists:
            n += 1
            name = f"{base_name} {n}"
        self.playlists[name] = []
        self._refresh_playlist_nav()
        self._refresh_playlist_grid()

    def _add_to_playlist(self, name: str, track: Track):
        if name in self.playlists and track not in self.playlists[name]:
            self.playlists[name].append(track)
            self._refresh_playlist_grid()

    def _refresh_playlist_nav(self):
        self.playlist_list.clear()
        for name in self.playlists:
            self.playlist_list.addItem(name)

    def _refresh_playlist_grid(self):
        while self.playlists_grid.count() > 1:
            item = self.playlists_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        for name, tracks in self.playlists.items():
            cover = tracks[0].cover_pixmap if tracks else generate_placeholder_cover(name, 160)
            card = PlaylistCard(name, len(tracks), cover)
            card.clicked_play.connect(lambda n=name: self._play_playlist(n))
            self.playlists_grid.insertWidget(self.playlists_grid.count() - 1, card)

    def _open_playlist_from_sidebar(self, item):
        name = item.text()
        self._switch_page(2, self.btn_playlists)

    def _play_playlist(self, name: str):
        tracks = self.playlists.get(name, [])
        if tracks:
            self._play_track(tracks[0], tracks)

    # -------------------------------------------------------- playback --
    def _on_track_double_clicked(self, item: QListWidgetItem):
        track: Track = item.data(Qt.ItemDataRole.UserRole)
        self._play_track(track, self.library)

    def _shuffle_play_all(self):
        if not self.library:
            return
        self.shuffle_on = True
        self.shuffle_btn.setChecked(True)
        shuffled = self.library[:]
        random.shuffle(shuffled)
        self._play_track(shuffled[0], shuffled)

    def _play_track(self, track: Track, context: list[Track]):
        self.current_context = context
        self.current_index = context.index(track) if track in context else 0
        self._load_and_play(track)

    def _load_and_play(self, track: Track):
        self.player.setSource(QUrl.fromLocalFile(track.filepath))
        self.player.play()

        self.now_title.setText(track.title)
        self.now_artist.setText(f"{track.artist} — {track.album}")

        pix = track.cover_pixmap
        if pix is None or pix.isNull():
            pix = generate_placeholder_cover(track.title)
        self.now_cover.setPixmap(pix)

    def _toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.player.source().isEmpty() and self.library:
                self._play_track(self.library[0], self.library)
            else:
                self.player.play()

    def _play_next(self):
        ctx = getattr(self, "current_context", None) or self.library
        if not ctx:
            return
        if self.shuffle_on:
            next_idx = random.randrange(len(ctx))
        else:
            next_idx = (self.current_index + 1) % len(ctx)
            if next_idx == 0 and self.repeat_mode == 0:
                self.player.stop()
                return
        self.current_index = next_idx
        self._load_and_play(ctx[next_idx])

    def _play_previous(self):
        ctx = getattr(self, "current_context", None) or self.library
        if not ctx:
            return
        if self.player.position() > 3000:
            self.player.setPosition(0)
            return
        prev_idx = (self.current_index - 1) % len(ctx)
        self.current_index = prev_idx
        self._load_and_play(ctx[prev_idx])

    def _toggle_shuffle(self):
        self.shuffle_on = self.shuffle_btn.isChecked()

    def _toggle_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        self.repeat_btn.setChecked(self.repeat_mode != 0)
        labels = {0: "\u21bb", 1: "\u21bb", 2: "1"}
        self.repeat_btn.setText(labels[self.repeat_mode])

    def _on_volume_changed(self, value: int):
        self.audio_output.setVolume(value / 100)

    # -------------------------------------------------------- player Qt --
    def _on_state_changed(self, state):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText("\u23f8" if is_playing else "\u25b6")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self.repeat_mode == 2:
                self.player.setPosition(0)
                self.player.play()
            else:
                self._play_next()

    def _on_position_changed(self, position_ms: int):
        if not self._seeking:
            self.seek_slider.setValue(position_ms)
        self.time_current.setText(self._fmt_time(position_ms))

    def _on_duration_changed(self, duration_ms: int):
        self.seek_slider.setRange(0, duration_ms)
        self.time_total.setText(self._fmt_time(duration_ms))

    def _on_seek_start(self):
        self._seeking = True

    def _on_seek_end(self):
        self.player.setPosition(self.seek_slider.value())
        self._seeking = False

    @staticmethod
    def _fmt_time(ms: int) -> str:
        seconds = max(0, ms // 1000)
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)

    window = NovaPlayer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
