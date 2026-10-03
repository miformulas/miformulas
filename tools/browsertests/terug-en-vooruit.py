"""Terug en vooruit door de geschiedenis van de browser (bouw 260915m): elke plaats is een stap, zodat de
zijknoppen van de muis, de browserknoppen, Alt+Links en de Android-terugknop werken. Playwright kan de
zijknoppen van een muis niet sturen (alleen links, rechts en midden); go_back() en go_forward() doen wat die
knoppen in de browser doen, dus dat is wat hier getest wordt. Sinds 260922j neemt een stap ook de vergelijking en de
bench view mee (C-a 7). Sinds 260922p is een formule die je uit de lijst opent meteen de plaats met haar versie, zodat
Bench view of een gewicht daarna geen tweede stap is en één keer terug de formule verlaat (C5 van de mini-audit op 260922m).
Sinds 261004a onthoudt een stap ook hoe ver de pagina naar beneden stond toen je wegklikte, zodat terug in een lange formule
op dezelfde regel landt en niet bovenaan; alleen een klik schrijft die positie (keuze A van Mathieu), dus een pagina die je met
terug verliet, begint bij vooruit bovenaan.
Vereist de lokale webserver op poort 8765, zie README."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def plek(page):
    return page.evaluate("() => ({tab: VIEW.tab, id: VIEW.id, sub: VIEW.sub && VIEW.sub.idx, help: HELPVIEW, home: HOMEVIEW})")

with sync_playwright() as b0:
    b = b0.chromium.launch()

    # ---------------- gewoon tabblad ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 850})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    check("de twee knoppen zijn verborgen in een tabblad",
          page.locator("#btnNavPrev").count() == 1 and not page.locator("#btnNavPrev").is_visible())

    # een formule met een nieuwe versie (de starterformules hebben er al twee), dan een materiaal, dan To order
    page.click("#list .item >> nth=0"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    f = plek(page)
    check(f"de formule staat open op versie 3 ({f})", f["tab"] == "F" and f["id"] and f["sub"] == 2)

    mid = page.evaluate("DATA.materials[5].id")
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(600)
    page.evaluate("() => switchTab('T')"); page.wait_for_timeout(600)
    check("To order staat open", plek(page)["tab"] == "T")

    page.go_back(); page.wait_for_timeout(700)
    p1 = plek(page)
    check(f"terug geeft het materiaal ({p1})", p1["tab"] == "M" and p1["id"] == mid)
    page.go_back(); page.wait_for_timeout(700)
    p2 = plek(page)
    check(f"nog eens terug geeft de formule ({p2})", p2["tab"] == "F" and p2["id"] == f["id"])
    check("en de versie waar je stond", p2["sub"] == 2)

    page.go_forward(); page.wait_for_timeout(700)
    check("vooruit geeft het materiaal weer", plek(page)["id"] == mid)
    page.go_forward(); page.wait_for_timeout(700)
    check("en nog eens vooruit geeft To order", plek(page)["tab"] == "T")

    # de handleiding is ook een plaats
    page.go_back(); page.wait_for_timeout(600)
    page.click("#btnHelp"); page.wait_for_timeout(800)
    check("de handleiding staat open", plek(page)["help"] is True)
    page.go_back(); page.wait_for_timeout(700)
    check(f"terug sluit de handleiding en geeft het materiaal ({plek(page)})",
          plek(page)["help"] is False and plek(page)["id"] == mid)

    # een verdwenen formule wordt overgeslagen, zonder fout
    page.evaluate("id => switchTab('F', id, {type:'v', idx:0})", f["id"]); page.wait_for_timeout(600)
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(600)
    page.evaluate("""id => { DATA.formulas = DATA.formulas.filter(x => x.id !== id); buildUsage(); }""", f["id"])
    page.wait_for_timeout(300)
    page.go_back(); page.wait_for_timeout(700)
    p3 = plek(page)
    check(f"terug naar een verwijderde formule geeft de lijst ({p3})", p3["tab"] == "F" and p3["id"] is None)
    check(f"zonder paginafout ({errs[:2]})", not errs)

    # de schuifpositie volgt de plaats ook bij terug: sinds 261004a de positie waar je wegklikte (tot dan bovenaan)
    page.evaluate("""() => { const f = [...DATA.formulas].sort((a,b) =>
        b.versions[b.versions.length-1].lines.length - a.versions[a.versions.length-1].lines.length)[0];
        switchTab('F', f.id, {type:'v', idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(700)
    page.evaluate("() => { const c = document.querySelector('#content'); c.scrollTop = c.scrollHeight; }")
    page.wait_for_timeout(300)
    diep = page.evaluate("document.querySelector('#content').scrollTop")
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(700)
    page.go_back(); page.wait_for_timeout(800)
    nu = page.evaluate("document.querySelector('#content').scrollTop")
    check(f"terug naar de formule landt waar je stond ({nu}, je stond op {diep})", diep > 0 and nu == diep)

    # bouw 260922j (C-a 7): terug naar een vergelijking of naar de bench view landt daar weer, niet op de tabel
    # van de laatste versie; de stap onthoudt ook wat je er nadien koos (B in Compare, de bench aan of uit)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions.length < 3 && !x.frozenImport);
        while (f.versions.length < 3) f.versions.push({v: f.versions.length + 1, date: today(), lines: f.versions[0].lines.map(l => ({...l}))});
        buildUsage(); switchTab("F", f.id, {type: "v", idx: 1}); }""")
    page.wait_for_timeout(700)
    page.click("#btnCmp"); page.wait_for_timeout(600)
    page.select_option("#cmpB", "v2"); page.wait_for_timeout(500)
    voor = page.evaluate("() => JSON.stringify(VIEW.sub)")
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(600)
    page.go_back(); page.wait_for_timeout(800)
    na = page.evaluate("() => ({sub: VIEW.sub, cmp: !!document.querySelector('#btnCmpClose')})")
    check(f"terug naar een vergelijking geeft die vergelijking ({voor} → {na})",
          na["cmp"] and (na["sub"] or {}).get("type") == "cmp" and (na["sub"] or {}).get("b") == "v2")
    if page.locator("#btnCmpClose").count():
        page.click("#btnCmpClose"); page.wait_for_timeout(600)
    check(f"en Close compare brengt je terug waar je ze opende ({plek(page)})", plek(page)["sub"] == 1)
    page.click("#btnBenchToggle"); page.wait_for_timeout(600)
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(600)
    page.go_back(); page.wait_for_timeout(800)
    na = page.evaluate("() => ({sub: VIEW.sub, bench: !!document.querySelector('.benchArea')})")
    check(f"terug naar de bench view geeft de bench view ({na})",
          na["bench"] and (na["sub"] or {}).get("idx") == 1 and (na["sub"] or {}).get("bench") is True)
    if page.locator(".benchArea").count():
        page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    check(f"zonder paginafout ({errs[:2]})", not errs)

    # 260922p (C5): uit de lijst geopend, dan Bench view en een gewicht: dat is één plaats, en één keer terug verlaat ze
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(600)
    page.evaluate("() => switchTab('F', null, null)"); page.wait_for_timeout(600)
    page.click("#list .item >> nth=1"); page.wait_for_timeout(700)
    fid, n0 = page.evaluate("VIEW.id"), page.evaluate("NAVI")
    page.click("#btnBenchToggle"); page.wait_for_timeout(600)
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    page.fill("input.w >> nth=0", "7"); page.keyboard.press("Tab"); page.wait_for_timeout(600)
    n1 = page.evaluate("NAVI")
    check(f"260922p (C5): uit de lijst geopend, dan Bench view en een gewicht: geen extra stap ({n0} → {n1})", n1 == n0)
    page.go_back(); page.wait_for_timeout(800)
    check(f"en één keer terug verlaat de formule ({plek(page)})", plek(page)["id"] != fid)
    page.go_forward(); page.wait_for_timeout(800)
    check(f"vooruit geeft haar weer, op de versie die je las ({plek(page)})", plek(page)["id"] == fid and plek(page)["sub"] is not None)

    # een herlaadbeurt volgt de instelling "Open where you left off"
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(700)
    page.evaluate("() => { saveData(); }"); page.wait_for_timeout(800)
    page.reload(); page.wait_for_timeout(1800)
    check(f"met de instelling uit begint een herlaadbeurt bovenaan ({plek(page)})", plek(page)["id"] is None)
    page.evaluate("() => { OPENLAST = true; idb.set('openLast', true); }"); page.wait_for_timeout(400)
    page.evaluate("id => switchTab('M', id, null)", mid); page.wait_for_timeout(900)
    page.evaluate("() => { saveData(); }"); page.wait_for_timeout(800)
    page.reload(); page.wait_for_timeout(1800)
    check(f"met de instelling aan landt ze op dezelfde plek ({plek(page)})",
          plek(page)["tab"] == "M" and plek(page)["id"] == mid)
    ctx.close()

    # ---------------- de geïnstalleerde app ----------------
    ctx = b.new_context(viewport={"width": 1400, "height": 850})
    ctx.add_init_script("Object.defineProperty(navigator, 'standalone', {get: () => true});")
    page = ctx.new_page()
    errs2 = []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)
    check("de geïnstalleerde app toont de twee knoppen",
          page.locator("#btnNavPrev").is_visible() and page.locator("#btnNavNext").is_visible())
    check("bij de start staan ze allebei uit",
          page.locator("#btnNavPrev").is_disabled() and page.locator("#btnNavNext").is_disabled())

    page.click("#list .item >> nth=0"); page.wait_for_timeout(700)
    check("na één stap kan terug wel en vooruit niet",
          not page.locator("#btnNavPrev").is_disabled() and page.locator("#btnNavNext").is_disabled())
    eerste = plek(page)["id"]
    page.click("#btnNavPrev"); page.wait_for_timeout(800)
    check("de terugknop werkt", plek(page)["id"] is None)
    check("en nu kan vooruit wel en terug niet",
          page.locator("#btnNavPrev").is_disabled() and not page.locator("#btnNavNext").is_disabled())
    page.click("#btnNavNext"); page.wait_for_timeout(800)
    check("de vooruitknop brengt de formule terug", plek(page)["id"] == eerste)

    # een nieuwe stap laat wat vooruit lag vallen
    page.click("#btnNavPrev"); page.wait_for_timeout(700)
    page.evaluate("id => switchTab('M', id, null)", page.evaluate("DATA.materials[2].id")); page.wait_for_timeout(800)
    check("een nieuwe stap zet de vooruitknop weer uit", page.locator("#btnNavNext").is_disabled())
    check(f"geen paginafouten in de geïnstalleerde app ({errs2[:2]})", not errs2)

    # bouw 260918d: van versie wisselen is zelf een stap, en terug landt op de versie waar je stond
    page.close()   # een herstart: het vorige venster is dicht (sinds 260922g bewaart in één browser één venster)
    pg3 = ctx.new_page(); pg3.on("dialog", lambda d: d.accept())
    pg3.goto(URL); pg3.wait_for_timeout(1500)
    pg3.evaluate("""() => { const f = DATA.formulas.find(x => x.versions.length > 1) || DATA.formulas[0];
        if (f.versions.length < 2) f.versions.push({v: 2, date: today(), lines: f.versions[0].lines.map(l => ({...l}))});
        window.__fid = f.id; switchTab("F", f.id, {type: "v", idx: 1}); }""")
    pg3.wait_for_timeout(900)
    pg3.evaluate("""() => switchTab("F", window.__fid, {type: "v", idx: 0})""")
    pg3.wait_for_timeout(900)
    check("we kijken naar v1", plek(pg3)["sub"] == 0)
    pg3.evaluate("""() => switchTab("M", DATA.materials[3].id, null)""")
    pg3.wait_for_timeout(900)
    pg3.go_back(); pg3.wait_for_timeout(1000)
    p3 = plek(pg3)
    check(f"terug landt op v1, niet op de laatste versie ({p3})", p3["tab"] == "F" and p3["sub"] == 0)
    pg3.go_back(); pg3.wait_for_timeout(1000)
    p4 = plek(pg3)
    check(f"en nog eens terug geeft de versie die daarvóór openstond ({p4})", p4["sub"] == 1)

    # bouw 260920o: de browser bewaart een vast aantal stappen (Chromium: vijftig) en laat de oudste vallen.
    # NAVI telde door, dus na tachtig plaatsen bleef de terugpijl aan terwijl klikken niets meer deed.
    pg3.close()
    pg4 = ctx.new_page(); pg4.on("dialog", lambda d: d.accept())
    errs4 = []
    pg4.on("pageerror", lambda e: errs4.append(str(e)))
    pg4.goto(URL); pg4.wait_for_timeout(1500)
    pg4.evaluate("""async n => { for (let i = 0; i < n; i++){ switchTab("M", DATA.materials[i].id, null);
        await new Promise(r => setTimeout(r, 15)); } }""", 80)
    pg4.wait_for_timeout(400)
    tel = pg4.evaluate("[NAVI, history.length]")
    check(f"tachtig plaatsen gezet, de browser houdt er vijftig ({tel})", tel[0] == 80 and tel[1] <= 50)
    klikken = 0
    while klikken < 80 and not pg4.locator("#btnNavPrev").is_disabled():
        waar = pg4.evaluate("VIEW.id")
        pg4.click("#btnNavPrev"); pg4.wait_for_timeout(160); klikken += 1
        if pg4.evaluate("VIEW.id") == waar:
            pg4.wait_for_timeout(400)          # niets bewoog: geef de app de tijd om dat te merken
    check(f"de terugpijl gaat uit zodra de browser niets meer heeft ({klikken} klikken, NAVI {pg4.evaluate('NAVI')})",
          pg4.locator("#btnNavPrev").is_disabled() and klikken < 80)
    check(f"de app bleef waar ze was ({pg4.url})", pg4.url.startswith(URL))
    check(f"geen paginafouten aan het einde van de geschiedenis ({errs4[:2]})", not errs4)
    # en de vooruitpijl herstelt zich zodra er weer een stap is
    pg4.evaluate("() => switchTab('M', DATA.materials[0].id, null)"); pg4.wait_for_timeout(500)
    check("een nieuwe stap zet de terugpijl weer aan", not pg4.locator("#btnNavPrev").is_disabled())

    # bouw 260922d: de gok zette NAVI op 0 maar liet de i in de ingang waar de browser op staat ongemoeid,
    # dus een latere popstate haalde die oude index terug: de vooruitpijl ging uit terwijl vooruit kon, en
    # de terugpijl lichtte aan het einde weer op. De ingang draagt nu de teller die we concludeerden.
    def stand(pg):
        return pg.evaluate("""() => ({NAVI, NAVMAX, i: (history.state||{}).i,
            terug: document.querySelector("#btnNavPrev").disabled,
            vooruit: document.querySelector("#btnNavNext").disabled})""")
    pg4.close()
    pg5 = ctx.new_page(); pg5.on("dialog", lambda d: d.accept())
    pg5.goto(URL); pg5.wait_for_timeout(1500)
    pg5.evaluate("""async n => { for (let i = 0; i < n; i++){ switchTab("M", DATA.materials[i].id, null);
        await new Promise(r => setTimeout(r, 15)); } }""", 80)
    pg5.wait_for_timeout(400)
    klikken = 0
    while klikken < 80 and not pg5.locator("#btnNavPrev").is_disabled():
        waar = pg5.evaluate("VIEW.id")
        pg5.click("#btnNavPrev"); pg5.wait_for_timeout(160); klikken += 1
        if pg5.evaluate("VIEW.id") == waar:
            pg5.wait_for_timeout(400)
    eind = stand(pg5)
    check(f"aan het einde draagt de ingang dezelfde teller als de app ({eind})",
          eind["terug"] is True and eind["NAVI"] == 0 and eind["i"] == 0)
    pg5.evaluate("() => switchTab('M', DATA.materials[3].id, null)"); pg5.wait_for_timeout(600)
    na = stand(pg5)
    check(f"een nieuwe stap zet de reeks netjes op één ({na})", na["NAVI"] == 1 and na["NAVMAX"] == 1)
    pg5.click("#btnNavPrev"); pg5.wait_for_timeout(700)
    terug = stand(pg5)
    check(f"en één keer terug laat vooruit gewoon toe ({terug})",
          terug["NAVI"] == 0 and terug["vooruit"] is False and terug["terug"] is True)
    # de terugpijl blijft uit aan het einde: vooruit en weer terug mag hem niet doen oplichten
    pg5.click("#btnNavNext"); pg5.wait_for_timeout(700)
    pg5.click("#btnNavPrev"); pg5.wait_for_timeout(700)
    weer = stand(pg5)
    check(f"vooruit en weer terug laat hem uit ({weer})", weer["terug"] is True)

    # dezelfde ontsporing na een herlaadbeurt: de bewaarde ingangen houden hun oude nummers
    pg5.close()
    pg6 = ctx.new_page(); pg6.on("dialog", lambda d: d.accept())
    pg6.goto(URL); pg6.wait_for_timeout(1500)
    pg6.evaluate("""async n => { for (let i = 0; i < n; i++){ switchTab("M", DATA.materials[i].id, null);
        await new Promise(r => setTimeout(r, 20)); } }""", 5)
    pg6.wait_for_timeout(400)
    pg6.reload(); pg6.wait_for_timeout(1800)
    pg6.go_back(); pg6.wait_for_timeout(900)
    herl = stand(pg6)
    check(f"na een herlaadbeurt blijft vooruit mogelijk na één stap terug ({herl})", herl["vooruit"] is False)

    # ---------------- terug landt waar je was op de pagina (bouw 261004a, keuze A) ----------------
    Y = "document.getElementById('content').scrollTop"
    def klik_materiaal(pg):
        return pg.evaluate("""() => { const c = document.getElementById('content'), r = c.getBoundingClientRect();
            const a = [...c.querySelectorAll('table.lines a.matlink')].find(a => { const q = a.getBoundingClientRect();
                return q.top > r.top + 40 && q.bottom < r.bottom - 40; });
            if (!a) return null; a.click(); return a.textContent; }""")
    def open_f(pg, naam, idx=None):
        pg.evaluate("""([n, i]) => { const f = DATA.formulas.find(x => x.name === n);
            switchTab('F', f.id, i == null ? null : {type: 'v', idx: i}); }""", [naam, idx])
        pg.wait_for_timeout(500)
    def schuif(pg, y):
        pg.evaluate("y => { document.getElementById('content').scrollTop = y; }", y)
    ctx7 = b.new_context(viewport={"width": 1280, "height": 800})
    pg7 = ctx7.new_page(); errs7 = []
    pg7.on("pageerror", lambda e: errs7.append(str(e))); pg7.on("dialog", lambda d: d.accept())
    pg7.goto(URL); pg7.wait_for_timeout(800); pg7.click("#btnStarter"); pg7.wait_for_timeout(1200)
    open_f(pg7, "1881 for men"); schuif(pg7, 900); pg7.wait_for_timeout(300)
    m = klik_materiaal(pg7); pg7.wait_for_timeout(500)
    st = pg7.evaluate(f"[VIEW.tab, {Y}]")
    check(f"een materiaal uit een lange formule opent bovenaan ({m}, {st})", m and st == ["M", 0])
    pg7.go_back(); pg7.wait_for_timeout(600)
    st = pg7.evaluate(f"[VIEW.tab, {Y}]")
    check(f"terug landt op de plaats in de formule, niet bovenaan ({st})", st == ["F", 900])
    pg7.go_forward(); pg7.wait_for_timeout(600)
    st = pg7.evaluate(f"[VIEW.tab, {Y}]")
    check(f"vooruit naar het materiaal begint bovenaan, want je verliet het met terug ({st})", st == ["M", 0])
    pg7.go_back(); pg7.wait_for_timeout(600)
    st = pg7.evaluate(Y)
    check(f"en terug staat de formule nog op dezelfde plaats ({st})", st == 900)
    schuif(pg7, 700); m = klik_materiaal(pg7); pg7.wait_for_timeout(500)    # meteen klikken, zonder te wachten
    pg7.go_back(); pg7.wait_for_timeout(600)
    st = pg7.evaluate(Y)
    check(f"ook als je meteen na het schuiven klikt ({m}, {st})", st == 700)
    open_f(pg7, "1881 for men"); schuif(pg7, 1200); open_f(pg7, "1881 for men", 0)
    v1 = pg7.evaluate(f"[VIEW.sub && VIEW.sub.idx, {Y}]")
    pg7.go_back(); pg7.wait_for_timeout(600)
    v2 = pg7.evaluate(f"[VIEW.sub && VIEW.sub.idx, {Y}]")
    check(f"een andere versie opent bovenaan, terug staat de vorige versie waar je was ({v1} → {v2})",
          v1 == [0, 0] and v2 == [1, 1200])
    klik_materiaal(pg7); pg7.wait_for_timeout(500)
    pg7.evaluate("navStep(-1)"); pg7.wait_for_timeout(700)                  # de pijl terug van de geïnstalleerde app
    st = pg7.evaluate(Y)
    check(f"de pijl terug van de geïnstalleerde app landt ook waar je was ({st})", st == 1200)
    check(f"geen paginafouten ({errs7[:2]})", not errs7)
    ctx7.close()
    ctx8 = b.new_context(viewport={"width": 390, "height": 844})               # een telefoon: hetzelfde paneel schuift
    pg8 = ctx8.new_page()
    pg8.on("dialog", lambda d: d.accept())
    pg8.goto(URL); pg8.wait_for_timeout(800); pg8.click("#btnStarter"); pg8.wait_for_timeout(1200)
    open_f(pg8, "1881 for men"); schuif(pg8, 1500); pg8.wait_for_timeout(300)
    y8 = pg8.evaluate(Y); klik_materiaal(pg8); pg8.wait_for_timeout(500)
    pg8.go_back(); pg8.wait_for_timeout(600)
    st = pg8.evaluate(Y)
    check(f"op een telefoon landt terug ook waar je was ({y8} → {st})", y8 > 1000 and st == y8)
    ctx8.close()

    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
