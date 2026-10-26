// =====================================================================
// Page STOCKAGE (Mohamed Elyess)
// 👉 Modèle à suivre : js/production.js (filtres, ajout, modification, suppression)
// =====================================================================
const COLONNES = [
  { cle: "stockage", titre: "Nom" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge">${lisible(v)}</span>` },
  { cle: "capacite", titre: "Capacité (MWh)" },
  { cle: "zone", titre: "Zone" },
];

async function charger() {
  try {
    const lignes = await api("/api/stockage");
    document.getElementById("liste").innerHTML = tableau(lignes, COLONNES);
  } catch (e) {
    toast(e.message, true);
  }
}

// TODO : filtres -> api("/api/stockage", { params })
// TODO : ajout -> api("/api/stockage", { method: "POST", body })
// TODO : modification -> api(`/api/stockage/${nom}`, { method: "PUT", body })
// TODO : suppression -> api(`/api/stockage/${nom}`, { method: "DELETE" })

charger();
