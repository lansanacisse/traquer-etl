import polars as pl


def _cle_iep(colonne: str):
    """Normalise une colonne IEP en texte pour une jointure fiable.

    IEP GAM (i64) et ENCT_EXTERNALID GLIMS (souvent texte) sont ramenes
    au meme type. On passe par le texte, en retirant les espaces et un
    eventuel '.0' de flottant, pour eviter les non-correspondances.
    """
    return (
        pl.col(colonne)
        .cast(pl.Utf8)
        .fill_null("")
        .str.strip_chars()
        .str.replace(r"\.0$", "")
        .alias("_IEP_KEY")
    )


def fusion_gam_glims(df_mouvements: pl.DataFrame, df_bio: pl.DataFrame) -> pl.DataFrame:
    """Jointure GAM x GLIMS par sejour (IEP). Une ligne par analyse."""

    mvt = df_mouvements.with_columns(_cle_iep("IEP"))
    bio = df_bio.with_columns(_cle_iep("IEP"))
    resultat = mvt.join(bio, on="_IEP_KEY", how="left")

    tri = [c for c in ("IPP", "IEP") if c in resultat.columns]
    resultat = resultat.drop("_IEP_KEY", strict=False)
    if tri:
        resultat = resultat.sort(tri, descending=[False] * len(tri), nulls_last=True)
    return resultat
