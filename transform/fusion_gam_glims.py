import polars as pl


def normalize_ipp(col: str, length: int = 9):
    """
    Normalise un identifiant patient :
    - cast string
    - trim
    - conserve les zéros à gauche
    """
    return pl.col(col).cast(pl.Utf8).fill_null("").str.strip_chars().str.zfill(length)


def fusionner(df_mouvements: pl.DataFrame, df_bio: pl.DataFrame) -> pl.DataFrame:
    """Jointure par intervalle (patient + date prélèvement dans mouvement)."""

    mvt = df_mouvements.with_columns(normalize_ipp("IPP").alias("IPP")).with_columns(
        pl.int_range(pl.len()).alias("_MVT_ID")
    )

    bio = df_bio.with_columns(normalize_ipp("IDNT_CODE").alias("IPP_BIO"))

    apparies = mvt.join_where(
        bio,
        pl.col("IPP") == pl.col("IPP_BIO"),
        pl.col("SPMN_SAMPLINGTIME") >= pl.col("DATE_DEBUT_MOUVEMENT"),
        pl.col("SPMN_SAMPLINGTIME") <= pl.col("DATE_FIN_MOUVEMENT"),
    )

    sans_analyse = mvt.join(
        apparies.select("_MVT_ID").unique(), on="_MVT_ID", how="anti"
    )

    resultat = pl.concat([apparies, sans_analyse], how="diagonal")

    tri_cols = [c for c in ("IPP", "DATE_DEBUT_MOUVEMENT") if c in resultat.columns]

    return resultat.drop(["_MVT_ID", "IPP_BIO"], strict=False).sort(
        tri_cols, nulls_last=True
    )
