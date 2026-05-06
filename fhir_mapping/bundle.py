import polars as pl
from fhir.resources.bundle import Bundle

from fhir_mapping.encounter import map_encounter
from fhir_mapping.location import map_department_location, map_uf_location
from fhir_mapping.observation import map_observation
from fhir_mapping.patient import map_patient
from fhir_mapping.service_request import map_service_request
from fhir_mapping.specimen import map_specimen
from fhir_mapping.task import map_task
from fhir_mapping.utils import add_to_bundle


def build_bundle(df: pl.DataFrame) -> Bundle:
    bundle = Bundle(type="transaction", entry=[])

    # Locations département
    for row in (
        df.filter(pl.col("departement").is_not_null())
        .unique(subset=["departement"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_department_location(row), "Location")

    # Locations UF
    for row in (
        df.filter(pl.col("code_uf").is_not_null())
        .unique(subset=["code_uf"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_uf_location(row), "Location")

    # Patients
    for row in (
        df.filter(pl.col("ipp").is_not_null()).unique(subset=["ipp"]).rows(named=True)
    ):
        add_to_bundle(bundle, map_patient(row), "Patient")

    # Encounters
    for row in (
        df.filter(pl.col("iep").is_not_null()).unique(subset=["iep"]).rows(named=True)
    ):
        add_to_bundle(bundle, map_encounter(row), "Encounter")

    # ServiceRequests
    for row in (
        df.filter(pl.col("id_source").is_not_null())
        .unique(subset=["id_source"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_service_request(row), "ServiceRequest")

    # Specimens
    for row in (
        df.filter(pl.col("id_prelevement").is_not_null())
        .unique(subset=["id_prelevement"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_specimen(row), "Specimen")

    # Observations
    for row in (
        df.filter(pl.col("id_isolation").is_not_null())
        .unique(subset=["id_isolation"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_observation(row), "Observation")
    # Tasks
    for row in (
        df.filter(pl.col("id_source").is_not_null())
        .unique(subset=["id_source"])
        .rows(named=True)
    ):
        add_to_bundle(bundle, map_task(row), "Task")

    return bundle
