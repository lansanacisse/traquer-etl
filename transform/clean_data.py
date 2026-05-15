from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl

MAPPING_COLONNES = {
    "sysdate": "date_extraction",
    "idnt_code": "ipp",
    "prsn_internalid": "ins_patient",
    "prsn_title": "titre",
    "prsn_lastname": "nom",
    "prsn_firstname": "prenom",
    "prsn_birthdate": "date_naissance",
    "prsn_sex": "sexe",
    "prsn_deceasetime": "date_deces",
    "enct_externalid": "iep",
    "enct_type": "type_sejour",
    "enct_starttime": "date_debut_sejour",
    "enct_endtime": "date_fin_sejour",
    "ord_internalid": "id_source_interne",
    "ord_externalid": "id_source_externe",
    "ord_description": "description_demande",
    "ord_prescriptiontime": "date_prescription",
    "ord_lowestobjecttime": "date_prelevement",
    "ord_receipttime": "date_reception",
    "ord_completiontime": "date_validation",
    "rslt_status": "statut_resultat",
    "crsp_internalid": "code_service_demandeur",
    "crsp_name": "nom_service_demandeur",
    "spmn_internalid": "id_prelevement_interne",
    "ml18_translation": "type_prelevement",
    "spmn_receipttime": "date_reception_prelevement",
    "isol_id": "id_isolation",
    "isol_validationtime": "date_validation_isolation",
    "morg_name": "nom_microorganisme",
    "ab_name": "nom_antibiotique",
    "ab_mnemonic": "sigle_antibiotique",
    "abrs_risreportvalue": "sensibilite_antibiotique",
    "abrs_micrawvalue": "cmi_antibiotique",
    "stay_id": "id_mouvement",
    "stay_starttime": "date_debut_mouvement",
    "stay_endtime": "date_fin_mouvement",
    "stay_externalid": "id_mouvement_externe",
    "ward_id": "id_unite_patient",
    "ward_mnemonic": "code_unite_patient",
    "ward_name": "nom_unite_patient",
    "ward_isicu": "unite_soins_critiques",
}


COLONNES_DATES_JULIEN = [
    "date_deces",
    "date_debut_sejour",
    "date_fin_sejour",
    "date_prescription",
    "date_prelevement",
    "date_reception",
    "date_validation",
    "date_reception_prelevement",
    "date_validation_isolation",
    "date_debut_mouvement",
    "date_fin_mouvement",
]


def julian_to_datetime(value):
    if value is None:
        return None

    value = float(value) - 1.5
    unix_epoch = 2440587.5
    seconds = (value - unix_epoch) * 86400

    return datetime.fromtimestamp(seconds, tz=ZoneInfo("Europe/Paris"))


def clean_data(df: pl.DataFrame) -> pl.DataFrame:
    df = df.rename({c: c.lower() for c in df.columns})

    df = df.rename(
        {old: new for old, new in MAPPING_COLONNES.items() if old in df.columns}
    )

    colonnes_dates_existantes = [
        col for col in COLONNES_DATES_JULIEN if col in df.columns
    ]

    if colonnes_dates_existantes:
        df = df.with_columns(
            pl.col(colonnes_dates_existantes).map_elements(
                julian_to_datetime,
                return_dtype=pl.Datetime(time_zone="Europe/Paris"),
            )
        )

    expressions = []

    if "sexe" in df.columns:
        expressions.append(
            pl.when(pl.col("sexe") == 1)
            .then(pl.lit("M"))
            .when(pl.col("sexe") == 2)
            .then(pl.lit("F"))
            .otherwise(pl.lit("Autres"))
            .alias("sexe")
        )

    if "sensibilite_antibiotique" in df.columns:
        expressions.append(
            pl.when(pl.col("sensibilite_antibiotique") == 1)
            .then(pl.lit("Sensible"))
            .when(pl.col("sensibilite_antibiotique") == 2)
            .then(pl.lit("Intermédiaire"))
            .when(pl.col("sensibilite_antibiotique") == 3)
            .then(pl.lit("Résistant"))
            .otherwise(pl.lit("Inconnu"))
            .alias("sensibilite_antibiotique")
        )

    if "statut_resultat" in df.columns:
        expressions.extend(
            [
                pl.when(pl.col("statut_resultat") == 1)
                .then(pl.lit("requested"))
                .when(pl.col("statut_resultat").is_in([2, 3]))
                .then(pl.lit("in-progress"))
                .when(pl.col("statut_resultat").is_in([4, 5, 6]))
                .then(pl.lit("completed"))
                .otherwise(pl.lit("requested"))
                .alias("statut_task"),
                pl.when(pl.col("statut_resultat").is_in([4, 5, 6]))
                .then(pl.lit("completed"))
                .otherwise(pl.lit("active"))
                .alias("statut_service_request"),
                pl.when(pl.col("statut_resultat").is_in([4, 5, 6]))
                .then(pl.lit("final"))
                .otherwise(pl.lit("registered"))
                .alias("statut_observation"),
            ]
        )

    if "date_fin_sejour" in df.columns:
        expressions.append(
            pl.when(pl.col("date_fin_sejour").is_not_null())
            .then(pl.lit("completed"))
            .otherwise(pl.lit("in-progress"))
            .alias("statut_encounter")
        )

    if expressions:
        df = df.with_columns(expressions)

    return df
