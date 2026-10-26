# Branche Réseau (Yassine)

Lignes de transport, lignes de distribution et postes de transformation.

| Critère | Où le montrer |
|---|---|
| Individus | `ontology/build_ontology.py`, section *Réseau* |
| SPARQL CRUD | `backend/app/queries/reseau.py` |
| API | `backend/app/routers/reseau.py` → Swagger `/docs`, tag *Réseau* |
| Interface | `frontend/reseau.html` + `frontend/js/reseau.js` |
| NLP | `backend/app/nlp/vocabulaire.py` (synonymes + relation `relie`) |
| Tests | `backend/tests/test_api.py`, section *RÉSEAU* |
| Valeur ajoutée | parcours de l'énergie + export CSV (page Réseau) |

## 1. Individus

| Individu | Classe | Tension | Relie | Zone |
|---|---|---|---|---|
| Poste_Sfax, Poste_Tunis | PosteTransformation | — | — | Sfax, Tunis |
| **Poste_Kairouan**, **Poste_Sousse** | PosteTransformation | — | — | Kairouan, Sousse |
| Ligne_Tozeur_Sfax | LigneTransport | 225 kV | Centrale_Solaire_Tozeur, Poste_Sfax | Sfax |
| Ligne_Rades_Tunis | LigneTransport | 225 kV | Centrale_Gaz_Rades, Poste_Tunis | Tunis |
| **Ligne_Kairouan_Sousse** | LigneTransport | 225 kV | Poste_Kairouan, Poste_Sousse | Kairouan |
| **Ligne_Sfax_Sousse** | LigneTransport | 150 kV | Poste_Sfax, Poste_Sousse | Sousse |
| Ligne_Poste_Usine_Sfax | LigneDistribution | 30 kV | Poste_Sfax, Usine_Sfax | Sfax |
| Ligne_Quartier_ElMenzah | LigneDistribution | 0,4 kV | Poste_Tunis, Residence_ElMenzah | Tunis |
| **Ligne_Quartier_Sfax** | LigneDistribution | 0,4 kV | Poste_Sfax, Usine_Sfax | Sfax |

En gras : les individus ajoutés. Deux zones ont été ajoutées : `Zone_Kairouan` et `Zone_Sousse`
(dans `AllDifferent`).

### Axiomes de la branche (à savoir expliquer)
- **Restriction** `LigneElectrique ⊑ relie min 2 ComposantSmartGrid` : une ligne relie au moins deux
  éléments. HermiT raisonne en monde ouvert : il ne signale rien s'il en manque un (il suppose qu'il
  existe un élément inconnu). C'est donc l'API qui fait respecter la règle et refuse une ligne avec
  moins de 2 éléments (erreur 400).
- **Disjonctions** `LigneTransport ⊓ LigneDistribution = ∅` et `LigneElectrique ⊓ PosteTransformation = ∅`.
- **Domaine** de `tensionKV` et de `relie` = `LigneElectrique`. Si on donne une tension à un poste,
  HermiT en déduit que le poste est une ligne, ce qui contredit la disjonction.
- **Propriété fonctionnelle** `estSitueDans` : une seule zone. Toutes les zones sont différentes
  (`AllDifferent`), donc deux zones pour un même élément rendent l'ontologie incohérente.

Démonstration avec HermiT :
```bash
python ontology/test_incoherence_reseau.py
# ✅ Ligne à la fois transport et distribution : incohérente, comme attendu
# ✅ Poste de transformation avec une tension : incohérente, comme attendu
# ✅ Ligne située dans deux zones : incohérente, comme attendu
```
Le script ajoute les erreurs en mémoire seulement : `SmartGrid.owl` n'est pas modifié.

## 2. Requêtes SPARQL (`queries/reseau.py`)

