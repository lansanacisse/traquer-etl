# Documentation du mapping FHIR — TRAQUER

## 1. Vue d'ensemble

Le mapping FHIR transforme la table fusionnée (GAM x GLIMS, vocabulaire des
systèmes sources) en un **Bundle FHIR R5** de type `transaction`, exporté en
XML pour intégration.

La conversion se fait en deux étapes distinctes :

```
Table fusionnée (CSV/DataFrame)
        │
        ▼
  transform/normalize.py   →  modèle pivot (5 tables canoniques)
        │
        ▼
  fhir_mapping/bundle.py   →  Bundle FHIR R5
        │
        ▼
  bundle.model_dump_xml()  →  XML
```

**Pourquoi deux étapes et pas une seule ?** La table fusionnée mélange les
grains (une ligne peut être un mouvement, une analyse, ou les deux à la
fois) et emploie le vocabulaire propre aux systèmes sources du CHU de Brest
(`ORD_INTERNALID`, `MORG_NAME`...). Le mapping FHIR ne doit connaître ni
l'un ni l'autre : il doit rester réutilisable par un autre établissement.
La normalisation est donc l'unique adaptateur propre à Brest ; c'est le
seul fichier qu'un autre CHU aurait à réécrire.

## 2. Le modèle pivot

`transform/normalize.py` expose une fonction unique :

```python
from transform.normalize import normaliser

pivot = normaliser(df_fusion)
# pivot est un dict[str, pl.DataFrame] avec 6 clés :
# "patients", "sejours", "mouvements", "unites", "dossiers", "prelevements"
```

Chaque table a un grain net (une ligne = une entité). C'est ce qui permet
au mapping de ne plus jamais deviner quelle ligne retenir.

| Table          | Grain (une ligne par...)      | Colonnes                                                                                   |
|----------------|--------------------------------|----------------------------------------------------------------------------------------------|
| `patients`     | `IPP`                          | `ipp`, `nom`, `prenom`, `date_naissance`, `date_deces`, `sexe`                               |
| `sejours`      | `IEP`                          | `iep`, `ipp`, `date_debut`, `date_fin`, `statut`                                             |
| `mouvements`   | `ID_MOUVEMENT`                 | `id_mouvement`, `iep`, `code_unite`, `nom_unite`, `batiment`, `etage`, `chambre`, `lit`, `date_debut`, `date_fin` |
| `unites`       | `code_unite` (déduite)         | `code_unite`, `nom_unite`                                                                    |
| `dossiers`     | `ORD_INTERNALID`               | `id_dossier`, `ipp`, `iep`, `libelle_examen`, `service_demandeur`, `statut_suivi`, `resultat_bhre`, `germe`, `date_prescription`, `date_validation` |
| `prelevements` | `SPMN_INTERNALID`              | `id_prelevement`, `id_dossier`, `ipp`, `date_prelevement`, `date_reception`                  |

### Règle de désambiguïsation : la première valeur non nulle

Dans la table fusionnée, les lignes de mouvement sans analyse ont leurs
colonnes GLIMS à `null` (nom, prénom, naissance...). Prendre une ligne au
hasard produirait un Patient sans nom. La normalisation prend donc, pour
chaque champ, **la première valeur non nulle** du groupe — jamais une ligne
arbitraire.

### Conversions appliquées

- **Fuseau horaire** : toutes les dates sont converties en Europe/Paris.
  FHIR exige un décalage horaire dès qu'un `dateTime` porte une heure ; une
  date naïve est non conforme.
- **Sentinelle Oracle `4712-12-31`** : neutralisée en `null`. Un mouvement
  ou un séjour encore en cours n'a pas de date de fin, pas une fin en l'an
  4712.
