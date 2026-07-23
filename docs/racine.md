# Fichiers à la racine

```
traquer-etl/
├── main.py           # point d'entrée : enchaîne les six étapes
├── config.py         # paramètres et identifiants
├── database.py       # connexion Oracle
├── cmd-traquer.sh    # lancement automatisé
├── .env              # mots de passe (jamais versionné)
└── pyproject.toml    # dépendances
```

---

## `main.py`

Seul fichier à lancer. Appelle les six étapes dans l'ordre.

```bash
python main.py
```

| Étape | Action |
|---|---|
| 1 | Extraction GLIMS et GAM |
| 2 | Classification BHRe, typage des mouvements |
| 3 | Fusion par séjour |
| 4 | Normalisation vers le modèle pivot |
| 5 | Construction du Bundle FHIR |
| 6 | Écriture du XML |

Chaque étape annonce ses volumes. Si le nombre de lignes chute entre deux
étapes, on sait immédiatement où chercher.

**Erreurs** : en cas d'échec, le programme s'arrête, journalise la cause
complète et renvoie le code `1` (`0` en cas de succès). C'est ce que teste un
cron. Mieux vaut aucun fichier qu'un fichier incomplet transmis à TRAQUER.

---

## `config.py`

Rassemble tout ce qui change d'un environnement à l'autre. Aucun autre fichier
ne doit contenir de valeur de configuration en dur.

| Variable | Rôle |
|---|---|
| `BASE_DIR` | Répertoire du projet, calculé automatiquement |
| `ORACLE_CONFIG` / `GAM_CONFIG` | Connexions GLIMS et GAM |
| `OUTPUT_DIR` | Dossier de sortie des XML |
| `FHIR_SERVER_URL` / `FHIR_TOKEN` | Serveur TRAQUER |

Les chemins sont ancrés sur `BASE_DIR`, jamais sur le répertoire courant : le
fichier XML atterrit au bon endroit même lancé depuis ailleurs, ce qui est
toujours le cas avec un cron.


## `database.py`

Une seule fonction : `get_oracle_connection(config)`. Elle reçoit la
configuration en paramètre, ce qui lui permet de servir GLIMS et GAM sans
duplication.

GLIMS et GAM partagent instance et identifiants. Seul le service diffère :

| Source | Service |
|---|---|
| GLIMS | `GLIMST` |
| GAM | `NOYGR` |
