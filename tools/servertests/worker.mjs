/* Server test for server/worker.js: the Cloudflare Worker that keeps miformulas-data.json in an R2
   bucket. No network and no Cloudflare account: a stand-in bucket with R2's own etag and upload-time
   semantics answers the calls, and the Worker's exported fetch() is driven straight from node.
   What it walks: the preflight, the two setup mistakes, the token, ?ping=1, reading, the gate in
   front of a write, the conflict guard, the race a conditional write has to survive, and the daily
   snapshots with their trimming.

       node worker.mjs [path to worker.js]

   Part of miFormulas, GPL v3 with additional terms, see LICENSE and NOTICE. */
import { createHash } from "node:crypto";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const workerPath = resolve(process.argv[2] || resolve(here, "../../server/worker.js"));
if (!existsSync(workerPath)) { console.error("not found: " + workerPath); process.exit(2); }
const worker = (await import(pathToFileURL(workerPath).href)).default;

const FILE = "miformulas-data.json";
const TOKEN = "a-long-random-token-for-the-test";
const DATA = '{"materials":[{"name":"Crème"}],"formulas":[]}';   // the accent is the point: bytes are not characters
const DATA2 = '{"materials":[{"name":"Iso E"}],"formulas":[{"name":"Test"}]}';
const OTHER = '{"materials":[],"formulas":[{"name":"From the other device"}]}';

let ok = 0, fail = 0;
function check(name, cond, extra) {
  if (cond) { ok++; console.log("OK   " + name); }
  else { fail++; console.log("FAIL " + name + (extra === undefined ? "" : "  <- " + String(extra).slice(0, 300))); }
}

/* ---------- the stand-in bucket ---------- */
const md5 = (b) => createHash("md5").update(b).digest("hex");