- **`DATE_VALIDATION_PCR`** : convertie depuis le format julien GLIMS.
- **Sexe** : `1`/`2` → `male`/`female`, tout le reste → `other`.
- **Statut de séjour** (GAM) → codes `Encounter.status` de FHIR R5 :

  | GAM         | FHIR R5       |
  |-------------|---------------|
  | Programmé   | `planned`     |
  | En cours    | `in-progress` |
  | Terminé     | `completed`   |

  ⚠️ R5 a remplacé `finished` (R4) par `completed`.

- **Statut de suivi TRAQUER** → code FHIR valide :

  | TRAQUER       | FHIR        |
  |---------------|-------------|
  | requested     | requested   |
  | in-progress   | in-progress |
  | done          | completed   |

  ⚠️ `done` n'est pas un code FHIR ; c'est `completed`.

### Colonnes en repli (pas encore dans l'export)

Deux colonnes ne sont pas encore remontées par les requêtes SQL actuelles.
La normalisation prévoit un repli pour ne pas casser en attendant :

| Colonne cible          | Repli utilisé  | À ajouter dans la requête |
|-------------------------|----------------|----------------------------|
| `UFO_ID` (code UF du mouvement) | `UF_ENTREE` (UF du séjour, approximatif) | `PRP.UFO_IDE` |
| `NOM_SERVICE_DEMANDEUR` | *(absent, `requester` non renseigné)* | `CRSP_NAME` |

Tant que `UFO_ID` n'est pas ajouté, tous les mouvements d'un même séjour
partagent la même Location (celle de l'UF d'entrée), même s'ils ont eu lieu
dans des unités différentes. C'est une approximation connue, pas un bug.

## 3. Le mapping FHIR

`fhir_mapping/` contient un module par ressource, plus un orchestrateur.

```
fhir_mapping/
├── __init__.py
├── utils.py            # identifiants, dates, références, ajout au bundle
├── patient.py           # map_patient(ligne)
├── location.py          # map_unite(ligne), map_service_demandeur(nom)
├── encounter.py         # map_encounter(sejour, mouvements)
├── service_request.py   # map_service_request(dossier, id_prelevements)
├── specimen.py           # map_specimen(ligne)
├── observation.py       # map_observation(dossier, id_prelevement)
├── task.py              # map_task(dossier)
└── bundle.py            # build_bundle(pivot) -> Bundle
```

Chaque `map_*` est une fonction pure : elle reçoit une ligne (ou un petit
groupe) déjà au bon grain et renvoie un objet `fhir.resources`. Il n'y a
plus aucune déduplication ni déduction à l'intérieur des mappers — tout le
travail de désambiguïsation a été fait en amont, dans la normalisation.

### 3.1 Convention d'identifiants et de références

Tous les identifiants FHIR sont construits de façon déterministe :

| Ressource       | Identifiant logique             |
|-----------------|----------------------------------|
| Patient         | `patient-{ipp}`                  |
| Encounter       | `encounter-{iep}`                |
| Location        | `location-{code}`                |
| ServiceRequest  | `servicerequest-{id_dossier}`    |
| Specimen        | `specimen-{id_prelevement}`      |
| Observation     | `observation-{id_dossier}`       |
| Task            | `task-{id_dossier}`              |

`clean_id()` normalise chaque valeur (minuscules, sans accent, uniquement
`A-Za-z0-9-.`) pour produire un identifiant FHIR valide.

**Toutes les références internes utilisent `urn:uuid:`.** C'est la
convention observée dans les bundles de référence de l'équipe
d'intégration (`scenario1-fhir-r5.xml`, `demo-fhir_SALIOU.xml`) : chaque
entrée du bundle porte un `fullUrl` en `urn:uuid:<id-logique>`, et toute
référence pointe vers ce même `urn:uuid:`. Le bundle est ainsi
**auto-portant** : chaque référence se résout à l'intérieur du bundle,
sans dépendre d'une base d'URL externe.

```python
# fhir_mapping/utils.py
def ref(id_logique, display=None):
    return Reference(reference=f"urn:uuid:{id_logique}", display=display)

def add_to_bundle(bundle, resource, type_ressource):
    bundle.entry.append(BundleEntry(
        fullUrl=f"urn:uuid:{resource.id}",
        resource=resource,
        request=BundleEntryRequest(method="PUT", url=f"{type_ressource}/{resource.id}"),
    ))
```

