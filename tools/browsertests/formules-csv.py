"""Formules invoeren uit een CSV (bouw 260916e): de rondgang van Export all formulas (Excel) met de elfde kolom Notes,
een blad zonder Formula-kolom, een vreemd blad met ; en decimale komma, de Total-regel als gewichtscontrole,
een onleesbaar gewicht dat Confirm blokkeert en een materialenblad dat netjes geweigerd wordt.
Vereist de lokale webserver op poort 8765, zie README."""
import csv, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def schrijf(pad, tekst):
    open(pad, "w", encoding="utf-8", newline="").write(tekst)
    return pad

with sync_playwright() as pw:
    b = pw.chromium.launch()
    tmp = tempfile.mkdtemp()

    # ---------------- 1. de rondgang: uitvoeren en elders weer invoeren ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1400)
    # een tweede versie met een label, notities en een spoorregel van 0,0004 g
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Rose de Mai 68");
        const v1 = f.versions[0];
        const nv = {v: 2, date: "2026-03-04", name: "45gr", notes: "Eerste regel.\\nTweede regel met ; en \\" erin.",
                    lines: v1.lines.map(l => ({...l}))};
        nv.lines[0].weightG = 0.0004;                       // een spoorregel mag niet naar 0 afronden
        nv.lines[1].weightG = 0.0025;                       // drie decimalen zouden hier 0,003 van maken (bouw 260920b)
        const eth = DATA.materials.find(m => m.isSolvent && m.name === "Ethanol");
        nv.lines.push({materialId: eth.id, dilutionPct: 100, weightG: 12.5, remark: 1});
        f.versions.push(nv); markDirty(); render(); }""")
    page.wait_for_timeout(400)
    telling = page.evaluate("""() => ({f: DATA.formulas.length,
        v: DATA.formulas.reduce((s, f) => s + f.versions.length, 0),
        l: DATA.formulas.reduce((s, f) => s + f.versions.reduce((t, v) => t + v.lines.length, 0), 0)})""")
    page.click("#btnHome"); page.wait_for_timeout(500)
    page.click("#homeIO"); page.wait_for_timeout(400)
    with page.expect_download() as dl:
        page.click("#btnExpF")
    pad = os.path.join(tmp, "uitvoer.csv"); dl.value.save_as(pad)
    page.wait_for_timeout(300)

    regels = list(csv.reader(open(pad, encoding="utf-8-sig"),
                             delimiter=";" if open(pad, encoding="utf-8-sig").readline().count(";") > 2 else ","))
    kop = regels[0]
    check(f"de uitvoer heeft elf kolommen ({len(kop)})", len(kop) == 11)
    check(f"de elfde heet Notes ({kop[-1]!r})", kop[-1] == "Notes")
    rose = [r for r in regels[1:] if r[0] == "Rose de Mai 68" and r[2] == "v2 45gr"]
    check(f"de tweede versie staat er met haar label ({len(rose)} rijen)", len(rose) == 10)   # 9 regels en de Total
    check("de notities staan alleen op de eerste regel van de versie",
          rose[0][10].startswith("Eerste regel.") and not any(r[10] for r in rose[1:]))
    check("de notities houden hun regeleinde", "\n" in rose[0][10])
    spoor = rose[0][6].replace(",", ".")
    check(f"een spoorregel houdt zes decimalen ({rose[0][6]!r})", float(spoor) == 0.0004)
    halve = rose[1][6].replace(",", ".")
    check(f"en een gewicht dat drie decimalen niet exact dragen ook ({rose[1][6]!r})", float(halve) == 0.0025)
    tot = [r for r in rose if r[4] == "Total"]
    check(f"de Total-regel sluit de versie af ({len(tot)})", len(tot) == 1 and tot[0][5] == "")
    check("een solventregel draagt (solvent) in de naam", any("(solvent)" in r[4] for r in rose))
    ctx.close()

    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs2 = []; msgs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnEmpty"); page.wait_for_timeout(1400)
    page.set_input_files("#impFile", pad); page.wait_for_timeout(900)
    check("het koppelvenster staat open", page.locator("#fcsvMap").is_visible())
    sel = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#fcsvMap select')].map(s => [s.dataset.k, s.value]))")
    check(f"alle acht de eigen kolommen zijn vooraf gekoppeld ({sel})", all(v != "" for v in sel.values()))
    telkst = page.text_content("#fcsvCount")
    check(f"de teller kent formules, versies en regels ({telkst.strip()})",
          f"{telling['f']} formula(s)" in telkst and f"{telling['v']} version(s)" in telkst and f"{telling['l']} line(s)" in telkst)
    check("de knop heet Continue", page.text_content("#dlgOk").strip() == "Continue")
    page.click("#dlgOk"); page.wait_for_timeout(1200)
    check("de voorvertoning is de samenvatting", page.locator("#btnImpOk").is_visible() and "Import formulas" in page.text_content("h2"))
    check("de Total-regel klopt, dus geen waarschuwing", page.locator("#impCheck").count() == 0)
    check("geen enkele regel is onleesbaar", page.locator("#impBad").count() == 0)
    msgs2.clear(); page.click("#btnImpOk"); page.wait_for_timeout(1500)
    na = page.evaluate("""() => ({f: DATA.formulas.length,
        v: DATA.formulas.reduce((s, f) => s + f.versions.length, 0),
        l: DATA.formulas.reduce((s, f) => s + f.versions.reduce((t, v) => t + v.lines.length, 0), 0)})""")
    check(f"alles is binnen ({na})", na == telling)
    r = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Rose de Mai 68");
        const v = f.versions[1], m = id => DATA.materials.find(x => x.id === id);
        return {cat: f.category, n: v.name, d: v.date, notes: v.notes, w0: v.lines[0].weightG, w1: v.lines[1].weightG,
                eth: !!m(v.lines[v.lines.length-1].materialId)?.isSolvent, ethw: v.lines[v.lines.length-1].weightG,
                nums: f.versions.map(x => x.v)}; }""")
    check(f"het versielabel is het label alleen ({r['n']!r})", r["n"] == "45gr")
    check(f"de datum en de categorie komen mee ({r['d']}, {r['cat']})", r["d"] == "2026-03-04" and r["cat"] == "Bases & Accords")
    check("de notities komen mee, met hun regeleinde", r["notes"].startswith("Eerste regel.") and "\n" in r["notes"])
    check(f"de spoorregel overleeft de rondgang ({r['w0']})", abs(r["w0"] - 0.0004) < 1e-9)
    check(f"en 0,0025 g komt niet als 0,003 terug ({r['w1']})", abs(r["w1"] - 0.0025) < 1e-9)
    check(f"de solventvlag komt mee ({r['eth']}, {r['ethw']} g)", r["eth"] is True and abs(r["ethw"] - 12.5) < 1e-9)
    check(f"de versies zijn hernummerd ({r['nums']})", r["nums"] == [1, 2])
    page.keyboard.press("Control+z"); page.wait_for_timeout(1200)
    check("één undo neemt de hele invoer terug",
          page.evaluate("DATA.formulas.length") == 0 and page.evaluate("DATA.materials.length") == 0)

    # ---------------- 2. zonder Formula-kolom: de bestandsnaam is de formule ----------------
    los = schrijf(os.path.join(tmp, "Mijn Roos.csv"),
        "Entry,Material,Dilution %,Weight g,Notes\r\n"
        "v3 45gr,Geraniol,100,12.5,Uit het schriftje\r\n"
        "v3 45gr,Citronellol,10,4,\r\n"
        "v3 45gr,Ethanol (solvent),100,30,\r\n")
    page.set_input_files("#impFile", los); page.wait_for_timeout(900)
    check("zonder Formula-kolom blijft die ongekoppeld",
          page.evaluate("() => document.querySelector('#fcsv_formula').value") == "")
    check("de teller ziet één formule met één versie", "1 formula(s) · 1 version(s) · 3 line(s)" in page.text_content("#fcsvCount"))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("de voorvertoning is de regeltabel met de keuzelijst", page.locator("#impTarget").is_visible())
    p = page.evaluate("() => ({n: IMPORTP.name, vn: IMPORTP.versionName, nt: IMPORTP.notes, s: IMPORTP.lines[2].solvent})")
    check(f"de bestandsnaam is de formulenaam ({p['n']!r})", p["n"] == "Mijn Roos")
    check(f"\"v3 45gr\" wordt het label ({p['vn']!r})", p["vn"] == "45gr")
    check(f"de notities zijn overgenomen ({p['nt']!r})", p["nt"] == "Uit het schriftje")
    check("\" (solvent)\" gaat van de naam af en wordt de vlag", p["s"] is True)
    msgs2.clear(); page.click("#btnImpOk"); page.wait_for_timeout(1200)
    r2 = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Mijn Roos");
        return f && {v: f.versions.length, n: f.versions[0].name, l: f.versions[0].lines.length,
                     sol: DATA.materials.find(m => m.name === "Ethanol")?.isSolvent}; }""")
    check(f"de formule is binnen ({r2})", r2 and r2["v"] == 1 and r2["n"] == "45gr" and r2["l"] == 3)
    check("het aangemaakte ethanol is een solvent", r2["sol"] is True)
    page.keyboard.press("Control+z"); page.wait_for_timeout(1000)
    check("undo neemt ze terug", page.evaluate("DATA.formulas.length") == 0)

    # ---------------- 3. een vreemd blad: ; decimale komma, synoniemen, twee formules ----------------
    vreemd = schrijf(os.path.join(tmp, "kladblok.csv"),
        "Formule;Versie;Ingredient;Dilutie;Gewicht\r\n"
        "Aura;v1;Geraniol;100;12,5\r\n"
        "Aura;v1;Hedione;10;7,25\r\n"
        "Aura;v2 20%;Geraniol;100;25\r\n"
        "Brise;;Linalool;100;40\r\n"
        "Brise;;Hedione;100;60\r\n")
    page.set_input_files("#impFile", vreemd); page.wait_for_timeout(900)
    v = page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#fcsvMap select')].map(s => [s.dataset.k, s.value]))")
    check(f"de synoniemen koppelen vanzelf ({v})",
          v["formula"] == "0" and v["entry"] == "1" and v["material"] == "2" and v["dilution"] == "3" and v["weight"] == "4")
    check("twee formules, drie versies, vijf regels", "2 formula(s) · 3 version(s) · 5 line(s)" in page.text_content("#fcsvCount"))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    msgs2.clear(); page.click("#btnImpOk"); page.wait_for_timeout(1200)
    r3 = page.evaluate("""() => { const a = DATA.formulas.find(x => x.name === "Aura"), br = DATA.formulas.find(x => x.name === "Brise");
        return {av: a && a.versions.map(v => v.name), aw: a && a.versions[0].lines[0].weightG,
                bv: br && br.versions.length, bl: br && br.versions[0].lines.length}; }""")
    check(f"Aura kreeg twee versies met het juiste label ({r3['av']})", r3["av"] == ["", "20%"])
    check(f"de decimale komma is gelezen ({r3['aw']})", abs(r3["aw"] - 12.5) < 1e-9)
    check(f"een lege Versie-cel blijft één versie ({r3['bv']} met {r3['bl']} regels)", r3["bv"] == 1 and r3["bl"] == 2)
    page.keyboard.press("Control+z"); page.wait_for_timeout(1000)

    # ---------------- 4. de Total-regel als gewichtscontrole, en een onleesbaar gewicht ----------------
    scheef = schrijf(os.path.join(tmp, "scheef.csv"),
        "Formula,Entry,Material,Dilution %,Weight g\r\n"
        "Test,v1,Geraniol,100,10\r\n"
        "Test,v1,Hedione,100,10\r\n"
        "Test,v1,Total,,25\r\n"
        "Test,v2,Geraniol,100,10\r\n"
        "Test,v2,Hedione,100,10\r\n"
        "Test,v2,Total,,20\r\n")
    page.set_input_files("#impFile", scheef); page.wait_for_timeout(900)
    check("de Total-regels tellen niet als regel", "1 formula(s) · 2 version(s) · 4 line(s)" in page.text_content("#fcsvCount"))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("de voorvertoning waarschuwt over de ene scheve Total", page.locator("#impCheck").count() == 1)
    check("en noemt de versie erbij", "Test v1" in page.text_content("#impCheck"))
    check("maar blokkeert de invoer niet", not page.locator("#btnImpOk").is_disabled())
    page.click("#btnImpCancel"); page.wait_for_timeout(500)

    stuk = schrijf(os.path.join(tmp, "stuk.csv"),
        "Formula,Entry,Material,Dilution %,Weight g\r\n"
        "Kapot,v1,Geraniol,100,10\r\n"
        "Kapot,v1,Hedione,100,ongeveer twee\r\n"
        "Kapot,v1,,100,5\r\n")
    page.set_input_files("#impFile", stuk); page.wait_for_timeout(900)
    check("de teller meldt de rij zonder materiaalnaam", "1 row(s) without a material name" in page.text_content("#fcsvCount"))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("de voorvertoning zet één regel rood: de rij zonder naam is er al uit (bouw 260918b)",
          page.locator("tr.badLine").count() == 1)
    check("Confirm import staat uit", page.locator("#btnImpOk").is_disabled())
    check("met de reden in de kolom Status", "weight is not a number" in page.text_content("table.lines"))
    check("en de rij zonder naam staat in de controleregel, niet in het rood",
          page.locator("#impCheck").count() == 1 and "no material name" in page.text_content("#impCheck"))
    page.click("#btnImpCancel"); page.wait_for_timeout(500)
    check("er is niets veranderd", page.evaluate("DATA.formulas.length") == 0)

    # ---------------- 4b. bouw 260918b: de Total-regel, het doorlopende label en de datum ----------------
    total = schrijf(os.path.join(tmp, "total.csv"),      # de dilutiekolom in Excel naar beneden doorgetrokken
        "Formula,Entry,Date,Material,Dilution %,Weight g\r\n"
        "Doorgetrokken,v1,2026-02-03,Geraniol,100,10\r\n"
        "Doorgetrokken,v1,2026-02-03,Hedione,100,15\r\n"
        "Doorgetrokken,v1,2026-02-03,Total,100,25\r\n")
    page.set_input_files("#impFile", total); page.wait_for_timeout(900)
    check("een Total-regel met een dilutie telt niet als regel",
          "1 formula(s) · 1 version(s) · 2 line(s)" in page.text_content("#fcsvCount"))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    check("en de gewichtscontrole klopt, dus geen waarschuwing", page.locator("#impCheck").count() == 0)
    check("geen materiaal Total in de voorvertoning", "Total" not in page.text_content("table.lines tbody"))
    page.click("#btnImpOk"); page.wait_for_timeout(1000)
    na = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Doorgetrokken");
        return {n: f.versions[0].lines.length, datum: f.versions[0].date,
                total: DATA.materials.some(m => /^total$/i.test(m.name)),
                bestel: (DATA.orderList || []).some(o => /^total$/i.test(o.name))}; }""")
    check(f"twee regels binnen, geen materiaal Total, geen bestelregel ({na})",
          na["n"] == 2 and not na["total"] and not na["bestel"])
    check(f"en de datum uit het blad staat op de versie ({na['datum']})", na["datum"] == "2026-02-03")
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    label = schrijf(os.path.join(tmp, "label.csv"),       # het label staat alleen bij de eerste formule
        "Formula,Entry,Material,Dilution %,Weight g\r\n"
        "Eerste,v1 45gr,Geraniol,100,10\r\n"
        "Tweede,,Hedione,100,10\r\n"
        "Derde,,Geraniol,100,10\r\n")
    page.set_input_files("#impFile", label); page.wait_for_timeout(900)
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    page.click("#btnImpOk"); page.wait_for_timeout(1200)
    labels = page.evaluate("""() => ["Eerste", "Tweede", "Derde"].map(n => {
        const f = DATA.formulas.find(x => x.name === n); return f ? f.versions[0].name : "?"; })""")
    check(f"het label loopt niet door naar de volgende formule ({labels})", labels == ["45gr", "", ""])
    page.keyboard.press("Control+z"); page.wait_for_timeout(700)

    # ---------------- 5. een materialenblad hoort hier niet ----------------
    mats = schrijf(os.path.join(tmp, "kast.csv"),
        "Name,CAS,Category,Dilutions %\r\n"
        "Iso E Super,54464-57-2,Woody,100 / 10\r\n")
    page.set_input_files("#impFile", mats); page.wait_for_timeout(900)
    check("Name koppelt aan Material", page.evaluate("() => document.querySelector('#fcsv_material').value") == "0")
    check("maar zonder gewichtskolom staat de knop uit", page.locator("#dlgOk").is_disabled())
    check("en de teller wijst de weg", "material names and the weights" in page.text_content("#fcsvCount"))
    page.click("#dlgCancel"); page.wait_for_timeout(400)

    # ---------------- 6. de JSON-weg blijft ongemoeid ----------------
    js = os.path.join(tmp, "geen-import.json")
    open(js, "w", encoding="utf-8").write('{"type":"iets-anders","lines":[]}')
    msgs2.clear(); page.set_input_files("#impFile", js); page.wait_for_timeout(700)
    check("een .json dat geen import is wordt nog altijd geweigerd",
          any("not a miFormulas import file" in m for m in msgs2))

    # ---------------- B6 (bouw 260922d): alleen een blad met een Date-kolom kan "geen datum" bedoelen ----------------
    # csvFormulaGroups start elke groep op date:"", dus csvToImport stuurde altijd een date-sleutel mee. De wacht van
    # 260920m leest "de sleutel bestaat" als "de afzender bedoelde geen datum", en daardoor kreeg élk blad zonder
    # Date-kolom versies met een lege datum, terwijl de regel is dat zo'n bestand vandaag krijgt.
    ctx3 = b.new_context(viewport={"width": 1400, "height": 900})
    pg3 = ctx3.new_page(); errs3 = []; msgs3 = []
    pg3.on("pageerror", lambda e: errs3.append(str(e)))
    pg3.on("dialog", lambda d: (msgs3.append(d.message), d.accept()))
    pg3.goto(URL); pg3.wait_for_timeout(800)
    pg3.click("#btnStarter"); pg3.wait_for_timeout(1500)
    vandaag = pg3.evaluate("today()")

    zonder = schrijf(os.path.join(tmp, "zonder-datum.csv"),
        "Material,Weight g\nIso E Super,10\nHedione,5\n")
    pg3.set_input_files("#impFile", zonder); pg3.wait_for_timeout(1000)
    pg3.click("#dlgOk"); pg3.wait_for_timeout(1100)      # eerst het kolomvenster
    pg3.click("#btnImpOk"); pg3.wait_for_timeout(1200)
    d1 = pg3.evaluate("""() => { const f = DATA.formulas.find(x => /zonder-datum/i.test(x.name));
        return f ? f.versions[f.versions.length-1].date : "geen formule"; }""")
    check(f"een blad zonder Date-kolom krijgt de datum van vandaag ({d1})", d1 == vandaag)
    pg3.keyboard.press("Control+z"); pg3.wait_for_timeout(700)

    leeg = schrijf(os.path.join(tmp, "lege-datum.csv"),
        "Formula,Date,Material,Weight g\nB6 leeg,,Iso E Super,10\n")
    pg3.set_input_files("#impFile", leeg); pg3.wait_for_timeout(1000)
    pg3.click("#dlgOk"); pg3.wait_for_timeout(1100)
    pg3.click("#btnImpOk"); pg3.wait_for_timeout(1200)
    d2 = pg3.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "B6 leeg");
        return f ? f.versions[f.versions.length-1].date : "geen formule"; }""")
    check(f"een blad mét een lege Date-cel houdt zijn lege datum ({d2!r})", d2 == "")
    pg3.keyboard.press("Control+z"); pg3.wait_for_timeout(700)

    twee = schrijf(os.path.join(tmp, "twee-zonder.csv"),
        "Formula,Material,Weight g\nB6 een,Iso E Super,10\nB6 twee,Hedione,5\n")
    pg3.set_input_files("#impFile", twee); pg3.wait_for_timeout(1000)
    pg3.click("#dlgOk"); pg3.wait_for_timeout(1100)
    pg3.click("#btnImpOk"); pg3.wait_for_timeout(1300)
    d3 = pg3.evaluate("""() => DATA.formulas.filter(f => /^B6 (een|twee)$/.test(f.name))
        .map(f => f.name + ":" + f.versions[0].date)""")
    check(f"ook bij meerdere formules in één blad zonder Date-kolom ({d3})",
          sorted(d3) == ["B6 een:" + vandaag, "B6 twee:" + vandaag])
    check(f"geen paginafouten bij de datumproef ({errs3[:2]})", not errs3)
    ctx3.close()

    check(f"geen paginafouten in de uitvoer ({errs[:2]})", not errs)
    check(f"geen paginafouten in de invoer ({errs2[:2]})", not errs2)
    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
