"""De CSV-route voor materialen (bouw 261010d): Export all materials (Excel) en Import materials inventory from CSV…
dragen ook het saldo en de regels van een beschrijving. Het saldo van Stock g (tracked) wordt bij de import een telling
van vandaag (een negatief saldo of een cel zonder getal blijft weg), de beschrijving gaat met haar regeleinden in de cel
en komt zo terug, een kop Stock uit een ander blad koppelt vanzelf, het sjabloon heeft de kolom, en §16 zegt het.
Vereist de lokale webserver op poort 8765, zie README."""
import csv, os, re, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, "..", "..", "index.html"), encoding="utf-8").read()
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def mat(page, name):
    return page.evaluate("""n => { const m = DATA.materials.find(x => x.name === n); if (!m) return null;
        const st = stockCalc(m);
        return {desc: m.description, ev: (m.stockEvents || []).map(e => ({t: e.t, g: e.g, date: e.date, note: e.note || ""})),
                tracked: st.tracked, qty: st.qty}; }""", name)

def rijen(pad):
    kop = open(pad, encoding="utf-8-sig").readline()
    sep = ";" if kop.count(";") > kop.count(",") else ","      # de uitvoer volgt de taal van de browser
    return list(csv.reader(open(pad, encoding="utf-8-sig", newline=""), delimiter=sep))

