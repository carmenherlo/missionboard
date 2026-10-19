import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"


def create_app(data_dir: Path | None = None) -> FastAPI:
    data_dir = data_dir or Path(os.environ.get("MISSIONBOARD_DATA_DIR", DEFAULT_DATA_DIR))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db.init_db(data_dir)
        yield

    app = FastAPI(title="missionboard", lifespan=lifespan)
    app.state.data_dir = data_dir

    @app.get("/api/health")
    def health():
        with db.connect(data_dir) as conn:
            conn.execute("SELECT 1")
        return {"status": "ok"}

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
