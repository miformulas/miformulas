"""Remove the starter formulas en Remove the starter set materials in Settings (bouw 261016b).
Draait op de lokale webserver (poort 8765, zie README); MIF_URL kiest een andere."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def tel(page):
    return page.evaluate("""() => ({fs: DATA.formulas.filter(f => f.starter).length, fe: DATA.formulas.filter(f => !f.starter).length,
      ms: DATA.materials.filter(m => m.starter).length, me: DATA.materials.filter(m => !m.starter).length, o: DATA.orderList.length})""")

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 900})
    errs, msgs, antwoord = [], [], {"v": True}
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept() if antwoord["v"] or d.type == "alert" else d.dismiss()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    start = tel(page)

    page.click("#btnSettings"); page.wait_for_timeout(400)
    check("Settings toont Remove the starter formulas", page.locator("#setStarterF").count() == 1)
    check("Settings toont Remove the starter set materials", page.locator("#setStarterM").count() == 1)
    if page.locator("#setStarterF").count() == 0:
        print(f"\n{ok} OK, {fail} FAIL"); raise SystemExit(1)
    check("beide knoppen actief met de starterset", page.locator("#setStarterF").is_enabled() and page.locator("#setStarterM").is_enabled())

    # een eigen formule die twee starter-materialen gebruikt, en een eigen materiaal
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.evaluate("""() => {
      const [a, c] = DATA.materials.filter(m => m.starter && !m.isSolvent);
      DATA.formulas.push({id: 'eigenF', name: 'Eigen formule', category: '', versions: [{v: 1, date: '2026-10-16',
        lines: [{materialId: a.id, dilutionPct: a.dilutions[0].pct, weightG: 1},
                {materialId: c.id, dilutionPct: c.dilutions[0].pct, weightG: 2}]}]});
      DATA.materials.push({id: 'eigenM', name: 'Eigen materiaal', dilutions: [{pct: 100, isBase: true, date: '', notes: ''}]});
      window.__kept = [a.name, c.name];
      const weg = DATA.materials.filter(m => m.starter && m !== a && m !== c)[0];
      DATA.orderList.push({id: 'o1', name: weg.name, materialId: weg.id, note: 'restock'});
      DATA.orderList.push({id: 'o2', name: 'Eigen materiaal', materialId: 'eigenM', note: ''});
      markDirty(); render(); }""")
    voor = tel(page)

    # 1. Cancel verandert niets
    antwoord["v"] = False
    page.click("#btnSettings"); page.wait_for_timeout(300); msgs.clear()
    page.click("#setStarterF"); page.wait_for_timeout(300)
    check("de vraag noemt het aantal formules", msgs and msgs[0] == f"Remove the {start['fs']} starter formulas, with all their versions? Your own formulas are not touched.")
    check("Cancel laat de formules staan", tel(page) == voor)
    antwoord["v"] = True
    page.keyboard.press("Escape"); page.wait_for_timeout(200)

    # 2. de formules
    page.click(f"#list .item:has-text('{page.evaluate('DATA.formulas.find(f => f.starter).name')}')"); page.wait_for_timeout(300)
    page.click("#btnSettings"); page.wait_for_timeout(300); msgs.clear()
    page.click("#setStarterF"); page.wait_for_timeout(500)
    n = tel(page)
    check("alle starterformules weg", n["fs"] == 0)
    check("de eigen formule blijft", n["fe"] == voor["fe"] == 1)
    check("de materialen blijven", n["ms"] == voor["ms"] and n["me"] == voor["me"])
    check("het venster is dicht", not page.evaluate("document.querySelector('#dlg').open"))
    check("de open starterformule is niet meer open", page.evaluate("VIEW.id === null"))
    check("de lijst toont alleen de eigen formule", page.locator("#list .item").count() == 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("één Undo brengt de formules terug", tel(page) == voor)
    page.keyboard.press("Control+y"); page.wait_for_timeout(400)
    check("Redo neemt ze weer weg", tel(page)["fs"] == 0)

    page.click("#btnSettings"); page.wait_for_timeout(300)
    check("zonder starterformules is de knop grijs", page.locator("#setStarterF").is_disabled())
    check("de materialenknop blijft actief", page.locator("#setStarterM").is_enabled())

    # 3. de materialen
    msgs.clear()
    page.click("#setStarterM"); page.wait_for_timeout(600)
    check("de vraag noemt het aantal en waarschuwt", msgs and msgs[0] == f"Remove the {voor['ms']} starter set materials? This includes starter materials you added stock, prices or notes to. Materials used in a formula stay.")
    kept = page.evaluate("window.__kept")
    check("de melding noemt wat bleef", len(msgs) > 1 and msgs[1] == f"{voor['ms'] - 2} materials removed. 2 kept because a formula uses them: {kept[0]}, {kept[1]}.")
    n = tel(page)
    check("de twee gebruikte starter-materialen blijven", n["ms"] == 2)
    check("het eigen materiaal blijft", n["me"] == voor["me"])
    check("de eigen formule is nog berekenbaar", page.evaluate("DATA.formulas[0].versions[0].lines.every(l => DATA.materials.some(m => m.id === l.materialId))"))
    check("de bestelregel van een verwijderd materiaal gaat mee", page.evaluate("!DATA.orderList.some(o => o.id === 'o1') && DATA.orderList.some(o => o.id === 'o2')"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    n = tel(page)
    check("één Undo brengt materialen en bestelregel terug", n["ms"] == voor["ms"] and page.evaluate("DATA.orderList.some(o => o.id === 'o1')"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("een tweede Undo brengt ook de formules terug", tel(page) == voor)

    # 4. alleen-lezen
    page.evaluate("() => { LOCKED = true; }")
    page.click("#btnSettings"); page.wait_for_timeout(300)
    check("alleen-lezen: beide knoppen grijs", page.locator("#setStarterF").is_disabled() and page.locator("#setStarterM").is_disabled())
    page.keyboard.press("Escape")
    page.evaluate("() => { LOCKED = false; }")

    check("geen fouten op de pagina", not errs)
    if errs: print(errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
