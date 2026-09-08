"""App screenshots for the manual (docs/img/app-*.png), taken with the starter set.

Run against a local web server with the contents of public/ on port 8765:
    cd public && python -m http.server 8765
    python tools/browsertests/screenshots.py
Chromium headless, light theme, 1280x800 at 2x, PNGs reduced to a 256-colour palette (Pillow). Nothing is written to the data file:
the starter set lives in the browser storage of a throw-away profile.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PUB, "docs", "img")
URL = "http://localhost:8765/"
APP_FILE = "file://" + os.path.join(PUB, "index.html").replace("\\", "/")
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
os.makedirs(OUT, exist_ok=True)

# fake File System Access API (as in file-mode.py), so that Save to a data file and Reopen can be shown
FAKE_FS = """
  window.__written = [];
  function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
  FakeHandle.prototype.queryPermission = async () => window.__perm || 'prompt';
  FakeHandle.prototype.requestPermission = async () => { window.__perm = 'granted'; return 'granted'; };
  FakeHandle.prototype.getFile = async function(){ return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
  FakeHandle.prototype.createWritable = async () => ({ write: async (s) => { window.__written.push(s); localStorage.setItem('fakefile', s); }, close: async () => {} });
  const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
  Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
  window.showOpenFilePicker = async () => { throw new Error('no picker'); };
  window.showSaveFilePicker = async (opts) => new FakeHandle(opts.suggestedName);
"""

# a small import file for the import preview: two lines match, one has a dilution not in stock, one material is new
IMPORT = {
    "type": "miformulas-import", "name": "Rose de Mai 68", "targetFormula": "Rose de Mai 68",
    "category": "Bases & Accords", "source": "photo of the lab notebook, 2026-09-05",
    "notes": "Second trial: more geraniol, a touch of rose oxide.",
    "lines": [
        {"material": "Phenyl Ethyl Alcohol (PEA)", "dilutionPct": 100, "weightG": 5.0},
        {"material": "Linalool", "dilutionPct": 100, "weightG": 1.0},
        {"material": "Geraniol", "dilutionPct": 100, "weightG": 0.8},
        {"material": "Rhodinol Bourbon", "dilutionPct": 100, "weightG": 1.0},
        {"material": "Geranyl Acetate", "dilutionPct": 100, "weightG": 2.5},
        {"material": "Citronellol", "dilutionPct": 10, "weightG": 0.5, "comment": "written as 10 %"},
        {"material": "Phenylacetic Aldehyde", "dilutionPct": 50, "weightG": 0.2},
        {"material": "Rose Absolute Turkey", "dilutionPct": 10, "weightG": 0.1},
        {"material": "Oeillet 35", "dilutionPct": 100, "weightG": 0.3},
    ],
}

def shot(page, name, selector=None, clip=None, full=False):
    path = os.path.join(OUT, name)
    if selector:
        page.locator(selector).screenshot(path=path)
    else:
        page.screenshot(path=path, clip=clip, full_page=full)
    print("wrote", name)

def settle(page, ms=3200):
    """wait until the autosave has run, so the header says Saved instead of Unsaved changes"""
    page.wait_for_timeout(ms)

def new_context(b, fake_fs=False, height=800):
    ctx = b.new_context(viewport={"width": 1280, "height": height}, device_scale_factor=2,
                        color_scheme="light", locale="en-GB", timezone_id="Europe/Brussels")
    if fake_fs:
        ctx.add_init_script(FAKE_FS)
    return ctx

def open_formula(page, name):
    page.click("#tabF")
    page.locator("#list").get_by_text(name, exact=True).click()
    page.wait_for_timeout(400)

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---- 1. start screen on the site (browser storage), with the Install link ----
    ctx = new_context(b)
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.evaluate("window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), {preventDefault(){}, prompt: async()=>{}}))")
    page.wait_for_timeout(200)
    shot(page, "app-start-browser.png", "#landing .card")

    # ---- 2. welcome page with the amber storage bar ----
    page.click("#btnStarter"); settle(page)
    shot(page, "app-welcome.png")
    shot(page, "app-header.png", clip={"x": 0, "y": 0, "width": 1280, "height": 44})
    # the amber bar belongs on the welcome shot only
    page.add_style_tag(content="#storageHint{display:none!important}"); page.wait_for_timeout(300)

    # ---- 3. formula page ----
    open_formula(page, "Rose de Mai 68")
    shot(page, "app-formula.png")
    open_formula(page, "Jasmin 231")
    # the list panel and the whole table of a longer formula, on a taller viewport
    page.set_viewport_size({"width": 1280, "height": 1300}); page.wait_for_timeout(300)
    shot(page, "app-formula-full.png")
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(300)

    # ---- 4. materials list and a material page ----
    page.click("#tabM"); page.wait_for_timeout(300)
    page.locator("#list").get_by_text("Geraniol", exact=True).click(); page.wait_for_timeout(400)
    shot(page, "app-material.png")

    # ---- 5. dilution dialog: change the dilution of a line that has a second dilution ----
    open_formula(page, "A Men")
    # Helional is used at 10 % and the library also has it at 100 %: switching up gives solvent back
    row = page.locator("table.lines tbody tr").filter(has_text="Helional").first
    dsel = row.locator("select").first
    cur = dsel.input_value()
    other = [v for v in dsel.locator("option").evaluate_all("os => os.map(o => o.value)") if v != cur and v != "custom"][-1]
    dsel.select_option(other); page.wait_for_timeout(500)
    shot(page, "app-dilution-dialog.png", "#dlg")
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---- 6. tick bar with three ticked lines, and the predilution dialog ----
    open_formula(page, "Ho Hang")
    cbs = page.locator("table.lines input.selCb")
    n = cbs.count()
    for i in range(n - 3, n):
        cbs.nth(i).check()
    page.wait_for_timeout(300)
    page.evaluate("document.querySelector('.tickBar').scrollIntoView({block:'end'})"); page.wait_for_timeout(300)
    tb = page.locator(".tickBar").bounding_box(); table = page.locator("table.lines").first.bounding_box()
    first = page.locator("table.lines tbody tr").nth(n - 3).bounding_box()
    top = first["y"] - 12
    shot(page, "app-tick-bar.png", clip={"x": table["x"] - 4, "y": top, "width": table["width"] + 8, "height": tb["y"] + tb["height"] - top + 4})
    page.click("#btnPredil"); page.wait_for_timeout(500)
    page.fill("#pdName", "Ho Hang trace mix")
    page.fill("#pdK", "100"); page.locator("#pdK").dispatch_event("input"); page.wait_for_timeout(400)
    shot(page, "app-predilution.png", "#dlg")
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---- 7. IFRA check and categories panel ----
    page.evaluate("IFRAOPEN = true; CATSOPEN = true")
    open_formula(page, "1881 for men")
    page.evaluate("document.querySelector('#ifraBox').scrollIntoView({block:'start'})"); page.wait_for_timeout(300)
    shot(page, "app-ifra.png", "#ifraBox")
    shot(page, "app-categories.png", "#catsBox")

    # ---- 8. bench view ----
    open_formula(page, "Rose de Mai 68")
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    # a few lines moved into groups with "Move ticked to…"
    def move(names, group):
        for nm in names:
            page.locator("#content .bsel").filter(has=page.locator("xpath=..").filter(has_text=nm)).first.check() if False else page.locator("#content *:has(> .bsel)").filter(has_text=nm).first.locator(".bsel").check()
        page.select_option("#bMoveSel", label=group); page.wait_for_timeout(400)
    try:
        move(["Phenyl Ethyl Alcohol (PEA)", "Geranyl Acetate"], "Group 1")
        move(["Geraniol", "Citronellol", "Rhodinol Bourbon"], "Group 2")
    except Exception as e:
        print("bench grouping skipped:", e)
    settle(page)
    shot(page, "app-bench-view.png")
    page.click("#btnBenchClose"); page.wait_for_timeout(300)

    # ---- 9. a second version, a variation, and Compare ----
    page.click("#btnNewV"); page.wait_for_timeout(400)
    row = page.locator("table.lines tbody tr").filter(has_text="Geraniol").first
    w = row.locator("input[type=text], input:not([type])").first
    w.fill("0.8"); w.press("Enter"); page.wait_for_timeout(300)
    row = page.locator("table.lines tbody tr").filter(has_text="Phenylacetic Aldehyde").first
    row.locator("button", has_text="✕").click(); page.wait_for_timeout(300)
    page.fill("#addMat", "Rose Oxide"); page.click("#btnAddLine"); page.wait_for_timeout(300)
    row = page.locator("table.lines tbody tr").filter(has_text="Rose Oxide").first
    w = row.locator("input[type=text], input:not([type])").first
    w.fill("0.1"); w.press("Enter"); settle(page)
    shot(page, "app-versions.png", clip={"x": 310, "y": 100, "width": 970, "height": 200})
    page.click("#btnCmp"); page.wait_for_timeout(500)
    shot(page, "app-compare.png")
    page.click("#btnCmpClose"); page.wait_for_timeout(300)
    page.click("#btnNewVar"); page.wait_for_timeout(300)
    page.fill("#nvLabel", "20%"); page.fill("#nvTarget", "50")
    shot(page, "app-new-variation.png", "#dlg")
    page.click("#dlgOk"); settle(page)
    shot(page, "app-variation.png")

    # ---- 10. order list ----
    page.click("#tabT"); page.wait_for_timeout(300)
    page.fill("#ordName", "Iris Butter"); page.fill("#ordNote", "running low"); page.click("#btnOrdAdd"); page.wait_for_timeout(300)
    page.fill("#ordName", "Orris Absolute"); page.fill("#ordNote", "for the iris trial"); page.click("#btnOrdAdd"); settle(page)
    shot(page, "app-order-list.png")

    # ---- 11. settings ----
    page.click("#btnSettings"); page.wait_for_timeout(400)
    shot(page, "app-settings.png", "#dlg")
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---- 12. import preview ----
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.evaluate("p => { IMPORTP = p; render(); }", IMPORT); page.wait_for_timeout(400)
    shot(page, "app-import-preview.png")
    ctx.close()

    # ---- 13. downloaded app opened from disk (file://): start screen and the data-file dialog ----
    ctx = new_context(b, fake_fs=True)
    page = ctx.new_page()
    page.route("https://miformulas.com/data/miformulas-starter.json",
               lambda r: r.fulfill(status=200, content_type="application/json", body=STARTER,
                                   headers={"Access-Control-Allow-Origin": "*"}))
    page.goto(APP_FILE); page.wait_for_timeout(800)
    shot(page, "app-start-file.png", "#landing .card")
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    shot(page, "app-data-file-dialog.png", "#dlg")
    page.click("#dlgOk"); settle(page)
    # restart: the browser remembers the file, the start screen offers Reopen
    page.evaluate("window.__perm = 'prompt'")
    page.reload(); page.wait_for_timeout(1000)
    shot(page, "app-start-reopen.png", "#landing .card")
    ctx.close()
    b.close()

# 256-colour palette: a third of the size, no visible loss on UI screenshots
try:
    from PIL import Image
    import glob
    for f in glob.glob(os.path.join(OUT, "app-*.png")):
        im = Image.open(f).convert("RGB")
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f, optimize=True)
    print("palette-reduced")
except ImportError:
    print("Pillow not installed: PNGs left at full size")
print("done")