### 3.2 Ressource par ressource

**Patient** (`patient.py`) — une ligne de `patients`.
`birthDate` et `deceasedDateTime` sont omis si absents. `gender` vaut
`unknown` par défaut.

**Location** (`location.py`) — deux familles, deux fonctions :
- `map_unite(ligne)` : l'unité de soins où le patient séjourne (clé : code
  UF du mouvement).
- `map_service_demandeur(nom_service)` : le service prescripteur de
  l'analyse (clé : son nom), référencé par `ServiceRequest.requester`.

**Encounter** (`encounter.py`) — un séjour et la liste de ses mouvements.
Chaque mouvement devient un `EncounterLocation` avec sa période ; la
chambre (`LIE_NUM`) est portée par `EncounterLocation.form`, avec le code
standard HL7 `ro` (Room). `Encounter.class` utilise le standard HL7
`v3-ActCode`, code `IMP` (hospitalisation).

**ServiceRequest** (`service_request.py`) — un dossier d'analyse
(`ORD_INTERNALID`). Référence tous ses prélèvements. Le `requester` pointe
vers la Location du service demandeur, si elle est connue. Le `code` est
en texte libre (`libelle_examen`), sans terminologie imposée. Le statut
FHIR (`active` / `completed`) est dérivé du statut de suivi TRAQUER — voir
tableau ci-dessous.

**Specimen** (`specimen.py`) — un prélèvement, rattaché à son dossier via
`request`. Statut fixe `available`.

**Observation** (`observation.py`) — le résultat BHRe d'un dossier, **une
Observation par dossier** (pas d'antibiogramme détaillé, choix délibéré de
sobriété). N'est produite **que si le résultat est disponible**
(`resultat_bhre` dans `{EPC, ERV, EPC+ERV, NEGATIF}`) ; sinon
`map_observation` renvoie `None` et rien n'est ajouté au bundle. Le
résultat est porté en texte libre (`valueCodeableConcept.text`), le germe
en `component`. Référence un seul prélèvement (le premier du dossier) : FHIR
n'autorise qu'un `Specimen` par Observation, même si le dossier en a
plusieurs.

**Task** (`task.py`) — le suivi d'une demande. **N'est produit que si
l'analyse n'est pas terminée** (`statut_suivi` dans `{requested,
in-progress}`). Une fois le résultat rendu, le statut de la ServiceRequest
et l'Observation suffisent ; le Task n'apporterait rien et serait du bruit
dans le bundle (décision reprise d'un échange avec l'équipe d'intégration).

### 3.3 Statuts : correspondances complètes

| Statut TRAQUER (`statut_suivi`) | Task (si produit) | ServiceRequest | Observation |
|-----|-----|-----|-----|
| `requested`   | `requested`   | `active`    | *(non produite)* |
| `in-progress` | `in-progress` | `active`    | *(non produite)* |
| `completed`   | *(aucun Task)*| `completed` | `final` (si résultat disponible) |

⚠️ Ce ne sont pas les mêmes valeurs de statut pour ServiceRequest et Task :
`ServiceRequest.status` n'accepte pas `requested`/`in-progress`, ce sont
des valeurs légales de `Task.status` uniquement. `fhir.resources` **ne
valide pas** ces listes de codes : une valeur incorrecte serait acceptée
silencieusement et se retrouverait, invalide, dans le XML final. La
correspondance ci-dessus doit donc rester strictement respectée.

### 3.4 Terminologie : position actuelle

Aucune terminologie métier propre à TRAQUER n'est imposée (le domaine
`traquer.org` est un site vitrine, sans registre de codes exploitable). Les
champs qui porteraient normalement un code (`Observation.code`,
`ServiceRequest.code`, `valueCodeableConcept`) sont en **texte libre**,
directement issu de la donnée métier. Le logiciel receveur applique sa
propre terminologie s'il en a besoin.

