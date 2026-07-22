# Copyright (c) 2026
# Tous droits réservés CHU Brest.


"""Observation : le resultat BHRe d'un dossier.

Une Observation par dossier (grain retenu). Elle porte le resultat de
surveillance en texte libre (valueCodeableConcept.text) et le
micro-organisme identifie en composant, sans code ni systeme imposes : le
logiciel receveur appliquera sa propre terminologie si necessaire.

Aucune Observation n'est produite tant que le resultat n'est pas disponible.
"""

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation, ObservationComponent

from fhir_mapping.utils import (
    fhir_datetime,
    id_encounter,
    id_observation,
    id_patient,
    id_service_request,
    id_specimen,
    ref,
    safe_str,
)

STATUTS_POSITIFS = {"EPC", "ERV", "EPC+ERV"}


def _valeur_resultat(resultat_bhre: str | None) -> str | None:
    """Texte libre : le resultat BHRe tel que produit par la classification."""
    if resultat_bhre in STATUTS_POSITIFS or resultat_bhre == "NEGATIF":
        return resultat_bhre
    return None


def map_observation(dossier: dict, id_prelevement=None) -> Observation | None:
    """Renvoie None si le resultat n'est pas disponible."""
    valeur = _valeur_resultat(dossier.get("resultat_bhre"))
    if valeur is None:
        return None

    id_dossier = dossier["id_dossier"]

    composants = []
    germe = safe_str(dossier.get("germe"))
    if germe:
        composants.append(
            ObservationComponent(
                code=CodeableConcept(text="Micro-organisme identifié"),
                valueCodeableConcept=CodeableConcept(text=germe),
            )
        )

    return Observation(
        id=id_observation(id_dossier),
        identifier=[Identifier(system="urn:analysis-ref", value=str(id_dossier))],
        basedOn=[ref(id_service_request(id_dossier))],
        status="final",
        code=CodeableConcept(text=dossier.get("libelle_examen") or None),
        subject=ref(id_patient(dossier["ipp"])),
        encounter=ref(id_encounter(dossier["iep"])) if dossier.get("iep") else None,
        effectiveDateTime=fhir_datetime(dossier.get("date_validation")),
        valueCodeableConcept=CodeableConcept(text=valeur),
        specimen=ref(id_specimen(id_prelevement)) if id_prelevement else None,
        component=composants or None,
    )
