# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""ServiceRequest : un dossier d'analyse (ORD_INTERNALID)"""

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.identifier import Identifier
from fhir.resources.servicerequest import ServiceRequest

from fhir_mapping.utils import (
    fhir_datetime,
    id_encounter,
    id_location,
    id_patient,
    id_service_request,
    id_specimen,
    ref,
)

STATUT_SERVICE_REQUEST = {
    "requested": "active",
    "in-progress": "active",
    "done": "completed",
}


def map_service_request(dossier: dict, id_prelevements: list) -> ServiceRequest:
    id_dossier = dossier["id_dossier"]
    service = dossier.get("service_demandeur")

    return ServiceRequest(
        id=id_service_request(id_dossier),
        identifier=[Identifier(system="urn:analysis-ref", value=str(id_dossier))],
        status=STATUT_SERVICE_REQUEST.get(dossier.get("statut_suivi"), "active"),
        intent="order",
        code=CodeableReference(
            concept=CodeableConcept(text=dossier.get("libelle_examen") or None)
        ),
        subject=ref(id_patient(dossier["ipp"])),
        encounter=ref(id_encounter(dossier["iep"])) if dossier.get("iep") else None,
        authoredOn=fhir_datetime(dossier.get("date_prescription")),
        requester=ref(id_location(service), display=service) if service else None,
        specimen=[ref(id_specimen(p)) for p in id_prelevements] or None,
    )