Seuls des **standards HL7 génériques**, nécessaires à la structure FHIR
elle-même, sont utilisés :

| Usage                          | Système                                                        | Code |
|---------------------------------|-----------------------------------------------------------------|------|
| Classe de l'Encounter            | `http://terminology.hl7.org/CodeSystem/v3-ActCode`              | `IMP` |
| Forme de l'`EncounterLocation`   | `http://terminology.hl7.org/CodeSystem/location-physical-type`  | `ro`  |

### 3.5 Construction du Bundle

`build_bundle(pivot)` assemble toutes les ressources dans un ordre précis :
**les cibles des références sont créées avant leurs sources**, pour que
toute référence trouve sa cible dans le bundle.

```
1. Location   — unités de soins, puis services demandeurs
2. Patient
3. Encounter  — un par séjour, avec ses mouvements
4. Pour chaque dossier :
     a. ServiceRequest
     b. Specimen (un par prélèvement du dossier)
     c. Observation (si résultat disponible)
     d. Task (si analyse non terminée)
```

```python
from transform.normalize import normaliser
from fhir_mapping.bundle import build_bundle

pivot = normaliser(df_fusion)
bundle = build_bundle(pivot)
xml = bundle.model_dump_xml(pretty_print=True)
```

## 4. Ce que le mapping ne fait PAS (limites connues)

- **Pas d'antibiogramme complet.** Un seul germe par dossier est transmis ;
  le détail par antibiotique (`AB_NAME`, `ABRS_RISREPORTVALUE`...) est
  perdu, par choix délibéré de sobriété (le besoin de l'hygiène est de
  savoir si le patient est porteur, pas de recevoir le compte rendu
  complet du laboratoire).
- **`requester` dépend d'une colonne pas encore dans l'export**
  (`NOM_SERVICE_DEMANDEUR` / `CRSP_NAME`). Tant qu'elle est absente, le
  `requester` est `None`.
- **Code d'unité approximatif** tant que `UFO_ID` n'est pas remonté (voir
  §2, colonnes en repli).
- **Un seul Specimen par Observation**, même si un dossier a plusieurs
  prélèvements : limite du modèle FHIR `Observation.specimen`
  (cardinalité 0..1), pas du mapping.
- **Aucune journalisation ni gestion d'erreurs** pour l'instant : une ligne
  mal formée peut faire échouer `build_bundle` sans message diagnostique
  détaillé.

## 5. Points de vigilance pour la génération XML

- **Fuseau horaire obligatoire** : vérifié par la normalisation, mais toute
  donnée ajoutée en amont doit rester tz-aware Europe/Paris.
- **`fhir.resources` ne valide pas les codes** (`status`, etc.) : une valeur
  hors nomenclature FHIR est acceptée silencieusement et se retrouve dans
  le XML. La responsabilité de respecter les tableaux du §3.3 repose sur le
  code appelant.
- **Sérialisation XML** : nécessite l'extra `fhir.resources[xml]`
  (`pip install "fhir.resources[xml]"`). Méthode : `bundle.model_dump_xml()`.

## 6. Fichiers du mapping

| Fichier | Rôle |
|---|---|
| `transform/normalize.py` | Table fusionnée → modèle pivot (5 tables) |
| `fhir_mapping/utils.py` | Identifiants, dates FHIR, références, ajout au bundle |
| `fhir_mapping/patient.py` | `map_patient` |
| `fhir_mapping/location.py` | `map_unite`, `map_service_demandeur` |
| `fhir_mapping/encounter.py` | `map_encounter` |
| `fhir_mapping/service_request.py` | `map_service_request` |
| `fhir_mapping/specimen.py` | `map_specimen` |
| `fhir_mapping/observation.py` | `map_observation` |
| `fhir_mapping/task.py` | `map_task` |
| `fhir_mapping/bundle.py` | `build_bundle` (orchestrateur) |