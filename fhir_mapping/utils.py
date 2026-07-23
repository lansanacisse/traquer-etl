# Copyright (c) 2026
# Tous droits réservés CHU Brest.

import re
import unicodedata
from datetime import date, datetime
from typing import Any

from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.reference import Reference
from fhir.resources.resource import Resource


def safe_str(valeur: Any) -> str | None:
    """Texte nettoye, ou None si vide."""
    if valeur is None:
        return None
    valeur = str(valeur).strip()
    return valeur or None


def clean_id(valeur: Any) -> str:
    """Normalise une valeur en identifiant FHIR (A-Z a-z 0-9 - .)."""
    if valeur is None:
        return "inconnu"
    valeur = str(valeur).strip()
    valeur = unicodedata.normalize("NFKD", valeur)
    valeur = valeur.encode("ascii", "ignore").decode("ascii")
    valeur = re.sub(r"[^A-Za-z0-9\-.]", "-", valeur)
    valeur = re.sub(r"-+", "-", valeur).strip("-")
    return valeur.lower() or "inconnu"


def fhir_datetime(valeur: datetime | str | None) -> str | None:
    """dateTime FHIR : ISO 8601 avec decalage horaire.

    FHIR exige un fuseau des qu'une heure est presente. Le pivot fournit
    des datetime tz-aware (Europe/Paris), donc isoformat() suffit.
    """
    if valeur is None:
        return None
    if isinstance(valeur, datetime):
        return valeur.isoformat()
    if isinstance(valeur, date):
        return valeur.isoformat()
    return safe_str(valeur)


def fhir_date(valeur: datetime | str | None) -> str | None:
    """date FHIR : AAAA-MM-JJ, sans heure."""
    if valeur is None:
        return None
    if isinstance(valeur, (datetime, date)):
        return (
            valeur.date().isoformat()
            if isinstance(valeur, datetime)
            else valeur.isoformat()
        )
    texte = safe_str(valeur)
    return texte[:10] if texte else None


def id_patient(ipp) -> str:
    return f"patient-{clean_id(ipp)}"


def id_encounter(iep) -> str:
    return f"encounter-{clean_id(iep)}"


def id_location(code) -> str:
    return f"location-{clean_id(code)}"


def id_service_request(id_dossier) -> str:
    return f"servicerequest-{clean_id(id_dossier)}"


def id_specimen(id_prelevement) -> str:
    return f"specimen-{clean_id(id_prelevement)}"


def id_observation(id_dossier) -> str:
    return f"observation-{clean_id(id_dossier)}"


def id_task(id_dossier) -> str:
    return f"task-{clean_id(id_dossier)}"


def ref(id_logique: str, display: str | None = None) -> Reference:
    """Reference interne au bundle, en urn:uuid (convention TRAQUER)."""
    return Reference(reference=f"urn:uuid:{id_logique}", display=display)


def add_to_bundle(bundle: Bundle, resource: Resource, type_ressource: str) -> None:
    """Ajoute une ressource au bundle de transaction."""
    bundle.entry.append(
        BundleEntry(
            fullUrl=f"urn:uuid:{resource.id}",
            resource=resource,
            request=BundleEntryRequest(
                method="PUT",
                url=f"{type_ressource}/{resource.id}",
            ),
        )
    )
