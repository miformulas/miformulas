"""Bouw 261014a: ronde 2 van de audit v3, de kleine punten in de nieuwe code (op bouw 261013a). Faalt op 261013a.
C1  Preserve weight is vooraf gekozen in de versie waarin de regel met Add line kwam, niet meer in een volgende versie.
C2  + New category met twee spaties op de formulepagina, de materiaalpagina en in Classify several…: één spatie.
C3  Een datum met het toetsenbord typen (dilutie en Purchase date) is één Undo-stap, en Undo zet de oude datum terug.
C4  Enter in het zoekveld van Classify several…, Browse the library… en Export my inventory as a library… drukt niets.
C5  Een treffer op alternatieve naam, CAS of leverancier toont in het grijze regeltje wat er trof; een naamtreffer niet.
C6  Classify several… op 320×568: Pyramid boven de knoppen; op 360 px breekt geen naam.
C7  De categorierij: op 320 px geen horizontale schuif op de materiaalpagina; op 820 px met de lijst open blijft
    + New category naast de keuzelijst van de formule.
C8  Settings met de library: de bron in woorden is de tooltip van de attributie, niet meer vier regels tekst.
C9  Een pijltje in Category op de formulepagina: de keuzelijst houdt de focus.
C10 migrate: Predils en Predilutions worden Premixes, met hun kleur. C16: een kleur die geen #RRGGBB is, valt weg, ook bij
    de Formulair-import.
C12 Download anyway in Settings (een browser zonder bestandstoegang): daarna de melding waar het bestand staat.
C13 Check for updates zonder antwoord geeft na 20 s op; C14 een antwoord dat de app niet is, krijgt een eigen melding.
Vereist de lokale webserver op poort 8765 (zie README); C13 en C14 via file:// (public\\index.html). Duurt ruim een minuut."""
import json, os, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
GEPUB = os.path.join(PUB, "..", "miformulas-materials.json")
ANDROID_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"
NO_FS = "delete window.showOpenFilePicker; delete window.showSaveFilePicker;"
KLEIN = {"type": "miformulas-materials", "name": "Proeflibrary", "version": "1", "licence": "CC BY 4.0",
         "attribution": "Proeflibrary, https://example.com",
         "source": "Compiled by the author from his own inventory: facts only. IFRA limits can be wrong or out of date.",
         "materials": [{"name": "Ambroxide", "aliases": ["Ambroxan"], "cas": "6790-58-5", "category": "Amber", "pyramid": 4},
                       {"name": "Ionone beta", "cas": "14901-07-6", "category": "Flowers - violet", "pyramid": 2}]}
LIB = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else KLEIN

ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def pagina(b, url=URL, starter=True, init=None, **kw):
    ctx = b.new_context(viewport=kw.pop("viewport", {"width": 1280, "height": 900}), accept_downloads=True, **kw)
    ctx.set_default_timeout(8000)
    p = ctx.new_page(); p.msgs = []; p.errs = []; p.antwoord = None
    def dlg(d):
        p.msgs.append(d.message)
        d.accept(p.antwoord if d.type == "prompt" and p.antwoord is not None else "") if d.type == "prompt" else d.accept()
    p.on("dialog", dlg)
    p.on("pageerror", lambda e: p.errs.append(str(e)))
    if init: p.add_init_script(init)
    p.goto(url); p.wait_for_timeout(700)
    if starter:
        p.click("#btnStarter"); p.wait_for_timeout(1200)
    return ctx, p

def open_f(p, naam, idx=None):
    fid = p.evaluate("n => DATA.formulas.find(x => x.name === n).id", naam)
    p.evaluate("([id, idx]) => { HOMEVIEW = false; HELPVIEW = false; const f = DATA.formulas.find(x => x.id === id); switchTab('F', id, {type: 'v', idx: idx == null ? f.versions.length - 1 : idx}); }", [fid, idx])
    p.wait_for_timeout(200)
    return fid

def sluit(p):   # het venster dicht als het nog open staat (op de vorige bouw sloot Enter het al)
    if p.evaluate("$('#dlg').open"): p.click("#dlgCancel")
    p.wait_for_timeout(200)

