# Copyright (c) 2026
# Tous droits réservés CHU Brest.

"""Location : unite de soins (sejour du patient) ou service demandeur.

Deux familles de Location coexistent, avec des cles differentes :
  - les unites ou le patient sejourne, identifiees par leur code UF ;
  - les services demandeurs (prescripteurs GLIMS), identifies par leur nom.
Les bundles de reference referencent une Location en `requester` de la
ServiceRequest, d'ou cette seconde famille.
"""

from fhir.resources.identifier import Identifier
from fhir.resources.location import Location

from fhir_mapping.utils import id_location, safe_str


def map_unite(ligne: dict) -> Location:
    """Unite de soins, cle = code UF du mouvement."""
    code = ligne["code_unite"]
    return Location(
        id=id_location(code),
        identifier=[Identifier(system="urn:unit-code", value=str(code))],
        name=safe_str(ligne.get("nom_unite")),
    )


def map_service_demandeur(nom_service: str) -> Location:
    """Service demandeur (prescripteur), cle = son nom."""
    return Location(
        id=id_location(nom_service),
        identifier=[Identifier(system="urn:service-demandeur", value=nom_service)],
        name=safe_str(nom_service),
    )
