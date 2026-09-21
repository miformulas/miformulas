"""One write at a time (build 260914b): a change made while a save is in flight must not be
reported as saved, must not send a second write with the old ETag, and must be written afterwards.
Also: browser storage that refuses to store, and the browser copy that is dropped for a data file.
Build 260915: a daily snapshot restored while the server is unreachable is not written over the
server's data, and a data file whose first write fails leaves the browser copy in place.
Uses a fake server inside the page (fetch is replaced before the app boots), so no webserver of its
own is needed beyond the one serving the app on port 8765 (see README)."""
import json
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

# a server that answers GET at once and holds every PUT until the test releases it
FAKE_SERVER = """
  window.__srv = {etag: "E0", data: {schema: 1, formulas: [], materials: [], materialCategories: [], formulaCategories: []},
                  puts: [], pending: [], codes: []};
  const realFetch = window.fetch.bind(window);
  window.fetch = (url, opt) => {
    const u = String(url && url.url ? url.url : url), o = opt || {};
    if (u.indexOf("data.php") >= 0){
      if ((o.method || "GET") === "GET")
        return Promise.resolve(new Response(JSON.stringify(__srv.data), {status: 200, headers: {ETag: __srv.etag}}));
      const ifm = (o.headers || {})["If-Match"] || "";
      const body = o.body;
      __srv.puts.push({ifm, body});
      return new Promise(res => __srv.pending.push(() => {
        if (ifm !== __srv.etag){ __srv.codes.push(409); res(new Response("{}", {status: 409})); return; }
        __srv.data = JSON.parse(body); __srv.etag = "E" + __srv.puts.length; __srv.codes.push(200);
        res(new Response("{}", {status: 200, headers: {ETag: __srv.etag}}));
      }));
    }
    return realFetch(url, opt);
  };
  window.__release = () => { const f = __srv.pending.shift(); if (f) f(); return !!f; };
"""

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- 1. server mode: a change during a write ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    errs = []; msgs = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.add_init_script(FAKE_SERVER)
    page.goto(URL); page.wait_for_timeout(1500)
    check("the app is in server mode", page.evaluate("[REMOTE, API]") == [True, "data.php"])

    page.evaluate("""() => { DATA.formulas.push({id: "f-a", name: "A", versions: []}); markDirty(); }""")
    page.wait_for_timeout(3000)                       # the autosave fires and hangs in the PUT
    check("one write is on its way", page.evaluate("__srv.puts.length") == 1)

    page.evaluate("""() => { DATA.formulas.push({id: "f-b", name: "B", versions: []}); markDirty(); }""")
    page.evaluate("() => { saveData(); }")             # Ctrl+S while the first write is in flight (do not await it)
    page.wait_for_timeout(1200)
    check("no second write with the same ETag", page.evaluate("__srv.puts.length") == 1)

    page.evaluate("__release()"); page.wait_for_timeout(800)
    check("the first write is not called saved, because B came after it",
          page.evaluate("DIRTY") is True and not page.locator("#saveState").inner_text().startswith("Saved"))
    check("the second write follows by itself, with the new ETag",
          page.evaluate("__srv.puts.length") == 2 and page.evaluate("__srv.puts[1].ifm") == "E1")

    page.evaluate("__release()"); page.wait_for_timeout(800)
    check("and then everything is saved", page.evaluate("DIRTY") is False
          and page.locator("#saveState").inner_text().startswith("Saved"))
    check("the server holds both changes",
          page.evaluate("__srv.data.formulas.map(f => f.name).join()") == "A,B")
    check("no conflict was reported", 409 not in page.evaluate("__srv.codes")
          and not any("another device" in m for m in msgs))

    # ---------- 1b. wie saveData() afwacht, wacht tot de data er echt is (bouw 260918a) ----------
    # Settings met een gewijzigde server en Forget doen "if (DIRTY) await saveData(); location.reload()"
    page.evaluate("""() => { window.__res = "wacht";
        DATA.formulas.push({id: "f-c", name: "C", versions: []}); markDirty();
        saveData().then(v => { window.__res = v; }); }""")
    page.wait_for_timeout(700)
    check("saveData geeft niets terug zolang de PUT hangt", page.evaluate("__res") == "wacht")
    page.evaluate("""() => { DATA.formulas.push({id: "f-d", name: "D", versions: []}); markDirty(); }""")
    page.evaluate("__release()"); page.wait_for_timeout(700)
    check("en ook niet na de eerste PUT, want D kwam er tijdens het schrijven bij",
          page.evaluate("__res") == "wacht" and page.evaluate("DIRTY") is True)
    page.evaluate("__release()"); page.wait_for_timeout(700)
    check(f"pas als alles weg is geeft hij true ({page.evaluate('__res')})",
          page.evaluate("__res") is True and page.evaluate("DIRTY") is False)
    check("en de server heeft C en D",
          page.evaluate("__srv.data.formulas.map(f => f.name).join()") == "A,B,C,D")
    check("no page errors", not errs)
    ctx.close()

    # ---------- 2. browser storage that cannot store ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.click("#btnStarter"); pg.wait_for_timeout(3400)      # the autosave runs 2.5 s after the change
    check("the starter set is kept in this browser", pg.evaluate("DEMO") is True
          and pg.locator("#saveState").inner_text().startswith("Saved"))
    pg.evaluate("idb.db = null")                       # from here IndexedDB refuses everything
    pg.evaluate("""() => { DATA.formulas[0].name = "Renamed"; markDirty(); }""")
    pg.wait_for_timeout(3200)
    state = pg.locator("#saveState").inner_text()
    check(f"it says so instead of “Saved” ({state!r})", "Browser storage is not available" in state)
    check("and the change stays marked as unsaved", pg.evaluate("DIRTY") is True)
    ctx.close()

    # ---------- 3. a data file replaces the browser copy ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page()
    pg.on("dialog", lambda d: d.accept())
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg.add_init_script("""
      window.__file = "";
      function FakeHandle(name){ this.name = name; this.kind = "file"; this.__fake = true; }
      FakeHandle.prototype.queryPermission = async () => "granted";
      FakeHandle.prototype.requestPermission = async () => "granted";
      FakeHandle.prototype.getFile = async function(){ return new File([window.__file || "{}"], this.name); };
      FakeHandle.prototype.createWritable = async () => ({ write: async s => { window.__file = s; }, close: async () => {} });
      window.showSaveFilePicker = async opts => new FakeHandle(opts.suggestedName);
    """)
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.click("#btnStarter"); pg.wait_for_timeout(3400)      # wait for the autosave into browser storage
    check("the browser copy exists first", bool(pg.evaluate("idb.get('demoData')")))
    pg.click("#storageHintSave"); pg.wait_for_timeout(500)
    pg.click("#dlgOk"); pg.wait_for_timeout(1500)
    check("the data is now in the file", bool(pg.evaluate("!!HANDLE")) and "formulas" in pg.evaluate("window.__file"))
    check("and the browser copy is dropped, so Forget cannot bring an old one back",
          pg.evaluate("idb.get('demoData')") is None)
    ctx.close()

    # ---------- 4. build 260915: a snapshot restored while the server is unreachable is not written over the server ----------
    SWITCHABLE = """
      window.__srv = {etag: "E0", data: {schema: 1, formulas: [{id:"f-s", name:"Server formula", versions: []}], materials: [],
                      materialCategories: [], formulaCategories: []}, puts: [], gets: 0};
      const realFetch = window.fetch.bind(window);
      window.fetch = (url, opt) => {
        const u = String(url && url.url ? url.url : url), o = opt || {};
        if (u.indexOf("data.php") >= 0){
          const mode = localStorage.getItem("__srvmode") || "up";      // up | down | empty
          if (mode === "down") return Promise.reject(new TypeError("Failed to fetch"));
          if ((o.method || "GET") === "GET"){
            __srv.gets++;
            if (mode === "empty") return Promise.resolve(new Response("no", {status: 404}));
            return Promise.resolve(new Response(JSON.stringify(__srv.data), {status: 200, headers: {ETag: __srv.etag}}));
          }
          __srv.puts.push({ifm: (o.headers || {})["If-Match"] || "", body: o.body});
          __srv.data = JSON.parse(o.body); __srv.etag = "E" + __srv.puts.length;
          return Promise.resolve(new Response("{}", {status: 200, headers: {ETag: __srv.etag}}));
        }
        return realFetch(url, opt);
      };
    """
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    errs = []; msgs = []
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.add_init_script(SWITCHABLE)
    pg.goto(URL); pg.wait_for_timeout(1500)
    check("morning: loaded from the server, snapshot kept",
          pg.evaluate("DATA.formulas.length") == 1 and bool(pg.evaluate("idb.get('dailyBak').then(b => !!(b && b.json))")))
    pg.evaluate("""() => { localStorage.setItem("__srvmode", "down"); }""")
    pg.reload(); pg.wait_for_timeout(1500)
    check("evening, server unreachable: the start screen offers the snapshot",
          pg.locator("#btnSnap").is_visible() and pg.locator("#btnOpen").inner_text() == "Connect to server")
    pg.click("#btnSnap"); pg.wait_for_timeout(3500)          # long enough for an autosave, if one were scheduled
    state = pg.locator("#saveState").inner_text()
    check(f"the snapshot is shown but not marked for saving ({state!r})", "not on the server" in state and pg.evaluate("DIRTY") is False)
    # the server comes back with the day's work on it (someone saved meanwhile), and the user makes a change
    pg.evaluate("""() => { localStorage.setItem("__srvmode", "up"); __srv.data.formulas.push({id:"f-day", name:"Day's work", versions: []}); __srv.etag = "E9"; }""")
    pg.evaluate("""() => { DATA.formulas.push({id:"f-x", name:"Evening change", versions: []}); markDirty(); }""")
    pg.wait_for_timeout(3500)
    state = pg.locator("#saveState").inner_text()
    check(f"before writing, the app reads the server and refuses to overwrite what is there ({state!r})",
          "was not loaded" in state and pg.evaluate("__srv.puts.length") == 0 and pg.evaluate("__srv.gets") >= 1)
    check("and says so once", sum("not loaded in this session" in m for m in msgs) == 1)
    check("the day's work is still on the server", pg.evaluate("__srv.data.formulas.some(f => f.id === 'f-day')"))
    # the same snapshot, but the server holds nothing (the case the snapshot is for): it is written
    pg.evaluate("""() => { localStorage.setItem("__srvmode", "empty"); }""")
    pg.reload(); pg.wait_for_timeout(1500)
    check("server empty: the start screen offers the snapshot next to the starter set",
          pg.locator("#btnSnap").is_visible() and pg.locator("#btnStarter").is_visible())
    pg.click("#btnSnap"); pg.wait_for_timeout(3500)
    check("and then the snapshot is written to the server",
          pg.evaluate("__srv.puts.length") == 1 and pg.locator("#saveState").inner_text().startswith("Saved"))
    check("no page errors", not errs)
    ctx.close()

    # ---------- 5. build 260915: Save to a data file whose first write fails keeps the browser copy ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    msgs = []
    pg = ctx.new_page()
    pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg.add_init_script("""
      function LockedHandle(name){ this.name = name; this.kind = "file"; }
      LockedHandle.prototype.queryPermission = async () => "granted";
      LockedHandle.prototype.requestPermission = async () => "granted";
      LockedHandle.prototype.getFile = async function(){ return new File(["{}"], this.name); };
      LockedHandle.prototype.createWritable = async () => { throw new DOMException("The file is locked", "NoModificationAllowedError"); };
      window.showSaveFilePicker = async opts => new LockedHandle(opts.suggestedName);
    """)
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.click("#btnStarter"); pg.wait_for_timeout(3400)
    check("the browser copy exists first", bool(pg.evaluate("idb.get('demoData')")))
    msgs.clear()
    pg.click("#storageHintSave"); pg.wait_for_timeout(500)
    pg.click("#dlgOk"); pg.wait_for_timeout(1500)
    check(f"the failed write is reported ({msgs})", any("could not be written" in m for m in msgs))
    check("the app stays in browser storage, with its copy intact",
          pg.evaluate("!!HANDLE") is False and bool(pg.evaluate("idb.get('demoData')")) and pg.evaluate("idb.get('fileHandle')") is None)
    pg.wait_for_timeout(3200)
    check("and saving to the browser continues", pg.locator("#saveState").inner_text().startswith("Saved"))
    ctx.close()

    # ---------- 6. bouw 260918a: een PUT-antwoord zonder zichtbare ETag-header ----------
    # cross-origin zonder Access-Control-Expose-Headers: de header is onzichtbaar, het lichaam draagt de etag
    def etag_server(header, body):
        return """
          window.__srv = {etag: "E0", data: {schema: 1, formulas: [], materials: [], materialCategories: [], formulaCategories: []},
                          puts: [], codes: []};
          const realFetch = window.fetch.bind(window);
          window.fetch = (url, opt) => {
            const u = String(url && url.url ? url.url : url), o = opt || {};
            if (u.indexOf("data.php") >= 0){
              if ((o.method || "GET") === "GET")
                return Promise.resolve(new Response(JSON.stringify(__srv.data), {status: 200, headers: {ETag: __srv.etag}}));
              const ifm = (o.headers || {})["If-Match"] || "";
              __srv.puts.push({ifm});
              if (ifm && ifm !== __srv.etag){ __srv.codes.push(409); return Promise.resolve(new Response("{}", {status: 409})); }
              __srv.data = JSON.parse(o.body); __srv.etag = "E" + __srv.puts.length; __srv.codes.push(200);
              const h = %s, b = %s;
              return Promise.resolve(new Response(JSON.stringify(b), {status: 200, headers: h}));
            }
            return realFetch(url, opt);
          };
        """ % (header, body)

    for naam, hdr, bod, verwacht_ifm, waarschuwing in [
        ("de etag staat alleen in het lichaam", "{}", '{ok: true, etag: __srv.etag}', True, False),
        ("de etag is nergens te zien", "{}", "{ok: true}", False, True)]:
        ctx = b.new_context(viewport={"width": 1200, "height": 900})
        pg = ctx.new_page(); m2 = []; e2 = []
        pg.on("pageerror", lambda e: e2.append(str(e)))
        pg.on("dialog", lambda d: (m2.append(d.message), d.accept()))
        pg.add_init_script(etag_server(hdr, bod))
        pg.goto(URL); pg.wait_for_timeout(1500)
        for n in ("X", "Y", "Z"):
            pg.evaluate("n => { DATA.formulas.push({id: 'f-' + n, name: n, versions: []}); markDirty(); }", n)
            pg.evaluate("() => saveData()"); pg.wait_for_timeout(500)
        codes = pg.evaluate("__srv.codes")
        state = pg.locator("#saveState").inner_text()
        check(f"{naam}: drie schrijfacties, geen enkele 409 ({codes})", codes == [200, 200, 200])
        check(f"{naam}: de koptekst meldt geen conflict ({state!r})", "Conflict" not in state and state.startswith("Saved"))
        check(f"{naam}: de server heeft alle drie",
              pg.evaluate("__srv.data.formulas.map(f => f.name).join()") == "X,Y,Z")
        ifms = pg.evaluate("__srv.puts.map(p => p.ifm)")
        if verwacht_ifm:
            check(f"{naam}: de volgende PUT stuurt de nieuwe If-Match ({ifms})", ifms[1] == "E1" and ifms[2] == "E2")
            check(f"{naam}: en er komt geen waarschuwing", not any("ETag" in x for x in m2))
        else:
            check(f"{naam}: de volgende PUT stuurt een lege If-Match ({ifms})", ifms[1] == "" and ifms[2] == "")
            check(f"{naam}: met één waarschuwing, niet bij elke schrijfactie",
                  len([x for x in m2 if "ETag" in x]) == 1)
        check(f"{naam}: geen paginafouten ({e2[:1]})", not e2)
        ctx.close()

    # ---------- 7. B14 (bouw 260920d): Ctrl+S met een veld dat nog de focus heeft ----------
    # De knop Save had het probleem niet, want een muisklik geeft eerst blur. Bij de sneltoets bleef de notitie
    # in het veld staan terwijl de statusregel "Saved" zei en DIRTY op false ging: geen beforeunload meer.
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page(); e3 = []
    pg.on("pageerror", lambda e: e3.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.click("#btnStarter"); pg.wait_for_timeout(1400)
    pg.evaluate("""() => { const f = DATA.formulas.find(x => x.versions.length && !x.frozenImport && !x.versions[0].frozen);
        window.__nid = f.id; NOTESOPEN = true; switchTab("F", f.id, {type:"v", idx: f.versions.length-1}); }""")
    pg.wait_for_timeout(800)
    pg.evaluate("""() => { const d = document.querySelector("#notesEd")?.closest("details"); if (d) d.open = true; }""")
    pg.wait_for_timeout(300)
    pg.click("#notesEd"); pg.type("#notesEd", "een waarneming die niet verloren mag gaan")
    pg.keyboard.press("Control+s"); pg.wait_for_timeout(900)
    r = pg.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__nid);
        return {data: (f.versions[f.versions.length-1].notes || ""), dirty: DIRTY,
                status: (document.querySelector("#saveState")?.textContent || "").trim()}; }""")
    check(f"Ctrl+S bewaart de notitie die nog in het veld staat ({r['data'][:24]!r})",
          "een waarneming die niet verloren mag gaan" in r["data"])
    check(f"en 'Saved' betekent dan ook echt bewaard ({r['dirty']}, {r['status'][:22]!r})",
          r["dirty"] is False and r["status"].startswith("Saved"))
    # hetzelfde voor een gewichtsveld dat nog de focus heeft
    pg.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__nid);
        window.__w0 = f.versions[f.versions.length-1].lines[0].weightG; }""")
    veld = pg.locator("input.w").first
    veld.click(); veld.fill("7.25")
    pg.keyboard.press("Control+s"); pg.wait_for_timeout(900)
    r = pg.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__nid);
        return {nu: f.versions[f.versions.length-1].lines[0].weightG, voor: window.__w0, dirty: DIRTY}; }""")
    check(f"ook een gewicht dat nog in het veld staat ({r})", r["nu"] == 7.25 and r["dirty"] is False)
    check(f"geen paginafouten ({e3[:1]})", not e3)
    ctx.close()

    # ---------- 8. B6 (bouw 260920h): Settings en Forget herladen niet over een mislukte schrijfactie heen ----------
    # saveData() zegt of het gelukt is; dat antwoord weggooien en toch herladen is hoe de wijziging verdwijnt.
    FAIL_PUT = """
      window.__srv = {etag:"E0", puts:0,
        data:{schema:1, formulas:[{id:"f-serv", name:"Op de server", versions:[{v:1, date:"2026-09-01", lines:[]}]}],
              materials:[], materialCategories:["Uncategorised"], formulaCategories:["Uncategorised"]}};
      const realFetch = window.fetch.bind(window);
      window.fetch = (url, opt) => {
        const u = String(url && url.url ? url.url : url), o = opt || {};
        if (u.indexOf("data.php") >= 0){
          if ((o.method || "GET") === "GET")
            return Promise.resolve(new Response(JSON.stringify(__srv.data), {status:200, headers:{ETag:__srv.etag}}));
          __srv.puts++; return Promise.resolve(new Response("{}", {status:500}));
        }
        return realFetch(url, opt);
      };
    """
    for naam, antwoord in (("Cancel", False), ("OK", True)):
        ctx = b.new_context(viewport={"width": 1200, "height": 900})
        pg = ctx.new_page(); m4 = []
        pg.on("dialog", lambda d: (m4.append(d.message), d.accept() if antwoord else d.dismiss()))
        pg.add_init_script(FAIL_PUT)
        pg.goto(URL); pg.wait_for_timeout(1600)
        pg.evaluate("""() => { DATA.formulas.push({id:"f-nieuw", name:"Net getypt", versions:[{v:1, date:today(), lines:[]}]});
            buildUsage(); markDirty(); }""")
        pg.wait_for_timeout(2600)                       # de autosave probeert en mislukt
        state = pg.locator("#saveState").inner_text()
        check(f"{naam}: de balk zegt dat het niet gelukt is ({state!r})", "Save failed" in state and pg.evaluate("DIRTY") is True)
        pg.click("#btnSettings"); pg.wait_for_timeout(700)
        pg.fill("#setServer", "data.php?v=2")
        m4.clear()
        pg.click("#dlgOk"); pg.wait_for_timeout(2500)
        gevraagd = any("could not be saved" in x for x in m4)
        check(f"{naam}: de app vraagt eerst, in plaats van te herladen ({[x[:40] for x in m4]})", gevraagd)
        if not antwoord:
            r = pg.evaluate("""() => idb.get("serverUrl").then(u => ({url: u,
                formules: DATA ? DATA.formulas.map(f => f.name) : null, dirty: DIRTY}))""")
            check(f"Cancel: je blijft staan en niets is toegepast ({r})",
                  r["formules"] and "Net getypt" in r["formules"] and r["url"] != "data.php?v=2" and r["dirty"] is True)
        else:
            r = pg.evaluate("""() => idb.get("serverUrl").then(u => ({url: u,
                formules: DATA ? DATA.formulas.map(f => f.name) : null}))""")
            check(f"OK: de server is gewijzigd en de app herladen ({r})",
                  r["url"] == "data.php?v=2" and r["formules"] == ["Op de server"])
        ctx.close()

    # Forget: dezelfde vraag, en de onthouden verwijzing wordt pas daarna gewist
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page(); m5 = []
    pg.on("dialog", lambda d: (m5.append(d.message),
          d.dismiss() if "could not be saved" in d.message else d.accept()))
    pg.add_init_script(FAIL_PUT)
    pg.goto(URL); pg.wait_for_timeout(1600)
    pg.evaluate("""() => idb.set("fileHandle", {name: "mijn-data.json"})""")
    pg.evaluate("""() => { DATA.formulas.push({id:"f-n2", name:"Net getypt", versions:[{v:1, date:today(), lines:[]}]});
        buildUsage(); markDirty(); }""")
    pg.wait_for_timeout(2600)
    pg.click("#btnSettings"); pg.wait_for_timeout(700)
    check("Forget staat er voor een onthouden bestand", pg.locator("#setForget").count() == 1)
    m5.clear()
    pg.click("#setForget"); pg.wait_for_timeout(1500)
    r = pg.evaluate("""() => idb.get("fileHandle").then(h => ({handle: h && h.name,
        formules: DATA ? DATA.formulas.map(f => f.name) : null}))""")
    check(f"Forget vraagt het ook ({[x[:36] for x in m5]})", any("could not be saved" in x for x in m5))
    check(f"en laat bij Cancel de onthouden verwijzing staan ({r})",
          r["handle"] == "mijn-data.json" and r["formules"] and "Net getypt" in r["formules"])
    ctx.close()

    # ---------- 9. B7 (bouw 260920h): een 404 van daarnet is geen vrijbrief om te overschrijven ----------
    EMPTY_THEN_FULL = """
      window.__srv = {etag:"E9", leeg:true, puts:[],
        data:{schema:1, formulas:[{id:"f-echt", name:"Echt werk", versions:[{v:1, date:"2026-09-01", lines:[]}]}],
              materials:[], materialCategories:["Uncategorised"], formulaCategories:["Uncategorised"]}};
      const realFetch = window.fetch.bind(window);
      window.fetch = (url, opt) => {
        const u = String(url && url.url ? url.url : url), o = opt || {};
        if (u.indexOf("data.php") >= 0){
          if ((o.method || "GET") === "GET"){
            if (__srv.leeg){ __srv.leeg = false; return Promise.resolve(new Response("", {status:404})); }
            return Promise.resolve(new Response(JSON.stringify(__srv.data), {status:200, headers:{ETag:__srv.etag}}));
          }
          __srv.puts.push({ifm: (o.headers||{})["If-Match"], n: JSON.parse(o.body).formulas.length});
          __srv.data = JSON.parse(o.body); return Promise.resolve(new Response("{}", {status:200, headers:{ETag:"E10"}}));
        }
        return realFetch(url, opt);
      };
    """
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page(); m6 = []
    pg.on("dialog", lambda d: (m6.append(d.message), d.accept()))
    pg.add_init_script(EMPTY_THEN_FULL)
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("""() => idb.set("serverUrl", "data.php")""")
    pg.reload(); pg.wait_for_timeout(2000)
    check("de server gaf 404, dus het startscherm biedt de starterset aan",
          pg.evaluate("[REMOTE, SERVER_EMPTY, LOADED]") == [True, True, False])
    m6.clear()
    pg.click("#btnStarter"); pg.wait_for_timeout(3000)
    r = pg.evaluate("""() => ({puts: __srv.puts, opDeServer: __srv.data.formulas.map(f => f.name)})""")
    check(f"er gaat geen schrijfactie heen ({r['puts']})", r["puts"] == [])
    check(f"en wat er intussen op de server staat, blijft staan ({r['opDeServer']})", r["opDeServer"] == ["Echt werk"])
    check(f"met een waarschuwing die zegt wat er aan de hand is ({[x[:50] for x in m6]})",
          any("was not loaded in this session" in x for x in m6))
    state = pg.locator("#saveState").inner_text()
    check(f"en de balk zegt het ook ({state!r})", "not loaded here" in state)
    ctx.close()

    # ---------- 10. D1 (bouw 260920j): een lege server met een Backup van jezelf ----------
    # "Connect to server" nam de plaats in van Open data file…, precies op het scherm waar je je eigen
    # data binnenbrengt. De knop staat er nu naast, en het bestand gaat naar de server, niet naar schijf.
    BACKUP = {"schema": 1, "formulas": [{"id": "f-mine", "name": "Uit mijn Backup", "category": "Uncategorised",
              "created": "2026-09-21", "versions": [{"v": 1, "date": "2026-09-21", "lines": []}]}],
              "materials": [], "materialCategories": [], "formulaCategories": []}
    PICKER = """
      window.__gets = 0;
      window.showOpenFilePicker = async () => [{ name: "mijn-backup.json", kind: "file",
        getFile: async () => new File([JSON.stringify(%s)], "mijn-backup.json") }];
    """ % json.dumps(BACKUP)
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page(); m7 = []; gets = []; puts = []
    pg.on("dialog", lambda d: (m7.append(d.message), d.accept()))
    def srv(route, request):
        if request.method == "GET":
            gets.append(1); route.fulfill(status=404, body="no")
        else:
            puts.append({"ifm": request.headers.get("if-match", ""), "body": request.post_data})
            route.fulfill(status=200, body='{"ok":true}', headers={"ETag": "E1"})
    pg.route("**/data.php*", srv)
    pg.add_init_script(PICKER)
    pg.goto(URL); pg.wait_for_timeout(900)
    pg.evaluate("""() => idb.set("serverUrl", "data.php")""")
    pg.reload(); pg.wait_for_timeout(1800)
    check("de server houdt nog niets, dus het startscherm blijft staan",
          pg.evaluate("[REMOTE, SERVER_EMPTY, LOADED]") == [True, True, False])
    check(f"de oude knop heet daar Connect to server ({pg.locator('#btnOpen').inner_text()!r})",
          pg.locator("#btnOpen").inner_text().strip() == "Connect to server")
    check("en Open data file… staat er nu naast", pg.locator("#btnLandOpen").is_visible()
          and pg.locator("#btnLandOpen").inner_text().strip().startswith("Open data file"))
    pg.click("#btnLandOpen"); pg.wait_for_timeout(900)
    check("het bestand opent de app met jouw formules",
          pg.evaluate("[!!DATA, DATA ? DATA.formulas.map(f => f.name) : null]") == [True, ["Uit mijn Backup"]])
    check("zonder een bestandsverwijzing vast te houden: de server is de plek",
          pg.evaluate("[HANDLE, REMOTE]") == [None, True])
    pg.wait_for_timeout(3200)
    check(f"en de eerste schrijfactie brengt het naar de server ({len(puts)} PUT)",
          len(puts) == 1 and "Uit mijn Backup" in (puts[0]["body"] or ""))
    check(f"die eerst nog eens keek, want er is hier niets geladen ({len(gets)} GET)", len(gets) >= 2)
    ctx.close()

    # ---------- 8. de pagina die stapt aan de kant schrijft meteen weg (bouw 260920o) ----------
    # Een telefoon sluit een pagina niet, ze verbergt ze, en beforeunload komt daar niet. Elke wijziging
    # stond dus 2,5 s buiten de opslag. visibilitychange en pagehide korten die wachttijd af.
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    pg = ctx.new_page()
    hfout = []
    pg.on("pageerror", lambda e: hfout.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.add_init_script(FAKE_SERVER)
    pg.goto(URL); pg.wait_for_timeout(1500)
    check("de app staat in serverstand", pg.evaluate("[REMOTE, API]") == [True, "data.php"])

    pg.evaluate("""() => { DATA.formulas.push({id: "f-h1", name: "Verborgen", versions: []}); markDirty(); }""")
    n0 = pg.evaluate("__srv.puts.length")
    pg.evaluate("""() => { Object.defineProperty(document, "visibilityState", {get: () => "hidden", configurable: true});
        document.dispatchEvent(new Event("visibilitychange")); }""")
    pg.wait_for_timeout(300)
    n1 = pg.evaluate("__srv.puts.length")
    check(f"de pagina verbergen schrijft meteen weg, ruim vóór de 2,5 s ({n0} -> {n1} PUT)", n1 == n0 + 1)
    pg.evaluate("__release()"); pg.wait_for_timeout(600)

    pg.evaluate("""() => { DATA.formulas.push({id: "f-h2", name: "Weg", versions: []}); markDirty(); }""")
    n2 = pg.evaluate("__srv.puts.length")
    pg.evaluate("""() => window.dispatchEvent(new PageTransitionEvent("pagehide", {persisted: false}))""")
    pg.wait_for_timeout(300)
    n3 = pg.evaluate("__srv.puts.length")
    check(f"en pagehide doet hetzelfde ({n2} -> {n3} PUT)", n3 == n2 + 1)
    pg.evaluate("__release()"); pg.wait_for_timeout(600)

    n4 = pg.evaluate("__srv.puts.length")
    pg.evaluate("""() => { DATA.formulas.push({id: "f-h3", name: "Gewoon", versions: []}); markDirty(); }""")
    pg.wait_for_timeout(300)
    check("zonder verbergen houdt de app haar eigen tempo aan", pg.evaluate("__srv.puts.length") == n4)
    pg.wait_for_timeout(2600)
    check(f"en schrijft ze na de gewone wachttijd alsnog ({pg.evaluate('__srv.puts.length')} PUT)",
          pg.evaluate("__srv.puts.length") == n4 + 1)
    pg.evaluate("__release()"); pg.wait_for_timeout(600)
    check("de server houdt alle drie de wijzigingen",
          pg.evaluate("__srv.data.formulas.map(f => f.name).join()") == "Verborgen,Weg,Gewoon")
    check(f"geen paginafouten ({hfout[:2]})", not hfout)
    ctx.close()

    b.close()

print(f"\n{ok} OK, {fail} FAIL")
