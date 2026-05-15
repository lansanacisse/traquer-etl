import re
import unicodedata
from datetime import date, datetime
from typing import Any

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.resource import Resource


def safe_str(value: Any) -> str | None:
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def clean_id(value: Any) -> str:
    value = str(value).strip()
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9\-.]", "-", value)
    value = re.sub(r"-+", "-", value)
    value = value.strip("-")

    return value or "unknown"


def safe_date_only(value: str | datetime | date | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    value = str(value).strip()
    return value[:10] if value else None


def safe_datetime(value: str | datetime | date | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    value = str(value).strip()
    return value or None


def get_demande_id(row: dict) -> str:
    return clean_id(row.get("id_source_interne") or row.get("id_source_externe"))


def get_prefix(row: dict) -> str | None:
    titre = safe_str(row.get("titre"))

    if titre:
        return titre

    sexe = row.get("sexe")

    if sexe == "M":
        return "M."

    if sexe == "F":
        return "Mme"

    return None


def add_to_bundle(bundle: Bundle, resource: Resource, resource_type: str) -> None:
    bundle.entry.append(
        BundleEntry(
            fullUrl=f"urn:uuid:{resource.id}",
            resource=resource,
            request=BundleEntryRequest(
                method="PUT",
                url=f"{resource_type}/{resource.id}",
            ),
        )
    )
