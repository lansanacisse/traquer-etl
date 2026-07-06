import logging
from datetime import datetime

import polars as pl

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
    presentes = [c for c in COLONNES_DATES_GAM if c in df.columns]
    if not presentes:
        return df
    return df.with_columns(
        [pl.col(c).cast(pl.String).str.to_datetime() for c in presentes]
    )


def statut_sejour(df: pl.DataFrame) -> pl.DataFrame:
    """
    Definit le statut du sejour :
    - 'Programme' si la date d'entree est dans le futur.
    - 'En cours'  si la date de sortie n'est pas definie.
    - 'Termine'   si la date de sortie est definie.
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


def mouvements_gam_csv(chemin_fichier: str) -> pl.DataFrame:
    """Commodite test / notebook : lit un CSV GAM puis transforme."""
    df_raw = pl.read_csv(chemin_fichier, separator=",")
    return mouvements_gam(df_raw)
