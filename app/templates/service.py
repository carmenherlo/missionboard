from app.children.repository import ChildrenRepository
from app.errors import InvalidError, NotFoundError
from app.images.libraries import ImageLibraries
from app.missions.repository import Mission, MissionsRepository
from app.missions.service import MissionEditor
from app.storage.photo_store import PhotoStore
from app.templates.repository import TemplatesRepository

NAME_MAX = 40  # same as a mission's name


def _unique_name(name: str, taken: set[str]) -> str:
    """The name, or "name (2)", "name (3)"… if it is already taken."""
    number = 2
    candidate = name
    while candidate in taken:
        suffix = f" ({number})"
        candidate = name[: NAME_MAX - len(suffix)].rstrip() + suffix
        number += 1
    return candidate


class TemplatesService(MissionEditor):
    """Templates: whole missions without a child, copied to children when applied.

    A copy never stays linked: changing a template does not change the
    missions made from it, nor the other way round.
    """

    not_found = "Template not found"

    def __init__(
        self,
        templates: TemplatesRepository,
        missions: MissionsRepository,
        children: ChildrenRepository,
        libraries: ImageLibraries,
        photos: PhotoStore,
    ):
        super().__init__(templates, libraries, photos)
        self._child_missions = missions
        self._children = children

    def list_all(self) -> list[Mission]:
        return self._missions.list_all()

    def create(self, name: str, image: str | None = None) -> Mission:
        with self._missions.atomic():
            template = self._new(None, name, image)
            self._missions.add(template)
        return template

    def apply(self, template_id: str, child_ids: list[str]) -> list[Mission]:
        """Give each child their own copy, at the end of their route."""
        if not child_ids or len(set(child_ids)) != len(child_ids):
            raise InvalidError("Choose one or more children, each once")
        with self._missions.atomic():
            template = self.get(template_id)
            for child_id in child_ids:
                if self._children.get(child_id) is None:
                    raise NotFoundError("Child not found")
            copies = [self._copy(template, child_id) for child_id in child_ids]
            for mission in copies:
                self._child_missions.add(mission)
        return copies

    def save_mission(self, mission_id: str) -> Mission:
        """A new template with everything in a child's mission."""
        with self._missions.atomic():
            mission = self._child_missions.get(mission_id)
            if mission is None:
                raise NotFoundError("Mission not found")
            taken = {t.name for t in self._missions.list_all()}
            template = self._copy(mission, None, name=_unique_name(mission.name, taken))
            self._missions.add(template)
        return template
