import marimo

__generated_with = "0.23.5"
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
    import pandas as pd
    from zoneinfo import ZoneInfo
    from datetime import datetime, timedelta
    from extract.oracle_extract import extract_oraglims_data

    return ZoneInfo, datetime, extract_oraglims_data, pl


@app.cell
def _(extract_oraglims_data):
    # data exctration
    df_raw = extract_oraglims_data()
    df_raw.head()
    return (df_raw,)


@app.cell
def _(df_raw):
    # lower columns and columns raname
    df0 = df_raw.rename({c: c.lower() for c in df_raw.columns})

    df1 = df0.rename({
        "sysdate": "date_extraction",

        "idnt_code": "ipp",
        "prsn_internalid": "ins_patient",
        "prsn_lastname": "nom",
        "prsn_firstname": "prenom",
        "prsn_birthdate": "date_naissance",
        "prsn_sex": "sexe",

        "enct_externalid": "iep",
        "enct_person": "id_patient_sejour",
        "enct_institution": "id_etablissement",
        "enct_type": "type_sejour",
        "enct_starttime": "date_debut_sejour",
        "enct_endtime": "date_fin_sejour",

        "ord_id": "id_demande",
        "ord_internalid": "id_source",
        "ord_shortid": "id_demande_court",
        "ord_description": "description",
        "ord_status": "statut_demande",
        "ord_lowestobjecttime": "date_prelevement",
        "ord_prescriptiontime": "date_prescription",
        "ord_receipttime": "date_reception",
        "ord_completiontime": "date_validation",

        "crsp_internalid": "code_uf",
        "crsp_name": "nom_uf",
        "dept_name": "departement",

        "spmn_id": "id_prelevement",
        "spmn_internalid": "id_prelevement_interne",
        "mat_shortname": "type_prelevement",
        "ml18_translation": "libelle_prelevement",
        "spmn_receipttime": "date_reception_prelevement",
        "spmn_status": "statut_prelevement",

        "isol_id": "id_isolation",
        "isol_status": "statut_isolation",
        "isol_availabilitytime": "date_disponibilite_isolation",
        "isol_validationtime": "date_validation_isolation",
        "isol_confirmationtime": "date_confirmation_isolation",

        "morg_id": "id_microorganisme",
        "morg_name": "microorganisme",

        "ab_id": "id_antibiotique",
        "ab_mnemonic": "code_antibiotique",
        "ab_name": "antibiotique",

        "abrs_id": "id_resultat_atb",
        "abrs_risreportvalue": "code_sensibilite",
        "abrs_micrawvalue": "cmi",
        "abrs_availabilitytime": "date_disponibilite_atb",
        "abrs_panel": "id_panel",
        "abp_name": "nom_panel",
        "abrs_status": "statut_resultat",
    })
    return (df1,)


@app.cell
def _(ZoneInfo, datetime, df1, pl):
    # date conversion
    def julian_to_datetime(value):
        if value is None:
            return None
        value = float(value) - 1.5
        unix_epoch = 2440587.5
        seconds = (value - unix_epoch) * 86400
        return datetime.fromtimestamp(seconds, tz=ZoneInfo("Europe/Paris"))

    colonnes_dates = [
        "date_debut_sejour",
        "date_fin_sejour",
        "date_prelevement",
        "date_prescription",
        "date_reception",
        "date_validation",
        "date_reception_prelevement",
        "date_disponibilite_isolation",
        "date_validation_isolation",
        "date_confirmation_isolation",
        "date_disponibilite_atb",
    ]

    df2 = df1.with_columns(
        pl.col([c for c in colonnes_dates if c in df1.columns])
        .map_elements(julian_to_datetime, return_dtype=pl.Datetime(time_zone="Europe/Paris"))
    )
    return (df2,)


@app.cell
def _(df2, pl):
    df3 = df2.with_columns([
        pl.when(pl.col("sexe") == 1).then(pl.lit("M"))
        .when(pl.col("sexe") == 2).then(pl.lit("F"))
        .otherwise(pl.lit("Autres"))
        .alias("sexe"),

        pl.when(pl.col("code_sensibilite") == 1).then(pl.lit("Sensible"))
        .when(pl.col("code_sensibilite") == 2).then(pl.lit("Intermédiaire"))
        .when(pl.col("code_sensibilite") == 3).then(pl.lit("Résistant"))
        .otherwise(None)
        .alias("Sensibilite"),
    ])
    return (df3,)


@app.cell
def _(df3):
    df3
    return


if __name__ == "__main__":
    app.run()
