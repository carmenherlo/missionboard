"""Spanish texts of the event log: details, descriptions and CSV columns.

The log stores codes and names; the sentences are written here when the
log is read, so they can be improved without touching stored events.
"""

DAYS = {"mon": "L", "tue": "M", "wed": "X", "thu": "J", "fri": "V", "sat": "S", "sun": "D"}

ZONES = {"child": "niño", "parents": "padres"}

CSV_HEADER = ["día", "hora", "zona", "tipo", "niño", "misión", "paso", "detalle", "descripción"]


def _schedule(schedule) -> str:
    if schedule is None:
        return "horario: siempre abierta"
    if schedule.end is None:
        return f"horario: desde {schedule.start}"
    return f"horario: {schedule.start}–{schedule.end}"


# How each changed field is written in the "detalle" column.
_FIELDS = {
    "name": lambda value: f"nombre: {value}",
    "text": lambda value: f"texto: {value}",
    "image": lambda value: "imagen cambiada" if value else "sin imagen",
    "days": lambda value: "días: " + " ".join(DAYS[day] for day in value),
    "schedule": _schedule,
    "avatar": lambda value: f"avatar: {value}",
    "color": lambda value: f"color: {value}",
    "order": lambda value: "orden: " + ", ".join(value),
}


def change_detail(changes: dict) -> str | None:
    """"días: L M X J · nombre: Mañana" for the fields that changed."""
    return " · ".join(_FIELDS[field](value) for field, value in changes.items()) or None


SCREENS = {
    "home": "el inicio",
    "event_log": "Registro de la prueba",
    "config": "Configurar",
    "change_code": "Código de padres",
    "children": "Niños",
    "child_new": "Añadir niño",
    "child_edit": "Editar niño",
    "missions": "Misiones",
    "child_missions": "Misiones de un niño",
    "mission_new": "Nueva misión",
    "mission_edit": "Editar misión",
    "step_edit": "Editar paso",
    "templates": "Plantillas",
    "template_new": "Nueva plantilla",
    "template_edit": "Editar plantilla",
    "template_apply": "Aplicar plantilla",
    "template_step_edit": "Editar paso de plantilla",
}

# config_changed, by (subject, action). Parents are the only ones who
# change the configuration, so it speaks to them.
_CONFIG = {
    ("child", "created"): "Añadiste a {child}",
    ("child", "changed"): "Cambiaste a {child}",
    ("child", "deleted"): "Borraste a {child}",
    ("mission", "created"): "Creaste «{mission}» para {child}",
    ("mission", "created_from_template"): "Aplicaste la plantilla «{mission}» a {child}",
    ("mission", "changed"): "Cambiaste «{mission}» de {child}",
    ("mission", "deleted"): "Borraste «{mission}» de {child}",
    ("missions", "reordered"): "Ordenaste las misiones de {child}",
    ("step", "created"): "Añadiste «{step}» a «{mission}» de {child}",
    ("step", "changed"): "Cambiaste «{step}» de «{mission}» de {child}",
    ("step", "deleted"): "Quitaste «{step}» de «{mission}» de {child}",
    ("steps", "reordered"): "Ordenaste los pasos de «{mission}» de {child}",
    ("template", "created"): "Creaste la plantilla «{mission}»",
    ("template", "created_from_mission"): "Guardaste la misión de {child} como plantilla «{mission}»",
    ("template", "changed"): "Cambiaste la plantilla «{mission}»",
    ("template", "deleted"): "Borraste la plantilla «{mission}»",
    ("template_step", "created"): "Añadiste «{step}» a la plantilla «{mission}»",
    ("template_step", "changed"): "Cambiaste «{step}» de la plantilla «{mission}»",
    ("template_step", "deleted"): "Quitaste «{step}» de la plantilla «{mission}»",
    ("template_steps", "reordered"): "Ordenaste los pasos de la plantilla «{mission}»",
    ("parent_code", "changed"): "Cambiaste el código de padres",
}


def _about(event) -> str:
    """«Leer un cuento» de «Alunizaje» de Bea: what a screen was showing."""
    parts = [f"«{name}»" for name in (event.step_text, event.mission_name) if name]
    if event.child_name:
        parts.append(event.child_name)
    return " de ".join(parts)


def describe(event) -> str:
    """The sentence for the "descripción" column and the latest events list."""
    if event.type == "parents_entered":
        return "Entraste en la zona de padres"
    if event.type == "screen_opened":
        screen = SCREENS.get(event.subject, event.subject)
        sentence = f"Abriste {screen}" if event.zone == "parents" else f"Se abrió {screen}"
        about = _about(event)
        return f"{sentence} · {about}" if about else sentence
    if event.type == "config_changed":
        template = _CONFIG.get((event.subject, event.action), f"{event.subject}: {event.action}")
        sentence = template.format(child=event.child_name, mission=event.mission_name, step=event.step_text)
        return f"{sentence} · {event.detail}" if event.detail else sentence
    return event.type
