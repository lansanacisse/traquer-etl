# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Task : suivi de la demande, uniquement tant qu'elle n'est pas terminee.

Les trois statuts TRAQUER (requested / in-progress / done) sont des valeurs
de Task.status, non de ServiceRequest.status. Une fois l'analyse terminee,
le Task n'apporte plus rien : le statut de la ServiceRequest et l'Observation
suffisent. On ne produit donc pas de Task dans ce cas.
"""

from fhir.resources.task import Task

from fhir_mapping.utils import (
    id_encounter,
    id_patient,
    id_service_request,
    id_task,
    ref,
)

STATUTS_AVEC_TASK = {"requested", "in-progress"}


def map_task(dossier: dict) -> Task | None:
    """Renvoie None si l'analyse est terminee (Task inutile)."""
    statut = dossier.get("statut_suivi")
    if statut not in STATUTS_AVEC_TASK:
        return None

    id_dossier = dossier["id_dossier"]

    return Task(
        id=id_task(id_dossier),
        status=statut,
        intent="order",
        description=dossier.get("libelle_examen") or None,
        focus=ref(id_service_request(id_dossier)),
        for_fhir=ref(id_patient(dossier["ipp"])),
        encounter=ref(id_encounter(dossier["iep"])) if dossier.get("iep") else None,
    )
