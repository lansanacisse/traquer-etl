import polars as pl
from fhir.resources.bundle import Bundle

from fhir_mapping.encounter import map_encounter
from fhir_mapping.location import map_patient_location
from fhir_mapping.observation import map_observation
from fhir_mapping.patient import map_patient
from fhir_mapping.service_request import map_service_request
from fhir_mapping.specimen import map_specimen
from fhir_mapping.task import map_task
from fhir_mapping.utils import add_to_bundle


def _not_empty(col: str) -> pl.Expr:
    return pl.col(col).is_not_null() & (pl.col(col).cast(pl.Utf8) != "")


def build_bundle(df: pl.DataFrame) -> Bundle:
    df = df.rename({c: c.lower() for c in df.columns})

    bundle = Bundle(type="transaction", entry=[])

    if "code_unite_patient" in df.columns:
        for row in (
            df.filter(_not_empty("code_unite_patient"))
            .unique(subset=["code_unite_patient"])
            .rows(named=True)
        ):
            add_to_bundle(bundle, map_patient_location(row), "Location")

    for row in df.filter(_not_empty("ipp")).unique(subset=["ipp"]).rows(named=True):
        add_to_bundle(bundle, map_patient(row), "Patient")

    if "iep" in df.columns:
        for _, group in df.filter(_not_empty("iep")).group_by("iep"):
            add_to_bundle(
                bundle,
                map_encounter(group.rows(named=True)),
                "Encounter",
            )

    for row in (
        df.filter(_not_empty("id_source_interne"))
        .unique(subset=["id_source_interne"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_service_request(row), "ServiceRequest")

    for row in (
        df.filter(_not_empty("id_prelevement_interne"))
        .unique(subset=["id_prelevement_interne"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_specimen(row), "Specimen")

    for row in (
        df.filter(_not_empty("id_source_interne"))
        .unique(subset=["id_source_interne"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_task(row), "Task")

    if "id_isolation" in df.columns:
        for _, group in df.filter(_not_empty("id_isolation")).group_by("id_isolation"):
            add_to_bundle(
                bundle,
                map_observation(group.rows(named=True)),
                "Observation",
            )

    return bundle