def open_m(p, mid):
    p.evaluate("id => { HOMEVIEW = false; HELPVIEW = false; switchTab('M', id, null); }", mid); p.wait_for_timeout(200)

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ================= C1, C2, C3, C9 op de starterset =================
    ctx, p = pagina(b)
    p.evaluate("pkg => { setMaterialList(normLibrary(pkg)); }", KLEIN)
    fid = open_f(p, "1881 for men")
    F = f"DATA.formulas.find(x => x.id === {json.dumps(fid)})"
    p.fill("#addMat", "Hedione"); p.press("#addMat", "Enter"); p.wait_for_timeout(300)
    w = p.locator("input.w").last; w.click(); w.fill("2"); p.keyboard.press("Enter"); p.wait_for_timeout(300)
    i = p.evaluate(F + ".versions.at(-1).lines.length - 1")
    p.select_option(f"select.d[data-dil='{i}']", "10"); p.wait_for_timeout(300)
    vers = p.evaluate("$('#dlg').querySelector('input[name=dm]:checked')?.value")
    check(f"C1 in de versie waarin de regel kwam: Preserve weight vooraf ({vers})", vers == "keepw")
    p.click("#dlgCancel"); p.wait_for_timeout(200)
    p.click("#btnNewV"); p.wait_for_timeout(300)
    i = p.evaluate(F + ".versions.at(-1).lines.length - 1")
    p.select_option(f"select.d[data-dil='{i}']", "10"); p.wait_for_timeout(300)
    volg = p.evaluate("$('#dlg').querySelector('input[name=dm]:checked')?.value")
    check(f"C1 in de volgende versie: niet meer Preserve weight vooraf ({volg})", volg not in (None, "keepw"))
    p.click("#dlgCancel"); p.wait_for_timeout(200)

    # C2: + New category met twee spaties
    p.antwoord = "Rose  chypre"; p.click("#btnNewFCat"); p.wait_for_timeout(300)
    cat = p.evaluate(F + ".category")
    check(f"C2 formulepagina: de categorie heet Rose chypre ({cat!r})", cat == "Rose chypre" and p.evaluate("DATA.formulaCategories.includes('Rose chypre')"))
    # C9: een pijltje in Category houdt de focus
    p.focus("#fCat"); c0 = p.evaluate(F + ".category")
    p.keyboard.press("ArrowUp"); p.wait_for_timeout(300)
    c1 = p.evaluate(F + ".category"); act = p.evaluate("document.activeElement && document.activeElement.id")
    check(f"C9 pijl omhoog wisselt de categorie en de keuzelijst houdt de focus ({c0} → {c1}, {act})", c1 != c0 and act == "fCat")
    p.keyboard.press("ArrowDown"); p.wait_for_timeout(300)
    check(f"C9 een tweede pijl wisselt opnieuw ({p.evaluate(F + '.category')})", p.evaluate(F + ".category") != c1)
    mid = p.evaluate("DATA.materials.find(m => m.name === 'Hedione').id")
    open_m(p, mid)
    p.antwoord = "Woody  dry"; p.click("#btnNewMatCat"); p.wait_for_timeout(300)
    mc = p.evaluate("id => DATA.materials.find(m => m.id === id).category", mid)
    check(f"C2 materiaalpagina: de categorie heet Woody dry ({mc!r})", mc == "Woody dry")
    p.click("#ltClassify"); p.wait_for_timeout(300)
    p.antwoord = "Groen  fris"; p.click("#clNewCat"); p.wait_for_timeout(200)
    check(f"C2 Classify several…: Groen fris gekozen ({p.evaluate('$(\"#clCat\").value')!r})", p.evaluate("$('#clCat').value") == "Groen fris")
    # C4: Enter in het zoekveld drukt niets
    p.fill("#clQ", "ionone"); p.msgs.clear(); p.press("#clQ", "Enter"); p.wait_for_timeout(300)
    check(f"C4 Enter in het zoekveld van Classify several…: het venster blijft, geen melding ({p.msgs})",
          p.evaluate("$('#dlg').open") and not p.msgs)
    sluit(p)
    p.evaluate("() => { browseList(); }"); p.wait_for_timeout(300)
    if p.locator("#brQ").count():
        p.fill("#brQ", "ambrox"); p.msgs.clear(); p.press("#brQ", "Enter"); p.wait_for_timeout(300)
        check(f"C4 Enter in het zoekveld van Browse the library…: het venster blijft, geen melding ({p.msgs})", p.evaluate("$('#dlg').open") and not p.msgs)
        sluit(p)
    else:
        check("C4 Browse the library… opent (de starterset heeft een library nodig)", False)
    p.evaluate("() => { exportInventoryLibrary(); }"); p.wait_for_timeout(300)
    p.fill("#exQ", "hedione"); p.msgs.clear(); p.press("#exQ", "Enter"); p.wait_for_timeout(300)
    check(f"C4 Enter in het zoekveld van Export my inventory as a library…: het venster blijft, geen melding ({p.msgs})", p.evaluate("$('#dlg').open") and not p.msgs)
    sluit(p)
    # C3: een datum typen is één Undo-stap
    open_m(p, mid)
    was = p.evaluate("id => DATA.materials.find(m => m.id === id).dilutions[0].date", mid)
    n0 = p.evaluate("UNDO.length")
    p.focus("[data-dildate='0']")
    for ch in "15032025": p.keyboard.press(ch); p.wait_for_timeout(40)
    p.keyboard.press("Tab"); p.wait_for_timeout(200)
    nu = p.evaluate("id => DATA.materials.find(m => m.id === id).dilutions[0].date", mid)
    check(f"C3 de dilutiedatum getypt: 2025, één Undo-stap ({nu}, {p.evaluate('UNDO.length') - n0})", nu.startswith("2025-") and p.evaluate("UNDO.length") - n0 == 1)
    p.evaluate("undo()"); p.wait_for_timeout(200)
    check(f"C3 één Undo zet de oude datum terug ({p.evaluate('id => DATA.materials.find(m => m.id === id).dilutions[0].date', mid)!r})",
          p.evaluate("id => DATA.materials.find(m => m.id === id).dilutions[0].date", mid) == was)
    open_m(p, mid)
    n0 = p.evaluate("UNDO.length")
    p.evaluate("() => { const d = document.querySelector('#mPurchDate').closest('details'); if (d) d.open = true; }")
    p.focus("#mPurchDate")
    for ch in "03022024": p.keyboard.press(ch); p.wait_for_timeout(40)
    p.keyboard.press("Tab"); p.wait_for_timeout(200)
    pd = p.evaluate("id => DATA.materials.find(m => m.id === id).purchaseDate", mid) or ""
    check(f"C3 Purchase date getypt: één Undo-stap ({pd}, {p.evaluate('UNDO.length') - n0})", pd.startswith("2024-") and p.evaluate("UNDO.length") - n0 == 1)
    # Tab blijft in een datumveld (het springt naar dag, maand of jaar): wie het veld verlaat, gaat naar een ander veld
    p.focus("[data-dildate='0']"); p.fill("[data-dildate='0']", "2024-12-24"); p.focus("[data-dilnote='0']"); p.wait_for_timeout(200)
    n1 = p.evaluate("UNDO.length")
    p.focus("[data-dildate='0']"); p.fill("[data-dildate='0']", "2024-12-25"); p.focus("[data-dilnote='0']"); p.wait_for_timeout(200)
    check("C3 een tweede datum na het verlaten van het veld is een eigen stap", p.evaluate("UNDO.length") == n1 + 1)
    check(f"C1-C9 geen paginafouten ({p.errs[:2]})", not p.errs)
    ctx.close()

    # ================= C5: wat de zoeklijst gevonden heeft =================
    ctx, p = pagina(b)
    ids = p.evaluate("""() => { const by = n => DATA.materials.find(m => m.name === n);
        const a = by('Vetiver Oil'), c = DATA.materials.find(m => m.cas && m.cas.length > 6 && !/\\d/.test(m.name)), s = by('Hedione');
        a.aliases = 'Rockrose absolute'; s.supplier = 'Hekserij'; invalidateMats(); render(); return [a.id, c.id, c.cas, s.id]; }""")
    def zoek(term):
        p.evaluate("() => switchTab('M', null, null)"); p.fill("#searchBox", term); p.wait_for_timeout(300)
    def grijs(mid):
        return p.evaluate("""id => { const s = document.querySelector(`#list .item[data-id="${id}"] .sub`);
            return s ? [s.textContent, s.querySelector('span[title]')?.title || ''] : null; }""", mid)
    zoek("rockrose"); g = grijs(ids[0])
    check(f"C5 een treffer op alternatieve naam toont die naam ({g})", g and g[0] == "Rockrose absolute" and g[1] == "found by alternative name")
    zoek(ids[2]); g = grijs(ids[1])
    check(f"C5 een treffer op CAS toont het nummer ({g})", g and g[0] == ids[2] and g[1] == "found by CAS number")
    zoek("hekserij"); g = grijs(ids[3])
    check(f"C5 een treffer op leverancier toont de leverancier ({g})", g and g[0] == "Hekserij" and g[1] == "found by supplier")
    zoek("hedione"); g = grijs(ids[3])
    check(f"C5 een treffer op naam toont wat er altijd stond ({g})", g and g[0] in ("starter", "") and not g[1].startswith("found"))
    ctx.close()

    # ================= C6 en C7 op een telefoon =================
    ctx, p = pagina(b, viewport={"width": 320, "height": 568}, is_mobile=True, has_touch=True, user_agent=ANDROID_UA)
    p.evaluate("() => switchTab('M', null, null)"); p.wait_for_timeout(300)
    p.click("#ltClassify"); p.wait_for_timeout(400)
    m6 = p.evaluate("""() => { const py = document.querySelector('#clPyr').getBoundingClientRect(), ok = document.querySelector('#dlgOk').closest('.toolRow').getBoundingClientRect();
        return [Math.round(py.bottom), Math.round(ok.top)]; }""")
    check(f"C6 op 320×568 staat Pyramid boven de knoppen (onderkant {m6[0]}, knoppen vanaf {m6[1]})", m6[0] <= m6[1])
    p.click("#dlgCancel"); p.wait_for_timeout(200)
    mid = p.evaluate("DATA.materials.find(m => m.name === 'Hedione').id"); open_m(p, mid)
    sw = p.evaluate("() => { const c = document.querySelector('#content'); return [c.scrollWidth, c.clientWidth]; }")
    check(f"C7 de materiaalpagina op 320 px zonder horizontale schuif ({sw})", sw[0] <= sw[1])
    ctx.close()
    ctx, p = pagina(b, viewport={"width": 360, "height": 640}, is_mobile=True, has_touch=True, user_agent=ANDROID_UA)
    p.evaluate("() => switchTab('M', null, null)"); p.wait_for_timeout(300)
    p.click("#ltClassify"); p.wait_for_timeout(400)
    p.fill("#clQ", "ionone"); p.wait_for_timeout(300)
    h = p.evaluate("() => [...document.querySelectorAll('#clRows .brRow')].map(r => [r.children[1].textContent, Math.round(r.children[1].getBoundingClientRect().height)])")
    hoog = [n for n, x in h if x > 26]
    check(f"C6 op 360 px breekt geen naam in Classify several… ({len(h)} rijen, gebroken: {hoog})", h and not hoog)
    ctx.close()
    ctx, p = pagina(b, viewport={"width": 820, "height": 1180})
    p.evaluate("""() => { const f = DATA.formulas.find(x => x.name === '1881 for men'); f.category = 'Leather balsam / parfum';
        if (!DATA.formulaCategories.includes(f.category)) DATA.formulaCategories.push(f.category); render(); }""")
    open_f(p, "1881 for men")
    lijst = p.evaluate("() => { const s = document.querySelector('#sidebar'); return !!s && s.getBoundingClientRect().width > 100; }")
    r7 = p.evaluate("() => { const s = document.querySelector('#fCat').getBoundingClientRect(), n = document.querySelector('#btnNewFCat').getBoundingClientRect(); return [Math.round(s.top), Math.round(n.top), Math.round(n.right), innerWidth]; }")
    check(f"C7 op 820 px met de lijst open ({lijst}): + New category naast de keuzelijst ({r7})", lijst and abs(r7[0] - r7[1]) < 8 and r7[2] <= r7[3])
    ctx.close()

    # ================= C8: Settings op 1366×660 met de library =================
    ctx, p = pagina(b, viewport={"width": 1366, "height": 660})
    p.evaluate("pkg => { setMaterialList(normLibrary(pkg)); render(); }", LIB); p.wait_for_timeout(300)
    p.click("#btnSettings"); p.wait_for_timeout(400)
    cr = p.evaluate("""() => { const d = [...document.querySelectorAll('#dlg .hint')].find(x => /materials library/i.test(x.textContent) && !/^(Materials library|Library):/.test(x.textContent));   // "Library:" sinds 261015a
        return d ? [d.textContent, d.title] : null; }""")
    src = LIB.get("source") or ""
    check(f"C8 de attributie zonder de bron in de tekst, met de bron als tooltip ({cr and cr[0][:60]!r})",
          bool(cr) and src and src not in cr[0] and cr[1] == src)
    print("     Settings op 1366×660:", p.evaluate("() => { const d = document.querySelector('#dlg'); return 'scrollHeight ' + d.scrollHeight + ' op ' + d.clientHeight; }"))
    ctx.close()

    # ================= C10 en C16: migrate en de Formulair-import =================
    ctx, p = pagina(b)
    r = p.evaluate("""() => { const d = migrate({formulas: [{name: 'P', category: 'Predilutions', versions: []}],
        materials: [{name: 'Q', category: 'Predils'}], materialCategories: ['Predils', 'Woody'], formulaCategories: ['Predilutions', 'Uncategorised'],
        categoryColours: {Predils: '#123456', Woody: '#845E3A', Bad: '" onmouseover="window.__x=1', Getal: 5, Kort: '#fff'}});
        return [d.materials[0].category, d.formulas[0].category, d.materialCategories, d.formulaCategories, d.categoryColours]; }""")
    check(f"C10 een Backup uit v2.0: Predils en Predilutions worden Premixes ({r[:4]})",
          r[0] == "Premixes" and r[1] == "Premixes" and "Predils" not in r[2] and "Premixes" in r[2] and "Predilutions" not in r[3] and "Premixes" in r[3])
    check(f"C10 met hun kleur ({r[4]})", r[4].get("Premixes") == "#123456" and "Predils" not in r[4])
    check(f"C16 een kleur die geen #RRGGBB is, valt weg ({sorted(r[4])})", sorted(r[4]) == ["Premixes", "Woody"])
    p.evaluate("() => mergeImport({formulas: [], materials: [], materialCategories: [], formulaCategories: [], categoryColours: {Zz: 'red; background:url(x)', Yy: '#00AA00'}})")
    kl = p.evaluate("[DATA.categoryColours.Zz, DATA.categoryColours.Yy]")
    check(f"C16 de Formulair-import neemt alleen een #RRGGBB over ({kl})", kl[0] is None and kl[1] == "#00AA00")
    ctx.close()

    # ================= C12: Download anyway in Settings =================
    ctx, p = pagina(b, init=NO_FS)
    p.click("#btnSettings"); p.wait_for_timeout(300)
    p.click("#setDownload"); p.wait_for_timeout(300)
    p.msgs.clear()
    with p.expect_download():
        p.click("#dlgOk")
    p.wait_for_timeout(500)
    check(f"C12 na Download anyway zegt een melding waar het bestand staat ({[m[:50] for m in p.msgs]})",
          any("is now in your Downloads folder" in m for m in p.msgs))
    ctx.close()

    # ================= C13 en C14: Check for updates =================
    def update(route, wacht):
        ctx, p = pagina(b, url=APP, starter=False)
        p.route("https://miformulas.com/index.html", route)
        p.click("#btnSettingsLanding"); p.wait_for_timeout(300)
        if not p.locator("#setUpdate").count():
            ctx.close(); return None
        p.msgs.clear(); p.click("#setUpdate"); p.wait_for_timeout(wacht)
        m = list(p.msgs); ctx.close(); return m
    m = update(lambda r: None, 22000)   # geen antwoord
    check(f"C13 zonder antwoord geeft Check for updates na 20 s op ({[x[:60] for x in (m or [])]})",
          m is not None and any("could not be fetched" in x and "connection" in x for x in m))
    m = update(lambda r: r.fulfill(status=200, content_type="text/html", body="<html><title>Hotel wifi</title><p>Log in</p></html>",
               headers={"Access-Control-Allow-Origin": "*"}), 1500)
    check(f"C14 een antwoord dat de app niet is, krijgt een eigen melding ({[x[:60] for x in (m or [])]})",
          m is not None and any("is not the app" in x for x in m) and not any("connection" in x for x in m))

    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
