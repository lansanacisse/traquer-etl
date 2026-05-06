from fhir.resources.codeablereference import CodeableReference
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.servicerequest import ServiceRequest

from fhir_mapping.utils import clean_id


def map_service_request(row: dict) -> ServiceRequest:
    source_id = clean_id(row["id_source"])
    ipp = clean_id(row["ipp"])
    iep = clean_id(row["iep"])

    return ServiceRequest(
        id=f"servicerequest-{source_id}",
        identifier=[
            Identifier(
                system="urn:service-request",
                value=str(row["id_source"]),
            )
        ],
        status="completed",
        intent="order",
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        encounter=Reference(reference=f"Encounter/encounter-{iep}"),
        code=CodeableReference(concept={"text": row.get("description")}),
        authoredOn=row.get("date_prescription"),
        requester=(
            Reference(
                reference=f"Location/location-uf-{clean_id(row['code_uf'])}",
                display=row.get("nom_uf"),
            )
            if row.get("code_uf")
            else None
        ),
    )
