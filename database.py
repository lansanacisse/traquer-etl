import oracledb

from config import GLIMS_CONFIG, GAM_CONFIG


def get_oracle_connection(config, database_name):
    """
    Création d'une connexion Oracle.

    database_name :
        Nom lisible de la base pour les logs (GLIMS ou GAM)
    """

    try:
        print(f"[{database_name}] Tentative de connexion Oracle...")

        dsn = oracledb.makedsn(
            config["host"],
            config["port"],
            service_name=config["service_name"],
        )

        conn = oracledb.connect(
            user=config["username"],
            password=config["password"],
            dsn=dsn,
        )

        print(f"[{database_name}] Connexion Oracle réussie")

        return conn

    except Exception as e:
        print(f"[{database_name}] Echec de connexion Oracle")
        print(f"[{database_name}] Erreur : {e}")
        raise


def get_glims_connection():
    """
    Connexion à la base GLIMS.
    """
    return get_oracle_connection(
        GLIMS_CONFIG,
        "GLIMS",
    )


def get_gam_connection():
    """
    Connexion à la base GAM.
    """
    return get_oracle_connection(
        GAM_CONFIG,
        "GAM",
    )
