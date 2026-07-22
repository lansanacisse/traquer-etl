# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Encounter : un sejour (IEP) et ses mouvements.

Les deux systemes de codage utilises ici (classe de rencontre, type de
lieu) sont des standards HL7 generiques, necessaires a la structure FHIR
elle-meme : ce ne sont pas une terminologie propre a TRAQUER.
"""

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.identifier import Identifier
from fhir.resources.period import Period

from fhir_mapping.utils import (
    fhir_datetime,
    id_encounter,
    id_location,
    id_patient,
    ref,
    safe_str,
)

# Standards HL7 .
SYSTEME_CLASSE_ENCOUNTER = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
SYSTEME_TYPE_LIEU = "http://terminology.hl7.org/CodeSystem/location-physical-type"


def _forme_chambre(chambre) -> CodeableConcept | None:
    """La chambre du patient (LIE_NUM), portee par EncounterLocation.form."""
    if chambre in (None, ""):
        return None
    return CodeableConcept(
        coding=[Coding(system=SYSTEME_TYPE_LIEU, code="ro", display="Room")],
        text=str(chambre),
    )


def map_encounter(sejour: dict, mouvements: list[dict]) -> Encounter:
    """Le sejour recu est deja au bon grain : aucune deduction a faire ici."""
    iep = sejour["iep"]

    locations = [
        EncounterLocation(
            location=ref(
                id_location(m["code_unite"]),
                display=safe_str(m.get("nom_unite")),
            ),
            form=_forme_chambre(m.get("chambre")),
            period=Period(
                start=fhir_datetime(m.get("date_debut_mouvement")),
                end=fhir_datetime(m.get("date_fin_mouvement")),
            ),
        )
        for m in mouvements
        if m.get("code_unite") is not None
    ]

    return Encounter(
        id=id_encounter(iep),
        identifier=[Identifier(system="urn:iep", value=str(iep))],
        status=sejour.get("statut_sejour") or "unknown",
        class_fhir=[
            CodeableConcept(
                coding=[Coding(system=SYSTEME_CLASSE_ENCOUNTER, code="IMP")]
            )
        ],
        subject=ref(id_patient(sejour["ipp"])),
        actualPeriod=Period(
            start=fhir_datetime(sejour.get("date_debut_sejour")),
            end=fhir_datetime(sejour.get("date_fin_sejour")),
        ),
        location=locations or None,
    )
