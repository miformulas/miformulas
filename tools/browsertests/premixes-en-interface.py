"""De premixes en de kleine interfacepunten van bouw 261002b (2/10/2026).
Premixes: Create premix… heet zo, met het venster, het achtervoegsel " - PREMIX", de IFRA-kop en één categorie
Premixes voor de formule en het materiaal, die de handeling zelf maakt (de starterset heeft er geen lege meer) en die
Undo met haar kleur terugneemt. Een premix staat stil: zonder zoekterm onderaan Materials in één dichte groep die met
een klik of Enter opengaat, met een zoekterm gewoon in de lijst; ook een oud materiaal in de categorie Predils; niet in
de tegel materials, niet bij Recently edited materials, niet in Export my inventory as a library…; en Share this
version… noemt de premix na het schrijven, een versie zonder premix niet.
Interface: + Add group staat boven de groepen; Pyramid base → top in de tabel, Compare en de bench (Base eerst, zonder
niveau achteraan, A–Z binnen een niveau); de tegels op Welcome openen wat ze tellen, ook met Enter, ook met een
verborgen lijst en op de telefoon; de regel onder de IFRA-check zonder "certificate", en de Help zonder predilution.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import json, sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

NOTE = "IFRA limits can be wrong or out of date. Check them against the current IFRA Standards."
RANK_UP = "p => p == null || p === 5 ? -1 : p"   # Base (4) eerst, dan omhoog, een materiaal zonder niveau achteraan

def tap(pg, sel):
    """Klikt als het element er is: op een oudere bouw faalt dan de controle, niet het hele script."""
    if pg.query_selector(sel):
        pg.click(sel); return True
    return False

def pick(pg, sel, val):
    if pg.query_selector(f"{sel} option[value='{val}']"):
        pg.select_option(sel, val); return True
    return False

def enter_on(pg, sel):
    if pg.query_selector(sel):
        pg.focus(sel); pg.keyboard.press("Enter"); return True
    return False

def open_formula(page, name, idx=None):
    page.evaluate("""([n, i]) => { const f = DATA.formulas.find(x => x.name === n);
      switchTab('F', f.id, {type:'v', idx: i == null ? f.versions.length - 1 : i}); }""", [name, idx])
    page.wait_for_timeout(500)

def base_to_top(levels_names):
    """True als de lijst (niveau, naam) van Base naar Top loopt, zonder niveau achteraan, A–Z binnen een niveau."""
    rank = lambda p: -1 if p is None or p == 5 else p
    keys = [(-rank(p), n.lower()) for p, n in levels_names]
    return keys == sorted(keys) and len(levels_names) > 3

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1600, "height": 950})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    def on_dialog(d): msgs.append(d.message); d.accept()
    page.on("dialog", on_dialog)
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(900)

    # ---------- de starterset draagt geen lege premix-categorieën meer
    cats = page.evaluate("""() => [DATA.materialCategories.includes("Predils"), DATA.formulaCategories.includes("Predilutions"),
      "Predils" in (DATA.categoryColours||{}), DATA.materialCategories.includes("Premixes"), DATA.formulaCategories.includes("Premixes")]""")
    check(f"de starterset heeft geen Predils, Predilutions of Premixes ({cats})", cats == [False, False, False, False, False])

    # ---------- de regel onder de IFRA-check
    open_formula(page, "Acqua di Gio for men")
    page.evaluate("() => { const d = document.getElementById('ifraBox'); if (d) d.open = true; }"); page.wait_for_timeout(200)
    nota = page.text_content("#ifraBox #ifraNote") if page.query_selector("#ifraBox #ifraNote") else ""
    check(f"onder de IFRA-check de korte regel ({nota!r})", nota.strip() == NOTE)

    # ---------- Share this version… zonder premix noemt niets
    msgs.clear()
    with page.expect_download() as dl:
        page.click("#btnShare")
    page.wait_for_timeout(400)
    check(f"Share this version… zonder premix: geen melding ({msgs})", not any("premix" in m for m in msgs))

    # ---------- Create premix…
    open_formula(page, "Acqua di Gio for men")
    knop = page.text_content("#btnPredil").strip()
    check(f"de knop heet Create premix… ({knop!r})", knop == "Create premix…")
    nlines = page.evaluate("() => currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines.length")
    for i in range(3):
        page.check(f'input.selCb[data-i="{i}"]')
    page.click("#btnPredil"); page.wait_for_timeout(400)
    titel = page.text_content("#dlg h3").strip()
    hint = page.text_content("#dlg .hint")
    naam = page.input_value("#pdName")
    check(f"het venster heet Create premix ({titel!r})", titel == "Create premix")
    check("het venster spreekt van one premix line", "one premix line" in hint)
    check(f"de voorgestelde naam eindigt op - PREMIX ({naam!r})", naam.endswith(" - PREMIX"))
    page.click("#dlgOk"); page.wait_for_timeout(600)
    res = page.evaluate("""(n) => { const m = DATA.materials.find(x => x.name === n), f = DATA.formulas.find(x => x.name === n),
        src = DATA.formulas.find(x => x.id === VIEW.id), v = currentVersion(src);
      return {mcat: m && m.category, flag: !!(m && m.isPredil), fcat: f && f.category, desc: m && m.description.slice(0, 11),
        fnote: f && f.versions[0].notes.slice(0, 11), vnote: (v.notes || "").slice(0, 8),
        mc: DATA.materialCategories.includes("Premixes"), fc: DATA.formulaCategories.includes("Premixes"),
        col: (DATA.categoryColours || {})["Premixes"], old: DATA.materialCategories.includes("Predils") || DATA.formulaCategories.includes("Predilutions")}; }""", naam)
    check(f"het materiaal staat in Premixes en draagt het kenmerk ({res['mcat']}, {res['flag']})", res["mcat"] == "Premixes" and res["flag"])
    check(f"de formule staat in Premixes ({res['fcat']})", res["fcat"] == "Premixes")
    check(f"de handeling maakt de categorie in beide lijsten, met haar kleur ({res['mc']}, {res['fc']}, {res['col']})",
          res["mc"] and res["fc"] and res["col"] == "#7A5EA8")
    check("geen Predils of Predilutions meer", not res["old"])
    check(f"de beschrijving en de notities zeggen Premix ({res['desc']!r}, {res['fnote']!r}, {res['vnote']!r})",
          res["desc"].startswith("Premix of") and res["fnote"].startswith("Premix for") and res["vnote"] == "Premix «")
    page.evaluate("() => { const d = document.getElementById('ifraBox'); if (d) d.open = true; }"); page.wait_for_timeout(200)
    kop = page.text_content("#ifraBox summary").strip()
    off = page.text_content("#ifraOff")
    check(f"de IFRA-kop zegt premix ({kop!r})", kop == "IFRA check – off (premix in this version)")
    check("en wijst naar Premixes", "the premix itself under Premixes" in off and "predil" not in off.lower())
    nlines2 = page.evaluate("() => currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines.length")
    check(f"de nieuwe versie heeft drie regels min één ({nlines} → {nlines2})", nlines2 == nlines - 2)

    # ---------- Undo neemt de categorie en de kleur mee terug, Redo zet ze terug
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    terug = page.evaluate("""() => [DATA.materialCategories.includes("Premixes"), DATA.formulaCategories.includes("Premixes"),
      "Premixes" in (DATA.categoryColours || {})]""")
    check(f"Undo neemt de categorie Premixes en haar kleur terug ({terug})", terug == [False, False, False])
    page.keyboard.press("Control+y"); page.wait_for_timeout(500)
    check("Redo zet de premix terug", page.evaluate("(n) => DATA.materials.some(x => x.name === n && x.isPredil)", naam))

    # ---------- Share this version… op de versie met de premix noemt haar
    open_formula(page, "Acqua di Gio for men")
    msgs.clear()
    with page.expect_download() as dl:
        page.click("#btnShare")
    page.wait_for_timeout(400)
    m = next((x for x in msgs if "premix" in x), "")
    check(f"Share this version… noemt de premix na het schrijven ({m[:90]!r})",
          f"uses the premix “{naam}”" in m and "share its formula as well" in m)
    pkg = json.load(open(dl.value.path(), encoding="utf-8"))
    check(f"het bestand zelf draagt de premix als één regel, zonder recept ({sum(l['material'] == naam for l in pkg['lines'])})",
          sum(l["material"] == naam for l in pkg["lines"]) == 1 and "Premix of" not in json.dumps(pkg))

    # ---------- stil in Materials
    page.evaluate("() => { QBY.M = ''; switchTab('M', null, null); }"); page.wait_for_timeout(400)
    lijst = page.evaluate("""(n) => ({items: [...document.querySelectorAll('#list .item')].map(e => e.textContent),
      head: (document.querySelector('#list [data-premixes]') || {}).textContent || null,
      open: (document.querySelector('#list [data-premixes]') || {getAttribute(){return null}}).getAttribute('aria-expanded'),
      last: (document.querySelector('#list > :last-child') || {}).hasAttribute ? document.querySelector('#list > :last-child').hasAttribute('data-premixes') : false})""", naam)
    check(f"zonder zoekterm staat de premix niet in de lijst ({sum(naam in t for t in lijst['items'])})",
          not any(naam in t for t in lijst["items"]) and len(lijst["items"]) >= 150)
    check(f"maar onderaan in een dichte groep Premixes ({lijst['head']!r}, {lijst['open']})",
          (lijst["head"] or "").replace("▸", "").strip().startswith("Premixes") and (lijst["head"] or "").strip().endswith("1")
          and lijst["open"] == "false" and lijst["last"])
    tap(page, "#list [data-premixes]"); page.wait_for_timeout(300)
    open1 = page.evaluate("""(n) => [(document.querySelector('#list [data-premixes]') || {getAttribute(){return null}}).getAttribute('aria-expanded'),
      [...document.querySelectorAll('#list .item')].some(e => e.textContent.includes(n))]""", naam)
    check(f"een klik opent de groep en toont de premix ({open1})", open1 == ["true", True])
    page.click(f"#list .item:has-text('{naam}')"); page.wait_for_timeout(400)
    check("de premix opent op haar pagina", page.evaluate("(n) => (matById(VIEW.id) || {}).name === n", naam))
    tap(page, "#list [data-premixes]"); page.wait_for_timeout(300)
    enter_on(page, "#list [data-premixes]"); page.wait_for_timeout(300)
    open2 = page.evaluate("() => [(document.querySelector('#list [data-premixes]') || {getAttribute(){return null}}).getAttribute('aria-expanded'), !!(document.activeElement && document.activeElement.hasAttribute('data-premixes'))]")
    check(f"dicht met een klik, open met Enter, en de focus blijft op de kop ({open2})", open2 == ["true", True])
    enter_on(page, "#list [data-premixes]"); page.wait_for_timeout(300)
    page.evaluate("() => { QBY.M = 'premix'; renderSidebar(); }"); page.wait_for_timeout(300)
    zoek = page.evaluate("""(n) => [[...document.querySelectorAll('#list .item')].some(e => e.textContent.includes(n)),
      !!document.querySelector('#list [data-premixes]')]""", naam)
    check(f"met een zoekterm staat de premix gewoon tussen de rest ({zoek})", zoek == [True, False])
    page.evaluate("""() => { QBY.M = ''; DATA.materials.push({id: 'm-oudpd', name: 'Oude predil', category: 'Predils', pyramid: 5,
      isSolvent: false, dilutions: [{pct: 50, isBase: true}]}); invalidateMats(); renderSidebar(); }"""); page.wait_for_timeout(300)
    oud = page.evaluate("""() => [[...document.querySelectorAll('#list .item')].some(e => e.textContent.includes('Oude predil')),
      (document.querySelector('#list [data-premixes]') || {}).textContent || '']""")
    check(f"een oud materiaal in Predils telt ook als premix ({oud})", not oud[0] and oud[1].strip().endswith("2"))
    page.evaluate("() => { DATA.materials = DATA.materials.filter(m => m.id !== 'm-oudpd'); invalidateMats(); renderSidebar(); }")

    # ---------- Welcome: de tegel en Recently edited materials
    page.click("#btnHome"); page.wait_for_timeout(500)
    tegel = page.evaluate("""() => { const t = [...document.querySelectorAll('.tile')].find(e => e.textContent.includes('materials'));
      return [+t.querySelector('b').textContent, DATA.materials.length, DATA.materials.filter(m => !isPredil(m)).length]; }""")
    check(f"de tegel materials telt de premix niet ({tegel})", tegel[0] == tegel[2] and tegel[1] == tegel[2] + 1)
    recent = page.evaluate("""() => { const h = [...document.querySelectorAll('.panelBox h3')].find(e => e.textContent === 'Recently edited materials');
      return h ? h.parentElement.textContent : null; }""")
    check(f"Recently edited materials toont de premix niet ({(recent or '')[:60]!r})", recent is not None and naam not in recent)

    # ---------- Export my inventory as a library… biedt de premix niet aan
    page.evaluate("() => exportInventoryLibrary()"); page.wait_for_timeout(400)
    rows = page.text_content("#exRows"); teller = page.text_content("#exCount")
    check(f"Export my inventory as a library… biedt de premix niet aan ({teller!r})", naam not in rows and f"of {tegel[2]} shown" in teller)
    page.keyboard.press("Escape"); page.wait_for_timeout(300)

    # ---------- de tegels openen wat ze tellen
    page.click("#btnHome"); page.wait_for_timeout(400)
    tap(page, ".tile[data-tile='M']"); page.wait_for_timeout(400)
    st = page.evaluate("() => [VIEW.tab, document.getElementById('tabM').classList.contains('active'), document.querySelectorAll('#list .item').length]")
    check(f"de tegel materials opent de lijst Materials ({st})", st[0] == "M" and st[1] and st[2] > 100)
    page.click("#btnHome"); page.wait_for_timeout(400)
    tap(page, ".tile[data-tile='T']"); page.wait_for_timeout(400)
    st = page.evaluate("() => [VIEW.tab, (document.querySelector('#content h2') || {}).textContent]")
    check(f"de tegel to order opent To order ({st})", st == ["T", "To order"])
    page.click("#btnHome"); page.wait_for_timeout(400)
    page.evaluate("() => document.body.classList.add('hidebar')")
    tiles = page.evaluate("() => [...document.querySelectorAll('.tile')].map(t => t.dataset.tile)")
    check(f"de vier tegels: formulas en versions naar Formulas, materials, to order ({tiles})", tiles == ["F", "F", "M", "T"])
    enter_on(page, ".tile[data-tile='F']"); page.wait_for_timeout(400)
    st = page.evaluate("() => [VIEW.tab, document.body.classList.contains('hidebar'), document.querySelectorAll('#list .item').length]")
    check(f"Enter op de tegel formulas opent de lijst, ook als ☰ ze verborg ({st})", st[0] == "F" and not st[1] and st[2] >= 16)

    # ---------- + Add group boven de groepen
    open_formula(page, "Acqua di Gio for men")
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    pos = page.evaluate("""() => { const btn = document.getElementById('btnAddGroup'), g0 = document.querySelector('[data-bgi="0"]'),
        col = document.querySelector('.benchWrap').children[1], bar = document.getElementById('bMoveSel').parentElement;
      return [col.contains(btn), !bar.contains(btn), btn.getBoundingClientRect().bottom <= g0.getBoundingClientRect().top + 1,
              col.firstElementChild.contains(btn)]; }""")
    check(f"+ Add group staat boven de groepen, niet in de werkbalk ({pos})", pos == [True, True, True, True])
    n0 = page.evaluate("() => document.querySelectorAll('[data-bgi]').length")
    page.click("#btnAddGroup"); page.wait_for_timeout(300)
    n1 = page.evaluate("() => document.querySelectorAll('[data-bgi]').length")
    check(f"+ Add group maakt een groep ({n0} → {n1})", n1 == n0 + 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)

    # ---------- Pyramid base → top: bench, tabel, Compare
    opts = page.evaluate("() => [...document.querySelectorAll('#bSortSel option')].map(o => o.textContent)")
    check(f"de bench kent beide piramidevolgordes ({opts[-2:]})", opts[-2:] == ["Pyramid top → base", "Pyramid base → top"])
    pick(page, "#bSortSel", "pyrb"); page.wait_for_timeout(300)
    pool = page.evaluate("""() => [...document.querySelectorAll('.blist[data-bdrop="pool"] .bname')].map(e => {
        const n = e.firstChild.textContent.replace(/ \\((solvent|to order)\\)$/, '').trim(), m = DATA.materials.find(x => x.name === n);
        return [m ? (m.pyramid ?? null) : null, n]; })""")
    check(f"bench: Pyramid base → top loopt van Base naar Top ({[x[0] for x in pool][:6]}…)", base_to_top([tuple(x) for x in pool]))
    page.click("#btnBenchToggle"); page.wait_for_timeout(400)
    opts = page.evaluate("() => [...document.querySelectorAll('#sortSel option')].map(o => o.textContent)")
    check(f"Order kent Pyramid base → top ({opts[:4]})", "Pyramid base → top" in opts and opts.index("Pyramid base → top") == opts.index("Pyramid top → base") + 1)
    pick(page, "#sortSel", "pyrb"); page.wait_for_timeout(400)
    rows = page.evaluate("""() => [...document.querySelectorAll('table.ftable tbody tr a.matlink')].map(a => {
        const m = matById(a.dataset.mat); return [m.pyramid ?? null, m.name]; })""")
    check(f"tabel: Pyramid base → top loopt van Base naar Top, zonder niveau achteraan ({[x[0] for x in rows][:6]}…{[x[0] for x in rows][-3:]})",
          base_to_top([tuple(x) for x in rows]))
    page.select_option("#sortSel", "pyr"); page.wait_for_timeout(400)
    rows2 = page.evaluate("""() => [...document.querySelectorAll('table.ftable tbody tr a.matlink')].map(a => matById(a.dataset.mat).pyramid ?? null)""")
    lv = lambda p: 9 if p is None or p == 5 else p
    check("en Pyramid top → base blijft van Top naar Base", [lv(x) for x in rows2] == sorted(lv(x) for x in rows2))
    pick(page, "#sortSel", "pyrb"); page.wait_for_timeout(300)
    page.click("#btnCmp"); page.wait_for_timeout(500)
    cs = page.evaluate("() => [document.getElementById('cmpSortSel').value, [...document.querySelectorAll('#cmpSortSel option')].map(o => o.textContent)]")
    check(f"Compare neemt base → top over uit de tabel ({cs[0]})", cs[0] == "pyrb" and "Pyramid base → top" in cs[1])
    crow = page.evaluate("""() => [...document.querySelectorAll('#content table.lines tbody tr')].map(tr => {
        const n = tr.cells[0].textContent.replace(/ \\(solvent\\)$/, '').trim(), m = DATA.materials.find(x => x.name === n);
        return [m ? (m.pyramid ?? null) : null, n]; })""")
    check(f"Compare: Pyramid base → top loopt van Base naar Top ({len(crow)} regels)", base_to_top([tuple(x) for x in crow]))
    page.click("#btnCmpClose"); page.wait_for_timeout(300)
    page.select_option("#sortSel", "orig"); page.wait_for_timeout(200)

    # ---------- de Help zegt premix en kent geen certificaat
    help_ = page.evaluate("() => document.getElementById('manualTpl').innerHTML")
    check(f"de Help zegt nergens predilution ({help_.lower().count('predilution')})", "predilution" not in help_.lower())
    check("en nergens IFRA certificate", "certificate" not in help_.lower())
    check("§8 heet Batch scaling and premixes", "8. Batch scaling and premixes" in help_)

    check(f"geen paginafouten ({errs[:2]})", not errs)

    # ---------- de telefoon: een tegel opent de lijst
    ph = b.new_context(viewport={"width": 390, "height": 844})
    pp = ph.new_page()
    perrs = []
    pp.on("pageerror", lambda e: perrs.append(str(e)))
    pp.on("dialog", lambda d: d.accept())
    pp.goto(URL); pp.wait_for_timeout(800)
    pp.click("#btnStarter"); pp.wait_for_timeout(900)
    pp.click("#btnHome"); pp.wait_for_timeout(400)
    vooraf = pp.evaluate("() => document.body.classList.contains('detail')")
    tap(pp, ".tile[data-tile='F']"); pp.wait_for_timeout(400)
    st = pp.evaluate("() => [document.body.classList.contains('detail'), getComputedStyle(document.getElementById('sidebar')).display, document.querySelectorAll('#list .item').length]")
    check(f"telefoon: de tegel formulas toont de lijst ({vooraf} → {st})", vooraf and not st[0] and st[1] != "none" and st[2] >= 16)
    pp.click("#btnBack") if pp.is_visible("#btnBack") else None
    pp.click("#btnHome"); pp.wait_for_timeout(400)
    tap(pp, ".tile[data-tile='M']"); pp.wait_for_timeout(400)
    st = pp.evaluate("() => [VIEW.tab, document.body.classList.contains('detail'), document.querySelectorAll('#list .item').length]")
    check(f"telefoon: de tegel materials toont de lijst Materials ({st})", st[0] == "M" and not st[1] and st[2] > 100)
    check(f"telefoon: geen paginafouten ({perrs[:2]})", not perrs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
