# Copyright (c) 2026
# Tous droits réservés.

"""
Point d'entree du pipeline TRAQUER.

Enchaine les six etapes, de l'extraction Oracle jusqu'a l'ecriture du
Bundle FHIR en XML :

    1. extraction GLIMS et GAM (Oracle)
    2. transformation de chaque source
    3. fusion par sejour (IEP)
    4. normalisation vers le modele pivot
    5. construction du Bundle FHIR
    6. sauvegarde locale du XML

Usage :
    python main.py
"""

import logging
import sys
from pathlib import Path

import polars as pl

from config import OUTPUT_DIR
from extract.oracle_extract import extract_gam_data, extract_oraglims_data
from fhir_mapping.bundle import build_bundle
from load.fhir_load import save_bundle_local
from transform.fusion_gam_glims import fusion_gam_glims
from transform.gam_mouvements import mouvements_gam
from transform.glims_biologie import biologie_glims
from transform.normalisation import normaliser

logger = logging.getLogger(__name__)


def configurer_logs(niveau: int = logging.INFO) -> None:
    """
    Configure la journalisation pour toute l'application.

    C'est le role du point d'entree, et de lui seul : un module de
    bibliotheque qui appellerait basicConfig ecraserait la configuration
    de l'appelant.
    """
    logging.basicConfig(
        level=niveau,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def _extraire() -> tuple[pl.DataFrame, pl.DataFrame]:
    """Extrait les donnees brutes de GLIMS et du GAM."""
    logger.info("Etape 1/6 : extraction Oracle")
    df_glims = extract_oraglims_data()
    df_gam = extract_gam_data()
    logger.info(
        "Extraction terminee : GLIMS %s lignes, GAM %s lignes",
        df_glims.height,
        df_gam.height,
    )
    return df_glims, df_gam


def _transformer(
    df_glims: pl.DataFrame, df_gam: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Classe la biologie (BHRe) et type les mouvements."""
    logger.info("Etape 2/6 : transformation des sources")
    df_bio = biologie_glims(df_glims)
    df_mouvements = mouvements_gam(df_gam)
    logger.info(
        "Transformation terminee : %s dossiers, %s mouvements",
        df_bio.height,
        df_mouvements.height,
    )
    return df_bio, df_mouvements


def executer_pipeline(dossier_sortie: Path = OUTPUT_DIR) -> Path:
    """
    Execute le pipeline complet et renvoie le chemin du XML produit.

    Chaque etape journalise son volume d'entree et de sortie : c'est ce
    qui permet de reperer ou une perte de lignes se produit, sans avoir a
    relancer le pipeline pas a pas.
    """
    df_glims, df_gam = _extraire()
    df_bio, df_mouvements = _transformer(df_glims, df_gam)

    logger.info("Etape 3/6 : fusion GAM x GLIMS par sejour")
    df_fusion = fusion_gam_glims(df_mouvements, df_bio)
    logger.info("Fusion terminee : %s lignes", df_fusion.height)

    logger.info("Etape 4/6 : normalisation vers le modele pivot")
    pivot = normaliser(df_fusion)
    logger.info(
        "Pivot construit : %s",
        ", ".join(f"{nom} {table.height}" for nom, table in pivot.items()),
    )

    logger.info("Etape 5/6 : construction du Bundle FHIR")
    bundle = build_bundle(pivot)
    logger.info("Bundle construit : %s ressources", len(bundle.entry or []))

    logger.info("Etape 6/6 : sauvegarde locale")
    chemin = save_bundle_local(bundle, output_dir=dossier_sortie)
    logger.info("Pipeline termine : %s", chemin)
    return chemin


def main() -> int:
    """
    Lance le pipeline et renvoie le code de sortie du processus.

    Retourne 0 si tout s'est bien passe, 1 en cas d'echec : c'est ce que
    cmd-traquer.sh (ou un cron) doit tester pour savoir si l'execution a
    reussi.
    """
    configurer_logs()
    try:
        executer_pipeline()
    except Exception:
        logger.exception("Echec du pipeline")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
