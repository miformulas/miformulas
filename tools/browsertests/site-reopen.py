"""Reopen op de site (browseropslagstand, http): een eerder geopend databestand wordt onthouden en aangeboden.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
URL = "http://localhost:8765/index.html"
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += cond; fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

FAKE_FS = """
  window.__written = [];
  function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
  FakeHandle.prototype.queryPermission = async () => window.__perm || 'granted';
  FakeHandle.prototype.requestPermission = async () => { window.__perm = 'granted'; return 'granted'; };
  FakeHandle.prototype.getFile = async function(){ if (localStorage.getItem('fakegone')) throw new DOMException('gone','NotFoundError'); return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
  FakeHandle.prototype.createWritable = async () => ({ write: async (s) => { window.__written.push(s); localStorage.setItem('fakefile', s); }, close: async () => {} });
  const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
  Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
  window.showOpenFilePicker = async (opts) => { window.__openOpts = opts; return [new FakeHandle('mydata.json')]; };
  window.showSaveFilePicker = async (opts) => new FakeHandle(opts.suggestedName);
"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    def new_page(extra="", accept=False):
        pg = ctx.new_page()
        pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="not here"))
        pg.add_init_script(FAKE_FS + extra)
        pg.on("dialog", lambda d: d.accept() if accept else d.dismiss())
        return pg

    # 1. first visit: no file remembered -> browser-storage landing with starter set
    pg = new_page()
    pg.goto(URL); pg.wait_for_timeout(1200)
    check("build stamp 260907f", pg.locator("#build").inner_text().strip() == "260907f")
    check("fresh: starter offered", pg.locator("#btnStarter").is_visible())
    check("fresh: no Reopen", not pg.locator("#btnReopen").is_visible())
    check("fresh: hint = browser storage", "stays in this browser" in pg.locator("#landingHint").inner_text())
    # open a data file on the site
    pg.evaluate("localStorage.setItem('fakefile', %s)" % json.dumps(STARTER))
    pg.click("#btnOpen"); pg.wait_for_timeout(1200)
    check("open file: app boots", not pg.locator("#landing").is_visible())
    check("open file: 16 formulas", pg.evaluate("DATA.formulas.length") == 16)
    check("open file: handle remembered", pg.evaluate("idb.get('fileHandle').then(h => h && h.name)") == "mydata.json")
    check("open file: storage bar hidden", pg.locator("#storageHint").evaluate("e => e.hidden"))
    # edit -> saved to the file, not to browser storage
    pg.evaluate("snapF(DATA.formulas[0]); DATA.formulas[0].name = 'Renamed on site'; markDirty(); saveData()")
    pg.wait_for_timeout(500)
    w = pg.evaluate("window.__written")
    check("edit: written to the file", len(w) >= 1 and "Renamed on site" in w[-1])
    check("edit: state says Saved (file)", pg.locator("#saveState").inner_text().startswith("Saved") and "browser" not in pg.locator("#saveState").inner_text())
    check("edit: browser storage untouched", pg.evaluate("idb.get('demoData').then(d => !d)"))

    # 2. next visit, permission back to prompt -> Reopen, no starter set
    pr = new_page(" window.__perm = 'prompt';")
    pr.goto(URL); pr.wait_for_timeout(1200)
    check("restart: Reopen offered", pr.locator("#btnReopen").is_visible() and "mydata.json" in pr.locator("#btnReopen").inner_text())
    check("restart: starter hidden", not pr.locator("#btnStarter").is_visible())
    check("restart: hint says remembered", "is remembered" in pr.locator("#landingHint").inner_text())
    pr.click("#btnReopen"); pr.wait_for_timeout(1200)
    check("restart: reopened with the edited data", not pr.locator("#landing").is_visible() and pr.evaluate("DATA.formulas[0].name") == "Renamed on site")

    # 3. next visit, permission still granted -> straight in
    pa = new_page(accept=True)
    pa.goto(URL); pa.wait_for_timeout(1200)
    check("granted: straight into the file", not pa.locator("#landing").is_visible() and pa.evaluate("!!HANDLE"))

    # 4. Settings: forget the remembered file -> browser-storage landing again
    pa.click("#btnSettings"); pa.wait_for_timeout(500)
    check("settings: forget button present", pa.locator("#setForget").is_visible() and "mydata.json" in pa.locator("#setForget").inner_text())
    pa.click("#setForget"); pa.wait_for_timeout(1500)
    check("forget: landing with starter set again", pa.locator("#landing").is_visible() and pa.locator("#btnStarter").is_visible() and not pa.locator("#btnReopen").is_visible())
    check("forget: handle gone", pa.evaluate("idb.get('fileHandle').then(h => !h)"))

    # 5. remembered file that no longer exists -> forget, back to browser storage with an explanation
    pa.click("#btnOpen"); pa.wait_for_timeout(800)   # remember it again
    pg2 = new_page(" window.__perm = 'prompt';")
    pg2.goto(URL); pg2.wait_for_timeout(1200)
    pg2.evaluate("localStorage.setItem('fakegone', '1')")
    check("gone: Reopen offered first", pg2.locator("#btnReopen").is_visible())
    pg2.click("#btnReopen"); pg2.wait_for_timeout(1000)
    check("gone: back to browser-storage landing", pg2.locator("#landing").is_visible() and pg2.locator("#btnStarter").is_visible() and not pg2.locator("#btnReopen").is_visible())
    h = pg2.locator("#landingHint").inner_text()
    check("gone: hint explains", "could not be opened" in h and "stays in this browser" in h)
    check("gone: handle forgotten", pg2.evaluate("idb.get('fileHandle').then(h => !h)"))
    pg2.evaluate("localStorage.removeItem('fakegone'); localStorage.removeItem('fakefile')")
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
