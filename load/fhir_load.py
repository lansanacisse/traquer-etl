# Copyright (c) 2026
# Tous droits réservés.

"""
Chargement du Bundle FHIR : derniere etape du pipeline.

Deux sorties possibles, independantes l'une de l'autre :
  - sauvegarde locale du XML (tests, archivage, verification manuelle) ;
  - envoi direct a un serveur FHIR (integration a l'application TRAQUER).
"""

from datetime import datetime
from pathlib import Path

import requests
from fhir.resources.bundle import Bundle


def bundle_to_xml_bytes(bundle: Bundle) -> bytes:
    """
    Serialise un Bundle FHIR en XML, toujours sous forme d'octets.

    Selon la version de fhir.resources, model_dump_xml() renvoie soit une
    chaine, soit des octets. On normalise ici pour que les appelants
    (ecriture fichier, requete HTTP) recoivent toujours le meme type.
    """
    content = bundle.model_dump_xml()

    if isinstance(content, str):
        return content.encode("utf-8")

    return content


def save_bundle_local(
    bundle: Bundle,
    output_dir: str = "data",
) -> Path:
    """
    Ecrit le Bundle au format XML dans un fichier local.

    Le nom du fichier est horodate a la seconde, ce qui evite d'ecraser
    les exports precedents et permet de suivre l'historique des envois.

    Retourne le chemin du fichier ecrit.
    """
    output_path = Path(output_dir)

    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"bundle_fhir_{timestamp}.xml"

    output_file.write_bytes(bundle_to_xml_bytes(bundle))

    print(f"Bundle sauvegardé : {output_file}")
    print(f"Nombre de ressources : {len(bundle.entry or [])}")

    return output_file


def send_bundle_to_server(
    bundle: Bundle,
    server_url: str,
    token: str | None = None,
) -> requests.Response:
    """
    Envoie le Bundle a un serveur FHIR par requete HTTP POST.

    Le token, s'il est fourni, est transmis en authentification Bearer.

    Retourne la reponse du serveur. Leve une exception HTTPError si le
    serveur repond en erreur (code 400 ou superieur).
    """
    xml_content = bundle_to_xml_bytes(bundle)

    headers = {
        "Content-Type": "application/fhir+xml",
        "Accept": "application/fhir+xml",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    # timeout indispensable : sans lui, la requete pourrait bloquer
    # le pipeline indefiniment si le serveur ne repond pas.
    response = requests.post(
        server_url,
        data=xml_content,
        headers=headers,
        timeout=60,
    )

    if response.status_code >= 400:
        print("Echec envoi serveur")
        print(f"{response.status_code}")
        print(response.text)
        response.raise_for_status()

    print("Bundle envoyé au serveur")
    print(f"{response.status_code}")

    return response
