"""The materials library: import one, see it in Settings, look it up in + New material, remove it.
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
        "licence": "CC BY 4.0", "count": 5, "materials": [
    {"name": "Testolide", "aliases": ["omega-testolactone", "Proefmusk"], "cas": "106-02-5",
     "category": "Test musks", "pyramid": 4, "ifraLimit": 99, "odour": ["musky", "animalic", "powdery"],
     "strength": "high", "tenacity": "more than 2 weeks",
     "use": {"mean": "1.5", "low": "0.76", "high": "3.2", "n": "83"}},
    {"name": "Dipropylene glycol", "cas": "25265-71-8", "category": "Solvents", "isSolvent": True},
    {"name": "Proefstof A", "category": "Test musks", "pyramid": 2},
    {"name": "Proefstof B", "category": "Test musks", "pyramid": 2},
    {"name": "Proefstof C", "category": "Test musks", "pyramid": 2}]}

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
    page.click("#btnIO"); page.wait_for_timeout(400)
    check("Import/Export offers Import materials library…", page.locator("#btnImpL").is_visible())
    page.click("#dlgOk"); page.wait_for_timeout(300)
    msgs.clear()
    page.set_input_files("#impList", f); page.wait_for_timeout(600)
    check(f"import reports name, version and count ({msgs})", any("Materials library loaded: Test material list 2026-09-13, 5 materials" in m for m in msgs))
    check("the message says nothing was added to your inventory", any("Nothing was added to your own inventory" in m for m in msgs))
    check("your own materials are untouched", page.evaluate("DATA.materials.length") == 199)
    check("the list sits in the data", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 5)
    page.click("#btnIO"); page.wait_for_timeout(400)
    check("Import/Export names the loaded list", "Test material list" in page.text_content("#dlg"))
    check("and says the materials you already have stay untouched", "the materials already in your inventory are untouched" in page.text_content("#dlg"))
    page.click("#dlgOk"); page.wait_for_timeout(300)

    # Settings shows it with Remove
    page.click("#btnSettings"); page.wait_for_timeout(400)
    dlg = page.text_content("#dlg")
    check("Settings names the list, its size and licence", "Test material list" in dlg and "5 materials" in dlg and "CC BY 4.0" in dlg)
    check("Settings offers Import and Remove", page.locator("#setListImp").is_visible() and page.locator("#setListDel").is_visible())
    check("Settings offers Get the latest list", page.locator("#setListGet").is_visible())
    check("Settings says the library is a reference", "the materials you own are not part of it" in dlg)
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
    check("datalist holds the names and the alternative names",   # 5 names + 2 aliases of Testolide
          page.locator("#nmList option").count() == 7)
    page.fill("#nmName", "Proefmusk"); page.wait_for_timeout(200)      # an alternative name finds it too
    found = page.text_content("#nmFound")
    check(f"an alias finds the material ({found!r})", "Testolide" in found and "106-02-5" in found and "Base" in found)
    check("the facts are shown", "musky, animalic, powdery" in found and "Impact: high" in found
          and "Substantivity: more than 2 weeks" in found and "Typical use: 1.5 %" in found)
    check("the facts stand on their own lines in the preview",
          "musky, animalic, powdery<br>Impact: high<br>Substantivity: more than 2 weeks<br>Typical use:" in page.inner_html("#nmFound"))
    check("the category of the list is preselected", page.locator("#nmCat").input_value() == "Test musks")
    page.click("#dlgOk"); page.wait_for_timeout(600)
    m = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Proefmusk");
      return m && {cas: m.cas, pyr: m.pyramid, ifra: m.ifraLimit, cat: m.category, al: m.aliases, d: m.description, sol: m.isSolvent}; }""")
    check(f"the material carries the facts ({m})", m and m["cas"] == "106-02-5" and m["pyr"] == 4 and m["ifra"] == 99 and m["cat"] == "Test musks")
    check(f"the library name is kept as an alternative name, its own name is not ({m and m['al']})",
          m and m["al"] == "Testolide; omega-testolactone")
    check("odour, impact, substantivity and use are each on their own line",
          m and m["d"].split("\n") == ["musky, animalic, powdery", "Impact: high",
                                       "Substantivity: more than 2 weeks",
                                       "Typical use: 1.5 % (usual range: 0.76 % to 3.2 %), 83 formulas"])
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

    # the search in Materials knows the list
    page.click("#tabM"); page.wait_for_timeout(300)   # since 260915g Undo returns to where the change started
    page.fill("#searchBox", "Hedione"); page.wait_for_timeout(400)
    check("no library block when the library knows nothing extra about it",
          "materials library:" not in page.text_content("#list"))
    page.fill("#searchBox", "Testolide"); page.wait_for_timeout(400)
    lst = page.text_content("#list")
    check(f"the search offers the entry of the list", "Not in your inventory" in lst and "Testolide" in lst)
    page.click("#list button[data-add]"); page.wait_for_timeout(600)
    added = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Testolide");
      return m && {cas: m.cas, d: m.description, pct: m.dilutions[0].pct, al: m.aliases}; }""")
    check(f"+ Add creates the material with its facts ({added})",
          added and added["cas"] == "106-02-5" and added["pct"] == 100 and "Impact: high" in added["d"]
          and added["al"] == "omega-testolactone; Proefmusk")
    check("the material page opened", page.locator("#content h2").first.inner_text().startswith("Testolide"))
    check("the list block is gone now that you have it", "Not in your inventory" not in page.text_content("#list"))
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # from 260914l the library also shows what it knows beside your own hits
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.fill("#nmName", "Proefstof Z"); page.click("#dlgOk"); page.wait_for_timeout(600)
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Proefstof"); page.wait_for_timeout(400)
    lst = page.text_content("#list")
    check("your own hit is listed", "Proefstof Z" in lst)
    check(f"and the library offers the ones you do not have",
          "Also in the materials library:" in lst and "Not in your inventory" not in lst)
    check("with a + Add for one of them", page.locator('#list button[data-add="Proefstof B"]').count() == 1)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)
    page.evaluate("() => { undo(); }"); page.wait_for_timeout(500)   # Proefstof Z weer weg
    check("Proefstof Z is weer weg", not page.evaluate("DATA.materials.some(m => m.name === 'Proefstof Z')"))

    # Browse the list…: several at once, one Undo step
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.click("#nmBrowse"); page.wait_for_timeout(400)
    check("the browse window lists the whole list", page.locator("#brRows .brRow").count() == 5)
    check("a material you already have cannot be ticked",
          page.locator('#brRows input[data-n="Testolide"]').is_disabled() and "in your inventory" in page.text_content("#brRows"))
    page.click('#brRows input[data-n="Proefstof A"]'); page.wait_for_timeout(150)
    page.click('#brRows input[data-n="Proefstof C"]', modifiers=["Shift"]); page.wait_for_timeout(300)
    check(f"shift-click ticks the range ({page.text_content('#brCount')!r})",
          "3 materials ticked" in page.text_content("#brCount")
          and page.locator('#brRows input[data-n="Proefstof B"]').is_checked()
          and not page.locator('#brRows input[data-n="Dipropylene glycol"]').is_checked())
    check("the button counts along", page.text_content("#dlgOk").strip() == "Add 3")
    page.click('#brRows input[data-n="Proefstof B"]', modifiers=["Shift"]); page.wait_for_timeout(300)
    check(f"shift-click unticks a range just as well ({page.text_content('#brCount')!r})",
          "1 material ticked" in page.text_content("#brCount")
          and page.locator('#brRows input[data-n="Proefstof A"]').is_checked()
          and not page.locator('#brRows input[data-n="Proefstof C"]').is_checked())
    page.click('#brRows input[data-n="Proefstof C"]', modifiers=["Shift"]); page.wait_for_timeout(300)
    page.fill("#brQ", "dipro"); page.wait_for_timeout(300)
    check("the filter narrows the window", page.locator("#brRows .brRow").count() == 1)
    page.check('#brRows input[data-n="Dipropylene glycol"]'); page.wait_for_timeout(200)
    check(f"ticks survive the filter ({page.text_content('#brCount')!r})", "4 materials ticked" in page.text_content("#brCount"))
    check("the button says how many", page.text_content("#dlgOk").strip() == "Add 4")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(800)
    dpg = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Dipropylene glycol");
      return m && {sol: m.isSolvent, cat: m.category, pct: m.dilutions[0].pct}; }""")
    check(f"the ticked material was added ({dpg})", dpg and dpg["sol"] and dpg["cat"] == "Solvents" and dpg["pct"] == 100)
    check(f"the message says how many ({msgs})", any("4 materials added to your inventory" in m for m in msgs))
    check("all four arrived", page.evaluate("['Dipropylene glycol','Proefstof A','Proefstof B','Proefstof C'].every(n => DATA.materials.some(x => x.name === n))"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("one undo takes all four back", page.evaluate("!['Dipropylene glycol','Proefstof A','Proefstof B','Proefstof C'].some(n => DATA.materials.some(x => x.name === n))"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    check("undo also takes the + Add material back", page.evaluate("!DATA.materials.some(x => x.name === 'Testolide')"))

    # ---- a library that is not tidy: doubles, an alias two entries share, values out of range (260915d) ----
    ROMMEL = {"type": "miformulas-materials", "name": "Rommelige lijst", "version": "x", "materials": [
        {"name": "Dubbel", "cas": "1-1-1", "category": "Test musks"},
        {"name": "dubbel", "cas": "9-9-9", "category": "Test musks"},          # dezelfde naam, andere feiten
        {"name": "Alpha", "aliases": ["gedeelde plantnaam"], "category": "Test musks"},
        {"name": "Beta", "aliases": ["gedeelde plantnaam"], "category": "Test musks"},
        {"name": "Scheef", "category": "Test musks", "pyramid": 7, "ifraLimit": -3,
         "isSolvent": "no", "description": {"x": 1}},
        {"name": "Halve", "category": "Test musks", "pyramid": 2.5},
        {"name": "Rosa damascena", "aliases": ["rosa damascena"], "category": "Test musks"},
        {"name": "", "category": "Test musks"}]}
    r = os.path.join(tempfile.mkdtemp(), "rommel.json")
    open(r, "w", encoding="utf-8").write(json.dumps(ROMMEL))
    page.click("#btnHome"); page.wait_for_timeout(300)
    msgs.clear(); page.set_input_files("#impList", r); page.wait_for_timeout(700)
    namen = page.evaluate("() => DATA.materialList.materials.map(m => m.name)")
    check(f"a doubled name is kept once ({namen})", namen.count("Dubbel") == 1 and "dubbel" not in namen)
    check("an entry without a name is dropped", "" not in namen and len(namen) == 6)
    scheef = page.evaluate("() => DATA.materialList.materials.find(m => m.name === 'Scheef')")
    halve = page.evaluate("() => DATA.materialList.materials.find(m => m.name === 'Halve')")
    check(f"a pyramid level outside 0 to 4 is no level ({scheef.get('pyramid')}, {halve.get('pyramid')})",
          "pyramid" not in scheef and "pyramid" not in halve)
    check("a negative IFRA value is not a limit", "ifraLimit" not in scheef)
    check('"no" is not a solvent', not scheef.get("isSolvent"))
    check("a description that is not text is left out", "description" not in scheef)
    check("and no empty field is stored on an entry",
          all(k in ("name", "cas", "category") for k in page.evaluate("() => Object.keys(DATA.materialList.materials[0])")))
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    opties = page.evaluate("() => [...document.querySelectorAll('#nmList option')].map(o => o.value)")
    check(f"the datalist holds one of two names that differ only in case ({opties})",
          len([o for o in opties if o.lower() == "rosa damascena"]) == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.click("#tabM"); page.wait_for_timeout(200)
    page.fill("#searchBox", "lpha"); page.wait_for_timeout(400)
    check("the library offers Alpha", page.locator('#list button[data-add="Alpha"]').count() == 1)
    page.click('#list button[data-add="Alpha"]'); page.wait_for_timeout(600)
    page.fill("#searchBox", "eta"); page.wait_for_timeout(400)
    check("an entry that merely shares an alternative name with Alpha stays on offer",
          page.locator('#list button[data-add="Beta"]').count() == 1)
    page.fill("#searchBox", ""); page.wait_for_timeout(200)
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.click("#nmBrowse"); page.wait_for_timeout(400)
    check("Alpha is greyed out in Browse, Beta is not",
          page.locator('#brRows input[data-n="Alpha"]').is_disabled()
          and not page.locator('#brRows input[data-n="Beta"]').is_disabled())
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)   # Alpha weer weg
    page.click("#btnHome"); page.wait_for_timeout(300)
    msgs.clear(); page.set_input_files("#impList", f); page.wait_for_timeout(700)   # de nette lijst terug
    check("the tidy list is back", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 5)

    # remove the list again
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.click("#setListDel"); page.wait_for_timeout(500)
    check("the list is gone", page.evaluate("DATA.materialList") is None)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("undo brings the list back", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 5)

    # it survives a save and a fresh visit (browser storage)
    page.click("#btnSave"); page.wait_for_timeout(600)
    pg2 = ctx.new_page(); pg2.on("dialog", lambda d: d.accept())
    # een tweede venster naast dit leest sinds 260922g alleen, en dat volstaat om te zien wat er bewaard is
    pg2.goto(URL); pg2.wait_for_function("() => typeof DATA !== 'undefined' && DATA && DATA.formulas", timeout=10000)
    check("the list is still there in a new visit", pg2.evaluate("DATA.materialList && DATA.materialList.materials.length") == 5)
    pg2.close()
    # ---------- bouw 260918c: accenten en de ligatuur œ staan een zoekopdracht niet meer in de weg ----------
    page.evaluate("""() => { setMaterialList(normLibrary({type: "miformulas-materials", name: "Accenten", version: "1",
        materials: [{name: "Vetiver Ha\u00efti", cas: "8016-96-4", category: "Woody", pyramid: 4},
                    {name: "Patchouli c\u0153ur", cas: "8014-09-3", category: "Woody", pyramid: 4}]}));
        DATA.materials = []; DATA.orderList = []; invalidateMats(); markDirty();
        switchTab("M", null, null); }""")
    page.wait_for_timeout(600)
    page.fill("#searchBox", "haiti"); page.wait_for_timeout(500)
    check("de bibliotheek biedt Vetiver Ha\u00efti aan als je haiti typt",
          page.locator('#list button[data-add="Vetiver Ha\u00efti"]').count() == 1)
    page.fill("#searchBox", "coeur"); page.wait_for_timeout(500)
    check("en Patchouli c\u0153ur als je coeur typt",
          page.locator('#list button[data-add="Patchouli c\u0153ur"]').count() == 1)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)
    check("listFind vindt ze ook zonder de accenten",
          page.evaluate("""() => { const a = listFind("Vetiver Haiti"), b = listFind("patchouli coeur");
              return [a && a.cas, b && b.cas]; }""") == ["8016-96-4", "8014-09-3"])
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.fill("#nmName", "Vetiver Haiti"); page.wait_for_timeout(400)
    check("+ New material toont de feiten uit de bibliotheek bij de naam zonder accent",
          "8016-96-4" in page.text_content("#nmFound"))
    page.click("#dlgOk"); page.wait_for_timeout(700)
    nieuw = page.evaluate("""() => { const m = DATA.materials.find(x => /vetiver/i.test(x.name));
        return m && {naam: m.name, cas: m.cas, pyr: m.pyramid}; }""")
    check(f"en het materiaal komt niet kaal binnen ({nieuw})",
          nieuw and nieuw["cas"] == "8016-96-4" and nieuw["pyr"] == 4)
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    zoek = page.evaluate("""() => { DATA.materials = [{id:"m-h", name:"Vetiver Ha\u00efti", category:"Woody",
            pyramid:4, isSolvent:false, dilutions:[{pct:100, isBase:true}]}];
        invalidateMats(); markDirty(); switchTab("M", null, null); return true; }""")
    page.wait_for_timeout(500)
    page.fill("#searchBox", "haiti"); page.wait_for_timeout(500)
    check("en de zijbalk vindt je eigen materiaal met accent op dezelfde manier",
          page.locator("#list .item").count() == 1)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # ---------- staart 32 (bouw 260920m): een bibliotheek woont in je databestand ----------
    # elke wijziging herschrijft dat bestand in zijn geheel, dus de maat telt en er is een plafond
    msgs.clear()
    page.set_input_files("#impList", f); page.wait_for_timeout(800)
    check(f"de melding noemt de maat van de bibliotheek ({[m[:70] for m in msgs][:1]})",
          any(("kB" in m or "MB" in m) and "library loaded" in m for m in msgs))
    groot = {"type": "miformulas-materials", "name": "Te grote lijst", "version": "2026-09-21",
             "materials": [{"name": "Vulstof %04d" % i, "category": "Test", "pyramid": 2,
                            "description": "x" * 900} for i in range(2600)]}
    pad_groot = os.path.join(tempfile.mkdtemp(), "groot.json")
    open(pad_groot, "w", encoding="utf-8").write(json.dumps(groot))
    voor = page.evaluate("""() => DATA.materialList && DATA.materialList.name""")
    msgs.clear()
    page.set_input_files("#impList", pad_groot); page.wait_for_timeout(1500)
    check(f"een bibliotheek boven 2 MB wordt geweigerd, met de reden ({[m[:80] for m in msgs][:1]})",
          any("limit is 2" in m and "data file" in m for m in msgs))
    check(f"en de geladen bibliotheek blijft wat ze was ({voor!r})",
          page.evaluate("""() => DATA.materialList && DATA.materialList.name""") == voor)

    # bouw 260922h (C-c 25): een bibliotheek leest het pyramid-niveau ook in woorden, zoals de CSV van materialen.
    # Een library die een assistent schrijft, gebruikt woorden; "Base" viel stil weg.
    woorden = {"type": "miformulas-materials", "name": "Woorden", "version": "1", "materials": [
        {"name": "Woord Base", "pyramid": "Base"}, {"name": "Woord Topheart", "pyramid": "Top-heart"},
        {"name": "Woord Spatie", "pyramid": "top / heart"}, {"name": "Woord Getal", "pyramid": 2},
        {"name": "Woord Tekstgetal", "pyramid": "3"}, {"name": "Woord Onzin", "pyramid": "Middle"}, {"name": "Woord Zeven", "pyramid": 7}]}
    pad_w = os.path.join(tempfile.mkdtemp(), "woorden.json")
    open(pad_w, "w", encoding="utf-8").write(json.dumps(woorden))
    page.set_input_files("#impList", pad_w); page.wait_for_timeout(800)
    lv = page.evaluate("""() => ["Base", "Topheart", "Spatie", "Getal", "Tekstgetal", "Onzin", "Zeven"].map(n => {
        const e = (DATA.materialList && DATA.materialList.materials || []).find(x => x.name === "Woord " + n); return e ? (e.pyramid ?? null) : "weg"; })""")
    check(f"25: Base, Top-heart en top / heart worden 4, 1 en 1; een woord dat niets zegt en 7 vallen weg ({lv})",
          lv == [4, 1, 1, 2, 3, None, None])

    check("no page errors", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
