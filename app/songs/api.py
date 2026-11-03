from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.deps import get_config_store, get_event_log, get_sound_files, require_parent
from app.errors import InvalidError
from app.events.service import EventLog
from app.routines.repository import RoutinesRepository
from app.songs.repository import Song, SongsRepository, SoundFiles
from app.songs.service import SongsService
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/songs", tags=["songs"])
parent_only = [Depends(require_parent)]

SONG_NAME_MAX = 40


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class SongPatch(BaseModel):
    name: str = Field(max_length=SONG_NAME_MAX)

    _name = field_validator("name")(_not_blank)


def get_songs_service(
    store: ConfigStore = Depends(get_config_store),
    files: SoundFiles = Depends(get_sound_files),
    events: EventLog = Depends(get_event_log),
) -> SongsService:
    return SongsService(SongsRepository(store), files, RoutinesRepository(store), events)


def present(song: Song, songs: SongsService) -> dict:
    return {**asdict(song), "url": f"/api/songs/{song.id}/file", "used_in": songs.used_in(song.id)}


@router.get("")
def list_songs(songs: SongsService = Depends(get_songs_service)):
    return [present(s, songs) for s in songs.list()]


@router.post("", status_code=201, dependencies=parent_only)
async def upload_song(
    request: Request,
    name: str = Query(max_length=SONG_NAME_MAX),
    seconds: float = Query(),
    songs: SongsService = Depends(get_songs_service),
):
    """The file as the body (like the photos: no form), its name and how long it lasts."""
    if not name.strip():
        raise InvalidError("Must not be empty")
    return present(songs.upload(await request.body(), name.strip(), seconds), songs)


@router.patch("/{song_id}", dependencies=parent_only)
def rename_song(song_id: str, body: SongPatch, songs: SongsService = Depends(get_songs_service)):
    return present(songs.rename(song_id, body.name), songs)


@router.delete("/{song_id}", status_code=204, dependencies=parent_only)
def delete_song(song_id: str, songs: SongsService = Depends(get_songs_service)) -> None:
    songs.delete(song_id)


@router.get("/{song_id}/file")
def song_file(song_id: str, songs: SongsService = Depends(get_songs_service)):
    return FileResponse(songs.file(song_id))
