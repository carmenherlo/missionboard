"""The SQLite schema's later migrations, from 17 (modo carrera, 23/11): db_migrations.py adds
them after the first ones, in this order. Never edit or reorder an entry once released."""

RECENT: list[str] = [
    # 17 · Modo carrera (modo-carrera.html, 23/11). A routine started by hand keeps the
    # minutes a parent added to (or took from) its parts today (JSON {part id: minutes}).
    # Each race that ended: how long it took against its time, whether it won (fast,
    # won), only finished (slow) or ran out of time (lost: its mission closes then), the
    # extra stars each child gets and, when a parent checks first, whether they were given.
    """
    ALTER TABLE routine_runs ADD COLUMN extra TEXT;
    CREATE TABLE races (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        routine_name TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        kids TEXT NOT NULL,
        planned_seconds INTEGER NOT NULL,
        took_seconds INTEGER,
        outcome TEXT NOT NULL,
        stars INTEGER NOT NULL,
        at TEXT NOT NULL,
        reviewed_at TEXT,
        given INTEGER
    )
    """,
    # 18 · The alien trains (carrera-estrategia.html, 24/11): the share of the race's time
    # the alien took in each race (it runs like the team's last races).
    """
    ALTER TABLE races ADD COLUMN ghost_share REAL
    """,
    # 19 · «¡Ánimo, equipo!» (carrera-estrategia.html, 25/11): who cheered in today's race,
    # and in which task (JSON ["task id:child id", …]); each cheer makes the alien stumble.
    """
    ALTER TABLE routine_runs ADD COLUMN cheers TEXT
    """,
    # 20 · The week, mission by mission (semana-misiones.html, 25/11): the first time a parent
    # changes a child's day, how the app had left it (JSON {"done": {mission id: [stars, name]},
    # "off": {mission id or '': phrase}}), so «Deshacer cambios» can bring it back.
    """
    CREATE TABLE day_snapshots (
        child_id TEXT NOT NULL,
        day TEXT NOT NULL,
        snapshot TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (child_id, day)
    )
    """,
]
