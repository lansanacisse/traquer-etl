# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""
Extraction Oracle : première étape du pipeline.

Une fonction générique exécute une requête Oracle et renvoie
les données brutes sous forme de DataFrame Polars.

GLIMS et GAM utilisent deux connexions Oracle différentes :
- GLIMS -> service GLIMST
- GAM   -> service GAM
"""

import polars as pl

from database import (
    get_glims_connection,
    get_gam_connection,
)

from queries.GAM_traquer import GAM_EXTRACT_QUERY
from queries.GLIMS_traquer import GLIMS_EXTRACT_QUERY


def extract_data(
    query: str,
    source: str,
    connection_factory,
) -> pl.DataFrame:
    """
    Execute une requête Oracle et retourne un DataFrame Polars.

    query :
        requête SQL à exécuter

    source :
        nom affiché dans les logs

    connection_factory :
        fonction permettant d'obtenir la connexion Oracle adaptée
    """

    print(f"Début de l'extraction {source}...")

    try:
        with connection_factory() as conn:

            print("Exécution de la requête SQL...")

            df = pl.read_database(
                query=query,
                connection=conn,
            )

        print(f"Extraction {source} terminée - " f"{df.height} lignes récupérées")

        return df

    except Exception as e:

        print(f"Echec de l'extraction {source}")
        print(f"{e}")

        raise


def extract_oraglims_data() -> pl.DataFrame:
    """
    Extraction microbiologie GLIMS.
    """

    return extract_data(
        GLIMS_EXTRACT_QUERY,
        "ORAGLIMS",
        get_glims_connection,
    )


def extract_gam_data() -> pl.DataFrame:
    """
    Extraction mouvements et séjours GAM.
    """

    return extract_data(
        GAM_EXTRACT_QUERY,
        "GAM",
        get_gam_connection,
    )
