from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.specimen import Specimen, SpecimenCollection

from fhir_mapping.utils import clean_id, get_demande_id, safe_datetime


def map_specimen(row: dict) -> Specimen:
    specimen_id = clean_id(row["id_prelevement_interne"])
    ipp = clean_id(row["ipp"])
    demande_id = get_demande_id(row)

    return Specimen(
        id=f"specimen-{specimen_id}",
        identifier=[
            Identifier(
                system="urn:prelevement-glims",
                value=str(row["id_prelevement_interne"]),
            )
        ],
        status="available",
        type=CodeableConcept(text=row.get("type_prelevement")),
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        request=[
            Reference(
                reference=f"ServiceRequest/servicerequest-{demande_id}",
            )
        ],
        collection=SpecimenCollection(
            collectedDateTime=safe_datetime(row.get("date_prelevement"))
        ),
        receivedTime=safe_datetime(
            row.get("date_reception_prelevement") or row.get("date_reception")
        ),
    )
