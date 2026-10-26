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