def koppeling(page):
    return page.evaluate("() => Object.fromEntries([...document.querySelectorAll('#csvMap select')].map(s => [s.dataset.k, s.value]))")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    tmp = tempfile.mkdtemp()

    # ---------------- 1. de export: saldo en beschrijving ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)
    page.evaluate("""() => { const by = n => DATA.materials.find(x => x.name === n);
        const h = by("Hedione"); h.description = "clean jasmine\\nwatery, radiant";
        h.stockEvents = [{t: "take", date: "2026-01-01", g: 40}, {t: "buy", date: "2026-02-01", amount: 10, unit: "g", g: 10}];
        const l = by("Linalool"); l.stockEvents = [{t: "take", date: "2026-01-01", g: 5}, {t: "prep", date: "2026-01-02", g: 7, formula: "Proef v1"}];
        const c = by("Coumarin"); delete c.stockEvents; c.description = "hay, tonka";
        markDirty(); }""")
    page.wait_for_timeout(300)
    n_mats = page.evaluate("DATA.materials.length")
    page.click("#btnHome"); page.wait_for_timeout(500)
    page.click("#homeIO"); page.wait_for_timeout(400)
    with page.expect_download() as dl:
        page.click("#btnExpM")
    pad = os.path.join(tmp, "uitvoer.csv"); dl.value.save_as(pad)
    rows = rijen(pad); kop = rows[0]
    rij = {r[0]: r for r in rows[1:] if r}
    si = kop.index("Stock g (tracked)") if "Stock g (tracked)" in kop else None
    di = kop.index("Description")
    check(f"de kolom Stock g (tracked) staat in de export (kolom {si})", si == 15)
    check(f"de beschrijving staat met haar regeleinde in één cel ({rij['Hedione'][di]!r})", rij["Hedione"][di] == "clean jasmine\nwatery, radiant")
    check(f"het saldo van Hedione is 40 + 10 ({rij['Hedione'][si]!r})", si is not None and rij["Hedione"][si].replace(",", ".") == "50.000")
    ctx.close()

    # ---------------- 2. terug inlezen in een lege app ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, accept_downloads=True)
    page = ctx.new_page(); errs2 = []; msgs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnEmpty"); page.wait_for_timeout(1400)
    vandaag = page.evaluate("today()")
    page.set_input_files("#impCsv", pad); page.wait_for_timeout(900)
    k = koppeling(page)
    check(f"de kolom Stock g (tracked) koppelt vanzelf ({k.get('stock')!r})", k.get("stock") == "15")
    check("alle eigen kolommen zijn gekoppeld", all(v != "" for v in k.values()))
    page.click("#dlgOk"); page.wait_for_timeout(1200)
    check(f"alle materialen zijn binnen ({page.evaluate('DATA.materials.length')} van {n_mats})", page.evaluate("DATA.materials.length") == n_mats)
    h = mat(page, "Hedione")
    check(f"het saldo wordt één telling van vandaag ({h['ev']})",
          h["ev"] == [{"t": "take", "g": 50, "date": vandaag, "note": "from spreadsheet"}])
    check(f"Hedione wordt bijgehouden met 50 g ({h['tracked']}, {h['qty']})", h["tracked"] and h["qty"] == 50)
    check(f"de beschrijving komt terug zoals ze was ({h['desc']!r})", h["desc"] == "clean jasmine\nwatery, radiant")
    l = mat(page, "Linalool")
    check(f"een negatief saldo geeft geen telling ({l['ev']})", l["ev"] == [] and not l["tracked"])
    c = mat(page, "Coumarin")
    check(f"zonder saldo blijft het materiaal onbijgehouden ({c['ev']})", c["ev"] == [] and not c["tracked"])
    check(f"een beschrijving van één regel blijft gelijk ({c['desc']!r})", c["desc"] == "hay, tonka")
    page.keyboard.press("Control+z"); page.wait_for_timeout(800)
    check("één Undo neemt alles terug, met de tellingen", page.evaluate("DATA.materials.length") == 0)

    # ---------------- 3. een ander blad: de kop Stock, een regeleinde van Windows ----------------
    blad = os.path.join(tmp, "kast.csv")
    open(blad, "w", encoding="utf-8", newline="").write(
        'Name;Stock;Notes\r\nAmbre test;12,5;"warm\r\nresinous"\r\nGeen getal;veel;\r\nLeeg;;\r\n')
    page.set_input_files("#impCsv", blad); page.wait_for_timeout(900)
    k = koppeling(page)
    check(f"de kop Stock koppelt vanzelf ({k.get('stock')!r}), Notes naar de beschrijving ({k.get('description')!r})",
          k.get("stock") == "1" and k.get("description") == "2")
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    a = mat(page, "Ambre test")
    check(f"12,5 wordt een telling van 12,5 g ({a and a['ev']})", a and a["ev"] == [{"t": "take", "g": 12.5, "date": vandaag, "note": "from spreadsheet"}])
    check(f"\\r\\n in een cel wordt \\n ({a and a['desc']!r})", a and a["desc"] == "warm\nresinous")
    g = mat(page, "Geen getal"); e = mat(page, "Leeg")
    check(f"een cel zonder getal en een lege cel geven geen telling ({g and g['ev']}, {e and e['ev']})",
          g and e and g["ev"] == [] and e["ev"] == [])
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)

    # ---------------- 4. het sjabloon ----------------
    with page.expect_download() as dl:
        page.click("#btnIO"); page.wait_for_timeout(400); page.click("#ioTpl")
    tpl = os.path.join(tmp, "sjabloon.csv"); dl.value.save_as(tpl)
    t = rijen(tpl); ts = t[0].index("Stock g (tracked)") if "Stock g (tracked)" in t[0] else None
    check(f"het sjabloon heeft de kolom Stock g (tracked), op de plaats van de export ({ts})", ts == 15 and t[0] == kop[:len(t[0])])
    check(f"de voorbeeldrijen: 85 bij Iso E Super, leeg bij ethanol ({ts is not None and [r[ts] for r in t[1:]]})",
          ts is not None and [r[ts] for r in t[1:]] == ["85", ""])
    page.set_input_files("#impCsv", tpl); page.wait_for_timeout(900)
    check("het sjabloon koppelt volledig", all(v != "" for v in koppeling(page).values()))
    page.click("#dlgOk"); page.wait_for_timeout(1000)
    i = mat(page, "Example: Iso E Super")
    check(f"het voorbeeld krijgt zijn telling van 85 g ({i and i['ev']})", i and i["ev"] == [{"t": "take", "g": 85, "date": vandaag, "note": "from spreadsheet"}])

    # ---------------- 5. de handleiding en de Help ----------------
    md = open(os.path.join(HERE, "..", "..", "docs", "manual.md"), encoding="utf-8").read()
    for naam, tekst in [("de handleiding", md), ("de Help in de app", SRC)]:
        check(f"{naam}: de kolom wordt een telling, de regels blijven, en niet meer 'ignored'",
              "becomes a stocktake dated today" in tekst and "keeps its lines" in tekst
              and "A stock column is ignored" not in tekst)
    check("de handleiding zegt wat er niet meegaat naar een andere kopie",
          "passes on your inventory without a single formula" in md and "the dates and notes of the dilutions" in md)

    check(f"geen paginafouten ({(errs + errs2)[:2]})", not errs and not errs2)
    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
