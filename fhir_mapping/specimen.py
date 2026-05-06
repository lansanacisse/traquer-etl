from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.specimen import Specimen
from fhir.resources.specimen import SpecimenCollection

from fhir_mapping.utils import clean_id


def map_specimen(row: dict) -> Specimen:
    specimen_id = clean_id(row["id_prelevement"])
    ipp = clean_id(row["ipp"])

    return Specimen(
        id=f"specimen-{specimen_id}",
        identifier=[
            Identifier(
                system="urn:specimen",
                value=str(row["id_prelevement"]),
            )
        ],
        status="available",
        type=CodeableConcept(
            text=row.get("libelle_prelevement") or row.get("type_prelevement")
        ),
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        collection=SpecimenCollection(collectedDateTime=row.get("date_prelevement")),
        receivedTime=row.get("date_reception_prelevement") or row.get("date_reception"),
    )
