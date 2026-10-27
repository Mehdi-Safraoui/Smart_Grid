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
  "Nombre d'éléments par zone": `SELECT ?zone (COUNT(?x) AS ?nombre) WHERE {
  ?x sg:estSitueDans ?zone .
} GROUP BY ?zone ORDER BY DESC(?nombre)`,
  "Puissance totale par zone": `SELECT ?zone (SUM(?p) AS ?totalMW) WHERE {
  ?s sg:puissanceMW ?p ; sg:estSitueDans ?zone .
} GROUP BY ?zone`,
  "Recherche par nom (contient « tozeur »)": `SELECT ?x WHERE {
  ?x a ?type .
  FILTER(CONTAINS(LCASE(STR(?x)), "tozeur"))
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
