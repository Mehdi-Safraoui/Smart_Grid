// =====================================================================
// Tableau de bord de la production (Mehdi) — valeur ajoutée
// Données : GET /api/production/tableau-de-bord (requêtes SPARQL SUM / COUNT / GROUP BY)
// =====================================================================
const COULEUR = { renouvelable: "var(--serie-renouvelable)", fossile: "var(--serie-fossile)" };
const CATEGORIE_DU_TYPE = { CentraleSolaire: "renouvelable", ParcEolien: "renouvelable", SourceFossile: "fossile" };
const NOM_DU_TYPE = { CentraleSolaire: "Centrales solaires", ParcEolien: "Parcs éoliens", SourceFossile: "Sources fossiles" };
const mw = (v) => `${Number(v).toLocaleString("fr-FR", { maximumFractionDigits: 1 })} MW`;

// --------------------------------------------------------------- infobulle au survol
const bulle = document.createElement("div");
bulle.className = "infobulle";
bulle.hidden = true;
document.body.appendChild(bulle);
document.addEventListener("mousemove", (ev) => {
  const cible = ev.target.closest("[data-info]");
  if (!cible) { bulle.hidden = true; return; }
  bulle.textContent = cible.dataset.info;
  bulle.hidden = false;
  bulle.style.left = ev.clientX + 14 + "px";
  bulle.style.top = ev.clientY + 14 + "px";
});

// --------------------------------------------------------------- barres horizontales
// lignes : [{ nom, segments: [{ valeur, couleur, info }] }]
function barres(lignes) {
  const max = Math.max(...lignes.map((l) => l.segments.reduce((s, x) => s + x.valeur, 0)), 1);
  return `<div class="barres">${lignes.map((l) => {
    const total = l.segments.reduce((s, x) => s + x.valeur, 0);
    const segs = l.segments.filter((x) => x.valeur > 0).map((x) =>
      `<div class="seg" style="width:${(100 * x.valeur) / total}%;background:${x.couleur}" data-info="${echapper(x.info)}"></div>`).join("");
    return `<div class="barre">
      <span class="nom" title="${echapper(l.nom)}">${echapper(l.nom)}</span>
      <div class="piste">
        <div class="segments" style="width:calc(${(85 * total) / max}% )">${segs}</div>
        <span class="total">${mw(total)}</span>
      </div></div>`;
  }).join("")}</div>`;
}

function graphe(titre, unite, legende, contenu, donnees) {
  return `<div class="dash-graphe">
    <h3>${titre}</h3><p class="unite">${unite}</p>
    ${legende ? `<div class="legende">${legende}</div>` : ""}
    ${contenu}
    <details><summary>Voir les données</summary>${tableau(donnees)}</details>
  </div>`;
}

const LEGENDE = `<span style="--c:var(--serie-renouvelable)">Renouvelable</span>
                 <span style="--c:var(--serie-fossile)">Fossile</span>`;

// --------------------------------------------------------------- rendu
async function chargerTableauDeBord() {
  let d;
  try {
    d = await api("/api/production/tableau-de-bord");
  } catch (e) {
    toast(e.message, true);
    return;
  }

  document.getElementById("dash-kpis").innerHTML = `
    <div class="dash-kpi"><div class="valeur">${d.total_mw.toLocaleString("fr-FR")}<small>MW</small></div>
      <div class="libelle">Puissance installée (${d.nombre_sources} sources)</div></div>
    <div class="dash-kpi"><div class="valeur">${d.part_renouvelable.toLocaleString("fr-FR")}<small>%</small></div>
      <div class="libelle">Part renouvelable (${mw(d.renouvelable_mw)} sur ${mw(d.total_mw)})</div>
      <div class="jauge" data-info="Renouvelable ${mw(d.renouvelable_mw)} · Fossile ${mw(d.fossile_mw)}">
        <span style="width:${d.part_renouvelable}%"></span></div></div>
    <div class="dash-kpi"><div class="valeur">${d.fossile_mw.toLocaleString("fr-FR")}<small>MW</small></div>
      <div class="libelle">Puissance fossile à remplacer</div></div>`;

  const zones = d.par_zone.map((z) => ({
    nom: lisible(z.zone),
    segments: [
      { valeur: z.renouvelable, couleur: COULEUR.renouvelable, info: `${lisible(z.zone)} · renouvelable : ${mw(z.renouvelable)}` },
      { valeur: z.fossile, couleur: COULEUR.fossile, info: `${lisible(z.zone)} · fossile : ${mw(z.fossile)}` },
    ],
  }));
  const types = d.par_type.map((t) => ({
    nom: NOM_DU_TYPE[t.type] ?? lisible(t.type),
    segments: [{ valeur: t.puissance, couleur: COULEUR[CATEGORIE_DU_TYPE[t.type]],
                 info: `${NOM_DU_TYPE[t.type] ?? lisible(t.type)} · ${mw(t.puissance)} · ${t.nombre} source(s)` }],
  }));
  const batiments = d.par_batiment.map((b) => ({
    nom: lisible(b.batiment),
    segments: [{ valeur: b.puissance, couleur: COULEUR.renouvelable,
                 info: `${lisible(b.batiment)} · ${mw(b.puissance)} renouvelables · ${b.sources} source(s)` }],
  }));

  document.getElementById("dash-graphes").innerHTML =
    graphe("Puissance installée par zone", "MW, renouvelable et fossile empilés", LEGENDE, barres(zones),
           d.par_zone.map((z) => ({ zone: z.zone, renouvelable_MW: z.renouvelable, fossile_MW: z.fossile }))) +
    graphe("Puissance par type de source", "MW", LEGENDE, barres(types), d.par_type) +
    graphe("Énergie verte reçue par bâtiment", "MW renouvelables qui alimentent chaque bâtiment (relation alimente)",
           "", barres(batiments), d.par_batiment);
}

chargerTableauDeBord();
