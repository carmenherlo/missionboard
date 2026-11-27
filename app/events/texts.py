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
    "shop_for": lambda value: "para: " + (", ".join(value) or "nadie"),
    "price": lambda value: f"precio: {value} {'estrella' if value == 1 else 'estrellas'}",
    # Ajustes and the switches on each screen (ajustes.html)
    "stars_per_mission": lambda value: f"estrellas por misión: {value}",
    "daily_prize_spins": lambda value: f"giros de la ruleta: {value}",
    "starting_stars": lambda value: f"estrellas de un niño nuevo: {value}",
    "seasons": lambda value: (
        "estaciones: "
        + " · ".join(
            f"{SEASONS.get(s.name, s.name)} {s.start[3:]}/{s.start[:2]} {s.manana} {s.dia} {s.tarde} {s.noche}"
            for s in value
        )
    ),
    "home": lambda value: "aspecto del inicio cambiado",
    "gift": lambda value: stars_detail(value),
    "phrase": lambda value: f"«{value}»",
    "day": lambda value: f"el {value}",
    "card": lambda value: f"tarjeta «{value}» retirada",
    "route": lambda value: "aspecto de la ruta cambiado",
    "notify": lambda value: "avisos al móvil: " + (", ".join(value.phones) or "ninguno"),
    "shop_notify": lambda value: (
        "avisar de los pedidos: " + ("sí" if value.on else "no") + f", recordar a las {value.remind_at}"
    ),
    "due_day": lambda value: "llega " + (_day(value) if value else "pronto"),
    "daily_prize": lambda value: "premio del día " + ("encendido" if value else "apagado"),
    "shop": lambda value: "tienda " + ("encendida" if value else "apagada"),
    "streaks": lambda value: "rachas " + ("encendidas" if value else "apagadas"),
    "streak_week": lambda value: "semana de la racha cambiada",
    "streak_rule": lambda value: "la racha cuenta con " + ("una misión" if value == "any" else "todas las misiones"),
}


def _day(value) -> str:
    return f"el {value.day}/{value.month}"


def change_detail(changes: dict) -> str | None:
    """ "días: L M X J · nombre: Mañana" for the fields that changed."""
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
    "routine_closed": "Escondieron la rutina «{routine}» en un dispositivo",
    "routine_reopened": "Volvieron a ver la rutina «{routine}» en un dispositivo",
    "routine_finished": "Finalizaron la rutina «{routine}» por hoy",
    "routine_paused": "Pausaron la rutina «{routine}»",
    "routine_resumed": "La rutina «{routine}» siguió tras la pausa",
    "routine_ended": "Acabó la rutina «{routine}»",
    "routine_adjusted": "Rutina «{routine}»: {detail}",
    "race_fast": "Carrera «{routine}»: ¡muy rápido!",
    "race_record": "Carrera «{routine}»: ¡récord!",
    "race_won": "Carrera «{routine}»: ganaron al extraterrestre",
    "race_slow": "Carrera «{routine}»: acabaron, pero ganó el extraterrestre",
    "race_lost": "Carrera «{routine}»: se acabó el tiempo",
    "race_reviewed": "Revisaron la carrera «{routine}»",
    "race_redo": "Carrera «{routine}»: los jueces piden repasar",
}


SCREENS = {
    "home": ("el inicio", None),
    "child_today": ("la ruta de un niño", "la ruta de {child}"),
    "child_place": ("el sitio de un niño", "el sitio de {child}"),
    "child_garage": ("el taller de un niño", "el taller de {child}"),
    "event_log": ("Registro", None),
    "backup": ("Copia de seguridad", None),
    "display": ("Esta pantalla", None),
    "settings": ("Ajustes", None),
    "appearance": ("Apariencia", None),
    "appearance_home": ("Apariencia · Pantalla de inicio", None),
    "appearance_missions": ("Apariencia · Camino de misiones", None),
    "appearance_seasons": ("Apariencia · Fondos y estaciones", None),
    "stars_settings": ("Estrellas por misión", None),
    "streak_settings": ("Racha y premio de la semana", None),
    "parents_today": ("Padres · Hoy", None),
    "parents_to_give": ("Padres · Por dar", None),
    "settings_home": ("Ajustes", None),
    "parents_child": ("Ficha de un niño", "La ficha de {child}"),
    "day_settings": ("El día", None),
    "config": ("Configurar", None),
    "notify": ("Avisos al móvil", None),
    "change_code": ("Código de padres", None),
    "device": ("Este aparato", None),
    "children": ("Niños", None),
    "child_new": ("Añadir niño", None),
    "child_edit": ("Nombre y avatar de un niño", "Nombre y avatar de {child}"),
    "child_settings": ("Ajustes de un niño", "Ajustes de {child}"),
    "child_movements": ("Movimientos de un niño", "Movimientos de {child}"),
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
    "routine_start_edit": ("Editar inicio de rutina", None),
    "routine_goal_edit": ("Editar meta de rutina", None),
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
    ("stars", "taken"): "Quitaste estrellas a {child}",
    ("prize", "delivered"): "Diste el premio «{mission}» a {child}",
    ("order", "due"): "Dijiste cuándo le llega «{mission}» a {child}",
    ("order", "delivered"): "Entregaste «{mission}» a {child}",
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
    ("mission_kid", "on"): "Pusiste a {child} en «{mission}»",
    ("mission_kid", "off"): "Quitaste a {child} de «{mission}»",
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
    ("shop_item", "reordered"): "Ordenaste la tienda",
    ("week_prize", "delivered"): "Entregaste el premio de la semana a {child} · «{mission}»",
    ("vouchers", "moment_started"): "Empezaste un momento de vales",
    ("vouchers", "moment_ended"): "Terminaste el momento de vales",
    ("voucher", "used"): "Marcaste como usada la tarjeta regalo «{mission}» de {child}",
    ("voucher", "removed"): "Eliminaste la tarjeta regalo «{mission}» de {child}",
    ("voucher", "undone"): "Devolviste al baúl la tarjeta regalo «{mission}» de {child}",
    ("free_day", "on"): "Marcaste el {mission} como día libre de {child}",
    ("free_day", "off"): "Quitaste el día libre del {mission} de {child}",
    ("day_off", "on"): "Dejaste libre a {child} todo el día {mission}",
    ("day_off", "off"): "Quitaste el día libre de {child} del {mission}",
    ("mission_off", "on"): "Dejaste libre «{mission}» a {child}",
    ("mission_off", "off"): "Quitaste lo libre de «{mission}» a {child}",
    ("day", "reset"): "Dejaste el {mission} de {child} como lo marcó la app",
    ("mission", "undone"): "Deshiciste «{mission}» de {child}: no la había hecho",
    ("mission", "marked_done"): "Marcaste «{mission}» de {child} como hecha",
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
    "order_seen": "{child} vio llegar «{mission}»",
    "week_full": "{child} llenó todos los depósitos de la semana · {detail}",
    "week_second": "{child} ganó el premio pequeño de la semana · {detail}",
    "week_none": "A {child} le faltó combustible esta semana · {detail}",
    "fuel_loaded": "{child} cargó en el cohete el depósito del {detail}",
    "voucher_used": "{child} eligió su tarjeta regalo «{detail}»",
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
