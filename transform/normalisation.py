# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""
Traduction du vocabulaire GLIMS / GAM (CHU de Brest) vers le format
STANDARD attendu par transform/pivot.py.

Ce fichier est SPÉCIFIQUE A BREST. Il ne fait qu'un renommage de colonnes :
aucun parsing de date, aucune agrégation, aucun découpage en entités.
C'est transform/pivot.py, générique, qui s'en charge ensuite à partir du
DataFrame standardisé produit ici.

C'est le seul fichier qu'un autre établissement aurait à réécrire pour
adopter le connecteur : il produit son propre `standardiser()` équivalent,
propre à ses systèmes sources, puis appelle directement
`transform.pivot.construire_pivot()`, sans rien modifier d'autre.

    from transform.normalisation import normaliser

    pivot = normaliser(df_fusion)   # traduction + construction du pivot,
                                     # pour l'usage interne au CHU de Brest
"""

import polars as pl

from transform.pivot import construire_pivot


def _colonne(df: pl.DataFrame, nom: str, repli: str | None = None) -> pl.Expr:
    """
    Renvoie l'expression de la colonne source si presente, sinon celle du
    repli, sinon une colonne de null.

    Sert aux colonnes pas encore remontees par les requetes actuelles
    (ex. UFO_ID) : le code fonctionne avant et apres leur ajout.
    """
    if nom in df.columns:
        return pl.col(nom)
    if repli and repli in df.columns:
        return pl.col(repli)
    return pl.lit(None)


def standardiser(df: pl.DataFrame) -> pl.DataFrame:
    """
    Traduit la table fusionnee GLIMS/GAM vers les noms de colonnes standards.

    Renommage pur, aucun traitement de date ni de valeur ici : ce travail
    generique est fait par transform.pivot.construire_pivot().

    UFO_ID est le code d'unite attendu (celui du mouvement). UF_ENTREE sert
    de repli tant que la requete GAM ne le remonte pas encore : approximation
    connue, l'UF du sejour est alors utilisee a la place de l'UF du mouvement.
    """
    return df.select(
        _colonne(df, "IPP").alias("ipp"),
        _colonne(df, "IEP").alias("iep"),
        _colonne(df, "ID_MOUVEMENT").alias("id_mouvement"),
        _colonne(df, "UFO_ID", repli="UF_ENTREE").alias("code_unite"),
        _colonne(df, "LIBELLE_SERVICE").alias("nom_unite"),
        _colonne(df, "LIE_BAT_NUM").alias("batiment"),
        _colonne(df, "ETG_NUM").alias("etage"),
        _colonne(df, "LIE_NUM").alias("chambre"),
        _colonne(df, "LIT_NUM").alias("lit"),
        _colonne(df, "DATE_DEBUT_MOUVEMENT").alias("date_debut_mouvement"),
        _colonne(df, "DATE_FIN_MOUVEMENT").alias("date_fin_mouvement"),
        _colonne(df, "DATE_ENTREE_SEJOUR").alias("date_debut_sejour"),
        _colonne(df, "DATE_SORTIE_SEJOUR").alias("date_fin_sejour"),
        _colonne(df, "STATUT_SEJOUR").alias("statut_sejour"),
        _colonne(df, "PRSN_LASTNAME").alias("nom"),
        _colonne(df, "PRSN_FIRSTNAME").alias("prenom"),
        _colonne(df, "PRSN_BIRTHDATE").alias("date_naissance"),
        _colonne(df, "PRSN_SEX").alias("sexe"),
        _colonne(df, "PRSN_DECEASETIME").alias("date_deces"),
        _colonne(df, "ORD_INTERNALID").alias("id_dossier"),
        _colonne(df, "ML18_TRANSLATION").alias("libelle_examen"),
        _colonne(df, "NOM_SERVICE_DEMANDEUR").alias("service_demandeur"),
        _colonne(df, "STATUT_RESULTAT").alias("statut_suivi"),
        _colonne(df, "STATUT_SURVEILLANCE").alias("resultat_bhre"),
        _colonne(df, "MORG_NAME").alias("germe"),
        _colonne(df, "DATE_PRESCRIPTION").alias("date_prescription"),
        _colonne(df, "DATE_VALIDATION_PCR").alias("date_validation"),
        _colonne(df, "SPMN_INTERNALID").alias("id_prelevement"),
        _colonne(df, "SPMN_SAMPLINGTIME").alias("date_prelevement"),
        _colonne(df, "SPMN_RECEIPTTIME").alias("date_reception"),
    )


def normaliser(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """
    Pipeline complet propre a Brest : traduction puis construction du pivot.

    Conserve pour ne pas changer l'usage existant (main.py). Un etablissement
    tiers n'appelle pas cette fonction : il ecrit son propre `standardiser()`
    puis appelle directement `transform.pivot.construire_pivot()`.
    """
    return construire_pivot(standardiser(df))
