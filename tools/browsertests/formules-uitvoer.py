"""Alle formules uitvoeren naar één bestand en ze elders weer invoeren (bouw 260915n).
De rondgang zit erin: uitvoeren, het JSON nalezen op wat er wel en niet in staat, en invoeren in een tweede
browser die de formules niet heeft. Vereist de lokale webserver op poort 8765, zie README."""
import datetime, json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

today = datetime.date.today().isoformat()

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ---------------- de afzender ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    # een tweede versie en een prijs, een leverancier en een trial log, die niet mee mogen
    page.click("#list .item >> nth=0"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    page.evaluate("""() => { const m = DATA.materials[0];
        m.costPerG = "12.5"; m.supplier = "Testleverancier"; m.inventory = "250 g";
        const f = DATA.formulas[0]; f.versions[0].trials = [{date: "2026-01-01", text: "geheim"}];
        f.versions[0].notes = "proefnotitie voor de uitvoer";   // de starterset heeft er geen
        f.versions[f.versions.length - 1].name = "proeflabel";
        markDirty(); }""")
    page.wait_for_timeout(300)
    verwacht = page.evaluate("""() => ({f: DATA.formulas.length,
        v: DATA.formulas.reduce((s,f) => s + f.versions.length, 0),
        l: DATA.formulas.reduce((s,f) => s + f.versions.reduce((t,v) => t + v.lines.length, 0), 0)})""")

    page.click("#btnHome"); page.wait_for_timeout(500)
    page.click("#btnIO"); page.wait_for_timeout(400)
    check("het Import/Export-venster heeft de knop", page.locator("#btnExpJ").is_visible())
    msgs.clear()
    with page.expect_download() as dl:
        page.click("#btnExpJ")
    pad = os.path.join(tempfile.mkdtemp(), "formules.json")
    dl.value.save_as(pad); page.wait_for_timeout(500)
    check(f"de bestandsnaam eindigt op miFormulas formulas.json ({dl.value.suggested_filename})",
          dl.value.suggested_filename.endswith("miFormulas formulas.json"))
    check(f"de melding telt formules, versies en regels ({msgs})",
          any(f"{verwacht['f']} formulas with {verwacht['v']} versions" in m for m in msgs))
    check("en zegt dat er niets van het labo meegaat", any("no price, supplier, stock or trial log" in m for m in msgs))

    pkg = json.load(open(pad, encoding="utf-8"))
    check("het type blijft miformulas-import", pkg.get("type") == "miformulas-import")
    check(f"alle formules staan erin ({len(pkg.get('formulas') or [])} van {verwacht['f']})",
          len(pkg["formulas"]) == verwacht["f"])
    nv = sum(len(f["versions"]) for f in pkg["formulas"])
    nl = sum(len(v["lines"]) for f in pkg["formulas"] for v in f["versions"])
    check(f"met al hun versies ({nv} van {verwacht['v']})", nv == verwacht["v"])
    check(f"en al hun regels ({nl} van {verwacht['l']})", nl == verwacht["l"])
    ruw = json.dumps(pkg)
    check("geen labogegevens in het bestand",
          "costPerG" not in ruw and "supplier" not in ruw and "inventory" not in ruw
          and "trials" not in ruw and "geheim" not in ruw)
    check("geen materialId, want dat wijst bij een ander naar iets anders", "materialId" not in ruw)
    l0 = pkg["formulas"][0]["versions"][0]["lines"][0]
    check(f"een regel draagt naam, dilutie en gewicht ({l0})",
          "material" in l0 and "dilutionPct" in l0 and "weightG" in l0)
    sol = [l for f in pkg["formulas"] for v in f["versions"] for l in v["lines"] if l.get("solvent")]
    check(f"de solventregels dragen hun vlag ({len(sol)})", len(sol) > 0)
    # ---------------- bouw 260918b: een regel naar een gewist materiaal ----------------
    # calc geeft zo'n regel een leeg materiaal, waarna de Excel-uitvoer letterlijk "undefined" schreef
    page.evaluate("""() => { DATA.formulas = []; DATA.materials = []; DATA.orderList = [];
        DATA.materials.push({id: "m-1", name: "Blijver", category: "Test", pyramid: 2, isSolvent: false,
                             dilutions: [{pct: 100, isBase: true}]});
        DATA.materials.push({id: "m-weg", name: "Verdwijner", category: "Test", pyramid: 2, isSolvent: false,
                             dilutions: [{pct: 100, isBase: true}]});
        DATA.formulas.push({id: "f-1", name: "Met een gat", category: "Test", created: today(), versions: [
            {v: 1, date: "2026-05-05", lines: [{materialId: "m-1", dilutionPct: 100, weightG: 10, remark: 1},
                                               {materialId: "m-weg", dilutionPct: 100, weightG: 5, remark: 1}]}]});
        DATA.materials = DATA.materials.filter(m => m.id !== "m-weg");   // het materiaal weg, de regel blijft
        invalidateMats(); buildUsage(); markDirty(); switchTab("F", "f-1", {type: "v", idx: 0}); }""")
    page.wait_for_timeout(700)
    tmp3 = tempfile.mkdtemp()
    msgs.clear()
    with page.expect_download() as dl3:
        page.click("#btnCsv")
    pad3 = os.path.join(tmp3, "versie.csv"); dl3.value.save_as(pad3)
    page.wait_for_timeout(300)
    tekst3 = open(pad3, encoding="utf-8-sig").read()
    check(f"de uitvoer van de versie vraagt eerst ({[m[:40] for m in msgs]})",
          any("no longer exists" in m for m in msgs))
    check("en schrijft geen undefined", "undefined" not in tekst3 and "Blijver" in tekst3)
    page.click("#btnIO"); page.wait_for_timeout(400)
    msgs.clear()
    with page.expect_download() as dl4:
        page.click("#btnExpF")
    pad4 = os.path.join(tmp3, "alles.csv"); dl4.value.save_as(pad4)
    page.wait_for_timeout(300)
    tekst4 = open(pad4, encoding="utf-8-sig").read()
    check(f"Export all formulas (Excel) vraagt hetzelfde ({[m[:40] for m in msgs]})",
          any("no longer exists" in m for m in msgs))
    check("en schrijft geen undefined", "undefined" not in tekst4 and "Blijver" in tekst4)
    rijen4 = [r for r in tekst4.splitlines() if "Met een gat" in r]
    check(f"de verweesde regel staat er niet in, de Total-regel wel ({len(rijen4)} rijen)", len(rijen4) == 2)

    # staart 31 (bouw 260920m): Export all my formulas… vraagt vooraf, net als de drie andere uitvoeren
    page.click("#btnIO"); page.wait_for_timeout(400)
    msgs.clear()
    with page.expect_download() as dl5:
        page.click("#btnExpJ")
    pad5 = os.path.join(tmp3, "alles.json"); dl5.value.save_as(pad5)
    page.wait_for_timeout(300)
    check(f"de grote uitvoer vraagt vóór ze schrijft ({[m[:46] for m in msgs]})",
          any("no longer exists" in m and "anyway" in m for m in msgs))
    check("en de melding achteraf zegt hoeveel er wegbleven",
          any("were left out" in m for m in msgs))
    pak5 = json.load(open(pad5, encoding="utf-8"))
    rg = [len(v["lines"]) for f in pak5["formulas"] for v in f["versions"]]
    check(f"het bestand draagt de goede regel en niet de verweesde ({rg})",
          rg == [1] and all(l.get("material") == "Blijver" for f in pak5["formulas"] for v in f["versions"] for l in v["lines"]))

    # staart 35: een versie zonder datum houdt haar lege datum bij de rondgang
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-1");
        f.versions[0].date = ""; markDirty(); render(); }""")
    page.wait_for_timeout(400)
    page.click("#btnIO"); page.wait_for_timeout(400)
    msgs.clear()
    with page.expect_download() as dl6:
        page.click("#btnExpJ")
    pad6 = os.path.join(tmp3, "zonderdatum.json"); dl6.value.save_as(pad6)
    page.wait_for_timeout(300)
    pak = json.load(open(pad6, encoding="utf-8"))
    leeg = [v for f in pak["formulas"] for v in f["versions"] if v.get("date") == ""]
    check(f"de uitvoer draagt de lege datum ({len(leeg)} versie(s))", len(leeg) >= 1)

    check(f"geen paginafouten bij de afzender ({errs[:2]})", not errs)
    ctx.close()

    # ---------------- de ontvanger ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    errs2 = []; msgs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnEmpty"); page.wait_for_timeout(1400)
    check("de ontvanger begint leeg", page.evaluate("DATA.formulas.length") == 0)

    page.set_input_files("#impFile", pad); page.wait_for_timeout(2000)
    tekst = page.text_content("#content")
    check(f"de voorvertoning noemt het aantal formules", f"{verwacht['f']} formulas" in tekst)
    check("en versies en regels", f"{verwacht['v']} versions" in tekst and f"{verwacht['l']} lines" in tekst)
    check("ze zegt dat de nieuwe materialen niet op de bestellijst komen",
          "not put on the order list" in tekst)
    check("er staat een regel per formule in de tabel",
          page.locator("#content table.lines tbody tr").count() == verwacht["f"])
    check("Confirm staat aan", not page.locator("#btnImpOk").is_disabled())

    msgs2.clear()
    page.click("#btnImpOk"); page.wait_for_timeout(2500)
    na = page.evaluate("""() => ({f: DATA.formulas.length,
        v: DATA.formulas.reduce((s,f) => s + f.versions.length, 0),
        l: DATA.formulas.reduce((s,f) => s + f.versions.reduce((t,v) => t + v.lines.length, 0), 0),
        m: DATA.materials.length, wl: DATA.materials.filter(x => x.wishlist).length,
        orders: (DATA.orderList || []).length})""")
    check(f"alle formules zijn binnen ({na})", na["f"] == verwacht["f"])
    check("met al hun versies", na["v"] == verwacht["v"])
    check("en al hun regels", na["l"] == verwacht["l"])
    check(f"de materialen zijn aangemaakt als “to order” ({na['wl']} van {na['m']})",
          na["m"] > 0 and na["wl"] == na["m"])
    check(f"maar de bestellijst blijft leeg ({na['orders']})", na["orders"] == 0)
    check(f"de melding noemt formules en materialen ({msgs2})",
          any("formula(s) added" in m and "to order" in m for m in msgs2))
    check("de versienummers lopen aaneen",
          page.evaluate("() => DATA.formulas.every(f => f.versions.every((v,i) => v.v === i+1))"))
    check("de notitie van een versie kwam mee",
          page.evaluate("() => DATA.formulas.some(f => f.versions.some(v => (v.notes||'').includes('proefnotitie')))"))
    check("en het label van een versie ook",
          page.evaluate("() => DATA.formulas.some(f => f.versions.some(v => v.name === 'proeflabel'))"))

    # één undo neemt alles terug
    page.keyboard.press("Control+z"); page.wait_for_timeout(2000)
    check("één undo neemt alle formules en materialen terug",
          page.evaluate("DATA.formulas.length") == 0 and page.evaluate("DATA.materials.length") == 0)
    page.keyboard.press("Control+y"); page.wait_for_timeout(2500)
    check("en redo brengt ze weer", page.evaluate("DATA.formulas.length") == verwacht["f"])

    # nog eens invoeren: dezelfde namen komen binnen als "(import)"
    page.set_input_files("#impFile", pad); page.wait_for_timeout(2500)
    tekst = page.text_content("#content")
    check("de voorvertoning waarschuwt voor de namen die je al hebt", "(import)" in tekst and "name you already have" in tekst)
    page.click("#btnImpOk"); page.wait_for_timeout(2500)
    check(f"de tweede invoer verdubbelt het aantal formules", page.evaluate("DATA.formulas.length") == verwacht["f"] * 2)
    check("en die dragen (import) achter hun naam",
          page.evaluate("() => DATA.formulas.filter(f => / \\(import\\)$/.test(f.name)).length") == verwacht["f"])
    check("zonder nieuwe materialen, want die had hij nu al",
          page.evaluate("DATA.materials.length") == na["m"])
    page.keyboard.press("Control+z"); page.wait_for_timeout(2000)

    # een onleesbare regel blokkeert Confirm
    stuk = json.loads(json.dumps(pkg))
    stuk["formulas"][0]["versions"][0]["lines"][0]["weightG"] = "veel"
    stuk["formulas"][0]["versions"][0]["lines"][1]["dilutionPct"] = 250
    pad2 = os.path.join(tempfile.mkdtemp(), "stuk.json")
    open(pad2, "w", encoding="utf-8").write(json.dumps(stuk))
    page.set_input_files("#impFile", pad2); page.wait_for_timeout(2500)
    check("een onleesbare regel blokkeert Confirm", page.locator("#btnImpOk").is_disabled())
    check("en de voorvertoning zegt in hoeveel formules ze zitten",
          "cannot be imported" in page.text_content("#content"))
    page.click("#btnImpCancel"); page.wait_for_timeout(600)
    # staart 35: en bij de ontvanger blijft ze leeg in plaats van vandaag te worden
    page.set_input_files("#impFile", pad6); page.wait_for_timeout(2000)
    page.click("#btnImpOk"); page.wait_for_timeout(1500)
    datums = page.evaluate("""() => { const f = DATA.formulas.find(x => /Met een gat/.test(x.name));
      return f ? f.versions.map(v => v.date) : null; }""")
    check(f"een versie zonder datum krijgt niet stilletjes die van vandaag ({datums})",
          datums == [""] )

    check(f"geen paginafouten bij de ontvanger ({errs2[:2]})", not errs2)

    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
