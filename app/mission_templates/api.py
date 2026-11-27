"""The mission templates: to see them, and to use one (Nueva misión, primer-arranque.html)."""

from fastapi import APIRouter, Depends

from app.children import avatars
from app.children.repository import ChildrenRepository
from app.deps import get_config_store, get_event_log, get_image_libraries, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.mission_templates.service import MissionTemplatesService
from app.missions.api import Presenter
from app.missions.repository import MissionsRepository
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api", tags=["mission templates"])
parent_only = [Depends(require_parent)]


def get_templates_service(
    store: ConfigStore = Depends(get_config_store), events: EventLog = Depends(get_event_log)
) -> MissionTemplatesService:
    return MissionTemplatesService(MissionsRepository(store), ChildrenRepository(store), events)


@router.get("/mission-templates")
def list_templates(
    templates: MissionTemplatesService = Depends(get_templates_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
):
    return [
        {
            "id": template["id"],
            "name": template["name"],
            "image_url": libraries.url(template["image"]),
            "color": template["color"],
            "colors": avatars.tones(template["color"]),
            "tasks": [{"text": t["text"], "image_url": libraries.url(t["image"])} for t in template["tasks"]],
        }
        for template in templates.list()
    ]


@router.post("/mission-templates/{template_id}/use", status_code=201, dependencies=parent_only)
def use_template(
    template_id: str,
    templates: MissionTemplatesService = Depends(get_templates_service),
    present: Presenter = Depends(),
):
    return present(templates.use(template_id))
