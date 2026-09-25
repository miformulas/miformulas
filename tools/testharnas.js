/* Testharnas voor de rekenkern van miFormulas.
 *
 * Haalt het <script>-blok uit miFormulas.html, zet top-level let/const om naar
 * var, voorziet DOM-stubs en draait de rekenkern tegen een databestand.
 *
 *   node testharnas.js <miFormulas.html> <data.json> [referentie|inventaris]
 *
 * Zonder derde argument draait de referentiecontrole:
 *   Bewonder 45gr        = 46,256 g / 85,12 %
 *   CC Blonde Amber v3   = 89,503 g / 20,10 %
 * Een referentieformule die niet in het bestand staat (de starterset heeft ze niet), wordt als "niet in dit
 * bestand" gemeld zonder fout; staat ze er wel, dan moet ze kloppen.
 * Met "inventaris" wordt elke versie van elke formule doorgerekend en gerapporteerd, zodat een databestand
 * in zijn geheel getoetst wordt, en rekent Compare (aggLines) elke versie na: gewicht, abs % en rel % per
 * materiaal moeten gelijk zijn aan wat de formuletabel (calc) zegt.
 */
"use strict";
const fs = require("fs");

const [htmlPath, dataPath, mode = "referentie"] = process.argv.slice(2);
if (!htmlPath || !dataPath) {
  console.error("gebruik: node testharnas.js <miFormulas.html> <data.json> [referentie|inventaris]");
  process.exit(2);
}

/* ---------- 1. script uit de HTML halen ---------- */
const html = fs.readFileSync(htmlPath, "utf8");
const m = html.match(/<script>\s*([\s\S]*?)<\/script>\s*<\/body>/i);
if (!m) { console.error("geen <script>-blok gevonden"); process.exit(2); }
let src = m[1];

/* ---------- 2. top-level let/const naar var ---------- */
src = src.replace(/^(\s*)(?:let|const)\s+/gm, (mm, sp) => (sp.length === 0 ? "var " : mm));

/* ---------- 3. DOM- en browserstubs ---------- */
const el = () => new Proxy(function () {}, {
  get(t, k) {
    if (k === "style" || k === "classList" || k === "dataset") return el();
    if (k === "textContent" || k === "value" || k === "innerHTML") return "";
    if (k === "options" || k === "children") return [];
    if (k === Symbol.toPrimitive) return () => "";
    return el();
  },
  set() { return true; },
  apply() { return el(); },
});
const doc = {
  getElementById: el, querySelector: el, querySelectorAll: () => [],
  createElement: el, addEventListener() {}, body: el(), documentElement: el(),
};
globalThis.document = doc;
globalThis.window = {
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  addEventListener() {}, indexedDB: null, showOpenFilePicker: undefined,
  location: { protocol: "file:", host: "" },
};
globalThis.location = globalThis.window.location;
try { Object.defineProperty(globalThis, "navigator", { value: { userAgent: "node" }, configurable: true }); } catch (e) {}
globalThis.alert = () => {};
globalThis.prompt = () => null;
globalThis.confirm = () => false;
globalThis.structuredClone = globalThis.structuredClone || (x => JSON.parse(JSON.stringify(x)));
globalThis.MutationObserver = globalThis.MutationObserver || class { observe() {} disconnect() {} };   // the app names its dialogs with one (260922l)

/* ---------- 4. uitvoeren ---------- */
const sandbox = { calc: null, migrate: null, matById: null, buildUsage: null };
try {
  // eslint-disable-next-line no-new-func
  new Function("__out", src + `
    ;try{__out.calc=calc}catch(e){}
    ;try{__out.aggLines=aggLines}catch(e){}
    ;try{__out.migrate=migrate}catch(e){}
    ;try{__out.matById=matById}catch(e){}
    ;try{__out.invalidateMats=invalidateMats}catch(e){}
    ;try{__out.setDATA=function(d){DATA=d}}catch(e){}
  `)(sandbox);
} catch (e) {
  console.error("script draaide niet:", e.message);
  process.exit(2);
}
for (const k of ["calc", "migrate", "setDATA"]) {
  if (!sandbox[k]) { console.error("functie ontbreekt: " + k); process.exit(2); }
}

const data = sandbox.migrate(JSON.parse(fs.readFileSync(dataPath, "utf8")));
sandbox.setDATA(data);
if (sandbox.invalidateMats) sandbox.invalidateMats();

const fmt = (x, d) => (x == null || isNaN(x) ? "–" : x.toFixed(d).replace(".", ","));

const linesOf = (f, item) => item.lines || [];   // sinds 260915b bestaan alleen versies; een oud bestand kan nog variaties dragen, die telt het harnas alleen
const oudeVariaties = data.formulas.reduce((s, f) => s + (f.variations || []).length, 0);
if (oudeVariaties) console.log(`LET OP     ${oudeVariaties} variatie(s) in het bestand: sinds bouw 260915b niet meer berekend of getoond (zet ze om naar versies)`);

let fouten = 0;

