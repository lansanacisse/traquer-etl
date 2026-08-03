# Copyright (c) 2026
# Tous droits réservés CHU Brest.


"""
transform/pivot.py

Construction du modèle pivot à partir d'un DataFrame déjà aux noms de
colonnes STANDARDS (voir fiche_nommage_standard_colonnes.md).

Module générique : il ne connaît ni GLIMS, ni le GAM, ni aucun système
source. Tout établissement dont l'extraction — ou sa propre couche de
traduction, comme transform/normalisation.py pour le CHU de Brest — produit
un DataFrame avec ces noms standards peut appeler construire_pivot()
directement, sans réécrire quoi que ce soit ici.

    from transform.pivot import construire_pivot

    pivot = construire_pivot(df_standard)
    pivot["patients"], pivot["sejours"], pivot["mouvements"],
    pivot["unites"], pivot["dossiers"], pivot["prelevements"]

Chaque table a un grain net (une ligne = une entité). Le mapping FHIR reçoit
ainsi des lignes propres et n'a plus rien à déduire.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl

FUSEAU = "Europe/Paris"
ANNEE_SENTINELLE = 4712


def _texte(df: pl.DataFrame, nom: str) -> pl.Expr:
    """Colonne en texte, valeur vide -> null. Null si la colonne est absente."""
    if nom not in df.columns:
        return pl.lit(None, dtype=pl.Utf8).alias(nom)
    col = pl.col(nom).cast(pl.Utf8).str.strip_chars()
    return pl.when(col == "").then(None).otherwise(col).alias(nom)


def _datetime_vide(nom: str) -> pl.Expr:
    """Colonne vide, mais correctement typee (Datetime tz-aware)."""
    return pl.lit(None, dtype=pl.Datetime(time_unit="us", time_zone=FUSEAU)).alias(nom)


def _horodatage(df: pl.DataFrame, nom: str) -> pl.Expr:
    """
    Colonne de date -> Datetime tz-aware Europe/Paris, sentinelle -> null.

    Accepte du texte, un type Datetime deja present, ou une colonne absente.
    Le fuseau est indispensable : FHIR exige un decalage horaire des qu'un
    dateTime porte une heure.
    """
    if nom not in df.columns:
        return _datetime_vide(nom)

    dtype = df.schema[nom]
    if dtype == pl.Null:
        return _datetime_vide(nom)

    col = pl.col(nom)
    if dtype == pl.Utf8:
        col = col.str.to_datetime(strict=False)
    elif dtype == pl.Date:
        col = col.cast(pl.Datetime("us"))

    deja_tz = isinstance(dtype, pl.Datetime) and dtype.time_zone is not None
    col = (
        col.dt.convert_time_zone(FUSEAU)
        if deja_tz
        else col.dt.replace_time_zone(FUSEAU)
    )
    return (
        pl.when(col.dt.year() >= ANNEE_SENTINELLE).then(None).otherwise(col).alias(nom)
    )


def _julien_vers_datetime(valeur):
    """Date julienne (float) -> datetime Europe/Paris. Passe les datetime deja types."""
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur if valeur.tzinfo else valeur.replace(tzinfo=ZoneInfo(FUSEAU))
    try:
        valeur = float(valeur) - 1.5
    except (TypeError, ValueError):
        return None
    secondes = (valeur - 2440587.5) * 86400
    return datetime.fromtimestamp(secondes, tz=ZoneInfo(FUSEAU))


def _horodatage_julien(df: pl.DataFrame, nom: str) -> pl.Expr:
    """Colonne pouvant arriver en date julienne -> Datetime tz-aware."""
    if nom not in df.columns or df.schema[nom] == pl.Null:
        return _datetime_vide(nom)
    return (
        pl.col(nom)
        .map_elements(
            _julien_vers_datetime,
            return_dtype=pl.Datetime(time_unit="us", time_zone=FUSEAU),
        )
        .alias(nom)
    )


def _premier_non_nul(colonne: str) -> pl.Expr:
    """
    Premiere valeur non nulle d'un groupe.

    Indispensable : une meme entite peut apparaitre sur plusieurs lignes,
    certaines avec des champs vides. Un `first()` naif produirait par
    exemple un patient sans nom.
    """
    return pl.col(colonne).drop_nulls().first().alias(colonne)


def table_patients(df: pl.DataFrame) -> pl.DataFrame:
    """Une ligne par ipp. Identite complete (premiere valeur non nulle)."""
    prepare = df.select(
        _texte(df, "ipp"),
        _texte(df, "nom"),
        _texte(df, "prenom"),
        _horodatage(df, "date_naissance"),
        _texte(df, "sexe"),
        _horodatage(df, "date_deces"),
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
    """Une ligne par iep."""
    prepare = df.select(
        _texte(df, "iep"),
        _texte(df, "ipp"),
        _horodatage(df, "date_debut_sejour"),
        _horodatage(df, "date_fin_sejour"),
        _texte(df, "statut_sejour"),
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
    """Une ligne par id_mouvement."""
    prepare = df.select(
        _texte(df, "id_mouvement"),
        _texte(df, "iep"),
        _texte(df, "code_unite"),
        _texte(df, "nom_unite"),
        _texte(df, "batiment"),
        _texte(df, "etage"),
        _texte(df, "chambre"),
        _texte(df, "lit"),
        _horodatage(df, "date_debut_mouvement"),
        _horodatage(df, "date_fin_mouvement"),
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


def table_unites(mouvements: pl.DataFrame) -> pl.DataFrame:
    """Une ligne par unite de soins, deduite des mouvements."""
    return (
        mouvements.filter(pl.col("code_unite").is_not_null())
        .group_by("code_unite", maintain_order=True)
        .agg(_premier_non_nul("nom_unite"))
    )


def table_dossiers(df: pl.DataFrame) -> pl.DataFrame:
    """Une ligne par id_dossier : le pivot du monde laboratoire."""
    prepare = df.select(
        _texte(df, "id_dossier"),
        _texte(df, "ipp"),
        _texte(df, "iep"),
        _texte(df, "libelle_examen"),
        _texte(df, "service_demandeur"),
        _texte(df, "statut_suivi"),
        _texte(df, "resultat_bhre"),
        _texte(df, "germe"),
        _horodatage(df, "date_prescription"),
        _horodatage_julien(df, "date_validation"),
    )
    return (
        prepare.filter(pl.col("id_dossier").is_not_null())
        .group_by("id_dossier", maintain_order=True)
        .agg(
            _premier_non_nul("ipp"),
            _premier_non_nul("iep"),
            _premier_non_nul("libelle_examen"),
            _premier_non_nul("service_demandeur"),
            _premier_non_nul("statut_suivi"),
            _premier_non_nul("resultat_bhre"),
            _premier_non_nul("germe"),
            _premier_non_nul("date_prescription"),
            _premier_non_nul("date_validation"),
        )
    )


def table_prelevements(df: pl.DataFrame) -> pl.DataFrame:
    """Une ligne par id_prelevement, rattachee a son dossier."""
    prepare = df.select(
        _texte(df, "id_prelevement"),
        _texte(df, "id_dossier"),
        _texte(df, "ipp"),
        _horodatage(df, "date_prelevement"),
        _horodatage(df, "date_reception"),
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


def construire_pivot(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """
    DataFrame standardise -> modele pivot (dict de 6 DataFrames).

    Point d'entree pour tout etablissement dont les donnees respectent la
    fiche de nommage standard (fiche_nommage_standard_colonnes.md).
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
