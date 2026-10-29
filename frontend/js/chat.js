// =====================================================================
// Page d'accueil : statistiques + assistant NLP (question -> SPARQL)
// =====================================================================
// Questions d'exemple, rangées par branche : chaque membre complète SA ligne
// avec des questions dont il a vérifié qu'elles fonctionnent (voir les tests).
const EXEMPLES = {
  "⚡ Production": [
    "Quelle est la source la plus puissante ?",
    "Quels parcs éoliens produisent plus de 60 MW ?",
    "Quelle est la puissance installée par zone ?",
    "Combien de sources par type ?",
    "Qui alimente l'usine de Sfax ?",
  ],
  "🔋 Stockage": [            // Mohamed Elyess
    "Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ?",
    "Quel stockage a la plus grande capacité ?",
    "Combien de batteries y a-t-il ?",
  ],
  "🏢 Consommation": [        // Ahmed Amine
    "Quels sont les gros consommateurs ?",
    "Quelle est la consommation totale des bâtiments à Tunis ?",
    "Quels bâtiments dépendent de la centrale de Radès ?",
  ],
  "🔌 Réseau": [              // Yassine
    "Quelles lignes ont une tension supérieure à 100 kV ?",
    "Quelles lignes sont reliées au poste de Sousse ?",
    "Qu'est-ce que relie la ligne Tozeur Sfax ?",
  ],
};

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

// Un clic sur un exemple REMPLIT le champ (sans envoyer) : l'utilisateur peut
// modifier la question (ex. changer « 60 MW » en « 90 MW ») puis cliquer sur Demander.
document.getElementById("examples").innerHTML = Object.entries(EXEMPLES).map(([theme, questions]) => `
  <div class="example-row">
    <span class="example-theme">${theme}</span>
    <div class="example-buttons">${questions.map((q) => `<button type="button">${echapper(q)}</button>`).join("")}</div>
  </div>`).join("");
document.querySelectorAll("#examples button").forEach((b) => b.addEventListener("click", () => {
  const champ = document.getElementById("question");
  champ.value = b.textContent;
  champ.focus();
}));

chargerStats();
