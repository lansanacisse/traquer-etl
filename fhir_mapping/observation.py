from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation, ObservationComponent
from fhir.resources.reference import Reference

from fhir_mapping.utils import clean_id


def map_observation(row: dict) -> Observation:
    isolation_id = clean_id(row["id_isolation"])

    ipp = clean_id(row["ipp"])
    iep = clean_id(row["iep"])
    specimen_id = clean_id(row["id_prelevement"])

    components = []

    if row.get("microorganisme"):
        components.append(
            ObservationComponent(
                code=CodeableConcept(text="Micro-organisme identifié"),
                valueCodeableConcept=CodeableConcept(text=row.get("microorganisme")),
            )
        )

    if row.get("antibiotique"):
        components.append(
            ObservationComponent(
                code=CodeableConcept(text=row.get("antibiotique")),
                valueCodeableConcept=(
                    CodeableConcept(text=row.get("sensibilite"))
                    if row.get("sensibilite")
                    else None
                ),
            )
        )

    return Observation(
        id=f"observation-{isolation_id}",
        identifier=[
            Identifier(
                system="urn:isolation",
                value=str(row["id_isolation"]),
            )
        ],
        status="final",
        code=CodeableConcept(text="Résultat microbiologique"),
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        encounter=Reference(reference=f"Encounter/encounter-{iep}"),
        specimen=Reference(reference=f"Specimen/specimen-{specimen_id}"),
        effectiveDateTime=row.get("date_validation_isolation"),
        interpretation=(
            [CodeableConcept(text=row.get("sensibilite"))]
            if row.get("sensibilite")
            else None
        ),
        component=components or None,
    )
