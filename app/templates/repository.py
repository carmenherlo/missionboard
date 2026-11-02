from app.missions.repository import Mission, MissionList


class TemplatesRepository(MissionList):
    """Templates: missions without a child, in the `templates` list of config.yaml."""

    section = "templates"

    def list_all(self) -> list[Mission]:
        return self._all()
