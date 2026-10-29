// =====================================================================
// Page d'accueil : statistiques + assistant NLP (question -> SPARQL)
// =====================================================================
const EXEMPLES = [
  "Quelles sources produisent plus de 50 MW ?",
  "Qui alimente l'usine de Sfax ?",
  "Quelle est la source la plus puissante ?",
  "Combien de bâtiments y a-t-il à Tunis ?",
  "Quels sont les gros consommateurs ?",
  "Liste les sources renouvelables à Tozeur",
  "Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ?",
  "Quel stockage a la plus grande capacité ?",
];

async function chargerStats() {
  try {
    const s = await api("/api/stats");
    const cartes = [
      ["Sources de production", s.production],
      ["Systèmes de stockage", s.stockage],
      ["Bâtiments consommateurs", s.consommation],
      ["Éléments du réseau", s.reseau],
      ["MW renouvelables", s.puissance_mw.SourceRenouvelable ?? 0],
      ["MW fossiles", s.puissance_mw.SourceFossile ?? 0],
    ];
    document.getElementById("stats").innerHTML = cartes
      .map(([l, v]) => `<div class="stat"><div class="value">${v}</div><div class="label">${l}</div></div>`).join("");
  } catch (e) {
    toast("Backend injoignable : lancez uvicorn (voir README)", true);
  }
}

function afficherReponse(r) {
  const tokens = r.analyse.tokens.map((t) => {
    const estEntite = r.analyse.entites.some((e) => e.texte.split(/\s+/).includes(t.texte));
    return `<span class="token ${estEntite ? "ent" : ""}"><b>${echapper(t.texte)}</b><small>${echapper(t.lemme)} · ${t.pos}</small></span>`;
  }).join("");
  const entites = r.analyse.entites.map((e) => `<span class="badge">${e.type} : ${echapper(e.valeur)}</span>`).join(" ") || "aucune";
  const filtres = r.analyse.filtres.map((f) => `${f.op} ${f.valeur} ${f.unite ?? ""}`).join(", ") || "aucun";
  const resultat = r.erreur
    ? `<p style="color:var(--red)">${echapper(r.erreur)}</p>`
    : tableau(r.resultats);

  const bloc = document.createElement("div");
  bloc.className = "answer";
  bloc.innerHTML = `
    <div class="q">❓ ${echapper(r.question)}</div>
    ${resultat}
    <details>
      <summary>Voir l'analyse NLP et la requête SPARQL générée</summary>
      <p><b>1. Tokens, lemmes et POS (spaCy)</b></p><div class="tokens">${tokens}</div>
      <p><b>2. Entités reconnues :</b> ${entites}<br>
         <b>Filtres :</b> ${filtres} &nbsp; <b>Attribut :</b> ${r.analyse.attribut ?? "—"}<br>
         <b>3. Intention :</b> ${r.analyse.intention}${r.analyse.relation ? " (relation " + r.analyse.relation + ")" : ""}</p>
      <p><b>4. Requête SPARQL</b></p><pre>${echapper(r.sparql || "—")}</pre>
    </details>`;
  document.getElementById("reponses").prepend(bloc);
}

async function poser(question) {
  try {
    afficherReponse(await api("/api/ask", { method: "POST", body: { question } }));
  } catch (e) {
    toast(e.message, true);
  }
}

document.getElementById("chat-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const champ = document.getElementById("question");
  poser(champ.value.trim());
  champ.value = "";
});

document.getElementById("examples").innerHTML = EXEMPLES.map((q) => `<button type="button">${q}</button>`).join("");
document.querySelectorAll("#examples button").forEach((b) => b.addEventListener("click", () => poser(b.textContent)));

chargerStats();
