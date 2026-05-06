from pathlib import Path
from datetime import datetime
import requests
from fhir.resources.bundle import Bundle


def bundle_to_xml_bytes(bundle: Bundle) -> bytes:
    content = bundle.model_dump_xml()

    if isinstance(content, str):
        return content.encode("utf-8")

    return content


def save_bundle_local(
    bundle: Bundle,
    output_dir: str = "data",
) -> Path:
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
    xml_content = bundle_to_xml_bytes(bundle)

    headers = {
        "Content-Type": "application/fhir+xml",
        "Accept": "application/fhir+xml",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

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
