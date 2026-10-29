// =====================================================================
// Page PRODUCTION (Mehdi) — EXEMPLE COMPLET À SUIVRE
// CRUD : liste + filtres (GET), ajout (POST), modification (PUT), suppression (DELETE)
// =====================================================================
const filtres = document.getElementById("filtres");
const form = document.getElementById("form-source");
let enEdition = null;   // nom de la source en cours de modification

const COLONNES = [
  { cle: "source", titre: "Source" },
  { cle: "type", titre: "Type", rendu: (v) => `<span class="badge">${lisible(v)}</span>` },
  { cle: "puissance", titre: "Puissance (MW)" },
  { cle: "zone", titre: "Zone" },
  { cle: "alimente", titre: "Alimente" },
];

// ---------------------------------------------------------------- READ
async function charger() {
  const params = Object.fromEntries(new FormData(filtres));
  try {
    const sources = await api("/api/production", { params });
    if (typeof chargerTableauDeBord === "function") chargerTableauDeBord();   // garde les graphiques à jour
    document.getElementById("liste").innerHTML = tableau(sources, COLONNES, (s) => `
      <button class="small secondary" onclick="editer('${s.source}')">Modifier</button>
      <button class="small danger" onclick="supprimer('${s.source}')">Supprimer</button>`);
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- CREATE / UPDATE
form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const d = Object.fromEntries(new FormData(form));
  try {
    if (enEdition) {
      const r = await api(`/api/production/${enEdition}`, {
        method: "PUT",
        body: { puissance: Number(d.puissance), zone: d.zone, type: d.type,
                nouveau_nom: d.nom !== enEdition ? d.nom : null },
      });
      toast(`${r.nom} modifiée`);
    } else {
      await api("/api/production", {
        method: "POST",
        body: { nom: d.nom, type: d.type, puissance: Number(d.puissance), zone: d.zone,
                alimente: d.alimente ? [d.alimente] : [] },
      });
      toast(`${d.nom} ajoutée`);
    }
    annuler();
    charger();
  } catch (e) {
    toast(e.message, true);
  }
});

async function editer(nom) {
  const s = await api(`/api/production/${nom}`);
  enEdition = nom;
  form.nom.value = nom;
  form.alimente.disabled = true;   // nom et type sont modifiables
  form.type.value = s.type;
  form.puissance.value = s.puissance;
  form.zone.value = s.zone;
  document.getElementById("form-titre").textContent = `Modifier ${lisible(nom)}`;
  document.getElementById("btn-enregistrer").textContent = "Enregistrer";
  document.getElementById("btn-annuler").hidden = false;
  form.scrollIntoView({ behavior: "smooth" });
}

function annuler() {
  enEdition = null;
  form.reset();
  form.nom.disabled = form.type.disabled = form.alimente.disabled = false;
  document.getElementById("form-titre").textContent = "Ajouter une source";
  document.getElementById("btn-enregistrer").textContent = "Ajouter";
  document.getElementById("btn-annuler").hidden = true;
}
document.getElementById("btn-annuler").addEventListener("click", annuler);

// ---------------------------------------------------------------- DELETE
async function supprimer(nom) {
  if (!confirm(`Supprimer ${lisible(nom)} ?`)) return;
  try {
    await api(`/api/production/${nom}`, { method: "DELETE" });
    toast(`${nom} supprimée`);
    charger();
  } catch (e) {
    toast(e.message, true);
  }
}

// ---------------------------------------------------------------- initialisation
filtres.addEventListener("submit", (ev) => { ev.preventDefault(); charger(); });
filtres.addEventListener("reset", () => setTimeout(charger));

(async () => {
  await remplirZones(document.getElementById("filtre-zone"));
  await remplirZones(document.getElementById("form-zone"), false);
  const batiments = await api("/api/consommation");
  document.getElementById("form-batiment").innerHTML = '<option value="">— aucun —</option>' +
    batiments.map((b) => `<option value="${b.batiment}">${lisible(b.batiment)}</option>`).join("");
  charger();
})();
