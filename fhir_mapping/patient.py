from fhir.resources.humanname import HumanName
from fhir.resources.identifier import Identifier
from fhir.resources.patient import Patient

from fhir_mapping.utils import (
    clean_id,
    get_prefix,
    safe_date_only,
    safe_datetime,
    safe_str,
)


def map_patient(row: dict) -> Patient:
    ipp = clean_id(row["ipp"])
    prefix = get_prefix(row)

    return Patient(
        id=f"patient-{ipp}",
        identifier=[
            Identifier(
                system="urn:ipp",
                value=str(row["ipp"]),
            )
        ],
        name=[
            HumanName(
                family=safe_str(row.get("nom")),
                given=[safe_str(row.get("prenom"))] if row.get("prenom") else None,
                prefix=[prefix] if prefix else None,
            )
        ],
        birthDate=safe_date_only(row.get("date_naissance")),
        gender=_map_gender(row.get("sexe")),
        deceasedDateTime=(
            safe_datetime(row.get("date_deces")) if row.get("date_deces") else None
        ),
    )


def _map_gender(value: str | None) -> str:
    if value == "M":
        return "male"

    if value == "F":
        return "female"

    return "unknown"
