// =====================================================================
// Page RESEAU (Yassine)
// 👉 Modèle à suivre : js/production.js (filtres, ajout, modification, suppression)
// =====================================================================
const COLONNES = [
  { cle: "element", titre: "Nom" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge">${lisible(v)}</span>` },
  { cle: "tension", titre: "Tension (kV)" },
  { cle: "zone", titre: "Zone" },
];

async function charger() {
  try {
    const lignes = await api("/api/reseau");
    document.getElementById("liste").innerHTML = tableau(lignes, COLONNES);
  } catch (e) {
    toast(e.message, true);
  }
}

// TODO : filtres -> api("/api/reseau", { params })
// TODO : ajout -> api("/api/reseau", { method: "POST", body })
// TODO : modification -> api(`/api/reseau/${nom}`, { method: "PUT", body })
// TODO : suppression -> api(`/api/reseau/${nom}`, { method: "DELETE" })

charger();
