# Copyright (c) 2026
# Tous droits réservés CHU Brest.

import polars as pl


def norm(col):
    """Normalise une colonne texte : trim + minuscule, null -> ''."""
    return pl.col(col).cast(pl.Utf8).fill_null("").str.strip_chars().str.to_lowercase()
