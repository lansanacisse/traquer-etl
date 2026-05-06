import re
import unicodedata
from typing import Any

from fhir.resources.bundle import BundleEntry, BundleEntryRequest


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


def add_to_bundle(bundle, resource, resource_type: str):
    bundle.entry.append(
        BundleEntry(
            fullUrl=f"urn:uuid:{resource.id}",
            resource=resource,
            request=BundleEntryRequest(
                method="POST",
                url=resource_type,
            ),
        )
    )
