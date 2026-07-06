import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import polars as pl
    from datetime import datetime
    import logging

    return datetime, logging, pl


@app.cell
def _():
    fichier = "GAM-Patient-ERV-CARBA.csv"
    return (fichier,)


@app.cell
def _(datetime, logging, pl):
    # transform/gam_mouvements.py
    # Configuration des logs pour le suivi du pipeline
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    def parser_dates_gam(df: pl.DataFrame) -> pl.DataFrame:
        """Type les colonnes temporelles du fichier GAM brut."""
        return df.with_columns(
            [
                pl.col("DATE_DEBUT_MOUVEMENT").cast(pl.String).str.to_datetime(),
                pl.col("DATE_FIN_MOUVEMENT").cast(pl.String).str.to_datetime(),
                pl.col("DATE_ENTREE_SEJOUR").cast(pl.String).str.to_datetime(),
                pl.col("DATE_SORTIE_SEJOUR").cast(pl.String).str.to_datetime(),
            ]
        )

    def statut_sejour(df: pl.DataFrame) -> pl.DataFrame:
        """
        Définit le statut du séjour :
        - 'planned' si la date d'entrée est dans le futur par rapport à la date du jour.
        - 'in-progress' si la date de sortie n'est pas définie (NONE).
        - 'finished' si la date de sortie est définie.
        """
        date_du_jour = datetime.now()
        return df.with_columns(
            pl.when(pl.col("DATE_ENTREE_SEJOUR") > pl.lit(date_du_jour))
            .then(pl.lit("planned"))
            .when(pl.col("DATE_SORTIE_SEJOUR").is_null())
            .then(pl.lit("in-progress"))
            .otherwise(pl.lit("finished"))
            .alias("STATUT_SEJOUR")
        )

    def mouvements_gam(chemin_fichier: str) -> pl.DataFrame:
        """
        Fonction maîtresse orchestrant uniquement les transformations du fichier GAM.
        Retourne le DataFrame intégralement transformé, prêt pour la suite du pipeline.
        """
        logging.info(
            f"Démarrage des transformations de l'extraction GAM : {chemin_fichier}"
        )

        df_raw = pl.read_csv(chemin_fichier, separator=",")
        df_parsed = parser_dates_gam(df_raw)
        df_statut = statut_sejour(df_parsed)

        logging.info(
            f"Transformations GAM terminées. Nombre de lignes générées : {df_statut.height}"
        )

        return df_statut

    return (mouvements_gam,)


@app.cell
def _(fichier, mouvements_gam):
    bhre = mouvements_gam(chemin_fichier=fichier)
    return (bhre,)


@app.cell
def _(bhre):
    bhre
    return


if __name__ == "__main__":
    app.run()
