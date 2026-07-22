import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Fusion  de données traquer**
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    # import library
    import polars as pl
    from zoneinfo import ZoneInfo
    from datetime import datetime, timedelta
    from pathlib import Path
    import sys
    import logging
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from transform.glims_biologie import biologie_glims_csv
    from transform.gam_mouvements import mouvements_gam_csv
    from transform.fusion_gam_glims import fusion_gam_glims

    return biologie_glims_csv, fusion_gam_glims, mouvements_gam_csv, pl


@app.cell
def _():
    GAM_pat = "GAM-Patient-ERV-CARBA.csv"
    GLIMS_pat = "GLIMS-Patient-ERV-CARBA.csv"
    return GAM_pat, GLIMS_pat


@app.cell
def _(GAM_pat, mouvements_gam_csv):
    df_gam_clean = mouvements_gam_csv(GAM_pat)
    df_gam_clean
    return (df_gam_clean,)


@app.cell
def _(GLIMS_pat, biologie_glims_csv):
    df_glims_clean = biologie_glims_csv(GLIMS_pat)
    df_glims_clean
    return (df_glims_clean,)


@app.cell
def _(df_gam_clean, df_glims_clean, fusion_gam_glims):
    df_fusion = fusion_gam_glims(df_gam_clean, df_glims_clean)
    df_fusion
    return (df_fusion,)


@app.cell
def _(pl):
    def statistiques(df):
        """Nombre de valeurs distinctes des principales entités."""

        return pl.DataFrame({
            "entite": [
                "patients (IPP)",
                "séjours (IEP)",
                "mouvements (ID_MOUVEMENT)",
                "dossiers (ORD_INTERNALID)",
            ],
            "nombre": [
                df.select(pl.col("IPP").drop_nulls().n_unique()).item(),
                df.select(pl.col("IEP").drop_nulls().n_unique()).item(),
                df.select(pl.col("ID_MOUVEMENT").drop_nulls().n_unique()).item(),
                df.select(pl.col("ORD_INTERNALID").drop_nulls().n_unique()).item(),
            ],
        })

    return (statistiques,)


@app.cell
def _(df_fusion, statistiques):
    stats = statistiques(df_fusion)
    print(stats)
    return


if __name__ == "__main__":
    app.run()
