"""
Vocabulaire du module NLP : fait le lien entre les mots du français et l'ontologie.

C'est ici que chaque membre ajoute les expressions de SA branche.
Les expressions sont écrites en minuscules ; les accents et le pluriel sont gérés
automatiquement (on compare aussi les lemmes fournis par spaCy).
"""

# ---------------------------------------------------------------------------
# 1. CLASSES : nom de la classe OWL -> expressions qui la désignent
# ---------------------------------------------------------------------------
CLASSES = {
    # --- Branche PRODUCTION (Mehdi) ---
    "SourceProduction": ["source", "source de production", "source d'énergie", "producteur",
                         "centrale", "installation de production"],
    "SourceRenouvelable": ["source renouvelable", "énergie renouvelable", "renouvelable",
                           "énergie verte", "source verte"],
    "CentraleSolaire": ["centrale solaire", "solaire", "photovoltaïque", "panneau solaire",
                        "ferme solaire"],
    "ParcEolien": ["parc éolien", "éolien", "éolienne", "ferme éolienne"],
    "SourceFossile": ["source fossile", "fossile", "centrale à gaz", "centrale gaz",
                      "centrale thermique", "non renouvelable"],

    # --- Branche STOCKAGE (Mohamed Elyess) ---
    "SystemeStockage": ["stockage", "système de stockage", "moyen de stockage"],
    "Batterie": ["batterie"],
    "StockageHydrogene": ["hydrogène", "stockage hydrogène", "stockage d'hydrogène", "h2"],
    # TODO Elyess : ajouter des synonymes (accumulateur, ...)

    # --- Branche CONSOMMATION (Ahmed Amine) ---
    "BatimentConsommateur": ["bâtiment", "consommateur", "bâtiment consommateur", "client",
                             "édifice", "établissement", "site consommateur"],
    "BatimentResidentiel": ["résidence", "bâtiment résidentiel", "résidentiel", "logement",
                            "maison", "habitation", "immeuble", "appartement", "villa", "cité",
                            "foyer", "quartier résidentiel"],
    # le tertiaire (hôtel, hôpital, école, bureaux) est rangé dans BatimentCommercial.
    # Pas de « centre commercial » ici : « centre » devient l'alias de Centre_Commercial_Tunis,
    # sinon « le centre commercial » désignerait tous les bâtiments commerciaux (hôtel compris)
    "BatimentCommercial": ["bâtiment commercial", "commercial", "magasin",
                           "commerce", "supermarché", "hôtel", "hôpital", "clinique", "école",
                           "bureau", "tertiaire", "bâtiment tertiaire"],
    "BatimentIndustriel": ["usine", "bâtiment industriel", "industriel", "industrie", "fabrique",
                           "atelier", "cimenterie", "site industriel"],
    "GrosConsommateur": ["gros consommateur", "grand consommateur", "bâtiment énergivore",
                         "gros client"],
    "BatimentAlimenteRenouvelable": ["bâtiment vert", "alimenté en renouvelable",
                                     "alimenté par du renouvelable", "bâtiment écologique",
                                     "bâtiment alimenté en énergie verte", "bâtiment propre"],

    # --- Branche RÉSEAU (Yassine) ---
    "InfrastructureReseau": ["infrastructure", "infrastructure du réseau", "équipement du réseau"],
    "LigneElectrique": ["ligne", "ligne électrique", "câble"],
    "LigneTransport": ["ligne de transport", "ligne haute tension", "haute tension"],
    "LigneDistribution": ["ligne de distribution", "basse tension", "moyenne tension"],
    "PosteTransformation": ["poste", "poste de transformation", "transformateur"],
    "Zone": ["zone", "région", "ville"],
    # TODO Yassine : ajouter des synonymes
}

# Branche de chaque classe -> sert à choisir l'attribut numérique par défaut
BRANCHE = {
    **dict.fromkeys(["SourceProduction", "SourceRenouvelable", "CentraleSolaire",
                     "ParcEolien", "SourceFossile"], "production"),
    **dict.fromkeys(["SystemeStockage", "Batterie", "StockageHydrogene"], "stockage"),
    **dict.fromkeys(["BatimentConsommateur", "BatimentResidentiel", "BatimentCommercial",
                     "BatimentIndustriel", "GrosConsommateur",
                     "BatimentAlimenteRenouvelable"], "consommation"),
    **dict.fromkeys(["InfrastructureReseau", "LigneElectrique", "LigneTransport",
                     "LigneDistribution", "PosteTransformation"], "reseau"),
}

