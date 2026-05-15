from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.servicerequest import ServiceRequest

from fhir_mapping.utils import clean_id, get_demande_id, safe_datetime


def map_service_request(row: dict) -> ServiceRequest:
    demande_id = get_demande_id(row)
    ipp = clean_id(row["ipp"])

    identifiers = [
        Identifier(
            system="urn:source-interne-glims",
            value=str(row.get("id_source_interne")),
        )
    ]

    if row.get("id_source_externe"):
        identifiers.append(
            Identifier(
                system="urn:source-externe-glims",
                value=str(row.get("id_source_externe")),
            )
        )

    return ServiceRequest(
        id=f"servicerequest-{demande_id}",
        identifier=identifiers,
        status=row.get("statut_service_request") or "active",
        intent="order",
        code=CodeableReference(
            concept=CodeableConcept(
                text=row.get("description_demande"),
            )
        ),
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        encounter=(
            Reference(reference=f"Encounter/encounter-{clean_id(row['iep'])}")
            if row.get("iep")
            else None
        ),
        authoredOn=safe_datetime(row.get("date_prescription")),
        specimen=(
            [
                Reference(
                    reference=f"Specimen/specimen-{clean_id(row['id_prelevement_interne'])}"
                )
            ]
            if row.get("id_prelevement_interne")
            else None
        ),
    )
