"""De zoekterm per lijst (Formulas, Materials, To order) en de schuifpositie van het paneel (bouw 260915l).
Vereist de lokale webserver op poort 8765, zie README."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def term(page): return page.input_value("#searchBox")
def rijen(page): return page.locator("#list .item").count()
def top(page): return page.evaluate("document.querySelector('#content').scrollTop")

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 800})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # ---------- de zoekterm hoort bij de lijst ----------
    page.click("#tabM"); page.wait_for_timeout(300)
    alle_m = rijen(page)
    page.fill("#searchBox", "vetiver"); page.wait_for_timeout(400)
    m_hits = rijen(page)
    check(f"Materials filtert op de term ({m_hits} van {alle_m})", 0 < m_hits < alle_m)

    page.click("#tabF"); page.wait_for_timeout(400)
    check(f"de term blijft niet staan in Formulas ({term(page)!r})", term(page) == "")
    alle_f = rijen(page)
    check("Formulas toont weer alles", alle_f > 0)

    page.fill("#searchBox", "acqua"); page.wait_for_timeout(400)
    f_hits = rijen(page)
    check(f"Formulas filtert op zijn eigen term ({f_hits} van {alle_f})", 0 < f_hits < alle_f)

    page.click("#tabM"); page.wait_for_timeout(400)
    check(f"Materials krijgt zijn eigen term terug ({term(page)!r})", term(page) == "vetiver")
    check("en toont weer dezelfde treffers", rijen(page) == m_hits)

    page.click("#tabT"); page.wait_for_timeout(400)
    check(f"To order begint zonder term ({term(page)!r})", term(page) == "")
    page.fill("#searchBox", "zzz-bestaat-niet"); page.wait_for_timeout(400)

    page.click("#tabF"); page.wait_for_timeout(400)
    check(f"Formulas heeft nog zijn term ({term(page)!r})", term(page) == "acqua")
    check("en nog zijn treffers", rijen(page) == f_hits)
    page.click("#tabT"); page.wait_for_timeout(400)
    check(f"To order houdt de zijne ({term(page)!r})", term(page) == "zzz-bestaat-niet")

    # leegmaken hoort ook onthouden te worden
    page.fill("#searchBox", ""); page.wait_for_timeout(300)
    page.click("#tabM"); page.wait_for_timeout(400)
    page.click("#tabT"); page.wait_for_timeout(400)
    check(f"een leeggemaakte term blijft leeg ({term(page)!r})", term(page) == "")

    # Home wisselt van lijst zonder switchTab: ook daar hoort de term te volgen
    page.click("#tabM"); page.wait_for_timeout(400)
    check("Materials heeft zijn term nog", term(page) == "vetiver")
    page.click("#btnHome"); page.wait_for_timeout(500)
    check(f"Home landt op Formulas met de term van Formulas ({term(page)!r})", term(page) == "acqua")
    page.fill("#searchBox", ""); page.wait_for_timeout(300)
    page.click("#tabM"); page.fill("#searchBox", ""); page.wait_for_timeout(400)

    # ---------- een ander item begint bovenaan ----------
    page.click("#tabF"); page.wait_for_timeout(300)
    # een formule met genoeg regels om te kunnen schuiven
    page.evaluate("""() => { const f = [...DATA.formulas].sort((a,b) =>
        b.versions[b.versions.length-1].lines.length - a.versions[a.versions.length-1].lines.length)[0];
        switchTab('F', f.id, {type:'v', idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(700)
    page.evaluate("() => { const c = document.querySelector('#content'); c.scrollTop = c.scrollHeight; }")
    page.wait_for_timeout(300)
    diep = top(page)
    check(f"de formulepagina is te schuiven ({diep} px)", diep > 100)

    # een re-render van dezelfde pagina laat de plek staan
    page.evaluate("() => { render(); }"); page.wait_for_timeout(400)
    check(f"een re-render houdt de leespositie ({top(page)} px)", top(page) == diep)

    # op een materiaal onderaan de formule klikken
    naam = page.evaluate("""() => { const links = [...document.querySelectorAll('#content .matlink[data-mat]')];
        const a = links[links.length - 1]; a.click(); return a.textContent.trim(); }""")
    page.wait_for_timeout(700)
    check(f"het materiaal {naam!r} is geopend", page.evaluate("VIEW.tab") == "M" and page.evaluate("!!VIEW.id"))
    check(f"en het staat bovenaan ({top(page)} px)", top(page) == 0)

    # en terug naar een formule vanuit de gebruikslijst onderaan de materiaalpagina
    page.evaluate("""() => { const n = {};
        DATA.formulas.forEach(f => f.versions.forEach(v => v.lines.forEach(l =>
          n[l.materialId] = (n[l.materialId] || 0) + 1)));
        const id = Object.keys(n).sort((a,b) => n[b] - n[a])[0];
        switchTab('M', id, null); }""")
    page.wait_for_timeout(700)
    page.evaluate("() => { const c = document.querySelector('#content'); c.scrollTop = c.scrollHeight; }")
    page.wait_for_timeout(300)
    check(f"de materiaalpagina van een veelgebruikt materiaal is te schuiven ({top(page)} px)", top(page) > 100)
    page.click("#content .usage a[data-go] >> nth=0"); page.wait_for_timeout(800)
    check("een klik in de gebruikslijst opent de formule", page.evaluate("VIEW.tab") == "F")
    check(f"en die begint ook bovenaan ({top(page)} px)", top(page) == 0)

    # ---------- de handleiding ----------
    page.evaluate("""() => { const f = DATA.formulas[0]; switchTab('F', f.id, {type:'v', idx:0}); }""")
    page.wait_for_timeout(600)
    page.evaluate("() => { const c = document.querySelector('#content'); c.scrollTop = 200; }")
    page.wait_for_timeout(200)
    page.click("#btnHelp"); page.wait_for_timeout(800)
    check(f"de handleiding begint bovenaan ({top(page)} px)", top(page) == 0)
    page.evaluate("() => { const c = document.querySelector('#content'); c.scrollTop = 1200; }")
    page.wait_for_timeout(300)
    diep_help = top(page)
    page.evaluate("() => { render(); }"); page.wait_for_timeout(400)
    check(f"een re-render in de handleiding houdt de leespositie ({top(page)} van {diep_help})", top(page) == diep_help)
    page.click("#helpClose"); page.wait_for_timeout(700)
    check(f"en de formule staat daarna weer bovenaan ({top(page)} px)", top(page) == 0)

    check(f"geen paginafouten ({errs[:2]})", not errs)
    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