if (mode === "referentie") {
  const cases = [
    { formule: "Bewonder", item: "45gr", src: "Bewonder v09 45gr", g: 46.256, pct: 85.12 },   // tot 260915b een variatie; nu de versie met die naam of die Formulair-bron
    { formule: "CC Blonde Amber", item: "v3", g: 89.503, pct: 20.10 },
  ];
  let gevonden = 0;
  for (const c of cases) {
    const f = data.formulas.find(x => x.name === c.formule);
    if (!f) { console.log(`NIET IN DIT BESTAND  ${c.formule}`); continue; }   // de starterset heeft ze niet: geen fout
    gevonden++;
    const it = (f.versions || []).find(v => "v" + v.v === c.item || (v.name || "") === c.item || (c.src && (v.sourceName || "").trim() === c.src));
    if (!it) { console.log(`ONTBREEKT  ${c.formule} / ${c.item}`); fouten++; continue; }
    const K = sandbox.calc(linesOf(f, it));
    const okG = Math.abs(K.totalW - c.g) < 0.001;
    const okP = Math.abs(K.totalAbsPct - c.pct) < 0.01;
    console.log(`${okG && okP ? "OK  " : "FOUT"} ${c.formule.padEnd(20)} ${c.item.padEnd(6)} `
      + `${fmt(K.totalW, 3).padStart(10)} g (verwacht ${fmt(c.g, 3)})  `
      + `${fmt(K.totalAbsPct, 2).padStart(6)} % (verwacht ${fmt(c.pct, 2)})`);
    if (!(okG && okP)) fouten++;
  }
  if (!gevonden) console.log("geen van de referentieformules staat in dit bestand: hier zegt alleen \"inventaris\" iets");
} else {
  let nF = 0, nI = 0, leeg = 0, nC = 0;
  const zelfde = (a, b) => Math.abs(a - b) <= 1e-9 * Math.max(1, Math.abs(a), Math.abs(b));
  for (const f of data.formulas) {
    nF++;
    for (const it of f.versions || []) {
      const L = linesOf(f, it);
      let K;
      try { K = sandbox.calc(L); }
      catch (e) { console.log("FOUT %s / v%s: %s", f.name, it.v, e.message); fouten++; continue; }
      nI++;
      if (!L.length) { leeg++; continue; }
      const relSom = K.rows.filter(r => r.rel != null).reduce((a, r) => a + r.rel, 0);
      const okRel = K.rows.every(r => r.rel == null) || Math.abs(relSom - 100) < 0.01;
      const okW = K.totalW > 0 && isFinite(K.totalW);
      const okA = isFinite(K.totalAbsPct) && K.totalAbsPct >= 0 && K.totalAbsPct <= 100.001;
      const onbekend = L.filter(l => !sandbox.matById(l.materialId)).length;
      if (sandbox.aggLines) {   // Compare rekent apart; bij B2 van de review van 22/09 liepen de twee uiteen
        const A = sandbox.aggLines(L), perM = new Map();
        for (const r of K.rows) if (r.rel != null) perM.set(r.l.materialId, (perM.get(r.l.materialId) || 0) + r.rel);
        let okC = zelfde(A.tw, K.totalW) && zelfde(A.abs, K.totalAbsPct);
        for (const [id, e] of A.map) if (e.rel != null && !zelfde(e.rel, perM.get(id) || 0)) okC = false;
        if (okC) nC++;
        else {
          fouten++;
          console.log(`VERSCHIL ${f.name.padEnd(22)} ${("v" + it.v).padEnd(8)} tabel ${fmt(K.totalW, 3)} g / ${fmt(K.totalAbsPct, 2)} %,`
            + ` Compare ${fmt(A.tw, 3)} g / ${fmt(A.abs, 2)} %`);
        }
      }
      if (!okRel || !okW || !okA || onbekend) {
        fouten++;
        console.log(`FOUT ${f.name.padEnd(22)} ${("v" + it.v).padEnd(8)} `
          + `rel-som ${fmt(relSom, 2)}  gewicht ${fmt(K.totalW, 3)}  abs ${fmt(K.totalAbsPct, 2)}`
          + (onbekend ? `  ${onbekend} regels met onbekend materiaal` : ""));
      }
    }
  }
  console.log(`${nF} formules, ${nI} versies doorgerekend, ${leeg} zonder regels; Compare gelijk op ${nC}`);
  // overzicht per formule
  console.log("");
  console.log(`${"formule".padEnd(24)} ${"item".padEnd(8)} ${"gewicht g".padStart(10)} ${"abs %".padStart(8)} ${"regels".padStart(7)}`);
  for (const f of data.formulas) {
    for (const it of f.versions || []) {
      const L = linesOf(f, it);
      if (!L.length) continue;
      const K = sandbox.calc(L);
      console.log(`${f.name.padEnd(24)} ${("v" + it.v).padEnd(8)} `
        + `${fmt(K.totalW, 3).padStart(10)} ${fmt(K.totalAbsPct, 2).padStart(8)} ${String(L.length).padStart(7)}`);
    }
  }
}

console.log("");
console.log(fouten ? `${fouten} probleem(en)` : "geen problemen");
process.exit(fouten ? 1 : 0);
