"""Bouw 261011e: de categorie van een formule zoals die van een materiaal, en Classify several… voor formules.
- Boven het zoekvak van Formulas: + New formula… (het venster van de kop) en Classify several…, op één regel.
- De formulepagina: de categorie boven Version, met het kleurvakje en + New category; Change category… is weg. Een
  andere keuze is één Undo-stap; + New category maakt de categorie en geeft ze de formule, en één Undo neemt beide terug;
  een bestaande naam in andere hoofdletters is die categorie; het kleurvakje zet de kleur van de categorie. Ook op een
  bevroren formule en op een formule zonder versies; niet in de bench view, die ook geen Version toont. Alleen lezen: uitgeschakeld, geen knoppen boven
  het zoekvak.
- Classify formulas: de open formule aangevinkt, geen Pyramid, zoeken op naam en categorie, Tick all shown, + New
  category, Apply in één Undo-stap die byte voor byte terugzet, de meldingen, ook bevroren formules.
- Op een telefoon: de knoppen boven de lijst en het venster in het scherm.
Vereist de lokale webserver op poort 8765 (zie README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

ANTWOORD = {"prompt": "Violet"}
def open_f(page, naam, bench=False, idx=1):
    page.evaluate("([n, b, i]) => { HOMEVIEW = false; const f = DATA.formulas.find(f => f.name === n); switchTab('F', f.id, {type: 'v', idx: Math.min(i, f.versions.length - 1), bench: b}); }", [naam, bench, idx])
    page.wait_for_timeout(350)
cat = lambda page, naam: page.evaluate("n => DATA.formulas.find(f => f.name === n).category", naam)

with sync_playwright() as pw:
    b = pw.chromium.launch()
    c = b.new_context(viewport={"width": 1400, "height": 900}, locale="en-GB")
    page = c.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    def dlg(d):
        msgs.append(d.message)
        d.accept(ANTWOORD["prompt"]) if d.type == "prompt" else d.accept()
    page.on("dialog", dlg)
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)

    # ---- de knoppen boven het zoekvak ----
    open_f(page, "Angel")
    knoppen = page.evaluate("""() => { const t = document.querySelector('#listTools'), z = document.querySelector('#searchBox').getBoundingClientRect();
      if (!t) return [[], false];   // een bouw van vóór 261011e
      const r = t.getBoundingClientRect(); return [[...t.querySelectorAll('button')].map(b => b.textContent.trim()), r.bottom <= z.top]; }""")
    check(f"boven het zoekvak van Formulas: + New formula… en Classify several… ({knoppen})",
          knoppen[0] == ["+ New formula…", "Classify several…"] and knoppen[1])
    page.click("#ltNew"); page.wait_for_timeout(300)
    check("+ New formula… boven het zoekvak opent het venster van de kop", page.locator("#nfName").is_visible())
    page.click("#dlgCancel"); page.wait_for_timeout(200)

    # ---- de categorie op de formulepagina ----
    rij = page.evaluate("""() => { const r = document.querySelector('#fCatRow'), v = document.querySelector('#verSel');
      const s = document.querySelector('#fCat'), kl = document.querySelector('#fCatCol'), n = document.querySelector('#btnNewFCat');
      const b = x => x.getBoundingClientRect();
      // since 261019a in the second row of the head, under the version
      return [s.getAttribute('aria-label'), s.value, b(r).top >= b(v).bottom - 1, Math.abs(b(s).top - b(n).top) < 8,
              b(kl).left > b(s).right - 1, b(n).left > b(kl).right - 1, n.textContent, s.getAttribute('aria-label')]; }""")
    check(f"de categorie staat onder de versie, in de tweede rij van de kop: keuzelijst, kleurvakje en + New category op één regel ({rij})",
          rij[0] == "Category of this formula" and rij[1] == "Uncategorised" and all(rij[2:6]) and rij[6] == "+ New category" and rij[7])
    check("Change category… is weg", page.locator("#btnCatF").count() == 0
          and page.locator("#content button", has_text="Change category").count() == 0)
    voor = page.evaluate("serialize()"); undo0 = page.evaluate("UNDO.length")
    page.select_option("#fCat", "Bases & Accords"); page.wait_for_timeout(400)
    groep = page.evaluate("() => [...document.querySelectorAll('#list .cat')].map(x => x.textContent.trim().replace(/\\s+/g, ' '))")
    check(f"een andere keuze is de nieuwe categorie, meteen ook in de lijst ({groep})",
          cat(page, "Angel") == "Bases & Accords" and "Bases & Accords 5" in groep and page.evaluate("$('#fCat').value") == "Bases & Accords")
    check("één Undo-stap", page.evaluate("UNDO.length") == undo0 + 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("Undo zet ze terug (serialize() gelijk aan ervoor)", page.evaluate("serialize()") == voor and cat(page, "Angel") == "Uncategorised")
    page.click("#btnNewFCat"); page.wait_for_timeout(400)
    check("+ New category maakt Violet en geeft ze de formule", cat(page, "Angel") == "Violet"
          and "Violet" in page.evaluate("DATA.formulaCategories") and page.evaluate("$('#fCat').value") == "Violet")
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("één Undo neemt de categorie en de nieuwe naam terug", page.evaluate("serialize()") == voor)
    ANTWOORD["prompt"] = "bases & accords"; page.click("#btnNewFCat"); page.wait_for_timeout(400)
    check("een bestaande naam in andere hoofdletters is die categorie, zonder een tweede",
          cat(page, "Angel") == "Bases & Accords" and not any(x == "bases & accords" for x in page.evaluate("allFormulaCats()")))
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    open_f(page, "Althenol")
    page.evaluate("() => { const i = document.querySelector('#fCatCol'); i.value = '#123456'; i.dispatchEvent(new Event('change', {bubbles: true})); }")
    page.wait_for_timeout(300)
    check("het kleurvakje zet de kleur van de categorie", page.evaluate("(DATA.categoryColours || {})['Bases & Accords']") == "#123456")
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    open_f(page, "Angel", bench=True)
    check("de bench view toont Category en Version niet: daar weeg je de versie die je opende",
          page.locator("#fCatRow").count() == 0 and page.locator("#verSel").count() == 0 and page.locator(".benchWrap").count() == 1)
    page.evaluate("() => { const f = DATA.formulas.find(f => f.name === 'Brut'); f.frozenImport = true; }")
    open_f(page, "Brut")
    frozen = page.evaluate("() => [document.querySelectorAll('#content input.w').length, document.querySelector('#fCat').disabled]")
    page.select_option("#fCat", "Bases & Accords"); page.wait_for_timeout(300)
    check(f"een bevroren formule krijgt ook een andere categorie: ze hoort bij de formule ({frozen})",
          frozen == [0, False] and cat(page, "Brut") == "Bases & Accords")
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    page.evaluate("""() => { DATA.formulas.push({id: "f-leeg", name: "Leeggelopen", category: "Uncategorised", created: today(),
        frozenImport: false, versions: []}); buildUsage(); markDirty(); switchTab("F", "f-leeg", null); }""")
    page.wait_for_timeout(500)
    page.select_option("#fCat", "Bases & Accords"); page.wait_for_timeout(300)
    check("ook op een formule zonder versies", cat(page, "Leeggelopen") == "Bases & Accords")
    page.evaluate("() => { DATA.formulas = DATA.formulas.filter(f => f.id !== 'f-leeg'); switchTab('F', null, null); }")
    open_f(page, "Angel")
    page.evaluate("() => { LOCKED = true; render(); }"); page.wait_for_timeout(200)
    check("alleen lezen: de categorie is uitgeschakeld en er staan geen knoppen boven het zoekvak",
          page.locator("#fCat").is_disabled() and page.locator("#btnNewFCat").is_disabled() and not page.locator("#listTools").is_visible())
    page.evaluate("() => { LOCKED = false; render(); }"); page.wait_for_timeout(200)

    # ---- Classify formulas ----
    open_f(page, "Angel")
    voor = page.evaluate("serialize()"); n_f = page.evaluate("DATA.formulas.length")
    page.click("#ltClassify"); page.wait_for_timeout(300)
    check(f"het venster heet Classify formulas, de open formule is aangevinkt, en er is geen Pyramid ({page.inner_text('#clCount')!r})",
          page.locator("#dlg h3").inner_text() == "Classify formulas" and page.inner_text("#clCount") == f"1 formula ticked · {n_f} of {n_f} shown"
          and page.locator("#clPyr").count() == 0 and page.inner_text("#dlgOk") == "Apply to 1")
    page.fill("#clQ", "for men"); page.wait_for_timeout(200)
    namen = page.locator("#clRows label > span:not(.sub)").all_inner_texts()
    page.fill("#clQ", "bases"); page.wait_for_timeout(200)
    n_bases = page.locator("#clRows input[data-i]").count()
    check(f"zoeken op naam ({len(namen)}: {namen[:2]}) en op categorie ({n_bases})",
          len(namen) >= 4 and all("for men" in n for n in namen) and n_bases == 4)
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(200)
    check(f"zonder keuze: {msgs}", msgs == ["Choose a category."] and page.evaluate("$('#dlg').open"))
    page.fill("#clQ", "for men"); page.click("#clAll")
    ANTWOORD["prompt"] = "Men"; page.click("#clNewCat"); page.wait_for_timeout(200)
    n_tick = len(namen) + 1
    undo0 = page.evaluate("UNDO.length")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(400)
    men = page.evaluate("() => DATA.formulas.filter(f => f.category === 'Men').map(f => f.name)")
    check(f"Apply: de formules for men en Angel in Men ({men}, {msgs})",
          sorted(men) == sorted(namen + ["Angel"]) and msgs == [f"{n_tick} formulas classified."]
          and "Men" in page.evaluate("DATA.formulaCategories"))
    check("één Undo-stap", page.evaluate("UNDO.length") == undo0 + 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("Undo zet alles terug, de nieuwe categorie inbegrepen (serialize() gelijk aan ervoor)", page.evaluate("serialize()") == voor)
    page.click("#ltClassify"); page.wait_for_timeout(300)
    page.click("#clNone"); page.fill("#clQ", "bases"); page.click("#clAll"); page.select_option("#clCat", "Bases & Accords")
    undo0 = page.evaluate("UNDO.length")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    check(f"niets te veranderen: een melding en geen Undo-stap ({msgs})",
          msgs == ["Nothing to change: the 4 formulas you ticked already have that."] and page.evaluate("UNDO.length") == undo0)
    page.evaluate("() => { const f = DATA.formulas.find(f => f.name === 'Brut'); f.frozenImport = true; render(); }")
    page.click("#ltClassify"); page.wait_for_timeout(300)
    page.click("#clNone"); page.fill("#clQ", "brut"); page.click("#clAll"); page.fill("#clQ", "althenol"); page.click("#clAll")
    page.select_option("#clCat", "Bases & Accords")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    check(f"een bevroren formule kan mee, en wat het al had telt apart ({msgs})",
          cat(page, "Brut") == "Bases & Accords" and msgs == ["1 formula classified. 1 already had it."])
    check(f"geen fouten in de pagina ({errs[:2]})", not errs)
    c.close()

    # ---- op een telefoon ----
    c = b.new_context(viewport={"width": 430, "height": 932}, locale="en-GB", is_mobile=True, has_touch=True,
                      user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
    page = c.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e))); page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    page.evaluate("() => { HOMEVIEW = false; switchTab('F', null, null); }"); page.wait_for_timeout(400)
    tel = page.evaluate("""() => { const bs = [...document.querySelectorAll('#listTools button')];
      return [bs.map(b => b.textContent.trim()), bs.every(b => b.getBoundingClientRect().right <= innerWidth && b.scrollWidth <= b.clientWidth + 1)]; }""")
    check(f"op een telefoon staan de twee knoppen boven de lijst, volledig leesbaar ({tel})", tel[0] == ["+ New formula…", "Classify several…"] and tel[1])
    page.locator("#ltClassify").click(); page.wait_for_timeout(300)
    vak = page.evaluate("() => { const d = document.querySelector('#dlg'), r = d.getBoundingClientRect(), o = document.querySelector('#dlgOk').getBoundingClientRect(); return [r.left >= 0, r.right <= innerWidth, o.bottom <= innerHeight, d.scrollHeight <= d.clientHeight + 1]; }")
    check(f"en het venster past zonder te scrollen ({vak})", all(vak))
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    open_f(page, "Angel")
    rij = page.evaluate("() => { const r = document.querySelector('#fCatRow').getBoundingClientRect(); return [r.right <= innerWidth, document.querySelector('#fCat').getBoundingClientRect().width > 100]; }")
    check(f"op een telefoon past de regel van de categorie in het scherm ({rij})", all(rij))
    check(f"geen fouten in de pagina op een telefoon ({errs[:2]})", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
