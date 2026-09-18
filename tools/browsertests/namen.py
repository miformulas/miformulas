"""Names and the library in every path that creates a material (build 260914e): Add line, a formula
import and Delivered bring the facts of the library along, a category is not duplicated by its
capitals, an alternative name you already own is flagged, and renaming cannot make two things with
the same name. Needs the local web server on port 8765 (see README)."""
import json
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

LIB = {"type": "miformulas-materials", "name": "Testbibliotheek", "version": "1", "materials": [
    {"name": "Testolide", "aliases": ["Proefmusk"], "cas": "106-02-5", "category": "musks",
     "pyramid": 4, "ifraLimit": 0.5, "odour": ["musky"], "strength": "high"},
    {"name": "Bestelstof", "cas": "999-99-9", "category": "Test", "pyramid": 2, "ifraLimit": 99},
]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    errs = []; msgs = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    page.evaluate("""pkg => { setMaterialList(normLibrary(pkg));
      if (!DATA.materialCategories.includes("Musks")) DATA.materialCategories.push("Musks");
      DATA.materialCategories.sort((a,b)=>a.localeCompare(b)); render(); }""", LIB)
    page.wait_for_timeout(400)

    # ---------- 1. Add line takes the facts of the library along ----------
    page.evaluate("""() => { DATA.formulas.push({id:"f-n", name:"Naamtest", category:"Uncategorised", created:today(),
      versions:[{v:1, date:today(), lines:[]}]});
      markDirty(); VIEW = {tab:"F", id:"f-n", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(500)
    page.fill("#addMat", "Testolide"); msgs.clear()
    page.click("#btnAddLine"); page.wait_for_timeout(700)
    check(f"the question says the library knows the name ({msgs})",
          any("materials library knows this name" in m for m in msgs))
    m1 = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Testolide");
      return m && {cas: m.cas, cat: m.category, pyr: m.pyramid, ifra: m.ifraLimit, wish: !!m.wishlist, al: m.aliases}; })()""")
    check(f"the new to-order material carries them ({m1})",
          m1 and m1["cas"] == "106-02-5" and m1["pyr"] == 4 and abs(m1["ifra"] - 0.5) < 1e-9 and m1["wish"])
    check(f"and the library category joins your own spelling ({m1['cat']})", m1["cat"] == "Musks")
    check("so no second category appears",
          page.evaluate("""DATA.materialCategories.filter(c => c.toLowerCase() === "musks").length""") == 1)
    check("its alternative names hold the library name",
          "Proefmusk" in (m1["al"] or ""))
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("one undo takes material, order line and category back",
          page.evaluate("""!DATA.materials.some(x => x.name === "Testolide")"""))

    # ---------- 2. typing an alternative name of a material you own ----------
    page.evaluate("""() => { DATA.materials.push({id:"m-own", name:"Ambroxide", category:"Musks", pyramid:4,
      aliases:"Proefalias; Ambrofix", isSolvent:false, dilutions:[{pct:100,isBase:true}]});
      DATA.materials.sort((a,b)=>a.name.localeCompare(b.name)); invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(400)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.fill("#nmName", "Proefalias"); msgs.clear()
    page.click("#dlgOk"); page.wait_for_timeout(600)
    check(f"the app says you already have it under another name ({msgs})",
          any("alternative name" in m for m in msgs) and any("Ambroxide" in m for m in msgs))
    check("and after confirming it is created anyway",
          page.evaluate("""DATA.materials.some(x => x.name === "Proefalias")"""))
    page.evaluate("""() => { DATA.materials = DATA.materials.filter(x => x.name !== "Proefalias"); invalidateMats(); render(); }""")

    # ---------- 3. renaming cannot make two of the same ----------
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Ambroxide"); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(400)
    msgs.clear()
    page.fill('[data-f="name"]', "Hedione"); page.locator('[data-f="name"]').press("Tab"); page.wait_for_timeout(600)
    check(f"renaming a material onto an existing name is refused ({msgs})",
          any("Another material is already called" in m for m in msgs)
          and page.evaluate("""DATA.materials.filter(x => x.name === "Hedione").length""") == 1)
    page.fill('[data-f="name"]', "Ambroxide bis"); page.locator('[data-f="name"]').press("Tab"); page.wait_for_timeout(600)
    check("a free name is accepted and the page follows",
          page.evaluate("""DATA.materials.some(x => x.name === "Ambroxide bis")""")
          and page.locator("#content h2").first.inner_text().strip().endswith("Ambroxide bis"))

    page.fill("#searchBox", ""); page.click("#tabF"); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(500)
    first = page.evaluate("(() => DATA.formulas.find(x => x.id === VIEW.id).name)()")
    other = page.evaluate("(() => DATA.formulas.find(x => x.id !== VIEW.id).name)()")
    msgs.clear()
    page.evaluate(f"""() => {{ window.prompt = () => {json.dumps(other)}; }}""")
    page.click("#btnRenameF"); page.wait_for_timeout(500)
    check(f"renaming a formula onto an existing name is refused ({msgs})",
          any("Another formula is already called" in m for m in msgs)
          and page.evaluate("(() => DATA.formulas.find(x => x.id === VIEW.id).name)()") == first)

    # ---------- 4. an import brings the facts along too ----------
    IMP = {"type": "miformulas-import", "name": "Importtest", "lines": [
        {"material": "Bestelstof", "dilutionPct": 10, "weightG": 2}]}
    page.evaluate("""pkg => { IMPORTP = pkg; VIEW = {tab:"F", id:null, sub:null}; HOMEVIEW = false; render(); }""", IMP)
    page.wait_for_timeout(600)
    page.click("#btnImpOk"); page.wait_for_timeout(800)
    m2 = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Bestelstof");
      return m && {cas: m.cas, cat: m.category, pyr: m.pyramid, ifra: m.ifraLimit, dil: m.dilutions[0].pct, wish: !!m.wishlist}; })()""")
    check(f"the imported material carries the library facts, at the dilution of the import ({m2})",
          m2 and m2["cas"] == "999-99-9" and m2["pyr"] == 2 and m2["ifra"] == 99 and m2["dil"] == 10 and m2["wish"])

    # ---------- 5. Delivered does the same ----------
    page.evaluate("""() => { DATA.materials = DATA.materials.filter(x => x.name !== "Testolide");
      DATA.orderList = [{id:"o-x", materialId:null, name:"Testolide", added:today()}];
      invalidateMats(); markDirty(); VIEW = {tab:"T", id:null, sub:null}; setTabs(); render(); }""")
    page.wait_for_timeout(500)
    page.fill("[data-oamt='0']", "10"); page.locator("[data-oamt='0']").press("Tab"); page.wait_for_timeout(300)
    page.fill("[data-oprice='0']", "20"); page.locator("[data-oprice='0']").press("Tab"); page.wait_for_timeout(300)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(500)
    page.click("#dlgOk"); page.wait_for_timeout(800)
    m3 = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Testolide");
      return m && {cas: m.cas, cat: m.category, cpg: m.costPerGram, inv: m.inventory, wish: !!m.wishlist}; })()""")
    check(f"a delivered material that the library knows is not bare ({m3})",
          m3 and m3["cas"] == "106-02-5" and m3["cat"] == "Musks" and abs(m3["cpg"] - 2) < 1e-9 and not m3["wish"])

    # ---------- 6. bouw 260918c: een alternatieve naam telt meteen mee ----------
    page.evaluate("""() => {
      DATA.materials = [{id:"m-amb", name:"Ambroxide", category:"Test", pyramid:4, isSolvent:false,
                         dilutions:[{pct:100, isBase:true}]}];
      DATA.orderList = [];
      DATA.formulas = [{id:"f-al", name:"Aliastest", category:"Uncategorised", created:today(),
                        versions:[{v:1, date:today(), lines:[{materialId:"m-amb", dilutionPct:100, weightG:10, remark:1}]}]}];
      invalidateMats(); buildUsage(); markDirty();
      matByName("Ambroxide");                       // de naamindex staat er nu, zoals na een import of een Add line
      VIEW = {tab:"M", id:"m-amb", sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(700)
    page.fill("[data-f='aliases']", "Ambroxan")
    page.locator("[data-f='aliases']").press("Tab"); page.wait_for_timeout(600)
    check("de alias wordt meteen door de naamindex gevonden",
          page.evaluate("""() => { const m = matByName("Ambroxan"); return m && m.name; }""") == "Ambroxide")
    msgs.clear()
    page.evaluate("""() => { switchTab("F", "f-al", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    page.fill("#addMat", "Ambroxan"); page.click("#btnAddLine"); page.wait_for_timeout(800)
    na = page.evaluate("""() => ({m: DATA.materials.length, o: (DATA.orderList || []).length,
        regels: DATA.formulas[0].versions[0].lines.map(l => l.materialId)})""")
    check(f"Add line landt op het bestaande materiaal, zonder tweede materiaal of bestelregel ({na})",
          na["m"] == 1 and na["o"] == 0 and na["regels"] == ["m-amb", "m-amb"])
    check("en de tweede regel op dezelfde dilutie vroeg eerst om bevestiging",
          any("already in this version" in m for m in msgs))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)

    # ---------- 7. hernoemen naar een naam die een ander als alias draagt ----------
    page.evaluate("""() => {
      DATA.materials.push({id:"m-and", name:"Andere stof", category:"Test", pyramid:2, isSolvent:false,
                           dilutions:[{pct:100, isBase:true}]});
      invalidateMats(); markDirty(); switchTab("M", "m-and", null); }""")
    page.wait_for_timeout(700)
    msgs.clear()
    page.fill("[data-f='name']", "Ambroxan")
    page.locator("[data-f='name']").press("Tab"); page.wait_for_timeout(700)
    check(f"hernoemen naar andermans alias vraagt eerst ({[m[:45] for m in msgs]})",
          any("as an alternative name" in m for m in msgs))
    check("en gaat door als je ja zegt, want de eigen naam wint van een alias",
          page.evaluate("""() => { const m = matByName("Ambroxan"); return m && m.id; }""") == "m-and")

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
