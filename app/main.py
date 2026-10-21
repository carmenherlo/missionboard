import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import errors
from app.children import api as children_api
from app.clock import Clock, SystemClock
from app.parents import api as parents_api
from app.settings import SettingsRepository
from app.storage import db
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

ERROR_STATUS = {
    errors.NotFoundError: 404,
    errors.ConflictError: 409,
    errors.InvalidError: 422,
    errors.PermissionDeniedError: 403,
    errors.TooLargeError: 413,
    errors.UnsupportedTypeError: 415,
}


def create_app(data_dir: Path | None = None, clock: Clock | None = None) -> FastAPI:
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
        yield

    app = FastAPI(title="missionboard", lifespan=lifespan)
    app.state.config_store = config_store
    app.state.photo_store = PhotoStore(data_dir)
    app.state.clock = clock or SystemClock()

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

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
