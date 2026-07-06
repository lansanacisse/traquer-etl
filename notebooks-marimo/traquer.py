import marimo

__generated_with = "0.23.9"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Normalisation et transformation de données traquer**
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Normalisation et transformation de données traquer**
    """)
    return


@app.cell
def _():
    # import library
    import polars as pl
    from zoneinfo import ZoneInfo
    from datetime import datetime, timedelta
    import sys
    import logging

    return (sys,)


@app.cell
def _(sys):
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from transform.glims_biologie import biologie_glims_csv
    from transform.gam_mouvements import mouvements_gam_csv

    return biologie_glims_csv, mouvements_gam_csv


@app.cell
def _():
    GAM_pat = "notebooks-marimo/GAM-Patient-ERV-CARBA.csv"
    GLIMS_pat = "notebooks-marimo/GLIMS-Patient-ERV-CARBA.csv"
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
def _(df_gam_clean, df_glims_clean):
    from transform.fusion_gam_glims import fusionner

    df_traquer = fusionner(df_gam_clean, df_glims_clean)
    df_traquer
    return


if __name__ == "__main__":
    app.run()
