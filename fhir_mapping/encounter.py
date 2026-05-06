from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.identifier import Identifier
from fhir.resources.period import Period
from fhir.resources.reference import Reference

from fhir_mapping.utils import clean_id


def map_encounter(row: dict) -> Encounter:
    iep = clean_id(row["iep"])
    ipp = clean_id(row["ipp"])

    return Encounter(
        id=f"encounter-{iep}",
        identifier=[Identifier(system="urn:iep", value=str(row["iep"]))],
        status="finished" if row.get("date_fin_sejour") else "in-progress",
        class_fhir=[
            CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        code="IMP",
                    )
                ]
            )
        ],
        subject=Reference(reference=f"Patient/patient-{ipp}"),
        actualPeriod=Period(
            start=row.get("date_debut_sejour"),
            end=row.get("date_fin_sejour"),
        ),
        location=(
            [
                EncounterLocation(
                    location=Reference(
                        reference=f"Location/location-uf-{clean_id(row['code_uf'])}",
                        display=row.get("nom_uf"),
                    ),
                    period=Period(
                        start=row.get("date_debut_sejour"),
                        end=row.get("date_fin_sejour"),
                    ),
                )
            ]
            if row.get("code_uf")
            else None
        ),
    )
