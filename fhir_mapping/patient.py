# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Patient : une ligne de la table pivot `patients`."""

from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.patient import Patient

from fhir_mapping.utils import fhir_date, fhir_datetime, id_patient, safe_str


def map_patient(ligne: dict) -> Patient:
    nom = safe_str(ligne.get("nom"))
    prenom = safe_str(ligne.get("prenom"))

    return Patient(
        id=id_patient(ligne["ipp"]),
        identifier=[Identifier(system="urn:ipp", value=str(ligne["ipp"]))],
        name=(
            [HumanName(family=nom, given=[prenom] if prenom else None)]
            if (nom or prenom)
            else None
        ),
        birthDate=fhir_date(ligne.get("date_naissance")),
        gender=ligne.get("sexe") or "unknown",
        deceasedDateTime=fhir_datetime(ligne.get("date_deces")),
    )
