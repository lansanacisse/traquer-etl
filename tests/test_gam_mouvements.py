"""
Tests unitaires du module gam_mouvements.

Convention : un test = une regle metier verifiee. Pas de melange de
plusieurs regles dans un meme test.
"""

from datetime import datetime

import polars as pl

from transformation.gam_mouvements import (
    appliquer_tests_qualite,
    calculer_duree_mouvement,
    caster_dates,
    consolider_anomalies_sejour,
    detecter_sejour_programme,
    reconstruire_date_fin_mouvement,
    repartir_mouvements,
    tester_duree_valide,
    tester_mouvement_en_cours,
    tester_ordre_chrono,
    tester_uf_presente,
    transformer_mouvements_gam,
)

DATE_REF = datetime(2026, 6, 24, 10, 0, 0)


def _df_mouvement(**overrides) -> pl.DataFrame:
    """Construit une ligne de mouvement avec des valeurs par defaut surchargeables."""
    base = {
        "IEP": "IEP001",
        "LIBELLE_SERVICE": "MEDECINE A",
        "UF_ENTREE": "UF100",
        "DATE_DEBUT_MOUVEMENT": "2026-06-01 08:00:00",
        "DATE_FIN_MOUVEMENT": "2026-06-02 08:00:00",
        "DATE_ENTREE_SEJOUR": "2026-06-01 08:00:00",
        "DATE_SORTIE_SEJOUR": "2026-06-05 08:00:00",
    }
    base.update(overrides)
    return pl.DataFrame([base])


# --- caster_dates ------------------------------------------------------------


def test_caster_dates_convertit_les_quatre_colonnes_en_datetime():
    df = _df_mouvement()
    resultat = caster_dates(df)

    for colonne in [
        "DATE_DEBUT_MOUVEMENT",
        "DATE_FIN_MOUVEMENT",
        "DATE_ENTREE_SEJOUR",
        "DATE_SORTIE_SEJOUR",
    ]:
        assert resultat.schema[colonne] == pl.Datetime


# --- detecter_sejour_programme ------------------------------------------------


def test_sejour_sans_sortie_et_entree_passee_est_programme():
    df = caster_dates(
        _df_mouvement(DATE_ENTREE_SEJOUR="2026-06-01 08:00:00", DATE_SORTIE_SEJOUR=None)
    )
    resultat = detecter_sejour_programme(df, DATE_REF)

    assert resultat["STATUT_PROGRAMMATION"][0] == "Sejour Programmé"


def test_sejour_avec_sortie_renseignee_nest_pas_programme():
    df = caster_dates(_df_mouvement())  # DATE_SORTIE_SEJOUR renseignee
    resultat = detecter_sejour_programme(df, DATE_REF)

    assert resultat["STATUT_PROGRAMMATION"][0] == "Standard / Clôturé"


def test_sejour_sans_sortie_mais_entree_future_nest_pas_programme():
    df = caster_dates(
        _df_mouvement(
            DATE_ENTREE_SEJOUR="2026-07-01 08:00:00",  # apres DATE_REF
            DATE_SORTIE_SEJOUR=None,
        )
    )
    resultat = detecter_sejour_programme(df, DATE_REF)

    assert resultat["STATUT_PROGRAMMATION"][0] == "Standard / Clôturé"


# --- reconstruire_date_fin_mouvement -----------------------------------------


def test_date_fin_manquante_reprend_le_debut_du_mouvement_suivant():
    df = pl.DataFrame(
        [
            {
                "IEP": "IEP001",
                "DATE_DEBUT_MOUVEMENT": "2026-06-01 08:00:00",
                "DATE_FIN_MOUVEMENT": None,
                "DATE_ENTREE_SEJOUR": "2026-06-01 08:00:00",
                "DATE_SORTIE_SEJOUR": None,
            },
            {
                "IEP": "IEP001",
                "DATE_DEBUT_MOUVEMENT": "2026-06-02 09:00:00",
                "DATE_FIN_MOUVEMENT": "2026-06-03 10:00:00",
                "DATE_ENTREE_SEJOUR": "2026-06-01 08:00:00",
                "DATE_SORTIE_SEJOUR": None,
            },
        ]
    )
    df = caster_dates(df)
    resultat = reconstruire_date_fin_mouvement(df)

    assert resultat["DATE_FIN_MOUVEMENT_CORRIGEE"][0] == datetime(2026, 6, 2, 9, 0, 0)


