"""A routine's times and songs, worked out on its stored form (a dict), so the
model, the repository and the editor all settle a routine the same way."""


def card_positions(doc: dict) -> dict[str, int]:
    """Where a song can start or end, in order: the alarm (-1), each part, the goal."""
    timed = doc.get("wake") is not None
    parts = doc.get("parts") or []
    cards = {part["id"]: index for index, part in enumerate(parts)}
    if timed and doc.get("alarm", True):
        cards["alarm"] = -1
    if doc.get("goal"):  # started by hand too: its goal comes after the parts
        cards["goal"] = len(parts)
    return cards


def minute_of(hhmm: str) -> int:
    """ "06:50" → 410 (minute of the day)."""
    hours, minutes = map(int, hhmm.split(":"))
    return hours * 60 + minutes


def hhmm(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def settled(doc: dict) -> dict:
    """Only the pinned time stays put (05/11): the parts have only their minutes, one
    after the other. Starting at a time ("Empieza a las"): from the first part's time,
    and the goal comes when they end (after checking the missions). Ending at a time
    ("Termina a las"): the last ends at its goal; the first part (and when it rings, as
    many minutes before as it was) moves to fit. Started by hand, its goal has no time."""
    if doc.get("wake") is None and doc.get("goal"):
        return {**doc, "goal": {**doc["goal"], "at": None}}
    if doc.get("wake") is None or not doc.get("parts"):
        return doc
    if doc.get("anchor") != "end":
        parts = [{**part, "at": None} for part in doc["parts"]]
        parts[0]["at"] = doc["parts"][0].get("at") or doc["wake"]
        if not doc.get("goal"):
            return {**doc, "parts": parts}
        end = minute_of(parts[0]["at"]) + sum(part["minutes"] for part in parts) + doc["goal"].get("check_minutes", 0)
        return {**doc, "parts": parts, "goal": {**doc["goal"], "at": hhmm(end % (24 * 60))}}
    if not doc.get("goal"):
        return doc
    parts = [{**part, "at": None} for part in doc["parts"]]
    first_at = doc["parts"][0].get("at")
    lead = (minute_of(first_at) - minute_of(doc["wake"])) % (24 * 60) if first_at else 0
    start = minute_of(doc["goal"]["at"]) - doc["goal"].get("check_minutes", 0) - sum(part["minutes"] for part in parts)
    if start < 0:
        return doc  # it would start the day before: refused as it is
    parts[0]["at"] = hhmm(start)
    return {**doc, "parts": parts, "wake": hhmm((start - lead) % (24 * 60))}


def music_kept(doc: dict) -> dict:
    """After any change, each song still from a card to a card: without the alarm, from
    the first part; a card gone, it goes (where it started) or ends there once (where
    it ended); moved round so that two would meet, the earlier one plays just once."""
    cards = card_positions(doc)
    first = doc["parts"][0]["id"] if doc.get("parts") else None
    kept, end = [], -2
    music = [dict(m) for m in doc.get("music") or []]
    for m in music:
        if m["start"] == "alarm" and "alarm" not in cards:
            m["start"] = first
        if m.get("until") not in cards or cards[m["until"]] < cards.get(m["start"], 0) or m["until"] == "alarm":
            m["until"] = None
    for m in sorted((m for m in music if m["start"] in cards), key=lambda m: cards[m["start"]]):
        start = cards[m["start"]]
        if start <= end:
            if kept and cards[kept[-1]["start"]] == start:
                continue  # two from the same card: the first one stays
            kept[-1]["until"] = None
        kept.append(m)
        end = cards[m["until"]] if m["until"] else start
    return {**doc, "music": kept}
