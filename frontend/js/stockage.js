// =====================================================================
// Page STOCKAGE (Mohamed Elyess)
// CRUD : liste + filtres (GET), ajout (POST), modification (PUT), suppression (DELETE)
// + statistiques par technologie + raisonneur HermiT (valeur ajoutée)
// =====================================================================
const filtres = document.getElementById("filtres");
const form = document.getElementById("form-stockage");
let enEdition = null;   // nom du stockage en cours de modification

const NOMS_TYPES = { Batterie: "Batterie", StockageHydrogene: "Stockage hydrogène" };
const nomType = (v) => NOMS_TYPES[v] || lisible(v);
const badgeType = (v) => `<span class="badge${v === "StockageHydrogene" ? " h2" : ""}">${nomType(v)}</span>`;

const COLONNES = [
  { cle: "stockage", titre: "Nom" },
  { cle: "type", titre: "Type", rendu: badgeType },
  { cle: "capacite", titre: "Capacité (MWh)" },
  { cle: "zone", titre: "Zone" },
  { cle: "stocke", titre: "Stocke l'énergie de" },
  { cle: "alimente", titre: "Alimente" },
];

// ---------------------------------------------------------------- READ
async function charger() {
  const params = Object.fromEntries(new FormData(filtres));
  try {
    const lignes = await api("/api/stockage", { params });
    document.getElementById("liste").innerHTML = tableau(lignes, COLONNES, (s) => `
      <button class="small secondary" onclick="editer('${s.stockage}')">Modifier</button>
      <button class="small danger" onclick="supprimer('${s.stockage}')">Supprimer</button>`);
  } catch (e) {
    toast(e.message, true);
  }
  chargerStats();
}

// Statistiques : COUNT / SUM / AVG par type (GROUP BY)
async function chargerStats() {
  try {
    const stats = await api("/api/stockage/statistiques");
    const total = stats.reduce((t, s) => t + s.totalMWh, 0);
    const nombre = stats.reduce((t, s) => t + s.nombre, 0);
    document.getElementById("stats").innerHTML =
      `<div class="stat"><div class="value">${nombre}</div><div class="label">Systèmes de stockage</div>
         <div class="detail">${total.toLocaleString("fr-FR")} MWh au total</div></div>` +
      stats.map((s) => `
        <div class="stat"><div class="value">${s.totalMWh.toLocaleString("fr-FR")} <small style="font-size:14px">MWh</small></div>
          <div class="label">${nomType(s.type)} · ${s.nombre} système(s)</div>
          <div class="detail">moyenne ${s.moyenneMWh.toFixed(1)} MWh</div>
          <div class="jauge"><span style="width:${total ? (100 * s.totalMWh) / total : 0}%"></span></div>
        </div>`).join("");
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- CREATE / UPDATE
const sourcesChoisies = () => [...form.stocke.selectedOptions].map((o) => o.value);

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const d = Object.fromEntries(new FormData(form));
  try {
    if (enEdition) {
      await api(`/api/stockage/${enEdition}`, {
        method: "PUT",
        body: { capacite: Number(d.capacite), zone: d.zone, stocke: sourcesChoisies() },
      });
      toast(`${enEdition} modifié`);
    } else {
      await api("/api/stockage", {
        method: "POST",
        body: { nom: d.nom, type: d.type, capacite: Number(d.capacite), zone: d.zone,
                stocke: sourcesChoisies(), alimente: d.alimente ? [d.alimente] : [] },
      });
      toast(`${d.nom} ajouté`);
    }
    annuler();
    charger();
  } catch (e) {
    toast(e.message, true);
  }
});

