# `extract/`


Récupère les données brutes dans les bases Oracle. Aucun traitement, aucun tri :
si les données arrivent bizarres, le problème vient de la base ou de la requête.

## Organisation

```
extract/
├── __init__.py
└── oracle_extract.py
```

| Fonction | Rôle |
|---|---|
| `extract_data(query, source, config)` | Exécute une requête, renvoie un DataFrame |
| `extract_oraglims_data()` | Analyses de microbiologie (service `GLIMST`) |
| `extract_gam_data()` | Séjours et mouvements (service `NOYGR`) |

Les deux dernières font une ligne : elles appellent la première avec leur
requête et leur service.


## Utilisation

```python
from extract.oracle_extract import extract_oraglims_data

df = extract_oraglims_data()
```

## Modifier

**Ajouter une source** : écrire la requête dans `queries/`, ajouter sa config
dans `config.py` si le service diffère, puis :

```python
def extract_nouvelle_source() -> pl.DataFrame:
    """Extrait les donnees de la nouvelle source."""
    return extract_data(NOUVELLE_QUERY, "NOUVELLE_SOURCE", NOUVELLE_CONFIG)
```

**Modifier une requête** : dans `queries/`, jamais ici.