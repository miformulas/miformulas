"""What the app refuses to swallow (build 260914f): negative weights, dilutions outside 0 to 100,
duplicate dilutions, a material left without a base dilution, text where a number belongs, and fields
of your own that start with an underscore. Plus the daily snapshot of the state you opened with, a
version that came in through Move into… and the hidden import reference. Build 260915: a negative target
total, a base dilution outside 0-100 in + New material, and Set EtOH without an ethanol material.
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

    # the snapshot of the state you opened with is written at once
    snap = page.evaluate("idb.get('dailyBak').then(b => b && {date: b.date, n: JSON.parse(b.json).formulas.length})")
    check(f"a daily snapshot is kept from the start ({snap})", snap and snap["n"] == 16)

    # ---------- 1. weights ----------
    page.evaluate("""() => {
      DATA.formulas.push({id:"f-v", name:"Validatietest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[{materialId: DATA.materials[0].id, dilutionPct:100, weightG:10, remark:1}]}], variations:[]});
      markDirty(); VIEW = {tab:"F", id:"f-v", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(500)
    msgs.clear()
    page.fill("input.w", "-5"); page.locator("input.w").press("Tab"); page.wait_for_timeout(500)
    w = page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions[0].lines[0].weightG)()""")
    check(f"a negative weight is refused ({msgs}, weight {w})",
          any("cannot be negative" in m for m in msgs) and w == 10)
    page.fill("input.w", "abc"); page.locator("input.w").press("Tab"); page.wait_for_timeout(500)
    check("and unreadable input puts the old figure back",
          page.locator("input.w").first.input_value().startswith("10")
          and page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions[0].lines[0].weightG)()""") == 10)

    # ---------- 2. dilutions ----------
    page.evaluate("""() => { window.prompt = () => "150"; }""")
    msgs.clear()
    page.select_option("[data-dil='0']", "custom"); page.wait_for_timeout(500)
    check(f"a dilution above 100 % is refused ({msgs})", any("between 0 and 100" in m for m in msgs))
    check("and the line keeps its dilution",
          page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions[0].lines[0].dilutionPct)()""") == 100)

    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Hedione"); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(500)
    before = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Hedione"); return m.dilutions.length; })()""")
    msgs.clear()
    page.fill("#newDil", "100"); page.click("#btnAddDil"); page.wait_for_timeout(500)
    check(f"a dilution that already exists is refused ({msgs})", any("already has a" in m for m in msgs))
    page.fill("#newDil", "0"); page.click("#btnAddDil"); page.wait_for_timeout(400)
    check("and so is 0 %", any("between 0 and 100" in m for m in msgs))
    check("nothing was added", page.evaluate("""(() => DATA.materials.find(x => x.name === "Hedione").dilutions.length)()""") == before)
    page.fill("#newDil", "25"); page.click("#btnAddDil"); page.wait_for_timeout(500)
    check("a proper dilution is accepted",
          page.evaluate("""(() => DATA.materials.find(x => x.name === "Hedione").dilutions.some(d => d.pct === 25))()"""))

    # deleting the base dilution leaves a base behind
    base_i = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Hedione");
      return m.dilutions.findIndex(d => d.isBase); })()""")
    page.click(f"[data-deldil='{base_i}']"); page.wait_for_timeout(600)
    dil = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Hedione");
      return {n: m.dilutions.length, base: (m.dilutions.find(d => d.isBase)||{}).pct, high: Math.max(...m.dilutions.map(d => d.pct))}; })()""")
    check(f"deleting the base dilution promotes the highest one left ({dil})", dil["base"] == dil["high"])

    # ---------- 3. numbers that arrive as text ----------
    calc = page.evaluate("""(() => { const id = DATA.materials[0].id;
      const K = calc([{materialId: id, dilutionPct: "10", weightG: "2"}, {materialId: id, dilutionPct: 100, weightG: 3}]);
      return {w: K.totalW, c: +K.content.toFixed(4)}; })()""")
    check(f"text in a weight or dilution still computes ({calc})", calc["w"] == 5 and abs(calc["c"] - 3.2) < 1e-9)

    # ---------- 4. a field of your own that starts with an underscore ----------
    page.evaluate("""() => { (DATA.categoryColours ||= {})["_Archive"] = "#123456"; markDirty(); }""")
    kept = page.evaluate("""(() => JSON.parse(serialize()).categoryColours["_Archive"])()""")
    check(f"it survives saving ({kept})", kept == "#123456")
    check("while our own transient flags do not",
          page.evaluate("""(() => { DATA.materials[0]._descHit = true;
            const out = JSON.parse(serialize()).materials[0]._descHit; delete DATA.materials[0]._descHit; return out; })()""") is None)

    # ---------- 5. a version that came in through Move into… can be deleted ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-v");
      f.versions.push({v:2, date:today(), imported:true, frozen:true, sourceName:"Aura v05",
        lines:[{materialId: DATA.materials[0].id, dilutionPct:100, weightG:5, remark:1}]});
      markDirty(); VIEW = {tab:"F", id:"f-v", sub:{type:"v", idx:1}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    check("an imported version offers Delete version", page.locator("#btnDelV").is_visible())
    check("and it says where it came from", "imported as “Aura v05”" in page.text_content(".metaLine"))

    # the import reference can be hidden without losing it
    page.click("#btnNameV"); page.wait_for_timeout(400)
    page.uncheck("#vnSrc"); page.click("#dlgOk"); page.wait_for_timeout(600)
    v2 = page.evaluate("""(() => { const v = DATA.formulas.find(x => x.id === "f-v").versions[1];
      return {src: v.sourceName, hide: !!v.hideSource, notes: v.notes || ""}; })()""")
    check(f"the reference is hidden but kept, so a second import still knows it ({v2})",
          v2["src"] == "Aura v05" and v2["hide"] and "Imported as" in v2["notes"])
    check("and the line above no longer shows it", "imported as" not in page.text_content(".metaLine"))
    msgs.clear()
    page.click("#btnDelV"); page.wait_for_timeout(600)
    check(f"deleting it asks first and then does it ({msgs})",
          any("Delete" in m for m in msgs)
          and page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions.length)()""") == 1)

    # ---------- 5b. build 260915: a target below zero, a base dilution outside 0-100, Set EtOH ----------
    page.evaluate("""() => { VIEW = {tab:"F", id:"f-v", sub:{type:"v", idx:0}}; SCALEOPEN = true; render(); }""")
    page.wait_for_timeout(500)
    w_before = page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions[0].lines[0].weightG)()""")
    steps = page.evaluate("UNDO.length")
    msgs.clear()
    page.fill("#scaleW", "-100"); page.click("#btnApplyScale"); page.wait_for_timeout(500)
    w_after = page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").versions[0].lines[0].weightG)()""")
    check(f"a negative target total is refused ({msgs}, {w_before} → {w_after})",
          any("above 0" in m for m in msgs) and w_after == w_before and page.evaluate("UNDO.length") == steps)
    msgs.clear()
    page.click("#btnNewVar"); page.wait_for_timeout(400)
    page.fill("#nvLabel", "neg"); page.fill("#nvTarget", "-50"); page.click("#dlgOk"); page.wait_for_timeout(500)
    check(f"and so is a negative target for a new variation ({msgs})",
          any("above 0" in m for m in msgs)
          and page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-v").variations.length)()""") == 0)
    if page.locator("#dlg").is_visible(): page.keyboard.press("Escape"); page.wait_for_timeout(300)
    msgs.clear()
    n_mat = page.evaluate("DATA.materials.length")
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.fill("#nmName", "Honderdvijftig"); page.fill("#nmDil", "150"); page.click("#dlgOk"); page.wait_for_timeout(500)
    check(f"+ New material refuses a base dilution above 100 % ({msgs})",
          any("between 0 and 100" in m for m in msgs) and page.evaluate("DATA.materials.length") == n_mat)
    if page.locator("#dlg").is_visible(): page.keyboard.press("Escape"); page.wait_for_timeout(300)
    # Set EtOH: without an ethanol material it leaves no empty undo step; with one, the line takes its base dilution
    page.evaluate("""() => { window.__eth = DATA.materials.filter(isEthanol).map(m => m.id);
      __eth.forEach(id => { matById(id).isSolvent = false; }); invalidateMats();
      VIEW = {tab:"F", id:"f-v", sub:{type:"v", idx:0}}; SCALEOPEN = true; render(); }""")
    page.wait_for_timeout(400)
    steps = page.evaluate("UNDO.length"); msgs.clear()
    page.fill("#targetAbs", "5"); page.click("#btnSetAbs"); page.wait_for_timeout(500)
    check(f"Set EtOH without an ethanol material says so and leaves no undo step ({msgs}, {steps} → {page.evaluate('UNDO.length')})",
          any("No ethanol" in m for m in msgs) and page.evaluate("UNDO.length") == steps)
    page.evaluate("""() => { __eth.forEach(id => { matById(id).isSolvent = true; });
      const e = DATA.materials.find(isEthanol); e.dilutions = [{pct:96, isBase:true}]; invalidateMats(); render(); }""")
    page.wait_for_timeout(400)
    page.fill("#targetAbs", "5"); page.click("#btnSetAbs"); page.wait_for_timeout(600)
    eth = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-v");
      const l = f.versions[0].lines.find(l => isEthanol(matById(l.materialId))); return l && l.dilutionPct; })()""")
    check(f"and the ethanol line it adds takes the material's base dilution ({eth} %)", eth == 96)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    page.evaluate("""() => { const e = DATA.materials.find(isEthanol); e.dilutions = [{pct:100, isBase:true}]; invalidateMats(); }""")

    # ---------- 6. the snapshot is offered when the data is gone ----------
    page.evaluate("""() => { DATA.formulas.find(x => x.id === "f-v").name = "Gewijzigd"; markDirty(); }""")
    page.wait_for_timeout(3200)
    page.evaluate("""() => idb.set("demoData", null)""")
    pg2 = ctx.new_page(); pg2.on("dialog", lambda d: d.accept())
    pg2.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg2.goto(URL); pg2.wait_for_timeout(1500)
    check("the start screen offers the snapshot", pg2.locator("#btnSnap").is_visible()
          and "Restore daily snapshot" in pg2.locator("#btnSnap").inner_text())
    pg2.click("#btnSnap"); pg2.wait_for_timeout(1200)
    check("which brings back the state you opened with, not the changed one",
          pg2.evaluate("DATA.formulas.length") == 16
          and pg2.evaluate("""!DATA.formulas.some(f => f.name === "Gewijzigd")"""))

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
