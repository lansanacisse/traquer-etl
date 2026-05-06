import polars as pl

from database import get_oracle_connection
from sql_queries import EXTRACT_QUERY


def extract_oraglims_data() -> pl.DataFrame:
    print("Début de l'extraction ORAGLIMS...")

    try:
        with get_oracle_connection() as conn:
            print("Exécution de la requête SQL...")

            df = pl.read_database(
                query=EXTRACT_QUERY,
                connection=conn,
            )

        print(f"Extraction terminée - {df.height} lignes récupérées")

        return df

    except Exception as e:
        print("Echec de l'extraction")
        print(f"{e}")
        raise


# if __name__ == "__main__":
#     extract_oraglims_data()
#     print("Test d'extraction terminée")
