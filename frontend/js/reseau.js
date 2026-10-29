// =====================================================================
// Page RESEAU (Yassine)
// CRUD : liste + filtres (GET), ajout (POST), modification (PUT), suppression (DELETE)
// Valeur ajoutée : export CSV de la liste + parcours de l'énergie (centrale -> bâtiment)
// =====================================================================
const filtres = document.getElementById("filtres");
const form = document.getElementById("form-element");
let enEdition = null;     // nom de l'élément en cours de modification
let derniereListe = [];   // pour l'export CSV

const COLONNES = [
  { cle: "element", titre: "Nom" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge">${lisible(v)}</span>` },
  { cle: "tension", titre: "Tension (kV)" },
  { cle: "zone", titre: "Zone" },
  { cle: "relie", titre: "Relie" },
];
const LIGNES = ["LigneTransport", "LigneDistribution"];

// ---------------------------------------------------------------- READ
async function charger() {
  const params = Object.fromEntries(new FormData(filtres));
  try {
    derniereListe = await api("/api/reseau", { params });
    document.getElementById("liste").innerHTML = tableau(derniereListe, COLONNES, (e) => `
      <button class="small secondary" onclick="editer('${e.element}')">Modifier</button>
      <button class="small danger" onclick="supprimer('${e.element}')">Supprimer</button>`);
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- CREATE / UPDATE
// Les champs tension / relie n'existent que pour une ligne
function majChampsLigne() {
  const ligne = LIGNES.includes(form.type.value);
  document.querySelectorAll(".champ-ligne").forEach((el) => (el.style.display = ligne ? "" : "none"));
  form.tension.required = form.relie1.required = form.relie2.required = ligne;
}
form.type.addEventListener("change", majChampsLigne);

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const d = Object.fromEntries(new FormData(form));
  const ligne = LIGNES.includes(form.type.value);
  const relie = [d.relie1, d.relie2, d.relie3].filter(Boolean);
  try {
    if (enEdition) {
      const body = { zone: d.zone };
      if (ligne) Object.assign(body, { tension: Number(d.tension), relie });
      await api(`/api/reseau/${enEdition}`, { method: "PUT", body });
      toast(`${enEdition} modifié`);
    } else {
      const body = { nom: d.nom, type: d.type, zone: d.zone };
      if (ligne) Object.assign(body, { tension: Number(d.tension), relie });
      await api("/api/reseau", { method: "POST", body });
      toast(`${d.nom} ajouté`);
    }
    annuler();
    await chargerComposants();
    charger();
  } catch (e) {
    toast(e.message, true);
  }
});

async function editer(nom) {
  const e = await api(`/api/reseau/${nom}`);
  enEdition = nom;
  form.nom.value = nom;
  form.nom.disabled = form.type.disabled = true;
  form.type.value = e.type;
  majChampsLigne();
  form.zone.value = e.zone;
  form.tension.value = e.tension ?? "";
  const relie = e.relie ? e.relie.split(", ") : [];
  [form.relie1, form.relie2, form.relie3].forEach((s, i) => (s.value = relie[i] || ""));
  document.getElementById("form-titre").textContent = `Modifier ${lisible(nom)}`;
  document.getElementById("btn-enregistrer").textContent = "Enregistrer";
  document.getElementById("btn-annuler").hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function annuler() {
  enEdition = null;
  form.reset();
  form.nom.disabled = form.type.disabled = false;
  majChampsLigne();
  document.getElementById("form-titre").textContent = "Ajouter un élément du réseau";
  document.getElementById("btn-enregistrer").textContent = "Ajouter";
  document.getElementById("btn-annuler").hidden = true;
}
document.getElementById("btn-annuler").addEventListener("click", annuler);

// ---------------------------------------------------------------- DELETE
async function supprimer(nom) {
  if (!confirm(`Supprimer ${lisible(nom)} ?`)) return;
  try {
    const r = await api(`/api/reseau/${nom}`, { method: "DELETE" });
    toast(`${nom} supprimé`);
    if (r.lignes_incompletes.length) {
      toast(`Attention : ${r.lignes_incompletes.map(lisible).join(", ")} relie(nt) moins de 2 éléments`, true);
    }
    await chargerComposants();
    charger();
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- VALEUR AJOUTÉE : export CSV
document.getElementById("btn-csv").addEventListener("click", () => {
  if (!derniereListe.length) return toast("Rien à exporter", true);
  const cellule = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [COLONNES.map((c) => cellule(c.titre)).join(";"),
    ...derniereListe.map((l) => COLONNES.map((c) => cellule(l[c.cle])).join(";"))].join("\r\n");
  // BOM UTF-8 + « ; » : s'ouvre directement dans Excel en français
  const url = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: "reseau.csv" });
  a.click();
  URL.revokeObjectURL(url);
});

// ---------------------------------------------------------------- VALEUR AJOUTÉE : parcours
document.getElementById("form-parcours").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const params = Object.fromEntries(new FormData(ev.target));
  const zone = document.getElementById("parcours");
  try {
    const etapes = await api("/api/reseau/parcours", { params });
    zone.innerHTML = '<div class="tokens">' + etapes.map((e) => `
      <span class="token"><b>${echapper(lisible(e.element))}</b>
        <small>${echapper(lisible(e.type))}${e.tension != null ? ` · ${e.tension} kV` : ""}</small></span>`)
      .join('<span style="align-self:center">→</span>') + "</div>";
  } catch (e) {
    zone.innerHTML = "";
    toast(e.message, true);
  }
});

// ---------------------------------------------------------------- initialisation
// Tous les composants du smart grid (pour relie, le filtre et le parcours)
async function chargerComposants() {
  const [sources, stockages, batiments, reseau] = await Promise.all([
    api("/api/production"), api("/api/stockage"), api("/api/consommation"), api("/api/reseau"),
  ]);
  const noms = [...new Set([...sources.map((x) => x.source), ...stockages.map((x) => x.stockage),
    ...batiments.map((x) => x.batiment), ...reseau.map((x) => x.element)])].sort();
  const options = (vide) => (vide !== null ? `<option value="">${vide}</option>` : "") +
    noms.map((n) => `<option value="${n}">${lisible(n)}</option>`).join("");
  const remplir = (select, vide) => {
    const avant = select.value;
    select.innerHTML = options(vide);
    select.value = noms.includes(avant) ? avant : select.options[0]?.value ?? "";
  };
  remplir(document.getElementById("filtre-relie"), "Tous");
  document.querySelectorAll(".form-relie").forEach((s) => remplir(s, "— choisir —"));
  remplir(document.getElementById("parcours-depart"), null);
  remplir(document.getElementById("parcours-arrivee"), null);
}

filtres.addEventListener("submit", (ev) => { ev.preventDefault(); charger(); });
filtres.addEventListener("reset", () => setTimeout(charger));

(async () => {
  await remplirZones(document.getElementById("filtre-zone"));
  await remplirZones(document.getElementById("form-zone"), false);
  await chargerComposants();
  // exemple du scénario de démo : de la centrale solaire de Tozeur à l'usine de Sfax
  document.getElementById("parcours-depart").value = "Centrale_Solaire_Tozeur";
  document.getElementById("parcours-arrivee").value = "Usine_Sfax";
  majChampsLigne();
  charger();
})();
