"""Pick an image for a step or mission from its text.

Only the featured images (the ones useful for routines) are candidates, so
a wrong guess is unlikely. Matching ignores case and accents and works on
whole words or long prefixes (at least 4 letters: "diente" ↔ "dientes").
The image with most matching words wins; with none, there is no suggestion.
"""

import re
import unicodedata

# Words that say nothing about the picture: articles and the like, and generic
# verbs ("ponerse el pijama" must not match "poner la mesa").
STOPWORDS = {
    "a", "al", "con", "de", "del", "el", "en", "la", "las", "lo", "los", "mi", "mis",
    "para", "por", "se", "su", "sus", "tu", "tus", "un", "una", "y",
    "hacer", "ir", "poner", "ponerse", "quitar", "quitarse", "preparar", "coger", "tomar",
    "lavar", "lavarse", "dejar", "llevar", "sacar", "meter",
}
MIN_PREFIX = 4


def words(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return [w for w in re.split(r"[^a-z0-9]+", plain) if len(w) >= 3 and w not in STOPWORDS]


def _matches(token: str, word: str) -> bool:
    if token == word:
        return True
    shorter, longer = sorted((token, word), key=len)
    return len(shorter) >= MIN_PREFIX and longer.startswith(shorter)


def best_match(text: str, candidates: list[tuple[str, set[str]]]) -> str | None:
    """candidates: (image ref, its words), in preference order. Returns a ref or None."""
    tokens = words(text)
    best_ref, best_score = None, 0
    for ref, item_words in candidates:
        score = sum(1 for token in tokens if any(_matches(token, w) for w in item_words))
        if score > best_score:
            best_ref, best_score = ref, score
    return best_ref
