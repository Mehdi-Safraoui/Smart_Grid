// =====================================================================
// Page CONSOMMATION (Ahmed Amine)
// 👉 Modèle à suivre : js/production.js (filtres, ajout, modification, suppression)
// =====================================================================
const COLONNES = [
  { cle: "batiment", titre: "Nom" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge">${lisible(v)}</span>` },
  { cle: "consommation", titre: "Consommation (kWh)" },
  { cle: "zone", titre: "Zone" },
];

async function charger() {
  try {
    const lignes = await api("/api/consommation");
    document.getElementById("liste").innerHTML = tableau(lignes, COLONNES);
  } catch (e) {
    toast(e.message, true);
  }
}

// TODO : filtres -> api("/api/consommation", { params })
// TODO : ajout -> api("/api/consommation", { method: "POST", body })
// TODO : modification -> api(`/api/consommation/${nom}`, { method: "PUT", body })
// TODO : suppression -> api(`/api/consommation/${nom}`, { method: "DELETE" })

charger();
