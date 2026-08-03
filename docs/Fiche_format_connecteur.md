# Format d'entrée pour TRAQUER

Cette fiche définit un nom de colonne **standard et neutre** pour chaque
donnée attendue en entrée du connecteur, indépendamment du logiciel source
(GLIMS, GAM, HPRIM). Chaque établissement traduit son propre
système vers ces noms ; tout ce qui vient après (fusion, mapping FHIR, export)
fonctionne alors sans modification.

Aucun nom ci-dessous ne fait référence à un éditeur ou logiciel particulier.

Six tables, une ligne par entité réelle :

| Table | Une ligne par |
|---|---|
| `patients` | patient |
| `sejours` | séjour hospitalier |
| `mouvements` | mouvement (changement d'unité) |
| `unites` | unité de soins |
| `dossiers` | dossier d'analyse |
| `prelevements` | prélèvement |

---

## Table `patients`

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `ipp` | Identifiant permanent du patient | texte | Oui | `167825` |
| `nom` | Nom de famille | texte | Oui | `DUPONT` |
| `prenom` | Prénom | texte | Oui | `Jean` |
| `date_naissance` | Date de naissance | date | Oui | `1974-01-31` |
| `sexe` | Sexe administratif, en code FHIR | texte : `male`, `female`, `other`, `unknown` | Oui | `male` |
| `date_deces` | Date de décès, si applicable | date ou vide | Non | (vide) |

---

## Table `sejours`

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `iep` | Identifiant du séjour hospitalier | texte | Oui | `320188` |
| `ipp` | Identifiant du patient concerné | texte | Oui | `167825` |
| `date_debut_sejour` | Date d'entrée | date | Oui | `2026-01-05 08:00:00` |
| `date_fin_sejour` | Date de sortie | date ou vide | Non (vide = en cours) | `2026-01-12 08:00:00` |
| `statut_sejour` | Statut du séjour, en code FHIR | texte : `planned`, `in-progress`, `completed` | Oui | `completed` |

---

## Table `mouvements`

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `id_mouvement` | Identifiant unique du mouvement | texte | Oui | `40017` |
| `iep` | Séjour auquel appartient ce mouvement | texte | Oui | `320188` |
| `code_unite` | Code de l'unité de soins **du mouvement** (pas du séjour) | texte | Oui | `500` |
| `nom_unite` | Libellé de l'unité de soins | texte | Oui | `Réanimation médicale` |
| `batiment` | Bâtiment | texte | Non | `A` |
| `etage` | Étage | texte | Non | `2` |
| `chambre` | Chambre (peut être alphanumérique) | texte | Non | `R106` |
| `lit` | Lit | texte | Non | `1` |
| `date_debut_mouvement` | Date de début du mouvement | date | Oui | `2026-01-05 08:00:00` |
| `date_fin_mouvement` | Date de fin du mouvement | date ou vide | Non (vide = en cours) | `2026-01-12 08:00:00` |

---

## Table `unites`

Table déduite des mouvements ; peut aussi être fournie directement.

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `code_unite` | Code de l'unité de soins | texte | Oui | `500` |
| `nom_unite` | Libellé de l'unité de soins | texte | Oui | `Réanimation médicale` |

---

## Table `dossiers`

Le dossier d'analyse est le pivot du monde laboratoire : tous les résultats
s'y rattachent.

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `id_dossier` | Identifiant du dossier d'analyse | texte | Oui | `ORD-A1` |
| `ipp` | Patient concerné | texte | Oui | `167825` |
| `iep` | Séjour concerné | texte | Oui | `320188` |
| `libelle_examen` | Libellé de l'examen demandé | texte | Oui | `Recherche de BHRe` |
| `service_demandeur` | Service ayant prescrit l'analyse | texte | Non | `Hygiène hospitalière` |
| `statut_suivi` | Avancement de l'analyse | texte : `requested`, `in-progress`, `done` | Oui | `done` |
| `resultat_bhre` | Résultat de la surveillance | texte : `EPC`, `ERV`, `EPC+ERV`, `NEGATIF`, `RESULTAT_NON_DISPONIBLE` | Oui | `EPC` |
| `germe` | Micro-organisme identifié | texte ou vide | Non | `Klebsiella pneumoniae` |
| `date_prescription` | Date de la demande d'analyse | date ou vide | Non | `2026-01-06 09:00:00` |
| `date_validation` | Date de validation du résultat | date ou vide | Non | `2026-01-08 14:00:00` |

---

## Table `prelevements`

| Colonne standard | Signification | Type | Obligatoire | Exemple |
|---|---|---|---|---|
| `id_prelevement` | Identifiant du prélèvement | texte | Oui | `SPMN-S1` |
| `id_dossier` | Dossier d'analyse auquel il appartient | texte | Oui | `ORD-A1` |
| `ipp` | Patient concerné | texte | Oui | `167825` |
| `date_prelevement` | Date et heure du prélèvement | date | Oui | `2026-01-07 10:00:00` |
| `date_reception` | Date et heure de réception au laboratoire | date ou vide | Non | `2026-01-07 12:00:00` |

---

## Règles communes à toutes les tables

**Identifiants** : toujours en texte, jamais en nombre. Un identifiant lu
comme un entier perd ses zéros de tête (`000167825` devient `167825`) et casse
les rapprochements entre tables.

**Dates** : format `AAAA-MM-JJ HH:MM:SS`, ou type date natif si la source en
dispose. Toute date sentinelle signifiant « pas de fin » (ex. convention
Oracle `4712-12-31`) doit être remplacée par une valeur vide avant transmission.

**Clés de rapprochement** : `ipp` relie une ligne à un même patient dans
toutes les tables. `iep` relie une ligne à un même séjour. `id_dossier` relie
une ligne à un même dossier d'analyse. Ces trois identifiants doivent être
strictement identiques (même valeur, même format) partout où ils apparaissent.

**Valeurs codées** (`sexe`, `statut_sejour`, `statut_suivi`) : à traduire vers
les valeurs listées dans cette fiche avant transmission. Toute autre valeur
n'est pas garantie d'être interprétée correctement en aval.