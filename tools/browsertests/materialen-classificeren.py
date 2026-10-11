"""Bouw 261011d: Classify several…, een categorie of een piramideniveau voor veel materialen tegelijk.
- De knop staat op de materiaalpagina naast + New category en het kleurvakje (het raster schuift niet op), niet op de
  pagina van een premix, en is uitgeschakeld als alleen lezen kan.
- Het venster: het materiaal van de pagina al aangevinkt en in beeld, een lijst zo hoog als het scherm toelaat zonder
  dat het venster scrolt (ook op een laag laptopscherm) en die niet verspringt, de telling en de knop Apply to N; zoeken
  op naam, categorie en
  CAS; Tick all shown, Untick all en Shift-klik; wat aangevinkt is, blijft dat bij een andere zoekterm; premixes staan
  er niet in.
- Apply: zonder vinkje of zonder keuze een melding en het venster blijft open; + New category (ook een bestaande naam in
  andere hoofdletters); alleen de categorie, alleen de piramide (ook "?"); de andere materialen en velden blijven; de
  melding telt wat veranderde en wat het al had; niets te veranderen is geen Undo-stap; één Undo zet alles terug, ook
  de nieuwe categorie, en Redo doet het opnieuw.
- Op een telefoon past het venster in het scherm.
Vereist de lokale webserver op poort 8765 (zie README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

ANTWOORD = {"prompt": "Violet"}
def open_mat(page, naam):
    page.evaluate("n => { HOMEVIEW = false; switchTab('M', DATA.materials.find(m => m.name === n).id, null); }", naam)
    page.wait_for_timeout(300)
def mats(page, namen):
    return page.evaluate("ns => ns.map(n => { const m = DATA.materials.find(x => x.name === n); return [m.category, m.pyramid]; })", namen)
IONONEN = ["Ionone Alpha", "Ionone Beta", "Ionone Pure", "Methyl Ionone", "Methyl Ionone Gamma", "Methyl Ionone Total"]

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

    # ---- de knop ----
    open_mat(page, "Ionone Beta")
    knop = page.locator("#btnClassify")
    check("op de materiaalpagina staat Classify several…", knop.count() == 1 and knop.inner_text().strip() == "Classify several…")
    rij = page.evaluate("""() => { const k = document.querySelector('#btnClassify'), n = document.querySelector('#btnNewMatCat'),
        kl = document.querySelector('#matCatCol'), p = document.querySelector('#content .pyr');
      const r = x => x.getBoundingClientRect();
      return [Math.abs(r(k).top - r(n).top) < 6, r(k).left > r(kl).right, k.parentElement === kl.parentElement, r(p).top > r(k).bottom - 2]; }""")
    check(f"naast + New category en het kleurvakje, op dezelfde rij, met Pyramid eronder: het raster schuift niet op ({rij})", all(rij))
    page.evaluate("() => { LOCKED = true; render(); }"); page.wait_for_timeout(200)
    check("alleen lezen: de knop is uitgeschakeld", page.locator("#btnClassify").is_disabled())
    page.evaluate("() => { LOCKED = false; render(); }"); page.wait_for_timeout(200)
    page.evaluate("() => { DATA.materials.find(m => m.name === 'BHT').isPredil = true; }")
    open_mat(page, "BHT")
    check("op de pagina van een premix staat de knop niet", page.locator("#btnClassify").count() == 0)

    # ---- het venster ----
    open_mat(page, "Ionone Beta")
    voor = page.evaluate("serialize()")
    n_eigen = page.evaluate("DATA.materials.filter(m => !isPredil(m)).length")
    page.click("#btnClassify"); page.wait_for_timeout(300)
    check("het venster heet Classify materials", page.locator("#dlg h3").inner_text() == "Classify materials")
    telling = page.inner_text("#clCount")
    check(f"het materiaal van de pagina is al aangevinkt, en de premix staat er niet in ({telling!r})",
          telling == f"1 material ticked · {n_eigen} of {n_eigen} shown" and page.inner_text("#dlgOk") == "Apply to 1"
          and page.locator('#clRows input[data-i]').count() == n_eigen
          and page.locator("#clRows label", has_text="BHT").count() == 0)
    zicht = page.evaluate("""() => { const l = document.querySelector('#clRows').getBoundingClientRect();
      const inBeeld = x => { const r = x.getBoundingClientRect(); return r.top >= l.top && r.bottom <= l.bottom; };
      return [[...document.querySelectorAll('#clRows label')].filter(inBeeld).length, inBeeld(document.querySelector('#clRows input:checked').closest('label'))]; }""")
    check(f"de lijst is zo hoog als het scherm toelaat: {zicht[0]} materialen tegelijk in beeld, het aangevinkte (Ionone Beta) ook",
          zicht[0] >= 12 and zicht[1])
    MAAT = "() => [Math.round(document.querySelector('#clRows').getBoundingClientRect().height), (d => d.scrollHeight <= d.clientHeight + 1)(document.querySelector('#dlg'))]"
    h0 = page.evaluate(MAAT)
    page.fill("#clQ", "ionone"); page.wait_for_timeout(200)
    h1 = page.evaluate(MAAT)
    check(f"het venster scrolt niet, en de lijst blijft even hoog met zes treffers, zodat niets verspringt ({h0}, {h1})",
          h0[1] and h1 == h0)
    namen = page.locator("#clRows label > span:not(.sub)").all_inner_texts()
    check(f"zoeken op naam ({namen})", sorted(namen) == sorted(IONONEN))
    page.fill("#clQ", "flowers - spicy"); page.wait_for_timeout(200)
    n_cat = page.locator("#clRows input[data-i]").count()
    page.fill("#clQ", "127-41-3"); page.wait_for_timeout(200)
    check(f"zoeken op categorie ({n_cat} rijen) en op CAS (Ionone Alpha)",
          n_cat >= 3 and page.locator("#clRows label > span:not(.sub)").all_inner_texts() == ["Ionone Alpha"])
    page.fill("#clQ", "ionone"); page.wait_for_timeout(200)
    page.click("#clNone"); page.wait_for_timeout(100)
    check("Untick all: niets meer aangevinkt, de knop zegt Apply", page.inner_text("#clCount").startswith("0 materials ticked")
          and page.inner_text("#dlgOk") == "Apply" and page.locator("#clRows input:checked").count() == 0)
    rows = page.locator("#clRows input[data-i]")
    rows.nth(0).click(); rows.nth(3).click(modifiers=["Shift"]); page.wait_for_timeout(100)
    check(f"Shift-klik vinkt een reeks aan ({page.inner_text('#clCount')!r})", page.inner_text("#clCount").startswith("4 materials ticked"))
    page.click("#clAll"); page.wait_for_timeout(100)
    check("Tick all shown vinkt alle zes ionones aan", page.inner_text("#clCount") == f"6 materials ticked · 6 of {n_eigen} shown"
          and page.inner_text("#dlgOk") == "Apply to 6")
    page.fill("#clQ", "lide"); page.wait_for_timeout(200)
    page.locator("#clRows input[data-i]").nth(0).click(); page.wait_for_timeout(100)
    page.fill("#clQ", ""); page.wait_for_timeout(200)
    check(f"wat aangevinkt is, blijft dat bij een andere zoekterm ({page.inner_text('#clCount')!r})",
          page.inner_text("#clCount").startswith("7 materials ticked") and page.locator("#clRows input:checked").count() == 7)
    page.fill("#clQ", "lide"); page.wait_for_timeout(200)
    page.locator("#clRows input[data-i]").nth(0).click(); page.fill("#clQ", "ionone"); page.wait_for_timeout(200)

    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(200)
    check(f"zonder keuze een melding, en het venster blijft open ({msgs[:1]})",
          msgs == ["Choose a category, a pyramid level, or both."] and page.evaluate("$('#dlg').open"))
    page.click("#clNewCat"); page.wait_for_timeout(200)
    check("+ New category: Violet staat erbij en is gekozen", page.evaluate("$('#clCat').value") == "Violet"
          and page.evaluate("[...$('#clCat').options].filter(o => o.value === 'Violet').length") == 1)
    ANTWOORD["prompt"] = "musks"; page.click("#clNewCat"); page.wait_for_timeout(200)
    check("een bestaande naam in andere hoofdletters kiest die categorie (Musks), zonder een tweede",
          page.evaluate("$('#clCat').value") == "Musks" and page.evaluate("[...$('#clCat').options].filter(o => /^musks$/i.test(o.value)).length") == 1)
    page.select_option("#clCat", "Violet")
    undo_voor = page.evaluate("UNDO.length")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(400)
    na = mats(page, IONONEN)
    check(f"Apply: de zes ionones in Violet, hun piramide onveranderd ({na})",
          all(x[0] == "Violet" for x in na) and all(x[1] == 3 for x in na) and not page.evaluate("$('#dlg').open"))
    check(f"de melding telt ze ({msgs})", msgs == ["6 materials classified."])
    groep = page.evaluate("() => [...document.querySelectorAll('#list .cat')].map(x => x.textContent.trim().replace(/\\s+/g, ' ')).find(t => t.startsWith('Violet'))")
    check(f"de nieuwe categorie staat in de lijst van categorieën, en links staat een groep Violet met zes ({groep!r})",
          "Violet" in page.evaluate("DATA.materialCategories") and groep == "Violet 6")
    check("de rest is onveranderd (Exaltolide, Citral)", mats(page, ["Exaltolide", "Citral"]) == [["Musks", 4], ["Citrus", 0]])
    check("de zes dragen de tijd van de wijziging", page.evaluate("() => DATA.materials.filter(m => m.category === 'Violet').every(m => m.modified === now())"))
    check("één Undo-stap", page.evaluate("UNDO.length") == undo_voor + 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("Undo zet alles terug, de nieuwe categorie inbegrepen (serialize() gelijk aan ervoor)", page.evaluate("serialize()") == voor)
    page.keyboard.press("Control+y"); page.wait_for_timeout(400)
    check("Redo doet het opnieuw", all(x[0] == "Violet" for x in mats(page, IONONEN)))

    # ---- alleen de piramide, "?", en wat het al had ----
    open_mat(page, "Exaltolide")
    page.click("#btnClassify"); page.wait_for_timeout(300)
    page.fill("#clQ", "lide"); page.click("#clAll"); page.select_option("#clPyr", "2")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    lide = page.evaluate("() => DATA.materials.filter(m => /lide$/.test(m.name)).map(m => [m.category, m.pyramid])")
    check(f"alleen de piramide: Heart, de categorie blijft ({lide}, {msgs})",
          len(lide) == 6 and all(x == ["Musks", 2] for x in lide) and msgs == ["6 materials classified."])
    page.click("#btnClassify"); page.wait_for_timeout(300)
    page.fill("#clQ", "lide"); page.click("#clAll"); page.select_option("#clPyr", "2")
    undo_voor = page.evaluate("UNDO.length")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    check(f"niets te veranderen: een melding en geen Undo-stap ({msgs})",
          msgs == ["Nothing to change: the 6 materials you ticked already have that."] and page.evaluate("UNDO.length") == undo_voor)
    page.click("#btnClassify"); page.wait_for_timeout(300)
    page.fill("#clQ", "musk"); page.click("#clAll"); page.select_option("#clPyr", "5")
    n_musk = page.locator("#clRows input:checked").count()
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    check(f"\"?\" kan ook ({msgs})", page.evaluate("DATA.materials.find(m => m.name === 'Tonalid').pyramid") == 5
          and msgs == [f"{n_musk} materials classified."])
    page.click("#btnClassify"); page.wait_for_timeout(300)
    page.click("#clNone"); page.select_option("#clPyr", "4")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(200)
    check(f"zonder vinkje een melding, en het venster blijft open ({msgs})",
          msgs == ["Tick the materials you want to classify."] and page.evaluate("$('#dlg').open"))
    page.fill("#clQ", "lide"); page.click("#clAll"); page.fill("#clQ", "ionone alpha"); page.click("#clAll")
    page.select_option("#clPyr", "5")
    msgs.clear(); page.click("#dlgOk"); page.wait_for_timeout(300)
    check(f"wat het al had, telt apart ({msgs})", msgs == ["1 material classified. 6 already had it."]
          and page.evaluate("DATA.materials.find(m => m.name === 'Ionone Alpha').pyramid") == 5)
    check(f"geen fouten in de pagina ({errs[:2]})", not errs)
    c.close()

    # ---- op een telefoon ----
    c = b.new_context(viewport={"width": 430, "height": 932}, locale="en-GB", is_mobile=True, has_touch=True,
                      user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
    page = c.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e))); page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    open_mat(page, "Ionone Beta")
    page.locator("#btnClassify").click(); page.wait_for_timeout(300)
    vak = page.evaluate("() => { const d = document.querySelector('#dlg'), r = d.getBoundingClientRect(), o = document.querySelector('#dlgOk').getBoundingClientRect(); return [r.left >= 0, r.right <= innerWidth, o.bottom <= innerHeight, d.scrollHeight <= d.clientHeight + 1, Math.round(document.querySelector('#clRows').getBoundingClientRect().height)]; }")
    check(f"op een telefoon past het venster in het scherm zonder te scrollen, Apply in beeld ({vak})", all(vak[:4]) and vak[4] >= 300)
    check(f"geen fouten in de pagina op een telefoon ({errs[:2]})", not errs)
    c.close()

    # ---- op een laptop met een laag scherm (1366 bij 768, min de balken van de browser) ----
    c = b.new_context(viewport={"width": 1366, "height": 660}, locale="en-GB")
    page = c.new_page(); page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    open_mat(page, "Ionone Beta")
    page.click("#btnClassify"); page.wait_for_timeout(300)
    laag = page.evaluate("""() => { const d = document.querySelector('#dlg'), p = document.querySelector('#clPyr').getBoundingClientRect(),
        o = document.querySelector('#dlgOk').getBoundingClientRect(), l = document.querySelector('#clRows').getBoundingClientRect();
      return [d.scrollHeight <= d.clientHeight + 1, p.bottom <= o.top, Math.round(l.height)]; }""")
    check(f"op een laag laptopscherm scrolt het venster niet: Pyramid boven de knoppen, de lijst korter ({laag})", laag[0] and laag[1] and laag[2] >= 144)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
