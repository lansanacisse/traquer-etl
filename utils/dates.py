from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl

FUSEAU = ZoneInfo("Europe/Paris")


def julian_to_datetime(value):
    """Convertit une date julienne GLIMS en datetime Europe/Paris."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=FUSEAU)
        return value
    value = float(value) - 1.5
    unix_epoch = 2440587.5
    seconds = (value - unix_epoch) * 86400
    return datetime.fromtimestamp(seconds, tz=FUSEAU)


def parser_colonnes_datetime(df, colonnes):
    """Type une liste de colonnes texte (dates Oracle) en Datetime.

    Ne traite que les colonnes presentes dans le DataFrame.
    """
    presentes = [c for c in colonnes if c in df.columns]
    if not presentes:
        return df
    return df.with_columns(
        [pl.col(c).cast(pl.String).str.to_datetime() for c in presentes]
    )
