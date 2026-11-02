from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.children.repository import ChildrenRepository
from app.deps import (
    get_config_store,
    get_event_log,
    get_image_libraries,
    get_photo_store,
    require_parent,
)
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.api import MissionCreate, Presenter, add_editing_routes
from app.missions.repository import MissionsRepository
from app.storage.config_store import ConfigStore
from app.storage.photo_store import PhotoStore
from app.templates.repository import TemplatesRepository
from app.templates.service import TemplatesService

router = APIRouter(prefix="/api", tags=["templates"])
parent_only = [Depends(require_parent)]


class ApplyIn(BaseModel):
    child_ids: list[str]


def get_templates_service(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    events: EventLog = Depends(get_event_log),
) -> TemplatesService:
    return TemplatesService(
        TemplatesRepository(store),
        MissionsRepository(store),
        ChildrenRepository(store),
        libraries,
        photos,
        events,
    )


@router.get("/templates")
def list_templates(templates: TemplatesService = Depends(get_templates_service), present: Presenter = Depends()):
    return [present(t) for t in templates.list_all()]


@router.post("/templates", status_code=201, dependencies=parent_only)
def create_template(
    body: MissionCreate,
    templates: TemplatesService = Depends(get_templates_service),
    present: Presenter = Depends(),
):
    return present(templates.create(body.name, body.image))


@router.post("/templates/{template_id}/apply", status_code=201, dependencies=parent_only)
def apply_template(
    template_id: str,
    body: ApplyIn,
    templates: TemplatesService = Depends(get_templates_service),
    present: Presenter = Depends(),
):
    """Copy the template to each child; returns the new missions."""
    return [present(m) for m in templates.apply(template_id, body.child_ids)]


@router.post("/missions/{mission_id}/template", status_code=201, dependencies=parent_only)
def save_as_template(
    mission_id: str,
    templates: TemplatesService = Depends(get_templates_service),
    present: Presenter = Depends(),
):
    return present(templates.save_mission(mission_id))


add_editing_routes(router, "/templates", get_templates_service)
