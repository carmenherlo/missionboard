"""Spanish texts of the event log: details, descriptions and CSV columns.

The log stores codes and names; the sentences are written here when the
log is read, so they can be improved without touching stored events.
"""

SEASONS = {"primavera": "primavera", "verano": "verano", "otono": "otoño", "invierno": "invierno"}

DAYS = {"mon": "L", "tue": "M", "wed": "X", "thu": "J", "fri": "V", "sat": "S", "sun": "D"}

# No zone: nobody in particular (the home screen, before a child picks their avatar).
ZONES = {"child": "niño", "parents": "padres", None: ""}

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
    "price": lambda value: f"precio: {value} {'estrella' if value == 1 else 'estrellas'}",
    # Ajustes and the switches on each screen (ajustes.html)
    "stars_per_mission": lambda value: f"estrellas por misión: {value}",
    "daily_prize_spins": lambda value: f"giros de la ruleta: {value}",
    "starting_stars": lambda value: f"estrellas de un niño nuevo: {value}",
    "day_starts_at": lambda value: f"el día empieza a las {value}",
    "routine_warn_minutes": lambda value: f"aviso antes de acabar cada parte: {value} min",
    "seasons": lambda value: "estaciones: " + " · ".join(
        f"{SEASONS.get(s.name, s.name)} {s.start[3:]}/{s.start[:2]} {s.manana} {s.dia} {s.tarde} {s.noche}" for s in value),
    "home": lambda value: "aspecto del inicio cambiado",
    "gift": lambda value: stars_detail(value),
    "route": lambda value: "aspecto de la ruta cambiado",
    "daily_prize": lambda value: "premio del día " + ("encendido" if value else "apagado"),
    "shop": lambda value: "tienda " + ("encendida" if value else "apagada"),
    "routines": lambda value: "rutinas " + ("encendidas" if value else "apagadas"),
}


def change_detail(changes: dict) -> str | None:
    """"días: L M X J · nombre: Mañana" for the fields that changed."""
    return " · ".join(_FIELDS[field](value) for field, value in changes.items()) or None


# Each screen as its title reads, with the names it shows; the plain name
# when one of those no longer exists (the id was not found).
def stars_detail(stars: int) -> str:
    """ "+1 estrella", "-5 estrellas" """
    return f"{stars:+d} {'estrella' if abs(stars) == 1 else 'estrellas'}"


def locked_detail(locked: tuple[str, str]) -> str:
    why, time = locked
    return f"se abre a las {time}" if why == "opens" else f"se cerró a las {time}"


def routine_detail(*, seconds=None, part=None, early=False) -> str | None:
    if seconds is not None:
        return f"a los {seconds} s"
    if part:
        return part
    if early:
        return "antes de hora: todos habían firmado"
    return None


_ROUTINE = {
    "routine_started": "Sonó la rutina «{routine}»",
    "routine_stopped": "Pararon la rutina «{routine}»",
    "routine_part": "Rutina «{routine}»: empieza {detail}",
    "routine_goal": "Rutina «{routine}»: llega la meta",
    "routine_closed": "Cerraron la rutina «{routine}»",
    "routine_reopened": "Volvieron a la rutina «{routine}»",
    "routine_finished": "Finalizaron la rutina «{routine}» por hoy",
    "routine_ended": "Acabó la rutina «{routine}»",
}


SCREENS = {
    "home": ("el inicio", None),
    "child_today": ("la ruta de un niño", "la ruta de {child}"),
    "event_log": ("Registro", None),
    "backup": ("Copia de seguridad", None),
    "display": ("Pantalla", None),
    "settings": ("Ajustes", None),
    "appearance": ("Apariencia", None),
    "appearance_home": ("Apariencia · Pantalla de inicio", None),
    "appearance_missions": ("Apariencia · Camino de misiones", None),
    "appearance_seasons": ("Apariencia · Fondos y estaciones", None),
    "stars_settings": ("Estrellas", None),
    "day_settings": ("El día", None),
    "config": ("Configurar", None),
    "change_code": ("Código de padres", None),
    "children": ("Niños", None),
    "child_new": ("Añadir niño", None),
    "child_edit": ("Editar niño", "Editar a {child}"),
    "missions": ("Misiones", None),
    "child_missions": ("Misiones de un niño", "Misiones de {child}"),
    "mission_new": ("Nueva misión", None),
    "mission_edit": ("Editar misión", "Editar «{mission}»"),
    "mission_child": ("Misión de un niño", "«{mission}» de {child}"),
    "task_edit": ("Editar tarea", "Editar «{step}» de «{mission}»"),
    "step_edit": ("Editar paso", "Editar «{step}» de «{mission}»"),
    "prizes": ("Premios del día", None),
    "routines": ("Rutinas", None),
    "shop": ("Tienda", None),
    "shop_item_edit": ("Editar artículo de la tienda", None),
    "routine_new": ("Nueva rutina", None),
    "routine_edit": ("Editar rutina", None),
    "routine_part_edit": ("Editar parte de rutina", None),
    "routine_voice": ("Lo que dice la voz", None),
    "songs": ("Canciones", None),
    "routine_music": ("Canción de una rutina", None),
    "prize_edit": ("Editar premio", None),
    "avatars": ("Avatares", None),
    "avatar_new": ("Subir avatar", None),
    "avatar_edit": ("Editar avatar", None),
}

