from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.task import Task

from fhir_mapping.utils import clean_id


def map_task(row: dict) -> Task:
    source_id = clean_id(row["id_source"])

    return Task(
        id=f"task-{source_id}",
        status=calculer_statut_task(row),
        intent="order",
        code=CodeableConcept(
            coding=[
                Coding(
                    system="http://hl7.org/fhir/CodeSystem/task-code",
                    code="fulfill",
                    display="Fulfill the focal request",
                )
            ]
        ),
        description=row.get("description"),
        focus=Reference(reference=f"ServiceRequest/servicerequest-{source_id}"),
        for_fhir=Reference(reference=f"Patient/patient-{clean_id(row['ipp'])}"),
        encounter=(
            Reference(reference=f"Encounter/encounter-{clean_id(row['iep'])}")
            if row.get("iep")
            else None
        ),
        executionPeriod=(
            Period(
                start=row.get("date_reception"),
                end=row.get("date_validation"),
            )
            if row.get("date_reception") or row.get("date_validation")
            else None
        ),
    )


def calculer_statut_task(row: dict) -> str:
    if (
        row.get("date_validation_isolation")
        or row.get("date_validation")
        or row.get("id_isolation")
    ):
        return "completed"
    if (
        row.get("id_prelevement")
        or row.get("date_reception_prelevement")
        or row.get("date_reception")
    ):
        return "in-progress"
    return "requested"
