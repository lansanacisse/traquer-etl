from datetime import datetime
from zoneinfo import ZoneInfo
import polars as pl

MAPPING_COLONNES = {
    "sysdate": "date_extraction",
    "idnt_code": "ipp",
    "prsn_internalid": "ins_patient",
    "prsn_lastname": "nom",
    "prsn_firstname": "prenom",
    "prsn_birthdate": "date_naissance",
    "prsn_sex": "sexe",
    "prsn_deceasetime": "date_deces",
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
    "rslt_status": "statut_resultat",
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
    "abrs_status": "statut_antibiogramme",
}


COLONNES_DATES_JULIEN = [
    "date_deces",
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


def julian_to_datetime(value):
    if value is None:
        return None

    value = float(value) - 1.5
    unix_epoch = 2440587.5
    seconds = (value - unix_epoch) * 86400

    return datetime.fromtimestamp(seconds, tz=ZoneInfo("Europe/Paris"))


def clean_data(df: pl.DataFrame) -> pl.DataFrame:
    """
    Nettoie les données ORAGLIMS :
    - noms de colonnes en minuscules
    - renommage métier
    - conversion des dates juliennes
    - traduction sexe et metier
    - traduction statut resultat et de la demande
    """

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

    df = df.with_columns(
        [
            # Sexe
            pl.when(pl.col("sexe") == 1)
            .then(pl.lit("M"))
            .when(pl.col("sexe") == 2)
            .then(pl.lit("F"))
            .otherwise(pl.lit("Autres"))
            .alias("sexe"),
            # Sensibilité
            pl.when(pl.col("code_sensibilite") == 1)
            .then(pl.lit("Sensible"))
            .when(pl.col("code_sensibilite") == 2)
            .then(pl.lit("Intermédiaire"))
            .when(pl.col("code_sensibilite") == 3)
            .then(pl.lit("Résistant"))
            .otherwise(None)
            .alias("sensibilite"),
            # RSLT_STATUS
            pl.when(pl.col("statut_resultat") == 1)
            .then(pl.lit("Prévu"))
            .when(pl.col("statut_resultat") == 2)
            .then(pl.lit("Initial"))
            .when(pl.col("statut_resultat") == 3)
            .then(pl.lit("Partiel"))
            .when(pl.col("statut_resultat") == 4)
            .then(pl.lit("Complet"))
            .when(pl.col("statut_resultat") == 5)
            .then(pl.lit("Fermé"))
            .when(pl.col("statut_resultat") == 6)
            .then(pl.lit("Discontinué"))
            .otherwise(pl.lit("Inconnu"))
            .alias("statut_resultat"),
            # ORD_STATUS
            pl.when(pl.col("statut_demande") == 1)
            .then(pl.lit("Prévu"))
            .when(pl.col("statut_demande") == 2)
            .then(pl.lit("Initial"))
            .when(pl.col("statut_demande") == 3)
            .then(pl.lit("Partiel"))
            .when(pl.col("statut_demande") == 4)
            .then(pl.lit("Complet"))
            .otherwise(pl.lit("Inconnu"))
            .alias("statut_demande"),
        ]
    )
    return df
