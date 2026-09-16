"""Export my inventory as a library: the dialog, what lands in the file, and the way back in.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

ALLOWED = {"name", "aliases", "cas", "category", "pyramid", "ifraLimit", "isSolvent", "description"}
DESC = "My own notes about this one.\nSecond line, kept as it is."

# a library with facts and descriptions side by side, to see which of the two wins
MIXED = {"type": "miformulas-materials", "name": "Mixed library", "materials": [
    {"name": "Beschrijfstof", "cas": "111-11-1", "category": "Test", "pyramid": 2,
     "odour": ["green", "watery"], "strength": "high", "description": "A colleague's own words."},
    {"name": "Feitenstof", "cas": "222-22-2", "category": "Test", "pyramid": 1,
     "odour": ["woody", "dry"], "strength": "medium"},
    {"name": "Leegstof", "cas": "333-33-3", "category": "Test", "odour": ["soapy"], "description": None}]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    start = page.evaluate("DATA.materials.length")

    # ---------- a material of our own, with everything that must stay behind ----------
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.fill("#nmName", "Proefmateriaal X"); page.wait_for_timeout(200)
    page.click("#dlgOk"); page.wait_for_timeout(500)
    page.fill('textarea[data-f="description"]', DESC); page.dispatch_event('textarea[data-f="description"]', "change")
    page.wait_for_timeout(300)
    check("the description is on the material", page.evaluate(
        "DATA.materials.find(m => m.name === 'Proefmateriaal X').description") == DESC)
    page.evaluate("""() => {
        const m = DATA.materials.find(x => x.name === 'Proefmateriaal X');
        m.aliases = 'Proefstof X; Testolide X'; m.cas = '106-02-5'; m.pyramid = 3; m.ifraLimit = 12.5;
        m.inventory = '250 g in the fridge'; m.costPerGram = 1.25; m.supplier = 'Somebody';
        const a = DATA.materials.find(x => x.name !== 'Proefmateriaal X' && !x.isSolvent);
        a.pyramid = 5; a.ifraLimit = -1; window.__pyr5 = a.name;
        render();
    }""")
    page.wait_for_timeout(300)
    pyr5 = page.evaluate("window.__pyr5")

    # ---------- the dialog ----------
    page.click("#btnHome"); page.wait_for_timeout(400)
    page.click("#btnIO"); page.wait_for_timeout(400)
    check("Import/Export offers Export my inventory as a library…", page.locator("#btnExpL").is_visible())
    page.click("#btnExpL"); page.wait_for_timeout(500)
    n = start + 1
    check("every material is ticked to begin with",
          page.locator("#exRows input[data-i]").count() == n
          and page.locator("#exRows input[data-i]:checked").count() == n)
    check("the button counts them", page.text_content("#dlgOk") == f"Export {n}")
    cnt = page.text_content("#exCount")
    check(f"the counter shows ticked and shown ({cnt})", f"{n} materials ticked · {n} of {n} shown" in cnt)
    check("the counter names the descriptions of your own", "with a description of your own" in cnt)
    check("the warning names what stays out",
          "Stock, price, supplier, dilutions and dates stay out" in page.text_content("#dlg"))
    check("the warning says the file carries no licence or attribution",
          "no name, licence or attribution" in page.text_content("#dlg"))

    # search
    page.fill("#exQ", "Proefmateriaal"); page.wait_for_timeout(300)
    check("the search narrows the list", page.locator("#exRows input[data-i]").count() == 1)
    check(f"the counter follows the search ({page.text_content('#exCount')})",
          f"{n} materials ticked · 1 of {n} shown" in page.text_content("#exCount"))
    check("the row shows that it has a description", "description" in page.text_content("#exRows"))
    page.fill("#exQ", "zzzgeenenkele"); page.wait_for_timeout(300)
    check("a search without a match says so", "Nothing in your inventory matches" in page.text_content("#exRows"))
    page.fill("#exQ", ""); page.wait_for_timeout(300)

    # shift-click unticks a range and ticks it back
    rows = "#exRows input[data-i]"
    page.locator(rows).nth(0).click(); page.wait_for_timeout(150)
    page.locator(rows).nth(4).click(modifiers=["Shift"]); page.wait_for_timeout(250)
    check("shift-click unticks the whole range", page.text_content("#dlgOk") == f"Export {n - 5}")
    check("the range is really unticked", page.locator("#exRows input[data-i]:checked").count() == n - 5)
    page.locator(rows).nth(0).click(); page.wait_for_timeout(150)
    page.locator(rows).nth(4).click(modifiers=["Shift"]); page.wait_for_timeout(250)
    check("shift-click ticks the range back", page.text_content("#dlgOk") == f"Export {n}")

    # ---------- the file ----------
    msgs.clear()
    with page.expect_download() as dl:
        page.click("#dlgOk")
    d = dl.value
    check("the file is named miformulas-my-materials.json", d.suggested_filename == "miformulas-my-materials.json")
    f = os.path.join(tempfile.mkdtemp(), "miformulas-my-materials.json")
    d.save_as(f)
    pkg = json.load(open(f, encoding="utf-8"))
    page.wait_for_timeout(300)
    check(f"the message counts what was written ({msgs})",
          any(f"{n} materials written to miformulas-my-materials.json" in m for m in msgs))
    check("nothing in your own data changed", page.evaluate("DATA.materials.length") == n)

    check("the file has no header of its own", set(pkg.keys()) == {"type", "materials"})
    check("the type makes it importable", pkg["type"] == "miformulas-materials")
    check("every ticked material is in it", len(pkg["materials"]) == n)
    stray = {k for e in pkg["materials"] for k in e} - ALLOWED
    check(f"no field travels that should not ({sorted(stray)})", not stray)

    x = next(e for e in pkg["materials"] if e["name"] == "Proefmateriaal X")
    check("the description travels as it is", x.get("description") == DESC)
    check("alternative names travel as a list", x.get("aliases") == ["Proefstof X", "Testolide X"])
    check("CAS, pyramid and IFRA travel", x.get("cas") == "106-02-5" and x.get("pyramid") == 3 and x.get("ifraLimit") == 12.5)
    check("stock, price and supplier stay behind",
          not {"inventory", "costPerGram", "supplier", "dilutions", "id", "modified"} & set(x))

    y = next(e for e in pkg["materials"] if e["name"] == pyr5)
    check("an unknown pyramid level is no level", "pyramid" not in y)
    check("a negative IFRA value is no limit", "ifraLimit" not in y)
    check("a solvent is marked as one",
          any(e.get("isSolvent") for e in pkg["materials"] if e["name"] == "Ethanol"))

    # ---------- the way back in: a colleague imports the file ----------
    page2 = ctx.new_page()
    page2.on("pageerror", lambda e: errs.append(str(e)))
    msgs2 = []
    page2.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page2.goto(URL); page2.wait_for_timeout(900)
    page2.evaluate("() => idb.set('demoData', null)")
    page2.reload(); page2.wait_for_timeout(900)
    page2.click("#btnStarter"); page2.wait_for_timeout(1200)
    page2.evaluate("""() => {
        const i = DATA.materials.findIndex(m => m.name === 'Proefmateriaal X');
        if (i >= 0) DATA.materials.splice(i, 1);
        render();
    }""")
    page2.click("#btnHome"); page2.wait_for_timeout(400)
    msgs2.clear()
    page2.set_input_files("#impList", f); page2.wait_for_timeout(700)
    check(f"a file without a name imports as a library ({msgs2})",
          any("Materials library loaded" in m for m in msgs2))
    check("it is named in the data", page2.evaluate("DATA.materialList.name") == "Materials library")
    check("all its materials arrived", page2.evaluate("DATA.materialList.materials.length") == n)

    page2.click("#btnNewMat"); page2.wait_for_timeout(300)
    page2.fill("#nmName", "Proefmateriaal X"); page2.wait_for_timeout(300)
    check("the preview shows the description that comes along", "Second line, kept as it is" in page2.text_content("#nmFound"))
    page2.click("#dlgOk"); page2.wait_for_timeout(600)
    got = page2.evaluate("DATA.materials.find(m => m.name === 'Proefmateriaal X')")
    check("the created material carries the description", got["description"] == DESC)
    check("and the facts that came with it", got["cas"] == "106-02-5" and got["pyramid"] == 3 and got["ifraLimit"] == 12.5)
    check("the alternative names came along", "Proefstof X" in (got.get("aliases") or ""))

    # ---------- description beats the fact lines, facts fill in when there is none ----------
    g = os.path.join(os.path.dirname(f), "mixed.json")
    open(g, "w", encoding="utf-8").write(json.dumps(MIXED))
    page2.click("#btnHome"); page2.wait_for_timeout(300)
    msgs2.clear()
    page2.set_input_files("#impList", g); page2.wait_for_timeout(700)
    for nm in ("Beschrijfstof", "Feitenstof", "Leegstof"):
        page2.click("#btnNewMat"); page2.wait_for_timeout(250)
        page2.fill("#nmName", nm); page2.wait_for_timeout(250)
        page2.click("#dlgOk"); page2.wait_for_timeout(450)
    desc = page2.evaluate("Object.fromEntries(DATA.materials.filter(m => ['Beschrijfstof','Feitenstof','Leegstof'].includes(m.name)).map(m => [m.name, m.description]))")
    check("a description from the library wins from the fact lines", desc["Beschrijfstof"] == "A colleague's own words.")
    check("without one the fact lines are still built", desc["Feitenstof"].startswith("woody, dry") and "Impact: medium" in desc["Feitenstof"])
    check("a description that is not text does not break the entry", desc["Leegstof"].startswith("soapy"))

    check(f"no page errors ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
