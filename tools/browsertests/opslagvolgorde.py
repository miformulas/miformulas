"""One write at a time (build 260914b): a change made while a save is in flight must not be
reported as saved, must not send a second write with the old ETag, and must be written afterwards.
Also: browser storage that refuses to store, and the browser copy that is dropped for a data file.
Uses a fake server inside the page (fetch is replaced before the app boots), so no webserver of its
own is needed beyond the one serving the app on port 8765 (see README)."""
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

    page.evaluate("""() => { DATA.formulas.push({id: "f-a", name: "A", versions: [], variations: []}); markDirty(); }""")
    page.wait_for_timeout(3000)                       # the autosave fires and hangs in the PUT
    check("one write is on its way", page.evaluate("__srv.puts.length") == 1)

    page.evaluate("""() => { DATA.formulas.push({id: "f-b", name: "B", versions: [], variations: []}); markDirty(); }""")
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
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
