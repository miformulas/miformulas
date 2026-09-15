/* miFormulas data endpoint as a Cloudflare Worker: the free counterpart of server/data.php,
   for anyone who wants the same data on a computer, a laptop and a phone without owning a server.

   Paste this file into the editor of a Worker on dash.cloudflare.com and deploy it. It needs two
   things, both set under the Worker's Settings:

     Bindings              an R2 bucket, with the variable name exactly  DATA
     Variables and Secrets a secret named exactly  TOKEN , holding a long random string of your own

   The same token goes into the app once per device, in Settings (the gear), together with the
   address of this Worker (https://<name>.<account>.workers.dev). Section 20 of the manual walks
   through the whole set-up with screenshots; https://miformulas.com/docs/manual.html

   Opening the address in a browser is the check that it works: it answers
   {"error":"invalid token","worker":3}, because a browser sends no token. Anything else names the
   step that was missed.

   In the bucket: miformulas-data.json, and snapshots/YYYY-MM-DD.json, the state before the first
   save of each day, the last fourteen days.

   GET  /            -> JSON body, header ETag
   PUT  /            -> body = JSON, headers X-Token, If-Match (ETag from load); 409 on conflict
   GET  /?ping=1     -> {"ok":true,"etag":...,"bytes":...}
   OPTIONS           -> CORS preflight (the app on miformulas.com calls this from another origin)

   The ETag is the R2 object etag, and the conflict guard uses R2's conditional put, so two
   devices saving at the same moment can never overwrite each other.

   Part of miFormulas, https://github.com/miformulas/miformulas - GPL v3, see LICENSE and NOTICE. */

const VERSION = 3;   // shown in every JSON answer, so you can see which code is live
const FILE = "miformulas-data.json";
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

function looksLikeDataFile(s) {
  // cheap check without parsing the whole file (a few MB): an object with materials and formulas
  const head = s.slice(0, 64).trimStart();
  return head.startsWith("{") && s.includes('"materials"') && s.includes('"formulas"');
}

async function snapshot(env, cur) {
  // daily snapshot of the previous content (first write of the day), keep the last KEEP_DAYS
  const key = SNAPDIR + today() + ".json";
  if (await env.DATA.head(key)) return;
  await env.DATA.put(key, cur.body, { httpMetadata: { contentType: "application/json" } });
  const list = await env.DATA.list({ prefix: SNAPDIR });
  const keys = list.objects.map((o) => o.key).sort();
  while (keys.length > KEEP_DAYS) await env.DATA.delete(keys.shift());
}

export default {
  async fetch(request, env) {
    const method = request.method;
    if (method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

    if (!env.TOKEN) return fail(500, "TOKEN secret is not set on the Worker");
    if (!env.DATA) return fail(500, "R2 bucket binding DATA is missing on the Worker");
    if ((request.headers.get("X-Token") || "") !== env.TOKEN) return fail(401, "invalid token");

    const url = new URL(request.url);

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
        // the conditional write was refused: either someone really wrote in between, or R2 could not
        // match the etag of this object (seen with multipart uploads from the dashboard). Re-check.
        const now = await env.DATA.head(FILE);
        if (now && sameTag(now.httpEtag, curTag)) put = await env.DATA.put(FILE, body, opts);
        else return fail(409, "conflict: the data changed on another device, reload before saving", { etag: now ? now.httpEtag : "", received: ifMatch, where: "write-race" });
      }
      if (!put) return fail(500, "write failed");
      return json(200, { ok: true, etag: put.httpEtag, bytes: body.length, saved: new Date().toISOString() }, { ETag: put.httpEtag });
    }

    return fail(405, "method not allowed");
  },
};