def test_dernier_mouvement_du_sejour_garde_date_fin_nulle_si_absente():
    df = pl.DataFrame(
        [
            {
                "IEP": "IEP001",
                "DATE_DEBUT_MOUVEMENT": "2026-06-02 09:00:00",
                "DATE_FIN_MOUVEMENT": None,
                "DATE_ENTREE_SEJOUR": "2026-06-01 08:00:00",
                "DATE_SORTIE_SEJOUR": None,
            }
        ]
    )
    df = caster_dates(df)
    resultat = reconstruire_date_fin_mouvement(df)

    assert resultat["DATE_FIN_MOUVEMENT_CORRIGEE"][0] is None


# --- consolider_anomalies_sejour ---------------------------------------------


def test_mouvement_avant_entree_sejour_est_une_anomalie():
    df = caster_dates(
        _df_mouvement(
            DATE_DEBUT_MOUVEMENT="2026-05-30 08:00:00",  # avant l'entree
            DATE_ENTREE_SEJOUR="2026-06-01 08:00:00",
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    anomalies = consolider_anomalies_sejour(df)

    assert anomalies.height == 1
    assert anomalies["TYPE_ANOMALIE"][0] == "Mouvement débute avant l'entrée du séjour"


def test_mouvement_apres_sortie_sejour_est_une_anomalie():
    df = caster_dates(
        _df_mouvement(
            DATE_FIN_MOUVEMENT="2026-06-10 08:00:00",  # apres la sortie
            DATE_SORTIE_SEJOUR="2026-06-05 08:00:00",
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    anomalies = consolider_anomalies_sejour(df)

    assert anomalies.height == 1
    assert anomalies["TYPE_ANOMALIE"][0] == "Mouvement finit après la sortie du séjour"


def test_sejour_ouvert_sans_sortie_nest_pas_teste_sur_la_borne_haute():
    df = caster_dates(_df_mouvement(DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None))
    df = reconstruire_date_fin_mouvement(df)
    anomalies = consolider_anomalies_sejour(df)

    assert anomalies.height == 0


# --- calculer_duree_mouvement -------------------------------------------------


def test_duree_mouvement_est_calculee_en_minutes():
    df = caster_dates(
        _df_mouvement(
            DATE_DEBUT_MOUVEMENT="2026-06-01 08:00:00",
            DATE_FIN_MOUVEMENT="2026-06-01 08:30:00",
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    resultat = calculer_duree_mouvement(df)

    assert resultat["DUREE_MOUVEMENT_MINUTES"][0] == 30


# --- tester_mouvement_en_cours ------------------------------------------------


def test_mouvement_sans_date_fin_corrigee_est_marque_en_cours():
    df = caster_dates(_df_mouvement(DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None))
    df = reconstruire_date_fin_mouvement(df)
    resultat = tester_mouvement_en_cours(df)

    assert resultat["TEST_MOUVEMENT_EN_COURS"][0] is True


def test_mouvement_avec_date_fin_nest_pas_en_cours():
    df = caster_dates(_df_mouvement())
    df = reconstruire_date_fin_mouvement(df)
    resultat = tester_mouvement_en_cours(df)

    assert resultat["TEST_MOUVEMENT_EN_COURS"][0] is False


# --- tester_duree_valide -------------------------------------------------------


def test_duree_inferieure_a_une_minute_est_invalide():
    df = caster_dates(
        _df_mouvement(
            DATE_DEBUT_MOUVEMENT="2026-06-01 08:00:00",
            DATE_FIN_MOUVEMENT="2026-06-01 08:00:30",
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    resultat = tester_duree_valide(df)

    assert resultat["TEST_DUREE_VALIDE"][0] is False


def test_duree_dune_minute_ou_plus_est_valide():
    df = caster_dates(
        _df_mouvement(
            DATE_DEBUT_MOUVEMENT="2026-06-01 08:00:00",
            DATE_FIN_MOUVEMENT="2026-06-01 08:01:00",
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    resultat = tester_duree_valide(df)

    assert resultat["TEST_DUREE_VALIDE"][0] is True


# --- tester_ordre_chrono -------------------------------------------------------


def test_fin_avant_debut_echoue_au_test_chronologique():
    df = caster_dates(
        _df_mouvement(
            DATE_DEBUT_MOUVEMENT="2026-06-02 08:00:00",
            DATE_FIN_MOUVEMENT="2026-06-01 08:00:00",  # incoherent
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    resultat = tester_ordre_chrono(df)

    assert resultat["TEST_ORDRE_CHRONO"][0] is False


# --- tester_uf_presente ---------------------------------------------------------


def test_uf_entree_nulle_echoue_au_test_uf_presente():
    df = caster_dates(_df_mouvement(UF_ENTREE=None))
    resultat = tester_uf_presente(df)

    assert resultat["TEST_UF_PRESENTE"][0] is False


# --- repartir_mouvements ---------------------------------------------------------


def test_mouvement_clos_et_conforme_est_valide():
    df = caster_dates(_df_mouvement())
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    df = appliquer_tests_qualite(df)

    df_valide, df_en_cours, df_anomalies = repartir_mouvements(df)

    assert df_valide.height == 1
    assert df_en_cours.height == 0
    assert df_anomalies.height == 0


def test_mouvement_en_cours_avec_uf_va_dans_le_groupe_en_cours():
    df = caster_dates(
        _df_mouvement(
            DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None, UF_ENTREE="UF100"
        )
    )
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    df = appliquer_tests_qualite(df)

    df_valide, df_en_cours, df_anomalies = repartir_mouvements(df)

    assert df_en_cours.height == 1
    assert df_valide.height == 0
    assert df_anomalies.height == 0


def test_mouvement_en_cours_sans_uf_va_dans_le_groupe_anomalies():
    df = caster_dates(
        _df_mouvement(DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None, UF_ENTREE=None)
    )
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    df = appliquer_tests_qualite(df)

    df_valide, df_en_cours, df_anomalies = repartir_mouvements(df)

    assert df_anomalies.height == 1
    assert df_en_cours.height == 0
    assert df_valide.height == 0


def test_aucune_ligne_nest_perdue_entre_les_trois_groupes():
    df = pl.concat(
        [
            caster_dates(_df_mouvement(IEP="IEP001")),
            caster_dates(
                _df_mouvement(
                    IEP="IEP002", DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None
                )
            ),
            caster_dates(_df_mouvement(IEP="IEP003", UF_ENTREE=None)),
        ]
    )
    df = reconstruire_date_fin_mouvement(df)
    df = calculer_duree_mouvement(df)
    df = appliquer_tests_qualite(df)

    df_valide, df_en_cours, df_anomalies = repartir_mouvements(df)

    assert df_valide.height + df_en_cours.height + df_anomalies.height == df.height


# --- transformer_mouvements_gam (test d'integration) ----------------------------


def test_transformer_mouvements_gam_retourne_les_quatre_dataframes():
    df_raw = pl.concat(
        [
            _df_mouvement(IEP="IEP001"),
            _df_mouvement(
                IEP="IEP002", DATE_FIN_MOUVEMENT=None, DATE_SORTIE_SEJOUR=None
            ),
        ]
    )
    resultat = transformer_mouvements_gam(df_raw, date_du_jour=DATE_REF)

    assert resultat.df_valide.height == 1
    assert resultat.df_en_cours.height == 1
    assert resultat.df_anomalies_qualite.height == 0
    assert resultat.df_anomalies_sejour.height == 0