async function editer(nom) {
  const s = await api(`/api/stockage/${nom}`);
  enEdition = nom;
  form.nom.value = nom;
  form.nom.disabled = form.type.disabled = form.alimente.disabled = true;
  form.type.value = s.type;
  form.capacite.value = s.capacite;
  form.zone.value = s.zone;
  const stockees = (s.stocke || "").split(", ");
  [...form.stocke.options].forEach((o) => (o.selected = stockees.includes(o.value)));
  document.getElementById("form-titre").textContent = `Modifier ${lisible(nom)}`;
  document.getElementById("btn-enregistrer").textContent = "Enregistrer";
  document.getElementById("btn-annuler").hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function annuler() {
  enEdition = null;
  form.reset();
  form.nom.disabled = form.type.disabled = form.alimente.disabled = false;
  document.getElementById("form-titre").textContent = "Ajouter un système de stockage";
  document.getElementById("btn-enregistrer").textContent = "Ajouter";
  document.getElementById("btn-annuler").hidden = true;
}
document.getElementById("btn-annuler").addEventListener("click", annuler);

// ---------------------------------------------------------------- DELETE
async function supprimer(nom) {
  if (!confirm(`Supprimer ${lisible(nom)} ?`)) return;
  try {
    await api(`/api/stockage/${nom}`, { method: "DELETE" });
    toast(`${nom} supprimé`);
    charger();
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- VALEUR AJOUTÉE : HermiT
const zoneRaisonnement = document.getElementById("raisonnement");
const btnEnregistrer = document.getElementById("btn-enregistrer-deductions");

async function raisonner(params = {}) {
  zoneRaisonnement.innerHTML = '<p class="empty">HermiT raisonne… (quelques secondes)</p>';
  btnEnregistrer.disabled = true;
  try {
    const r = await api("/api/stockage/raisonner", { method: "POST", params });
    let html = `<div class="verdict ${r.coherente ? "ok" : "ko"}">${r.coherente ? "✅" : "❌"} ${echapper(r.message)}
                <small style="font-weight:400">(${r.duree_s} s)</small></div>`;
    if (r.coherente) {
      if (r.enregistrees) {
        html += `<p>${r.enregistrees} déduction(s) enregistrée(s) dans le serveur SPARQL : elles sont maintenant
                 visibles dans les pages, la console et l'assistant.</p>`;
      } else if (r.deductions.length) {
        html += `<h3>${r.deductions.length} nouvelle(s) déduction(s), pas encore dans la base</h3>` +
          tableau(r.deductions, [
            { cle: "individu", titre: "Individu" },
            { cle: "propriete", titre: "Propriété" },
            { cle: "valeur", titre: "Valeur déduite", rendu: (v) => `<b>${echapper(lisible(v))}</b>` },
            { cle: "genre", titre: "Origine", rendu: (v) => v === "classe"
                ? "classe définie / domaine" : "propriété inverse" },
          ]);
        btnEnregistrer.disabled = false;
      } else {
        html += '<p class="hint">Aucune nouvelle déduction : la base est déjà à jour. Ajoutez par exemple un '
              + "bâtiment de plus de 100 000 kWh alimenté par une source renouvelable, puis relancez.</p>";
      }
      html += '<div class="definies">' + Object.entries(r.classes_definies).map(([c, membres]) =>
        `<div><b>${lisible(c)}</b> (déduite par HermiT)<br>${membres.map(lisible).join(", ") || "—"}</div>`).join("") + "</div>";
    }
    zoneRaisonnement.innerHTML = html;
    if (r.enregistrees) charger();
  } catch (e) {
    zoneRaisonnement.innerHTML = "";
    toast(e.message, true);
  }
}
document.getElementById("btn-raisonner").addEventListener("click", () => raisonner());
btnEnregistrer.addEventListener("click", () => raisonner({ enregistrer: true }));
document.getElementById("btn-incoherence").addEventListener("click", () => raisonner({ tester_incoherence: true }));

// ---------------------------------------------------------------- initialisation
filtres.addEventListener("submit", (ev) => { ev.preventDefault(); charger(); });
filtres.addEventListener("reset", () => setTimeout(charger));

(async () => {
  await remplirZones(document.getElementById("filtre-zone"));
  await remplirZones(document.getElementById("form-zone"), false);
  const [sources, batiments] = await Promise.all([api("/api/production"), api("/api/consommation")]);
  const opt = (v) => `<option value="${v}">${lisible(v)}</option>`;
  document.getElementById("filtre-source").innerHTML = '<option value="">Toutes</option>' +
    sources.map((s) => opt(s.source)).join("");
  document.getElementById("form-source").innerHTML = sources.map((s) => opt(s.source)).join("");
  document.getElementById("form-batiment").innerHTML = '<option value="">— aucun —</option>' +
    batiments.map((b) => opt(b.batiment)).join("");
  charger();
})();
