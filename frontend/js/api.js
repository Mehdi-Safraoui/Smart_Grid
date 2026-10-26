// =====================================================================
// Communication front -> back (utilisé par toutes les pages)
// =====================================================================
// Si le front est servi par FastAPI (http://localhost:8000), API_URL reste vide.
// Si vous ouvrez les pages avec Live Server, mettez "http://localhost:8000".
const API_URL = location.port === "8000" ? "" : "http://localhost:8000";

async function api(chemin, { method = "GET", body, params } = {}) {
  let url = API_URL + chemin;
  if (params) {
    const p = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => { if (v !== "" && v != null) p.append(k, v); });
    if ([...p].length) url += "?" + p;
  }
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail ? JSON.stringify(data.detail) : `Erreur ${res.status}`);
  return data;
}

// ---------------------------------------------------------------- utilitaires
function toast(message, erreur = false) {
  const t = document.createElement("div");
  t.className = "toast" + (erreur ? " error" : "");
  t.textContent = message;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// "Centrale_Solaire_Tozeur" -> "Centrale Solaire Tozeur"
const lisible = (v) => (typeof v === "string" ? v.replace(/^Zone_/, "").replace(/_/g, " ") : v ?? "");

const echapper = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Construit un tableau HTML à partir d'une liste d'objets
function tableau(lignes, colonnes, actions) {
  if (!lignes.length) return '<p class="empty">Aucun résultat</p>';
  colonnes = colonnes || Object.keys(lignes[0]).map((k) => ({ cle: k, titre: k }));
  const tete = colonnes.map((c) => `<th>${echapper(c.titre)}</th>`).join("") + (actions ? "<th></th>" : "");
  const corps = lignes.map((l) =>
    "<tr>" + colonnes.map((c) => `<td>${c.rendu ? c.rendu(l[c.cle], l) : echapper(lisible(l[c.cle]))}</td>`).join("") +
    (actions ? `<td class="actions">${actions(l)}</td>` : "") + "</tr>").join("");
  return `<div class="table-wrap"><table><thead><tr>${tete}</tr></thead><tbody>${corps}</tbody></table></div>`;
}

// Remplit un <select> avec les zones de l'ontologie
async function remplirZones(select, avecVide = true) {
  const zones = await api("/api/zones");
  select.innerHTML = (avecVide ? '<option value="">Toutes</option>' : "") +
    zones.map((z) => `<option value="${z}">${lisible(z)}</option>`).join("");
}

// Marque l'onglet actif dans la navigation
document.addEventListener("DOMContentLoaded", () => {
  const page = location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav a").forEach((a) => {
    if (a.getAttribute("href") === page) a.classList.add("active");
  });
});