function fakeR2() {
  const map = new Map();
  let clock = Date.parse("2026-09-21T09:00:00Z");
  const bytesOf = async (v) => Buffer.from(await new Response(v).arrayBuffer());
  const meta = (key, r) => ({ key, etag: r.etag, httpEtag: `"${r.etag}"`, size: r.bytes.length, uploaded: new Date(r.at) });
  const api = {
    log: [],                  // every put: { key, refused }
    refuse: 0,                // refuse this many conditional puts on etagMatches, whatever the state
    onConditionalPut: null,   // a hand that writes in between, to play out a race; called before every guarded put
    async head(key) { const r = map.get(key); return r ? meta(key, r) : null; },
    async get(key) {
      const r = map.get(key);
      return r ? { ...meta(key, r), body: new Blob([r.bytes]).stream() } : null;
    },
    async put(key, value, opts = {}) {
      const only = opts.onlyIf;
      if (only && api.onConditionalPut) await api.onConditionalPut(key, opts);
      const cur = map.get(key);
      const no = (why) => { api.log.push({ key, refused: why }); return null; };
      if (only && "etagMatches" in only) {
        if (api.refuse > 0) { api.refuse--; return no("refused"); }
        const want = String(only.etagMatches).replace(/^W\//i, "").replace(/^"|"$/g, "");
        if (!cur || cur.etag !== want) return no("etagMatches");
      }
      // R2 lets the write through as long as the object was not written after that moment (like
      // If-Unmodified-Since, equal counts), and that is exactly what the fallback in worker.js leans on
      if (only && "uploadedBefore" in only && (!cur || cur.at > only.uploadedBefore.getTime())) return no("uploadedBefore");
      const bytes = await bytesOf(value);
      clock += 1000;
      const r = { bytes, etag: md5(bytes), at: clock };
      map.set(key, r);
      api.log.push({ key, refused: null });
      return meta(key, r);
    },
    async delete(key) { map.delete(key); },
    async list({ prefix = "" } = {}) {
      return { objects: [...map.keys()].filter((k) => k.startsWith(prefix)).map((k) => meta(k, map.get(k))) };
    },
    /* helpers for the test itself, not something R2 knows */
    seed(key, text) { const b = Buffer.from(text); clock += 1000; map.set(key, { bytes: b, etag: md5(b), at: clock }); },
    text(key) { const r = map.get(key); return r ? r.bytes.toString("utf8") : null; },
    keys() { return [...map.keys()].sort(); },
    puts(key) { return api.log.filter((e) => e.key === key); },
    reset() { map.clear(); api.log = []; api.refuse = 0; api.onConditionalPut = null; },
  };
  return api;
}

const R2 = fakeR2();
const env = { TOKEN, DATA: R2 };
const hit = (method, path = "/", opts = {}) => worker.fetch(
  new Request("https://data.example.com" + path, { method, body: opts.body, headers: opts.headers || {} }), opts.env || env);
const body = async (r) => { const t = await r.text(); try { return JSON.parse(t); } catch { return t; } };
const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Brussels", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
const put = (b, headers = {}) => hit("PUT", "/", { body: b, headers: { "X-Token": TOKEN, ...headers } });

/* ---------- 1. the preflight and the two setup mistakes ---------- */
let r = await hit("OPTIONS");
check("OPTIONS answers 204 without a token", r.status === 204, r.status);
check("OPTIONS carries Allow-Origin and Allow-Methods",
  r.headers.get("Access-Control-Allow-Origin") === "*" && /PUT/.test(r.headers.get("Access-Control-Allow-Methods") || ""),
  r.headers.get("Access-Control-Allow-Methods"));
check("OPTIONS allows the headers the app sends",
  /X-Token/i.test(r.headers.get("Access-Control-Allow-Headers") || "") && /If-Match/i.test(r.headers.get("Access-Control-Allow-Headers") || ""),
  r.headers.get("Access-Control-Allow-Headers"));
check("OPTIONS exposes the ETag (without it the conflict guard is off)",
  /ETag/i.test(r.headers.get("Access-Control-Expose-Headers") || ""), r.headers.get("Access-Control-Expose-Headers"));
check("OPTIONS is no-store and nosniff as well",
  r.headers.get("Cache-Control") === "no-store" && r.headers.get("X-Content-Type-Options") === "nosniff");

r = await hit("GET", "/", { env: { DATA: R2 } });
check("a Worker without the TOKEN secret says so", r.status === 500 && /TOKEN/.test(JSON.stringify(await body(r))));
r = await hit("GET", "/", { env: { TOKEN } });
check("a Worker without the DATA binding says so", r.status === 500 && /DATA/.test(JSON.stringify(await body(r))));

/* ---------- 2. the token ---------- */
r = await hit("GET");
let j = await body(r);
check("no token at all is 401", r.status === 401 && j.error === "invalid token", r.status + " " + JSON.stringify(j));
check("the answer names the live version of the code", j.worker >= 1, j.worker);
r = await hit("GET", "/", { headers: { "X-Token": "wrong" } });
j = await body(r);
check("a wrong token is 401", r.status === 401);
check("the refusal does not carry the token", !JSON.stringify(j).includes(TOKEN));

/* ---------- 3. ?ping=1 and reading on an empty bucket ---------- */
r = await hit("GET", "/?ping=1", { headers: { "X-Token": TOKEN } });
j = await body(r);
check("?ping=1 on an empty bucket is ok with etag null and 0 bytes", r.status === 200 && j.ok === true && j.etag === null && j.bytes === 0, JSON.stringify(j));
r = await hit("GET", "/", { headers: { "X-Token": TOKEN } });
check("reading an empty bucket is 404, not a crash", r.status === 404 && (await body(r)).error === "no data file yet");

/* ---------- 4. the gate in front of a write ---------- */
R2.seed(FILE, DATA2);
const before = R2.text(FILE);
r = await put("");
check("an empty body is refused", r.status === 400 && (await body(r)).error === "empty body");
r = await put("not json at all");
check("a body that is not JSON is refused", r.status === 400 && /not a miFormulas data file/.test((await body(r)).error));
r = await put('{"notes":"materials and formulas belong in here"}');
check("a JSON object that only mentions the words is refused", r.status === 400);
r = await put('[{"materials":[],"formulas":[]}]');
check("an array is refused", r.status === 400);
r = await put('{"materials":[],"formulas":[]');
check("a file that was cut off is refused", r.status === 400);
check("none of the refusals touched the stored data", R2.text(FILE) === before);

/* ---------- 5. writing, reading back, and the byte count ---------- */
R2.reset();
r = await put(DATA);
j = await body(r);
check("a good body is written", r.status === 200 && j.ok === true, JSON.stringify(j));
check("the answer carries the ETag both as a header and in the body",
  r.headers.get("ETag") === j.etag && /^"/.test(j.etag || ""), r.headers.get("ETag") + " / " + j.etag);
check("bytes is what R2 stored, not the number of characters",
  j.bytes === Buffer.byteLength(DATA) && j.bytes === DATA.length + 1, j.bytes + " vs " + DATA.length);
check("the bucket holds exactly what was sent", R2.text(FILE) === DATA);
check("an empty bucket gets no snapshot of nothing", R2.keys().every((k) => !k.startsWith("snapshots/")), R2.keys().join(", "));

r = await hit("GET", "/", { headers: { "X-Token": TOKEN } });
const readBack = await r.text();
check("reading gives the same bytes back", r.status === 200 && readBack === DATA);
check("reading carries the ETag of the object and the CORS header",
  r.headers.get("ETag") === j.etag && r.headers.get("Access-Control-Allow-Origin") === "*");
const tag = j.etag;
r = await hit("GET", "/?ping=1", { headers: { "X-Token": TOKEN } });
j = await body(r);
check("?ping=1 reports the etag and the real size", j.etag === tag && j.bytes === Buffer.byteLength(DATA), JSON.stringify(j));

/* ---------- 6. the conflict guard ---------- */
r = await put(DATA2, { "If-Match": '"0000000000000000000000000000dead"' });
j = await body(r);
check("a stale If-Match is 409", r.status === 409 && j.where === "if-match", r.status + " " + JSON.stringify(j));
check("the 409 hands back the etag to reload with", j.etag === tag, j.etag);
check("the data did not change", R2.text(FILE) === DATA);
r = await put(DATA2, { "If-Match": "W/" + tag });
check("the weak form of the same etag is accepted", r.status === 200, r.status);
check("and that write landed", R2.text(FILE) === DATA2);
r = await put(DATA);
check("a device that sends no If-Match still writes", r.status === 200 && R2.text(FILE) === DATA);

/* ---------- 7. the race a conditional write has to survive ---------- */
R2.reset(); R2.seed(FILE, DATA2);
R2.refuse = 1;                       // R2 cannot match the etag although nothing changed
r = await put(DATA);
j = await body(r);
check("a conditional write R2 refuses while nothing changed still lands", r.status === 200 && R2.text(FILE) === DATA, r.status + " " + JSON.stringify(j));
check("and it took a second, guarded attempt on the file", R2.puts(FILE).length === 2, JSON.stringify(R2.puts(FILE)));

R2.reset(); R2.seed(FILE, DATA2);
R2.refuse = 1;
R2.onConditionalPut = () => { R2.onConditionalPut = null; R2.seed(FILE, OTHER); };   // another device wrote in between
r = await put(DATA);
j = await body(r);
check("a write that another device beat to it is 409", r.status === 409 && j.where === "write-race", r.status + " " + JSON.stringify(j));
check("and the other device's data is still there", R2.text(FILE) === OTHER);

R2.reset(); R2.seed(FILE, DATA2);
R2.refuse = 1;
R2.onConditionalPut = (key, opts) => { if ("uploadedBefore" in (opts.onlyIf || {})) R2.seed(FILE, OTHER); };
r = await put(DATA);
j = await body(r);
check("someone writing between the look and the guarded write is 409 as well", r.status === 409 && j.where === "write-race", r.status + " " + JSON.stringify(j));
check("and that data survives too", R2.text(FILE) === OTHER);

/* ---------- 8. the daily snapshots ---------- */
R2.reset(); R2.seed(FILE, DATA2);
const snapKey = "snapshots/" + today() + ".json";
await put(DATA);
check("the first write of the day keeps the previous content", R2.text(snapKey) === DATA2, R2.keys().join(", "));
await put(DATA2);
check("a second write the same day leaves that snapshot alone", R2.text(snapKey) === DATA2);

R2.reset(); R2.seed(FILE, DATA2);
for (let d = 1; d <= 16; d++) R2.seed("snapshots/2026-01-" + String(d).padStart(2, "0") + ".json", "old " + d);
R2.seed("snapshots/my own backup.json", "mine");
await put(DATA);
const snaps = R2.keys().filter((k) => /^snapshots\/\d{4}-\d{2}-\d{2}\.json$/.test(k));
check("trimming keeps fourteen daily files", snaps.length === 14, snaps.length + ": " + snaps.join(", "));
check("the oldest three are gone and the fourth is not", !R2.text("snapshots/2026-01-03.json") && R2.text("snapshots/2026-01-04.json") === "old 4");
check("today's snapshot is one of the fourteen", snaps.includes(snapKey));
check("a backup you put there by hand survives", R2.text("snapshots/my own backup.json") === "mine");

/* ---------- 9. anything else ---------- */
r = await hit("DELETE", "/", { headers: { "X-Token": TOKEN } });
check("a method the endpoint does not know is 405", r.status === 405 && (await body(r)).error === "method not allowed");

console.log(`\n${ok} OK, ${fail} FAIL`);
process.exit(fail ? 1 : 0);