# ---------------------------------------------------------------------------
# 2. ATTRIBUTS NUMÉRIQUES (DataProperties)
# ---------------------------------------------------------------------------
ATTRIBUT_PAR_BRANCHE = {
    "production": "puissanceMW",
    "stockage": "capaciteStockageMWh",
    "consommation": "consommationKWh",
    "reseau": "tensionKV",
}

# unité écrite dans la question -> attribut
UNITES = {
    "mw": "puissanceMW", "mégawatt": "puissanceMW", "megawatt": "puissanceMW",
    "mwh": "capaciteStockageMWh",
    "kwh": "consommationKWh",
    "kv": "tensionKV", "kilovolt": "tensionKV",
}

# mots (lemmes) qui indiquent l'attribut concerné
MOTS_ATTRIBUT = {
    "puissanceMW": ["puissance", "puissant", "produire", "production", "produit"],
    "capaciteStockageMWh": ["capacité", "stocker"],
    "consommationKWh": ["consommation", "consommer", "énergivore"],
    "tensionKV": ["tension"],
}

# ---------------------------------------------------------------------------
# 3. RELATIONS (ObjectProperties) : lemme du verbe -> propriété
#    sujet = classe du domaine ; objet = classe du codomaine
# ---------------------------------------------------------------------------
RELATIONS = {
    # Mehdi
    "alimenter": {"propriete": "alimente", "sujet": "SourceProduction",
                  "objet": "BatimentConsommateur"},
    "fournir": {"propriete": "alimente", "sujet": "SourceProduction",
                "objet": "BatimentConsommateur"},
    # Ahmed Amine : « Quels bâtiments dépendent de la centrale de Radès ? »
    # -> relation inverse estAlimentePar (le bâtiment est le sujet du verbe)
    "approvisionner": {"propriete": "alimente", "sujet": "SourceProduction",
                       "objet": "BatimentConsommateur"},
    "dependre": {"propriete": "estAlimentePar", "sujet": "BatimentConsommateur",
                 "objet": "SourceProduction"},
    # TODO Elyess : "stocker" -> stockeEnergieDe (sujet SystemeStockage, objet SourceProduction)
    # TODO Yassine : "relier" / "connecter" -> relie (sujet LigneElectrique, objet ComposantSmartGrid)
}

# ---------------------------------------------------------------------------
# 4. COMPARATEURS (filtrage numérique)
# ---------------------------------------------------------------------------
COMPARATEURS = [  # (expression, opérateur SPARQL) — les plus longues d'abord
    ("supérieure ou égale à", ">="), ("supérieur ou égal à", ">="),
    ("inférieure ou égale à", "<="), ("inférieur ou égal à", "<="),
    ("plus de", ">"), ("supérieure à", ">"), ("supérieur à", ">"), ("au-delà de", ">"),
    ("au dela de", ">"), ("dépasse", ">"), ("dépassant", ">"), ("au moins", ">="),
    ("moins de", "<"), ("inférieure à", "<"), ("inférieur à", "<"), ("en dessous de", "<"),
    ("au plus", "<="), ("au maximum", "<="), ("égale à", "="), ("égal à", "="),
    ("exactement", "="), (">=", ">="), ("<=", "<="), (">", ">"), ("<", "<"), ("=", "="),
]

MOTS_COMPTAGE = ["combien", "nombre"]
# agrégats sur l'attribut numérique (« consommation totale », « puissance moyenne »)
MOTS_SOMME = ["total", "totale", "somme", "cumulé", "cumulée"]
MOTS_MOYENNE = ["moyenne", "moyen"]
MOTS_MAX = ["le plus", "la plus", "les plus", "maximum", "max", "plus grand", "plus grande"]
MOTS_MIN = ["le moins", "la moins", "les moins", "minimum", "min", "plus petit", "plus petite",
            "plus faible"]
