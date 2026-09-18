"""Terug en vooruit door de geschiedenis van de browser (bouw 260915m): elke plaats is een stap, zodat de
zijknoppen van de muis, de browserknoppen, Alt+Links en de Android-terugknop werken. Playwright kan de
zijknoppen van een muis niet sturen (alleen links, rechts en midden); go_back() en go_forward() doen wat die
knoppen in de browser doen, dus dat is wat hier getest wordt.
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

    # een formule met twee versies, dan een materiaal, dan To order
    page.click("#list .item >> nth=0"); page.wait_for_timeout(500)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    f = plek(page)
    check(f"de formule staat open op versie 2 ({f})", f["tab"] == "F" and f["id"] and f["sub"] == 1)

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
    check("en de versie waar je stond", p2["sub"] == 1)

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

    # de schuifpositie volgt de plaats ook bij terug
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
    check(f"terug naar de formule begint bovenaan ({nu}, je stond op {diep})", nu == 0)

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

    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
