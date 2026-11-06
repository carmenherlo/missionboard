import pytest

from app.images.libraries import LIBRARIES, ImageLibraries
from app.images.suggest import best_match, words


@pytest.mark.parametrize(
    "text, ref",
    [
        ("Hacer la cama", "fluent/bed"),
        ("Vestirse", "fluent/t-shirt"),
        ("Desayunar", "fluent/bowl-with-spoon"),
        ("Lavarse los dientes", "fluent/toothbrush"),
        ("Lavarse las manos", "fluent/soap"),
        ("Preparar la mochila", "fluent/backpack"),
        ("Recoger los juguetes", "fluent/teddy-bear"),
        ("Despegue", "fluent/rocket"),
        ("Merendar", "fluent/glass-of-milk"),
        ("Peinarse", None),
        ("Ponerse el pijama", "own/pajamas"),  # not "poner la mesa"
    ],
)
def test_suggestions_for_common_steps(text, ref):
    assert ImageLibraries(LIBRARIES).suggest(text) == ref


def test_words_ignore_case_accents_and_filler():
    assert words("Lavarse los DIENTES después") == ["dientes", "despues"]


def test_more_matching_words_win():
    candidates = [("x/one", {"cama"}), ("x/two", {"cama", "hacer"} | {"deshacer"}), ("x/three", {"cama", "sabanas"})]
    assert best_match("cama sabanas", candidates) == "x/three"


def test_long_prefixes_match_short_ones_do_not():
    assert best_match("dientes", [("x/a", {"diente"})]) == "x/a"
    assert best_match("mes", [("x/a", {"mesa"})]) is None