# config_changed, by (subject, action). Parents are the only ones who
# change the configuration, so it speaks to them.
_CONFIG = {
    ("child", "created"): "Añadiste a {child}",
    ("child", "changed"): "Cambiaste a {child}",
    ("child", "deleted"): "Borraste a {child}",
    ("mission", "created"): "Creaste «{mission}»",
    ("mission", "changed"): "Cambiaste «{mission}»",
    ("mission", "deleted"): "Borraste «{mission}»",
    ("mission", "opened_today"): "Abriste «{mission}» solo por hoy para {child}",
    ("stars", "given"): "Regalaste estrellas a {child}",
    ("missions", "reordered"): "Ordenaste las misiones",
    ("task", "created"): "Añadiste la tarea «{step}» a «{mission}»",
    ("task", "changed"): "Cambiaste la tarea «{step}» de «{mission}»",
    ("task", "deleted"): "Quitaste la tarea «{step}» de «{mission}»",
    ("tasks", "reordered"): "Ordenaste las tareas de «{mission}»",
    ("step", "created"): "Añadiste el paso «{step}» a «{mission}»",
    ("step", "changed"): "Cambiaste el paso «{step}» de «{mission}»",
    ("step", "deleted"): "Quitaste el paso «{step}» de «{mission}»",
    ("steps", "reordered"): "Ordenaste los pasos de «{mission}»",
    ("activation", "on"): "Activaste «{step}» de «{mission}» a {child}",
    ("activation", "off"): "Apagaste «{step}» de «{mission}» a {child}",
    ("parent_code", "changed"): "Cambiaste el código de padres",
    ("routine", "created"): "Creaste la rutina «{mission}»",
    ("routine", "changed"): "Cambiaste la rutina «{mission}»",
    ("routine", "deleted"): "Borraste la rutina «{mission}»",
    ("routine", "tested"): "Probaste la rutina «{mission}»",
    ("backup", "restored"): "Pusiste una copia de seguridad (lo que había quedó guardado en backups/)",
    ("routine_part", "created"): "Añadiste «{step}» a la rutina «{mission}»",
    ("routine_part", "changed"): "Cambiaste «{step}» de la rutina «{mission}»",
    ("routine_part", "deleted"): "Quitaste «{step}» de la rutina «{mission}»",
    ("shop_item", "created"): "Añadiste «{mission}» a la tienda",
    ("shop_item", "changed"): "Cambiaste «{mission}» de la tienda",
    ("shop_item", "deleted"): "Quitaste «{mission}» de la tienda",
    ("prize", "created"): "Añadiste el premio «{mission}»",
    ("prize", "changed"): "Cambiaste el premio «{mission}»",
    ("prize", "deleted"): "Borraste el premio «{mission}»",
    ("song", "created"): "Subiste la canción «{mission}»",
    ("song", "changed"): "Cambiaste la canción «{mission}»",
    ("song", "deleted"): "Borraste la canción «{mission}»",
    ("avatar", "created"): "Subiste el avatar «{mission}»",
    ("avatar", "changed"): "Cambiaste el avatar «{mission}»",
    ("avatar", "deleted"): "Borraste el avatar «{mission}»",
    ("settings", "changed"): "Cambiaste los ajustes",
    ("features", "changed"): "Cambiaste lo que está encendido",
}


# What a child does on their route ({detail} inside the sentence when it reads better there).
_CHILD = {
    "mission_opened": "{child} abrió «{mission}»",
    "step_checked": "{child} marcó «{step}» en «{mission}»",
    "step_unchecked": "{child} desmarcó «{step}» en «{mission}»",
    "mission_completed": "{child} completó «{mission}» · {detail}",
    "step_spoken": "{child} escuchó «{step}»",
    "mission_locked": "{child} tocó «{mission}», que {detail}",
    "prize_unlocked": "{child} desbloqueó el premio del día",
    "prize_locked": "{child} tocó el premio, aún bloqueado",
    "prize_spun": "{child} giró la ruleta · {detail}",
    "purchase": "{child} compró «{mission}» · {detail}",
}


def _screen(event) -> str:
    plain, with_names = SCREENS.get(event.subject, (event.subject, None))
    names = {"child": event.child_name, "mission": event.mission_name, "step": event.step_text}
    try:
        return with_names.format_map({k: v for k, v in names.items() if v}) if with_names else plain
    except KeyError:  # a name it needs is missing
        return plain


def describe(event) -> str:
    """The sentence for the "descripción" column and the latest events list."""
    if event.type == "parents_entered":
        return "Entraste en la zona de padres"
    if event.type == "screen_opened":
        return f"Abriste {_screen(event)}" if event.zone == "parents" else f"Se abrió {_screen(event)}"
    if event.type in _ROUTINE:
        sentence = _ROUTINE[event.type].format(routine=event.subject, detail=event.detail)
        if event.detail and "{detail}" not in _ROUTINE[event.type]:
            sentence = f"{sentence} · {event.detail}"
        return sentence
    if event.type in _CHILD:
        return _CHILD[event.type].format(
            child=event.child_name, mission=event.mission_name, step=event.step_text, detail=event.detail
        )
    if event.type == "config_changed":
        template = _CONFIG.get((event.subject, event.action), f"{event.subject}: {event.action}")
        sentence = template.format(child=event.child_name, mission=event.mission_name, step=event.step_text)
        return f"{sentence} · {event.detail}" if event.detail else sentence
    return event.type
