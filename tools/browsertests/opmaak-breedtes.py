"""Bouw 261019d: geen scherm loopt over zichzelf, op gangbare breedtes (UX-audit van 19/10, ronde 1).
De controle van lezer A van de audit (overlap, uitsteken, buiten de pagina, zijwaarts schuiven), op de formulapagina, de
bench view, Compare, een materiaalpagina met Dilutions en Stock open, de lijst, Import formula en vijf vensters, van 701 tot 1940 px met de
lijst open en dicht en op een telefoon; daarnaast wat de audit apart vond: de kop van een formule met een lange importnaam
in twee rijen, de bench view in twee kolommen waar de pagina plaats heeft, de kop die niet springt bij een wijziging, en
de afdruk (Total één keer, licht ook vanuit het donkere thema). Met de starterset en een paar namen die lang zijn zoals in
echte data. Draait op de lokale webserver (poort 8765, zie README)."""
import json, os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
HERE = os.path.dirname(os.path.abspath(__file__))
GEPUB = os.path.join(HERE, "..", "..", "..", "miformulas-materials.json")
LIB = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else {
    "type": "miformulas-materials", "name": "Kleine library", "version": "2026-10-19", "licence": "CC BY 4.0",
    "materials": [{"name": "Javanol", "cas": "198404-98-7", "category": "Woody - sandal", "pyramid": 4, "ifraLimit": 99}]}
PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
            "Mobile/15E148 Safari/604.1")
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

