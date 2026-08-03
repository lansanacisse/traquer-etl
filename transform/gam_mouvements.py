# Copyright (c) 2026
# Tous droits réservés CHU Brest.


import logging
from datetime import datetime

import polars as pl

from utils.dates import parser_colonnes_datetime

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

COLONNES_DATES_GAM = [
    "EVENT_TIME",
    "DATE_DEBUT_MOUVEMENT",
    "DATE_FIN_MOUVEMENT",
    "DATE_ENTREE_SEJOUR",
    "DATE_SORTIE_SEJOUR",
]


def parser_dates_gam(df: pl.DataFrame) -> pl.DataFrame:
    """Type les colonnes temporelles GAM presentes en Datetime."""
    return parser_colonnes_datetime(df, COLONNES_DATES_GAM)


def statut_sejour(df: pl.DataFrame) -> pl.DataFrame:
    """
    Definit le statut FHIR du sejour (Encounter.status) :
    - 'planned'     si la date d'entree est dans le futur.
    - 'in-progress' si la date de sortie n'est pas definie.
    - 'completed'   si la date de sortie est definie.
    """
    date_du_jour = datetime.now()
    return df.with_columns(
        pl.when(pl.col("DATE_ENTREE_SEJOUR") > pl.lit(date_du_jour))
        .then(pl.lit("planned"))
        .when(pl.col("DATE_SORTIE_SEJOUR").is_null())
        .then(pl.lit("in-progress"))
        .otherwise(pl.lit("completed"))
        .alias("STATUT_SEJOUR")
    )


def mouvements_gam(df: pl.DataFrame) -> pl.DataFrame:
    """
    Transforme un DataFrame GAM deja charge (usage prod, sortie de extract).
    Retourne le DataFrame transforme, pret pour la suite du pipeline.
    """
    logging.info("Démarrage des transformations GAM (%s lignes).", df.height)
    df_parsed = parser_dates_gam(df)
    df_statut = statut_sejour(df_parsed)
    logging.info("Transformations GAM terminées. Lignes : %s", df_statut.height)
    return df_statut


COLONNES_TEXTE_GAM = {
    "UF_ENTREE": pl.Utf8,
    "UF_SORTIE": pl.Utf8,
    "UFO_ID": pl.Utf8,
    "LIE_ETB_NUM": pl.Utf8,
    "LIE_BAT_NUM": pl.Utf8,
    "ETG_NUM": pl.Utf8,
    "LIE_NUM": pl.Utf8,
    "LIT_NUM": pl.Utf8,
}


def mouvements_gam_csv(chemin_fichier: str) -> pl.DataFrame:
    """Commodite test / notebook : lit un CSV GAM puis transforme."""
    df_raw = pl.read_csv(
        chemin_fichier,
        separator=",",
        schema_overrides=COLONNES_TEXTE_GAM,
        infer_schema_length=None,
    )
    return mouvements_gam(df_raw)
