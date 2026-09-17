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

    check(f"geen paginafouten ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
