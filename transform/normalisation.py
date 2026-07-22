# Copyright (c) 2026
# Tous droits réservés CHU Brest.

from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl

FUSEAU = ZoneInfo("Europe/Paris")
ANNEE_SENTINELLE = 4000


def _colonne(df: pl.DataFrame, nom: str) -> pl.Expr:
    """Colonne si presente, sinon colonne de nulls (evite un KeyError)."""
    if nom in df.columns:
        return pl.col(nom)
    return pl.lit(None).alias(nom)


def _texte(df: pl.DataFrame, nom: str) -> pl.Expr:
    """Colonne castee en texte, vide -> null."""
    col = _colonne(df, nom).cast(pl.Utf8).str.strip_chars()
    return pl.when(col == "").then(None).otherwise(col)


def _datetime_vide() -> pl.Expr:
    """Colonne vide correctement typee (Datetime tz-aware)."""
    return pl.lit(None, dtype=pl.Datetime(time_unit="us", time_zone="Europe/Paris"))


def _horodatage(df: pl.DataFrame, nom: str) -> pl.Expr:
    """
    Colonne de date -> Datetime tz-aware Europe/Paris, sentinelle -> null.

    Accepte du texte ("2026-01-05 08:00:00.000") comme du Datetime deja type.
    Le fuseau est indispensable : FHIR exige un decalage horaire des qu'un
    dateTime porte une heure.
    """
    if nom not in df.columns:
        return _datetime_vide().alias(nom)

    dtype = df.schema[nom]

    if dtype == pl.Null:
        return _datetime_vide().alias(nom)

    col = pl.col(nom)
    if dtype == pl.Utf8:
        col = col.str.to_datetime(strict=False)
    elif dtype == pl.Date:
        col = col.cast(pl.Datetime("us"))

    deja_tz = isinstance(dtype, pl.Datetime) and dtype.time_zone is not None
    col = (
        col.dt.convert_time_zone("Europe/Paris")
        if deja_tz
        else col.dt.replace_time_zone("Europe/Paris")
    )

    return pl.when(col.dt.year() >= ANNEE_SENTINELLE).then(None).otherwise(col)


def _julien_vers_datetime(valeur):
    """Date julienne GLIMS (float) -> datetime Europe/Paris."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur if valeur.tzinfo else valeur.replace(tzinfo=FUSEAU)
    try:
        valeur = float(valeur) - 1.5
    except (TypeError, ValueError):
        return None
    secondes = (valeur - 2440587.5) * 86400
    return datetime.fromtimestamp(secondes, tz=FUSEAU)


def _horodatage_julien(df: pl.DataFrame, nom: str) -> pl.Expr:
    """Colonne julienne -> Datetime tz-aware."""
    if nom not in df.columns or df.schema[nom] == pl.Null:
        return _datetime_vide().alias(nom)
    return (
        pl.col(nom)
        .map_elements(
            _julien_vers_datetime,
            return_dtype=pl.Datetime(time_unit="us", time_zone="Europe/Paris"),
        )
        .alias(nom)
    )


def _premier_non_nul(colonne: str) -> pl.Expr:
    """
    Premiere valeur non nulle d'un groupe.

    Indispensable : dans la table fusionnee, l'identite du patient est nulle
    sur les lignes de mouvement sans analyse. Un `first()` naif produirait
    un Patient sans nom ni date de naissance.
    """
    return pl.col(colonne).drop_nulls().first().alias(colonne)


def table_patients(df: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par IPP. Identite complete (premiere valeur non nulle).

    PRSN_SEX arrive deja en code FHIR (traduit dans glims_biologie.py,
    fonction expr_sexe) : on la reprend telle quelle, sans retraduire.
    """
    prepare = df.select(
        _colonne(df, "IPP").alias("ipp"),
        _texte(df, "PRSN_LASTNAME").alias("nom"),
        _texte(df, "PRSN_FIRSTNAME").alias("prenom"),
        _horodatage(df, "PRSN_BIRTHDATE").alias("date_naissance"),
        _texte(df, "PRSN_SEX").alias("sexe"),
        _horodatage(df, "PRSN_DECEASETIME").alias("date_deces"),
    )
    return (
        prepare.filter(pl.col("ipp").is_not_null())
        .group_by("ipp", maintain_order=True)
        .agg(
            _premier_non_nul("nom"),
            _premier_non_nul("prenom"),
            _premier_non_nul("date_naissance"),
            _premier_non_nul("sexe"),
            _premier_non_nul("date_deces"),
        )
    )


