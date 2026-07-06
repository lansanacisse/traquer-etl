"""
Biologie GLIMS : classification BHRe (EPC / ERV) a partir d'un export GLIMS.

Module importable dans un pipeline :

    from biologie_glims import biologie_glims, depuis_csv, classifier, consolider

    # depuis un DataFrame Polars deja charge :
    df_bhre = biologie_glims(df)

    # depuis un fichier CSV GLIMS :
    df_bhre = depuis_csv("GLIMS-Patient-CULT-PCR.csv")

Le pipeline produit une ligne par ORD_INTERNALID, etiquetee
EPC / ERV / EPC+ERV / NEGATIF / RESULTAT_NON_DISPONIBLE.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl


def norm(col):
    """Normalise une colonne texte : trim + minuscule, null -> ''."""
    return pl.col(col).cast(pl.Utf8).fill_null("").str.strip_chars().str.to_lowercase()


def julian_to_datetime(value):
    """Convertit une date julienne GLIMS en datetime Europe/Paris."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=ZoneInfo("Europe/Paris"))
        return value
    value = float(value) - 1.5
    unix_epoch = 2440587.5
    seconds = (value - unix_epoch) * 86400
    return datetime.fromtimestamp(seconds, tz=ZoneInfo("Europe/Paris"))


def expr_sexe():
    """Transforme PRSN_SEX numerique en libelle : 1 -> M, 2 -> F, sinon Autres."""
    sexe = pl.col("PRSN_SEX").cast(pl.Utf8).fill_null("").str.strip_chars()
    return (
        pl.when(sexe == "1")
        .then(pl.lit("M"))
        .when(sexe == "2")
        .then(pl.lit("F"))
        .otherwise(pl.lit("Autres"))
        .alias("PRSN_SEX")
    )


def lire_csv(chemin):
    """Lit le CSV GLIMS brut (SPMN_INTERNALID force en texte)."""
    return pl.read_csv(
        chemin, separator=",", schema_overrides={"SPMN_INTERNALID": pl.Utf8}
    )


def nettoyer(df_raw):
    """Applique les types et convertit les dates juliennes."""
    schema_types = {
        "IDNT_CODE": pl.Utf8,
        "PRSN_ID": pl.Int64,
        "PRSN_INTERNALID": pl.Utf8,
        "PRSN_LASTNAME": pl.Utf8,
        "PRSN_FIRSTNAME": pl.Utf8,
        "PRSN_SEX": pl.Utf8,
        "ORD_INTERNALID": pl.Utf8,
        "SPMN_INTERNALID": pl.Utf8,
        "ML18_TRANSLATION": pl.Utf8,
        "ML86_TRANSLATION": pl.Utf8,
        "ML07_TRANSLATION": pl.Utf8,
        "MORG_NAME": pl.Utf8,
        "AB_MNEMONIC": pl.Utf8,
        "AB_NAME": pl.Utf8,
        "ABRS_RISREPORTVALUE": pl.Utf8,
        "ABRS_STATUS": pl.Int64,
        "RSLT_STATUS": pl.Int64,
    }
    types_presents = {c: t for c, t in schema_types.items() if c in df_raw.columns}

    df = df_raw.with_columns([pl.col(c).cast(t) for c, t in types_presents.items()])

    conversions = []
    for col in ("SPMN_SAMPLINGTIME", "SPMN_RECEIPTTIME"):
        if col in df.columns:
            conversions.append(
                pl.col(col)
                .map_elements(julian_to_datetime, return_dtype=pl.Datetime)
                .alias(col)
            )
    if conversions:
        df = df.with_columns(conversions)

    if "PRSN_SEX" in df.columns:
        df = df.with_columns(expr_sexe())
    return df


def expr_isot_positif():
    """ISOT_VALUE positif. Ne se lit jamais seul (cf. couplage carba)."""
    isot = (
        pl.col("ISOT_VALUE")
        .cast(pl.Utf8)
        .fill_null("")
        .str.strip_chars()
        .str.to_lowercase()
    )
    return isot.is_in(["positive", "positif", "oui", "ok", "pos", "bb_posv"])


