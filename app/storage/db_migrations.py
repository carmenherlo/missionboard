"""The SQLite schema, as the migrations that build it (see db.migrate). From 17 on, in
db_migrations_recent.py."""

from app.storage.db_migrations_recent import RECENT

# Schema migrations, applied in order. The schema version is the number
# applied so far (stored in PRAGMA user_version). Never edit or reorder
# an entry once released: add a new one instead. No trailing "--" comments:
# migrate() appends the version bump after each script.
MIGRATIONS: list[str] = [
    # 1 · The event log: what happens in the app, with a copy of the names
    # at that moment (history must not depend on the configuration).
    """
    CREATE TABLE events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        at TEXT NOT NULL,
        day TEXT NOT NULL,
        zone TEXT NOT NULL,
        type TEXT NOT NULL,
        subject TEXT,
        action TEXT,
        child_id TEXT,
        child_name TEXT,
        mission_id TEXT,
        mission_name TEXT,
        step_id TEXT,
        step_text TEXT,
        detail TEXT
    );
    CREATE INDEX events_day ON events (day)
    """,
    # 2 · A child's day: the steps checked and the missions completed, per
    # app day (a new day starts empty), and every star won or spent as a
    # movement of their piggy bank (the balance is the sum).
    """
    CREATE TABLE step_checks (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        step_id TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id, step_id)
    );
    CREATE TABLE mission_completions (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        child_name TEXT,
        mission_name TEXT,
        stars INTEGER NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id)
    );
    CREATE TABLE star_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id TEXT NOT NULL,
        child_name TEXT,
        amount INTEGER NOT NULL,
        reason TEXT NOT NULL,
        mission_id TEXT,
        mission_name TEXT,
        day TEXT NOT NULL,
        at TEXT NOT NULL
    );
    CREATE INDEX star_movements_child ON star_movements (child_id)
    """,
    # 3 · The daily prize: what each child won each day on the wheel, with a
    # copy of the prize as it was (prizes can be renamed or deleted later).
    """
    CREATE TABLE prize_spins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        child_name TEXT,
        prize_id TEXT,
        prize_text TEXT NOT NULL,
        prize_image TEXT,
        at TEXT NOT NULL
    );
    CREATE INDEX prize_spins_day ON prize_spins (day, child_id)
    """,
    # 4 · Routines: what happened to each routine each day, so it does not
    # ring again once stopped, closed or finished (on any device).
    """
    CREATE TABLE routine_runs (
        day TEXT NOT NULL,
        routine_id TEXT NOT NULL,
        started_at TEXT,
        stopped_at TEXT,
        closed_phase TEXT,
        finished_at TEXT,
        PRIMARY KEY (day, routine_id)
    )
    """,
    # 5 · A routine started by hand remembers who it is with (JSON list of child ids).
    """
    ALTER TABLE routine_runs ADD COLUMN kids TEXT
    """,
    # 6 · The shop: what each child bought, with a copy of the item as it was;
    # delivered_at is set once a parent hands it over (step 7).
    """
    CREATE TABLE purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        child_name TEXT,
        item_id TEXT,
        item_text TEXT NOT NULL,
        item_image TEXT,
        price INTEGER NOT NULL,
        at TEXT NOT NULL,
        delivered_at TEXT
    );
    CREATE INDEX purchases_child ON purchases (child_id)
    """,
    # 7 · A mission a parent has opened for a child, only that day.
    """
    CREATE TABLE mission_openings (
        day TEXT NOT NULL,
        child_id TEXT NOT NULL,
        mission_id TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (day, child_id, mission_id)
    )
    """,
    # 8 · A purchase is an order on its way (tienda-2.html): the day a parent says it
    # arrives, when the child saw it arrive, and the last day the parents' phones were
    # reminded. Those already handed over count as seen.
    """
    ALTER TABLE purchases ADD COLUMN due_day TEXT;
    ALTER TABLE purchases ADD COLUMN seen_at TEXT;
    ALTER TABLE purchases ADD COLUMN reminded_day TEXT;
    UPDATE purchases SET seen_at = delivered_at WHERE delivered_at IS NOT NULL
    """,
    # 9 · Padres · Hoy (step 7): a prize of the wheel handed over by a parent.
    """
    ALTER TABLE prize_spins ADD COLUMN delivered_at TEXT
    """,
    # 10 · Rachas (rachas.html): how each child's week ended (its prize, if any, with a
    # copy of its text; when they saw it and when a parent handed it over), and the days
    # a parent let off (ill, away): they neither count nor break the week.
    """
    CREATE TABLE streak_weeks (
        child_id TEXT NOT NULL,
        child_name TEXT NOT NULL,
        week_end TEXT NOT NULL,
        tier TEXT NOT NULL,
        prize_text TEXT NOT NULL,
        full_days INTEGER NOT NULL,
        days INTEGER NOT NULL,
        at TEXT NOT NULL,
        shown_at TEXT,
        delivered_at TEXT,
        PRIMARY KEY (child_id, week_end)
    );
    CREATE TABLE free_days (
        child_id TEXT NOT NULL,
        day TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (child_id, day)
    )
    """,
    # 11 · The rocket's workshop (taller.html): a full tank the child loaded into the
    # rocket (they tap it; its light on the rocket comes on).
    """
    CREATE TABLE fuel_loads (
        child_id TEXT NOT NULL,
        day TEXT NOT NULL,
        at TEXT NOT NULL,
        PRIMARY KEY (child_id, day)
    )
    """,
    # 12 · The picture of a week's prize (13/11), copied with its text when the week closes.
    """
    ALTER TABLE streak_weeks ADD COLUMN prize_image TEXT
    """,
    # 13 · Momentos de vales (vales-2.html): a parent opens one for a while, and each child
    # picks a gift card from their chest (a copy of its text; the card itself is the prize
    # of the wheel or of the week, used once delivered).
    """
    CREATE TABLE voucher_moments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        ends_at TEXT NOT NULL,
        ended_at TEXT
    );
    CREATE TABLE voucher_picks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moment_id INTEGER NOT NULL,
        child_id TEXT NOT NULL,
        child_name TEXT,
        voucher_id TEXT NOT NULL,
        prize_text TEXT NOT NULL,
        at TEXT NOT NULL
    )
    """,
    # 14 · A routine started by hand, paused by a parent (18/11): since when. On going on,
    # its start moves forward as long as it was paused.
    "ALTER TABLE routine_runs ADD COLUMN paused_at TEXT",
    # 15 · Días libres (dias-libres.html, 19/11): a day a child does not have to do, whole
    # (mission_id '') or one mission of it, with an optional sentence the voice says. It
    # takes in the free days of rachas (migration 10), which were whole days.
    """
    CREATE TABLE day_offs (
        child_id TEXT NOT NULL,
        day TEXT NOT NULL,
        mission_id TEXT NOT NULL DEFAULT '',
        phrase TEXT NOT NULL DEFAULT '',
        at TEXT NOT NULL,
        PRIMARY KEY (child_id, day, mission_id)
    );
    INSERT INTO day_offs (child_id, day, mission_id, phrase, at) SELECT child_id, day, '', '', at FROM free_days;
    DROP TABLE free_days
    """,
    # 16 · Rachas worked out each time (20/11): a week's result is no longer
    # stored when it closes, but read from the missions done and the days let off. A row
    # keeps only what happened: the child launched it (with the tier they saw), the prize
    # was handed over, and, once the week can no longer change, its final result (frozen_at).
    # Weeks that ended a week ago or more are over: their stored result stays as it was.
    # Each child's racha starts on a day (streak_starts): the days before are not judged.
    """
    CREATE TABLE streak_weeks_new (
        child_id TEXT NOT NULL,
        child_name TEXT NOT NULL,
        week_end TEXT NOT NULL,
        tier TEXT,
        full_days INTEGER,
        days INTEGER,
        frozen_at TEXT,
        prize_text TEXT NOT NULL DEFAULT '',
        prize_image TEXT,
        launched_at TEXT,
        launched_tier TEXT,
        delivered_at TEXT,
        PRIMARY KEY (child_id, week_end)
    );
    INSERT INTO streak_weeks_new
        SELECT child_id, child_name, week_end, tier, full_days, days,
               CASE WHEN week_end <= date('now', '-7 days') THEN at END,
               prize_text, prize_image, shown_at, CASE WHEN shown_at IS NOT NULL THEN tier END, delivered_at
        FROM streak_weeks;
    CREATE TABLE streak_starts (
        child_id TEXT PRIMARY KEY,
        day TEXT NOT NULL
    );
    INSERT INTO streak_starts (child_id, day)
        SELECT child_id, MIN(CASE WHEN days > 0 THEN date(week_end, '-6 days') ELSE date(week_end, '+1 day') END)
        FROM streak_weeks GROUP BY child_id;
    DROP TABLE streak_weeks;
    ALTER TABLE streak_weeks_new RENAME TO streak_weeks
    """,
    *RECENT,
]
