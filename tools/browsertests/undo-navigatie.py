"""Undo, Redo and where you land (build 260914g): a new category goes back with the action that made
it, a predilution takes its two categories back, Replace plus a dilution change is one step, Redo
returns to the place the change was made, Copy from an older version takes that version, and a new
version keeps the bench arrangement. Build 260922j: Ctrl+Z in a field you have not typed in is the app's undo (B6),
Redo lands where the change was made (B7), the bench view stores its groups at the first change and works on a version
without an arrangement (B8, C-a 6), Cancel in Replace keeps Redo (C-a 3), no name of spaces and no empty step from Name
version (C-a 4, C-a 5), and a predilution keeps the arrangement and takes its colour back on Undo (C-a 1, P2).
Needs the local web server on port 8765 (see README)."""
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
    # bouw 260922f: de regels van de predilutieformule dragen een id, zoals elke regel (anders past een bench erop niet na herladen)
    pids = page.evaluate("""() => { const pf = DATA.formulas.find(x => x.category === "Predilutions");
        return pf ? pf.versions[0].lines.map(l => typeof l.id === "string" && l.id.startsWith("l-")) : null; }""")
    check(f"en de regels van de predilutieformule dragen een id ({pids})", bool(pids) and all(pids))
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
    # bouw 260922j (B8, C-a 6): openen schrijft niets en is geen undo-stap; de eerste handeling bewaart de vijf
    # groepen, binnen haar eigen undo-stap
    u0 = page.evaluate("UNDO.length")
    page.click("#btnBenchToggle"); page.wait_for_timeout(700)
    check(f"opening the bench view shows five groups, writes nothing and takes no undo step ({page.evaluate('UNDO.length') - u0})",
          page.locator("[data-bgi]").count() == 5
          and page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions[0].bench === undefined)()""")
          and page.evaluate("UNDO.length") == u0)
    page.locator(".bsel").first.check(); page.select_option("#bMoveSel", "1"); page.wait_for_timeout(700)
    eerste = page.evaluate("""(() => { const b = DATA.formulas.find(x => x.id === "f-u").versions[0].bench;
        return b ? b.groups.map(g => g.keys.length).join(",") + "|" + b.byId : null; })()""")
    check(f"the first move stores the five groups, the line in group 2, in one undo step ({eerste})",
          eerste == "0,1,0,0,0|true" and page.evaluate("UNDO.length") == u0 + 1)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("and its Undo takes the whole arrangement back, while the view stays the bench",
          page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-u").versions[0].bench === undefined)()""")
          and page.locator("[data-bgi]").count() == 5)
    page.keyboard.press("Control+y"); page.wait_for_timeout(700)
    page.click("#btnBenchClose"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    check("and a new version takes the arrangement along",
          page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-u");
            const v = f.versions[f.versions.length-1]; return (v.bench||{groups:[]}).groups.length; })()""") == 5)

    # mini-audit C13: 260920k haalde de bench-vlag door Close compare en de versiekiezer, maar
    # + New version en Delete version schreven VIEW.sub zonder die vlag en zetten je op de tabel
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
      VIEW = {tab:"F", id:"f-u", sub:{type:"v", idx:f.versions.length-1, bench:true}}; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    check("de bench view staat open", page.locator(".brow").count() > 0)
    page.click("#btnNewV"); page.wait_for_timeout(800)
    check(f"+ New version laat je in de bench view ({page.evaluate('() => !!(VIEW.sub && VIEW.sub.bench)')})",
          page.evaluate("() => !!(VIEW.sub && VIEW.sub.bench)") and page.locator(".brow").count() > 0)
    check("en op de nieuwe versie",
          page.evaluate("""() => VIEW.sub.idx === DATA.formulas.find(x => x.id === "f-u").versions.length - 1"""))
    msgs.clear()
    page.click("#btnDelV"); page.wait_for_timeout(800)
    check(f"Delete version ook ({page.evaluate('() => !!(VIEW.sub && VIEW.sub.bench)')}, {[m[:40] for m in msgs]})",
          page.evaluate("() => !!(VIEW.sub && VIEW.sub.bench)") and page.locator(".brow").count() > 0)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
      while (f.versions.length > 1) f.versions.pop();
      VIEW = {tab:"F", id:"f-u", sub:{type:"v", idx:0}}; setTabs(); render(); }""")
    page.wait_for_timeout(500)

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
        (typeof benchFor === "function" ? benchFor(v) : v.bench).groups[0].keys = ["l-1"]; markDirty(); render(); }""")   # de regel van 5 g in de eerste groep
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

    # ---------- 7b. bouw 260922f: een schikking die in de app gemaakt is, overleeft herladen en Redo ----------
    # De eerste keer Bench view maakte een bench zonder de vlag byId, en migrate haalde de sleutels dan door de
    # kaart van oude sleutels, waar een regel-id nooit in staat: elke groep was leeg na de volgende herlaadbeurt,
    # en ook na één Redo, want redo() draait migrate op de hele data.
    page.evaluate("""() => {
      DATA.formulas.push({id:"f-r", name:"Reloadtest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[
          {id:"l-r1", materialId:"m-u1", dilutionPct:100, weightG:5,  remark:1},
          {id:"l-r2", materialId:"m-u2", dilutionPct:100, weightG:95, remark:1}]}]});
      buildUsage(); markDirty(); switchTab("F", "f-r", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    page.click("#btnBenchToggle"); page.wait_for_timeout(800)   # sinds 260922j maakt pas de eerste handeling de bench aan
    page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-r").versions[0];
        (typeof benchFor === "function" ? benchFor(v) : v.bench).groups[0].keys = ["l-r1", "l-r2"]; markDirty(); render(); }""")
    page.wait_for_timeout(300)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-r"); snapF(f); f.name = "Reloadtest 2"; markDirty(); render(); }""")
    page.wait_for_timeout(300)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    page.keyboard.press("Control+y"); page.wait_for_timeout(600)
    naRedo = page.evaluate("""() => DATA.formulas.find(x => x.id === "f-r").versions[0].bench.groups[0].keys""")
    check(f"na Undo en Redo staat de schikking er nog ({naRedo})", naRedo == ["l-r1", "l-r2"])
    page.evaluate("() => saveData()"); page.wait_for_timeout(800)
    page.reload(); page.wait_for_timeout(1500)
    naReload = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-r").versions[0];
        return [v.bench.byId === true, v.bench.groups[0].keys]; }""")
    check(f"na herladen ook ({naReload})", naReload[1] == ["l-r1", "l-r2"] and naReload[0])
    page.evaluate("""() => { DATA.formulas = DATA.formulas.filter(x => x.id !== "f-r");
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

    # ---------- 9. het weegblad herschaalt niet (bouw 260920b) ----------
    # Een blad op een ander gewicht dan de versie zou een batch op de bank leggen waar geen versienummer
    # naar terugwijst; Batch scaling hoort daarom bij de bewerkbare versie en het blad drukt wat er staat.
    page.evaluate("""() => {
        DATA.formulas.push({id:"f-print", name:"Printtest", category:"Uncategorised", versions:[
          {v:1, frozen:true, date:today(), lines:[{id:"p1", materialId:DATA.materials[0].id, dilutionPct:100, weightG:40, remark:1}]},
          {v:2, date:today(), lines:[{id:"p2", materialId:DATA.materials[0].id, dilutionPct:100, weightG:50, remark:1}]}]});
        buildUsage(); SCALEOPEN = true; switchTab("F", "f-print", {type:"v", idx:1}); }""")
    page.wait_for_timeout(700)
    check("de bewerkbare versie heeft Batch scaling", page.locator("#scaleBox").count() == 1)
    page.fill("#scaleW", "500")                      # een doelgewicht invullen, niet toepassen
    page.evaluate("""() => { window.print = () => { window.__printed = true; }; }""")
    page.click("#btnPrint"); page.wait_for_timeout(500)
    blad = page.evaluate("""() => document.getElementById("printArea").innerText.replace(/,/g, ".")""")
    check(f"het blad drukt het opgeslagen gewicht ({blad.splitlines()[1] if len(blad.splitlines()) > 1 else blad!r})",
          page.evaluate("() => !!window.__printed") and "50.000" in blad and "500.000" not in blad)
    check("en de kopregel noemt het totaal, geen doel", " total " in blad and "target" not in blad)
    page.evaluate("""() => { document.getElementById("printArea").innerHTML = ""; window.dispatchEvent(new Event("beforeprint")); }""")
    blad3 = page.evaluate("""() => document.getElementById("printArea").innerText.replace(/,/g, ".")""")
    check("en Ctrl+P zonder knop drukt hetzelfde blad", "50.000" in blad3 and "500.000" not in blad3)
    bewaard = page.evaluate("""() => DATA.formulas.find(x => x.id === "f-print").versions[1].lines[0].weightG""")
    check(f"het invullen van een doelgewicht raakt de versie niet ({bewaard})", bewaard == 50)
    page.evaluate("""() => switchTab("F", "f-print", {type:"v", idx:0})""")
    page.wait_for_timeout(600)
    check("een bevroren versie heeft geen Batch scaling meer", page.locator("#scaleBox").count() == 0)
    check("en dus ook geen doelgewichtveld", page.locator("#scaleW").count() == 0)

    # ---------- 10. B6 (bouw 260922j): Ctrl+Z in een veld waarin je niets typte, is de undo van de app ----------
    # Na Add line en na een gewicht zet de app de cursor terug in een veld, en Ctrl+Z ging dan naar dat veld, dat niets
    # terug te nemen had. Een veld waarin je typt, houdt zijn eigen Ctrl+Z, ook nadat je het typwerk terugnam.
    page.evaluate("""() => { const ms = DATA.materials.filter(m => !m.isSolvent && m.id !== "m-u1").slice(0, 3);
        DATA.formulas.push({id:"f-z", name:"Ctrlztest", category:"Uncategorised", created:today(), versions:[
          {v:1, date:today(), lines: ms.map((m, i) => ({id:"z" + i, materialId:m.id, dilutionPct:(m.dilutions.find(d => d.isBase) || m.dilutions[0]).pct,
            weightG:1 + i, remark:1}))}]});
        buildUsage(); markDirty(); switchTab("F", "f-z", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    zl = lambda: page.evaluate("""() => DATA.formulas.find(x => x.id === "f-z").versions[0].lines.length""")
    zw = lambda: page.evaluate("""() => DATA.formulas.find(x => x.id === "f-z").versions[0].lines[0].weightG""")
    n0 = zl()
    page.fill("#addMat", "Hedione"); page.keyboard.press("Enter"); page.wait_for_timeout(700)
    n1 = zl(); foc = page.evaluate("() => document.activeElement.id")
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check(f"Add line, then Ctrl+Z with the cursor back in the box: the line goes ({n0} → {n1} → {zl()}, cursor in {foc})",
          n1 == n0 + 1 and zl() == n0 and foc == "addMat")
    page.locator("input.w").first.fill("7"); page.keyboard.press("Enter"); page.wait_for_timeout(600)
    w1 = zw(); foc = page.evaluate("() => document.activeElement.className")
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check(f"a weight with Enter, then Ctrl+Z in that field: the weight goes back ({w1} → {zw()}, cursor in {foc})",
          w1 == 7 and zw() == 1 and foc == "w")
    page.locator("input.w").first.fill("8"); page.keyboard.press("Tab"); page.wait_for_timeout(600)
    foc = page.evaluate("() => { const a = document.activeElement; return a.className + ':' + a.dataset.i; }")
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check(f"a weight with Tab, then Ctrl+Z in the next weight: the weight goes back ({zw()}, cursor in {foc})",
          zw() == 1 and foc == "w:1")
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z"); snapF(f); f.name = "Ctrlztest hernoemd"; markDirty(); render(); }""")
    page.wait_for_timeout(500)
    page.locator("input.selCb").first.check(); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("a ticked box does not hold Ctrl+Z back",
          page.evaluate("""() => DATA.formulas.find(x => x.id === "f-z").name""") == "Ctrlztest")
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z"); snapF(f); f.name = "Ctrlztest 2"; markDirty(); render(); }""")
    page.wait_for_timeout(500)
    u1 = page.evaluate("UNDO.length")
    page.locator("input.w").first.click(); page.keyboard.press("End"); page.keyboard.type("5")
    for _ in range(3):
        page.keyboard.press("Control+z"); page.wait_for_timeout(250)
    check(f"typing in a weight and pressing Ctrl+Z three times takes back the typing, never a change of the app ({u1} → {page.evaluate('UNDO.length')})",
          page.evaluate("UNDO.length") == u1 and zw() == 1
          and page.evaluate("""() => DATA.formulas.find(x => x.id === "f-z").name""") == "Ctrlztest 2")
    page.click("#addMat"); page.keyboard.type("Hed")
    for _ in range(2):
        page.keyboard.press("Control+z"); page.wait_for_timeout(250)
    check("and the same in the box under the table", page.evaluate("UNDO.length") == u1)
    page.click("#content h2"); page.wait_for_timeout(200)
    page.locator("input.w").first.fill("9"); page.keyboard.press("Enter"); page.wait_for_timeout(600)
    page.click("#btnUndo"); page.wait_for_timeout(600)
    page.click("#addMat"); page.keyboard.press("Control+y"); page.wait_for_timeout(700)
    check(f"Ctrl+Y in a field you have not typed in is the app's redo ({zw()})", zw() == 9)

    # ---------- 11. B7 (bouw 260922j): Redo gaat naar de plek van de wijziging, niet naar waar je Undo drukte ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z"); snapF(f); f.name = "Redoplek"; markDirty(); render(); }""")
    page.wait_for_timeout(400)
    page.evaluate("""() => switchTab("M", DATA.materials[5].id, null)"""); page.wait_for_timeout(500)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    na_undo = page.evaluate("() => [VIEW.tab, VIEW.id]")
    page.evaluate("""() => switchTab("M", DATA.materials[6].id, null)"""); page.wait_for_timeout(500)
    page.click("#content h2"); page.keyboard.press("Control+y"); page.wait_for_timeout(700)
    na_redo = page.evaluate("""() => [VIEW.tab, VIEW.id, DATA.formulas.find(x => x.id === "f-z").name]""")
    check(f"Undo goes to the formula ({na_undo}), and so does Redo, wherever you press it ({na_redo})",
          na_undo == ["F", "f-z"] and na_redo == ["F", "f-z", "Redoplek"])
    page.evaluate("""() => switchTab("M", DATA.materials[6].id, null)"""); page.wait_for_timeout(500)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("and the Undo that Redo leaves behind goes there as well",
          page.evaluate("""() => [VIEW.tab, VIEW.id, DATA.formulas.find(x => x.id === "f-z").name]""") == ["F", "f-z", "Ctrlztest 2"])

    # ---------- 12. B8 (bouw 260922j): een versie zonder schikking, bereikt met de bench view open ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z");
        f.versions.push({v:2, date:today(), lines: structuredClone(f.versions[0].lines),
          bench: {groups:[{id:"gz", title:"Kern", keys:["z0"]}], byId:true}});
        buildUsage(); markDirty(); switchTab("F", "f-z", {type:"v", idx:1, bench:true}); }""")
    page.wait_for_timeout(700)
    page.select_option("#verSel", "0"); page.wait_for_timeout(700)
    fouten = len(errs); u2 = page.evaluate("UNDO.length")
    groepen = page.locator("[data-bgi]").count()
    page.locator(".bsel").first.check(); page.select_option("#bMoveSel", "pool"); page.wait_for_timeout(500)
    check(f"v1 without an arrangement shows five groups ({groepen}), and sending to Unsorted what is there already takes no step",
          groepen == 5 and page.evaluate("UNDO.length") == u2 and len(errs) == fouten)
    page.click("#btnAddGroup"); page.wait_for_timeout(600)
    n = page.evaluate("""() => (DATA.formulas.find(x => x.id === "f-z").versions[0].bench || {groups:[]}).groups.length""")
    check(f"+ Add group works there, without an error, in one undo step ({n} groups, {errs[fouten:][:1]})",
          n == 6 and len(errs) == fouten and page.evaluate("UNDO.length") == u2 + 1)
    if page.locator("#bMoveSel option[value='2']").count():   # op 260922i stond hier geen enkele groep
        page.locator(".bsel").first.check(); page.select_option("#bMoveSel", "2"); page.wait_for_timeout(600)
    check("and so does Move ticked to…", len(errs) == fouten
          and page.evaluate("""() => ((DATA.formulas.find(x => x.id === "f-z").versions[0].bench || {groups: []}).groups[2] || {keys: []}).keys.length""") == 1)
    page.click("#btnBenchClose"); page.wait_for_timeout(400)

    # ---------- 13. C-a 3 (bouw 260922j): Cancel in ⇄ Replace met het dilutievenster laat Redo en de datum staan ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u"); f.versions[0].lines[0].dilutionPct = 10;
        switchTab("F", "f-u", {type:"v", idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(600)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u"); snapF(f); f.versions[0].lines[1].weightG = 90; markDirty(); render(); }""")
    page.wait_for_timeout(300)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    page.evaluate("""() => { DATA.formulas.find(x => x.id === "f-u").modified = "2020-01-01 00:00"; }""")
    r0 = page.evaluate("REDO.length")
    page.click("[data-repl='0']"); page.wait_for_timeout(400)
    page.fill("#rmNew", "Hedione"); page.click("#dlgOk"); page.wait_for_timeout(500)
    venster = page.locator("#dlg").is_visible() and "Change dilution" in page.locator("#dlg").inner_text()
    page.click("#dlgCancel"); page.wait_for_timeout(500)
    na = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-u");
        return {redo: REDO.length, knopUit: $("#btnRedo").disabled, mod: f.modified, m: (matById(f.versions[0].lines[0].materialId)||{}).name}; }""")
    check(f"Cancel in the dilution window of ⇄ Replace keeps the Redo step and the date of the formula ({venster}, {r0} → {na})",
          venster and r0 == 1 and na["redo"] == 1 and not na["knopUit"] and na["mod"] == "2020-01-01 00:00" and na["m"] == "Undo stof")
    page.click("#content h2"); page.keyboard.press("Control+y"); page.wait_for_timeout(600)
    check("and that Redo still works",
          page.evaluate("""() => DATA.formulas.find(x => x.id === "f-u").versions[0].lines[1].weightG""") == 90)

    # ---------- 14. C-a 4 en C-a 5 (bouw 260922j): geen naam van spaties, en Apply zonder wijziging is geen stap ----------
    page.evaluate("""() => { window.prompt = () => "   "; }""")
    u3 = page.evaluate("UNDO.length")
    page.click("#btnRenameF"); page.wait_for_timeout(400)
    check("Rename refuses a name of spaces alone",
          page.evaluate("""() => DATA.formulas.find(x => x.id === "f-u").name""") == "Undotest" and page.evaluate("UNDO.length") == u3)
    page.click("#btnNameV"); page.wait_for_timeout(400); page.click("#dlgOk"); page.wait_for_timeout(400)
    check(f"Name version with Apply and nothing changed takes no undo step ({u3} → {page.evaluate('UNDO.length')})",
          page.evaluate("UNDO.length") == u3)
    page.click("#btnNameV"); page.wait_for_timeout(400); page.fill("#vnName", "met label"); page.click("#dlgOk"); page.wait_for_timeout(400)
    check("with a change it does",
          page.evaluate("UNDO.length") == u3 + 1
          and page.evaluate("""() => DATA.formulas.find(x => x.id === "f-u").versions[0].name""") == "met label")

    # ---------- 15. C-a 1 en P2 (bouw 260922j): Create predilution neemt de schikking mee, en Undo ook de kleur ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z"), v = f.versions[f.versions.length - 1];
        v.bench = {groups:[{id:"gk", title:"Kern", keys:[v.lines[1].id, v.lines[2].id]}], byId:true};
        DATA.materialCategories = DATA.materialCategories.filter(c => c !== "Predils");
        DATA.formulaCategories = DATA.formulaCategories.filter(c => c !== "Predilutions");
        delete DATA.categoryColours["Predils"]; markDirty(); switchTab("F", "f-z", {type:"v", idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(700)
    page.check('input.selCb[data-i="0"]'); page.click("#btnPredil"); page.wait_for_timeout(500)
    page.click("#dlgOk"); page.wait_for_timeout(800)
    pd = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-z"), v = f.versions[f.versions.length - 1];
        return {versies: f.versions.length, groep: v.bench ? v.bench.groups[0].keys.length : null, kleur: DATA.categoryColours["Predils"] || null}; }""")
    check(f"the predilution version keeps the arrangement ({pd})", pd["versies"] == 3 and pd["groep"] == 2 and pd["kleur"])
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check("and its Undo takes the colour of Predils back with the category",
          page.evaluate("""() => !DATA.materialCategories.includes("Predils") && !("Predils" in DATA.categoryColours)"""))

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
