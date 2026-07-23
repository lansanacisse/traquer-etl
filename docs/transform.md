# `transform/`


Cœur métier. Répond à la question : **ce patient est-il porteur d'une bactérie
hautement résistante ?** Transforme des résultats de laboratoire en texte libre
en une information exploitable : EPC, ERV, les deux, négatif, ou pas encore
disponible.

## Organisation

```
transform/
├── glims_biologie.py     # étape 2a : qui est porteur ?
├── gam_mouvements.py     # étape 2b : où est le patient ?
├── fusion_gam_glims.py   # étape 3 : rapprochement
└── normalisation.py      # étape 4 : mise en forme
```

Ces quatre fichiers s'enchaînent dans cet ordre.

---

## `glims_biologie.py` : classification BHRe

### Le problème

Les résultats ne disent pas « ce patient est porteur ». Ils disent, en texte
libre : « Présence d'une Carbapénémase de type NDM », « Absence de
Carbapénémase type OXA48 », ou « Recherche d'ERV » avec ailleurs « Positif ».
Il faut lire plusieurs colonnes ensemble pour conclure.

### Statuts produits

`STATUT_SURVEILLANCE` :

| Valeur | Signification |
|---|---|
| `EPC` / `ERV` / `EPC+ERV` | Porteur |
| `NEGATIF` | Recherche faite, rien trouvé |
| `RESULTAT_NON_DISPONIBLE` | Analyse pas encore aboutie |


`STATUT_RESULTAT` : `requested` (prélèvement pas fait), `in-progress` (culture
en cours), `done` (résultat disponible).

### Consolidation

Une analyse produit plusieurs lignes (une par antibiotique testé, par exemple).
`consolider()` n'en garde qu'une par dossier, par priorité :

```
EPC+ERV  >  EPC  >  ERV  >  NEGATIF  >  RESULTAT_NON_DISPONIBLE
```


## `gam_mouvements.py` : parcours du patient

Type les dates et calcule le statut du séjour :

| Situation | Statut |
|---|---|
| Entrée dans le futur | `planned` |
| Pas de date de sortie | `in-progress` |
| Sortie renseignée | `completed` |

Ces valeurs sont déjà celles de FHIR : elles ne seront pas retraduites.


## `fusion_gam_glims.py` : rapprochement

Relie les analyses aux séjours par l'**IEP**.


## `normalisation.py` : mise en forme

Découpe la table fusionnée en **six tables propres**, une ligne par entité
réelle. C'est le **modèle pivot**.

| Table | Une ligne par | Contenu |
|---|---|---|
| `patients` | IPP | Nom, prénom, naissance, sexe, décès |
| `sejours` | IEP | Dates, statut |
| `mouvements` | mouvement | Unité, chambre, lit, période |
| `unites` | unité | Code et libellé |
| `dossiers` | analyse | Résultat BHRe, germe, service demandeur |
| `prelevements` | prélèvement | Dates de prélèvement et réception |

C'est le seul fichier à réécrire si un autre hôpital réutilise le connecteur
avec d'autres logiciels sources.


## Interactions

![alt text](image.png)