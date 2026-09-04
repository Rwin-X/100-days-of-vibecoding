"""
Library scanning and metadata extraction for Nova.

Uses mutagen to read ID3 / FLAC / MP4 tags, including embedded cover art,
without any network access — everything is local.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtGui import QPixmap
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".oga", ".opus"}


@dataclass
class Track:
    filepath: str
    title: str = "Unknown Title"
    artist: str = "Unknown Artist"
    album: str = "Unknown Album"
    duration_seconds: int = 0
    cover_bytes: bytes | None = field(default=None, repr=False)
    _cover_pixmap_cache: QPixmap | None = field(default=None, repr=False, compare=False)

    @property
    def cover_pixmap(self) -> QPixmap | None:
        if self._cover_pixmap_cache is not None:
            return self._cover_pixmap_cache
        if self.cover_bytes:
            pix = QPixmap()
            if pix.loadFromData(self.cover_bytes):
                self._cover_pixmap_cache = pix
                return pix
        return None

    def __eq__(self, other):
        return isinstance(other, Track) and self.filepath == other.filepath

    def __hash__(self):
        return hash(self.filepath)


def extract_cover_art(filepath: str) -> bytes | None:
    """Pull embedded album art bytes from common tag formats."""
    ext = Path(filepath).suffix.lower()
    try:
        if ext == ".mp3":
            audio = ID3(filepath)
            for tag in audio.values():
                if isinstance(tag, APIC):
                    return tag.data
        elif ext == ".flac":
            audio = FLAC(filepath)
            if audio.pictures:
                return audio.pictures[0].data
        elif ext == ".m4a":
            audio = MP4(filepath)
            covers = audio.tags.get("covr") if audio.tags else None
            if covers:
                return bytes(covers[0])
        else:
            # generic fallback via mutagen's File()
            audio = MutagenFile(filepath)
            if audio is not None and audio.tags:
                for key in audio.tags.keys():
                    if "APIC" in key or "covr" in key.lower():
                        val = audio.tags[key]
                        if isinstance(val, list):
                            val = val[0]
                        data = getattr(val, "data", None)
                        if data:
                            return data
    except Exception:
        return None
    return None


def _read_tags(filepath: str) -> Track:
    filename_stem = Path(filepath).stem
    title, artist, album, duration = filename_stem, "Unknown Artist", "Unknown Album", 0

    try:
        audio = MutagenFile(filepath, easy=True)
        if audio is not None:
            title = (audio.get("title") or [filename_stem])[0]
            artist = (audio.get("artist") or ["Unknown Artist"])[0]
            album = (audio.get("album") or ["Unknown Album"])[0]
            if audio.info is not None and hasattr(audio.info, "length"):
                duration = int(audio.info.length)
    except Exception:
        pass

    cover = extract_cover_art(filepath)

    return Track(
        filepath=filepath,
        title=title,
        artist=artist,
        album=album,
        duration_seconds=duration,
        cover_bytes=cover,
    )


class LibraryScanner:
    """Recursively scans a directory for supported audio files."""

    def scan(self, root_folder: str) -> list[Track]:
        tracks: list[Track] = []
        for dirpath, _dirnames, filenames in os.walk(root_folder):
            for name in filenames:
                ext = Path(name).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_path = os.path.join(dirpath, name)
                    try:
                        tracks.append(_read_tags(full_path))
                    except Exception:
                        continue
        tracks.sort(key=lambda t: (t.artist.lower(), t.album.lower(), t.title.lower()))
        return tracks
