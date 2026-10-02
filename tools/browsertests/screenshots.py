"""App screenshots for the manual (docs/img/app-*.png), taken with the starter set.

Run against a local web server with the contents of public/ on port 8765:
    cd public && python -m http.server 8765
    python tools/browsertests/screenshots.py
    python tools/browsertests/screenshots.py app-predilution.png …   # only these are written (and reduced)
Chromium headless, light theme, 1280x800 at 2x, PNGs reduced to a 256-colour palette (Pillow). Nothing is written to the data file:
the starter set lives in the browser storage of a throw-away profile.
"""
import json, math, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(PUB, "docs", "img")
URL = "http://localhost:8765/"
APP_FILE = "file://" + os.path.join(PUB, "index.html").replace("\\", "/")
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
# the published materials library lives outside the repository (miformulas.com serves it from R2).
# Put a copy next to public/ to get the real thing in the shots; without it a small stand-in is used.
LIBRARY = os.path.abspath(os.path.join(PUB, "..", "miformulas-materials.json"))
os.makedirs(OUT, exist_ok=True)
# names on the command line: only those shots are written, so one figure can be made again without touching the others
# (build 261002a); the palette reduction at the end takes only what this run wrote
ONLY = set(sys.argv[1:])
WRITTEN = []

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
    if ONLY and name not in ONLY:
        return
    path = os.path.join(OUT, name)
    if selector:
        # an element is cut on whole pixels, each edge rounded to the nearest one: an element shot rounds a fractional edge
        # outwards and left a strip of the page behind under three of the windows (v1.7)
        el = page.locator(selector); el.scroll_into_view_if_needed(); b = el.bounding_box()
        x, y = round(b["x"]), round(b["y"])
        clip = {"x": x, "y": y, "width": round(b["x"] + b["width"]) - x, "height": round(b["y"] + b["height"]) - y}
    page.screenshot(path=path, clip=clip, full_page=full)
    WRITTEN.append(path)
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
    page.set_viewport_size({"width": 1440, "height": 800}); page.wait_for_timeout(400)   # the wide header, the one the manual describes
    hb = page.locator("header").first.bounding_box()
    shot(page, "app-header.png", clip={"x": 0, "y": 0, "width": 1440, "height": hb["y"] + hb["height"]})
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(400)
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

    # ---- 6. tick bar with three ticked lines (the premix has a window of its own, 6b) ----
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

    # ---- 6b. premixes (manual section 8), in a window of its own: a premix adds a formula, a material and two
    # versions, and the other shots should not see them. Acqua di Gio for men scaled to 20 g has fifteen lines under
    # 25 mg; Lower takes the five at 100 % to their 10 % dilution, and the ten that were at 10 % already go into a
    # premix with a factor of 10, which makes the smallest 48 mg (build 261002a, on the starter set at 10 %) ----
    ctx_p = new_context(b)
    pp = ctx_p.new_page(); pp.on("dialog", lambda d: d.accept())                    # Lower reports the ten it skipped
    pp.goto(URL); pp.wait_for_timeout(800)
    pp.click("#btnStarter"); settle(pp, 1500)
    pp.add_style_tag(content="#storageHint{display:none!important}")
    open_formula(pp, "Acqua di Gio for men")
    pp.click("#btnNewV"); pp.wait_for_timeout(600)                                 # v3: the version you scale
    pp.evaluate("SCALEOPEN = true; render()"); pp.wait_for_timeout(300)
    pp.fill("#scaleW", "20"); pp.click("#btnApplyScale"); pp.wait_for_timeout(600)
    pp.locator("span.sortable[data-sort='weight']").first.click(); pp.wait_for_timeout(500)
    cbs = pp.locator("table.ftable input.selCb")
    cbs.nth(0).click(); pp.keyboard.down("Shift"); cbs.nth(14).click(); pp.keyboard.up("Shift"); pp.wait_for_timeout(300)
    pp.click("#btnDilDown"); pp.wait_for_timeout(800)                              # the fifteen under 25 mg: Lower
    cbs = pp.locator("table.ftable input.selCb")                                   # the ten still under 25 mg
    cbs.nth(0).click(); pp.keyboard.down("Shift"); cbs.nth(9).click(); pp.keyboard.up("Shift"); pp.wait_for_timeout(300)
    pp.mouse.move(5, 5); pp.evaluate("document.activeElement.blur()")             # no focus ring on the last tick
    pp.evaluate("document.querySelector('#sortSel').scrollIntoView({block: 'start'}); window.scrollBy(0, -70)"); pp.wait_for_timeout(300)
    top = pp.locator("#sortSel").bounding_box(); tbl = pp.locator("table.ftable").first.bounding_box()
    last = pp.locator("table.ftable tbody tr").nth(11).bounding_box()                 # the ten ticked and the two after them
    hb = pp.locator("header").first.bounding_box()
    y0 = max(round(top["y"]) - 6, round(hb["y"] + hb["height"]) + 2)                 # never the edge of the header
    shot(pp, "app-predil-ticked.png", clip={"x": round(tbl["x"]) - 4, "y": y0, "width": round(tbl["width"]) + 8,
                                            "height": round(last["y"] + last["height"]) - y0})
    pp.click("#btnPredil"); pp.wait_for_timeout(500)
    pp.fill("#pdK", "10"); pp.locator("#pdK").dispatch_event("input"); pp.wait_for_timeout(300)
    shot(pp, "app-predilution.png", "#dlg")
    pp.click("#dlgOk"); pp.wait_for_timeout(900)
    pp.select_option("#sortSel", "orig"); pp.wait_for_timeout(500)                  # the premix line is the last one
    rows = pp.locator("table.ftable tbody tr"); n = rows.count()
    first = rows.nth(n - 4); first.scroll_into_view_if_needed(); pp.mouse.move(5, 5); pp.wait_for_timeout(300)
    a = first.bounding_box(); tbl = pp.locator("table.ftable").first.bounding_box(); foot = pp.locator("table.ftable tfoot").first.bounding_box()
    y0 = round(a["y"]) - 4
    shot(pp, "app-predil-version.png", clip={"x": round(tbl["x"]) - 4, "y": y0, "width": round(tbl["width"]) + 8,
                                             "height": round(foot["y"] + foot["height"]) + 4 - y0})
    open_formula(pp, "Acqua di Gio for men - v3 - PREMIX")
    pp.mouse.move(5, 5)
    shot(pp, "app-predil-mix.png", "table.ftable")
    ctx_p.close()

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
    page.click("#btnBenchToggle"); page.wait_for_timeout(300)

    # ---- 9. a second version and Compare ----
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

    # ---- 10. order list ----
    page.click("#tabT"); page.wait_for_timeout(300)
    page.fill("#ordName", "Iris Butter"); page.fill("#ordNote", "running low"); page.click("#btnOrdAdd"); page.wait_for_timeout(300)
    page.fill("#ordName", "Orris Absolute"); page.fill("#ordNote", "for the iris trial"); page.click("#btnOrdAdd"); settle(page)
    # Since 260920c the table scrolls inside its wrapper, so nothing is out of reach at 1280 px, but the
    # row is 1029 px wide in a 919 px wrapper there and a figure would show "De" cut in half. One wide shot.
    page.set_viewport_size({"width": 1440, "height": 800}); page.wait_for_timeout(400)
    shot(page, "app-order-list.png")
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(400)

    # ---- 10b. the materials library: import it, then Browse ----
    page.click("#btnHome"); page.wait_for_timeout(300)
    lib = LIBRARY
    if not os.path.exists(lib):                      # a stand-in, so the script also runs from a bare clone
        lib = os.path.join(OUT, "_library.json")
        open(lib, "w", encoding="utf-8").write(json.dumps({
            "type": "miformulas-materials", "name": "miFormulas materials library",
            "version": "0000-00-00", "licence": "CC BY 4.0", "materials": [
                {"name": n, "category": "Musks", "pyramid": 4} for n in
                ("Ambrettolide", "Exaltolide", "Habanolide", "Muscenone", "Nirvanolide", "Velvione")]}))
        print("no", LIBRARY, "- using a stand-in library")
    page.set_input_files("#impList", lib); page.wait_for_timeout(900)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.click("#nmBrowse"); page.wait_for_timeout(500)
    page.fill("#brQ", "musk"); page.wait_for_timeout(400)
    boxes = page.locator("#brRows input[data-n]:not([disabled])")
    for i in range(min(3, boxes.count())):
        boxes.nth(i).click(); page.wait_for_timeout(120)
    shot(page, "app-browse-library.png", "#dlg")
    page.click("#dlgCancel"); page.wait_for_timeout(300)   # Browse reuses the same dialog, so one Cancel closes both

    # ---- 10c. Move into… with Move together, on three imported formulas ----
    page.evaluate("""() => {
        const src = DATA.formulas.find(f => f.versions.length && f.versions[0].lines.length > 4) || DATA.formulas[0];
        const base = src.versions[0];
        const mk = (name, k) => ({id: uid("f-"), name, category: "Uncategorised", modified: now(), frozenImport: true,
            versions: [{v: 1, date: "2026-08-" + (10 + k), name: "", notes: "", sourceName: name, imported: true, frozen: true,
                        lines: base.lines.map(l => ({...l, weightG: +(((l.weightG || 0) * (1 + k / 20)).toFixed(3))}))}]});
        for (const [i, n] of ["Aura v04", "Aura v05", "Aura v05 20%"].entries()) DATA.formulas.push(mk(n, i));
        const f = DATA.formulas.find(x => x.name === "Aura v04");
        switchTab("F", f.id, {type: "v", idx: 0});
    }""")
    page.wait_for_timeout(600)
    page.click("#btnMoveF"); page.wait_for_timeout(600)
    shot(page, "app-move-into.png", "#dlg")
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.evaluate("""() => {                                   // leave the starter set as it was
        DATA.formulas = DATA.formulas.filter(f => !/^Aura v0/.test(f.name));
        HOMEVIEW = true; VIEW = {tab:"F", id:null, sub:null}; render();
    }""")
    settle(page)

    # ---- 11. settings, with the library block (taller viewport: the dialog scrolls otherwise) ----
    page.set_viewport_size({"width": 1280, "height": 1150}); page.wait_for_timeout(300)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    shot(page, "app-settings.png", "#dlg")
    page.fill("#setServer", "https://miformulas-data.yourname.workers.dev/")
    page.fill("#setToken", "k7QwPz2mR4xL9vB3tNdY")     # not a real token: the field shows dots
    page.evaluate("""() => {        // step 9 is about the two fields and Apply: the rest of the window only makes the figure tall
        const box = document.querySelector("#dlg > div"), grid = document.querySelector("#setServer").closest(".fieldGrid");   // since 260930c the second grid
        const keep = new Set([box.querySelector("h3"), grid, grid.nextElementSibling,
                              [...box.querySelectorAll(".toolRow")].pop()]);
        for (const k of [...box.children]) if (!keep.has(k)) k.remove();
    }""")
    page.wait_for_timeout(700)                             # let the shrunken dialog settle before the shot
    shot(page, "cloudflare-09-app-settings.png", "#dlg > div")   # the card itself: section 7, step 9
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(300)

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
    # Median cut gives a colour that covers only a few pixels no palette entry of its own and merges it into its
    # neighbour: the green of "only in B" in app-compare.png came out grey (D-F1 of the audit v2). So median cut
    # chooses 240 colours, and up to 16 colours that it moved by more than 40 on a channel, on at least 40 pixels,
    # get an entry of their own; every other pixel keeps what median cut gave it.
    import numpy as np
    def reduce(im, extra_max=16, drift=40, min_px=40):
        q = im.quantize(colors=256 - extra_max, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        a = np.asarray(im, dtype=np.int16); idx = np.array(q)
        pal = np.array(q.getpalette()[:3 * 256], dtype=np.int16).reshape(-1, 3)
        far = np.abs(a - pal[idx]).max(axis=2) > drift
        cols, counts = np.unique(a[far].reshape(-1, 3), axis=0, return_counts=True)
        extra = [tuple(int(v) for v in cols[i]) for i in np.argsort(-counts)[:extra_max] if counts[i] >= min_px]
        used = int(idx.max()) + 1
        flat = q.getpalette()[:3 * used]
        for k, c in enumerate(extra):
            idx[far & np.all(a == c, axis=2)] = used + k
            flat += list(c)
        out = Image.fromarray(idx.astype(np.uint8), "P")
        out.putpalette(flat + [0] * (768 - len(flat)))
        return out
    for f in WRITTEN:
        reduce(Image.open(f).convert("RGB")).save(f, optimize=True)
    print("palette-reduced")
except ImportError:
    print("Pillow not installed: PNGs left at full size")
print("done")