def table_sejours(df: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par IEP.

    STATUT_SEJOUR arrive deja en code FHIR (traduit dans gam_mouvements.py,
    fonction statut_sejour) : on la reprend telle quelle, sans retraduire.
    """
    prepare = df.select(
        _colonne(df, "IEP").alias("iep"),
        _colonne(df, "IPP").alias("ipp"),
        _horodatage(df, "DATE_ENTREE_SEJOUR").alias("date_debut_sejour"),
        _horodatage(df, "DATE_SORTIE_SEJOUR").alias("date_fin_sejour"),
        _texte(df, "STATUT_SEJOUR").alias("statut_sejour"),
    )
    return (
        prepare.filter(pl.col("iep").is_not_null())
        .group_by("iep", maintain_order=True)
        .agg(
            _premier_non_nul("ipp"),
            _premier_non_nul("date_debut_sejour"),
            _premier_non_nul("date_fin_sejour"),
            _premier_non_nul("statut_sejour"),
        )
    )


def table_mouvements(df: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par ID_MOUVEMENT.

    Le code d'unite est UFO_ID (UF du mouvement). Repli sur UF_ENTREE tant
    que la requete GAM ne remonte pas UFO_ID : approximation connue, toutes
    les Location d'un sejour pointeraient alors vers l'UF d'entree.
    """
    code_unite = "UFO_ID" if "UFO_ID" in df.columns else "UF_ENTREE"

    prepare = df.select(
        _colonne(df, "ID_MOUVEMENT").alias("id_mouvement"),
        _colonne(df, "IEP").alias("iep"),
        _texte(df, code_unite).alias("code_unite"),
        _texte(df, "LIBELLE_SERVICE").alias("nom_unite"),
        _texte(df, "LIE_BAT_NUM").alias("batiment"),
        _texte(df, "ETG_NUM").alias("etage"),
        _texte(df, "LIE_NUM").alias("chambre"),
        _texte(df, "LIT_NUM").alias("lit"),
        _horodatage(df, "DATE_DEBUT_MOUVEMENT").alias("date_debut_mouvement"),
        _horodatage(df, "DATE_FIN_MOUVEMENT").alias("date_fin_mouvement"),
    )
    return (
        prepare.filter(pl.col("id_mouvement").is_not_null())
        .group_by("id_mouvement", maintain_order=True)
        .agg(
            _premier_non_nul("iep"),
            _premier_non_nul("code_unite"),
            _premier_non_nul("nom_unite"),
            _premier_non_nul("batiment"),
            _premier_non_nul("etage"),
            _premier_non_nul("chambre"),
            _premier_non_nul("lit"),
            _premier_non_nul("date_debut_mouvement"),
            _premier_non_nul("date_fin_mouvement"),
        )
        .sort("date_debut_mouvement", nulls_last=True)
    )


def table_dossiers(df: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par ORD_INTERNALID : le pivot du monde GLIMS.

    Porte le libelle d'examen (ML18), le service demandeur (requester),
    le resultat BHRe et le statut de suivi.

    STATUT_RESULTAT arrive deja defini (glims_biologie.py, fonction
    expr_statut_resultat) : on le reprend tel quel, sans retraduire.
    """
    prepare = df.select(
        _texte(df, "ORD_INTERNALID").alias("id_dossier"),
        _colonne(df, "IPP").alias("ipp"),
        _colonne(df, "IEP").alias("iep"),
        _texte(df, "ML18_TRANSLATION").alias("libelle_examen"),
        _texte(df, "NOM_SERVICE_DEMANDEUR").alias("service_demandeur"),
        _texte(df, "MORG_NAME").alias("germe"),
        _texte(df, "STATUT_SURVEILLANCE").alias("resultat_bhre"),
        _texte(df, "STATUT_RESULTAT").alias("statut_suivi"),
        # Vide tant que la requete GLIMS ne remonte pas ORD_PRESCRIPTIONTIME :
        # le champ circule quand meme, prêt a etre alimente sans autre change.
        _horodatage(df, "DATE_PRESCRIPTION").alias("date_prescription"),
        _horodatage_julien(df, "DATE_VALIDATION_PCR").alias("date_validation"),
    )
    return (
        prepare.filter(pl.col("id_dossier").is_not_null())
        .group_by("id_dossier", maintain_order=True)
        .agg(
            _premier_non_nul("ipp"),
            _premier_non_nul("iep"),
            _premier_non_nul("libelle_examen"),
            _premier_non_nul("service_demandeur"),
            _premier_non_nul("germe"),
            _premier_non_nul("resultat_bhre"),
            _premier_non_nul("statut_suivi"),
            _premier_non_nul("date_prescription"),
            _premier_non_nul("date_validation"),
        )
    )


def table_prelevements(df: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par SPMN_INTERNALID, rattachee a son dossier.

    L'ipp est repris ici car le Specimen FHIR reference directement le
    Patient (champ `subject`), sans passer par le dossier.
    """
    prepare = df.select(
        _texte(df, "SPMN_INTERNALID").alias("id_prelevement"),
        _texte(df, "ORD_INTERNALID").alias("id_dossier"),
        _colonne(df, "IPP").alias("ipp"),
        _horodatage(df, "SPMN_SAMPLINGTIME").alias("date_prelevement"),
        _horodatage(df, "SPMN_RECEIPTTIME").alias("date_reception"),
    )
    return (
        prepare.filter(pl.col("id_prelevement").is_not_null())
        .group_by("id_prelevement", maintain_order=True)
        .agg(
            _premier_non_nul("id_dossier"),
            _premier_non_nul("ipp"),
            _premier_non_nul("date_prelevement"),
            _premier_non_nul("date_reception"),
        )
    )


def table_unites(mouvements: pl.DataFrame) -> pl.DataFrame:
    """
    Une ligne par unite de soins, deduite de la table des mouvements.

    Alimente les ressources Location du bundle. Sans elle, les Encounter
    referenceraient des Location absentes du bundle (references orphelines).
    """
    return (
        mouvements.filter(pl.col("code_unite").is_not_null())
        .group_by("code_unite", maintain_order=True)
        .agg(_premier_non_nul("nom_unite"))
    )


def normaliser(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """
    Table fusionnee -> modele pivot (dictionnaire de DataFrames).

    Retourne les cles : patients, sejours, mouvements, unites, dossiers,
    prelevements.
    """
    mouvements = table_mouvements(df)
    return {
        "patients": table_patients(df),
        "sejours": table_sejours(df),
        "mouvements": mouvements,
        "unites": table_unites(mouvements),
        "dossiers": table_dossiers(df),
        "prelevements": table_prelevements(df),
    }
