from fhir.resources.identifier import Identifier
from fhir.resources.location import Location
from fhir.resources.reference import Reference

from fhir_mapping.utils import clean_id


def map_department_location(row: dict) -> Location:
    dept = clean_id(row["departement"])

    return Location(
        id=f"location-departement-{dept}",
        identifier=[
            Identifier(system="urn:departement", value=str(row["departement"]))
        ],
        name=row.get("departement"),
    )


def map_uf_location(row: dict) -> Location:
    uf = clean_id(row["code_uf"])

    return Location(
        id=f"location-uf-{uf}",
        identifier=[Identifier(system="urn:uf", value=str(row["code_uf"]))],
        name=row.get("nom_uf"),
        partOf=(
            Reference(
                reference=f"Location/location-departement-{clean_id(row['departement'])}"
            )
            if row.get("departement")
            else None
        ),
    )
