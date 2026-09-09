"""Formulair import added to the current library (build 260909d): pendingImport left by
formulair-import.html is merged at the next start, in browser-storage mode here.
Checks: materials matched by name (dilutions added, empty fields filled), new materials and
formulas added, categories and colours merged, a formula imported before is skipped, the
message, one Undo, a pending import with no data yet becomes the data, the Welcome page
"Your data" line. Needs the local webserver (cd public && python -m http.server 8765)."""
import json
from playwright.sync_api import sync_playwright
URL = "http://localhost:8765/"
fouten = []
def check(m, c):
    print(("OK   " if c else "FOUT ") + m)
    if not c: fouten.append(m)

PKG = {
  "meta": {"schema": 1, "source": "test"},
  "materialCategories": ["Flowers - white", "Test category"], "formulaCategories": ["Uncategorised", "Tests"],
  "suppliers": ["Test Supplier"], "categoryColours": {"Test category": "#123456", "Flowers - white": "#000000"},
  "materials": [
    {"id": "m-f1", "name": "hedione ", "cas": "24851-98-7", "category": "Test category", "supplier": "Test Supplier",
     "costPerGram": 0.5, "ifraLimit": None, "inventory": "12 g", "pyramid": 2, "isSolvent": False, "description": "from Formulair",
     "dilutions": [{"pct": 100, "isBase": True, "date": "", "notes": ""}, {"pct": 10, "isBase": False, "date": "", "notes": "test"}], "locations": {}, "density": None, "modified": "2026-09-09"},
    {"id": "m-f2", "name": "Brand New Material", "cas": "", "category": "Test category", "supplier": "", "costPerGram": None,
     "ifraLimit": None, "inventory": None, "pyramid": 1, "isSolvent": False, "description": "", "dilutions": [{"pct": 100, "isBase": True, "date": "", "notes": ""}], "locations": {}, "density": None, "modified": "2026-09-09"},
  ],
  "formulas": [
    {"id": "f-f1", "name": "Test Import v01", "category": "Tests", "created": "2026-09-09", "modified": "2026-09-09 10:00", "frozenImport": True,
     "versions": [{"v": 1, "name": "", "date": "2026-09-09", "notes": "hello", "lines": [
        {"materialId": "m-f1", "dilutionPct": 10, "weightG": 1.5, "remark": None},
        {"materialId": "m-f2", "dilutionPct": 100, "weightG": 0.5, "remark": 2}], "sourceName": "Test Import v01", "imported": True, "frozen": True}],
     "variations": []},
  ],
  "shopSites": [], "orderList": [],
}

with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    msgs = []; pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.goto(URL); pg.wait_for_timeout(600)
    pg.evaluate("new Promise(r=>{const t=idb.db.transaction('kv','readwrite').objectStore('kv').clear(); t.onsuccess=r; t.onerror=r;})")
    pg.goto(URL); pg.wait_for_timeout(600)
    pg.click("#btnStarter"); pg.wait_for_timeout(800)
    base = pg.evaluate("[DATA.formulas.length, DATA.materials.length]")
    check(f"starter set loaded: {base}", base == [16, 199])
    check("Welcome page says where the data is", "kept in this browser" in pg.text_content("#whereData"))
    check("Welcome page offers Save to a data file… in Chrome", pg.locator("#homeToFile").is_visible())
    pg.click("#btnSave"); pg.wait_for_timeout(500)

    # the importer's hand-over, then a restart
    pg.evaluate("t => idb.set('pendingImport', t)", json.dumps(PKG)); pg.wait_for_timeout(200)
    pg.goto(URL); pg.wait_for_timeout(1500)
    after = pg.evaluate("[DATA.formulas.length, DATA.materials.length]")
    check(f"after the restart: one formula and one material added: {after}", after == [17, 200])
    check("message names the counts", any("Formulas: 1 added" in m and "1 added, 1 matched by name" in m and "1 dilutions added" in m for m in msgs))
    hed = pg.evaluate("(() => { const m = DATA.materials.find(x => x.name === 'Hedione'); return m && {dils: m.dilutions.map(d => d.pct), base: m.dilutions.filter(d => d.isBase).length, cas: m.cas, inv: m.inventory, cat: m.category, desc: m.description, cost: m.costPerGram}; })()")
    check(f"Hedione matched by name (case and spaces ignored): 10 % dilution added, one base: {hed and hed['dils']}", hed and 10 in hed["dils"] and hed["base"] == 1)
    check("Hedione: empty fields filled, existing kept", hed and hed["inv"] == "12 g" and hed["cost"] == 0.5 and hed["cat"] != "Test category" and hed["cas"] == "24851-98-7")
    f = pg.evaluate("(() => { const f = DATA.formulas.find(x => x.name === 'Test Import v01'); const ids = new Set(DATA.materials.map(m => m.id)); return f && {frozen: f.frozenImport, ok: f.versions[0].lines.every(l => ids.has(l.materialId)), hed: DATA.materials.find(x => x.name === 'Hedione').id === f.versions[0].lines[0].materialId, cat: f.category}; })()")
    check("imported formula: frozen, lines point to library materials, Hedione line remapped", f and f["frozen"] and f["ok"] and f["hed"] and f["cat"] == "Tests")
    cats = pg.evaluate("[DATA.materialCategories.includes('Test category'), DATA.formulaCategories.includes('Tests'), DATA.suppliers.includes('Test Supplier'), DATA.categoryColours['Test category'], DATA.categoryColours['Flowers - white']]")
    check(f"categories, supplier and colours merged, existing colour kept: {cats}", cats[0] and cats[1] and cats[2] and cats[3] == "#123456" and cats[4] != "#000000")
    check("pending import cleared", pg.evaluate("idb.get('pendingImport')") in (None, ""))
    check("Welcome page shown after the import", pg.locator("#whereData").is_visible())
    # one Undo
    pg.keyboard.press("Control+z"); pg.wait_for_timeout(400)
    undone = pg.evaluate("[DATA.formulas.length, DATA.materials.length, DATA.materials.find(x => x.name === 'Hedione').dilutions.length]")
    check(f"Undo takes the whole import back: {undone}", undone == [16, 199, 1])
    pg.keyboard.press("Control+y"); pg.wait_for_timeout(400)
    check("Redo brings it back", pg.evaluate("DATA.formulas.length") == 17)
    # a second import of the same package: formula skipped, nothing doubled
    msgs.clear()
    pg.click("#btnSave"); pg.wait_for_timeout(500)
    pg.evaluate("t => idb.set('pendingImport', t)", json.dumps(PKG)); pg.goto(URL); pg.wait_for_timeout(1500)
    again = pg.evaluate("[DATA.formulas.length, DATA.materials.length]")
    check(f"same import again: formula skipped, materials matched: {again}", again == [17, 200] and any("1 already present" in m for m in msgs))
    check("no JavaScript errors", not errs)
    ctx.close()

    # no data yet: the pending import becomes the data
    ctx = b.new_context(); pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(600)
    pg.evaluate("t => idb.set('pendingImport', t)", json.dumps(PKG)); pg.goto(URL); pg.wait_for_timeout(1200)
    fresh = pg.evaluate("DATA ? [DATA.formulas.length, DATA.materials.length, DEMO] : null")
    check(f"empty browser: the import becomes the data: {fresh}", fresh == [1, 2, True])
    check("no JavaScript errors (fresh)", not errs)
    ctx.close(); b.close()

print("\n" + ("alles in orde" if not fouten else f"{len(fouten)} fout(en)"))
raise SystemExit(1 if fouten else 0)
