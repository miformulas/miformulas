"""Bouw 261011b: de eerste vijf minuten. De pagina docs/first-five-minutes.html (uit first-five-minutes.md, door
tools/bouw-docs.py), de links ernaartoe (het startscherm, Welcome zolang je nog niets van jezelf hebt, de navigatie van
de pagina's, §1 van de handleiding en de README), en de stappen van de pagina zelf in de app: Get the latest library,
Javanol uit de library (puur) met een dilutie van 10 % erbij, My first accord met het toetsenbord (Enter in Add
material…, Tab van gewicht naar gewicht; abs % 70.20), + New version met het label "more javanol", Ctrl+Z en Compare. Zo
raakt de tekst niet uit de pas met de app. En op een telefoon: + New material… en + New formula… onder Start here.
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
FIRST5 = "https://miformulas.com/docs/first-five-minutes.html"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
DOCS = os.path.join(PUB, "docs")
lees = lambda rel: open(os.path.join(PUB, rel), encoding="utf-8").read() if os.path.exists(os.path.join(PUB, rel)) else ""
GEPUB = os.path.join(PUB, "..", "miformulas-materials.json")
LIB = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else {
    "type": "miformulas-materials", "name": "Kleine library", "version": "2026-10-11", "licence": "CC BY 4.0",
    "materials": [{"name": "Javanol", "aliases": ["Sandal Cyclopropane"], "cas": "198404-98-7", "category": "Woody - sandal",
                   "pyramid": 4, "ifraLimit": 99, "odour": ["woody", "sandalwood", "fatty", "rose"], "strength": "high"}]}
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

# ---------------- 1. de pagina en waar ze genoemd wordt ----------------
md, htm = lees("docs/first-five-minutes.md"), lees("docs/first-five-minutes.html")
check("docs/first-five-minutes.md en .html bestaan", bool(md) and bool(htm))
check("de titel: Your first five minutes with miFormulas",
      "<title>Your first five minutes with miFormulas</title>" in htm and "<h1" in htm and "Your first five minutes with miFormulas</h1>" in htm)
for rel in ("docs/manual.html", "docs/ai-prompts.html", "docs/first-five-minutes.html"):
    nav = (re.search(r'<nav class="top">(.*?)</nav>', lees(rel), flags=re.S) or [None, ""])[1] if lees(rel) else ""
    eigen = rel.endswith("first-five-minutes.html")
    check(f"{rel}: de navigatie noemt First five minutes" + (" (zichzelf zonder link)" if eigen else ""),
          ("<span>First five minutes</span>" in nav) if eigen else ('<a href="first-five-minutes.html">First five minutes</a>' in nav))
figs = re.findall(r'<img src="(img/[^"]+)"', htm)
check(f"vier figuren, en elke figuur bestaat ({figs})",
      len(figs) == 4 and all(os.path.exists(os.path.join(DOCS, f)) for f in figs)
      and {"img/first-material-dialog.png", "img/first-formula.png", "img/first-compare.png"} <= set(figs))
ids = set(re.findall(r'<h2 id="([^"]+)"', lees("docs/manual.html")))
ankers = re.findall(r'href="manual\.html#([^"]+)"', htm)
check(f"elke link naar de handleiding wijst naar een bestaande sectie ({len(ankers)} links)",
      len(ankers) >= 10 and all(a in ids for a in ankers))
check("de app op je eigen pc of Mac: Download the app, Check for updates en Install as an app, met §14 en §15",
      all(x in htm for x in ("<strong>Download the app</strong>", "<strong>Check for updates</strong>",
                             "<strong>Install as an app</strong>", "manual.html#s14-", "manual.html#s15-")))
check("de pagina zelf staat niet in de app (de Help is de handleiding)", "Your first five minutes with miFormulas" not in lees("index.html"))
check("§1 van de handleiding en de README noemen de pagina", FIRST5 in lees("docs/manual.md") and FIRST5 in lees("README.md"))

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1400, "height": 900}, color_scheme="light")
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))

    page.goto(URL + "docs/first-five-minutes.html"); page.wait_for_timeout(600)
    page.evaluate("document.querySelectorAll('img').forEach(i => i.loading = 'eager')"); page.wait_for_timeout(600)
    check("de pagina op de site toont haar figuren",
          page.evaluate("[...document.images].length === 4 && [...document.images].every(i => i.complete && i.naturalWidth > 0)"))

    # ---------------- 2. de links in de app ----------------
    page.route("https://data.miformulas.com/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(LIB)))
    page.goto(URL); page.wait_for_timeout(800)
    a = page.locator("#btnFirstFive")
    check("het startscherm: New here? Your first five minutes, in een nieuw tabblad",
          a.is_visible() and a.get_attribute("href") == FIRST5 and a.get_attribute("target") == "_blank"
          and "New here?" in page.locator("#firstFive").inner_text())
    kleur = page.evaluate("""() => [getComputedStyle(document.querySelector('#btnFirstFive')).color,
        getComputedStyle(document.querySelector('#btnManual')).color]""")
    check(f"in de kleur van de andere links van het startscherm, niet het blauw van de browser ({kleur})", kleur[0] == kleur[1])
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    w = page.locator("#firstFiveHome")
    check("Welcome, Start here: dezelfde link zolang je niets van jezelf hebt",
          w.is_visible() and w.locator("a").get_attribute("href") == FIRST5 and "a material, a formula and a version" in w.inner_text())

    # ---------------- 3. de stappen van de pagina ----------------
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.click("#setListGet"); page.wait_for_timeout(900)
    check("Before you start: Get the latest library in Settings laadt de library",
          page.evaluate("!!(DATA.materialList && DATA.materialList.materials.some(m => m.name === 'Javanol'))"))
    check("en die voegt niets toe aan je inventory", page.evaluate("!DATA.materials.some(m => m.name === 'Javanol')"))
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.fill("#nmName", "Javanol"); page.wait_for_timeout(300)
    gevonden = page.inner_text("#nmFound")
    check(f"1. + New material…: de library kent Javanol en het venster toont CAS, piramide en IFRA ({gevonden[:70]!r})",
          "Javanol" in gevonden and "CAS 198404-98-7" in gevonden and "Base" in gevonden and "IFRA 99" in gevonden)
    check("en kiest de categorie; de knop heet Create", page.evaluate("$('#nmCat').value") == "Woody - sandal"
          and page.inner_text("#dlgOk").strip() == "Create")
    page.click("#dlgOk"); page.wait_for_timeout(600)
    jav = "() => DATA.materials.find(m => m.name === 'Javanol')"
    check("de materiaalpagina opent, met de feiten van de library; Javanol puur, zoals hij verkocht wordt",
          page.evaluate(f"(() => {{ const m = ({jav})(); return !!m && m.cas === '198404-98-7' && m.dilutions.length === 1 && m.dilutions[0].pct === 100 && VIEW.tab === 'M' && VIEW.id === m.id; }})()"))
    page.click("#dilBox summary"); page.wait_for_timeout(200)   # the guide: open Dilutions (closed to start since 261019c)
    page.fill("#newDil", "10"); page.click("#btnAddDil"); page.wait_for_timeout(400)
    check("Add dilution: de 10 % erbij",
          page.evaluate(f"(() => {{ const d = ({jav})().dilutions; return d.length === 2 && d.some(x => x.pct === 10) && d.some(x => x.pct === 100); }})()"))
    check("in de eigen inventory nu: Welcome noemt de eerste vijf minuten niet meer",
          page.evaluate("(() => { document.querySelector('#btnHome').click(); return !document.querySelector('#firstFiveHome'); })()"))

    page.click("#btnNew"); page.wait_for_timeout(400)
    page.fill("#nfName", "My first accord"); page.click("#dlgOk"); page.wait_for_timeout(600)
    check("2. + New formula…: My first accord, met een leeg Add material…",
          page.locator("#content h2").first.inner_text().startswith("My first accord") and page.get_attribute("#addMat", "placeholder") == "Add material…")
    page.click("#addMat")
    for n in ("Hedione", "Iso E Super", "Javanol", "Ethanol"):
        page.keyboard.type(n); page.keyboard.press("Enter"); page.wait_for_timeout(350)
    lijnen = "() => DATA.formulas.find(f => f.name === 'My first accord').versions.at(-1).lines.map(l => [matById(l.materialId).name, l.dilutionPct, l.weightG])"
    check(f"met het toetsenbord: naam en Enter, de cursor blijft in Add material…, de regel met gewicht 0 ({page.evaluate(lijnen)})",
          page.evaluate(lijnen) == [["Hedione", 100, 0], ["Iso E Super", 100, 0], ["Javanol", 100, 0], ["Ethanol", 100, 0]]
          and page.evaluate("document.activeElement.id") == "addMat")
    msgs.clear(); page.select_option('select[data-dil="2"]', "10"); page.wait_for_timeout(400)
    check(f"10 % kiezen bij Javanol: zonder vraag, want het gewicht is nog 0 ({msgs[:1]})",
          not msgs and not page.evaluate("$('#dlg').open") and page.evaluate(lijnen)[2][1] == 10)
    w0 = page.input_value('input.w[data-i="0"]')
    page.click('input.w[data-i="0"]', click_count=3)
    for i, g in enumerate(("4", "3", "0.2", "2.8")):
        page.keyboard.type(g); page.keyboard.press("Tab"); page.wait_for_timeout(350)
        if i < 3:
            sel = page.evaluate("(() => { const a = document.activeElement; return [a.dataset.i, a.selectionStart === 0 && a.selectionEnd === a.value.length]; })()")
            if sel != [str(i + 1), True]: print("     na Tab", i, sel)
    check(f"de gewichten: {w0} geselecteerd en 4 typen, Tab naar het volgende gewicht, al geselecteerd: 3, 0.2 en 2.8 ({page.evaluate(lijnen)})",
          w0 == "0.000" and page.evaluate(lijnen) == [["Hedione", 100, 4], ["Iso E Super", 100, 3], ["Javanol", 10, 0.2], ["Ethanol", 100, 2.8]])
    check("na het laatste gewicht staat de cursor weer in Add material…", page.evaluate("document.activeElement.id") == "addMat")
    page.click("#content h2"); page.wait_for_timeout(300)
    K = page.evaluate("""() => { const v = DATA.formulas.find(f => f.name === 'My first accord').versions.at(-1), K = calc(v.lines);
        return {abs: +K.totalAbsPct.toFixed(2), w: +K.totalW.toFixed(3), rel: K.rows.map(r => r.rel == null ? null : +r.rel.toFixed(2))}; }""")
    check(f"de figuur klopt: totaal 10 g, abs % 70.20, Javanol 0.28 rel % (binnen het gebruik van de library) ({K})",
          K["abs"] == 70.2 and K["w"] == 10 and K["rel"][3] is None and abs(sum(K["rel"][:3]) - 100) < 0.02 and K["rel"][2] == 0.28)

    page.click("#btnNewV"); page.wait_for_timeout(600)
    versies = "() => DATA.formulas.find(f => f.name === 'My first accord').versions.map(v => [v.v, v.name || '', v.lines.find(l => matById(l.materialId).name === 'Javanol').weightG])"
    check(f"3. + New version kopieert v1 naar v2 en toont v2 ({page.evaluate(versies)})",
          page.evaluate(versies) == [[1, "", 0.2], [2, "", 0.2]] and page.evaluate("VIEW.sub.idx") == 1)
    page.fill('input.w[data-i="2"]', "0.3"); page.press('input.w[data-i="2"]', "Enter"); page.wait_for_timeout(300)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(400)
    check("Ctrl+Z zet het gewicht terug", page.evaluate(versies)[1][2] == 0.2)
    page.fill('input.w[data-i="2"]', "0.3"); page.press('input.w[data-i="2"]', "Enter"); page.wait_for_timeout(300)
    page.click("#btnNameV"); page.wait_for_timeout(300)
    page.fill("#vnName", "more javanol"); page.click("#dlgOk"); page.wait_for_timeout(400)
    check(f"in v2 Javanol op 0.3 g en het label more javanol; v1 blijft zoals het was ({page.evaluate(versies)})",
          page.evaluate(versies) == [[1, "", 0.2], [2, "more javanol", 0.3]])
    page.evaluate("() => { VIEW.sub = {type: 'v', idx: 0}; render(); }")
    page.wait_for_timeout(300)
    check("v1 is bevroren: geen gewichtsvelden", page.locator("input.w").count() == 0 and "frozen" in page.inner_text("#content .fMeta"))
    page.evaluate("() => { VIEW.sub = {type: 'v', idx: 1}; render(); }"); page.wait_for_timeout(300)
    page.click("#btnCmp"); page.wait_for_timeout(500)
    rij = page.locator("#content table tbody tr").first.inner_text()
    check(f"Compare zet v1 en v2 more javanol naast elkaar, met Javanol bovenaan ({rij!r})",
          "v2 more javanol" in page.inner_text("#content") and rij.startswith("Javanol") and "+0.14" in rij)

    # ---------------- 4. waar je werk staat ----------------
    page.click("#btnCmpClose"); page.wait_for_timeout(300)
    page.click("#btnHome"); page.wait_for_timeout(400)
    check("Backup in de kop en Save to a data file… (Chrome en Edge) zijn er",
          page.locator("#btnBackup").is_visible() and "Save to a data file…" in page.inner_text("body"))
    page.click("#btnSettings"); page.wait_for_timeout(400)
    check("Download the app staat ook in Settings op de site", page.locator("#setDownload").is_visible()
          and page.inner_text("#setDownload").strip() == "Download the app")
    page.keyboard.press("Escape")
    check(f"geen fouten in de pagina ({errs[:2]})", not errs)

    # ---------------- 5. op een telefoon: de pagina zegt waar de knoppen daar staan ----------------
    IPHONE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
              "Mobile/15E148 Safari/604.1")
    ctx2 = b.new_context(viewport={"width": 430, "height": 932}, is_mobile=True, has_touch=True, user_agent=IPHONE)
    pg = ctx2.new_page(); pg.on("dialog", lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(800); pg.click("#btnStarter"); pg.wait_for_timeout(1500)
    pg.click("#btnHome"); pg.wait_for_timeout(400)
    check("op een telefoon staan + New material… en + New formula… niet in de kop, wel op Welcome onder Start here",
          not pg.locator("#btnNewMat").is_visible() and not pg.locator("#btnNew").is_visible()
          and pg.locator("#startHere #homeNewM").is_visible() and pg.locator("#startHere #homeNewF").is_visible())
    check("Settings (⚙) en de undo-pijl staan er wel in de kop", pg.locator("#btnSettings").is_visible() and pg.locator("#btnUndo").is_visible())
    pg.click("#homeNewM"); pg.wait_for_timeout(400)
    check("+ New material… opent ook daar", pg.evaluate("$('#dlg').open") and "New material" in pg.inner_text("#dlg h3"))
    ctx2.close()
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
