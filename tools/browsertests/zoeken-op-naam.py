"""Bouw 261012a: zoeken in de lijsten als één lijst op naam, en de versie als tekst in de bench view.
- Materials met een zoekterm: geen categoriegroepen, één lijst op naam: eerst wat op naam, alternatieve naam of leverancier
  treft, dan onder "In descriptions ✎ (N)" wat alleen in de beschrijving treft (elk met ✎), helemaal onderaan wat de
  library nog kent. De regel "N match(es) in descriptions ✎" bovenaan is weg. Een rij opent zoals voordien.
- Formulas met een zoekterm: ook één lijst op naam, de categorie in het grijze regeltje in de plaats van het aantal
  versies (lang: afgekapt met …); de tooltip geeft de volledige categorie en het aantal versies. Sinds 261015a houdt een
  formule zonder categorie haar aantal versies (audit v3, E9).
- Zonder zoekterm: de groepen zoals voordien, en in Formulas geen categorie in het regeltje.
- De bench view noemt de versie die open is als gewone tekst, met dezelfde woorden als de keuzelijst van de tabel; zonder
  keuzelijst of knoppen.
- Op een telefoon past een lange categorie in de rij.
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, re, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

LANG = "Zeep, shampoo en andere dingen voor in de badkamer"
LIB = {"type": "miformulas-materials", "name": "Zoeken op naam", "version": "2026-10-12", "licence": "CC BY 4.0",
       "materials": [{"name": "Zoekproef uit de library", "category": "Woody"},
                     {"name": "Alleen in de library", "category": "Woody"}]}

# wat de lijst toont, van boven naar onder: rijen als naam, het kopje van de beschrijvingen en de library als merkers
VOLGORDE = """() => [...document.querySelectorAll('#list > *')].map(e => {
  if (e.classList.contains('item')){ const id = e.dataset.id, x = DATA.materials.find(m => m.id === id) || DATA.formulas.find(f => f.id === id);
    return (x ? x.name : '?') + (e.textContent.includes('✎') ? ' ✎' : ''); }
  if (e.classList.contains('cat')) return 'CAT ' + e.textContent.trim().replace(/\\s+/g, ' ');
  if (e.classList.contains('sugRow')) return 'LIB ' + e.querySelector('button').dataset.add;
  return 'HINT ' + e.textContent.trim(); })"""

def open_f(page, naam, bench=False, idx=1):
    page.evaluate("([n, b, i]) => { HOMEVIEW = false; const f = DATA.formulas.find(f => f.name === n); switchTab('F', f.id, {type: 'v', idx: Math.min(i, f.versions.length - 1), bench: b}); }", [naam, bench, idx])
    page.wait_for_timeout(350)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    c = b.new_context(viewport={"width": 1400, "height": 900}, locale="en-GB")
    page = c.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)

    # eigen materialen en formules: de volgorde op categorie is telkens een andere dan die op naam
    page.evaluate("""() => {
        let n = 0;
        const maak = (naam, extra) => Object.assign({id: "m-zp" + (++n), name: naam, category: "Fruits", pyramid: 2,
            isSolvent: false, cas: "", aliases: "", supplier: "", description: "",
            dilutions: [{pct: 100, isBase: true, date: today(), notes: ""}]}, extra);
        DATA.materials.push(
            maak("Zoekproef Beta", {category: "Aldehydes"}),
            maak("Alfa zoekproef", {category: "Woody"}),
            maak("Midden", {category: "Fruits", aliases: "zoekproef alias"}),
            maak("Kruid", {category: "Herbal - Green", supplier: "Zoekproef BV"}),
            maak("Aardbei", {category: "Fruits", description: "lijkt op een zoekproef"}),
            maak("Yuzu", {category: "Citrus", description: "zoekproef"}));
        invalidateMats();
        const v = (nr, extra) => Object.assign({v: nr, name: "", date: "2026-10-0" + nr, notes: "",
            lines: [{materialId: "m-zp1", dilutionPct: 100, weightG: 1, remark: null}]}, extra);
        DATA.formulas.push(
            {id: "f-zp1", name: "Zoekformule B", category: "Amber", created: today(), modified: now(), frozenImport: false,
             versions: [v(1), v(2, {name: "kort"})]},
            {id: "f-zp2", name: "A zoekformule", category: "Zeep, shampoo en andere dingen voor in de badkamer",
             created: today(), modified: now(), frozenImport: false,
             versions: [v(1, {name: "uit Formulair", sourceName: "Bron v01", imported: true}), v(2), v(3, {name: "derde"})]},
            {id: "f-zp3", name: "Zoekformule met een heel lange naam over twee regels", category: "Amber", created: today(),
             modified: now(), frozenImport: false, versions: [v(1)]});
        for (const c of ["Amber", "Zeep, shampoo en andere dingen voor in de badkamer"])
            if (!DATA.formulaCategories.includes(c)) DATA.formulaCategories.push(c);
        render(); }""")
    page.wait_for_timeout(300)

    f = os.path.join(tempfile.mkdtemp(), "zoeken-op-naam.json")
    open(f, "w", encoding="utf-8").write(json.dumps(LIB))
    page.click("#btnHome"); page.wait_for_timeout(400)
    page.set_input_files("#impList", f); page.wait_for_timeout(800)

    def zoek(term, tab="M"):
        page.click("#tab" + tab); page.wait_for_timeout(250)
        page.fill("#searchBox", term); page.wait_for_timeout(400)
        return page.evaluate(VOLGORDE)

    # ---------- Materials ----------
    r = zoek("zoekproef")
    check(f"Materials met een zoekterm: geen categoriegroepen ({[x for x in r if x.startswith('CAT')]})",
          not any(x.startswith("CAT") for x in r))
    check(f"eerst naam, alternatieve naam en leverancier op naam, dan het kopje, dan de beschrijvingen op naam, dan de library ({r})",
          r == ["Alfa zoekproef", "Kruid", "Midden", "Zoekproef Beta", "HINT In descriptions ✎ (2)", "Aardbei ✎", "Yuzu ✎",
                "HINT Also in the materials library:", "LIB Zoekproef uit de library"])
    check("de regel 'match(es) in descriptions' bovenaan is weg", "match(es)" not in page.text_content("#list"))
    kop = page.evaluate("() => { const k = document.querySelector('#descHead'); return k && [k.textContent.trim(), getComputedStyle(k).position]; }")
    check(f"het kopje heeft een id en blijft niet plakken zoals een categorie ({kop})",
          bool(kop) and kop[0] == "In descriptions ✎ (2)" and kop[1] != "sticky")
    r = zoek("lijkt op")
    check(f"alleen beschrijvingen: het kopje en de rij, zonder iets erboven ({r})",
          r == ["HINT In descriptions ✎ (1)", "Aardbei ✎"])
    r = zoek("alleen in de library")
    check(f"niets van jezelf: alleen wat de library kent, met de oude woorden ({r})",
          r == ["HINT Not in your inventory. In the materials library:", "LIB Alleen in de library"])
    r = zoek("alfa zoekproef")
    check(f"een naam in twee woorden: één treffer, geen kopje ({r})", r == ["Alfa zoekproef"])
    zoek("zoekproef")
    page.locator("#list .item", has_text="Yuzu").click(); page.wait_for_timeout(400)
    sel = page.evaluate("() => [document.querySelector('#content h2')?.textContent.trim(), [...document.querySelectorAll('#list .item.sel')].map(e => e.dataset.id)]")
    check(f"een rij onder de beschrijvingen opent het materiaal en staat geselecteerd ({sel})",
          sel[0] and sel[0].startswith("Yuzu") and sel[1] == ["m-zp6"])
    r = zoek("")
    check(f"zonder zoekterm: de groepen zoals voordien ({[x for x in r if x.startswith('CAT')][:4]})",
          sum(x.startswith("CAT") for x in r) >= 5 and not any(x.startswith("HINT") for x in r))

    # ---------- Formulas ----------
    r = zoek("zoekformule", "F")
    check(f"Formulas met een zoekterm: geen groepen, één lijst op naam ({r})",
          r == ["A zoekformule", "Zoekformule B", "Zoekformule met een heel lange naam over twee regels"])
    subs = page.evaluate("""() => [...document.querySelectorAll('#list .item .sub')].map(s => [s.textContent.trim(), s.className, s.title,
        s.scrollWidth > s.clientWidth + 1, Math.round(s.getBoundingClientRect().width / s.closest('.item').getBoundingClientRect().width * 100)])""")
    check(f"de categorie in het grijze regeltje, in de plaats van het aantal versies ({[s[0] for s in subs]})",
          len(subs) == 3 and subs[0][0] == LANG and subs[1][0] == "Amber" and subs[2][0] == "Amber")
    check(f"de tooltip: de volledige categorie en het aantal versies ({[s[2] for s in subs]})",
          [s[2] for s in subs] == [LANG + " · 3 versions", "Amber · 2 versions", "Amber · 1 version"])
    check(f"een lange categorie wordt afgekapt en laat de naam ruimte ({subs[0][3:]})",
          len(subs) == 3 and subs[0][3] and subs[0][4] <= 51 and "fcat" in subs[0][1])
    check(f"een korte categorie wordt niet afgekapt, ook niet naast een lange naam die over twee regels loopt ({[x[3:] for x in subs[1:]]})",
          len(subs) == 3 and not subs[1][3] and not subs[2][3])
    lijn = page.evaluate("""() => { const r = [...document.querySelectorAll('#list .item')][0]; const n = r.firstElementChild, s = r.querySelector('.sub');
        const rn = document.createRange(); rn.selectNodeContents(n); const rs = document.createRange(); rs.selectNodeContents(s);
        return Math.abs(rn.getClientRects()[0].bottom - rs.getClientRects()[0].bottom); }""")
    check(f"het afgekapte regeltje staat op de lijn van de naam ({lijn:.1f} px)", lijn < 3)
    r = zoek("starter", "F")
    sub = page.evaluate("() => document.querySelector('#list .item .sub')?.textContent.trim()")
    opnaam = page.evaluate("r => JSON.stringify(r) === JSON.stringify([...r].sort((a, b) => a.localeCompare(b)))", r)
    # sinds 261015a houdt een formule zonder categorie haar aantal versies (audit v3, E9)
    check(f"'starter' in Formulas: één lijst op naam, zonder categorie het aantal versies, en starter in het regeltje ({sub})",
          not any(x.startswith("CAT") for x in r) and len(r) >= 10 and opnaam
          and re.fullmatch(r"\d+ versions? · starter", sub or ""))
    r = zoek("", "F")
    subs = page.evaluate("() => [...document.querySelectorAll('#list .item .sub')].map(s => [s.textContent.trim(), s.className])")
    check(f"zonder zoekterm: de groepen, en het regeltje zonder categorie ({subs[:2]})",
          sum(x.startswith("CAT") for x in r) >= 3 and all(s[1] == "sub" and not s[0].startswith(("Amber", "Uncategorised")) for s in subs))

    # ---------- de bench view ----------
    for naam, idx, verwacht in [("A zoekformule", 0, "v1 uit Formulair (2026-10-01): Bron v01 🔒"),
                                ("A zoekformule", 2, "v3 derde (2026-10-03)"), ("Zoekformule B", 1, "v2 kort (2026-10-02)")]:
        open_f(page, naam, False, idx)
        keuze = page.evaluate("() => { const s = document.querySelector('#verSel'); return s && s.options[s.selectedIndex].textContent; }")
        page.click("#btnBenchToggle"); page.wait_for_timeout(400)
        bank = page.evaluate("""() => { const r = document.querySelector('#benchVer'); if (!r) return null;
            return [null, r.textContent, r.querySelectorAll('select,button,input').length,   // since 261019a the text alone, in the head
                    !!document.querySelector('#verSel'), !!document.querySelector('#fCatDd'), !!document.querySelector('.benchWrap')]; }""")
        check(f"de bench view noemt {verwacht}: de woorden van de keuzelijst ({keuze!r}), zonder keuzelijst of knoppen ({bank})",
              bool(bank) and bank[1] == verwacht == keuze and bank[2] == 0
              and not bank[3] and not bank[4] and bank[5])
        page.click("#btnBenchToggle"); page.wait_for_timeout(400)
        check(f"Table view: de keuzelijst terug, de tekstregel weg ({naam} v{idx + 1})",
              page.locator("#verSel").count() == 1 and page.locator("#benchVer").count() == 0)
    open_f(page, "A zoekformule", True, 1)
    pos = page.evaluate("""() => { const v = document.querySelector('#benchVer'), w = document.querySelector('.benchWrap');
        if (!v || !w) return [false, false];   // een bouw van vóór 261012a
        const r = v.getBoundingClientRect(); return [r.bottom <= w.getBoundingClientRect().top + 1, r.height < 40]; }""")
    check(f"de regel staat boven de bank, op één lijn ({pos})", all(pos))

    # ---------- een telefoon ----------
    page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(300)
    page.evaluate("() => { HOMEVIEW = false; switchTab('F', null); }"); page.wait_for_timeout(400)   # de lijst, zonder open pagina
    page.fill("#searchBox", "zoekformule"); page.wait_for_timeout(400)
    past = page.evaluate("""() => [...document.querySelectorAll('#list .item')].map(r => [r.scrollWidth <= r.clientWidth + 1,
        r.getBoundingClientRect().right <= innerWidth + 1])""")
    check(f"op een telefoon past een lange categorie in de rij ({past})", len(past) == 3 and all(all(x) for x in past))
    check(f"geen fouten in de pagina ({errs[:2]})", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
