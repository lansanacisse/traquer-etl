from fhir.resources.identifier import Identifier
from fhir.resources.location import Location

from fhir_mapping.utils import clean_id, safe_str


def map_patient_location(row: dict) -> Location:
    code = clean_id(row["code_unite_patient"])

    return Location(
        id=f"location-{code}",
        identifier=[
            Identifier(
                system="urn:unit-code",
                value=str(row["code_unite_patient"]),
            )
        ],
        name=safe_str(row.get("nom_unite_patient")),
    )
