"""Materialen invoeren uit een CSV (bouw 260916, bibliotheekknop 260916b, Import/Export-venster 260916d): de rondgang met de eigen CSV-uitvoer, een vreemd
blad met ; en decimale komma en andere kopnamen, een Windows-1252-bestand, dubbels, het sjabloon en undo.
Vereist de lokale webserver op poort 8765, zie README."""
import csv, io, json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def mat(page, name):
    return page.evaluate("""n => { const m = DATA.materials.find(x => x.name === n);
        return m && {cas: m.cas, al: m.aliases, cat: m.category, sup: m.supplier, cost: m.costPerGram, ifra: m.ifraLimit,
                     pyr: m.pyramid, sol: !!m.isSolvent, loc: m.locations, dens: m.density,
                     dil: (m.dilutions||[]).map(d => d.pct), base: (m.dilutions||[]).find(d => d.isBase)?.pct, desc: m.description}; }""", name)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    tmp = tempfile.mkdtemp()

    # ---------------- 1. de rondgang: uitvoeren, elders invoeren ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)
    # een materiaal met alles erop en eraan, met de basis niet als eerste dilutie
    page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Hedione");
        m.cas = "24851-98-7"; m.aliases = "methyl dihydrojasmonate; MDJ"; m.supplier = "Proefleverancier"; m.inventory = "250 g";
        m.purchaseDate = "2026-02-03"; m.costPerGram = 0.085; m.ifraLimit = 99; m.pyramid = 2; m.isSolvent = false;
        m.locations = {kast: true, frigo: true, diepvries: false}; m.density = 0.99;
        m.dilutions = [{pct: 10, isBase: false, date: "2026-01-01", notes: ""}, {pct: 100, isBase: true, date: "2026-01-01", notes: ""}];
        m.description = "clean jasmine\\nwatery, radiant"; markDirty(); }""")
    page.wait_for_timeout(300)
    voor = mat(page, "Hedione")
    n_mats = page.evaluate("DATA.materials.length")
    page.click("#btnHome"); page.wait_for_timeout(500)
    check("de Welcome-pagina heeft de knop", page.locator("#btnImpCsv").is_visible())
    check("en de link naar het sjabloon", page.locator("#btnCsvTpl").is_visible())
    check("Welcome verwijst naar Import/Export", page.locator("#homeIO").is_visible())
    page.click("#homeIO"); page.wait_for_timeout(400)   # de uitvoer zit in het venster
    with page.expect_download() as dl:
        page.click("#btnExpM")
    pad = os.path.join(tmp, "uitvoer.csv"); dl.value.save_as(pad)
    kop = open(pad, encoding="utf-8-sig").readline()
    sep = ";" if kop.count(";") > kop.count(",") else ","      # de uitvoer volgt de taal van de browser
    rij = [r for r in csv.reader(open(pad, encoding="utf-8-sig"), delimiter=sep) if r and r[0] == "Hedione"][0]
    check(f"Dilutions % zet de basis eerst ({rij[16]!r}, scheidingsteken {sep!r})", rij[16].startswith("100"))
    ctx.close()

    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs2 = []; msgs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnEmpty"); page.wait_for_timeout(1400)
    page.set_input_files("#impCsv", pad); page.wait_for_timeout(900)
    check("het koppelvenster staat open", page.locator("#csvMap").is_visible())
    sel = page.evaluate("() => [...document.querySelectorAll('#csvMap select')].map(s => s.value !== '')")
    check(f"de eigen kolommen zijn allemaal vooraf gekoppeld ({sum(sel)} van {len(sel)})", all(sel))
    check("de teller kondigt de invoer aan", f"{n_mats} material(s)" in page.text_content("#csvCount"))
    check("de knop telt mee", page.text_content("#dlgOk").strip() == f"Import {n_mats}")
    msgs2.clear(); page.click("#dlgOk"); page.wait_for_timeout(1200)
    check(f"alle materialen zijn binnen ({page.evaluate('DATA.materials.length')} van {n_mats})", page.evaluate("DATA.materials.length") == n_mats)
    check("de melding zegt hoeveel", any(f"{n_mats} material(s) imported" in m for m in msgs2))
    check("de app staat op Materials", page.evaluate("VIEW.tab") == "M")
    na = mat(page, "Hedione")
    check(f"CAS, aliassen, categorie, leverancier komen terug ({na['cas']}, {na['al']}, {na['cat']}, {na['sup']})",
          na["cas"] == voor["cas"] and na["al"] == voor["al"] and na["cat"] == voor["cat"] and na["sup"] == voor["sup"])
    check(f"kost, IFRA, dichtheid als getal ({na['cost']}, {na['ifra']}, {na['dens']})",
          na["cost"] == voor["cost"] and na["ifra"] == voor["ifra"] and na["dens"] == voor["dens"])
    check(f"piramide en solventvlag ({na['pyr']}, {na['sol']})", na["pyr"] == 2 and na["sol"] is False)
    check(f"de bewaarplaatsen ({na['loc']})", na["loc"] == {"kast": True, "frigo": True, "diepvries": False})
    check(f"de diluties met de basis ({na['dil']}, basis {na['base']})", sorted(na["dil"]) == [10, 100] and na["base"] == 100)
    check(f"de beschrijving ({na['desc']!r})", "clean jasmine" in (na["desc"] or ""))
    sol = page.evaluate("DATA.materials.filter(m => m.isSolvent).length")
    check(f"de solventen van de starterset zijn solvent gebleven ({sol})", sol > 0)

    # nog eens hetzelfde bestand: alles overgeslagen
    page.set_input_files("#impCsv", pad); page.wait_for_timeout(900)
    check("een tweede keer: alles wordt overgeslagen", f"{n_mats} skipped" in page.text_content("#csvCount"))
    check("en de knop staat uit", page.locator("#dlgOk").is_disabled())
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # één undo neemt de hele invoer terug
    page.keyboard.press("Control+z"); page.wait_for_timeout(800)
    check("één undo neemt alles terug", page.evaluate("DATA.materials.length") == 0)

    # ---------------- 2. een vreemd blad: ; en decimale komma, andere kopnamen, dubbels ----------------
    vreemd = os.path.join(tmp, "kast.csv")
    open(vreemd, "w", encoding="utf-8", newline="") .write(
        "Material;CAS No.;Vendor;Price;IFRA;Note;Dilution;Notes\r\n"
        "Iso E Super;54464-57-2;Perfumers Apprentice;0,12;99;Base;10%;woody, velvety\r\n"
        "Ethanol;64-17-5;;0,01;;;100;\r\n"
        "iso e super;54464-57-2;;;;;;dubbel in het blad\r\n"
        ";;;;;;;een rij zonder naam\r\n"
        "Hedione;24851-98-7;;0,085;99;Heart;100 / 10;\"jasmine; \"\"radiant\"\"\"\r\n")
    page.set_input_files("#impCsv", vreemd); page.wait_for_timeout(900)
    v = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#csvMap select')].map(s => [s.dataset.k, s.value]))")
    check(f"de synoniemen koppelen vanzelf (name={v['name']}, cas={v['cas']}, supplier={v['supplier']}, cost={v['costPerGram']}, ifra={v['ifraLimit']}, dil={v['dilutions']}, desc={v['description']})",
          v["name"] == "0" and v["cas"] == "1" and v["supplier"] == "2" and v["costPerGram"] == "3" and v["ifraLimit"] == "4"
          and v["dilutions"] == "6" and v["description"] == "7")
    check("een onbekende kop (Note) blijft ongekoppeld", v["pyramid"] == "")
    page.select_option("#csv_pyramid", "5"); page.wait_for_timeout(300)   # de gebruiker koppelt ze zelf
    check("de teller: drie erbij, één dubbel, één zonder naam",
          "3 material(s)" in page.text_content("#csvCount") and "1 skipped" in page.text_content("#csvCount") and "1 row(s) without a name" in page.text_content("#csvCount"))
    msgs2.clear(); page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("drie materialen aangemaakt", page.evaluate("DATA.materials.length") == 3)
    iso = mat(page, "Iso E Super")
    check(f"decimale komma gelezen ({iso['cost']})", iso["cost"] == 0.12)
    check(f"10% wordt dilutie 10 als basis ({iso['dil']}, basis {iso['base']})", iso["dil"] == [10] and iso["base"] == 10)
    check(f"Base wordt piramide 4 ({iso['pyr']})", iso["pyr"] == 4)
    check(f"de leverancier ({iso['sup']})", iso["sup"] == "Perfumers Apprentice")
    hed = mat(page, "Hedione")
    check(f"een aanhalingsteken in een veld overleeft ({hed['desc']!r})", hed["desc"] == 'jasmine; "radiant"')
    check(f"Heart wordt 2 en 100 / 10 geeft twee diluties ({hed['pyr']}, {hed['dil']})", hed["pyr"] == 2 and hed["dil"] == [100, 10])
    check("zonder solventkolom is niets solvent", page.evaluate("DATA.materials.filter(m => m.isSolvent).length") == 0)
    check("de melding noemt de overgeslagen rij", any("1 row(s) skipped" in m for m in msgs2))

    # ---------------- 3. Windows-1252, zoals Excel het schrijft ----------------
    w = os.path.join(tmp, "excel.csv")
    open(w, "wb").write("Name;Category\r\nPatchouli cœur;Woody\r\nCrème brulée base;Gourmand\r\n".encode("cp1252"))
    page.set_input_files("#impCsv", w); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(800)
    namen = page.evaluate("DATA.materials.map(m => m.name)")
    check(f"Windows-1252 wordt goed gelezen ({[n for n in namen if 'c' in n.lower() and 'ur' in n.lower()]})",
          "Patchouli cœur" in namen and "Crème brulée base" in namen)
    check("een nieuwe categorie is aangemaakt", page.evaluate("DATA.materialCategories.includes('Gourmand')"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("undo neemt ook de categorie terug", not page.evaluate("DATA.materialCategories.includes('Gourmand')") and page.evaluate("DATA.materials.length") == 3)

    # ---------------- 4. het sjabloon ----------------
    with page.expect_download() as dl:
        page.click("#btnHome"); page.wait_for_timeout(500); page.click("#btnCsvTpl")
    tpl = os.path.join(tmp, "sjabloon.csv"); dl.value.save_as(tpl)
    check(f"het sjabloon heet miformulas-materials-template.csv ({dl.value.suggested_filename})", dl.value.suggested_filename == "miformulas-materials-template.csv")
    kop2 = open(tpl, encoding="utf-8-sig").readline()
    regels = list(csv.reader(open(tpl, encoding="utf-8-sig"), delimiter=";" if kop2.count(";") > kop2.count(",") else ","))
    check(f"het sjabloon heeft de kopregel en twee voorbeeldrijen ({len(regels)})", len(regels) == 3 and regels[0][0] == "Name" and regels[1][0].startswith("Example"))
    check("de kop is die van de uitvoer", regels[0][:4] == ["Name", "CAS", "Alternative names", "Category"])
    page.set_input_files("#impCsv", tpl); page.wait_for_timeout(900)
    check("het sjabloon zelf koppelt volledig", page.evaluate("() => [...document.querySelectorAll('#csvMap select')].every(s => s.value !== '')"))
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---------------- 5. een bestand dat geen CSV is ----------------
    slecht = os.path.join(tmp, "leeg.csv"); open(slecht, "w").write("\n\n")
    msgs2.clear(); page.set_input_files("#impCsv", slecht); page.wait_for_timeout(600)
    check(f"een leeg bestand geeft een melding, geen venster ({msgs2})", any("header row" in m for m in msgs2) and not page.locator("#csvMap").is_visible())

    # ---------------- 6. de bibliotheek vanuit het venster (bouw 260916b) ----------------
    # de gepubliceerde bibliotheek komt van een lokale kopie: de test mag het net niet op
    ctx3 = b.new_context(viewport={"width": 1400, "height": 900})
    page = ctx3.new_page(); errs3 = []; msgs3 = []
    page.on("pageerror", lambda e: errs3.append(str(e)))
    page.on("dialog", lambda d: (msgs3.append(d.message), d.accept()))
    lib = os.path.join(tmp, "bibliotheek.json")
    open(lib, "w", encoding="utf-8").write(json.dumps({"type": "miformulas-materials", "name": "Testbibliotheek", "version": "2026-09-16",
        "materials": [{"name": "Iso E Super", "cas": "54464-57-2", "category": "Woody", "pyramid": 4},
                      {"name": "Hedione", "cas": "24851-98-7", "category": "Floral", "pyramid": 2, "aliases": ["Methyl dihydrojasmonate"]}]}))
    page.route("https://data.miformulas.com/miformulas-materials.json", lambda r: r.fulfill(path=lib, content_type="application/json"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnEmpty"); page.wait_for_timeout(1400)
    check("het Welcome-blok heeft de nieuwe knopnaam", page.text_content("#btnImpCsv").strip() == "Import materials inventory from CSV…")
    check("en houdt alleen de twee wegen naar binnen", page.evaluate(
        "() => [...document.querySelectorAll('#content .panelBox:last-of-type button, #content .panelBox:last-of-type a.btn')].map(b => b.id)")
        == ["btnImpFormulair", "btnImpCsv"])
    page.click("#btnIO"); page.wait_for_timeout(400)
    volgorde = page.evaluate("() => [...document.querySelectorAll('#dlg button, #dlg a.btn')].map(b => b.id).filter(id => !id.startsWith('dlg'))")
    check(f"het venster heeft de knoppen in de afgesproken volgorde ({volgorde})",
          volgorde[:9] == ["ioFormulair", "ioCsv", "btnImpL", "btnImpF", "btnExpL", "btnExpJ", "btnExpF", "btnExpM", "ioRestore"]
          and volgorde[9:] in ([], ["ioSnap"]))   # sinds 260922k de twee wegen terug onderaan, de dagsnapshot alleen als er een is
    check("Cancel is verborgen, want een menu heeft niets te annuleren",
          page.evaluate("() => getComputedStyle(document.querySelector('#dlgCancel')).display") == "none")
    blok = page.text_content("#dlg")
    check("de hint van Export all my formulas… somt op wat niet meegaat", "No price, supplier, stock or trial log goes along" in blok)
    check("en die van Import formula… noemt ook de uitvoer van een andere miFormulas", "all the formulas exported from another miFormulas" in blok)
    check("die van de bibliotheek zegt dat de eigen materialen onaangeroerd blijven", "does not change the materials already in your inventory" in blok)
    check("de prompts zijn een link naar de juiste prompt",
          page.locator('#dlg a[href$="ai-prompts.html#s1-photo-pdf-or-spreadsheet-to-import-file"]').count() == 1
          and page.locator('#dlg a[href$="ai-prompts.html#s2-checking-and-completing-your-materials"]').count() == 1)
    page.click("#dlgOk"); page.wait_for_timeout(300)
    zonder = os.path.join(tmp, "namen.csv")
    open(zonder, "w", encoding="utf-8", newline="").write("Name\r\nIso E Super\r\nHedione\r\nMethyl dihydrojasmonate\r\nNieuwe stof\r\n")
    page.set_input_files("#impCsv", zonder); page.wait_for_timeout(900)
    check("het venster heet naar de knop", "Import materials inventory from CSV" in page.text_content("#dlg h3"))
    check("zonder bibliotheek zegt het venster dat", "No materials library loaded" in page.text_content("#csvLib"))
    check("en biedt Get the latest library aan", page.locator("#csvLibGet").is_visible())
    check("de teller zwijgt dan over de bibliotheek", "knows" not in page.text_content("#csvCount") and "4 material(s)" in page.text_content("#csvCount"))
    page.click("#csvLibGet"); page.wait_for_timeout(1500)
    check("het venster blijft open", page.locator("#csvMap").is_visible())
    check(f"de bibliotheek is geladen ({page.evaluate('DATA.materialList && DATA.materialList.name')})", page.evaluate("DATA.materialList && DATA.materialList.name") == "Testbibliotheek")
    check("de regel noemt ze nu", "Testbibliotheek 2026-09-16" in page.text_content("#csvLib") and page.locator("#csvLibGet").count() == 0)
    # sinds bouw 260920m telt het plan de aliassen mee die de invoer zelf meegeeft: de rij "Methyl dihydrojasmonate"
    # landt straks op de Hedione die deze invoer aanmaakt, dus ze wordt niet meer als nieuw materiaal beloofd
    tel = page.text_content("#csvCount")
    check(f"de teller belooft er drie, want de aliasrij landt op de stof die hier gemaakt wordt ({tel})",
          "3 material(s) will be created" in tel)
    check(f"en zegt hoeveel namen de bibliotheek kent ({tel})", "knows 2 of them" in tel)
    check("de Welcome-pagina achter het venster is bijgewerkt", "Import & export" in page.text_content("#content .panelBox:last-of-type"))
    msgs3.clear(); page.click("#dlgOk"); page.wait_for_timeout(1000)
    iso = mat(page, "Iso E Super"); hed = mat(page, "Hedione"); mdj = mat(page, "Methyl dihydrojasmonate")
    check(f"de bibliotheek vult aan wat het blad niet had ({iso['cas']}, {iso['cat']}, {iso['pyr']})", iso["cas"] == "54464-57-2" and iso["cat"] == "Woody" and iso["pyr"] == 4)
    check(f"de alias uit de bibliotheek komt bij de stof, en de rij met die alias is dezelfde stof en wordt overgeslagen ({hed['al']}, {msgs3})",
          mdj is None and "Methyl dihydrojasmonate" in (hed["al"] or "") and any("1 row(s) skipped" in m for m in msgs3))
    check("een naam die ze niet kent komt kaal binnen", mat(page, "Nieuwe stof")["cas"] in (None, ""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check("undo neemt de invoer terug", page.evaluate("DATA.materials.length") == 0)
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    check("en een tweede undo de bibliotheek", page.evaluate("DATA.materialList") is None)
    # als het ophalen mislukt, blijft het venster open en de knop bruikbaar
    page.unroute("https://data.miformulas.com/miformulas-materials.json")
    page.route("https://data.miformulas.com/miformulas-materials.json", lambda r: r.fulfill(status=503, body="down"))
    msgs3.clear(); page.set_input_files("#impCsv", zonder); page.wait_for_timeout(900)
    page.click("#csvLibGet"); page.wait_for_timeout(1200)
    check(f"mislukt ophalen geeft een melding ({msgs3})", any("could not be fetched" in m for m in msgs3))
    check("het venster staat nog open en de knop is weer bruikbaar", page.locator("#csvMap").is_visible() and not page.locator("#csvLibGet").is_disabled())
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    # ---------------- 7. bouw 260918b: aliassen, negatieve getallen, de BOM en een verkeerd blad ----------------
    page.evaluate("""(t) => { DATA.materials = []; DATA.orderList = [];
        setMaterialList(JSON.parse(t)); markDirty(); render(); }""", open(lib, encoding="utf-8").read())
    page.wait_for_timeout(400)
    # de bibliotheek kent "Hedione" met de alias "Methyl dihydrojasmonate"; het blad brengt een eigen alias mee
    alias = os.path.join(tmp, "alias.csv")
    open(alias, "w", encoding="utf-8", newline="").write(
        "Name,Alternative names,Cost EUR/g,Density g/ml\r\n"
        "Methyl dihydrojasmonate,MDJ,0.085,0.99\r\n"
        "Iso E Super,,-2,-1,5\r\n")
    msgs3.clear(); page.set_input_files("#impCsv", alias); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    al = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Methyl dihydrojasmonate");
        return m ? (m.aliases || "") : null; }""")
    check(f"de alias uit het blad komt erbij zonder die uit de bibliotheek te wissen ({al})",
          al is not None and "MDJ" in al and "Hedione" in al)
    neg = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Iso E Super");
        return m ? {cost: m.costPerGram, dens: m.density} : null; }""")
    check(f"een negatieve prijs en dichtheid komen er niet in ({neg})",
          neg is not None and neg["cost"] in (None, "") and neg["dens"] in (None, ""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # een lege maar gekoppelde kolom Solvent mag de vlag uit de bibliotheek niet wissen (bouw 260918c)
    page.evaluate("""(t) => { DATA.materials = []; DATA.orderList = [];
        const lib = JSON.parse(t);
        lib.materials.push({name: "Proefsolvent", cas: "64-17-5", category: "Solvents", isSolvent: true});
        setMaterialList(normLibrary(lib)); markDirty(); render(); }""", open(lib, encoding="utf-8").read())
    page.wait_for_timeout(400)
    solv = os.path.join(tmp, "solvent.csv")
    open(solv, "w", encoding="utf-8", newline="").write("Name,Solvent\r\nProefsolvent,\r\n")
    page.set_input_files("#impCsv", solv); page.wait_for_timeout(900)
    check("de kolom Solvent koppelt vanzelf", page.evaluate("() => document.querySelector('#csv_isSolvent').value") == "1")
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("een lege cel laat de solventvlag uit de bibliotheek staan",
          page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Proefsolvent"); return m && !!m.isSolvent; }"""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    open(solv, "w", encoding="utf-8", newline="").write("Name,Solvent\r\nProefsolvent,no\r\n")
    page.set_input_files("#impCsv", solv); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("maar een ingevulde cel beslist wel",
          page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Proefsolvent"); return m && !m.isSolvent; }"""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # een UTF-8 BOM op een bestand dat verderop geen geldige UTF-8 is: de terugval mocht de BOM niet laten staan
    mojibake = os.path.join(tmp, "mojibake.csv")
    open(mojibake, "wb").write(b"\xef\xbb\xbfName,Supplier\r\nCistus\xe9,Robertet\x92s\r\n")
    page.set_input_files("#impCsv", mojibake); page.wait_for_timeout(900)
    kolom = page.evaluate("() => document.querySelector('#csv_name').value")
    kop = page.evaluate("() => [...document.querySelectorAll('#dlg table.lines thead th')].map(t => t.textContent)")
    check(f"de eerste kolom heet Name en koppelt vanzelf, zonder BOM ervoor ({kop})",
          kolom == "0" and kop and kop[0] == "Name")
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # een blad met formules hoort in het andere venster
    fblad = os.path.join(tmp, "formules.csv")
    open(fblad, "w", encoding="utf-8", newline="").write(
        "Formula,Entry,Material,Dilution %,Weight g\r\nAura,v1,Hedione,100,10\r\n")
    msgs3.clear(); page.set_input_files("#impCsv", fblad); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(600)
    check(f"een formulesblad wordt geweigerd met de weg erbij ({[m[:40] for m in msgs3]})",
          any("sheet of formulas" in m and "Import formula" in m for m in msgs3))
    check("en het venster blijft open", page.locator("#csvMap").is_visible())
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # lege uitvoer: zeggen dat er niets is, in plaats van een leeg bestand te schrijven
    page.evaluate("""() => { DATA.materials = []; DATA.formulas = []; markDirty(); render(); }""")
    page.wait_for_timeout(400)
    page.click("#btnIO"); page.wait_for_timeout(400)
    msgs3.clear(); page.click("#btnExpM"); page.wait_for_timeout(600)
    check(f"een lege inventaris levert geen leeg bestand ({[m[:40] for m in msgs3]})",
          any("no materials in your inventory" in m for m in msgs3))
    page.click("#btnIO"); page.wait_for_timeout(400)          # het venster sluit bij elke uitvoerknop
    msgs3.clear(); page.click("#btnExpF"); page.wait_for_timeout(600)
    check(f"en een lege formulelijst evenmin ({[m[:40] for m in msgs3]})",
          any("no formulas to export" in m for m in msgs3))

    # ---------------- staart 28 en 34 (bouw 260920m) ----------------
    # 28: "100 / 100 / 10" maakte twee keer dezelfde dilutie, wat de app overal elders weigert
    # 34: het plan kende de aliassen niet die de invoer zelf meegeeft, en beloofde meer dan er kwam
    page.evaluate("""() => { setMaterialList({type:"miformulas-materials", name:"Aliaslijst", version:"1",
        materials:[{name:"Ambroxide", aliases:["Ambroxan"], cas:"6790-58-5", category:"Test", pyramid:4}]});
        render(); }""")
    page.wait_for_timeout(400)
    dub = os.path.join(tmp, "dubbele-dilutie.csv")
    open(dub, "w", encoding="utf-8", newline="").write(
        "Name;Category;Dilutions\nDubbeldil;Test;100 / 100 / 10\nAmbroxide;Test;100\nAmbroxan;Test;100\n")
    msgs3.clear()
    page.set_input_files("#impCsv", dub); page.wait_for_timeout(900)
    telling = page.text_content("#csvCount")
    check(f"het plan belooft twee materialen, niet drie: de alias telt mee ({telling.strip()[:60]!r})",
          "2 material(s) will be created" in telling)
    page.click("#dlgOk"); page.wait_for_timeout(1200)
    dd = mat(page, "Dubbeldil")
    check(f"dezelfde dilutie komt maar één keer binnen ({dd['dil']}, basis {dd['base']})",
          sorted(dd["dil"]) == [10, 100] and dd["base"] == 100)
    check(f"er kwamen er twee, zoals beloofd ({page.evaluate('DATA.materials.length')})",
          page.evaluate("""() => DATA.materials.filter(m => /Dubbeldil|Ambroxide|Ambroxan/.test(m.name)).length""") == 2)
    check(f"en de melding zegt waarom de derde rij wegviel ({[m[:110] for m in msgs3][-1:]})",
          any("earlier row in this sheet" in m for m in msgs3))

    check(f"geen paginafouten in deel 6 ({errs3[:2]})", not errs3)

    # ---------------- 7. bouw 260922h: de aankoopdatum in de korte vorm van een spreadsheet ----------------
    # "3/02/2025" werd bewaard zoals het er stond, en het datumveld op de materiaalpagina toonde niets.
    page.evaluate("LOCALE = 'nl-BE'")
    dat = os.path.join(tmp, "aankoopdatums.csv")
    open(dat, "w", encoding="utf-8", newline="").write(
        "Name;Purchase date\nDatum Kort;3/02/2025\nDatum Iso;2025-02-04\nDatum Fout;31/02/2025\nDatum Leeg;\n")
    msgs3.clear()
    page.set_input_files("#impCsv", dat); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(1200)
    pd = page.evaluate("""() => ["Datum Kort", "Datum Iso", "Datum Fout", "Datum Leeg"].map(n => { const m = DATA.materials.find(x => x.name === n); return m ? (m.purchaseDate || "") : null; })""")
    check(f"23: 3/02/2025 wordt 2025-02-03, een onmogelijke datum blijft leeg ({pd})", pd == ["2025-02-03", "2025-02-04", "", ""])
    check(f"23: de slotmelding telt de datum die niet te lezen was ({[m[-120:] for m in msgs3][-1:]})",
          any("1 purchase date(s) could not be read" in m for m in msgs3))
    page.evaluate("""() => switchTab("M", DATA.materials.find(x => x.name === "Datum Kort").id, null)""")
    page.wait_for_timeout(500)
    veld = page.evaluate("""() => { const e = [...document.querySelectorAll('#content input[type=date]')][0]; return e ? e.value : null; }""")
    check(f"23: en het datumveld toont ze ({veld})", veld == "2025-02-03")
    page.evaluate("LOCALE = undefined")
    check(f"geen paginafouten in deel 7 ({errs3[:2]})", not errs3)

    check(f"geen paginafouten ({errs2[:2]})", not errs2)
    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
