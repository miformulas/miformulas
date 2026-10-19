"""Bouw 261019a: een rustiger formulepagina (Reddit, 19/10: "the formula creation view could use some focus").
De kop in twee rijen met een menu ⋯, de tick bar pas bij een vinkje, onder de tabel Batch scaling als strook en een menu
Print / export, de vier panelen twee aan twee met gewone titels, de piramide in het paneel van de categorieën.
Draait op de lokale webserver (poort 8765, zie README)."""
import os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

INK, DANGER = "rgb(33, 42, 51)", "rgb(196, 47, 31)"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 660}, accept_downloads=True)
    page = ctx.new_page()
    errs, msgs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.dismiss() if d.type == "prompt" else d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.add_style_tag(content="#storageHint{display:none!important}")
    def open_f(name, idx=None):
        page.evaluate("([n, i]) => { const f = DATA.formulas.find(x => x.name === n); switchTab('F', f.id, {type: 'v', idx: i ?? f.versions.length - 1}); }", [name, idx])
        page.wait_for_timeout(500)
    box = lambda s: page.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return r.width || r.height ? {x: r.x, y: r.y, w: r.width, h: r.height} : null; }", s)
    vis = lambda s: page.locator(s).count() > 0 and page.locator(s).first.is_visible()

    # ---------- 1. de kop in twee rijen ----------
    open_f("Jasmin 231")
    r1 = {s: box(s) for s in ("#content h2", "#verSel", "#btnNameV", "#btnNewV", "#btnCmp", "#btnBenchToggle", "#fMore summary")}
    check(f"eerste rij: naam, versie, potlood, + New version, Compare, Bench view en ⋯ op één lijn ({ {k: round(v['y']) if v else None for k, v in r1.items()} })",
          all(r1.values()) and max(v["y"] + v["h"] / 2 for v in r1.values()) - min(v["y"] + v["h"] / 2 for v in r1.values()) < 6)
    check("⋯ staat rechts, na Bench view", r1["#fMore summary"] and r1["#btnBenchToggle"] and r1["#fMore summary"]["x"] > r1["#btnBenchToggle"]["x"] > r1["#btnCmp"]["x"])
    r2 = {s: box(s) for s in ("#fCat", "#sortSel")}
    check("tweede rij: de categorie en Order, onder de eerste",
          all(r2.values()) and abs(r2["#fCat"]["y"] - r2["#sortSel"]["y"]) < 6 and r2["#fCat"]["y"] > r1["#verSel"]["y"] + 20)
    meta = page.text_content(".fMeta") if page.locator(".fMeta").count() else ""
    check(f"de tweede rij zegt sinds wanneer en starter set ({meta.strip()[:80]!r})", "since " in meta and "starter set" in meta)
    t = page.evaluate("() => document.querySelector('table.ftable').getBoundingClientRect().top - document.querySelector('#content').getBoundingClientRect().top")
    check(f"de tabel begint hoog op de pagina ({t:.0f} px onder de bovenkant)", t < 140)
    check("geen piramide en geen balk meer in de kop", page.locator(".fTop .fpyr, .fMeta .fpyr, .pyrbar").count() == 0 and page.locator("#catsBox .fpyr").count() == 1)
    check("Delete version en Delete formula staan niet in zicht", not vis("#btnDelV") and not vis("#btnDelF") and not vis("#btnRenameF"))

    # ---------- 2. het menu ⋯ ----------
    if vis("#fMore summary"):
        page.click("#fMore summary"); page.wait_for_timeout(150)
        check("⋯ opent het menu met Rename, Copy, Delete version en Delete formula",
              all(vis(s) for s in ("#btnRenameF", "#btnCopyF", "#btnDelV", "#btnDelF")))
        page.keyboard.press("Escape"); page.wait_for_timeout(150)
        check("Escape sluit het", not vis("#btnRenameF"))
        page.click("#fMore summary"); page.click("#content h2"); page.wait_for_timeout(150)
        check("een klik ernaast sluit het", not vis("#btnRenameF"))
        page.click("#fMore summary"); msgs.clear(); page.click("#btnRenameF"); page.wait_for_timeout(200)
        check(f"Rename… uit het menu vraagt de naam, en het menu sluit ({msgs[:1]})", msgs[:1] == ["Formula name:"] and not vis("#btnRenameF"))
        n = page.evaluate("DATA.formulas.find(f => f.name === 'Jasmin 231').versions.length")
        page.click("#btnNewV"); page.wait_for_timeout(400)
        page.click("#fMore summary"); page.click("#btnDelV"); page.wait_for_timeout(400)
        check("Delete version uit het menu", page.evaluate("DATA.formulas.find(f => f.name === 'Jasmin 231').versions.length") == n)
        page.evaluate("() => { DATA.formulas.push({id: 'f-solo', name: 'Solo', category: 'Uncategorised', created: today(), versions: [{v: 1, date: today(), lines: []}]}); }")
        open_f("Solo"); page.click("#fMore summary"); page.wait_for_timeout(150)
        check("een formule met één versie heeft Move into… in het menu", vis("#btnMoveF"))
        page.keyboard.press("Escape")
        page.evaluate("() => { DATA.formulas = DATA.formulas.filter(f => f.id !== 'f-solo'); }")
    else:
        check("het menu ⋯ bestaat", False)

    # ---------- 3. de bench view ----------
    open_f("Jasmin 231")
    if vis("#btnBenchToggle"):
        page.click("#btnBenchToggle"); page.wait_for_timeout(400)
        check("de bench view noemt de versie in de kop, zonder Delete version",
              vis("#benchVer") and page.locator("#btnDelV").count() == 0 and page.locator("#verSel").count() == 0)
        page.click("#btnBenchToggle"); page.wait_for_timeout(300)

    # ---------- 4. de tick bar ----------
    check("de tick bar is weg zolang er niets aangevinkt is", page.locator(".tickBar").count() == 1 and not vis(".tickBar"))
    cbs = page.locator("input.selCb")
    cbs.nth(1).click(); cbs.nth(4).click(modifiers=["Shift"]); page.wait_for_timeout(150)
    txt = page.text_content("#tickCount") if page.locator("#tickCount").count() else ""
    check(f"vier aangevinkt: de bar verschijnt en telt ({txt!r})", vis(".tickBar") and txt == "4 lines ticked:")
    cbs.nth(1).click(); cbs.nth(4).click(modifiers=["Shift"]); page.wait_for_timeout(150)
    check("alles weer uit: de bar verdwijnt", not vis(".tickBar"))
    open_f("Acqua di Gio for men")
    page.evaluate("document.querySelector('#content').scrollTop = 0"); page.locator("input.selCb").first.click(); page.wait_for_timeout(200)
    tb = box(".tickBar")
    check(f"bij een lange tabel blijft de bar onderaan het venster ({tb and round(tb['y'] + tb['h'])} px van 660)", tb and 560 < tb["y"] + tb["h"] <= 660)
    page.locator("input.selCb").first.click()

    # ---------- 5. onder de tabel ----------
    open_f("Jasmin 231")
    e = {s: box(s) for s in ("#addMat", "#btnAddLine", "#btnScale", "#btnPrep", "#outMenu summary", "#btnPrint")}
    check("links Add material…, Add line en Batch scaling, rechts Mark as prepared, Print / export en Print weighing sheet",
          all(e.values()) and e["#addMat"]["x"] < e["#btnAddLine"]["x"] < e["#btnScale"]["x"] < e["#btnPrep"]["x"] < e["#outMenu summary"]["x"] < e["#btnPrint"]["x"])
    check("Print full formula, Excel export en Share this version zitten in het menu", not vis("#btnSheet") and not vis("#btnCsv") and not vis("#btnShare"))
    if vis("#outMenu summary"):
        page.click("#outMenu summary"); page.wait_for_timeout(150)
        check("Print / export opent met de drie", vis("#btnSheet") and vis("#btnCsv") and vis("#btnShare"))
        with page.expect_download() as d:
            page.click("#btnCsv")
        check(f"Excel export uit het menu ({d.value.suggested_filename})", d.value.suggested_filename.endswith(".csv") and not vis("#btnCsv"))

    # ---------- 6. Batch scaling als strook ----------
    check("Batch scaling is dicht", page.locator("#scaleBox").count() == 1 and not vis("#scaleW"))
    if vis("#btnScale"):
        page.click("#btnScale"); page.wait_for_timeout(150)
        tops = page.evaluate("() => [...document.querySelectorAll('#scaleBox .sg')].map(s => Math.round(s.getBoundingClientRect().top))")
        check(f"de knop opent een strook met de drie velden op één regel ({tops})", vis("#scaleW") and len(tops) == 3 and len(set(tops)) == 1
              and page.get_attribute("#btnScale", "aria-expanded") == "true")
        page.fill("#scaleW", "50"); page.click("#btnApplyScale"); page.wait_for_timeout(400)
        w = page.evaluate("DATA.formulas.find(f => f.name === 'Jasmin 231').versions.at(-1).lines.reduce((s, l) => s + l.weightG, 0)")
        check(f"Target total werkt en de strook blijft open ({w:.3f} g)", abs(w - 50) < 1e-6 and vis("#scaleW"))
        page.keyboard.press("Control+z"); page.wait_for_timeout(300)
        page.click("#btnScale"); page.wait_for_timeout(150)
        check("en gaat weer dicht", not vis("#scaleW"))

    # ---------- 7. de vier panelen ----------
    ids = page.evaluate("() => [...document.querySelectorAll('.fblocks > details')].map(d => d.id)")
    check(f"vier panelen, in deze volgorde ({ids})", ids == ["notesBox", "trialBox", "catsBox", "ifraBox"])
    pb = {s: box(s) for s in ("#notesBox", "#trialBox", "#catsBox", "#ifraBox")}
    check("twee aan twee op 1366 px", all(pb.values()) and abs(pb["#notesBox"]["y"] - pb["#trialBox"]["y"]) < 2
          and abs(pb["#catsBox"]["y"] - pb["#ifraBox"]["y"]) < 2 and pb["#catsBox"]["y"] > pb["#notesBox"]["y"])
    st = page.evaluate("""() => [...document.querySelectorAll('.fblocks > details > summary')].map(s => { const c = getComputedStyle(s);
        return [c.textTransform, c.color, c.fontWeight, c.letterSpacing]; })""")
    check(f"de titels zijn gewoon: geen hoofdletters, in de kleur van de tekst ({st[:1]})",
          len(st) == 4 and all(x[0] == "none" and x[1] == INK and x[2] == "600" for x in st))
    s_ifra = page.text_content("#ifraBox summary") or ""
    warn = page.evaluate("() => { const w = document.querySelector('#ifraBox summary .warn'); return w ? getComputedStyle(w).color : null; }")
    check(f"de IFRA check zegt het oordeel, alleen het ⚠ is rood ({s_ifra.strip()!r}, {warn})", "⚠ 3 over limit" in s_ifra and warn == DANGER)
    s_cat = page.text_content("#catsBox summary") or ""
    check(f"Pyramid & categories, zonder balk ({s_cat.strip()!r})", s_cat.strip().startswith("Pyramid & categories") and page.locator("#catsBox summary .pyrbar").count() == 0)
    s_tr = page.text_content("#trialBox summary") if page.locator("#trialBox").count() else ""
    check(f"Trial log zonder regels is dicht en zegt empty ({s_tr.strip()!r})", "empty" in s_tr and not page.evaluate("document.querySelector('#trialBox')?.open"))
    if page.locator("#trialBox").count():
        page.click("#trialBox summary"); page.fill("#trialText", "day 3, top too sharp"); page.click("#btnAddTrial"); page.wait_for_timeout(300)
        s_tr = page.text_content("#trialBox summary")
        check(f"met een regel telt de titel ze en blijft het paneel open ({s_tr.strip()!r})", "1 entry" in s_tr and page.evaluate("document.querySelector('#trialBox').open"))
        page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    page.set_viewport_size({"width": 800, "height": 660}); page.wait_for_timeout(300)
    pb = {s: box(s) for s in ("#notesBox", "#trialBox")}
    check("op een smal venster één kolom", all(pb.values()) and pb["#trialBox"]["y"] > pb["#notesBox"]["y"] + 20)
    page.set_viewport_size({"width": 1366, "height": 660}); page.wait_for_timeout(200)

    # ---------- 8. een bevroren versie en alleen-lezen ----------
    open_f("Jasmin 231", 0)
    check("een bevroren versie: geen Add material en geen Batch scaling, wel Print / export en Print weighing sheet",
          page.locator("#addMat").count() == 0 and page.locator("#btnScale").count() == 0 and vis("#outMenu summary") and vis("#btnPrint"))
    page.evaluate("document.body.classList.add('ro')"); page.wait_for_timeout(100)
    check("in alleen-lezen verdwijnt ⋯ (alles erin wijzigt iets)", page.locator("#fMore").count() == 1 and not vis("#fMore"))
    page.evaluate("document.body.classList.remove('ro')")

    check("geen fouten op de pagina", not errs)
    if errs: print(errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
