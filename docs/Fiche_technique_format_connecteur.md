# Format de données attendu par le connecteur TRAQUER


Cette fiche décrit le format que doit produire un établissement pour utiliser le connecteur sans modifier la couche de normalisation ni le mapping FHIR.

Le connecteur ne connaît pas GLIMS ni le GAM en tant que systèmes : il ne lit que des colonnes, sous des noms et des types précis. Tout établissement dont l'extraction produit ces colonnes peut brancher directement sa source, en ne réécrivant que l'étape d'extraction (`extract/`) et les requêtes SQL
(`queries/`).

**Ce que cette fiche ne couvre pas** : les règles de détection EPC/ERV, calées sur les libellés du laboratoire du CHU de Brest. Un établissement dont les colonnes correspondent à cette fiche peut avoir des libellés différents (« Présence de... » contre une autre formulation) et doit vérifier ses propres résultats contre les règles de `transform/glims_biologie.py`. 

---

## 1. Le principe

Deux extractions, deux DataFrames en entrée, puis un pipeline commun :

```
Extraction GLIMS  →  DataFrame GLIMS  ─┐
                                       ├─▶  Fusion  ─▶  Normalisation  ─▶  FHIR
Extraction GAM    →  DataFrame GAM   ─┘
```

L'établissement adoptant le connecteur doit produire les deux DataFrames
décrits ci-dessous. Le reste du pipeline (fusion, normalisation, mapping FHIR, export) fonctionne sans modification si les colonnes et formats correspondent.

---

## 2. DataFrame GLIMS (résultats de laboratoire)

Une ligne par résultat élémentaire (avant consolidation). Le pipeline
consolide ensuite à une ligne par dossier d'analyse.

| Colonne | Type attendu | Description | Obligatoire |
|---|---|---|---|
| `ORD_INTERNALID` | texte | Identifiant du dossier d'analyse. Clé de rattachement de tous les résultats. | Oui |
| `IEP` | texte ou entier | Identifiant du séjour. Doit correspondre à l'IEP du GAM. | Oui |
| `IDNT_CODE` | texte | Identifiant du patient (IPP). Doit correspondre à l'IPP du GAM. Attention aux zéros de tête (`000167825`) : forcer explicitement le type texte à la lecture, ne jamais laisser un outil inférer un entier. | Oui |
| `PRSN_ID` | entier | Identifiant interne patient côté laboratoire | Non |
| `PRSN_INTERNALID` | texte | Identifiant interne alternatif | Non |
| `PRSN_LASTNAME`, `PRSN_FIRSTNAME` | texte | Identité du patient | Oui |
| `PRSN_BIRTHDATE` | date | Date de naissance. Texte ISO (`AAAA-MM-JJ HH:MM:SS`) ou type date natif selon la source. | Oui |
| `PRSN_SEX` | texte, `"1"` ou `"2"` | Sexe codé numériquement. Toute autre valeur est traitée comme non renseignée. | Oui |
| `PRSN_DECEASETIME` | date ou vide | Date de décès si applicable | Non |
| `SPMN_INTERNALID` | texte | Identifiant du prélèvement | Oui |
| `SPMN_SAMPLINGTIME`, `SPMN_RECEIPTTIME` | date | Dates de prélèvement et de réception | Oui |
| `ML18_TRANSLATION` | texte | Libellé de l'examen demandé | Oui |
| `ML86_TRANSLATION` | texte | Contexte de la recherche (ex. « Recherche de Carbapénémase ») | Oui |
| `ML07_TRANSLATION` | texte | Résultat en texte libre (ex. « Présence de... », « Absence de... ») | Oui |
| `MORG_NAME` | texte ou vide | Micro-organisme identifié | Non |
| `AB_NAME` | texte ou vide | Nom de l'antibiotique testé | Non |
| `ABRS_RISREPORTVALUE` | texte, `"1"` = résistant | Résultat de l'antibiogramme | Non |
| `MOT_DESCRIPTION` | texte ou vide | Motif du test (utilisé pour la détection carbapénémase) | Non |
| `ISOT_VALUE` | texte ou vide | Valeur brute du test d'isolement | Non |
| `RSLT_STATUS` | entier, 1 à 6 | Statut du résultat labo (voir mapping ci-dessous) | Oui |
| `NOM_SERVICE_DEMANDEUR` | texte | Service ayant prescrit l'analyse | Non (recommandé) |
| `DATE_VALIDATION_PCR` | date ou nombre julien | Date de validation, si PCR | Non |

