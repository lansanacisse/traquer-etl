import oracledb
from config import ORACLE_CONFIG


def get_oracle_connection():
    try:
        print("Tentative de connexion à Oracle...")
        dsn = oracledb.makedsn(
            ORACLE_CONFIG["host"],
            ORACLE_CONFIG["port"],
            service_name=ORACLE_CONFIG["service_name"],
        )

        conn = oracledb.connect(
            user=ORACLE_CONFIG["username"],
            password=ORACLE_CONFIG["password"],
            dsn=dsn,
        )

        print("Connexion Oracle réussie")
        return conn

    except Exception as e:
        print("Echec de connexion à Oracle")
        print(f"{e}")
        raise


# if __name__ == "__main__":
#     with get_oracle_connection() as conn:
#         print("Test de connexion terminé")
