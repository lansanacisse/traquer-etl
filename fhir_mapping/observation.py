from fhir.resources.annotation import Annotation
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation, ObservationComponent
from fhir.resources.reference import Reference

from fhir_mapping.utils import clean_id, get_demande_id, safe_datetime


def map_observation(rows: list[dict]) -> Observation:
    row = rows[0]

    isolation_id = clean_id(row["id_isolation"])
    ipp = clean_id(row["ipp"])
    demande_id = get_demande_id(row)

    components = []

    if row.get("nom_microorganisme"):
        components.append(
            ObservationComponent(
                code=CodeableConcept(text="Micro-organisme identifié"),
                valueCodeableConcept=CodeableConcept(
                    text=row.get("nom_microorganisme")
                ),
            )
        )

    seen_antibiotiques = set()

    for r in rows:
        nom_antibiotique = r.get("nom_antibiotique")
        sigle_antibiotique = r.get("sigle_antibiotique")
        sensibilite = r.get("sensibilite_antibiotique")
        cmi = r.get("cmi_antibiotique")

        key = (
            nom_antibiotique,
            sigle_antibiotique,
            sensibilite,
            cmi,
        )

        if not nom_antibiotique or key in seen_antibiotiques:
            continue

        seen_antibiotiques.add(key)

        components.append(
            ObservationComponent(
                code=CodeableConcept(
                    text=nom_antibiotique,
                ),
                valueCodeableConcept=(
                    CodeableConcept(text=sensibilite) if sensibilite else None
                ),
            )
        )

    notes = []

    for r in rows:
        if r.get("cmi_antibiotique") is not None and r.get("nom_antibiotique"):
            notes.append(
                Annotation(
                    text=f"{r.get('nom_antibiotique')} - CMI: {r.get('cmi_antibiotique')}"
                )
            )

    return Observation(
        id=f"observation-{isolation_id}",
        identifier=[
            Identifier(
                system="urn:isolation-glims",
                value=str(row["id_isolation"]),
            )
        ],
        basedOn=[
            Reference(
                reference=f"ServiceRequest/servicerequest-{demande_id}",
            )
        ],
        status=row.get("statut_observation") or "final",
        code=CodeableConcept(
            text=row.get("description_demande") or "Résultat microbiologique"
        ),
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        encounter=(
            Reference(reference=f"Encounter/encounter-{clean_id(row['iep'])}")
            if row.get("iep")
            else None
        ),
        specimen=(
            Reference(
                reference=f"Specimen/specimen-{clean_id(row['id_prelevement_interne'])}"
            )
            if row.get("id_prelevement_interne")
            else None
        ),
        effectiveDateTime=safe_datetime(
            row.get("date_validation_isolation") or row.get("date_validation")
        ),
        interpretation=(
            [CodeableConcept(text=row.get("sensibilite_antibiotique"))]
            if row.get("sensibilite_antibiotique")
            else None
        ),
        note=notes or None,
        component=components or None,
    )