**Mapping `RSLT_STATUS` attendu** :

| Valeur | Signification |
|---|---|
| 1, 2 | Demande faite, résultat non disponible |
| 3 | Analyse en cours |
| 4, 5, 6 | Résultat disponible |

Si le système source utilise un codage différent, il doit être traduit vers
ces trois catégories avant d'entrer dans le pipeline.

---

## 3. DataFrame GAM (mouvements et séjours)

Une ligne par mouvement (changement d'unité).

| Colonne | Type attendu | Description | Obligatoire |
|---|---|---|---|
| `IPP` | entier ou texte | Identifiant permanent du patient | Oui |
| `IEP` | entier ou texte | Identifiant du séjour | Oui |
| `ID_MOUVEMENT` | entier ou texte | Identifiant unique du mouvement | Oui |
| `UFO_ID` | texte | Code de l'unité **du mouvement** (pas du séjour) | Oui |
| `LIBELLE_SERVICE` | texte | Libellé de l'unité | Oui |
| `LIE_BAT_NUM` | texte | Bâtiment | Non |
| `ETG_NUM` | texte | Étage | Non |
| `LIE_NUM` | texte | Chambre. Peut être alphanumérique (`R106`) : ne jamais laisser un outil inférer un type numérique. | Non |
| `LIT_NUM` | texte | Lit | Non |
| `DATE_ENTREE_SEJOUR`, `DATE_SORTIE_SEJOUR` | date | Bornes du séjour. Sortie vide = séjour en cours. | Oui |
| `DATE_DEBUT_MOUVEMENT`, `DATE_FIN_MOUVEMENT` | date | Bornes du mouvement | Oui |

**Piège connu** : si la base source utilise une date sentinelle pour marquer
l'absence de fin (`4712-12-31`, convention Oracle), elle doit être neutralisée
en valeur vide avant d'entrer dans le pipeline. Sans cela, un séjour en cours
se termine en l'an 4712 dans le résultat final.

**Le statut du séjour** (`STATUT_SEJOUR`) est calculé par le connecteur
lui-même à partir des dates d'entrée et de sortie ; il n'est pas attendu en
entrée.

---

## 4. Clés de rapprochement entre les deux sources

| Clé | Rôle |
|---|---|
| `IPP` (GAM) = `IDNT_CODE` (GLIMS) | Identifie le même patient |
| `IEP` (GAM) = `IEP` (GLIMS) | Identifie le même séjour, sert de clé de fusion |

Le rapprochement se fait **par séjour**, pas par date de prélèvement.


---

## 5. Fuseau horaire et formats de date

Toutes les dates doivent pouvoir être interprétées en Europe/Paris. FHIR exige un décalage horaire dès qu'un horodatage comporte une heure ; le connecteur l'applique automatiquement si les dates arrivent :

- soit déjà typées (type date natif d'une base de données),
- soit en texte au format `AAAA-MM-JJ HH:MM:SS[.mmm]`,
- soit en nombre julien (convention GLIMS spécifique).

Un format de date qui ne correspond à aucun de ces trois cas doit être
converti avant l'entrée dans le pipeline.

---

## 6. Ce qui reste à vérifier même si les colonnes correspondent

Le respect de cette fiche garantit que le pipeline s'exécute sans erreur
technique. Il ne garantit pas que la classification EPC/ERV soit juste pour un autre établissement, car ces règles lisent le **contenu textuel** des colonnes `ML07_TRANSLATION`, `ML86_TRANSLATION`, `MOT_DESCRIPTION`, `ISOT_VALUE`, qui dépend des habitudes de rédaction du laboratoire.

À vérifier avant mise en production dans un nouvel établissement :

- Les libellés positifs et négatifs employés localement correspondent-ils aux motifs recherchés dans `transform/glims_biologie.py` (ex. « présence »,
« absence », « recherche de »)  ?
- Les valeurs codées (sexe, résultat d'antibiogramme) suivent-elles le même
  codage numérique ?
- Un jeu de résultats réels, positifs et négatifs, a-t-il été rejoué contre le pipeline pour confirmer que la classification produite est correcte ?

Cette vérification relève du laboratoire local, pas d'une simple lecture de
cette fiche.