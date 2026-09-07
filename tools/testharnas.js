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
 * Met "inventaris" wordt elke versie en variatie van elke formule doorgerekend
 * en gerapporteerd, zodat een databestand in zijn geheel getoetst wordt.
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

/* ---------- 4. uitvoeren ---------- */
const sandbox = { calc: null, migrate: null, matById: null, buildUsage: null, varLinesRaw: null };
try {
  // eslint-disable-next-line no-new-func
  new Function("__out", src + `
    ;try{__out.calc=calc}catch(e){}
    ;try{__out.migrate=migrate}catch(e){}
    ;try{__out.matById=matById}catch(e){}
    ;try{__out.invalidateMats=invalidateMats}catch(e){}
    ;try{__out.varLinesRaw=varLinesRaw}catch(e){}
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

function linesOf(f, item) {
  if (item.label === undefined) return item.lines || [];      // versie
  if (item.lines) return item.lines;                          // bevroren variatie
  return sandbox.varLinesRaw ? sandbox.varLinesRaw(f, item) : [];
}

let fouten = 0;

if (mode === "referentie") {
  const cases = [
    { formule: "Bewonder", item: "45gr", g: 46.256, pct: 85.12 },
    { formule: "CC Blonde Amber", item: "v3", g: 89.503, pct: 20.10 },
  ];
  for (const c of cases) {
    const f = data.formulas.find(x => x.name === c.formule);
    if (!f) { console.log(`ONTBREEKT  ${c.formule}`); fouten++; continue; }
    const it = (f.variations || []).find(v => v.label === c.item)
            || (f.versions || []).find(v => "v" + v.v === c.item);
    if (!it) { console.log(`ONTBREEKT  ${c.formule} / ${c.item}`); fouten++; continue; }
    const K = sandbox.calc(linesOf(f, it));
    const okG = Math.abs(K.totalW - c.g) < 0.001;
    const okP = Math.abs(K.totalAbsPct - c.pct) < 0.01;
    console.log(`${okG && okP ? "OK  " : "FOUT"} ${c.formule.padEnd(20)} ${c.item.padEnd(6)} `
      + `${fmt(K.totalW, 3).padStart(10)} g (verwacht ${fmt(c.g, 3)})  `
      + `${fmt(K.totalAbsPct, 2).padStart(6)} % (verwacht ${fmt(c.pct, 2)})`);
    if (!(okG && okP)) fouten++;
  }
} else {
  let nF = 0, nI = 0, leeg = 0;
  for (const f of data.formulas) {
    nF++;
    for (const it of [...(f.versions || []), ...(f.variations || [])]) {
      const L = linesOf(f, it);
      let K;
      try { K = sandbox.calc(L); }
      catch (e) { console.log("FOUT %s / %s: %s", f.name, it.label ?? ("v" + it.v), e.message); fouten++; continue; }
      nI++;
      if (!L.length) { leeg++; continue; }
      const relSom = K.rows.filter(r => r.rel != null).reduce((a, r) => a + r.rel, 0);
      const okRel = K.rows.every(r => r.rel == null) || Math.abs(relSom - 100) < 0.01;
      const okW = K.totalW > 0 && isFinite(K.totalW);
      const okA = isFinite(K.totalAbsPct) && K.totalAbsPct >= 0 && K.totalAbsPct <= 100.001;
      const onbekend = L.filter(l => !sandbox.matById(l.materialId)).length;
      if (!okRel || !okW || !okA || onbekend) {
        fouten++;
        console.log(`FOUT ${f.name.padEnd(22)} ${String(it.label ?? ("v" + it.v)).padEnd(8)} `
          + `rel-som ${fmt(relSom, 2)}  gewicht ${fmt(K.totalW, 3)}  abs ${fmt(K.totalAbsPct, 2)}`
          + (onbekend ? `  ${onbekend} regels met onbekend materiaal` : ""));
      }
    }
  }
  console.log(`${nF} formules, ${nI} versies en variaties doorgerekend, ${leeg} zonder regels`);
  // overzicht per formule
  console.log("");
  console.log(`${"formule".padEnd(24)} ${"item".padEnd(8)} ${"gewicht g".padStart(10)} ${"abs %".padStart(8)} ${"regels".padStart(7)}`);
  for (const f of data.formulas) {
    for (const it of [...(f.versions || []), ...(f.variations || [])]) {
      const L = linesOf(f, it);
      if (!L.length) continue;
      const K = sandbox.calc(L);
      console.log(`${f.name.padEnd(24)} ${String(it.label ?? ("v" + it.v)).padEnd(8)} `
        + `${fmt(K.totalW, 3).padStart(10)} ${fmt(K.totalAbsPct, 2).padStart(8)} ${String(L.length).padStart(7)}`);
    }
  }
}

console.log("");
console.log(fouten ? `${fouten} probleem(en)` : "geen problemen");
process.exit(fouten ? 1 : 0);
