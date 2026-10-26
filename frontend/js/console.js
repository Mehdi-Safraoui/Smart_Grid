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
  "Recherche par nom (contient « tozeur »)": `SELECT ?x WHERE {
  ?x a ?type .
  FILTER(CONTAINS(LCASE(STR(?x)), "tozeur"))
}`,
  "Hiérarchie des classes": `SELECT ?classe ?parent WHERE {
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