# the check of reader A (UX audit, 19/10): a list of problems in a part of the page
CHECK_JS = r"""
(opts) => {
  const scope = document.querySelector(opts.scope) || document.body, TOL = 2, TOLH = 3, out = [], seen = new Set();
  const push = p => { const k = p.kind + "|" + p.el + "|" + (p.other || ""); if (!seen.has(k)){ seen.add(k); out.push(p); } };
  const de = document.documentElement, vw = de.clientWidth;
  const desc = el => { let s = el.tagName.toLowerCase(); if (el.id) s += "#" + el.id; else if (typeof el.className === "string" && el.className.trim()) s += "." + el.className.trim().split(/\s+/)[0];
    const t = (el.tagName === "SELECT" ? el.selectedOptions[0]?.textContent : el.tagName === "INPUT" ? el.value || el.placeholder : el.innerText || "") || "";
    return t.trim() ? `${s} «${t.trim().replace(/\s+/g, " ").slice(0, 30)}»` : s; };
  const shown = el => { if (!el.getClientRects().length) return false;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement){ const cs = getComputedStyle(a);
      if (cs.visibility === "hidden" || cs.display === "none" || +cs.opacity < .05) return false;
      if (a.tagName === "DETAILS" && !a.open && a !== el && !el.closest("summary")) return false; }
    return true; };
  const clipCache = new Map();
  const clipOf = el => { if (clipCache.has(el)) return clipCache.get(el); let c = {l: -1e9, t: -1e9, r: 1e9, b: 1e9}; const p = el.parentElement;
    if (p){ c = {...clipOf(p)}; const cs = getComputedStyle(p);
      if (cs.overflowX !== "visible" || cs.overflowY !== "visible"){ const r = p.getBoundingClientRect();
        if (cs.overflowX !== "visible"){ c.l = Math.max(c.l, r.left); c.r = Math.min(c.r, r.right); }
        if (cs.overflowY !== "visible"){ c.t = Math.max(c.t, r.top); c.b = Math.min(c.b, r.bottom); } } }
    clipCache.set(el, c); return c; };
  const clipR = (r, el) => { const c = clipOf(el), l = Math.max(r.left, c.l), t = Math.max(r.top, c.t), rr = Math.min(r.right, c.r), b = Math.min(r.bottom, c.b);
    return rr - l > .5 && b - t > .5 ? {left: l, top: t, right: rr, bottom: b} : null; };
  const layerOf = el => { for (let a = el; a && a.nodeType === 1; a = a.parentElement){ const cs = getComputedStyle(a);
    if (["fixed", "sticky", "absolute"].includes(cs.position) || a.tagName === "DIALOG") return a; } return document.body; };
  const scrollerX = el => { for (let a = el.parentElement; a; a = a.parentElement){ const ox = getComputedStyle(a).overflowX; if (ox === "auto" || ox === "scroll") return a; } return null; };
  for (const el of [de, document.body]) if (el.scrollWidth > el.clientWidth + 1) push({kind: "page-overflow", el: el.tagName.toLowerCase()});
  const all = [scope, ...scope.querySelectorAll("*")].filter(shown);
  for (const el of all){ const cs = getComputedStyle(el);
    if (!["SELECT", "INPUT", "TEXTAREA", "SUMMARY", "BUTTON"].includes(el.tagName) && el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1
        && (cs.overflowX === "auto" || cs.overflowX === "scroll") && !el.matches(opts.scrollOk || "#none")) push({kind: "h-scroll", el: desc(el), sw: el.scrollWidth, cw: el.clientWidth}); }
  const boxes = [], rng = document.createRange();
  const walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {acceptNode: n => n.nodeValue.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
  for (let n; (n = walker.nextNode());){ const el = n.parentElement; if (!el || !shown(el) || el.closest("select,option,script,style,textarea")) continue;
    rng.selectNodeContents(n); const ocs = getComputedStyle(el), own = el.getBoundingClientRect();
    for (const r0 of rng.getClientRects()){ let r = r0;
      if (ocs.overflowX !== "visible"){ const l = Math.max(r.left, own.left), rr = Math.min(r.right, own.right); if (rr - l <= .5) continue; r = {left: l, right: rr, top: r.top, bottom: r.bottom}; }
      const c = clipR(r, el); if (c) boxes.push({r: c, el, layer: layerOf(el)}); } }
  for (const el of scope.querySelectorAll("input:not([type=hidden]),select,textarea,button,summary,svg,.swatch,.pyricon,.catdot")){
    if (!shown(el) || el.closest("svg") && el.tagName.toLowerCase() !== "svg") continue;
    const c = clipR(el.getBoundingClientRect(), el); if (c) boxes.push({r: c, el, layer: layerOf(el)}); }
  const ctrlOf = el => el.closest("button,summary,select,label,a,.badge") || el;
  boxes.sort((a, b) => a.r.top - b.r.top);
  for (let i = 0; i < boxes.length; i++){ const A = boxes[i];
    for (let j = i + 1; j < boxes.length && boxes[j].r.top < A.r.bottom - TOLH; j++){ const B = boxes[j];
      if (A.layer !== B.layer || A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el)) continue;
      const ca = ctrlOf(A.el), cb = ctrlOf(B.el); if (ca === cb || ca.contains(cb) || cb.contains(ca)) continue;
      const w = Math.min(A.r.right, B.r.right) - Math.max(A.r.left, B.r.left), h = Math.min(A.r.bottom, B.r.bottom) - Math.max(A.r.top, B.r.top);
      if (w > TOL && h > TOLH) push({kind: "overlap", el: desc(ca), other: desc(cb)}); } }
  for (const el of all){ if (el === scope) continue; const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const c = clipR(r, el); if (c && (c.right > vw + 1 || c.left < -1) && !scrollerX(el)) push({kind: "off-page", el: desc(el)}); }
  const frames = all.filter(el => { if (el === scope || ["HTML", "BODY", "TR", "TBODY", "THEAD", "TFOOT", "TABLE", "OPTION", "TD", "TH"].includes(el.tagName)) return false;
    const cs = getComputedStyle(el); return parseFloat(cs.borderLeftWidth) > 0 && parseFloat(cs.borderRightWidth) > 0 || cs.backgroundColor !== "rgba(0, 0, 0, 0)"; });
  for (const F of frames){ const fr = F.getBoundingClientRect(); if (!fr.width) continue;
    for (const b of boxes){ if (!F.contains(b.el) || b.el === F) continue;
      if (Math.max(fr.left - b.r.left, b.r.right - fr.right) > 2){ push({kind: "sticks-out", el: desc(b.el), other: desc(F)}); break; } } }
  return out;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    errs = []
    def start(ctx):
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: d.dismiss() if d.type in ("prompt", "confirm") else d.accept())
        pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
        pg.route("https://data.miformulas.com/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(LIB)))
        pg.goto(URL); pg.wait_for_timeout(800)
        pg.click("#btnStarter"); pg.wait_for_timeout(1300)
        pg.add_style_tag(content="#storageHint{display:none!important}")
        pg.evaluate("() => document.querySelector('#btnNewMat').click()"); pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#nmLibGet').click()"); pg.wait_for_timeout(1200)   # the library, as from the site
        pg.evaluate("() => document.querySelector('#dlg').close()"); pg.wait_for_timeout(150)
        # names as long as in real data: an imported formula with five frozen versions, a long amount, three dilutions and stock
        pg.evaluate("""() => {
          const src = DATA.formulas.find(x => x.name === 'Acqua di Gio for men'), f = structuredClone(src);
          f.id = 'f-lang'; f.name = 'Hermes Orange Verte'; f.category = 'Citrus'; f.created = '2026-01-17'; delete f.starter;
          f.versions = [0, 1, 2, 3, 4].map(i => ({...structuredClone(src.versions[src.versions.length - 1]), v: i + 1, date: '2026-01-2' + i,
            imported: true, sourceName: 'Hermes Orange Verte v' + (i ? i : 'BASIS')}));
          DATA.formulas.push(f);
          const m = DATA.materials.find(x => x.name === 'Geraniol');
          m.inventory = '10 ml(10%) + 10 gr (10%) + 5 gr puur'; m.dilutions.push({pct: 1.5});
          m.stockEvents = [{t: 'take', date: today(), g: 25}];
          markDirty(); render(); }""")
        pg.wait_for_timeout(300)
        return pg
    def go(pg, what):
        pg.evaluate("""w => { HOMEVIEW = false; DILOPEN = true; STOCKOPEN = true; USEOPEN = true;
          const f = DATA.formulas.find(x => x.id === 'f-lang'), m = DATA.materials.find(x => x.name === 'Geraniol');
          if (w === 'F') switchTab('F', f.id, {type: 'v', idx: 4});
          if (w === 'B') switchTab('F', f.id, {type: 'v', idx: 4, bench: true});
          if (w === 'C') switchTab('F', f.id, {type: 'cmp', a: 0, b: 4});
          if (w === 'M') switchTab('M', m.id, null); }""", what)
        pg.wait_for_timeout(250)
    probs = lambda pg, scope, ok_scroll=None: pg.evaluate(CHECK_JS, {"scope": scope, "scrollOk": ok_scroll})
    fmt = lambda ps: "; ".join(f"{q['kind']} {q['el']}" + (f" × {q['other']}" if q.get("other") else "") for q in ps[:3])

    # ---------- 1. the pages, from 1000 to 1940 px, with the list open and closed ----------
    ctx = b.new_context(viewport={"width": 1366, "height": 800}); pg = start(ctx)
    NAMES = {"F": "de formulapagina", "B": "de bench view", "C": "Compare", "M": "een materiaalpagina met Dilutions en Stock open"}
    for what in ("F", "B", "C", "M"):
        go(pg, what)
        for lijst in (True, False):
            if pg.evaluate("document.body.classList.contains('hidebar')") == lijst: pg.keyboard.press("Control+b"); pg.wait_for_timeout(200)
            slecht = []
            for w in [701, 760, 820, 880, 940] + list(range(1000, 1941, 60 if lijst else 120)):
                pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(60)
                ps = probs(pg, "#content")
                if ps: slecht.append(f"{w}: {fmt(ps)}")
            check(f"{NAMES[what]}, lijst {'open' if lijst else 'dicht'}: niets loopt over elkaar of buiten de pagina ({slecht[:2]})", not slecht)
        if pg.evaluate("document.body.classList.contains('hidebar')"): pg.keyboard.press("Control+b"); pg.wait_for_timeout(200)

    # ---------- 2. the head of a formula with a long import name: two rows, the whole name in the version list ----------
    go(pg, "F")
    for w in (1280, 1366, 1440):
        pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(120)
        r = pg.evaluate("""() => { const t = el => [...el.children].filter(c => c.getClientRects().length).map(c => c.getBoundingClientRect());
          const rows = el => { const a = t(el).map(r => r.top + r.height / 2); return Math.max(...a) - Math.min(...a); };
          const s = document.querySelector('#verSel'), cs = getComputedStyle(s), cv = document.createElement('canvas').getContext('2d');
          cv.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
          return {r1: Math.round(rows(document.querySelector('.fTop'))), r2: Math.round(rows(document.querySelector('.fMeta'))),
            need: Math.round(cv.measureText(s.selectedOptions[0].textContent).width), avail: Math.round(s.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - 16)}; }""")
        check(f"{w} px met de lijst: de kop in twee rijen, elk op één lijn ({r})", r["r1"] < 8 and r["r2"] < 8)
        if w >= 1366: check(f"{w} px: de versielijst toont de hele importnaam met het slot ({r['need']} in {r['avail']} px)", r["need"] <= r["avail"] + 2)
    meta = pg.text_content(".fMeta") or ""
    check(f"de tweede rij herhaalt de importnaam niet ({meta.strip()[:70]!r})", "imported as" not in meta)
    check("Bench view staat in de tweede rij, rechts", pg.locator(".fMeta #btnBenchToggle").count() == 1)

    # the category opens its list, colour and + New category within the page
    for what, dd in (("F", "#fCatDd"), ("M", "#mCatDd")):
        go(pg, what); slecht = []
        for w in (701, 760, 1000, 1366):
            pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(100)
            er = pg.evaluate("d => { const e = document.querySelector(d); if (e) e.open = true; return !!e; }", dd); pg.wait_for_timeout(100)
            ps = probs(pg, "#content")
            if ps or not er: slecht.append(f"{w}: {fmt(ps) if er else 'geen keuze als ' + dd}")
            pg.evaluate("d => { const e = document.querySelector(d); if (e) e.open = false; }", dd)
        check(f"de categorie van {'een formule' if what == 'F' else 'een materiaal'} opent binnen de pagina ({slecht[:2]})", not slecht)

    # ---------- 3. the bench view in two columns wherever the page has room ----------
    go(pg, "B")
    twee = []
    for lijst in (True, False):
        if pg.evaluate("document.body.classList.contains('hidebar')") == lijst: pg.keyboard.press("Control+b"); pg.wait_for_timeout(200)
        for w in (1280, 1366):
            pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(100)
            twee.append(pg.evaluate("() => { const c = [...document.querySelector('.benchWrap').children].map(e => e.getBoundingClientRect().top); return Math.abs(c[0] - c[1]) < 4; }"))
    if pg.evaluate("document.body.classList.contains('hidebar')"): pg.keyboard.press("Control+b"); pg.wait_for_timeout(200)
    check(f"de bench view staat in twee kolommen op 1280 en 1366 px, met en zonder de lijst ({twee})", all(twee))

    # ---------- 4. the list and five windows ----------
    pg.set_viewport_size({"width": 1366, "height": 800}); pg.wait_for_timeout(100)
    pg.click("#tabM"); pg.wait_for_timeout(300)
    for w in (1000, 1366, 1920):
        pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(100)
        ps = probs(pg, "#sidebar")
        check(f"de lijst Materials op {w} px: niets schuift zijwaarts of over elkaar ({fmt(ps)})", not ps)
    pg.fill("#searchBox", "amber"); pg.wait_for_timeout(400)
    ps = probs(pg, "#sidebar"); lib_ = pg.locator("#sidebar .sugRow").count()
    check(f"zoeken met {lib_} resultaten uit de library ({fmt(ps)})", lib_ and not ps)
    pg.fill("#searchBox", ""); pg.wait_for_timeout(300)
    vensters = {"Classify several…": "() => document.querySelector('#ltClassify').click()",
                "Export my inventory as a library…": "() => exportInventoryLibrary()",
                "Import & export": "() => document.querySelector('#btnIO').click()",
                "+ New material…": "() => document.querySelector('#btnNewMat').click()",
                "Browse the library…": "() => browseList()"}
    for naam, js in vensters.items():
        for w in (1000, 1366):
            pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(100)
            pg.evaluate(js); pg.wait_for_timeout(400)
            open_ = pg.evaluate("() => document.querySelector('#dlg').open && document.querySelector('#dlg').innerText.trim().length > 20")
            ps = probs(pg, "#dlg", "#dlg .brList, #dlg [style*='overflow:auto'] *, #clRows")
            check(f"{naam} op {w} px: het venster past om zijn inhoud ({'open' if open_ else 'niet open'}; {fmt(ps)})", open_ and not ps)
            pg.evaluate("() => document.querySelector('#dlg').close()"); pg.wait_for_timeout(150)

    # the page of Import formula: the overlap check, and the line under its title in its own small grey letter (it lost
    # its style in 261019b, when the old head of a material that shared it went)
    IMP = {"type": "miformulas-import", "name": "Rose de Mai 68", "targetFormula": "Rose de Mai 68", "category": "Bases & Accords",
           "source": "photo of the lab notebook, 2026-09-05", "lines": [{"material": "Geraniol", "dilutionPct": 100, "weightG": 0.8},
           {"material": "Rose Absolute Turkey", "dilutionPct": 10, "weightG": 0.1}]}
    pg.evaluate("p => { HOMEVIEW = false; IMPORTP = p; render(); }", IMP); pg.wait_for_timeout(400)
    slecht = []
    for w in (701, 1000, 1366):
        pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(100)
        ps = probs(pg, "#content")
        if ps: slecht.append(f"{w}: {fmt(ps)}")
    ml = pg.evaluate("""() => { const m = document.querySelector('#content .metaLine'), h = document.querySelector('#content h2');
      return m ? [parseFloat(getComputedStyle(m).fontSize) < parseFloat(getComputedStyle(document.body).fontSize), getComputedStyle(m).color !== getComputedStyle(h).color] : null; }""")
    check(f"Import formula: niets over elkaar ({slecht[:2]}), de regel onder de titel klein en grijs ({ml})", not slecht and ml and all(ml))
    pg.evaluate("() => { IMPORTP = null; render(); }"); pg.wait_for_timeout(200)

    # ---------- 5. the header keeps its height while you work ----------
    sprong = []
    for w in range(1180, 1301, 20):
        pg.set_viewport_size({"width": w, "height": 800}); pg.wait_for_timeout(80)
        hs = pg.evaluate("""() => { const h = () => Math.round(document.querySelector('header').getBoundingClientRect().height), out = [];
          for (const [s, d] of [['Saved 18:16', false], ['Unsaved changes', true], ['Data kept in this browser', false]]){ setState(s, s.startsWith('Saved') ? 'this browser' : '', d); out.push(h()); }
          return out; }""")
        if len(set(hs)) > 1: sprong.append((w, hs))
    check(f"van 1180 tot 1300 px springt de kop niet bij Unsaved changes ({sprong[:3]})", not sprong)

    # ---------- 6. the printout: Total once, and light paper from the dark theme ----------
    go(pg, "F")
    pg.evaluate("() => { window.print = () => {}; document.querySelector('#btnSheet').click(); }"); pg.wait_for_timeout(300)
    pg.evaluate("() => { document.documentElement.dataset.theme = 'dark'; }")
    pg.emulate_media(media="print")
    pr = pg.evaluate("() => ({tfoot: getComputedStyle(document.querySelector('#printArea tfoot') || document.body).display, scheme: getComputedStyle(document.documentElement).colorScheme})")
    pg.emulate_media(media="screen"); pg.evaluate("() => { delete document.documentElement.dataset.theme; }")
    check(f"de afdruk zet Total één keer, aan het einde ({pr['tfoot']})", pr["tfoot"] == "table-row-group")
    check(f"de afdruk is licht, ook vanuit het donkere thema ({pr['scheme']})", "light" in pr["scheme"] and "dark" not in pr["scheme"])
    ctx.close()

    # ---------- 7. a phone ----------
    ctx = b.new_context(viewport={"width": 390, "height": 844}, user_agent=PHONE_UA, is_mobile=True, has_touch=True)
    pg = start(ctx)
    pg.evaluate("document.body.classList.add('detail')")
    for what in ("F", "B", "C", "M"):
        go(pg, what)
        ps = probs(pg, "#content")
        check(f"telefoon, {NAMES[what]}: niets loopt over elkaar of buiten het scherm ({fmt(ps)})", not ps)
    for what, dd in (("F", "#fCatDd"), ("M", "#mCatDd")):
        go(pg, what); er = pg.evaluate("d => { const e = document.querySelector(d); if (e) e.open = true; return !!e; }", dd); pg.wait_for_timeout(100)
        ps = probs(pg, "#content")
        check(f"telefoon: de categorie van {'een formule' if what == 'F' else 'een materiaal'} opent binnen het scherm ({fmt(ps) if er else 'geen keuze'})", er and not ps)
    go(pg, "B")
    cut = pg.evaluate("() => [...document.querySelectorAll('.bname')].filter(e => e.scrollWidth > e.clientWidth + 1).length")
    check(f"telefoon, bench view: geen naam afgekapt ({cut})", cut == 0)

    check("geen fouten op de pagina", not errs)
    if errs: print(errs[:3])
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
