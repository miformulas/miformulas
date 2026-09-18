/* Eenmalige controle bij bouw 260918d: de bench-groepen bewaarden hun regels als
 * materiaal|dilutie|volgnummer, en dragen sinds deze bouw de eigen id van de regel.
 * migrate() vertaalt de opgeslagen sleutels één keer. Dit script zegt of dat op een
 * databestand ook echt alle sleutels terugvindt.
 *
 *   node tools/controleer-bench.js <miFormulas.html> <data.json>
 *
 * Verandert niets: het leest het bestand, laat migrate() erop los in het geheugen en telt.
 */
"use strict";
const fs = require("fs");
const [htmlPath, dataPath] = process.argv.slice(2);
if (!htmlPath || !dataPath) {
  console.error("gebruik: node tools/controleer-bench.js <miFormulas.html> <data.json>");
  process.exit(2);
}

const raw = JSON.parse(fs.readFileSync(dataPath, "utf8"));

/* tellen zoals het bestand op schijf staat, en meteen zien welke sleutels daar al nergens naar wezen:
   de oude weergave liet die stil weg, dus zij horen ook niet mee te verhuizen */
let versies = 0, groepen = 0, sleutels = 0, benchversies = 0, alDood = 0;
const dode = [];
for (const f of raw.formulas || []) {
  for (const v of f.versions || []) {
    versies++;
    if (!v.bench || !Array.isArray(v.bench.groups)) continue;
    benchversies++;
    const seen = new Map(), bestaat = new Set();
    for (const l of v.lines || []) {
      const b = l.materialId + "|" + (l.dilutionPct ?? 100);
      const n = seen.get(b) || 0; seen.set(b, n + 1);
      bestaat.add(b + "|" + n);
    }
    for (const g of v.bench.groups) {
      groepen++;
      for (const k of g.keys || []) {
        sleutels++;
        if (!bestaat.has(k)) { alDood++; if (dode.length < 5) dode.push([f.name, v.v, k]); }
      }
    }
  }
}

/* migrate() uit de app halen, zoals testharnas.js het doet */
const html = fs.readFileSync(htmlPath, "utf8");
const m = html.match(/<script>\s*([\s\S]*?)<\/script>\s*<\/body>/i);
if (!m) { console.error("geen <script>-blok gevonden"); process.exit(2); }
let src = m[1].replace(/^(\s*)(?:let|const)\s+/gm, (mm, sp) => (sp.length === 0 ? "var " : mm));
/* de stubs en de aanroep van testharnas.js: de app draait zonder DOM */
const el = () => new Proxy(function () {}, {
  get(t, k) {
    if (k === "style" || k === "classList" || k === "dataset") return el();
    if (k === "textContent" || k === "value" || k === "innerHTML") return "";
    if (k === "options" || k === "children") return [];
    if (k === Symbol.toPrimitive) return () => "";
    return el();
  },
  apply: () => el(), set: () => true,
});
globalThis.document = {querySelector: el, querySelectorAll: () => [], addEventListener(){}, createElement: el,
                       body: el(), documentElement: el(), head: el()};
globalThis.addEventListener = () => {};
globalThis.removeEventListener = () => {};
globalThis.dispatchEvent = () => true;
globalThis.window = globalThis;
globalThis.matchMedia = () => ({matches: false, addEventListener(){}, addListener(){}});
globalThis.localStorage = {getItem: () => null, setItem(){}, removeItem(){}};
globalThis.sessionStorage = globalThis.localStorage;
globalThis.indexedDB = null;
globalThis.location = {protocol: "file:", href: "file:///miFormulas.html", hash: ""};
globalThis.history = {replaceState(){}, pushState(){}, state: null};
try { Object.defineProperty(globalThis, "navigator", {value: {userAgent: "node"}, configurable: true}); } catch (e) {}
globalThis.alert = () => {};
globalThis.prompt = () => null;
globalThis.confirm = () => false;
globalThis.structuredClone = globalThis.structuredClone || (x => JSON.parse(JSON.stringify(x)));

const sandbox = {migrate: null};
try {
  // eslint-disable-next-line no-new-func
  new Function("__out", src + "\n;try{__out.migrate=migrate}catch(e){}")(sandbox);
} catch (e) { console.error("script draaide niet:", e.message); }
const migrate = sandbox.migrate;
if (typeof migrate !== "function") { console.error("migrate() niet gevonden in de app"); process.exit(2); }

const na = migrate(JSON.parse(JSON.stringify(raw)));

/* na de vertaling: hoeveel sleutels wijzen nog naar een bestaande regel? */
let naSleutels = 0, naGroepen = 0, weg = 0, regels = 0, metId = 0;
for (const f of na.formulas || []) {
  for (const v of f.versions || []) {
    for (const l of v.lines || []) { regels++; if (l.id) metId++; }
    if (!v.bench || !Array.isArray(v.bench.groups)) continue;
    const ids = new Set((v.lines || []).map(l => l.id));
    for (const gr of v.bench.groups) {
      naGroepen++;
      for (const k of gr.keys || []) { naSleutels++; if (!ids.has(k)) weg++; }
    }
  }
}

console.log(`${versies} versie(s), ${regels} regel(s), ${metId} met een eigen id`);
console.log(`bench: ${benchversies} versie(s) met een schikking, ${groepen} groep(en), ${sleutels} sleutel(s) op schijf`);
console.log(`na de vertaling: ${naGroepen} groep(en), ${naSleutels} sleutel(s), waarvan ${weg} die geen regel meer aanwijzen`);
const kwijt = sleutels - naSleutels;
if (alDood) {
  console.log(`\n${alDood} sleutel(s) wezen op schijf al naar geen enkele regel en gaan niet mee; de eerste vijf:`);
  for (const [fn, vv, k] of dode) console.log(`   ${fn} v${vv}: ${k}`);
}
const onverwacht = kwijt - alDood;
if (onverwacht > 0) console.log(`\n${onverwacht} levende sleutel(s) vonden hun regel niet terug.`);
console.log(onverwacht > 0 || weg ? "\nNAKIJKEN" : "\ngeen problemen");
process.exit(onverwacht > 0 || weg ? 1 : 0);
