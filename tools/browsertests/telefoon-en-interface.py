"""De telefoon en de interface (bouw 260922l, ronde 4 van de vijfde audit).
B24: de formuletabel op de telefoon geeft de naam de ruimte (390 en 360 px), zonder afgeknipte vakken of koppen.
B25: de bench view op de telefoon houdt het gewicht in beeld. B26 en C11: elk venster past op de telefoon, de hoofdknop
staat erin en onder de knoppenrij schemert niets door. C-e 34: tussen 701 en 1366 px valt geen knop of kolom meer
buiten beeld (bestellijst, formuletabel naast de lijst). 35: --muted haalt 4,5:1 op elk licht vlak, de bench inbegrepen.
36: Ctrl+S in een venster opent het opslagvenster van de browser niet. 37: elk venster heeft een naam, vier velden een
label. 38: Delivered toont "Density g/ml" alleen bij ml. 39: de koptekst blijft op één rij (bestandsnaam, AM/PM,
geïnstalleerde app). 40: Ctrl+P vanuit de handleiding. 41: de Formulair-importer in de kleuren en het thema van de app.
42: kleinigheden (–% in de bench, ✕, links in vensters, veldnamen, kleurstalen, het tabblad To order, Import & export).
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import json
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
URL = BASE + "/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)
def lum(h):
    h = h.lstrip("#"); c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True); return (la + 0.05) / (lb + 0.05)
STANDALONE = """(() => { const mm = window.matchMedia.bind(window); window.matchMedia = q => /display-mode:\\s*standalone/.test(q)
    ? {matches: true, media: q, addEventListener(){}, removeEventListener(){}, addListener(){}, removeListener(){}} : mm(q); })();"""
FIRST5 = "DATA.formulas.find(x => (x.versions.at(-1).lines || []).length >= 5)"

with sync_playwright() as p:
    b = p.chromium.launch()
    def start(W, H=900, phone=False, locale="en-GB", init=None, scheme=None):
        opts = {"viewport": {"width": W, "height": H}, "locale": locale}
        if phone: opts.update(is_mobile=True, has_touch=True, device_scale_factor=3)
        if scheme: opts["color_scheme"] = scheme
        ctx = b.new_context(**opts); pg = ctx.new_page(); pg.msgs = []
        pg.on("dialog", lambda d: (pg.msgs.append(d.message), d.accept()))
        if init: pg.add_init_script(init)
        pg.goto(URL); pg.wait_for_timeout(800)
        pg.click("#btnStarter"); pg.wait_for_timeout(1500)
        return pg
    def open_formula(pg):
        pg.evaluate(f"() => switchTab('F', {FIRST5}.id, null)"); pg.wait_for_timeout(700)
    js = lambda pg, sel: pg.evaluate(f"document.querySelector({json.dumps(sel)})?.click()")
    def closedlg(pg):
        pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
        if pg.evaluate("document.querySelector('#dlg').open"): pg.evaluate("document.querySelector('#dlg').close()")

    # ---------- B24, B25, B26 and C11: the phone ----------
    for W, H in ((390, 844), (360, 800)):
        pg = start(W, H, phone=True)
        open_formula(pg)
        t = pg.evaluate("""() => { const t = document.querySelector('#content table.ftable') || document.querySelector('#content table.lines');
            const ths = [...t.querySelectorAll('thead th')].filter(x => x.offsetParent);
            const col = k => { const th = ths.find(x => x.querySelector(`[data-sort="${k}"]`)); return th ? Math.round(th.getBoundingClientRect().width) : 0; };
            const cb = ths[0] && !ths[0].textContent.trim() ? Math.round(ths[0].getBoundingClientRect().width) : 0;
            const cut = el => el.scrollWidth > el.clientWidth + 1;
            const rows = [...t.querySelectorAll('tbody tr')].slice(0, 8);
            const inCell = sel => rows.every(r => { const e = r.querySelector(sel); if (!e) return true; const a = e.getBoundingClientRect(), c = e.closest('td').getBoundingClientRect();
                return a.right <= c.right + 0.5 && a.left >= c.left - 0.5; });
            return {name: col('name'), cb, headCut: ths.filter(x => x.textContent.trim() && cut(x)).map(x => x.textContent.trim()),
                    namesCut: rows.map(r => r.querySelector('a.matlink')).filter(a => a && (cut(a) || cut(a.closest('td')))).map(a => a.textContent),
                    dilInCell: inCell('select.d'), wInCell: inCell('input.w'), tableFits: t.getBoundingClientRect().width <= t.parentElement.clientWidth + 0.5}; }""")
        check(f"{W} px: de formuletabel geeft de naam de ruimte, niet het vinkje (naam {t['name']} px, vinkje {t['cb']} px)",
              t["name"] >= 60 and t["cb"] and t["name"] > 2 * t["cb"])
        check(f"{W} px: geen afgekapte materiaalnaam ({t['namesCut']}) en geen afgekapte kop ({t['headCut']})", not t["namesCut"] and not t["headCut"])
        check(f"{W} px: de dilutiekeuze en het gewichtsveld staan heel in hun vak, de tabel past", t["dilInCell"] and t["wInCell"] and t["tableFits"])
        bb = pg.locator(".benchBtn")
        if bb.count(): bb.first.click(); pg.wait_for_timeout(700)
        bench = pg.evaluate("""() => { const c = document.querySelector('#content'), p = document.querySelector('.bpanel');
            const bw = [...document.querySelectorAll('.brow .bw')].slice(0, 6);
            return {scroll: c.scrollWidth - c.clientWidth, panelRight: p ? Math.round(p.getBoundingClientRect().right) : 9999, vw: innerWidth,
                    weights: bw.map(x => [x.textContent, Math.round(x.getBoundingClientRect().right), x.scrollWidth <= x.clientWidth])}; }""")
        check(f"{W} px: de bench view past op het scherm (paneel tot {bench['panelRight']} px, pagina schuift {bench['scroll']} px)",
              bench["panelRight"] <= bench["vw"] and bench["scroll"] == 0)
        check(f"{W} px: elk gewicht staat volledig in beeld ({bench['weights'][:2]})",
              bench["weights"] and all(r <= bench["vw"] and whole for _, r, whole in bench["weights"]))
        if bb.count(): pg.locator(".benchBtn").first.click(); pg.wait_for_timeout(500)
        dl = {}
        def measure(name):
            pg.wait_for_timeout(450)
            dl[name] = pg.evaluate("""() => { const d = document.querySelector('#dlg'); if (!d.open) return null;
                const ok = document.querySelector('#dlgOk'), r = d.getBoundingClientRect();
                return {over: d.scrollWidth - d.clientWidth, okIn: ok ? ok.getBoundingClientRect().right <= r.right + 0.5 : false}; }""")
            closedlg(pg)
        js(pg, "#btnSettings"); measure("Settings")
        js(pg, "#btnIO"); measure("Import & export")
        js(pg, "#btnNameV"); measure("Name version")
        js(pg, "#btnCopyF"); measure("Copy")
        js(pg, "#btnCatF"); measure("Change category")
        js(pg, ".replBtn"); measure("Replace")
        pg.evaluate("() => { [...document.querySelectorAll('.selCb')].slice(0, 2).forEach(c => { c.checked = true; c.dispatchEvent(new Event('change', {bubbles: true})); }); }")
        pg.wait_for_timeout(300)
        js(pg, "#btnPredil"); measure("Create predilution")
        pg.evaluate("""() => { DATA.orderList.push({name: "Iso E Super", note: "", amount: "", unit: "g", price: "", url: ""}); markDirty(); switchTab('T'); }""")
        pg.wait_for_timeout(700)
        js(pg, "#btnShops"); measure("shop list")
        js(pg, "[data-odeliv]"); measure("Delivered")
        bad = {k: v for k, v in dl.items() if not v or v["over"] > 0 or not v["okIn"]}
        check(f"{W} px: elk van de {len(dl)} vensters past en heeft zijn knop erin ({bad})", not bad)
        js(pg, "#btnSettings"); pg.wait_for_timeout(450)
        gap = pg.evaluate("""() => { const d = document.querySelector('#dlg'), row = document.querySelector('#dlgOk').parentElement;
            d.scrollTop = Math.max(0, (d.scrollHeight - d.clientHeight) / 2);
            return Math.round(d.getBoundingClientRect().bottom - row.getBoundingClientRect().bottom); }""")
        check(f"{W} px: de knoppenrij sluit onderaan af, er schemert niets onder door ({gap} px)", 0 <= gap <= 2)
        pg.context.close()

    # ---------- C-e 34: between 701 and 1366 px ----------
    for W in (1280, 1366):
        pg = start(W)
        pg.evaluate("""() => { DATA.orderList.push({name: "Iso E Super", note: "for the vetiver accord, 2 bottles", amount: "100", unit: "g", price: "18.50",
            url: "https://www.example-shop.com/products/iso-e-super-100g", added: "2026-09-20"}); markDirty(); switchTab('T'); }""")
        pg.wait_for_timeout(700)
        o = pg.evaluate("""() => { const w = document.querySelector('#content .tblwrap'), r = w.getBoundingClientRect();
            const dv = document.querySelector('[data-odeliv]'), x = document.querySelector('[data-odel]');
            return {scroll: w.scrollWidth - w.clientWidth, dv: dv.getBoundingClientRect().right <= r.right + 0.5, x: x.getBoundingClientRect().right <= r.right + 0.5}; }""")
        check(f"{W} px: in de bestellijst staan Delivered… en ✕ in beeld ({o})", o["dv"] and o["x"] and o["scroll"] == 0)
        pg.context.close()
    for W in (760, 850):
        pg = start(W)
        pg.evaluate(f"() => {{ DATA.materials.forEach((m, i) => {{ if (i % 3 === 0) m.costPerGram = 0.5; }}); markDirty(); switchTab('F', {FIRST5}.id, null); }}")
        pg.wait_for_timeout(700)
        f = pg.evaluate("""() => { const t = document.querySelector('#content table.lines'), w = t.parentElement, r = w.getBoundingClientRect();
            return {scroll: w.scrollWidth - w.clientWidth, beyond: [...t.querySelectorAll('thead th')].filter(x => x.offsetParent && x.getBoundingClientRect().right > r.right + 1).map(x => x.textContent.trim() || '(knoppen)')}; }""")
        check(f"{W} px met de lijst ernaast: de formuletabel past, met Rel % en ✕ ({f})", f["scroll"] == 0 and not f["beyond"])
        if W == 850:
            pg.keyboard.press("Control+b"); pg.wait_for_timeout(500)
            full = pg.evaluate("() => [...document.querySelectorAll('#content table.lines thead th')].filter(x => x.offsetParent).map(x => x.textContent.trim())")
            check(f"850 px zonder de lijst: de volle tabel, met Abs % en Cost ({full})", any("Abs" in x for x in full) and any("Cost" in x for x in full))
        pg.context.close()

    # ---------- C-e 35 to 38, 40 and 42 on one desktop page ----------
    pg = start(1280)
    k = pg.evaluate("""() => { const cs = getComputedStyle(document.documentElement); const g = n => cs.getPropertyValue(n).trim();
        return {muted: g('--muted'), soft: g('--accent-soft'), bench: g('--bench'), bench2: g('--bench2'), panel: g('--panel')}; }""")
    worst = min(ratio(k["muted"], k[v]) for v in ("soft", "bench", "bench2", "panel"))
    check(f"--muted haalt 4,5:1 op de roze selectie, de bench en het paneel (slechtste {worst:.3f}:1)", worst >= 4.5)
    pg.evaluate("() => { window.__s = []; window.addEventListener('keydown', e => { if (e.key === 's') window.__s.push(e.defaultPrevented); }); }")
    pg.click("#btnSettings"); pg.wait_for_timeout(400)
    pg.keyboard.press("Control+s"); pg.wait_for_timeout(200)
    check(f"Ctrl+S in een venster opent het opslagvenster van de browser niet ({pg.evaluate('window.__s')})",
          pg.evaluate("window.__s") == [True] and pg.evaluate("document.querySelector('#dlg').open"))
    nm = pg.evaluate("() => { const d = document.querySelector('#dlg'), id = d.getAttribute('aria-labelledby'); return id && document.getElementById(id) ? document.getElementById(id).textContent.trim() : null; }")
    check(f"Settings heeft zijn titel als naam ({nm!r})", nm == "Settings")
    closedlg(pg)
    pg.click("#btnIO"); pg.wait_for_timeout(400)
    nm = pg.evaluate("() => { const d = document.querySelector('#dlg'), id = d.getAttribute('aria-labelledby'); return id && document.getElementById(id) ? document.getElementById(id).textContent.trim() : null; }")
    check(f"Import & export ook ({nm!r})", nm == "Import & export")
    lk = pg.evaluate("() => [getComputedStyle(document.querySelector('#ioTpl')).color, getComputedStyle(document.querySelector('#dlg .hint a[target]')).color]")
    check(f"links in een venster in de accentkleur, niet in browserblauw ({lk})", lk[0] == lk[1] == "rgb(126, 27, 98)")
    closedlg(pg)
    named = lambda sel: pg.evaluate(f"() => {{ const s = document.querySelector({json.dumps(sel)}); return !!(s && (s.labels.length || s.getAttribute('aria-label'))); }}")
    open_formula(pg)
    pg.click("#btnCatF"); pg.wait_for_timeout(400)
    cat = named("#catSel"); closedlg(pg)
    pg.evaluate("""() => { DATA.orderList.push({name: "Iso E Super", note: "", amount: "", unit: "g", price: "", url: ""}); markDirty(); switchTab('T'); }""")
    pg.wait_for_timeout(600)
    pg.click("#btnShops"); pg.wait_for_timeout(400)
    shops = named("#shopsEd"); closedlg(pg)
    pg.click("[data-odeliv]"); pg.wait_for_timeout(500)
    unit = named("#dvU")
    check(f"Change category, de winkellijst en de eenheid in Delivered hebben een naam ({cat}, {shops}, {unit})", cat and shops and unit)
    dens = pg.evaluate("() => getComputedStyle(document.querySelector('#dvDensL')).display")
    check(f"Delivered in gram: geen los label Density g/ml ({dens})", dens == "none")
    pg.select_option("#dvU", "ml"); pg.wait_for_timeout(300)
    dens = pg.evaluate("() => [getComputedStyle(document.querySelector('#dvDensL')).display, getComputedStyle(document.querySelector('#dvDensW')).display]")
    check(f"in ml: het label en het veld samen ({dens})", dens[0] != "none" and dens[1] != "none")
    closedlg(pg)
    tabs = pg.evaluate("() => [...document.querySelectorAll('#tabs button')].map(x => [x.textContent.trim(), Math.round(x.getBoundingClientRect().height)])")
    lh = pg.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#tabT')).lineHeight)")
    check(f"het tabblad To order houdt zijn telling op één regel ({tabs}, regelhoogte {lh})", "(" in tabs[2][0] and tabs[2][1] < 2 * lh)
    io_title = pg.evaluate("document.querySelector('#btnIO').title")
    check(f"de knop ⇅ heet Import & export ({io_title[:16]!r})", io_title.startswith("Import & export"))
    check("de balk over de browseropslag sluit met ✕ zoals de rest", pg.evaluate("document.querySelector('#storageHintClose').textContent") == "✕")
    pg.click("#btnHome"); pg.wait_for_timeout(400)
    check("de Welcome-pagina noemt het venster Import & export", pg.evaluate("document.querySelector('#homeIO') && document.querySelector('#homeIO').textContent") == "Import & export")
    pg.evaluate("id => switchTab('M', id, null)", pg.evaluate("DATA.materials[0].id")); pg.wait_for_timeout(500)
    lab = pg.evaluate("""() => { const all = [...document.querySelectorAll('#content .fieldGrid > label, #content .fieldGrid > span')];
        const pick = t => all.find(x => x.textContent.trim() === t); const st = e => e ? [getComputedStyle(e).color, getComputedStyle(e).fontSize] : null;
        return {Name: st(pick('Name')), Storage: st(pick('Storage')), Pyramid: st(pick('Pyramid'))}; }""")
    check(f"Storage en Pyramid zien eruit als de andere veldnamen ({lab})", lab["Name"] and lab["Storage"] == lab["Name"] and lab["Pyramid"] == lab["Name"])
    # a formula with a solvent line: "–" in the bench, not "–%"
    fid = pg.evaluate("""() => { const f = DATA.formulas.find(x => (x.versions.at(-1).lines || []).some(l => { const m = matById(l.materialId); return m && m.isSolvent; })); return f ? f.id : null; }""")
    if fid:
        pg.evaluate("id => switchTab('F', id, null)", fid); pg.wait_for_timeout(600)
        pg.locator(".benchBtn").first.click(); pg.wait_for_timeout(600)
        sv = pg.evaluate("() => [...document.querySelectorAll('.bp')].map(x => x.textContent).filter(t => t.startsWith('–'))")
        check(f"de bench toont bij een solvent – zoals de tabel, niet –% ({sv})", sv and all(t == "–" for t in sv))
        pg.locator(".benchBtn").first.click(); pg.wait_for_timeout(400)
    else:
        check("de starterset heeft een formule met een solvent", False)
    # Ctrl+P from the manual
    pg.evaluate(f"() => switchTab('F', {FIRST5}.id, {{type: 'v', idx: 0}})"); pg.wait_for_timeout(500)
    pg.click("#btnHelp"); pg.wait_for_timeout(600)
    pg.evaluate("() => { document.querySelector('#printArea').innerHTML = ''; window.dispatchEvent(new Event('beforeprint')); }")
    pr = pg.evaluate("() => document.querySelector('#printArea').innerText")
    check(f"Ctrl+P vanuit de handleiding drukt geen weegblad af, maar wijst naar de afdrukbare handleiding ({pr[:60]!r})",
          "manual" in pr and "miformulas.com/docs/manual.html" in pr and "Weight (g)" not in pr)
    pg.context.close()

    # ---------- C-e 39: the header on one row ----------
    for loc in ("en-US", "en-GB"):
        rows = {}
        for W in (1301, 1330, 1366):
            pg = start(W, locale=loc)
            pg.evaluate("() => setState('Saved ' + new Date(2026, 8, 20, 20, 54).toLocaleTimeString(LOCALE, {hour:'2-digit', minute:'2-digit'}), 'miformulas-data.json', false)")
            pg.wait_for_timeout(150)
            rows[W] = pg.evaluate("() => Math.round(document.querySelector('header').getBoundingClientRect().height)")
            pg.context.close()
        check(f"{loc}, met de naam van het databestand: de kop blijft op één rij op 1301, 1330 en 1366 px ({rows})", len(set(rows.values())) == 1 and max(rows.values()) < 60)
    pg = start(1440, locale="en-US")
    pg.evaluate("() => setState('Saved 20:54', 'miformulas-data.json', false)"); pg.wait_for_timeout(150)
    check("op 1440 px staat de plaats er nog bij", pg.evaluate("getComputedStyle(document.querySelector('#stWhere')).display") != "none")
    pg.context.close()
    sa = {}
    for W in (1280, 1320, 1440):
        pg = start(W, init=STANDALONE)
        sa[W] = pg.evaluate("() => [Math.round(document.querySelector('header').getBoundingClientRect().height), getComputedStyle(document.querySelector('#build')).display]")
        pg.context.close()
    check(f"de geïnstalleerde app houdt de kop op één rij op 1280 en 1320 px ({sa})", sa[1280][0] < 60 and sa[1320][0] < 60)
    check("en toont daar de bouwstempel pas weer op een breed scherm", sa[1280][1] == "none" and sa[1440][1] != "none")

    # ---------- C-e 42: a colour swatch on a touch screen ----------
    pg = start(390, 844, phone=True)
    sw = pg.evaluate("() => { const s = document.createElement('span'); s.className = 'swatch'; document.body.append(s); const w = s.getBoundingClientRect().width; s.remove(); return w; }")
    check(f"een kleurstaal is op een aanraakscherm minstens 24 px ({sw})", sw >= 23.9)
    pg.context.close()

    # ---------- C-e 41: the Formulair importer ----------
    FI = BASE + "/formulair-import.html"
    def fi(scheme, theme=None):
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, color_scheme=scheme); pg = ctx.new_page()
        pg.goto(URL); pg.wait_for_timeout(300)
        pg.evaluate(f"() => {{ if ({json.dumps(theme)}) localStorage.setItem('miformulas-theme', {json.dumps(theme)}); else localStorage.removeItem('miformulas-theme'); }}")
        pg.goto(FI); pg.wait_for_timeout(500)
        r = pg.evaluate("""() => { const cs = getComputedStyle(document.documentElement), g = n => cs.getPropertyValue(n).trim(), a = document.querySelector('main a[href*="manual"]');
            return {ground: g('--ground'), muted: g('--muted'), link: a ? getComputedStyle(a).color : null,
                    btn: (() => { const x = document.createElement('button'); x.className = 'primary'; document.body.append(x);   // the real one is made later
                                  const v = getComputedStyle(x).backgroundImage; x.remove(); return v; })()}; }""")
        ctx.close(); return r
    lt = fi("light")
    check(f"importer, licht: het grijs van de app ({lt['muted']}) en de link in de accentkleur ({lt['link']})", lt["muted"].lower() == "#5a6773" and lt["link"] == "rgb(126, 27, 98)")
    dk = fi("dark")
    check(f"importer, donker systeem: de donkere kleuren van de app ({dk['ground']}), link {dk['link']}", dk["ground"].lower() == "#1c1122" and dk["link"] == "rgb(240, 140, 197)")
    ch = fi("dark", "light")
    check(f"importer: Light gekozen in de app wint van een donker systeem ({ch['ground']})", ch["ground"].lower() == "#fbfcfd")
    ch = fi("light", "dark")
    check(f"importer: Dark gekozen in de app wint van een licht systeem ({ch['ground']})", ch["ground"].lower() == "#1c1122")
    check(f"importer: de hoofdknop in het verloop van de app ({lt['btn'][:40]})", "gradient" in (lt["btn"] or ""))
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
