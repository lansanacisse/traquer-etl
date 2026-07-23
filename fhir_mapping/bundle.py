# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Construction du Bundle FHIR (transaction) a partir du modele pivot.

Le pivot fournit des tables deja au bon grain (une ligne = une entite), donc
cet orchestrateur ne fait que parcourir et assembler : plus aucun `unique`
hasardeux, plus aucun choix de ligne arbitraire.

    from transform.normalize import normaliser
    from fhir_mapping.bundle import build_bundle

    bundle = build_bundle(normaliser(df_fusion))

Ordre de construction : les cibles des references sont creees avant leurs
sources (Location, Patient, puis Encounter, puis le monde GLIMS).
"""

import polars as pl
from fhir.resources.bundle import Bundle

from fhir_mapping.encounter import map_encounter
from fhir_mapping.location import map_service_demandeur, map_unite
from fhir_mapping.observation import map_observation
from fhir_mapping.patient import map_patient
from fhir_mapping.service_request import map_service_request
from fhir_mapping.specimen import map_specimen
from fhir_mapping.task import map_task
from fhir_mapping.utils import add_to_bundle


def _lignes(table: pl.DataFrame) -> list[dict]:
    return table.rows(named=True) if table is not None and table.height else []


def _grouper(table: pl.DataFrame, cle: str) -> dict:
    """Indexe les lignes d'une table par une cle etrangere."""
    index: dict = {}
    for ligne in _lignes(table):
        index.setdefault(ligne.get(cle), []).append(ligne)
    return index


def build_bundle(pivot: dict[str, pl.DataFrame]) -> Bundle:
    bundle = Bundle(type="transaction", entry=[])

    mouvements_par_sejour = _grouper(pivot.get("mouvements"), "iep")
    prelevements_par_dossier = _grouper(pivot.get("prelevements"), "id_dossier")

    # Location : unites de sejour, puis services demandeurs.
    for unite in _lignes(pivot.get("unites")):
        add_to_bundle(bundle, map_unite(unite), "Location")

    services = {
        d["service_demandeur"]
        for d in _lignes(pivot.get("dossiers"))
        if d.get("service_demandeur")
    }
    for service in sorted(services):
        add_to_bundle(bundle, map_service_demandeur(service), "Location")

    # Patient
    for patient in _lignes(pivot.get("patients")):
        add_to_bundle(bundle, map_patient(patient), "Patient")

    # Encounter (le sejour et ses mouvements)
    for sejour in _lignes(pivot.get("sejours")):
        mouvements = mouvements_par_sejour.get(sejour["iep"], [])
        add_to_bundle(bundle, map_encounter(sejour, mouvements), "Encounter")

    # Le monde GLIMS : dossier -> demande, prelevements, resultat, suivi.
    for dossier in _lignes(pivot.get("dossiers")):
        prelevements = prelevements_par_dossier.get(dossier["id_dossier"], [])
        ids_prelevements = [p["id_prelevement"] for p in prelevements]

        add_to_bundle(
            bundle,
            map_service_request(dossier, ids_prelevements),
            "ServiceRequest",
        )

        for prelevement in prelevements:
            add_to_bundle(bundle, map_specimen(prelevement), "Specimen")

        # Un dossier peut avoir plusieurs prelevements, mais l'Observation
        # FHIR n'en reference qu'un : on retient le premier.
        observation = map_observation(
            dossier, ids_prelevements[0] if ids_prelevements else None
        )
        if observation is not None:
            add_to_bundle(bundle, observation, "Observation")

        # Task uniquement tant que l'analyse n'est pas terminee.
        task = map_task(dossier)
        if task is not None:
            add_to_bundle(bundle, task, "Task")

    return bundle
