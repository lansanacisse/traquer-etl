from extract.oracle_extract import extract_oraglims_data
from transform.clean_data import clean_data
from fhir_mapping.bundle import build_bundle
from load.fhir_load import save_bundle_local


def main():

    print("DEBUT EXTRACTION GLIMS")
    df_raw = extract_oraglims_data()

    print(f"Nombre de lignes extraites : {len(df_raw)}")

    print("DEBUT DE TRAIITEMENT")
    df_clean = clean_data(df_raw)

    print(f"Nombre de lignes nettoyées : {len(df_clean)}")

    print("DEBUT BUILD FHIR BUNDLE")
    bundle = build_bundle(df_clean)

    nb_resources = len(bundle.entry or [])

    print(f"Nombre de ressources FHIR : {nb_resources}")

    print("DEBUT SAUVEGARDE")

    output_file = save_bundle_local(
        bundle=bundle,
        output_dir="output/local",
    )

    print(f"XML sauvegardé : {output_file}")

    print("FIN PIPELINE TRAQUER")


if __name__ == "__main__":
    main()
