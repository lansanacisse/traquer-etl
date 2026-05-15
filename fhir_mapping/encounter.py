from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.identifier import Identifier
from fhir.resources.period import Period
from fhir.resources.reference import Reference

from fhir_mapping.utils import clean_id, safe_datetime


def _max_datetime(values):
    values = [v for v in values if v is not None]
    return max(values) if values else None


def map_encounter(rows: list[dict]) -> Encounter:
    row = rows[0]

    iep = clean_id(row["iep"])
    ipp = clean_id(row["ipp"])

    rows_sorted = sorted(
        rows,
        key=lambda r: r.get("date_debut_mouvement") or r.get("date_debut_sejour") or "",
    )

    locations = []
    seen = set()

    for r in rows_sorted:
        code_unite = r.get("code_unite_patient")

        if not code_unite:
            continue

        key = (
            code_unite,
            r.get("date_debut_mouvement"),
            r.get("date_fin_mouvement"),
            r.get("chambre_patient"),
        )

        if key in seen:
            continue

        seen.add(key)

        form = None
        if r.get("chambre_patient"):
            form = CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/location-physical-type",
                        code="ro",
                        display="Room",
                    )
                ],
                text=str(r.get("chambre_patient")),
            )

        locations.append(
            EncounterLocation(
                location=Reference(
                    reference=f"Location/location-{clean_id(code_unite)}",
                    display=r.get("nom_unite_patient"),
                ),
                form=form,
                period=Period(
                    start=safe_datetime(r.get("date_debut_mouvement")),
                    end=safe_datetime(r.get("date_fin_mouvement")),
                ),
            )
        )

    derniere_fin_mouvement = _max_datetime(
        [r.get("date_fin_mouvement") for r in rows_sorted]
    )

    actual_end = _max_datetime(
        [
            row.get("date_fin_sejour"),
            derniere_fin_mouvement,
        ]
    )

    return Encounter(
        id=f"encounter-{iep}",
        identifier=[
            Identifier(
                system="urn:iep",
                value=str(row["iep"]),
            )
        ],
        status=row.get("statut_encounter") or "in-progress",
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
            start=safe_datetime(row.get("date_debut_sejour")),
            end=safe_datetime(actual_end),
        ),
        location=locations or None,
    )
