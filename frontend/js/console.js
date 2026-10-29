// =====================================================================
// Console SPARQL (lecture seule) — utile pour la démo des requêtes
// Chaque membre peut ajouter ici les requêtes de sa branche.
// =====================================================================
const EXEMPLES_SPARQL = {
  "Toutes les sources et leur puissance": `SELECT ?source ?puissance WHERE {
  ?source a/rdfs:subClassOf* sg:SourceProduction ;
          sg:puissanceMW ?puissance .
} ORDER BY DESC(?puissance)`,
  "Sources renouvelables de plus de 20 MW": `SELECT ?source ?puissance WHERE {
  ?source a/rdfs:subClassOf* sg:SourceRenouvelable ;
          sg:puissanceMW ?puissance .
  FILTER(?puissance > 20)
}`,
  "Qui alimente quel bâtiment": `SELECT ?source ?batiment WHERE {
  ?source sg:alimente ?batiment .
}`,
  "Production : part renouvelable par zone (IF + SUM)": `SELECT ?zone (SUM(?p) AS ?totalMW)
       (SUM(IF(?vert, ?p, 0)) AS ?renouvelableMW)
       (ROUND(100 * SUM(IF(?vert, ?p, 0)) / SUM(?p)) AS ?pourcentage)
WHERE {
  { SELECT DISTINCT ?s ?p ?zone WHERE {
      ?s a/rdfs:subClassOf* sg:SourceProduction ;
         sg:puissanceMW ?p ; sg:estSitueDans ?zone . } }
  BIND(EXISTS { ?s a/rdfs:subClassOf* sg:SourceRenouvelable } AS ?vert)
} GROUP BY ?zone ORDER BY DESC(?totalMW)`,
  "Production : sources dont l'énergie n'est stockée nulle part (FILTER NOT EXISTS)": `SELECT ?source ?puissance ?zone WHERE {
  ?source a/rdfs:subClassOf* sg:SourceProduction ;
          sg:puissanceMW ?puissance ; sg:estSitueDans ?zone .
  FILTER NOT EXISTS { ?stockage sg:stockeEnergieDe ?source }
} ORDER BY DESC(?puissance)`,
  "Production : sources renouvelables plus puissantes que la moyenne (sous-requête AVG)": `SELECT ?source ?puissance ?moyenne WHERE {
  { SELECT (AVG(?p) AS ?moyenne) WHERE {
      ?s a/rdfs:subClassOf* sg:SourceRenouvelable ; sg:puissanceMW ?p . } }
  ?source a/rdfs:subClassOf* sg:SourceRenouvelable ;
          sg:puissanceMW ?puissance .
  FILTER(?puissance > ?moyenne)
} ORDER BY DESC(?puissance)`,
  "Consommation : total, moyenne et max par type de bâtiment": `SELECT ?type (COUNT(?b) AS ?nombre) (SUM(?c) AS ?totalKWh)
       (AVG(?c) AS ?moyenneKWh) (MAX(?c) AS ?maxKWh) WHERE {
  VALUES ?type { sg:BatimentResidentiel sg:BatimentCommercial sg:BatimentIndustriel }
  ?b a ?type ;
     sg:consommationKWh ?c .
} GROUP BY ?type ORDER BY DESC(?totalKWh)`,
  "Consommation : gros consommateurs (FILTER, sans raisonneur)": `SELECT DISTINCT ?batiment ?consommation ?zone WHERE {
  ?batiment a/rdfs:subClassOf* sg:BatimentConsommateur ;
            sg:consommationKWh ?consommation ;
            sg:estSitueDans ?zone .
  FILTER(?consommation >= 100000)
} ORDER BY DESC(?consommation)`,
  "Consommation : bâtiments sans aucune source renouvelable (FILTER NOT EXISTS)": `SELECT ?batiment ?consommation
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?src), "#"); separator=", ") AS ?alimentePar) WHERE {
  ?batiment a/rdfs:subClassOf* sg:BatimentConsommateur ;
            sg:consommationKWh ?consommation ;
            sg:estAlimentePar ?src .
  FILTER NOT EXISTS {
    ?batiment sg:estAlimentePar ?verte .
    ?verte a/rdfs:subClassOf* sg:SourceRenouvelable .
  }
} GROUP BY ?batiment ?consommation`,
  "Consommation : part de chaque zone dans le total (sous-requête)": `SELECT ?zone ?totalZone ?totalGlobal
       (ROUND(100 * ?totalZone / ?totalGlobal) AS ?pourcentage) WHERE {
  # domaine de consommationKWh = BatimentConsommateur : inutile de tester le type
  { SELECT ?zone (SUM(?c) AS ?totalZone) WHERE {
      ?b sg:consommationKWh ?c ; sg:estSitueDans ?zone .
    } GROUP BY ?zone }
  { SELECT (SUM(?c2) AS ?totalGlobal) WHERE { ?b2 sg:consommationKWh ?c2 } }
} ORDER BY DESC(?totalZone)`,
  "Nombre d'éléments par zone": `SELECT ?zone (COUNT(?x) AS ?nombre) WHERE {
  ?x sg:estSitueDans ?zone .
} GROUP BY ?zone ORDER BY DESC(?nombre)`,
  "Puissance totale par zone": `SELECT ?zone (SUM(?p) AS ?totalMW) WHERE {
  ?s sg:puissanceMW ?p ; sg:estSitueDans ?zone .
} GROUP BY ?zone`,
  "Recherche par nom (contient « tozeur »)": `SELECT DISTINCT ?x WHERE {
  ?x a owl:NamedIndividual .
  FILTER(CONTAINS(LCASE(STR(?x)), "tozeur"))
}`,
  "Réseau : nombre de lignes et tension moyenne par type": `SELECT ?type (COUNT(?ligne) AS ?nombre)
       (AVG(?tension) AS ?tensionMoyenne) (MAX(?tension) AS ?tensionMax) WHERE {
  VALUES ?type { sg:LigneTransport sg:LigneDistribution }
  ?ligne a ?type ;
         sg:tensionKV ?tension .
} GROUP BY ?type`,
  "Réseau : lignes raccordées à chaque poste": `SELECT ?poste (COUNT(DISTINCT ?ligne) AS ?nbLignes)
       (GROUP_CONCAT(DISTINCT STRAFTER(STR(?ligne), "#"); separator=", ") AS ?lignes) WHERE {
  ?poste a sg:PosteTransformation .
  ?ligne sg:relie ?poste .
} GROUP BY ?poste ORDER BY DESC(?nbLignes)`,
  "Réseau : parcours source → ligne → poste → ligne → bâtiment": `SELECT DISTINCT ?source ?transport ?poste ?distribution ?batiment WHERE {
  ?source a/rdfs:subClassOf* sg:SourceProduction .
  ?transport sg:relie ?source , ?poste .
  ?poste a sg:PosteTransformation .
  ?distribution a sg:LigneDistribution ;
                sg:relie ?poste , ?batiment .
  ?batiment a/rdfs:subClassOf* sg:BatimentConsommateur .
}`,
  "Stockage : capacité totale et moyenne par technologie": `SELECT ?type (COUNT(?s) AS ?nombre)
       (SUM(?c) AS ?totalMWh) (AVG(?c) AS ?moyenneMWh) WHERE {
  ?s a ?type ; sg:capaciteStockageMWh ?c .
  FILTER(?type IN (sg:Batterie, sg:StockageHydrogene))
} GROUP BY ?type ORDER BY DESC(?totalMWh)`,
  "Stockage : énergie stockée par source (renouvelable ou non)": `SELECT ?source ?categorie (COUNT(?s) AS ?nbStockages)
       (SUM(?c) AS ?capaciteMWh) WHERE {
  ?s sg:stockeEnergieDe ?source ; sg:capaciteStockageMWh ?c .
  OPTIONAL { ?source a/rdfs:subClassOf* sg:SourceRenouvelable . BIND("renouvelable" AS ?r) }
  BIND(COALESCE(?r, "fossile") AS ?categorie)
} GROUP BY ?source ?categorie ORDER BY DESC(?capaciteMWh)`,
  "Stockage : batteries de plus de 20 MWh hors zone de leur source": `SELECT ?stockage ?capacite ?zoneStockage ?source ?zoneSource WHERE {
  ?stockage a sg:Batterie ; sg:capaciteStockageMWh ?capacite ;
            sg:estSitueDans ?zoneStockage ; sg:stockeEnergieDe ?source .
  ?source sg:estSitueDans ?zoneSource .
  FILTER(?capacite >= 20 && ?zoneStockage != ?zoneSource)
}`,
  "Hiérarchie des classes":`SELECT ?classe ?parent WHERE {
  ?classe rdfs:subClassOf ?parent .
  FILTER(isIRI(?parent))
} ORDER BY ?parent`,
};

const select = document.getElementById("exemples");
const zone = document.getElementById("requete");
select.innerHTML = Object.keys(EXEMPLES_SPARQL).map((k) => `<option>${k}</option>`).join("");
select.addEventListener("change", () => (zone.value = EXEMPLES_SPARQL[select.value]));
zone.value = EXEMPLES_SPARQL[select.value];

document.getElementById("executer").addEventListener("click", async () => {
  try {
    const lignes = await api("/api/sparql", { method: "POST", body: { requete: zone.value } });
    document.getElementById("resultat").innerHTML = `<p>${lignes.length} résultat(s)</p>` + tableau(lignes);
  } catch (e) {
    toast(e.message, true);
  }
});