def expr_ml07_positif():
    """
    ML07 positif : deux familles de libelles.
      - "positi" (Positif / Positive ...)
      - "presence" (Presence d'une Carbapenemase de type NDM ...)
      - formes courtes : oui / ok
    """
    ml07 = norm("ML07_TRANSLATION")
    return ml07.str.contains(r"positi|pr[ée]sence|present") | ml07.is_in(["oui", "ok"])


def expr_contexte_carba():
    """Contexte carbapenemase : porte par ML07, ML86 ou MOT_DESCRIPTION."""
    return (
        norm("ML07_TRANSLATION").str.contains(r"carba")
        | norm("ML86_TRANSLATION").str.contains(r"carba")
        | norm("MOT_DESCRIPTION").str.contains(r"carba")
    )


def expr_mot_carba():
    """MOT_DESCRIPTION mentionne la carbapenemase."""
    return norm("MOT_DESCRIPTION").str.contains(r"carba")


def expr_contexte_erv():
    """Contexte ERV : recherche d'ERV (ML18) ou ML86 erv / glycopeptide."""
    return norm("ML18_TRANSLATION").str.contains("recherche d'erv") | norm(
        "ML86_TRANSLATION"
    ).str.contains(r"\berv\b|glycopeptide")


def expr_contexte_entero():
    """Contexte enterocoque : faecium / enterococcus (sans exiger faecium)."""
    return norm("MORG_NAME").str.contains(
        r"faecium|enterococcus|enterocoque|entérocoque"
    )


def expr_vanco_resistante():
    """Vancomycine rendue Resistante (ABRS_RISREPORTVALUE = 1)."""
    ab_vanco = norm("AB_NAME").str.contains("vanco")
    abrs_resistant = (
        pl.col("ABRS_RISREPORTVALUE").cast(pl.Utf8).fill_null("").str.strip_chars()
        == "1"
    )
    return ab_vanco & abrs_resistant


def expr_pcr_positif(df):
    """
    Un gene PCR positif (colonnes larges OXA48/KPC/NDM/VIM_IMP).
    Branche seulement si ces colonnes existent, sinon False.
    """
    genes = ["OXA48", "KPC", "NDM", "VIM_IMP"]
    presents = [g for g in genes if g in df.columns]

    def gene_positif(col):
        return (
            pl.col(col)
            .cast(pl.Utf8)
            .fill_null("")
            .str.strip_chars()
            .str.to_lowercase()
            .is_in(["p", "positif", "positive"])
        )

    if presents:
        return pl.any_horizontal([gene_positif(g) for g in presents])
    return pl.lit(False)


def expr_is_epc(df):
    """
    EPC positif si :
      - un gene PCR est positif, OU
      - contexte carba avec ML07 ou ISOT positif, OU
      - MOT = Carbapenemase couple a ISOT positif (couplage anti
        faux positif "Envoi vers le SIR / OK").
    """
    return (
        expr_pcr_positif(df)
        | (expr_contexte_carba() & (expr_ml07_positif() | expr_isot_positif()))
        | (expr_mot_carba() & expr_isot_positif())
    )


def expr_is_erv():
    """
    ERV positif si :
      - contexte ERV avec ML07 ou ISOT positif, OU
      - vanco resistante en contexte enterocoque.
    """
    return (expr_contexte_erv() & (expr_ml07_positif() | expr_isot_positif())) | (
        expr_vanco_resistante() & expr_contexte_entero()
    )


def expr_resultat_disponible():
    """Resultat exploitable si RSLT_STATUS in (3 Partiel, 4 Complet, 5 Ferme)."""
    return pl.col("RSLT_STATUS").is_in([3, 4, 5])


