// =====================================================================
// Page CONSOMMATION (Ahmed Amine)
// CRUD : liste + filtres (GET), ajout (POST), modification (PUT), suppression (DELETE)
// + indicateurs, reclassement SPARQL et carte Leaflet (valeur ajoutée)
// =====================================================================
const filtres = document.getElementById("filtres");
const form = document.getElementById("form-batiment");
let enEdition = null;   // nom du bâtiment en cours de modification

const kwh = (v) => (v == null ? "" : Number(v).toLocaleString("fr-FR"));
const TYPES = { BatimentResidentiel: "Résidentiel", BatimentCommercial: "Commercial", BatimentIndustriel: "Industriel" };

const COLONNES = [
  { cle: "batiment", titre: "Bâtiment" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge type">${TYPES[v] || lisible(v)}</span>` },
  { cle: "consommation", titre: "Consommation (kWh)", rendu: kwh },
  { cle: "zone", titre: "Zone" },
  { cle: "alimentePar", titre: "Alimenté par" },
  { cle: "gros", titre: "Classes déduites", rendu: (_, b) =>
      (b.gros ? '<span class="badge gros">Gros consommateur</span> ' : "") +
      (b.renouvelable ? '<span class="badge vert">Renouvelable</span>' : "") },
];

// ---------------------------------------------------------------- READ
async function charger() {
  const params = Object.fromEntries(new FormData(filtres));
  try {
    const batiments = await api("/api/consommation", { params });
    document.getElementById("liste").innerHTML = tableau(batiments, COLONNES, (b) => `
      <button class="small secondary" onclick="editer('${b.batiment}')">Modifier</button>
      <button class="small danger" onclick="supprimer('${b.batiment}')">Supprimer</button>`);
  } catch (e) {
    toast(e.message, true);
  }
  chargerIndicateurs();
  chargerCarte();
}

async function chargerIndicateurs() {
  const tous = await api("/api/consommation");
  const total = tous.reduce((s, b) => s + (b.consommation || 0), 0);
  const gros = tous.filter((b) => b.gros).length;
  const verts = tous.filter((b) => b.renouvelable).length;
  const part = tous.length ? Math.round((100 * verts) / tous.length) : 0;
  document.getElementById("kpis").innerHTML = [
    [tous.length, "bâtiments"],
    [`${kwh(Math.round(total / 1000))} MWh`, "consommation totale"],
    [gros, "gros consommateurs (≥ 100 000 kWh)"],
    [`${part} %`, `alimentés en renouvelable (${verts})`],
  ].map(([v, l]) => `<div class="stat"><div class="value">${v}</div><div class="label">${l}</div></div>`).join("");
}

// ---------------------------------------------------------------- CREATE / UPDATE
const fournisseursChoisis = () => [...form.alimente_par.selectedOptions].map((o) => o.value);

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const d = Object.fromEntries(new FormData(form));
  try {
    if (enEdition) {
      const r = await api(`/api/consommation/${enEdition}`, {
        method: "PUT",
        body: { consommation: Number(d.consommation), zone: d.zone, alimente_par: fournisseursChoisis(),
                type: d.type, nouveau_nom: d.nom !== enEdition ? d.nom : null },
      });
      toast(`${r.nom} modifié`);
    } else {
      await api("/api/consommation", {
        method: "POST",
        body: { nom: d.nom, type: d.type, consommation: Number(d.consommation), zone: d.zone,
                alimente_par: fournisseursChoisis() },
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
  const b = await api(`/api/consommation/${nom}`);
  const actuels = (b.alimentePar || "").split(", ");
  enEdition = nom;
  form.nom.value = nom;
  form.type.value = b.type;   // nom et type sont modifiables
  form.consommation.value = b.consommation;
  form.zone.value = b.zone;
  [...form.alimente_par.options].forEach((o) => (o.selected = actuels.includes(o.value)));
  document.getElementById("form-titre").textContent = `Modifier ${lisible(nom)}`;
  document.getElementById("btn-enregistrer").textContent = "Enregistrer";
  document.getElementById("btn-annuler").hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function annuler() {
  enEdition = null;
  form.reset();
  form.nom.disabled = form.type.disabled = false;
  document.getElementById("form-titre").textContent = "Ajouter un bâtiment";
  document.getElementById("btn-enregistrer").textContent = "Ajouter";
  document.getElementById("btn-annuler").hidden = true;
}
document.getElementById("btn-annuler").addEventListener("click", annuler);

// ---------------------------------------------------------------- DELETE
async function supprimer(nom) {
  if (!confirm(`Supprimer ${lisible(nom)} ?`)) return;
  try {
    await api(`/api/consommation/${nom}`, { method: "DELETE" });
    toast(`${nom} supprimé`);
    charger();
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- classes définies
document.getElementById("btn-classer").addEventListener("click", async () => {
  try {
    const n = await api("/api/consommation/classer", { method: "POST" });
    toast(`Reclassement : ${n.GrosConsommateur || 0} gros consommateurs, ` +
          `${n.BatimentAlimenteRenouvelable || 0} bâtiments alimentés en renouvelable`);
    charger();
  } catch (e) {
    toast(e.message, true);
  }
});

// ---------------------------------------------------------------- carte (valeur ajoutée)
// Coordonnées des chefs-lieux : les zones de l'ontologie n'ont pas de latitude / longitude
const COORDONNEES = {
  Zone_Tunis: [36.8065, 10.1815], Zone_Nabeul: [36.4561, 10.7376], Zone_Tozeur: [33.9197, 8.1335],
  Zone_Sfax: [34.7406, 10.7603], Zone_Kairouan: [35.6781, 10.0963], Zone_Sousse: [35.8256, 10.6360],
  Zone_Bizerte: [37.2744, 9.8739], Zone_Gabes: [33.8815, 10.0982], Zone_Monastir: [35.7643, 10.8113],
  Zone_Gafsa: [34.4250, 8.7842], Zone_Ariana: [36.8625, 10.1956], Zone_BenArous: [36.7531, 10.2189],
  Zone_Medenine: [33.3549, 10.5055], Zone_Kebili: [33.7044, 8.9690], Zone_Beja: [36.7256, 9.1817],
  Zone_Jendouba: [36.5011, 8.7802], Zone_Kasserine: [35.1676, 8.8365], Zone_Mahdia: [35.5047, 11.0622],
};
const BRANCHES = {
  SourceProduction: "⚡ Production", SystemeStockage: "🔋 Stockage",
  BatimentConsommateur: "🏢 Consommation", InfrastructureReseau: "🔌 Réseau",
};
let carte, calque;

async function chargerCarte() {
  const [elements, bilan] = await Promise.all([api("/api/consommation/carte"),
                                               api("/api/consommation/par-zone")]);
  afficherBilan(bilan);
  if (typeof L === "undefined") {   // Leaflet indisponible (pas d'Internet)
    document.getElementById("carte").innerHTML = '<p class="empty">Carte indisponible hors ligne</p>';
    return;
  }
  if (!carte) {
    carte = L.map("carte", { scrollWheelZoom: false }).setView([34.6, 9.7], 6);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18, attribution: "© OpenStreetMap",
    }).addTo(carte);
  }
  if (calque) calque.remove();
  calque = L.layerGroup().addTo(carte);

  const parZone = {};
  elements.forEach((e) => ((parZone[e.zone] ||= []).push(e)));
  const stats = Object.fromEntries(bilan.map((z) => [z.zone, z]));
  const max = Math.max(1, ...bilan.map((z) => z.total || 0));

  Object.entries(parZone).forEach(([zone, liste]) => {
    const pos = COORDONNEES[zone];
    if (!pos) return;
    const z = stats[zone];
    const couleur = !z ? "#8a99a8" : z.nbRenouvelable / z.nombre >= 0.5 ? "#1e9e6a" : "#f2a900";
    const rayon = z ? 9 + 21 * Math.sqrt((z.total || 0) / max) : 7;
    const groupes = Object.entries(BRANCHES).map(([cle, titre]) => {
      const noms = liste.filter((e) => e.branche === cle);
      if (!noms.length) return "";
      return `<b>${titre}</b><ul>${noms.map((e) => `<li>${echapper(lisible(e.element))}` +
        (e.consommation != null ? ` <small>(${kwh(e.consommation)} kWh)</small>` : "") + "</li>").join("")}</ul>`;
    }).join("");
    const resume = z ? `<small>${z.nombre} bâtiment(s) · ${kwh(z.total)} kWh</small><br>` : "";
    L.circleMarker(pos, { radius: rayon, color: couleur, fillColor: couleur, fillOpacity: 0.55, weight: 2 })
      .bindPopup(`<div class="popup"><h4>${echapper(lisible(zone))}</h4>${resume}${groupes}</div>`)
      .bindTooltip(lisible(zone))
      .addTo(calque);
  });
}

function afficherBilan(bilan) {
  document.getElementById("bilan").innerHTML = tableau(bilan, [
    { cle: "zone", titre: "Zone" },
    { cle: "nombre", titre: "Bât." },
    { cle: "total", titre: "Total (kWh)", rendu: kwh },
    { cle: "moyenne", titre: "Moy. (kWh)", rendu: (v) => kwh(Math.round(v)) },
    { cle: "nbRenouvelable", titre: "% renouv.", rendu: (v, z) => `${Math.round((100 * v) / z.nombre)} %` },
  ]);
}

// ---------------------------------------------------------------- initialisation
filtres.addEventListener("submit", (ev) => { ev.preventDefault(); charger(); });
filtres.addEventListener("reset", () => setTimeout(charger));

(async () => {
  await remplirZones(document.getElementById("filtre-zone"));
  await remplirZones(document.getElementById("form-zone"), false);
  const fournisseurs = await api("/api/consommation/fournisseurs");
  const options = (branche) => fournisseurs.filter((f) => f.branche === branche)
    .map((f) => `<option value="${f.element}">${lisible(f.element)}</option>`).join("");
  const groupes = `<optgroup label="Sources de production">${options("SourceProduction")}</optgroup>` +
                  `<optgroup label="Systèmes de stockage">${options("SystemeStockage")}</optgroup>`;
  document.getElementById("form-fournisseur").innerHTML = groupes;
  document.getElementById("filtre-fournisseur").innerHTML = '<option value="">Tous</option>' + groupes;
  charger();
})();
