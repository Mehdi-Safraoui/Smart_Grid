"""
Module NLP : traduit une question en français en requête SPARQL.

Outils : spaCy (modèle fr_core_news_sm) pour la tokenisation, la lemmatisation,
l'étiquetage morpho-syntaxique (POS) et le PhraseMatcher (reconnaissance des entités
de l'ontologie). Aucune API de LLM n'est utilisée.

Pipeline en 4 étapes :
  1. Prétraitement      : tokens + lemmes + POS (spaCy), normalisation (minuscules, accents)
  2. Reconnaissance     : PhraseMatcher -> classes, zones, individus de l'ontologie
                          + expressions régulières -> comparateurs, nombres, unités
  3. Intention          : liste / comptage / filtre / superlatif / relation / détail
  4. Génération SPARQL  : on remplit un gabarit de requête avec les éléments trouvés
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc, Span
from spacy.util import filter_spans

from . import vocabulaire as V

# ---------------------------------------------------------------------------
# Chargement du modèle spaCy
# ---------------------------------------------------------------------------
try:
    nlp = spacy.load("fr_core_news_sm")
except OSError as e:  # modèle non installé
    raise RuntimeError("Modèle spaCy manquant : python -m spacy download fr_core_news_sm") from e


def normaliser(texte: str) -> str:
    """minuscules + suppression des accents :  'Éolienne' -> 'eolienne'"""
    texte = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def _sequences(doc) -> tuple[list[str], list[str]]:
    """Deux versions de la phrase : mots normalisés et lemmes normalisés."""
    mots = [normaliser(t.text) for t in doc]
    lemmes = [normaliser(t.lemma_) for t in doc]
    return mots, lemmes


def _mots_du_nom(nom: str) -> list[str]:
    """'Parc_Eolien_SidiDaoud' -> ['parc', 'eolien', 'sidi', 'daoud']"""
    morceaux = re.sub(r"([a-z])([A-Z])", r"\1 \2", nom.replace("_", " ")).split()
    return [normaliser(m) for m in morceaux]


# ---------------------------------------------------------------------------
# Étape 2 : reconnaissance des entités avec le PhraseMatcher de spaCy
# ---------------------------------------------------------------------------
class Reconnaisseur:
    def __init__(self) -> None:
        self.matcher = PhraseMatcher(nlp.vocab)
        self._dynamiques: tuple = ()
        self._cles_dynamiques: set[str] = set()
        for classe, expressions in V.CLASSES.items():
            self._ajouter(f"CLASSE|{classe}", expressions)
        self.mots_generiques = {normaliser(m) for exprs in V.CLASSES.values()
                                for e in exprs for m in e.split()} | {"h2", "zone", "quartier"}

    def _ajouter(self, cle: str, expressions: list[str]) -> None:
        motifs = []
        for doc in nlp.pipe(expressions):
            mots, lemmes = _sequences(doc)
            motifs += [Doc(nlp.vocab, words=mots), Doc(nlp.vocab, words=lemmes)]
        self.matcher.add(cle, motifs)
        if not cle.startswith("CLASSE|"):
            self._cles_dynamiques.add(cle)

    def mettre_a_jour(self, zones: list[str], individus: list[str]) -> None:
        """Ajoute les zones et individus présents dans la base (appelé à chaque question,
        pour reconnaître aussi les individus ajoutés via le CRUD)."""
        if (tuple(zones), tuple(individus)) == self._dynamiques:
            return
        for cle in self._cles_dynamiques:          # on retire les anciennes zones/individus
            if cle in self.matcher:
                self.matcher.remove(cle)
        self._cles_dynamiques = set()
        for z in zones:
            self._ajouter(f"ZONE|{z}", [" ".join(_mots_du_nom(z.replace("Zone_", "")))])
        noms_zones = {normaliser(z.replace("Zone_", "")) for z in zones}
        alias_vus: dict[str, list[str]] = {}
        for ind in individus:
            mots = _mots_du_nom(ind)
            alias = [" ".join(mots)]
            distinctifs = [m for m in mots if m not in self.mots_generiques and m not in noms_zones]
            if distinctifs:
                alias_vus.setdefault(" ".join(distinctifs), []).append(ind)
            self._ajouter(f"INDIVIDU|{ind}", alias)
        for a, inds in alias_vus.items():
            # alias court (« Radès », « El Menzah ») : s'il est partagé par plusieurs individus,
            # on garde celui dont le nom se termine par l'alias, puis le nom le plus court.
            if len(inds) > 1:
                inds = [i for i in inds if " ".join(_mots_du_nom(i)).endswith(a)] or inds
                plus_court = min(len(_mots_du_nom(i)) for i in inds)
                inds = [i for i in inds if len(_mots_du_nom(i)) == plus_court]
            if len(inds) == 1:
                self._ajouter(f"INDIVIDU|{inds[0]}", [a])
        self._dynamiques = (tuple(zones), tuple(individus))

    def entites(self, doc) -> list[Span]:
        mots, lemmes = _sequences(doc)
        spans = []
        for seq in (mots, lemmes):
            d = Doc(nlp.vocab, words=seq)
            for match_id, start, end in self.matcher(d):
                spans.append(Span(doc, start, end, label=nlp.vocab.strings[match_id]))
        return sorted(filter_spans(spans), key=lambda s: s.start)  # garde les plus longues


reconnaisseur = Reconnaisseur()

NOMBRE = r"(\d{1,3}(?:[   ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
UNITE = r"\s*(mwh|mw|kwh|kv|megawatts?|kilovolts?)?"


def _nombre(txt: str) -> float:
    return float(re.sub(r"[   ]", "", txt).replace(",", "."))


# ---------------------------------------------------------------------------
# Résultat de l'analyse
# ---------------------------------------------------------------------------
@dataclass
class Analyse:
    question: str
    tokens: list[dict] = field(default_factory=list)
    entites: list[dict] = field(default_factory=list)
    filtres: list[dict] = field(default_factory=list)
    intention: str = "liste"
    relation: dict | None = None
    superlatif: str | None = None
    agregat: str | None = None
    attribut: str | None = None
    sparql: str = ""
    erreur: str | None = None


# ---------------------------------------------------------------------------
# Étapes 1 à 3 : analyse de la question
# ---------------------------------------------------------------------------
def analyser(question: str) -> Analyse:
    doc = nlp(question)
    a = Analyse(question=question)
    a.tokens = [{"texte": t.text, "lemme": t.lemma_, "pos": t.pos_} for t in doc]
    spans = reconnaisseur.entites(doc)
    for s in spans:
        type_, valeur = s.label_.split("|", 1)
        a.entites.append({"texte": s.text, "type": type_, "valeur": valeur, "debut": s.start})

    texte = normaliser(question)

    # Filtres numériques : "plus de 20 MW", "entre 10 et 100 kWh", "> 50"
    m = re.search(rf"entre\s+{NOMBRE}{UNITE}\s+et\s+{NOMBRE}{UNITE}", texte)
    if m:
        unite = m.group(2) or m.group(4)
        a.filtres += [{"op": ">=", "valeur": _nombre(m.group(1)), "unite": unite},
                      {"op": "<=", "valeur": _nombre(m.group(3)), "unite": unite}]
    else:
        comps = sorted(V.COMPARATEURS, key=lambda c: -len(c[0]))
        alt = "|".join(re.escape(normaliser(c)) for c, _ in comps)
        for m in re.finditer(rf"({alt})\s*{NOMBRE}{UNITE}", texte):
            op = dict((normaliser(c), o) for c, o in comps)[m.group(1)]
            a.filtres.append({"op": op, "valeur": _nombre(m.group(2)), "unite": m.group(3)})

    # Attribut numérique concerné : unité > mot-clé > branche de la classe
    lemmes = {normaliser(t.lemma_) for t in doc} | {normaliser(t.text) for t in doc}
    for f in a.filtres:
        if f["unite"]:
            u = f["unite"].rstrip("s")
            a.attribut = V.UNITES.get(u, a.attribut)
    if not a.attribut:
        for attr, mots in V.MOTS_ATTRIBUT.items():
            if lemmes & {normaliser(m) for m in mots}:
                a.attribut = attr
                break

    # Intention
    if any(normaliser(m) in texte.split() for m in V.MOTS_COMPTAGE):
        a.intention = "comptage"
    else:
        # « consommation totale », « puissance moyenne » : on ignore les mots déjà reconnus
        # comme entité (« moyenne tension » désigne une classe, pas une moyenne)
        couverts = {i for s in spans for i in range(s.start, s.end)}
        hors_entites = {normaliser(t.text) for t in doc if t.i not in couverts}
        if hors_entites & {normaliser(m) for m in V.MOTS_SOMME}:
            a.agregat = "SUM"
        elif hors_entites & {normaliser(m) for m in V.MOTS_MOYENNE}:
            a.agregat = "AVG"
    if not a.filtres:
        if any(re.search(rf"\b{normaliser(m)}\b", texte) for m in V.MOTS_MIN):
            a.superlatif = "ASC"
        elif any(re.search(rf"\b{normaliser(m)}\b", texte) for m in V.MOTS_MAX):
            a.superlatif = "DESC"
    for t in doc:
        lem = normaliser(t.lemma_)
        # le petit modèle spaCy se trompe parfois de lemme (« alimente » étiqueté NOM) :
        # on accepte aussi les formes conjuguées qui commencent par le radical du verbe,
        # sauf les noms dérivés du verbe (« alimentation », « stockage »)
        verbe = lem if lem in V.RELATIONS else next(
            (v for v in V.RELATIONS if normaliser(t.text).startswith(v[:-2])
             and not normaliser(t.text).startswith((v[:-2] + "ation", v[:-2] + "age"))),
            None)
        if verbe:
            rel = V.RELATIONS[verbe]
            suivant = [normaliser(x.text) for x in doc[t.i + 1:t.i + 3]]
            passif = "par" in suivant or "Part" in t.morph.get("VerbForm")
            # « Qu'alimente la batterie ? » : question sur l'objet, le sujet est après le verbe
            # (mais pas « Qu'est-ce QUI alimente l'usine ? » : là, « qui » est le sujet)
            inversion = (normaliser(doc[0].text) in ("que", "qu'", "quoi")
                         and normaliser(doc[t.i - 1].text) != "qui")
            a.relation = {**rel, "position": t.i, "passif": passif or inversion, "verbe": t.text}
            a.intention = "relation" if a.intention != "comptage" else "comptage_relation"
            break
    if a.agregat and a.intention == "liste":
        a.intention = "agregat"
    if a.filtres and a.intention == "liste":
        a.intention = "filtre"
    if a.superlatif and a.intention == "liste":
        a.intention = "superlatif"
    types = {e["type"] for e in a.entites}
    if a.intention == "liste" and types == {"INDIVIDU"}:
        a.intention = "detail"
    return a


# ---------------------------------------------------------------------------
# Étape 4 : génération de la requête SPARQL
# ---------------------------------------------------------------------------
def _contraintes(var: str, ents: list[dict]) -> tuple[list[str], bool]:
    """Transforme les entités en motifs SPARQL pour la variable donnée."""
    lignes, lie = [], False
    classes = [e["valeur"] for e in ents if e["type"] == "CLASSE" and e["valeur"] != "Zone"]
    zones = [e["valeur"] for e in ents if e["type"] == "ZONE"]
    individus = [e["valeur"] for e in ents if e["type"] == "INDIVIDU"]
    if individus:
        lignes.append(f"VALUES ?{var} {{ {' '.join('sg:' + i for i in individus)} }}")
        lie = True
    if classes:
        lignes.append(f"VALUES ?classe_{var} {{ {' '.join('sg:' + c for c in classes)} }}")
        lignes.append(f"?{var} a/rdfs:subClassOf* ?classe_{var} .")
    if zones:
        lignes.append(f"VALUES ?zone_{var} {{ {' '.join('sg:' + z for z in zones)} }}")
        lignes.append(f"?{var} sg:estSitueDans ?zone_{var} .")
    return lignes, lie


def generer(a: Analyse) -> str:
    ents = a.entites

    # --- Détail d'un individu ---
    if a.intention == "detail":
        ind = ents[0]["valeur"]
        return (f"SELECT ?propriete ?valeur WHERE {{\n"
                f"  sg:{ind} ?propriete ?valeur .\n"
                f"  FILTER(?valeur != owl:NamedIndividual)\n}}")

    # --- Question avec une relation (ex. « qui alimente l'usine de Sfax ? ») ---
    if a.relation:
        r = a.relation
        pos = r["position"]
        avant = [e for e in ents if e["debut"] < pos]
        apres = [e for e in ents if e["debut"] > pos]
        cote_sujet, cote_objet = (apres, avant) if r["passif"] else (avant, apres)
        vs, vo = "sujet", "objet"
        c_s, lie_s = _contraintes(vs, cote_sujet)
        c_o, lie_o = _contraintes(vo, cote_objet)
        # Pas de classe imposée sur un côté non précisé (« qui ») : le domaine et le
        # codomaine de la propriété suffisent (ex. alimente : source OU stockage).
        if lie_s and not lie_o:
            projection = [vo]
        elif lie_o and not lie_s:
            projection = [vs]
        else:
            projection = [vs, vo]
        corps = "\n  ".join(c_s + c_o + [f"?{vs} sg:{r['propriete']} ?{vo} ."])
        if a.intention == "comptage_relation":
            p = projection[0]
            return f"SELECT (COUNT(DISTINCT ?{p}) AS ?nombre) WHERE {{\n  {corps}\n}}"
        return (f"SELECT DISTINCT {' '.join('?' + p for p in projection)} WHERE {{\n"
                f"  {corps}\n}}")

    # --- Liste / filtre / superlatif / comptage ---
    classes = [e["valeur"] for e in ents if e["type"] == "CLASSE" and e["valeur"] != "Zone"]
    attribut = a.attribut
    if not attribut and classes:
        attribut = V.ATTRIBUT_PAR_BRANCHE.get(V.BRANCHE.get(classes[0], ""))
    if not classes:
        if attribut:   # « qu'est-ce qui produit plus de 100 MW ? » -> classe déduite de l'attribut
            racines = {"puissanceMW": "SourceProduction", "capaciteStockageMWh": "SystemeStockage",
                       "consommationKWh": "BatimentConsommateur", "tensionKV": "LigneElectrique"}
            ents = ents + [{"type": "CLASSE", "valeur": racines[attribut]}]
        elif any(e["type"] == "ZONE" for e in ents) or any(e["valeur"] == "Zone" for e in ents):
            if any(e["type"] == "ZONE" for e in ents):
                ents = ents + [{"type": "CLASSE", "valeur": "ComposantSmartGrid"}]
            else:   # « quelles sont les zones ? »
                return "SELECT ?zone WHERE {\n  ?zone a sg:Zone .\n} ORDER BY ?zone"
        else:
            raise ValueError("Je n'ai reconnu aucun élément de l'ontologie dans la question.")

    lignes, _ = _contraintes("element", ents)
    agregat = a.intention == "agregat" and attribut
    if attribut:
        motif = f"?element sg:{attribut} ?{attribut} ."
        lignes.append(motif if (a.filtres or a.superlatif or agregat) else f"OPTIONAL {{ {motif} }}")
    for f in a.filtres:
        lignes.append(f"FILTER(?{attribut} {f['op']} {f['valeur']})")
    corps = "\n  ".join(lignes)

    if a.intention == "comptage":
        return f"SELECT (COUNT(DISTINCT ?element) AS ?nombre) WHERE {{\n  {corps}\n}}"
    if agregat:
        # sous-requête DISTINCT : un élément n'est compté qu'une fois même s'il a plusieurs types
        nom = "total" if a.agregat == "SUM" else "moyenne"
        return (f"SELECT ({a.agregat}(?{attribut}) AS ?{nom}) (COUNT(?element) AS ?nombre) WHERE {{\n"
                f"  {{ SELECT DISTINCT ?element ?{attribut} WHERE {{\n  {corps}\n  }} }}\n}}")

    sel = "?element" + (f" ?{attribut}" if attribut else "") + " ?zone"
    requete = (f"SELECT DISTINCT {sel} WHERE {{\n  {corps}\n"
               f"  OPTIONAL {{ ?element sg:estSitueDans ?zone }}\n}}")
    if a.superlatif and attribut:
        requete += f"\nORDER BY {a.superlatif}(?{attribut})\nLIMIT 1"
    elif attribut:
        requete += f"\nORDER BY DESC(?{attribut})"
    return requete


def traduire(question: str, zones: list[str], individus: list[str]) -> Analyse:
    """Point d'entrée : question en français -> Analyse (avec la requête SPARQL)."""
    reconnaisseur.mettre_a_jour(zones, individus)
    a = analyser(question)
    try:
        a.sparql = generer(a)
    except ValueError as e:
        a.erreur = str(e)
    return a
