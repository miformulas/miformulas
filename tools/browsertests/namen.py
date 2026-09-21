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

    # ---------- 8. bouw 260918e: Uncategorised als vertrekpunt en een kleur per categorie ----------
    page.evaluate("""() => { switchTab("F", null, null); }"""); page.wait_for_timeout(500)
    page.click("#btnNew"); page.wait_for_timeout(500)
    check(f"een nieuwe formule vertrekt van Uncategorised ({page.locator('#catSel').input_value()!r})",
          page.locator("#catSel").input_value() == "Uncategorised")
    page.fill("#nfName", "Kleurtest A"); page.select_option("#catSel", "Predilutions")
    page.click("#dlgOk"); page.wait_for_timeout(800)
    check("die in de gekozen categorie landt",
          page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Kleurtest A"); return f && f.category; }""")
          == "Predilutions")
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Kleurtest A");
        switchTab("F", f.id, {type:"v", idx:0}); }"""); page.wait_for_timeout(600)
    page.evaluate("""() => switchTab("F", null, null)"""); page.wait_for_timeout(500)
    page.click("#btnNew"); page.wait_for_timeout(500)
    check(f"en de volgende vertrekt weer van Uncategorised, niet van de laatst bekeken formule "
          f"({page.locator('#catSel').input_value()!r})",
          page.locator("#catSel").input_value() == "Uncategorised")
    check("met een kleurkiezer ernaast", page.locator("#catCol").count() == 1
          and not page.locator("#catCol").is_disabled())
    kleur0 = page.locator("#catCol").input_value()
    uncat = page.evaluate("""() => ((DATA.categoryColours||{})["Uncategorised"] || "").toLowerCase()""")
    check(f"die de kleur van die categorie toont ({kleur0!r})", kleur0 == uncat)
    page.select_option("#catSel", "Predilutions"); page.wait_for_timeout(400)
    zonder = page.locator("#catCol").input_value()
    check(f"en meewisselt met de keuzelijst ({zonder!r} voor Predilutions, dat er nog geen heeft)",
          zonder != uncat)
    page.evaluate("""() => { const c = document.querySelector("#catCol");
        c.value = "#3366cc"; c.dispatchEvent(new Event("change")); }""")
    page.wait_for_timeout(500)
    check("een kleur blijft bij de categorie, niet bij de formule",
          page.evaluate("""() => (DATA.categoryColours||{})["Predilutions"]""") == "#3366cc")
    page.select_option("#catSel", "Uncategorised"); page.wait_for_timeout(300)
    check(f"en de kiezer volgt terug ({page.locator('#catCol').input_value()!r})",
          page.locator("#catCol").input_value() == uncat)
    page.select_option("#catSel", "Predilutions"); page.wait_for_timeout(300)
    check("naar de zopas gekozen kleur", page.locator("#catCol").input_value() == "#3366cc")
    page.click("#dlgCancel"); page.wait_for_timeout(400)
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    terug = page.evaluate("""() => (DATA.categoryColours||{})["Predilutions"]""")
    check(f"Ctrl+Z neemt de kleur terug ({terug!r})", terug in (None, ""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)      # en de testformule
    check("en daarna de formule zelf",
          page.evaluate("""() => !DATA.formulas.some(x => x.name === "Kleurtest A")"""))

    # dezelfde kiezer op de materiaalpagina en in + New material
    page.evaluate("""() => switchTab("M", DATA.materials[0].id, null)"""); page.wait_for_timeout(600)
    check("de materiaalpagina heeft + New category met een kleurkiezer",
          page.locator("#btnNewMatCat").count() == 1 and page.locator("#matCatCol").count() == 1)
    cat = page.evaluate("""() => DATA.materials[0].category""")
    page.evaluate("""() => { const c = document.querySelector("#matCatCol");
        c.value = "#cc3366"; c.dispatchEvent(new Event("change")); }""")
    page.wait_for_timeout(600)
    check(f"de kleur van de materiaalcategorie wordt bewaard ({cat!r})",
          page.evaluate("(n) => (DATA.categoryColours||{})[n]", cat) == "#cc3366")
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    page.click("#tabM"); page.wait_for_timeout(300)
    page.click("#btnNewMat"); page.wait_for_timeout(500)
    check("+ New material heeft ze ook",
          page.locator("#btnNewNmCat").count() == 1 and page.locator("#nmCatCol").count() == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(400)

    # ---------- 9. B15 (bouw 260920d): het venster "Name version" zet de importverwijzing één keer bij ----------
    # Het venster dient om een label te zetten; elke Apply schreef opnieuw een alinea in een veld van de gebruiker.
    page.evaluate("""() => { const m = DATA.materials[0];
        DATA.formulas.push({id:"f-src", name:"Bron", category:"Uncategorised", created:today(), frozenImport:true,
          versions:[{v:1, date:today(), imported:true, frozen:true, sourceName:"Bron v03", notes:"eigen waarneming",
                     lines:[{id:"s1", materialId:m.id, dilutionPct:100, weightG:9, remark:1}]}]});
        buildUsage(); switchTab("F", "f-src", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    for ronde in range(3):
        page.click("#btnNameV"); page.wait_for_timeout(400)
        if ronde == 0:
            page.evaluate("""() => { const c = document.querySelector("#vnSrc"); if (c) c.checked = false; }""")
        page.click("#dlgOk"); page.wait_for_timeout(500)
    r = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-src").versions[0];
        return {keer: ((v.notes||"").match(/Imported as/g) || []).length, notes: v.notes, hide: !!v.hideSource}; }""")
    check(f"drie keer Apply geeft één keer “Imported as …” ({r['keer']})", r["keer"] == 1 and r["hide"] is True)
    check("en de eigen notitie staat er nog voor", r["notes"].startswith("eigen waarneming"))
    # opnieuw aanvinken en weer uitvinken voegt ze evenmin een tweede keer toe
    page.click("#btnNameV"); page.wait_for_timeout(400)
    page.evaluate("""() => { const c = document.querySelector("#vnSrc"); if (c) c.checked = true; }""")
    page.click("#dlgOk"); page.wait_for_timeout(500)
    check("aanvinken toont de verwijzing weer in de kop",
          page.evaluate("""() => !DATA.formulas.find(x => x.id === "f-src").versions[0].hideSource"""))
    page.click("#btnNameV"); page.wait_for_timeout(400)
    page.evaluate("""() => { const c = document.querySelector("#vnSrc"); if (c) c.checked = false; }""")
    page.click("#dlgOk"); page.wait_for_timeout(500)
    r = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-src").versions[0];
        return ((v.notes||"").match(/Imported as/g) || []).length; }""")
    check(f"en weer uitvinken ook niet ({r})", r == 1)

    # ---------- 10. B4 (bouw 260920e): de bestellijst en Delivered vouwen zoals de rest ----------
    # "Vertofix coeur" naast "Vertofix cœur" gaf een tweede, leeg materiaal dat daarna élke opzoeking op de naam
    # van het eerste kaapte: het stond vooraan in de lijst en matByName neemt de eerste.
    page.evaluate("""() => { DATA.orderList = [];
        DATA.materials = DATA.materials.filter(x => !/vertofix/i.test(x.name));
        DATA.materials.push({id:"m-vert", name:"Vertofix cœur", category:"Woody", pyramid:4, ifraLimit:99,
          isSolvent:false, cas:"", aliases:"", dilutions:[{pct:100, isBase:true, date:today(), notes:""}]});
        DATA.materials.sort((a,b)=>a.name.localeCompare(b.name)); invalidateMats(); switchTab("T"); }""")
    page.wait_for_timeout(500)
    page.fill("#ordName", "Vertofix coeur"); page.click("#btnOrdAdd"); page.wait_for_timeout(600)
    r = page.evaluate("""() => { const o = DATA.orderList[0];
        return {id: o.materialId, echte: matById(o.materialId)?.name,
                badge: !!document.querySelector("table.lines.ord tbody .badge")}; }""")
    check(f"een ligatuur op de bestellijst is het materiaal dat je al hebt ({r})",
          r["echte"] == "Vertofix cœur" and not r["badge"])
    page.evaluate("""() => { const o = DATA.orderList[0]; o.amount = 50; o.unit = "g"; o.price = "25"; render(); }""")
    page.wait_for_timeout(400)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(500)
    hint = page.evaluate("""() => document.querySelector("#dlg .hint")?.textContent.trim()""")
    check(f"en het venster noemt het materiaal dat het bijwerkt ({hint!r})",
          "Updates" in (hint or "") and "Vertofix cœur" in (hint or ""))
    page.click("#dlgOk"); page.wait_for_timeout(800)
    r = page.evaluate("""() => { const alle = DATA.materials.filter(x => /vertofix/i.test(x.name));
        const g = matByName("Vertofix cœur");
        return {aantal: alle.length, treffer: g && g.name, ifra: g && g.ifraLimit}; }""")
    check(f"Delivered werkt het bij in plaats van een dubbel te maken ({r})",
          r["aantal"] == 1 and r["treffer"] == "Vertofix cœur" and r["ifra"] == 99)

    # ---------- 11. B22 (bouw 260920e): een gedeelde alias beslist niet meer alleen ----------
    # Materialen van dezelfde plant of isomeren met een eigen profiel delen nu eenmaal een naam; de app moet
    # het vragen in plaats van de eerste uit de lijst te nemen.
    page.evaluate("""() => { const maak = (naam, alias) => ({id:"m-"+naam.replace(/\\W/g,""), name:naam,
            category:"Flowers", pyramid:2, isSolvent:false, aliases: alias,
            dilutions:[{pct:100, isBase:true, date:today(), notes:""}]});
        DATA.materials.push(maak("Ylang A", "cananga odorata"), maak("Ylang B", "cananga odorata"),
                            maak("Ylang C", "cananga odorata; ylang eigen"));
        DATA.materials.sort((a,b)=>a.name.localeCompare(b.name)); invalidateMats(); render(); }""")
    page.wait_for_timeout(500)
    r = page.evaluate("""() => ({alle: matsByName("cananga odorata").map(x => x.name),
        eigenNaam: matsByName("Ylang A").map(x => x.name),
        uniekeAlias: matsByName("ylang eigen").map(x => x.name)})""")
    check(f"matsByName geeft alle dragers van een gedeelde alias ({r['alle']})", r["alle"] == ["Ylang A", "Ylang B", "Ylang C"])
    check(f"een eigen naam blijft één materiaal ({r['eigenNaam']})", r["eigenNaam"] == ["Ylang A"])
    check(f"en een alias die maar één materiaal draagt ook ({r['uniekeAlias']})", r["uniekeAlias"] == ["Ylang C"])
    page.evaluate("""() => { if (!DATA.formulas.some(x => x.id === "f-amb"))
            DATA.formulas.push({id:"f-amb", name:"Ambigutest", category:"Uncategorised", created:today(),
              frozenImport:false, versions:[{v:1, date:today(), lines:[]}]});
        buildUsage(); switchTab("F", "f-amb", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    voor = page.evaluate("""() => DATA.formulas.find(x => x.id === "f-amb").versions[0].lines.length""")
    page.fill("#addMat", "cananga odorata"); page.click("#btnAddLine"); page.wait_for_timeout(600)
    opties = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return s ? [...s.options].map(o => o.textContent.split(" · ")[0]) : null; }""")
    check(f"Add line vraagt welk materiaal je bedoelt ({opties})", opties == ["Ylang A", "Ylang B", "Ylang C"])
    page.select_option("#pkMat", "1"); page.click("#dlgOk"); page.wait_for_timeout(700)
    r = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-amb").versions[0];
        return {n: v.lines.length, mat: matById(v.lines[v.lines.length-1].materialId)?.name}; }""")
    check(f"en neemt de gekozen ({r})", r["n"] == voor + 1 and r["mat"] == "Ylang B")
    # ⇄ Replace vraagt het in hetzelfde venster, want een tweede venster annuleert de vervanging
    page.click("[data-repl='0']"); page.wait_for_timeout(500)
    page.fill("#rmNew", "cananga odorata"); page.click("#dlgOk"); page.wait_for_timeout(500)
    opties = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return s ? [...s.options].map(o => o.textContent.split(" · ")[0]) : null; }""")
    check(f"⇄ Replace vraagt het in hetzelfde venster ({opties})", opties == ["Ylang A", "Ylang B", "Ylang C"])
    page.select_option("#pkMat", "2"); page.click("#dlgOk"); page.wait_for_timeout(800)
    check("en vervangt door de gekozene",
          page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-amb").versions[0];
              return matById(v.lines[0].materialId)?.name; }""") == "Ylang C")
    # Delivered vraagt het vóór het venster opengaat: daar kan je de naam niet zelf hertypen
    page.evaluate("""() => { DATA.orderList = [{id:"o-amb", materialId:null, name:"cananga odorata",
        amount:10, unit:"g", price:"20", added:today()}]; switchTab("T"); }""")
    page.wait_for_timeout(500)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(500)
    opties = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return s ? [...s.options].map(o => o.textContent.split(" · ")[0]) : null; }""")
    check(f"Delivered vraagt het ook ({opties})", opties == ["Ylang A", "Ylang B", "Ylang C"])
    page.select_option("#pkMat", "0"); page.click("#dlgOk"); page.wait_for_timeout(600)
    hint = page.evaluate("""() => document.querySelector("#dlg .hint")?.textContent.trim()""")
    check(f"en werkt daarna dat materiaal bij ({hint!r})", "Ylang A" in (hint or ""))
    page.click("#dlgOk"); page.wait_for_timeout(700)
    r = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Ylang A");
        return {n: DATA.materials.filter(x => /ylang|cananga/i.test(x.name)).length, prijs: m.costPerGram}; }""")
    check(f"zonder een vierde materiaal te maken ({r})", r["n"] == 3 and r["prijs"] > 0)

    # de invoervoorvertoning vraagt niets, maar zegt wel wat er speelt
    page.evaluate("""() => { IMPORTP = {name:"Ylangproef", category:"Uncategorised", source:"", lines:[
        {material:"cananga odorata", dilutionPct:100, weightG:5},
        {material:"ylang eigen", dilutionPct:100, weightG:5}]}; render(); }""")
    page.wait_for_timeout(700)
    rijen = page.evaluate("""() => [...document.querySelectorAll("#content table.lines tbody tr")]
        .map(tr => [...tr.cells].map(c => c.textContent.trim()).join(" | "))""")
    check(f"de voorvertoning noemt de naam uit het bestand ({rijen[0][:60]!r})", "← cananga odorata" in rijen[0])
    check("en alle materialen die die naam dragen",
          "shared name: Ylang A, Ylang B, Ylang C" in rijen[0])
    check(f"een alias van één materiaal krijgt die melding niet ({rijen[1][:50]!r})", "shared name" not in rijen[1])
    page.evaluate("""() => { IMPORTP = null; render(); }"""); page.wait_for_timeout(400)
    # het aliasveld zegt het meteen
    msgs.clear()
    page.evaluate("""() => switchTab("M", DATA.materials.find(x => x.name === "Ylang A").id, null)""")
    page.wait_for_timeout(600)
    page.fill("[data-f='aliases']", "cananga odorata; iets eigens")
    page.locator("[data-f='aliases']").press("Tab"); page.wait_for_timeout(600)
    check(f"het aliasveld noemt de materialen die de naam al dragen ({[m[:60] for m in msgs]})",
          any("Ylang B" in m and "Ylang C" in m and "already answer" in m for m in msgs))

    # ---------- 11b. één zoekfunctie voor de lijst en voor de naamvelden (bouw 260920f) ----------
    # De zoeklijst filtert (een treffer te veel kost niets), een naamveld identificeert (er belandt een gewicht op).
    # Alles wat de lijst vindt is nu ook via het veld bereikbaar, maar als keuze, nooit als stille greep.
    page.evaluate("""() => { DATA.materials = DATA.materials.filter(x => !/^Ylang [ABC]$/.test(x.name));
        const maak = (naam, extra) => Object.assign({id:"m-"+naam.replace(/\\W/g,""), name:naam, category:"Flowers",
            pyramid:2, isSolvent:false, cas:"", aliases:"", supplier:"", description:"",
            dilutions:[{pct:100, isBase:true, date:today(), notes:""}]}, extra);
        DATA.materials.push(maak("Ylang cas", {cas:"8006-81-3; cananga odorata"}),
                            maak("Ylang beschrijving", {description:"floral\\nBotanical: cananga odorata"}),
                            maak("Ylang alias", {aliases:"ylang unieke alias"}));
        DATA.materials.sort((a,b)=>a.name.localeCompare(b.name)); invalidateMats(); }""")
    page.wait_for_timeout(400)
    r = page.evaluate("""() => matSearch("cananga odorata").map(h => h.m.name + "/" + h.via)""")
    check(f"matSearch vindt een naam naast het CAS-nummer en in de beschrijving ({r})",
          "Ylang cas/cas" in r and "Ylang beschrijving/description" in r)
    check("de suggestielijst draagt de alternatieve namen",
          page.evaluate("""() => matListHtml().includes('value="ylang unieke alias"')"""))
    lab = page.evaluate("""() => { const a = DATA.materials.find(x => x.name === "Ylang cas"),
            b2 = DATA.materials.find(x => x.name === "Ylang beschrijving");
        a.aliases = "gedeelde plantnaam"; b2.aliases = "gedeelde plantnaam"; invalidateMats();
        const m = /value="gedeelde plantnaam" label="([^"]*)"/.exec(matListHtml());
        a.aliases = ""; b2.aliases = ""; invalidateMats();
        return m && m[1]; }""")
    check(f"en noemt bij een gedeelde naam de materialen die hem dragen ({lab!r})",
          lab and "Ylang beschrijving" in lab and "Ylang cas" in lab)
    page.evaluate("""() => { if (!DATA.formulas.some(x => x.id === "f-amb"))
            DATA.formulas.push({id:"f-amb", name:"Ambigutest", category:"Uncategorised", created:today(),
              frozenImport:false, versions:[{v:1, date:today(), lines:[]}]});
        buildUsage(); switchTab("F", "f-amb", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    voor = page.evaluate("""() => DATA.formulas.find(x => x.id === "f-amb").versions[0].lines.length""")
    msgs.clear()
    page.fill("#addMat", "cananga odorata"); page.click("#btnAddLine"); page.wait_for_timeout(700)
    r = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return {opties: s ? [...s.options].map(o => o.textContent) : null,
                tekst: document.querySelector("#dlg .hint")?.textContent.trim(),
                geen: !!document.querySelector("#pkNone")}; }""")
    check(f"Add line biedt de bredere treffers aan in plaats van meteen een materiaal te maken ({r['opties']})",
          r["opties"] and len(r["opties"]) == 2 and not msgs)
    check("met de reden erbij", any("CAS number" in o for o in (r["opties"] or []))
          and any("description" in o for o in (r["opties"] or [])))
    check(f"en een uitweg om het toch aan te maken ({r['geen']})", r["geen"] is True)
    page.select_option("#pkMat", "0"); page.click("#dlgOk"); page.wait_for_timeout(700)
    r = page.evaluate("""() => { const v = DATA.formulas.find(x => x.id === "f-amb").versions[0];
        return {n: v.lines.length, mat: matById(v.lines[v.lines.length-1].materialId)?.name,
                nieuw: DATA.materials.some(x => normName(x.name) === "cananga odorata")}; }""")
    check(f"de gekozene komt in de formule, zonder een nieuw materiaal ({r})",
          r["n"] == voor + 1 and r["mat"] == "Ylang beschrijving" and r["nieuw"] is False)
    msgs.clear()
    page.fill("#addMat", "cananga odorata"); page.click("#btnAddLine"); page.wait_for_timeout(600)
    page.click("#pkNone"); page.wait_for_timeout(800)
    check(f"None of these stelt alsnog de gewone vraag ({[m[:45] for m in msgs]})",
          any("is not in your inventory" in m for m in msgs))
    check("en maakt het materiaal aan", page.evaluate("""() => DATA.materials.some(x => normName(x.name) === "cananga odorata")"""))
    page.evaluate("""() => { DATA.materials = DATA.materials.filter(x => normName(x.name) !== "cananga odorata");
        DATA.orderList = []; invalidateMats(); buildUsage();
        switchTab("F", "f-amb", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    # ⇄ Replace en de bestellijst vragen het ook, in plaats van "Unknown material"
    page.click("[data-repl='0']"); page.wait_for_timeout(500)
    page.fill("#rmNew", "cananga odorata"); page.click("#dlgOk"); page.wait_for_timeout(600)
    opties = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return s ? [...s.options].map(o => o.textContent.split(" · ")[0]) : null; }""")
    check(f"⇄ Replace zegt niet meer alleen 'Unknown material' ({opties})",
          opties and set(opties) == {"Ylang cas", "Ylang beschrijving"})
    page.evaluate("""() => document.querySelector("#dlgCancel")?.click()"""); page.wait_for_timeout(400)
    page.evaluate("""() => { DATA.orderList = []; switchTab("T"); }"""); page.wait_for_timeout(500)
    page.fill("#ordName", "cananga odorata"); page.click("#btnOrdAdd"); page.wait_for_timeout(700)
    opties = page.evaluate("""() => { const s = document.querySelector("#pkMat");
        return s ? [...s.options].map(o => o.textContent.split(" · ")[0]) : null; }""")
    check(f"de bestellijst ook, vóór je iets bestelt dat je al hebt ({opties})",
          opties and set(opties) == {"Ylang cas", "Ylang beschrijving"})
    page.select_option("#pkMat", "0"); page.click("#dlgOk"); page.wait_for_timeout(700)
    check("en de regel hangt aan dat materiaal",
          page.evaluate("""() => { const o = DATA.orderList[0]; return o && !!o.materialId && matById(o.materialId).name; }""") in ("Ylang beschrijving", "Ylang cas"))

    # ---------- 12. staart 17 (bouw 260920e): formulenamen vouwen zoals Rename ----------
    msgs.clear()
    page.evaluate("""() => { DATA.formulas.push({id:"f-rose", name:"Rose", category:"Uncategorised", created:today(),
        versions:[{v:1, date:today(), lines:[]}]}); buildUsage(); switchTab("F", "f-rose", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    page.click("#btnCopyF"); page.wait_for_timeout(400)
    page.fill("#cpName", "Rosé"); page.click("#dlgOk"); page.wait_for_timeout(600)
    check(f"Copy to new formula weigert “Rosé” naast “Rose” ({[m[:40] for m in msgs]})",
          any("already exists" in m for m in msgs) and
          page.evaluate("""() => DATA.formulas.filter(x => /^Ros/.test(x.name)).length""") == 1)
    page.evaluate("""() => document.querySelector("#dlgCancel")?.click()"""); page.wait_for_timeout(400)

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
