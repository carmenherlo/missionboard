from __future__ import annotations

import secrets
from dataclasses import replace
from types import SimpleNamespace

from app.errors import InvalidError, NotFoundError, TooLargeError, UnsupportedTypeError
from app.events.service import EventLog
from app.routines.repository import RoutinesRepository
from app.songs.repository import Song, SongsRepository, SoundFiles

MAX_SONG_BYTES = 15 * 1024 * 1024
MAX_SONG_SECONDS = 60 * 60


def sniff_song(data: bytes) -> str | None:
    """The file extension for a song, by its content (what its type says is not trusted)."""
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return ".mp3"
    if data[4:8] == b"ftyp":
        return ".m4a"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    return None


class SongsService:
    """The songs the routines can play: uploaded once, used in any routine."""

    def __init__(self, songs: SongsRepository, files: SoundFiles, routines: RoutinesRepository, events: EventLog):
        self._songs = songs
        self._files = files
        self._routines = routines
        self._events = events

    def list(self) -> list[Song]:
        return self._songs.list()

    def get(self, song_id: str) -> Song:
        song = self._songs.get(song_id)
        if song is None:
            raise NotFoundError("Song not found")
        return song

    def used_in(self, song_id: str) -> list[str]:
        """The routines that play it (their names)."""
        return [r.name for r in self._routines.list() if any(m.song == song_id for m in r.music)]

    def upload(self, data: bytes, name: str, seconds: float) -> Song:
        if len(data) > MAX_SONG_BYTES:
            raise TooLargeError("Song is too large (max 15 MB)")
        extension = sniff_song(data)
        if extension is None:
            raise UnsupportedTypeError("A song must be MP3, M4A, OGG or WAV")
        if not 0 < seconds <= MAX_SONG_SECONDS:
            raise InvalidError("How long it lasts is missing")
        song = Song(id=secrets.token_hex(4), name=name, file=self._files.save(data, extension), seconds=round(seconds, 1))
        self._songs.add(song)
        self._log("created", song)
        return song

    def rename(self, song_id: str, name: str) -> Song:
        with self._songs.atomic():
            song = replace(self.get(song_id), name=name)
            self._songs.update(song)
        self._log("changed", song, {"name": name})
        return song

    def delete(self, song_id: str) -> None:
        """Out of the library, and out of every routine that played it."""
        with self._songs.atomic():
            song = self.get(song_id)
            for routine in self._routines.list():
                if any(m.song == song_id for m in routine.music):
                    doc = routine.to_doc()
                    doc["music"] = [m for m in doc["music"] if m["song"] != song_id]
                    self._routines.update(type(routine).model_validate(doc))
            self._songs.remove(song_id)
        self._files.delete(song.file)
        self._log("deleted", song)

    def file(self, song_id: str):
        path = self._files.path(self.get(song_id).file)
        if path is None:
            raise NotFoundError("Song file not found")
        return path

    def _log(self, action: str, song: Song, changes: dict | None = None) -> None:
        self._events.config_changed("song", action, mission=SimpleNamespace(id=song.id, name=song.name), changes=changes)
