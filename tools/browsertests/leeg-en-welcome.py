"""Start empty, het blok Start here op Welcome, de kolom Cost die pas met een prijs verschijnt, en een
kaal databestand dat + New formula en + New material niet meer laat crashen (B10, B14, E2 van de review).
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright
URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(900)
    check("Start empty staat op het startscherm", page.locator("#btnEmpty").is_visible())
    page.click("#btnEmpty"); page.wait_for_timeout(1200)
    check(f"met een bevestiging ({[m[:40] for m in msgs]})", any("Start with nothing" in m for m in msgs))
    d = page.evaluate("() => ({f: DATA.formulas.length, m: DATA.materials.length, cat: DATA.materialCategories, fcat: DATA.formulaCategories, sup: DATA.suppliers})")
    check(f"de data is leeg maar volledig ({d})", d["f"] == 0 and d["m"] == 0 and d["cat"] and d["fcat"] and isinstance(d["sup"], list))
    check("het startscherm is weg", not page.locator("#landing").is_visible())
    txt = page.text_content("#content")
    check(f"Welcome wijst de weg met één primaire knop", "Start here" in txt)
    prim = page.evaluate("""() => [...document.querySelectorAll("#content button.primary, #content a.btn.primary")].map(x => x.textContent.trim())""")
    check(f"en dat is de enige primaire knop op het scherm ({prim})", len(prim) == 1)
    check("geen paneel Recently edited op een lege start", "Recently edited" not in txt)
    msgs.clear()
    page.click("#content button.primary"); page.wait_for_timeout(600)
    check("de primaire knop opent New formula", page.locator("#nfName").count() == 1)
    page.fill("#nfName", "Proef"); page.click("#dlgOk"); page.wait_for_timeout(700)
    check(f"en een formule maken werkt in een leeg bestand ({errs[:1]})", page.evaluate("() => DATA.formulas.length") == 1 and not errs)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.fill("#nmName", "Proefstof"); page.click("#dlgOk"); page.wait_for_timeout(700)
    check(f"een materiaal aanmaken ook ({errs[:1]})", page.evaluate("() => DATA.materials.length") == 1 and not errs)
    tab = page.evaluate("""() => { switchTab("F", DATA.formulas[0].id, {type:"v", idx:0});
        return document.querySelector("#content").textContent; }""")
    page.wait_for_timeout(500)
    kop = page.evaluate("""() => [...document.querySelectorAll("table.lines th")].map(t => t.textContent.trim())""")
    check(f"zonder prijzen staat er geen kolom Cost ({kop})", not any("Cost" in k for k in kop))
    page.evaluate("""() => { DATA.materials[0].costPerGram = 2; render(); }""")
    page.wait_for_timeout(400)
    kop = page.evaluate("""() => [...document.querySelectorAll("table.lines th")].map(t => t.textContent.trim())""")
    check(f"met één prijs verschijnt ze ({kop})", any("Cost" in k for k in kop))
    # een minimaal bestand openen
    pth = os.path.join(tempfile.mkdtemp(), "min.json")
    open(pth, "w").write(json.dumps({"formulas": [], "materials": []}))
    page.evaluate("() => { DIRTY = false; }")
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    errs.clear()
    page.evaluate("""(t) => { DATA = migrate(JSON.parse(t)); boot(); }""", json.dumps({"formulas": [], "materials": []}))
    page.wait_for_timeout(800)
    page.click("#btnNew"); page.wait_for_timeout(400)
    check(f"een kaal databestand laat + New formula nog werken ({errs[:1]})", page.locator("#nfName").count() == 1 and not errs)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    check(f"en + New material ({errs[:1]})", page.locator("#nmName").count() == 1 and not errs)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    # de balk en de Welcome-knop zeggen hetzelfde: nooit allebei
    page.evaluate("() => { HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); }")
    page.wait_for_timeout(400)
    dub = page.evaluate("""() => { const bar = !document.querySelector("#storageHint").hidden;
        const b = document.querySelector("#homeToFile");
        return {bar, knop: !!b && !!b.offsetParent}; }""")
    check(f"Save to a data file… staat één keer op het scherm ({dub})", not (dub["bar"] and dub["knop"]))
    check(f"geen paginafouten ({errs[:2]})", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
