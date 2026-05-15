from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.task import Task

from fhir_mapping.utils import clean_id, get_demande_id, safe_datetime


def map_task(row: dict) -> Task:
    demande_id = get_demande_id(row)
    ipp = clean_id(row["ipp"])

    return Task(
        id=f"task-{demande_id}",
        status=row.get("statut_task") or "requested",
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
        description=row.get("description_demande"),
        focus=Reference(
            reference=f"ServiceRequest/servicerequest-{demande_id}",
        ),
        for_fhir=Reference(reference=f"Patient/patient-{ipp}"),
        encounter=(
            Reference(reference=f"Encounter/encounter-{clean_id(row['iep'])}")
            if row.get("iep")
            else None
        ),
        executionPeriod=(
            Period(
                start=safe_datetime(row.get("date_reception")),
                end=safe_datetime(row.get("date_validation")),
            )
            if row.get("date_reception") or row.get("date_validation")
            else None
        ),
    )
