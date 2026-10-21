"""Bouw 261021a, de meldingen van 20/10 (Nog te doen, punten 23, 34, 35, 36 en 37):
- Browse the library… in + New material begint met de getypte naam, en Cancel of Escape keert terug naar New material met
  naam, categorie en dilutie; na Add niet, en een volgende Cancel opent niets meer;
- Fill in from the library… in het menu ⋯ van een materiaal: alleen lege velden, de namen van de regel als alternatieve
  naam (behalve een alternatieve naam van een ander materiaal), de opzoeklinks via die naam, één Undo-stap, ook voor een
  nieuwe categorie; niet zonder library en niet in alleen-lezen;
- Dilution made met een nieuw percentage zet het ook onder Dilutions, een bestaand blijft;
- een notitie in het Stock-paneel (stockNote), “· note” in de titel, in Export all materials en de CSV-invoer;
- Purchase › Add vraagt de aankoopdatum als die een andere datum heeft: Set date en No change, één Undo-stap.
Draait op de lokale webserver (poort 8765, zie README)."""
import json, os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
TGSC = "https://www.thegoodscentscompany.com/data/ab1015131.html"
LIB = {"type": "miformulas-materials", "name": "Testlibrary", "version": "2026-10-21", "licence": "CC BY 4.0", "materials": [
    {"name": "Rose absolute", "aliases": ["rosa damascena", "rose absolute bulgarian"], "cas": "8007-01-0", "category": "Flowers - red",
     "pyramid": 2, "ifraLimit": 99, "odour": ["rosy", "honeyed"], "strength": "medium", "tgsc": TGSC},
    {"name": "Zz testwood", "aliases": ["Zz wood"], "category": "Testwood 261021", "pyramid": 4},
    {"name": "Rose otto", "aliases": ["rosa damascena"], "cas": "8007-01-0", "category": "Flowers - red", "pyramid": 1}]}
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 760})
    page = ctx.new_page()
    errs, msgs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("https://data.miformulas.com/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(LIB)))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.add_style_tag(content="#storageHint{display:none!important}")
    vis = lambda s: page.locator(s).count() > 0 and page.locator(s).first.is_visible()
    def klik(s):   # op een oudere bouw zonder dat element: een FAIL in plaats van een wachttijd van 30 s
        if vis(s): page.click(s); page.wait_for_timeout(200); return True
        check(f"{s} is er", False); return False
    def vul(s, v):
        if vis(s): page.fill(s, v); return True
        check(f"{s} is er", False); return False
    val = lambda s: page.input_value(s) if page.locator(s).count() else None
    txt = lambda s: (page.locator(s).first.text_content() or "") if page.locator(s).count() else ""
    dlg_open = lambda: page.evaluate("document.querySelector('#dlg').open")
    M = lambda n, expr: page.evaluate(f"n => {{ const m = DATA.materials.find(x => x.name === n); return m ? ({expr}) : undefined; }}", n)
    def open_m(name):
        page.evaluate("n => { const m = DATA.materials.find(x => x.name === n); switchTab('M', m.id, null); }", name); page.wait_for_timeout(400)
    def esc():
        page.keyboard.press("Escape"); page.wait_for_timeout(300)
    today = page.evaluate("today()")

    # ---------- 34 zonder library: geen Fill in from the library… ----------
    open_m("Geraniol")
    klik("#mMore summary")
    check("zonder library staat Fill in from the library… niet in het menu ⋯", page.locator("#btnFillLib").count() == 0 and vis("#btnDelMat"))
    esc()
    page.evaluate("async () => { setMaterialList(await fetchLibrary()); render(); }"); page.wait_for_timeout(400)
    check("de testlibrary is geladen", page.evaluate("listMaterials().length") == 3)

    # ---------- 23: Browse the library… vanuit + New material ----------
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    hint = txt("#nmBrowse + .hint")
    check(f"de uitleg naast Browse the library… ({hint!r})", hint == "search the whole library and add one or more")
    cat2 = page.evaluate("() => [...document.querySelectorAll('#nmCat option')].map(o => o.value).find(v => v !== 'Uncategorised')")
    page.fill("#nmName", "rose"); page.select_option("#nmCat", cat2); page.fill("#nmDil", "10")
    klik("#nmBrowse"); page.wait_for_timeout(300)
    rows = page.locator("#brRows input[data-n]").count()
    check(f"Browse begint met de getypte naam als zoekterm ({val('#brQ')!r}, {rows} regels)", val("#brQ") == "rose" and rows == 2)
    klik("#dlgCancel"); page.wait_for_timeout(300)
    back = [dlg_open(), val("#nmName"), val("#nmCat"), val("#nmDil")]
    check(f"Cancel brengt New material terug met naam, categorie en dilutie ({back})", back == [True, "rose", cat2, "10"])
    klik("#nmBrowse"); page.wait_for_timeout(300)
    esc()
    back = [dlg_open(), val("#nmName"), val("#nmCat"), val("#nmDil")]
    check(f"Escape in Browse doet hetzelfde ({back})", back == [True, "rose", cat2, "10"])
    # een naam uit de library kiest de categorie, en die blijft na Cancel
    if vul("#nmName", "Zz testwood"): page.dispatch_event("#nmName", "input"); page.wait_for_timeout(200)
    c1 = val("#nmCat")
    klik("#nmBrowse"); page.wait_for_timeout(300); klik("#dlgCancel"); page.wait_for_timeout(300)
    check(f"een categorie uit de library blijft na Cancel ({c1!r}, {val('#nmCat')!r})", c1 == "Testwood 261021" and val("#nmCat") == c1)
    if vul("#nmName", ""): page.dispatch_event("#nmName", "input")
    klik("#nmBrowse"); page.wait_for_timeout(300)
    n0 = page.evaluate("DATA.materials.length")
    klik("#brRows input[data-n='Rose otto']")
    klik("#dlgOk"); page.wait_for_timeout(400)
    check("na Add komt New material niet terug", not dlg_open() and page.evaluate("DATA.materials.length") == n0 + 1)
    page.click("#btnNewMat"); page.wait_for_timeout(300); klik("#dlgCancel"); page.wait_for_timeout(300)
    check("een volgende Cancel opent niets meer", not dlg_open())
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo neemt Rose otto terug", page.evaluate("!DATA.materials.some(m => m.name === 'Rose otto')"))

    # ---------- 34: Fill in from the library… ----------
    page.evaluate("""() => { addOneFromList('Rose absolute');
        const r = addFromList(null, 'Rose absolute Bulgaria', 100, null); DATA.materials.sort((a,b) => a.name.localeCompare(b.name));
        invalidateMats(); markDirty(); render(); }"""); page.wait_for_timeout(300)
    check("Rose absolute uit de library draagt de alternatieve namen van de regel",
          "rosa damascena" in (M("Rose absolute", "m.aliases") or ""))
    open_m("Rose absolute Bulgaria")
    links0 = page.evaluate("() => document.querySelector('.fLinks a.lookup')?.href || ''")
    check(f"zonder feiten zoekt TGSC via DuckDuckGo ({links0[:40]})", "duckduckgo" in links0)
    klik("#mMore summary")
    check("met library staat Fill in from the library… boven Delete material",
          vis("#btnFillLib") and txt("#btnFillLib") == "Fill in from the library…"
          and page.evaluate("() => { const b = [...document.querySelectorAll('#mMore .menuPop button')]; return b.map(x => x.id).join(); }") == "btnFillLib,btnDelMat")
    klik("#btnFillLib"); page.wait_for_timeout(300)
    check(f"het venster zoekt met de naam van het materiaal; de alternatieve naam van de regel vindt ze ({val('#flQ')!r}, {txt('#flRows label')[:30]!r})",
          dlg_open() and val("#flQ") == "Rose absolute Bulgaria" and page.locator("#flRows label").count() == 1
          and txt("#flRows label").startswith("Rose absolute"))
    vul("#flQ", "rose bulgaria x"); page.dispatch_event("#flQ", "input") if page.locator("#flQ").count() else None; page.wait_for_timeout(200)
    check("niets gevonden: dat zegt de lijst", "Nothing in the library matches." in txt("#flRows"))
    vul("#flQ", "rose absolute"); page.dispatch_event("#flQ", "input") if page.locator("#flQ").count() else None; page.wait_for_timeout(200)
    page.keyboard.press("Enter"); page.wait_for_timeout(200)
    check("Enter in het zoekveld vult niets in", dlg_open() and M("Rose absolute Bulgaria", "m.cas") == "")
    rij = page.locator("#flRows label", has_text="Rose absolute")
    check(f"de regel die je al hebt, staat erin en is te kiezen ({txt('#flRows label')!r})",
          rij.count() == 1 and "in your inventory" in (rij.first.text_content() or "") and rij.first.locator("input").is_enabled())
    if rij.count() and rij.first.is_visible(): rij.first.locator("input").click(); page.wait_for_timeout(200)
    w = txt("#flWhat")
    check(f"onder de lijst wat er gebeurt ({w!r})", w == "Fills in CAS, category, pyramid level, IFRA limit and description; adds 1 alternative name.")
    klik("#dlgOk"); page.wait_for_timeout(400)
    got = M("Rose absolute Bulgaria", "[m.cas, m.category, m.pyramid, m.ifraLimit, m.description, m.aliases]")
    check(f"de lege velden zijn ingevuld ({got})", got and got[:4] == ["8007-01-0", "Flowers - red", 2, 99] and got[4].startswith("rosy, honeyed"))
    check("de naam van de regel als alternatieve naam; een alternatieve naam van Rose absolute niet", got and got[5] == "Rose absolute")
    check("een import vindt nog altijd Rose absolute, zonder te vragen",
          page.evaluate("matsByName('Rose absolute').map(m => m.name).join()") == "Rose absolute"
          and page.evaluate("matsByName('rosa damascena').map(m => m.name).join()") == "Rose absolute")
    links1 = page.evaluate("() => document.querySelector('.fLinks a.lookup')?.href || ''")
    check(f"de TGSC-link opent nu de pagina uit de library ({links1})", links1 == TGSC)
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    got = M("Rose absolute Bulgaria", "[m.cas, m.category, m.pyramid, m.ifraLimit, m.description, m.aliases || '']")
    check(f"één Undo neemt alles terug ({got})", got == ["", "Uncategorised", 5, None, "", ""])
    # wat je zelf invulde, blijft
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Rose absolute Bulgaria'); m.ifraLimit = 0.5; m.description = 'my own words'; render(); }")
    page.wait_for_timeout(200)
    klik("#mMore summary"); klik("#btnFillLib"); page.wait_for_timeout(300)
    vul("#flQ", "8007-01-0"); page.dispatch_event("#flQ", "input") if page.locator("#flQ").count() else None; page.wait_for_timeout(200)
    check("zoeken op CAS vindt beide rozen", page.locator("#flRows label").count() == 2)
    if vis("#flRows label"): page.locator("#flRows label", has_text="Rose absolute").first.locator("input").click()
    page.wait_for_timeout(200)
    w = txt("#flWhat")
    check(f"een eigen IFRA-limiet en beschrijving tellen niet als leeg ({w!r})", w == "Fills in CAS, category and pyramid level; adds 1 alternative name.")
    klik("#dlgOk"); page.wait_for_timeout(400)
    got = M("Rose absolute Bulgaria", "[m.cas, m.ifraLimit, m.description]")
    check(f"en ze blijven staan ({got})", got == ["8007-01-0", 0.5, "my own words"])
    klik("#mMore summary"); klik("#btnFillLib"); page.wait_for_timeout(300)
    check(f"met een CAS begint het zoekveld met de CAS ({val('#flQ')!r})", val("#flQ") == "8007-01-0")
    esc()
    # een nieuwe categorie gaat mee in dezelfde Undo-stap
    page.evaluate("() => { addFromList(null, 'Mystery wood', 100, null); DATA.materials.sort((a,b) => a.name.localeCompare(b.name)); invalidateMats(); render(); }")
    open_m("Mystery wood")
    klik("#mMore summary"); klik("#btnFillLib"); page.wait_for_timeout(300)
    vul("#flQ", "zz wood"); page.dispatch_event("#flQ", "input") if page.locator("#flQ").count() else None; page.wait_for_timeout(200)
    klik("#flRows input[type=radio]")
    klik("#dlgOk"); page.wait_for_timeout(400)
    check("een categorie uit de library die je nog niet had, komt erbij",
          M("Mystery wood", "m.category") == "Testwood 261021" and page.evaluate("DATA.materialCategories.includes('Testwood 261021')"))
    check("de namen van de regel komen erbij", M("Mystery wood", "m.aliases") == "Zz testwood; Zz wood")
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo neemt ook de categorie terug", M("Mystery wood", "m.category") == "Uncategorised" and not page.evaluate("DATA.materialCategories.includes('Testwood 261021')"))
    page.evaluate("document.body.classList.add('ro')"); page.wait_for_timeout(100)
    if vis("#mMore summary"): page.click("#mMore summary"); page.wait_for_timeout(200)
    check("in alleen-lezen staat Fill in from the library… er niet", page.locator("#btnFillLib").count() == 1 and not vis("#btnFillLib"))
    esc(); page.evaluate("document.body.classList.remove('ro')")

    # ---------- 35: Dilution made met een nieuw percentage ----------
    open_m("Geraniol")
    page.evaluate("() => { STOCKOPEN = true; render(); }"); page.wait_for_timeout(300)
    d0 = M("Geraniol", "m.dilutions.map(d => d.pct)")
    d0 = M("Geraniol", "JSON.stringify(m.dilutions)")
    vul("#stDilPct", "5"); vul("#stDilG", "20"); klik("#btnDil"); page.wait_for_timeout(300)
    d1 = M("Geraniol", "m.dilutions.map(d => [d.pct, d.isBase, d.date, d.notes])")
    check(f"Dilution made zet 5 % onder Dilutions, gedateerd vandaag, niet als basis, op zijn plaats ({d1})",
          d1 and [d[0] for d in d1] == [100, 10, 5] and d1[2] == [5, False, today, ""])
    check("de stockregel staat er ook", M("Geraniol", "(m.stockEvents || []).at(-1)?.t") == "dil")
    page.evaluate("() => { DATA.materials.find(x => x.name === 'Geraniol').dilutions[1].date = '2025-01-01'; render(); }"); page.wait_for_timeout(200)
    vul("#stDilPct", "10"); vul("#stDilG", "5"); klik("#btnDil"); page.wait_for_timeout(300)
    d2 = M("Geraniol", "m.dilutions.map(d => [d.pct, d.date])")
    check(f"een bestaande dilutie verandert niet ({d2})", d2 and len(d2) == 3 and d2[1] == [10, "2025-01-01"])
    page.keyboard.press("Control+z"); page.wait_for_timeout(200); page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo neemt de stockregel en de dilutie samen terug", M("Geraniol", "JSON.stringify(m.dilutions)") == d0
          and not M("Geraniol", "(m.stockEvents || []).length"))

    # ---------- 36: de notitie in het Stock-paneel ----------
    lab = page.evaluate("() => document.querySelector('label[for=mStockNote]')?.textContent || ''")
    check(f"een tekstvak Note in het Stock-paneel, ook zonder gevolgde stock ({lab!r})", vis("textarea#mStockNote[data-f=stockNote]") and lab == "Note")
    vul("#mStockNote", "20 g left of the 2024 bottle")
    if vis("#mStockNote"): page.press("#mStockNote", "Tab")
    page.wait_for_timeout(300)
    check("de notitie staat op het materiaal en in het databestand",
          M("Geraniol", "m.stockNote") == "20 g left of the 2024 bottle" and '"stockNote":"20 g left of the 2024 bottle"' in page.evaluate("serialize()").replace(": ", ":"))
    page.evaluate("() => { STOCKOPEN = false; render(); }"); page.wait_for_timeout(300)
    s = txt("#stockBox summary").strip()
    check(f"de dichte titel zegt dat er een notitie is ({s!r})", s == "Stock – not tracked · note")
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.stockEvents = [{t: 'take', date: today(), g: 12}]; render(); }")
    page.wait_for_timeout(200)
    s = txt("#stockBox summary").strip()
    check(f"ook bij gevolgde stock ({s!r})", s.startswith("Stock – 12") and s.endswith(" · note"))
    rows = page.evaluate("() => { let out = null; const o = dlCsv; dlCsv = r => { out = r; }; try{ exportAllMaterials(); } finally { dlCsv = o; } return out; }")
    gr = [r for r in (rows or [])[1:] if r[0] == "Geraniol"]
    check(f"Export all materials heeft de kolom Stock note, als laatste ({(rows or [[]])[0][-2:]})",
          rows and rows[0][-1] == "Stock note" and gr and gr[0][-1] == "20 g left of the 2024 bottle")
    tpl = page.evaluate("() => { let out = null; const o = dlCsv; dlCsv = r => { out = r; }; try{ csvTemplate(); } finally { dlCsv = o; } return out; }")
    check("het sjabloon heeft dezelfde kolommen, elke rij even lang", tpl and tpl[0][-1] == "Stock note" and all(len(r) == len(tpl[0]) for r in tpl))
    page.evaluate("""() => { const t = 'Name;Stock note\\nCsv note test;two bottles, one nearly empty\\n';
        const pc = parseCsv(t); applyCsvImport(pc, csvAutoMap(pc.header)); }"""); page.wait_for_timeout(400)
    check("de CSV-invoer leest de kolom Stock note", M("Csv note test", "m.stockNote") == "two bottles, one nearly empty")

    # ---------- 37: Purchase vraagt de aankoopdatum ----------
    open_m("Geraniol")
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.purchaseDate = '2025-11-03'; STOCKOPEN = true; render(); }")
    page.wait_for_timeout(300)
    vul("#stBuyAmt", "50"); klik("#btnBuy"); page.wait_for_timeout(300)
    h = txt("#dlg h3")
    check(f"na Add het venster Purchase date, met de kalender op vandaag en No change ({h!r}, {val('#pdDate')!r}, {txt('#dlgCancel')!r})",
          dlg_open() and h == "Purchase date" and val("#pdDate") == today and txt("#dlgCancel") == "No change" and txt("#dlgOk") == "Set date"
          and "2025-11-03" in txt("#dlg .hint"))
    esc()
    got = M("Geraniol", "[m.purchaseDate, m.stockEvents.at(-1).t, m.stockEvents.at(-1).date]")
    check(f"No change (Escape) laat de aankoopdatum staan; de aankoop staat op vandaag ({got})", got == ["2025-11-03", "buy", today])
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo neemt de aankoop terug", M("Geraniol", "m.stockEvents.length") == 1)
    yday = page.evaluate("() => { const d = new Date(Date.now() - 86400000); return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`; }")
    vul("#stBuyAmt", "50"); klik("#btnBuy"); page.wait_for_timeout(300)
    vul("#pdDate", yday); klik("#dlgOk"); page.wait_for_timeout(300)
    got = M("Geraniol", "[m.purchaseDate, m.stockEvents.at(-1).date]")
    check(f"Set date zet de aankoopdatum en dateert de aankoop ({got})", got == [yday, yday])
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    got = M("Geraniol", "[m.purchaseDate, m.stockEvents.length]")
    check(f"één Undo voor de aankoop en de datum ({got})", got == ["2025-11-03", 1])
    # een eerste aankoop: de start van het volgen krijgt dezelfde datum
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.stockEvents = []; render(); }"); page.wait_for_timeout(200)
    vul("#stBuyAmt", "30"); klik("#btnBuy"); page.wait_for_timeout(300)
    vul("#pdDate", yday); klik("#dlgOk"); page.wait_for_timeout(300)
    got = M("Geraniol", "m.stockEvents.map(e => [e.t, e.date])")
    check(f"bij een eerste aankoop ook de start van het volgen ({got})", got == [["take", yday], ["buy", yday]])
    # geen venster als de datum leeg is of al vandaag zegt
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.purchaseDate = ''; render(); }"); page.wait_for_timeout(200)
    vul("#stBuyAmt", "10"); klik("#btnBuy"); page.wait_for_timeout(300)
    check("een lege aankoopdatum wordt meteen vandaag, zonder venster", not dlg_open() and M("Geraniol", "m.purchaseDate") == today)
    vul("#stBuyAmt", "10"); klik("#btnBuy"); page.wait_for_timeout(300)
    check("staat ze al op vandaag, dan geen venster", not dlg_open())

    check(f"geen fouten in de pagina ({errs[:2]})", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
