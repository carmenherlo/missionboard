"""Which season and which moment of the day it is (fondos y estaciones): the
background of the children's screens."""

from datetime import date

from app.settings import MOMENTS, Season


def current_season(seasons: tuple[Season, ...], day: date) -> Season:
    """The last one that has started; in January, the last of the list goes on."""
    started = [season for season in seasons if season.start <= day.strftime("%m-%d")]
    return started[-1] if started else seasons[-1]


def current_moment(season: Season, time: str) -> str:
    """The last moment that has started; before the morning, the night goes on."""
    started = [moment for moment in MOMENTS if getattr(season, moment) <= time]
    return started[-1] if started else "noche"
