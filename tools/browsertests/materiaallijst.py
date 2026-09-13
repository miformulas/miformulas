"""The material list: import one list, see it in Settings, look it up in + New material, remove it.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

LIST = {"type": "miformulas-materials", "name": "Test material list", "version": "2026-09-13",
        "licence": "CC BY 4.0", "count": 2, "materials": [
    {"name": "Testolide", "aliases": ["omega-testolactone", "Proefmusk"], "cas": "106-02-5",
     "category": "Test musks", "pyramid": 4, "ifraLimit": 99, "odour": ["musky", "animalic", "powdery"],
     "strength": "high", "tenacity": "more than 2 weeks",
     "use": {"mean": "1.5", "low": "0.76", "high": "3.2", "n": "83"}},
    {"name": "Dipropylene glycol", "cas": "25265-71-8", "category": "Solvents", "isSolvent": True}]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # without a list the New material dialog has no lookup
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    check("no datalist without a list", page.locator("#nmList").count() == 0)
    page.click("#dlgCancel"); page.wait_for_timeout(200)

    # import the list from the Welcome page
    f = os.path.join(tempfile.mkdtemp(), "miformulas-materials.json")
    open(f, "w", encoding="utf-8").write(json.dumps(LIST))
    page.click("#btnHome"); page.wait_for_timeout(400)
    check("Welcome offers Import material list…", page.locator("#btnImpL").is_visible())
    msgs.clear()
    page.set_input_files("#impList", f); page.wait_for_timeout(600)
    check(f"import reports name, version and count ({msgs})", any("Test material list 2026-09-13, 2 materials" in m for m in msgs))
    check("the list sits in the data", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 2)
    check("Welcome names the loaded list", "Test material list" in page.text_content("#content"))

    # Settings shows it with Remove
    page.click("#btnSettings"); page.wait_for_timeout(400)
    dlg = page.text_content("#dlg")
    check("Settings names the list, its size and licence", "Test material list" in dlg and "2 materials" in dlg and "CC BY 4.0" in dlg)
    check("Settings offers Import and Remove", page.locator("#setListImp").is_visible() and page.locator("#setListDel").is_visible())
    check("Settings offers Get the latest list", page.locator("#setListGet").is_visible())
    page.click("#dlgCancel"); page.wait_for_timeout(200)

    # Get the latest list: the published address, answered here by a stand-in
    page.route("https://data.miformulas.com/**", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({**LIST, "name": "Fetched list", "version": "2026-09-13b",
                         "materials": LIST["materials"][:1]})))
    page.click("#btnSettings"); page.wait_for_timeout(400)
    msgs.clear(); page.click("#setListGet"); page.wait_for_timeout(800)
    check(f"the fetched list replaces the imported one ({msgs})",
          page.evaluate("DATA.materialList && DATA.materialList.name") == "Fetched list"
          and page.evaluate("DATA.materialList.materials.length") == 1)
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("undo brings the imported list back", page.evaluate("DATA.materialList.name") == "Test material list")
    page.unroute("https://data.miformulas.com/**")

    # + New material: the lookup
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    check("datalist holds the list", page.locator("#nmList option").count() == 2)
    page.fill("#nmName", "Proefmusk"); page.wait_for_timeout(200)      # an alternative name finds it too
    found = page.text_content("#nmFound")
    check(f"an alias finds the material ({found!r})", "Testolide" in found and "106-02-5" in found and "Base" in found)
    check("the facts line is shown", "musky, animalic, powdery" in found and "more than 2 weeks" in found and "typical 1.5 %" in found)
    check("the category of the list is preselected", page.locator("#nmCat").input_value() == "Test musks")
    page.click("#dlgOk"); page.wait_for_timeout(600)
    m = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Proefmusk");
      return m && {cas: m.cas, pyr: m.pyramid, ifra: m.ifraLimit, cat: m.category, al: m.aliases, d: m.description, sol: m.isSolvent}; }""")
    check(f"the material carries the facts ({m})", m and m["cas"] == "106-02-5" and m["pyr"] == 4 and m["ifra"] == 99 and m["cat"] == "Test musks")
    check("alternative names came along", m and m["al"] == "omega-testolactone; Proefmusk")
    check("odour, strength, tenacity and use are in the description",
          m and "musky, animalic, powdery" in m["d"] and "high" in m["d"] and "83 formulas" in m["d"])
    check("the new category was added", page.evaluate("DATA.materialCategories.includes('Test musks')"))
    check("the material page opened", page.locator("#content h2").first.inner_text().startswith("Proefmusk"))
    page.click("#content h2"); page.wait_for_timeout(100)      # Ctrl+Z in a text field is the browser's own undo
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("undo removes the material and its category",
          page.evaluate("!DATA.materials.some(x => x.name === 'Proefmusk') && !DATA.materialCategories.includes('Test musks')"))

    # a name of your own still works, without facts
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.fill("#nmName", "Eigen mengsel 1"); page.wait_for_timeout(200)
    check("no list line for an unknown name", page.text_content("#nmFound").strip() == "")
    page.click("#dlgOk"); page.wait_for_timeout(500)
    page.click("#content h2"); page.wait_for_timeout(100)
    own = page.evaluate("(() => { const m = DATA.materials.find(x => x.name === 'Eigen mengsel 1'); return m && {d: m.description, pyr: m.pyramid}; })()")
    check(f"an unknown material stays empty ({own})", own and own["d"] == "" and own["pyr"] == 5)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)

    # a name that already exists is refused, as before
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.fill("#nmName", "Hedione"); msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(400)
    check(f"an existing name is refused ({msgs})", any("already exists" in m for m in msgs))
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # remove the list again
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.click("#setListDel"); page.wait_for_timeout(500)
    check("the list is gone", page.evaluate("DATA.materialList") is None)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("undo brings the list back", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 2)

    # it survives a save and a fresh visit (browser storage)
    page.click("#btnSave"); page.wait_for_timeout(600)
    pg2 = ctx.new_page(); pg2.on("dialog", lambda d: d.accept())
    pg2.goto(URL); pg2.wait_for_timeout(1200)
    check("the list is still there in a new visit", pg2.evaluate("DATA.materialList && DATA.materialList.materials.length") == 2)
    check("no page errors", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
