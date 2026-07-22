# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Specimen : un prelevement (SPMN_INTERNALID), rattache a son dossier."""

from fhir.resources.identifier import Identifier
from fhir.resources.specimen import Specimen, SpecimenCollection

from fhir_mapping.utils import (
    fhir_datetime,
    id_patient,
    id_service_request,
    id_specimen,
    ref,
)


def map_specimen(ligne: dict) -> Specimen:
    id_prelevement = ligne["id_prelevement"]

    return Specimen(
        id=id_specimen(id_prelevement),
        identifier=[
            Identifier(system="urn:prelevement-glims", value=str(id_prelevement))
        ],
        status="available",
        subject=ref(id_patient(ligne["ipp"])),
        request=(
            [ref(id_service_request(ligne["id_dossier"]))]
            if ligne.get("id_dossier")
            else None
        ),
        collection=SpecimenCollection(
            collectedDateTime=fhir_datetime(ligne.get("date_prelevement"))
        ),
        receivedTime=fhir_datetime(ligne.get("date_reception")),
    )