def expr_statut_resultat():
    """
    Libelle oriente FHIR (ServiceRequest.status), mapping labo :
      1/2 -> requested, 3 -> in-progress, 4/5 -> completed, 6 -> revoked.
    """
    return (
        pl.when(pl.col("RSLT_STATUS").is_in([1, 2]))
        .then(pl.lit("requested"))
        .when(pl.col("RSLT_STATUS") == 3)
        .then(pl.lit("in-progress"))
        .when(pl.col("RSLT_STATUS").is_in([4, 5]))
        .then(pl.lit("completed"))
        .when(pl.col("RSLT_STATUS") == 6)
        .then(pl.lit("revoked"))
        .otherwise(pl.lit(None))
        .alias("STATUT_RESULTAT")
    )


def classifier(df):
    """
    Ajoute IS_EPC, IS_ERV, STATUT_RESULTAT et STATUT_SURVEILLANCE.
    Un positif n'est jamais masque par le statut du resultat ; la
    distinction NEGATIF / RESULTAT_NON_DISPONIBLE depend, elle, de
    la disponibilite du resultat.
    """
    return df.with_columns(
        [
            expr_is_epc(df).alias("IS_EPC"),
            expr_is_erv().alias("IS_ERV"),
            expr_statut_resultat(),
        ]
    ).with_columns(
        pl.when(pl.col("IS_EPC") & pl.col("IS_ERV"))
        .then(pl.lit("EPC+ERV"))
        .when(pl.col("IS_EPC"))
        .then(pl.lit("EPC"))
        .when(pl.col("IS_ERV"))
        .then(pl.lit("ERV"))
        .when(expr_resultat_disponible())
        .then(pl.lit("NEGATIF"))
        .otherwise(pl.lit("RESULTAT_NON_DISPONIBLE"))
        .alias("STATUT_SURVEILLANCE")
    )


def consolider(df):
    """
    Reduit a une ligne par ORD_INTERNALID.
    Priorite : EPC+ERV > EPC > ERV > NEGATIF > RESULTAT_NON_DISPONIBLE.
    Un positif l'emporte ; un vrai negatif passe avant "pas de resultat".
    Departage a priorite egale : prelevement le plus recent.
    maintain_order=True garantit que .first() retient la plus haute
    priorite (group_by ne conserve pas l'ordre du tri sans ce parametre).
    """
    priorite = (
        pl.when(pl.col("STATUT_SURVEILLANCE") == "EPC+ERV")
        .then(0)
        .when(pl.col("STATUT_SURVEILLANCE") == "EPC")
        .then(1)
        .when(pl.col("STATUT_SURVEILLANCE") == "ERV")
        .then(2)
        .when(pl.col("STATUT_SURVEILLANCE") == "NEGATIF")
        .then(3)
        .otherwise(4)
        .alias("PRIORITE")
    )
    tri = ["PRIORITE"]
    descending = [False]
    if "SPMN_SAMPLINGTIME" in df.columns:
        tri.append("SPMN_SAMPLINGTIME")
        descending.append(True)

    return (
        df.with_columns(priorite)
        .sort(tri, descending=descending, nulls_last=True)
        .group_by("ORD_INTERNALID", maintain_order=True)
        .first()
        .drop("PRIORITE")
    )


# =====================================================================
# Points d'entree
# =====================================================================
def biologie_glims(df, detail=False):
    """
    Classe et consolide un DataFrame GLIMS deja charge.

    Parametres
    ----------
    df : pl.DataFrame
        Donnees GLIMS (idealement deja nettoyees ; nettoyer() est
        applique automatiquement si les dates sont encore juliennes).
    detail : bool
        Si True, retourne (df_traquer, df_bhre) au lieu de df_bhre seul.

    Retour
    ------
    pl.DataFrame consolide (une ligne par ORD_INTERNALID), ou le couple
    (df_traquer, df_bhre) si detail=True.
    """
    df_traquer = classifier(df)
    df_bhre = consolider(df_traquer)
    if detail:
        return df_traquer, df_bhre
    return df_bhre


def depuis_csv(chemin, detail=False):
    """Lit un CSV GLIMS, le nettoie, puis classe et consolide."""
    df_clean = nettoyer(lire_csv(chemin))
    return biologie_glims(df_clean, detail=detail)
