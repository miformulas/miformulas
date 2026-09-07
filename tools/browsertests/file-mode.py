"""Bestandsmodus (gedownloade app geopend via file://): hint, dialoog, starterset, aanmaak van het databestand, herstart met Reopen, verdwenen bestand.
Draait rechtstreeks op public\index.html; de starterset wordt vanaf schijf geserveerd omdat de test miformulas.com nabootst."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += cond; fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    page = ctx.new_page()
    written = []
    # the site is not reachable from here: serve the starter set for the absolute URL
    page.route("https://miformulas.com/data/miformulas-starter.json",
               lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                   headers={"Access-Control-Allow-Origin": "*"}))
    # fake File System Access API: showSaveFilePicker returns a handle that records what is written
    FAKE_FS = """
      // fake File System Access API. The handle is structured-clonable (methods on the prototype),
      // so the app can store it in IndexedDB; when it comes back, the prototype is re-attached.
      window.__written = [];
      function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
      FakeHandle.prototype.queryPermission = async () => window.__perm || 'granted';
      FakeHandle.prototype.requestPermission = async () => { window.__perm = 'granted'; return 'granted'; };
      FakeHandle.prototype.getFile = async function(){ if (localStorage.getItem('fakegone')) throw new DOMException('gone','NotFoundError'); return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
      FakeHandle.prototype.createWritable = async () => ({ write: async (s) => { window.__written.push(s); localStorage.setItem('fakefile', s); }, close: async () => {} });
      const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
      Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
      window.showOpenFilePicker = async () => { throw new Error('no picker in test'); };
      window.showSaveFilePicker = async (opts) => { window.__pickerOpts = opts; return new FakeHandle(opts.suggestedName); };
    """
    page.add_init_script(FAKE_FS)
    msgs = []
    page.on("console", lambda m: msgs.append(m.text))
    page.on("dialog", lambda d: (msgs.append("DIALOG " + d.message), d.dismiss()))
    page.goto(APP)
    page.wait_for_timeout(800)

    check("protocol is file:", page.evaluate("location.protocol") == "file:")
    check("build stamp 260907e", page.locator("#build").inner_text().strip() == "260907e")
    hint = page.locator("#landingHint").inner_text()
    check("hint mentions own computer", "from your own computer" in hint)
    check("hint recommends Documents\\miFormulas", "Documents\\miFormulas" in hint)
    check("hint mentions backups subfolder", "backups" in hint)
    check("hint warns that the starter set creates a new file", "Open data file" in hint and "create a new one" in hint)
    check("starter button visible", page.locator("#btnStarter").is_visible())
    check("open data file visible", page.locator("#btnOpen").is_visible())
    check("download link hidden in file mode", not page.locator("#btnDownload").is_visible())
    check("STARTER_URL absolute", page.evaluate("STARTER_URL") == "https://miformulas.com/data/miformulas-starter.json")

    page.click("#btnStarter")
    page.wait_for_timeout(1200)
    check("dialog explains the data file", page.locator("#dlg").evaluate("d => d.open") and "miformulas-data.json" in page.locator("#dlg").inner_text())
    check("dialog names Documents\\miFormulas and backups", "Documents\\miFormulas" in page.locator("#dlg").inner_text() and "backups" in page.locator("#dlg").inner_text())
    check("picker not yet opened", page.evaluate("window.__pickerOpts") is None)
    # Cancel in the dialog: back to the start screen with a hint
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    check("dialog cancel: landing stays", page.locator("#landing").is_visible())
    check("dialog cancel: hint says nothing saved", "No data file was created" in page.locator("#landingHint").inner_text())
    # again, now through Choose location
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    check("OK button says Choose location", page.locator("#dlgOk").inner_text().startswith("Choose location"))
    page.click("#dlgOk")
    page.wait_for_timeout(1500)
    check("landing gone", not page.locator("#landing").is_visible())
    opts = page.evaluate("window.__pickerOpts")
    check("save picker suggested miformulas-data.json", opts and opts.get("suggestedName") == "miformulas-data.json")
    check("save picker id miformulas-data", opts and opts.get("id") == "miformulas-data")
    check("save picker starts in Documents", opts and opts.get("startIn") == "documents")
    w = page.evaluate("window.__written")
    check("data file written once", len(w) == 1)
    d = json.loads(w[0]) if w else {}
    check("written file has 16 formulas", len(d.get("formulas", [])) == 16)
    check("written file has 199 materials", len(d.get("materials", [])) == 199)
    st = page.locator("#saveState").inner_text()
    check("state shows Saved (file)", st.startswith("Saved") and "browser" not in st)
    check("no dialogs", not any(m.startswith("DIALOG") for m in msgs))
    check("file handle stored", page.evaluate("idb.get('fileHandle').then(h => !!h && h.name)") == "miformulas-data.json")
    page.evaluate("localStorage.setItem('fakefile', window.__written.at(-1))")

    # restart: same browser profile, permission back to "prompt" -> Reopen, no starter set
    pr = ctx.new_page()
    pr.add_init_script(FAKE_FS + " window.__perm = 'prompt';")
    pr.goto(APP); pr.wait_for_timeout(1000)
    check("restart: landing shown", pr.locator("#landing").is_visible())
    check("restart: Reopen button visible", pr.locator("#btnReopen").is_visible() and "miformulas-data.json" in pr.locator("#btnReopen").inner_text())
    check("restart: starter button hidden", not pr.locator("#btnStarter").is_visible())
    hr = pr.locator("#landingHint").inner_text()
    check("restart: hint says file is remembered", "is remembered" in hr and "miformulas-data.json" in hr)
    pr.click("#btnReopen"); pr.wait_for_timeout(1200)
    check("restart: reopened, landing gone", not pr.locator("#landing").is_visible())
    check("restart: 16 formulas loaded", pr.evaluate("DATA.formulas.length") == 16)

    # restart after the data file was deleted: Reopen fails -> forget it, offer the starter set
    pg = ctx.new_page()
    pg.route("https://miformulas.com/data/miformulas-starter.json",
             lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                 headers={"Access-Control-Allow-Origin": "*"}))
    pg.add_init_script(FAKE_FS + " window.__perm = 'prompt';")
    pg.goto(APP); pg.wait_for_timeout(1000)
    pg.evaluate("localStorage.setItem('fakegone', '1')")
    check("gone: Reopen offered first", pg.locator("#btnReopen").is_visible() and not pg.locator("#btnStarter").is_visible())
    pg.click("#btnReopen"); pg.wait_for_timeout(1000)
    check("gone: landing stays", pg.locator("#landing").is_visible())
    check("gone: Reopen hidden", not pg.locator("#btnReopen").is_visible())
    check("gone: starter offered", pg.locator("#btnStarter").is_visible())
    check("gone: hint explains", "could not be opened" in pg.locator("#landingHint").inner_text())
    check("gone: handle forgotten", pg.evaluate("idb.get('fileHandle').then(h => !h)"))
    pg.evaluate("localStorage.removeItem('fakegone')")
    pg.click("#btnStarter"); pg.wait_for_timeout(1200); pg.click("#dlgOk"); pg.wait_for_timeout(1500)
    check("gone: starter set creates a new file", not pg.locator("#landing").is_visible() and pg.evaluate("DATA.formulas.length") == 16)
    pg.evaluate("idb.set('fileHandle', null)"); pg.evaluate("localStorage.removeItem('fakefile')")

    # cancelled picker: back to the start screen
    page2 = ctx.new_page()
    page2.route("https://miformulas.com/data/miformulas-starter.json",
                lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                    headers={"Access-Control-Allow-Origin": "*"}))
    page2.add_init_script("window.showSaveFilePicker = async () => { throw new DOMException('cancel','AbortError'); }; window.showOpenFilePicker = async () => {};")
    page2.goto(APP); page2.wait_for_timeout(800)
    page2.click("#btnStarter"); page2.wait_for_timeout(1200); page2.click("#dlgOk"); page2.wait_for_timeout(1000)
    check("cancelled picker: landing stays", page2.locator("#landing").is_visible())
    check("cancelled picker: hint says nothing saved", "No data file was created" in page2.locator("#landingHint").inner_text())
    check("cancelled picker: no file handle stored", page2.evaluate("idb.get('fileHandle').then(h => !h)"))

    # offline: clear message
    page3 = ctx.new_page()
    page3.route("https://miformulas.com/data/miformulas-starter.json", lambda r: r.abort())
    dl = []
    page3.on("dialog", lambda d: (dl.append(d.message), d.dismiss()))
    page3.goto(APP); page3.wait_for_timeout(800)
    page3.click("#btnStarter"); page3.wait_for_timeout(1500)
    check("offline: alert mentions internet", any("internet connection" in m for m in dl))
    check("offline: landing stays, no dialog", page3.locator("#landing").is_visible() and not page3.locator("#dlg").evaluate("d => d.open"))
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
