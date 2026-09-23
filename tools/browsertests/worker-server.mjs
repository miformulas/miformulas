// A real HTTP server for server-drop.py (build 260922g): the files of the repo, and /api through the real
// server/worker.js with an R2 bucket kept in memory. It can cut a connection after the Worker has written, which is
// what a fetch replaced inside the page can never show: the browser's own handling of an answer that goes missing.
//   node worker-server.mjs <port>
// Control: GET /__ctl?drop=1 (the next PUT is written, then its socket is cut), ?closeall=1 (every answer closes its
// connection and the idle ones are closed now, so the next request runs on a fresh connection, which the browser
// does not resend when it breaks), ?seed=1 with a POST body (put that text in the bucket), ?clear=1; every call
// answers with the PUTs seen so far and what the bucket holds.
import http from "node:http"; import { readFile } from "node:fs/promises"; import { createHash } from "node:crypto";
import { extname, join, dirname } from "node:path"; import { pathToFileURL, fileURLToPath } from "node:url";
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PORT = +process.argv[2] || 8791, TOKEN = "tok-test", KEY = "miformulas-data.json";
const worker = (await import(pathToFileURL(join(ROOT, "server", "worker.js")).href)).default;
const md5 = b => createHash("md5").update(b).digest("hex");
const map = new Map(); let clock = Date.now();
const meta = (key, r) => ({ key, etag: r.etag, httpEtag: `"${r.etag}"`, size: r.bytes.length, uploaded: new Date(r.at) });
const R2 = {
  async head(k){ const r = map.get(k); return r ? meta(k, r) : null; },
  async get(k){ const r = map.get(k); return r ? { ...meta(k, r), body: new Blob([r.bytes]).stream() } : null; },
  async put(k, v, o = {}){ const only = o.onlyIf, cur = map.get(k);
    if (only && "etagMatches" in only && (!cur || cur.etag !== String(only.etagMatches).replace(/"/g, ""))) return null;
    if (only && "uploadedBefore" in only && (!cur || cur.at > only.uploadedBefore.getTime())) return null;
    const bytes = Buffer.from(await new Response(v).arrayBuffer()); clock += 1000;
    const r = { bytes, etag: md5(bytes), at: clock }; map.set(k, r); return meta(k, r); },
  async delete(k){ map.delete(k); },
  async list({ prefix = "" } = {}){ return { objects: [...map.keys()].filter(k => k.startsWith(prefix)).map(k => meta(k, map.get(k))) }; },
};
const ctl = { drop: 0, closeall: 0, puts: [] };
const TYPES = { ".html": "text/html", ".json": "application/json", ".js": "text/javascript", ".webmanifest": "application/manifest+json", ".png": "image/png", ".svg": "image/svg+xml" };
const server = http.createServer(async (req, res) => {
  const u = new URL(req.url, "http://x");
  const chunks = []; for await (const c of req) chunks.push(c); const body = Buffer.concat(chunks);
  if (ctl.closeall) res.setHeader("Connection", "close");
  if (u.pathname === "/__ctl"){
    for (const k of ["drop", "closeall"]) if (u.searchParams.has(k)) ctl[k] = +u.searchParams.get(k);
    if (u.searchParams.has("clear")){ map.clear(); ctl.puts = []; }
    if (ctl.closeall) setTimeout(() => server.closeIdleConnections(), 50);   // the browser's kept-alive connections go too
    if (u.searchParams.has("seed")){ const b = Buffer.from(body.toString()); clock += 1000; map.set(KEY, { bytes: b, etag: md5(b), at: clock }); }
    const r = map.get(KEY);
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ puts: ctl.puts, data: r ? r.bytes.toString() : null, etag: r ? r.etag : null })); return;
  }
  if (u.pathname.startsWith("/api")){
    const isPut = req.method === "PUT";
    if (isPut) ctl.puts.push({ ifm: req.headers["if-match"] || "", t: Date.now() });
    const r = await worker.fetch(new Request("http://127.0.0.1:" + PORT + req.url, { method: req.method, headers: req.headers,
      body: ["GET", "HEAD", "OPTIONS"].includes(req.method) ? undefined : body }), { TOKEN, DATA: R2 });
    if (isPut){ ctl.puts[ctl.puts.length - 1].status = r.status;
      if (ctl.drop > 0){ ctl.drop--; ctl.puts[ctl.puts.length - 1].dropped = true; req.socket.destroy(); return; } }   // written, and the answer never arrives
    const h = {}; r.headers.forEach((v, k) => h[k] = v);
    res.writeHead(r.status, h); res.end(Buffer.from(await r.arrayBuffer())); return;
  }
  try{ const p = join(ROOT, decodeURIComponent(u.pathname === "/" ? "/index.html" : u.pathname));
    const f = await readFile(p); res.writeHead(200, { "content-type": TYPES[extname(p)] || "application/octet-stream" }); res.end(f); }
  catch(e){ res.writeHead(404); res.end("not found"); }
}).listen(PORT, "127.0.0.1", () => console.log("listening " + PORT));