| Fonction | Requête | Points à expliquer |
|---|---|---|
| `lister()` | `SELECT … GROUP BY` | `OPTIONAL` pour la tension (un poste n'en a pas), `GROUP_CONCAT` pour la liste des éléments reliés, `FILTER(?tension >= …)`, `CONTAINS(LCASE(STR(?x)))` pour la recherche, `a/rdfs:subClassOf*` pour le filtre « toutes les lignes » |
| `obtenir()` | `SELECT` | un seul individu |
| `creer()` | `INSERT DATA` | tension et `relie` seulement pour une ligne ; au moins 2 éléments, qui doivent exister (requête `VALUES`) |
| `modifier()` | `DELETE / INSERT WHERE` | l'`OPTIONAL` dans le `WHERE` permet de modifier même si l'ancienne valeur n'existe pas |
| `supprimer()` | `DELETE WHERE` (×2) | comme sujet puis comme objet ; renvoie les lignes qui relient désormais moins de 2 éléments (`GROUP BY … HAVING (COUNT(…) < 2)`) |
| `parcours()` | `SELECT` + parcours en largeur | voir la valeur ajoutée |

Tous les noms passent par `safe_id()`, ce qui empêche l'injection SPARQL.
Petite particularité : `GROUP_CONCAT(DISTINCT COALESCE(…, ""))`. Sans le `COALESCE`, rdflib plante
sur un poste, car toutes ses valeurs `?x` sont vides.

Dans la **console SPARQL**, trois requêtes « Réseau » : agrégation `COUNT / AVG / MAX` par type de
ligne, nombre de lignes par poste (`GROUP_CONCAT`), et le parcours complet
source → ligne de transport → poste → ligne de distribution → bâtiment, en une seule requête.

## 3. API (`/api/reseau`)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/reseau?type=&zone=&min_kv=&max_kv=&recherche=&relie_a=` | liste filtrée |
| GET | `/api/reseau/{nom}` | un élément |
| POST | `/api/reseau` | ajout `{nom, type, zone, tension, relie: [..]}` |
| PUT | `/api/reseau/{nom}` | modification `{tension?, zone?, relie?}` |
| DELETE | `/api/reseau/{nom}` | suppression |
| GET | `/api/reseau/parcours?depart=&arrivee=` | chemin de l'énergie |

## 4. NLP

Ajouts dans `vocabulaire.py` :
- des synonymes : *liaison, ligne THT, ligne BT/MT, transport, distribution, poste source, sous-station, gouvernorat…* ;
- les verbes `relier`, `connecter` et `raccorder` → propriété `relie` (sujet `LigneElectrique`).

Questions testées :
- Quelles lignes ont une tension supérieure à 100 kV ?
- Quelles sont les lignes de distribution ?
- Qu'est-ce que relie la ligne Tozeur Sfax ?
- Quelles lignes sont reliées au poste de Sousse ?
- Quelles lignes connectent la centrale solaire de Tozeur ?
- Combien de lignes relient le poste de Sfax ?
- Quelle ligne a la tension la plus faible ?
- Combien de postes y a-t-il ?
- Quels sont les postes de transformation à Sousse ?
- Qu'est-ce qu'il y a à Sfax ?

**Point technique (participe passé).** Dans « les bâtiments *alimentés par* la centrale », la voix
passive inverse le sujet et l'objet. Mais dans « les lignes *reliées au* poste », la ligne reste le
sujet de `relie`. Le pipeline inverse donc toujours avec « par ». Pour un participe sans « par »,
il n'inverse pas si la relation porte l'option `participe_sans_inversion` (seule modification
faite dans `pipeline.py` : une ligne, sans effet sur les autres relations).

## 5. Scénario de démo (≈ 1 min)

« Je suis le parcours de l'énergie, de la centrale de Tozeur jusqu'à l'usine de Sfax. »
1. **Page Réseau** → section *Parcours de l'énergie* : Centrale solaire Tozeur → Usine Sfax → *Tracer*.
   Résultat : centrale → Ligne_Tozeur_Sfax (transport 225 kV) → Poste_Sfax → Ligne_Poste_Usine_Sfax
   (distribution 30 kV) → usine. La tension baisse au poste de transformation.
2. **J'ajoute** `Ligne_Kairouan_Sfax` (transport, 225 kV, zone Kairouan, relie Poste_Kairouan et
   Poste_Sfax) → elle apparaît dans la liste. Filtre *tension min 200* : elle y est.
3. Je trace **Poste Kairouan → Usine Sfax** : le chemin passe maintenant par la nouvelle ligne.
4. **Assistant** (Accueil) : « *Quelles lignes sont reliées au poste de Sfax ?* » → la nouvelle
   ligne sort tout de suite, avec la requête SPARQL générée dans « Voir l'analyse NLP ».
5. J'essaie de créer une ligne qui ne relie qu'un élément → refusée (restriction `relie min 2`).

## 6. Valeur ajoutée
- **Parcours de l'énergie** : l'API lit toutes les arêtes `relie` en une requête SPARQL, construit un
  graphe et cherche le plus court chemin par un parcours en largeur (BFS). Une seconde requête
  donne le type le plus précis de chaque étape (`FILTER NOT EXISTS` sur les sous-classes) et sa tension.
- **Export CSV** de la liste filtrée (séparateur `;` et BOM UTF-8 : s'ouvre directement dans Excel).
