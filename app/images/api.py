from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.deps import get_image_libraries, get_photo_store
from app.errors import NotFoundError
from app.images.libraries import ImageLibraries
from app.images.photos import PHOTO_FILENAME
from app.storage.photo_store import PhotoStore

router = APIRouter(prefix="/api", tags=["images"])


@router.get("/images")
def list_libraries(libraries: ImageLibraries = Depends(get_image_libraries)):
    """Every library with its catalog; the browser searches it locally."""
    return {"libraries": libraries.catalogs()}


@router.get("/photos/{filename}")
def get_photo(filename: str, photos: PhotoStore = Depends(get_photo_store)):
    path = photos.path(filename) if PHOTO_FILENAME.match(filename) else None
    if path is None:
        raise NotFoundError("Photo not found")
    return FileResponse(path)
