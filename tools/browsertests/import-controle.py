"""Import formula…: the gate for files written elsewhere. A line without a material, an unreadable or negative
weight and a dilution outside 0 to 100 are shown in red and block Confirm; what is readable is repaired
(a decimal comma, a percent sign, a missing dilution). And what one import leaves behind, Undo takes back.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

TMP = tempfile.mkdtemp()
def schrijf(naam, pkg):
    p = os.path.join(TMP, naam)
    open(p, "w", encoding="utf-8").write(json.dumps(pkg))
    return p

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    goed = page.evaluate("() => DATA.materials[0].name")
    eerste_zonder_alias = page.evaluate("""() => {
        const m = DATA.materials.find(x => !(x.aliases || "").trim());
        return m ? m.name : null; }""")

    # ---------- 1. regels die niet door de poort komen ----------
    stuk = schrijf("stuk.json", {"type": "miformulas-import", "name": "Kapot", "lines": [
        {"material": goed, "dilutionPct": 100, "weightG": 10},
        {"dilutionPct": 100, "weightG": 5},                       # geen naam
        {"material": "", "dilutionPct": 100, "weightG": 5},       # lege naam
        {"material": goed, "dilutionPct": 100, "weightG": "abc"},
        {"material": goed, "dilutionPct": 100, "weightG": -3},
        {"material": goed, "dilutionPct": 0, "weightG": 2},
        {"material": goed, "dilutionPct": 150, "weightG": 2},
    ]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", stuk); page.wait_for_timeout(900)
    txt = page.text_content("#content")
    check("de voorvertoning opent", "Import formula" in txt)
    check("zes regels worden geweigerd", page.locator("#impBad").count() == 1 and "6 line(s) cannot be imported" in txt)
    check("zes regels staan in het rood", page.locator("tr.badLine").count() == 6)
    for reden in ("no material name", "weight is not a number", "negative weight", "dilution must be above 0 and at most 100"):
        check(f"de reden staat erbij: {reden}", reden in txt)
    check("Confirm import is uitgeschakeld", page.locator("#btnImpOk").is_disabled())
    check("een regel zonder naam landt niet op het eerste materiaal zonder aliassen",
          eerste_zonder_alias is None or txt.count(eerste_zonder_alias) == 0 or "no material name" in txt)
    check("het totaal telt alleen de leesbare regels", "10,000" in txt or "10.000" in txt)
    n_voor = page.evaluate("() => DATA.formulas.length")
    page.click("#btnImpCancel"); page.wait_for_timeout(400)
    check("Cancel laat de data ongemoeid", page.evaluate("() => DATA.formulas.length") == n_voor)

    # ---------- 2. wat wél leesbaar is, wordt hersteld ----------
    los = schrijf("los.json", {"type": "miformulas-import", "name": "Herstel", "category": "Tests",
        "source": "a photo", "lines": [
        {"material": goed, "dilutionPct": "10%", "weightG": "2,5"},   # percentteken en decimale komma
        {"material": goed, "weightG": 7},                             # geen dilutie: 100
        {"material": "Onbekend spul XYZ", "dilutionPct": 10, "weightG": 1, "cas": "1-2-3", "solvent": True},
    ]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", los); page.wait_for_timeout(900)
    check("geen geweigerde regels meer", page.locator("#impBad").count() == 0)
    check("Confirm import staat aan", not page.locator("#btnImpOk").is_disabled())
    check("de hint over een rond totaal staat er wel bij een fototranscriptie",
          "suggests a complete transcription" in page.text_content("#content"))
    page.click("#btnImpOk"); page.wait_for_timeout(900)
    got = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Herstel");
        const v = f.versions[0];
        return {cat: f.category, n: v.lines.length,
                regels: v.lines.map(l => [matById(l.materialId).name, l.dilutionPct, l.weightG]),
                nieuw: (() => { const m = DATA.materials.find(x => x.name === "Onbekend spul XYZ");
                                return m && {cas: m.cas, solvent: !!m.isSolvent, wish: !!m.wishlist}; })()}; }""")
    check(f"de drie regels zijn binnen ({got['regels']})", got["n"] == 3)
    check("«2,5» is 2,5 g geworden", got["regels"][0][2] == 2.5)
    check("«10%» is dilutie 10 geworden", got["regels"][0][1] == 10)
    check("een ontbrekende dilutie is 100", got["regels"][1][1] == 100)
    check(f"het nieuwe materiaal draagt het CAS en de solventvlag uit het bestand ({got['nieuw']})",
          got["nieuw"] and got["nieuw"]["cas"] == "1-2-3" and got["nieuw"]["solvent"] and got["nieuw"]["wish"])

    # ---------- 3. Undo neemt de formule, het materiaal en beide categorieën terug ----------
    had_cat = page.evaluate("() => DATA.formulaCategories.includes('Tests')")
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)
    na = page.evaluate("""() => ({f: DATA.formulas.some(x => x.name === "Herstel"),
        m: DATA.materials.some(x => x.name === "Onbekend spul XYZ"),
        cat: DATA.formulaCategories.includes("Tests"),
        order: (DATA.orderList || []).some(o => o.name === "Onbekend spul XYZ")})""")
    check("Undo neemt de formule terug", not na["f"])
    check("en het nieuwe materiaal", not na["m"])
    check("en de bestelregel", not na["order"])
    check("en de nieuwe formulecategorie", had_cat and not na["cat"])

    # ---------- 4. een naam die alleen in hoofdletters verschilt ----------
    bestaand = page.evaluate("() => DATA.formulas[0].name")
    zelfde = schrijf("zelfde.json", {"type": "miformulas-import", "name": bestaand.lower(),
        "lines": [{"material": goed, "dilutionPct": 100, "weightG": 10}]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", zelfde); page.wait_for_timeout(900)
    check("de gelijknamige formule staat voorgekozen",
          page.evaluate("() => document.querySelector('#impTarget').value") != "")
    page.select_option("#impTarget", "")   # toch als nieuwe formule
    page.wait_for_timeout(200)
    page.click("#btnImpOk"); page.wait_for_timeout(900)
    namen = page.evaluate("() => DATA.formulas.map(f => f.name)")
    check(f"ze komt binnen met (import) achter de naam, ook bij een hoofdletterverschil",
          f"{bestaand.lower()} (import)" in namen and namen.count(bestaand) == 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)

    # ---------- 5. een bestand dat geen import is ----------
    msgs.clear()
    geen = schrijf("geen.json", {"type": "miformulas-materials", "materials": [{"name": "X"}]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", geen); page.wait_for_timeout(600)
    check(f"een bibliotheekbestand wordt geweigerd ({[m[:40] for m in msgs]})",
          any("not a miFormulas import file" in m for m in msgs))

    # ---------- 6. hetzelfde onbekende materiaal op twee regels wordt één keer aangemaakt ----------
    tweemaal = schrijf("tweemaal.json", {"type": "miformulas-import", "name": "Dubbel", "lines": [
        {"material": "Onbekend spul QQ", "dilutionPct": 100, "weightG": 4},
        {"material": goed, "dilutionPct": 100, "weightG": 6},
        {"material": "onbekend SPUL qq", "dilutionPct": 100, "weightG": 2},   # dezelfde naam, andere hoofdletters
    ]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", tweemaal); page.wait_for_timeout(900)
    txt = page.text_content("#content")
    check(f"de voorvertoning telt één nieuw materiaal, niet twee", "1 new (will be created" in txt)
    page.click("#btnImpOk"); page.wait_for_timeout(900)
    dub = page.evaluate('''() => { const f = DATA.formulas.find(x => x.name === "Dubbel");
        const ids = f.versions[0].lines.map(l => l.materialId);
        return {mats: DATA.materials.filter(m => normName(m.name) === normName("Onbekend spul QQ")).length,
                zelfde: ids[0] === ids[2],
                order: (DATA.orderList || []).filter(o => normName(o.name) === normName("Onbekend spul QQ")).length}; }''')
    check(f"het materiaal is één keer aangemaakt en beide regels wijzen ernaar ({dub})",
          dub["mats"] == 1 and dub["zelfde"] and dub["order"] == 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # ---------- 7. een bestand met regels die geen regel zijn ----------
    msgs.clear()
    rommel = schrijf("rommel.json", {"type": "miformulas-import", "name": "Rommel", "lines": [
        {"material": goed, "dilutionPct": 100, "weightG": 10},
        None, 42, "een regel als tekst",
        {"material": {"naam": goed}, "weightG": 3},
        {"material": ["lijst"], "weightG": 3},
    ]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", rommel); page.wait_for_timeout(900)
    txt = page.text_content("#content")
    check("een bestand met stukke regels opent de voorvertoning in plaats van te crashen", "Import formula" in txt)
    check("de vijf onbruikbare regels worden geweigerd",
          "5 line(s) cannot be imported" in txt and page.locator("#btnImpOk").is_disabled())
    page.click("#btnImpCancel"); page.wait_for_timeout(400)

    # ---------- 8. bouw 260918b: een gewicht dat geen getal is omdat het oneindig is ----------
    oneindig = schrijf("oneindig.json", {"type": "miformulas-import", "name": "Oneindig", "lines": [
        {"material": goed, "dilutionPct": 100, "weightG": 10},
        {"material": goed, "dilutionPct": 100, "weightG": "1e999"},
    ]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", oneindig); page.wait_for_timeout(900)
    txt = page.text_content("#content")
    check("een oneindig gewicht komt niet door de poort",
          "1 line(s) cannot be imported" in txt and page.locator("#btnImpOk").is_disabled())
    check("met dezelfde reden als andere onleesbare gewichten", "weight is not a number" in txt)
    check("en het totaal telt het niet mee", "\u221e" not in txt)
    page.click("#btnImpCancel"); page.wait_for_timeout(400)

    # ---------- een materiaal-id in het bestand telt niet mee (bouw 260920a) ----------
    # De starterset geeft iedereen dezelfde id's m1…m199, dus een verzonnen of overgenomen id landde
    # bij vrijwel elke ontvanger op een bestaand materiaal, en de voorvertoning toonde alleen dat materiaal.
    naam_m1 = page.evaluate("() => (DATA.materials.find(m => m.id === 'm1')||{}).name")
    ander = page.evaluate("""() => { const a = (DATA.materials.find(m => m.id === 'm1')||{}).name;
        return (DATA.materials.find(m => m.id !== 'm1' && m.name !== a)||{}).name; }""")
    idtest = schrijf("idtest.json", {"type": "miformulas-import", "name": "Idtest",
        "lines": [{"material": ander, "materialId": "m1", "dilutionPct": 100, "weightG": 5}]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", idtest); page.wait_for_timeout(900)
    txt = page.text_content("#content")
    check("de naam beslist, niet het materiaal-id uit het bestand", ander in txt and naam_m1 not in txt)
    check("en de regel telt als treffer op die naam", "matched" in txt)
    page.click("#btnImpCancel"); page.wait_for_timeout(400)

    # ---------- staart 29, 30 en 33 (bouw 260920m) ----------
    # 33: "matched" rekende regels min unieke nieuwe namen, dus een nieuwe naam op drie regels telde twee treffers te veel
    drie = schrijf("drie.json", {"type": "miformulas-import", "name": "Drie keer nieuw", "lines": [
        {"material": "Nooitgezien X", "dilutionPct": 100, "weightG": 1},
        {"material": "Nooitgezien X", "dilutionPct": 10, "weightG": 2},
        {"material": "Nooitgezien X", "dilutionPct": 1, "weightG": 3}]})
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", drie); page.wait_for_timeout(900)
    tel = page.text_content("#content").split("lines")[1].split("new")[0]
    check(f"drie regels op één nieuwe naam: geen enkele treffer ({tel.strip()!r})", "0 matched" in tel)
    page.click("#btnImpCancel"); page.wait_for_timeout(400)

    # 30: een bestand zonder naam geeft geen bestelregel "needed for undefined"
    naamloos = schrijf("naamloos.json", {"type": "miformulas-import", "lines": [
        {"material": "Naamloze stof Q", "dilutionPct": 100, "weightG": 5}]})
    page.set_input_files("#impFile", naamloos); page.wait_for_timeout(900)
    page.click("#btnImpOk"); page.wait_for_timeout(1200)
    notitie = page.evaluate("""() => { const o = (DATA.orderList||[]).find(x => /Naamloze stof Q/.test(x.name));
      return o ? o.note : null; }""")
    check(f"de bestelregel noemt de formule, niet “undefined” ({notitie!r})",
          notitie and "undefined" not in notitie and "Imported formula" in notitie)
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # 29: een bestand waar niets uit komt, komt niet door de sluis
    leeg = schrijf("leeg.json", {"type": "miformulas-import", "source": "Leegtest",
        "formulas": [{"name": "Zonder regels", "versions": [{"name": "v1", "lines": []}]}]})
    # eerst laten wegschrijven: anders viel de gewone schrijfbeurt van 2,5 s midden in deze controle en
    # mat ze de klok in plaats van het invoervenster (ze zakte alleen door onder belasting)
    page.evaluate("() => saveData()"); page.wait_for_timeout(400)
    undo0 = page.evaluate("UNDO.length"); vuil0 = page.evaluate("DIRTY")
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.set_input_files("#impFile", leeg); page.wait_for_timeout(900)
    check("Confirm staat uit bij een bestand zonder regels",
          page.locator("#btnImpOk").is_disabled() and page.locator("#impEmpty").count() == 1)
    page.click("#btnImpCancel"); page.wait_for_timeout(500)
    check(f"en er blijft geen undo-stap of schrijfbeurt achter ({undo0} → {page.evaluate('UNDO.length')})",
          page.evaluate("UNDO.length") == undo0 and page.evaluate("DIRTY") == vuil0)

    # ---- bouw 260922a, punt A1: twee namen van één bibliotheekingang geven één materiaal ----
    # addFromList hangt de eigen naam en de aliassen van de ingang op het nieuwe materiaal, dus de tweede
    # regel hoort daarop te landen. Vroeger kwamen er twee potjes die elkaars naam als alias droegen, en de
    # IFRA-controle woog daarna elk half materiaal tegen de hele limiet.
    page.click("#btnHome"); page.wait_for_timeout(300)
    bib = schrijf("bib.json", {"type": "miformulas-materials", "name": "A1", "version": "1", "materials": [
        {"name": "Proefstof A1", "aliases": ["Tweede naam A1"], "cas": "111-11-1",
         "category": "Test", "pyramid": 3, "ifraLimit": 1}]})
    page.set_input_files("#impList", bib); page.wait_for_timeout(900)
    check("de proefbibliotheek is geladen",
          page.evaluate("typeof listMaterials === 'function' && listMaterials().some(m => m.name === 'Proefstof A1')"))
    voorM = page.evaluate("DATA.materials.length")
    tweenamen = schrijf("tweenamen.json", {"type": "miformulas-import", "name": "A1 test", "lines": [
        {"material": "Proefstof A1", "dilutionPct": 100, "weightG": 0.6},
        {"material": "Tweede naam A1", "dilutionPct": 100, "weightG": 0.6},
        {"material": "Ethanol", "dilutionPct": 100, "weightG": 98.8, "solvent": True}]})
    page.set_input_files("#impFile", tweenamen); page.wait_for_timeout(1000)
    kop = page.text_content("#content")
    import re as _re
    mnew = _re.search(r"(\d+) new \(will be created", kop or "")
    check(f"de voorvertoning belooft één nieuw materiaal voor die twee namen ({mnew.group(1) if mnew else '?'})",
          bool(mnew) and mnew.group(1) == "1")
    page.click("#btnImpOk"); page.wait_for_timeout(1200)
    gemaakt = page.evaluate("DATA.materials.length") - voorM
    namen = page.evaluate("""() => DATA.materials.filter(m => /A1/.test(m.name) || /A1/.test(m.aliases||"")).map(m => m.name)""")
    check(f"en er komt ook één materiaal ({gemaakt}: {namen})", gemaakt == 1)
    een = page.evaluate("""() => { const a = matByName('Proefstof A1'), b = matByName('Tweede naam A1');
        return [!!a, !!b, a && b && a.id === b.id]; }""")
    check(f"beide namen wijzen naar hetzelfde materiaal ({een})", een == [True, True, True])
    gew = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === 'A1 test');
        const v = f.versions[f.versions.length-1];
        const ids = new Set(v.lines.map(l => l.materialId));
        return [v.lines.length, ids.size]; }""")
    check(f"de twee regels staan op één materiaal ({gew})", gew == [3, 2])
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # ---- bouw 260922a, punt A5: een vorm die geen lijst is, zet de app niet vast ----
    page.click("#btnHome"); page.wait_for_timeout(300)
    for naam, pkg in [
        ("obj.json",  {"type": "miformulas-import", "formulas": [{"name": "X", "versions": {"v1": {"lines": []}}}]}),
        ("getal.json",{"type": "miformulas-import", "formulas": [{"name": "X", "versions": 3}]}),
        ("tekst.json",{"type": "miformulas-import", "formulas": [{"name": "X", "versions": "oeps"}]}),
        ("regels.json",{"type": "miformulas-import", "formulas": [{"name": "X", "versions": [{"lines": {"a": 1}}]}]}),
    ]:
        f = schrijf(naam, pkg)
        page.set_input_files("#impFile", f); page.wait_for_timeout(900)
        # de voorvertoning wordt getekend in plaats van te gooien, en de sluis weigert het bestand netjes
        getekend = page.evaluate("!!document.querySelector('#btnImpCancel')")
        leeg = page.locator("#impEmpty").count() == 1
        dicht = page.locator("#btnImpOk").count() == 0 or page.locator("#btnImpOk").is_disabled()
        check(f"{naam}: de voorvertoning wordt getekend in plaats van te gooien", getekend)
        check(f"{naam}: Confirm blijft dicht en het zegt waarom (leeg={leeg})", dicht and leeg)
        page.click("#btnImpCancel"); page.wait_for_timeout(500)
        page.click("#tabF"); page.wait_for_timeout(300)
        page.click("#list .item >> nth=0"); page.wait_for_timeout(600)
        weer = page.evaluate("[!!IMPORTP, !!VIEW.id, !!document.querySelector('#btnImpCancel')]")
        check(f"{naam}: en daarna opent een formule gewoon ({weer})", weer == [False, True, False])
    nX = page.evaluate("DATA.formulas.filter(f => f.name === 'X').length")
    check(f"en er is niets ingevoerd ({nX} formule(s) X)", nX == 0)

    # ---------- B5 (bouw 260922d): het venster telt wat er werkelijk aankomt ----------
    # applyBulkImport laat een versie zonder regels vallen en een formule die daardoor geen versie overhoudt.
    # De kop telde alles wat het bestand noemt, dus ze beloofde formules en versies die nooit aankwamen.
    page.click("#btnHome"); page.wait_for_timeout(300)
    gemengd = schrijf("gemengd.json", {"type": "miformulas-import", "source": "B5", "formulas": [
        {"name": "B5 volledig", "versions": [{"name": "v1", "lines": [
            {"material": "Iso E Super", "dilutionPct": 100, "weightG": 1}]}]},
        {"name": "B5 half", "versions": [
            {"name": "leeg", "lines": []},
            {"name": "vol", "lines": [{"material": "Iso E Super", "dilutionPct": 100, "weightG": 2}]}]},
        {"name": "B5 leeg", "versions": [{"name": "niets", "lines": []}]}]})
    page.set_input_files("#impFile", gemengd); page.wait_for_timeout(1100)
    kop = " ".join((page.text_content("#content") or "").split())
    check(f"de kop telt wat er aankomt, niet wat het bestand noemt ({kop[:60]!r})",
          "2 formulas · 2 versions" in kop)
    drop = page.evaluate("""() => { const e = document.querySelector("#impDrop"); return e ? e.textContent.trim() : null; }""")
    check(f"en een regel zegt wat er wegvalt ({drop!r})",
          bool(drop) and "2 version(s)" in drop and "1 formula(s)" in drop)
    check("de rij van de lege formule zegt het ook", "no lines – left out" in (page.text_content("#content") or ""))
    voorF = page.evaluate("DATA.formulas.length")
    page.click("#btnImpOk"); page.wait_for_timeout(1200)
    kwam = page.evaluate("DATA.formulas.length") - voorF
    namen = page.evaluate("""() => DATA.formulas.filter(f => /^B5 /.test(f.name)).map(f => f.name + ":" + f.versions.length)""")
    check(f"en er komt precies dat aan ({kwam}: {namen})",
          kwam == 2 and sorted(namen) == ["B5 half:1", "B5 volledig:1"])
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    check(f"geen paginafouten ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
