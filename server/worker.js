/* miFormulas data endpoint as a Cloudflare Worker: the free counterpart of server/data.php,
   for anyone who wants the same data on a computer, a laptop and a phone without owning a server.

   Paste this file into the editor of a Worker on dash.cloudflare.com and deploy it. It needs two
   things, both on the Worker's own page rather than in the editor:

     tab Bindings                           an R2 bucket, with the variable name exactly  DATA
     tab Settings, Runtime variables and    a secret named exactly  TOKEN , holding a long random
     secrets                                string of your own

   The same token goes into the app once per device, in Settings (the gear), together with the
   address of this Worker (https://<name>.<account>.workers.dev). Section 7 of the manual walks
   through the whole set-up with screenshots; https://miformulas.com/docs/manual.html

   Opening the address in a browser is the check that it works: it answers
   {"error":"invalid token","worker":5}, because a browser sends no token. Anything else names the
   step that was missed; a plain "Hello World!" means this code has not been deployed yet.

   In the bucket: miformulas-data.json, and snapshots/YYYY-MM-DD.json, the state before the first
   save of each day, the last fourteen days. And, only if you put one there yourself, a published
   materials library: that one file is handed out without a token, which is how miformulas.com
   serves the library behind Get the latest library. Your data is never public.

   GET  /            -> JSON body, header ETag
   PUT  /            -> body = JSON, headers X-Token, If-Match (ETag from load); 409 on conflict
   GET  /?ping=1     -> {"ok":true,"worker":5,"etag":...,"bytes":...}
   GET  /miformulas-materials.json -> that public library, read-only and without a token; 404 when
                        the bucket holds no such file, which is the ordinary set-up
   OPTIONS           -> CORS preflight (the app on miformulas.com calls this from another origin)

   The ETag is the R2 object etag, and the conflict guard uses R2's conditional put, so two
   devices saving at the same moment can never overwrite each other.

   Part of miFormulas, https://github.com/miformulas/miformulas - GPL v3, see LICENSE and NOTICE. */

const VERSION = 5;   // shown in every JSON answer, so you can see which code is live
const FILE = "miformulas-data.json";
const LIST_FILE = "miformulas-materials.json";   // the one file this Worker hands out without a token
const SNAPDIR = "snapshots/";
const KEEP_DAYS = 14;
const TIMEZONE = "Europe/Brussels";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, PUT, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Token, If-Match",
  "Access-Control-Expose-Headers": "ETag",
  "Access-Control-Max-Age": "86400",
};
const BASE = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", ...CORS };

function json(status, obj, extra = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...BASE, ...extra },
  });
}
function fail(status, msg, extra = {}) { return json(status, { error: msg, worker: VERSION, ...extra }); }

function today() {
  // YYYY-MM-DD in Brussels time, like date('Y-m-d') on the NAS
  const p = new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const g = (t) => p.find((x) => x.type === t).value;
  return `${g("year")}-${g("month")}-${g("day")}`;
}

