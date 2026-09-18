"""Undo, Redo and where you land (build 260914g): a new category goes back with the action that made
it, a predilution takes its two categories back, Replace plus a dilution change is one step, Redo
returns to the place the change was made, Copy from an older version takes that version, and a new
version keeps the bench arrangement. Needs the local web server on port 8765 (see README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    errs = []; msgs = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1600)

    # ---------- 1. a new formula category goes back with the formula ----------
    page.click("#btnNew"); page.wait_for_timeout(400)
    page.fill("#nfName", "Undotest")
    page.evaluate("""() => { window.prompt = () => "Proefcategorie"; }""")
    page.click("#btnNewCat"); page.wait_for_timeout(300)
    page.click("#dlgOk"); page.wait_for_timeout(700)
    check("the formula landed in the new category",
          page.evaluate("""DATA.formulaCategories.includes("Proefcategorie")"""))
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("and Undo takes the category back with it",
          page.evaluate("""!DATA.formulaCategories.includes("Proefcategorie")"""))

    # ---------- 1b. a category change that creates a category goes back in one step (alsoUndo, build 260917c) ----------
    page.evaluate('''() => { const f = DATA.formulas.find(x => x.versions.length === 1);
      switchTab("F", f.id, {type:"v", idx:0}); }''')
    page.wait_for_timeout(500)
    oud = page.evaluate("() => DATA.formulas.find(x => x.id === VIEW.id).category")
    page.click("#btnCatF"); page.wait_for_timeout(400)
    page.evaluate('''() => { window.prompt = () => "Catproef"; }''')
    page.click("#btnNewCat"); page.wait_for_timeout(300)
    page.click("#dlgOk"); page.wait_for_timeout(700)
    check("the formula moved to a category that did not exist yet",
          page.evaluate("() => DATA.formulas.find(x => x.id === VIEW.id).category") == "Catproef"
          and page.evaluate('''DATA.formulaCategories.includes("Catproef")'''))
    fouten = len(errs)
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check(f"one Undo takes the category change and the new category back, without an error ({errs[fouten:][:1]})",
          page.evaluate("() => DATA.formulas.find(x => x.id === VIEW.id).category") == oud
          and page.evaluate('''!DATA.formulaCategories.includes("Catproef")''')
          and len(errs) == fouten)

    # ---------- 2. a predilution takes its two categories back ----------
    page.evaluate("""() => {
      DATA.materials.push(
        {id:"m-u1", name:"Undo stof", category:"Test", pyramid:2, isSolvent:false, costPerGram:1, dilutions:[{pct:100,isBase:true},{pct:10}]},
        {id:"m-u2", name:"Undo solvent", category:"Solvents", pyramid:5, isSolvent:true, dilutions:[{pct:100,isBase:true}]});
      invalidateMats();
      DATA.materialCategories = DATA.materialCategories.filter(c => c !== "Predils");
      DATA.formulaCategories = DATA.formulaCategories.filter(c => c !== "Predilutions");
      DATA.formulas.push({id:"f-u", name:"Undotest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[{materialId:"m-u1", dilutionPct:100, weightG:2, remark:1},
                                   {materialId:"m-u2", dilutionPct:100, weightG:98, remark:1}]}]});
      markDirty(); VIEW = {tab:"F", id:"f-u", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    page.check('input.selCb[data-i="0"]'); page.wait_for_timeout(200)
    page.click("#btnPredil"); page.wait_for_timeout(500)
    page.click("#dlgOk"); page.wait_for_timeout(800)
    check("the predilution made its categories",
          page.evaluate("""DATA.materialCategories.includes("Predils") && DATA.formulaCategories.includes("Predilutions")"""))
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check("and one Undo takes formula, material and both categories back",
          page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions.length)()""") == 1
          and page.evaluate("""!DATA.materialCategories.includes("Predils") && !DATA.formulaCategories.includes("Predilutions")"""))

    # ---------- 3. Replace plus a dilution change is one step ----------
    steps = page.evaluate("UNDO.length")
    page.click("[data-repl='0']"); page.wait_for_timeout(400)
    page.fill("#rmNew", "Hedione"); page.click("#dlgOk"); page.wait_for_timeout(500)
    if page.locator("#dlg").is_visible():
        page.click("#dlgOk"); page.wait_for_timeout(600)      # the dilution dialog, if the new material lacks that dilution
    line = page.evaluate("""(() => { const l = DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0];
      return {m: (matById(l.materialId)||{}).name, dil: l.dilutionPct}; })()""")
    check(f"the material was replaced ({line})", line["m"] == "Hedione")
    check(f"in a single undo step ({steps} → {page.evaluate('UNDO.length')})",
          page.evaluate("UNDO.length") == steps + 1)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("which puts the old material back at once",
          page.evaluate("""(() => (matById(DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0].materialId)||{}).name)()""") == "Undo stof")

    # ---------- 3b. the same through the dilution dialog (build 260915): still one step, and Undo brings the old material back ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
      f.versions[0].lines[0].dilutionPct = 10; markDirty(); render(); }""")      # a dilution Hedione does not have, so Replace opens the dialog
    page.wait_for_timeout(400)
    steps = page.evaluate("UNDO.length")
    page.click("[data-repl='0']"); page.wait_for_timeout(400)
    page.fill("#rmNew", "Hedione"); page.click("#dlgOk"); page.wait_for_timeout(500)
    check("the dilution dialog opened", page.locator("#dlg").is_visible() and "Change dilution" in page.locator("#dlg").inner_text())
    page.click("#dlgOk"); page.wait_for_timeout(600)
    line = page.evaluate("""(() => { const l = DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0];
      return {m: (matById(l.materialId)||{}).name, dil: l.dilutionPct}; })()""")
    check(f"replaced and moved to a dilution Hedione has ({line})", line["m"] == "Hedione" and line["dil"] == 100)
    check(f"in a single undo step ({steps} → {page.evaluate('UNDO.length')})", page.evaluate("UNDO.length") == steps + 1)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    line = page.evaluate("""(() => { const l = DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0];
      return {m: (matById(l.materialId)||{}).name, dil: l.dilutionPct}; })()""")
    check(f"and Undo brings the old material back on its old dilution ({line})", line["m"] == "Undo stof" and line["dil"] == 10)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u"); f.versions[0].lines[0].dilutionPct = 100; markDirty(); render(); }""")
    page.wait_for_timeout(300)

    # ---------- 4. Redo returns to the page the change was on ----------
    w0 = page.locator("input.w").first
    w0.fill("5"); w0.press("Tab"); page.wait_for_timeout(600)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check("Undo took the weight back",
          page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0].weightG)()""") != 5)
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Hedione"); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(500)
    page.keyboard.press("Control+y"); page.wait_for_timeout(800)
    check("and Redo brings you back to the formula it changed, wherever you had wandered off to",
          page.evaluate("VIEW.tab") == "F" and page.evaluate("VIEW.id") == "f-u"
          and page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions[0].lines[0].weightG)()""") == 5)
    page.fill("#searchBox", ""); page.wait_for_timeout(200)

    # ---------- 5. Copy to new formula from an older version takes that version ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
      f.versions.push({v:2, date:today(), lines:[{materialId:"m-u1", dilutionPct:100, weightG:9, remark:1}]});
      markDirty(); VIEW = {tab:"F", id:"f-u", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    page.click("#btnCopyF"); page.wait_for_timeout(500)
    page.fill("#cpName", "Kopie van v1"); page.click("#dlgOk"); page.wait_for_timeout(800)
    cp = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.name === "Kopie van v1");
      return f && {lines: f.versions[0].lines.length, w: f.versions[0].lines[0].weightG}; })()""")
    check(f"the copy takes the version you were looking at, not the latest ({cp})", cp and cp["lines"] == 2)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)

    # ---------- 6. a new version keeps the bench arrangement ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
      VIEW = {tab:"F", id:"f-u", sub:{type:"v", idx:0}}; setTabs(); render(); }""")
    page.wait_for_timeout(500)
    before = page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions[0].bench === undefined)()""")
    check("a version without a bench keeps it that way while rendering", before)
    page.click("#btnBenchToggle"); page.wait_for_timeout(700)
    check("opening the bench view creates the groups",
          page.evaluate("""(() => (DATA.formulas.find(x => x.id === "f-u").versions[0].bench||{groups:[]}).groups.length)()""") == 5)
    page.click("#btnBenchClose"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    check("and a new version takes the arrangement along",
          page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-u");
            const v = f.versions[f.versions.length-1]; return (v.bench||{groups:[]}).groups.length; })()""") == 5)

    # ---------- 7. bouw 260918d: een bench-groep houdt zijn eigen regel vast ----------
    page.evaluate("""() => {
      DATA.formulas.push({id:"f-b", name:"Benchtest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[
          {id:"l-1", materialId:"m-u1", dilutionPct:100, weightG:5,  remark:1},
          {id:"l-2", materialId:"m-u1", dilutionPct:100, weightG:20, remark:1},
          {id:"l-3", materialId:"m-u2", dilutionPct:100, weightG:75, remark:1}]}]});
      buildUsage(); markDirty(); switchTab("F", "f-b", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    page.click("#btnBenchToggle"); page.wait_for_timeout(800)
    page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-b").versions[0];
        v.bench.groups[0].keys = ["l-1"]; markDirty(); render(); }""")   # de regel van 5 g in de eerste groep
    page.wait_for_timeout(600)
    eerst = page.evaluate("""() => { const g = [...document.querySelectorAll("[data-bgi]")][0];
        return [...g.querySelectorAll(".brow")].map(r => r.innerText.replace(/\\s+/g, " ")); }""")
    check(f"de groep toont de regel van 5 g ({eerst})",
          len(eerst) == 1 and "5.000 g" in eerst[0].replace(",", "."))
    page.click("#btnBenchClose"); page.wait_for_timeout(500)
    page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-b").versions[0];
        v.lines = v.lines.filter(l => l.id !== "l-1"); markDirty(); render(); }""")   # de regel van 5 g gewist
    page.wait_for_timeout(500)
    page.click("#btnBenchToggle"); page.wait_for_timeout(800)
    na = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-b").versions[0];
        const g0 = [...document.querySelectorAll("[data-bgi]")][0];
        return {groep: [...g0.querySelectorAll(".brow")].map(r => r.innerText.replace(/\\s+/g, " ")),
                pool: [...document.querySelectorAll("[data-bdrop='pool'] .brow")].map(r => r.innerText.replace(/\\s+/g, " ")),
                keys: v.bench.groups[0].keys}; }""")
    check(f"de groep neemt de regel van 20 g niet over ({na['keys']}, {na['groep']})",
          "l-2" not in na["keys"] and not na["groep"])
    check(f"en die regel staat nog gewoon in de pool ({na['pool']})",
          any("20.000 g" in r.replace(",", ".") for r in na["pool"]))
    page.click("#btnBenchClose"); page.wait_for_timeout(400)
    page.evaluate("""() => { DATA.formulas = DATA.formulas.filter(x => x.id !== "f-b");
        buildUsage(); markDirty(); switchTab("F", "f-u", {type:"v", idx:0}); }""")
    page.wait_for_timeout(500)

    # ---------- 8. Ctrl+P zonder printknop drukt af wat op het scherm staat ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
        switchTab("F", f.id, {type:"v", idx: 0}); }""")
    page.wait_for_timeout(600)
    leeg = page.evaluate("""() => document.querySelector("#printArea").innerHTML.trim().length""")
    check(f"het printblad is leeg zolang er niet gedrukt is ({leeg})", leeg == 0)
    page.evaluate("""() => window.dispatchEvent(new Event("beforeprint"))""")
    page.wait_for_timeout(300)
    blad = page.evaluate("""() => document.querySelector("#printArea").innerText""")
    check(f"Ctrl+P vult het met de versie op het scherm ({blad.split(chr(10))[0]!r})", "Undotest" in blad)
    page.evaluate("""() => { switchTab("M", DATA.materials[0].id, null); }""")
    page.wait_for_timeout(500)
    check("en een nieuwe weergave laat geen oud blad achter",
          page.evaluate("""() => document.querySelector("#printArea").innerHTML.trim().length""") == 0)
    page.evaluate("""() => window.dispatchEvent(new Event("beforeprint"))""")
    page.wait_for_timeout(300)
    blad2 = page.evaluate("""() => document.querySelector("#printArea").innerText""")
    check(f"buiten een formule zegt het blad wat je moet doen ({blad2.split(chr(10))[0]!r})",
          "nothing to print" in blad2.lower())

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
