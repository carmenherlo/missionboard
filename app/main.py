import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import errors
from app.children import api as children_api
from app.clock import Clock, SystemClock
from app.events import api as events_api
from app.events.repository import EventsRepository
from app.images import api as images_api
from app.images.libraries import LIBRARIES, ImageLibraries, Library
from app.missions import api as missions_api
from app.parents import api as parents_api
from app.prizes import api as prizes_api
from app.routines import api as routines_api
from app.shop import api as shop_api
from app.songs import api as songs_api
from app.songs.repository import SoundFiles
from app.shop.repository import PurchasesRepository
from app.routines.repository import RoutinesRepository, RunsRepository
from app.settings import SettingsRepository
from app.storage import db
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore
from app.templates import api as templates_api
from app.voice import api as voice_api
from app.voice.service import MODEL_NAME, Voice
from app.today import api as today_api
from app.today.repository import BackgroundStore, DayRepository

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

# The app's own code must never be stale after an update: the browser asks
# the server every time (a quick "not modified" when nothing changed).
NO_CACHE = {"Cache-Control": "no-cache"}


class AppStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith((".js", ".css")):
            response.headers.update(NO_CACHE)
        return response


ERROR_STATUS = {
    errors.NotFoundError: 404,
    errors.ConflictError: 409,
    errors.InvalidError: 422,
    errors.PermissionDeniedError: 403,
    errors.TooLargeError: 413,
    errors.UnsupportedTypeError: 415,
}


def create_app(
    data_dir: Path | None = None,
    clock: Clock | None = None,
    libraries: list[Library] | None = None,
) -> FastAPI:
    data_dir = data_dir or Path(os.environ.get("MISSIONBOARD_DATA_DIR", DEFAULT_DATA_DIR))
    config_store = ConfigStore(data_dir)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config_store.migrate()
        db.migrate(data_dir)
        # Fail at startup, not mid-use, if settings were mistyped by hand.
        settings = SettingsRepository(config_store)
        settings.settings()
        settings.features()
        RoutinesRepository(config_store).list()  # and if a routine's times do not add up
        threading.Thread(target=app.state.voice.load, daemon=True).start()  # it takes a moment
        yield

    app = FastAPI(title="missionboard", lifespan=lifespan)
    app.state.config_store = config_store
    app.state.photo_store = PhotoStore(data_dir)
    app.state.sound_files = SoundFiles(data_dir)
    app.state.clock = clock or SystemClock()
    app.state.events_repository = EventsRepository(data_dir)
    app.state.day_repository = DayRepository(data_dir)
    app.state.background_store = BackgroundStore(data_dir)
    app.state.runs_repository = RunsRepository(data_dir)
    app.state.purchases_repository = PurchasesRepository(data_dir)
    # The natural voice (app/voice/): its model in data/voices/ or where
    # MISSIONBOARD_VOICE_MODEL says (the Docker image brings it).
    model = Path(os.environ.get("MISSIONBOARD_VOICE_MODEL", data_dir / "voices" / MODEL_NAME))
    app.state.voice = Voice(model, data_dir / "voice-cache")
    app.state.image_libraries = ImageLibraries(LIBRARIES if libraries is None else libraries)

    @app.exception_handler(errors.DomainError)
    def domain_error(request: Request, exc: errors.DomainError):
        return JSONResponse(status_code=ERROR_STATUS.get(type(exc), 400), content={"detail": str(exc)})

    @app.get("/api/health")
    def health():
        with db.connect(data_dir) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    app.include_router(parents_api.router)
    app.include_router(children_api.router)
    app.include_router(missions_api.router)
    app.include_router(templates_api.router)
    app.include_router(prizes_api.router)
    app.include_router(images_api.router)
    app.include_router(events_api.router)
    app.include_router(today_api.router)
    app.include_router(routines_api.router)
    app.include_router(voice_api.router)
    app.include_router(shop_api.router)
    app.include_router(songs_api.router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html", headers=NO_CACHE)

    app.mount("/static", AppStaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