function sameTag(a, b) {
  // Cloudflare's edge may turn a strong ETag into a weak one (W/"...") when it compresses the
  // response; the app sends that back as If-Match. Compare without W/ and quotes.
  const norm = (e) => (e || "").trim().replace(/^W\//i, "").replace(/^"|"$/g, "");
  return norm(a) === norm(b);
}

const SNAPKEY = /^snapshots\/\d{4}-\d{2}-\d{2}\.json$/;   // a daily snapshot, and nothing else

function looksLikeDataFile(s) {
  // Cheap check without parsing the whole file (a few MB would not fit in the CPU budget): an object that
  // carries materials and formulas as fields. Looking for the bare words would let any text through that
  // happens to mention them, and it would be written over the good data.
  const head = s.slice(0, 64).trimStart(), tail = s.slice(-64).trimEnd();
  return head.startsWith("{") && tail.endsWith("}")
    && /"materials"\s*:/.test(s) && /"formulas"\s*:/.test(s);
}

async function snapshot(env, cur) {
  // daily snapshot of the previous content (first write of the day), keep the last KEEP_DAYS
  const key = SNAPDIR + today() + ".json";
  if (await env.DATA.head(key)) return;
  await env.DATA.put(key, cur.body, { httpMetadata: { contentType: "application/json" } });
  const list = await env.DATA.list({ prefix: SNAPDIR });
  // only the daily files count: a backup you put in this folder by hand used to be counted as a snapshot,
  // so it either ate a day or was the first thing deleted
  const keys = list.objects.map((o) => o.key).filter((k) => SNAPKEY.test(k)).sort();
  while (keys.length > KEEP_DAYS) await env.DATA.delete(keys.shift());
}

export default {
  async fetch(request, env) {
    const method = request.method;
    if (method === "OPTIONS") return new Response(null, { status: 204, headers: BASE });   // BASE, so this answer carries no-store and nosniff too

    const url = new URL(request.url);
    // One name is public on purpose, and only this one: a materials library you publish for others to
    // fetch. Read-only, GET only, no token. An ordinary bucket holds no such file and answers 404, and
    // nothing about your own data is reachable this way.
    if (method === "GET" && env.DATA && url.pathname === "/" + LIST_FILE) {
      const lib = await env.DATA.get(LIST_FILE);
      if (!lib) return fail(404, "no materials library in this bucket");
      return new Response(lib.body, {
        status: 200,
        headers: { "Content-Type": "application/json; charset=utf-8", ETag: lib.httpEtag, ...CORS,
          "X-Content-Type-Options": "nosniff",
          "Cache-Control": "public, max-age=300" },   // not BASE: a library may be cached, and a new upload is live within five minutes
      });
    }

    if (!env.TOKEN) return fail(500, "TOKEN secret is not set on the Worker");
    if (!env.DATA) return fail(500, "R2 bucket binding DATA is missing on the Worker");
    if ((request.headers.get("X-Token") || "") !== env.TOKEN) return fail(401, "invalid token");

    if (method === "GET") {
      if (url.searchParams.has("ping")) {
        const h = await env.DATA.head(FILE);
        return json(200, { ok: true, worker: VERSION, etag: h ? h.httpEtag : null, bytes: h ? h.size : 0 });
      }
      const obj = await env.DATA.get(FILE);
      if (!obj) return fail(404, "no data file yet");
      return new Response(obj.body, {
        status: 200,
        headers: { "Content-Type": "application/json; charset=utf-8", ETag: obj.httpEtag, ...BASE },
      });
    }

    if (method === "PUT" || method === "POST") {
      const body = await request.text();
      if (!body) return fail(400, "empty body");
      if (!looksLikeDataFile(body)) return fail(400, "body is not a miFormulas data file");

      const cur = await env.DATA.get(FILE);
      const curTag = cur ? cur.httpEtag : "";
      const ifMatch = request.headers.get("If-Match") || "";
      if (cur && ifMatch && !sameTag(ifMatch, curTag)) {
        await cur.body.cancel();
        return fail(409, "conflict: the data changed on another device, reload before saving", { etag: curTag, received: ifMatch, where: "if-match" });
      }
      if (cur) await snapshot(env, cur);

      // conditional write: only if nobody wrote in between (atomic on R2)
      const opts = { httpMetadata: { contentType: "application/json" } };
      let put = await env.DATA.put(FILE, body, cur ? { ...opts, onlyIf: { etagMatches: cur.etag } } : opts);
      if (!put && cur) {
        // The conditional write was refused: either someone really wrote in between, or R2 could not match the
        // etag of this object (seen with multipart uploads from the dashboard). Look again, and keep a guard:
        // writing without one leaves a window between this head and that put in which another device can write,
        // and that write would be overwritten without a word. uploadedBefore closes it on time instead of on etag.
        const now = await env.DATA.head(FILE);
        if (!now || !sameTag(now.httpEtag, curTag))
          return fail(409, "conflict: the data changed on another device, reload before saving", { etag: now ? now.httpEtag : "", received: ifMatch, where: "write-race" });
        put = await env.DATA.put(FILE, body, { ...opts, onlyIf: { uploadedBefore: now.uploaded } });
        if (!put) return fail(409, "conflict: the data changed on another device, reload before saving", { etag: now.httpEtag, received: ifMatch, where: "write-race" });
      }
      if (!put) return fail(500, "write failed");
      // put.size is what R2 stored: body.length counts characters, so every accent made the number too low,
      // while ?ping=1 and data.php report real bytes and section 7 holds them against your last Backup
      return json(200, { ok: true, etag: put.httpEtag, bytes: put.size ?? body.length, saved: new Date().toISOString() }, { ETag: put.httpEtag });
    }

    return fail(405, "method not allowed");
  },
};
