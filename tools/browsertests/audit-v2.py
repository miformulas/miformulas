"""De audit v2 (op bouw 260922q, 30/09/2026): wat een gewone gebruiker bij het werk tegenkomt.
Ronde 2 (bouw 260930a): B2 Enter in een klein veld drukt zijn knop; B3 Tab op het laatste gewicht gaat naar Add
material…; B4 Batch scaling in de volgorde van gebruik (concentratie, totaal, factor), en 50 g op 20 % lukt in die
volgorde; B6 Preserve weight vooraf op een regel die net met Add line kwam; B7 Move in Move into… grijs zonder doel;
B8 schikken in de bench view zet de datum van de formule niet; B21 een verse start zegt geen "Unsaved changes" en staat
meteen in de browseropslag; C12 de vier uitvoerknoppen onder de tabel blijven samen op 1280 px met de lijst open.
Ronde 3 (bouw 260930b): B9 Supplier stelt je eigen leveranciers voor; B10 Usage in formulas één regel per formule met de
versies (v1–v3), de kop telt formules; B11 Delivered… leest "€ 15"; B12 geen cijfers als voorbeeld in Amount en Price;
en tegen de echte worker.js (worker-server.mjs): B16 de data van deze browser naar een lege server, B17 Connect to
server op een lege server zegt het, B18 een geweigerd token wordt zo genoemd, B19 een mislukte verbinding zegt het.
Vereist een webserver met de inhoud van public\\ op poort 8765 (cd public && python -m http.server 8765)."""
import json, os, subprocess, sys, urllib.request
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

OPEN_FIRST = """() => { const f = DATA.formulas.find(x => x.versions.at(-1).lines.length >= 5);
  switchTab('F', f.id, {type:'v', idx: f.versions.length - 1}); return f.id; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    def on_dialog(d): msgs.append(d.message); d.accept()
    page.on("dialog", on_dialog)
    page.goto(URL); page.wait_for_timeout(800)

    # ---------- B21: een verse start zegt geen "Unsaved changes" en is meteen bewaard
    page.click("#btnStarter"); page.wait_for_timeout(250)
    st = page.text_content("#stMain") or ""
    check(f"B21: meteen na Start with the starter set geen 'Unsaved changes' ({st!r})", "Unsaved" not in st)
    page.wait_for_timeout(600)
    saved = page.evaluate("async () => { const d = await idb.get('demoData'); return !!d && d.length > 1000 && !DIRTY; }")
    check("B21: de starterset staat binnen een seconde in de browseropslag", saved)

    fid = page.evaluate(OPEN_FIRST); page.wait_for_timeout(500)

    # ---------- C12: de vier knoppen samen op één rij op 1280 px met de lijst open
    tops = page.evaluate("() => ['btnSheet','btnCsv','btnShare','btnPrint'].map(id => Math.round(document.getElementById(id).getBoundingClientRect().top))")
    inGroup = page.evaluate("() => ['btnSheet','btnCsv','btnShare','btnPrint'].every(id => document.getElementById(id).parentElement.classList.contains('outBtns'))")
    check(f"C12: de vier uitvoerknoppen in één groep en op één rij op 1280 px ({tops})", inGroup and len(set(tops)) == 1)

    # ---------- B3: Tab op het laatste gewicht gaat naar Add material…
    n = page.evaluate("() => document.querySelectorAll('input.w').length")
    last = page.locator("input.w").nth(n - 1)
    last.click(); page.keyboard.press("Control+A"); page.keyboard.type("0.777"); page.keyboard.press("Tab"); page.wait_for_timeout(300)
    act = page.evaluate("() => document.activeElement && document.activeElement.id")
    check(f"B3: Tab op het laatste gewicht gaat naar Add material… ({act!r})", act == "addMat")
    w1 = page.evaluate("() => document.querySelectorAll('input.w')[1]")
    page.locator("input.w").nth(0).click(); page.keyboard.press("Control+A"); page.keyboard.type("0.5"); page.keyboard.press("Tab"); page.wait_for_timeout(300)
    idx = page.evaluate("() => [...document.querySelectorAll('input.w')].indexOf(document.activeElement)")
    check(f"B3: Tab midden in de kolom gaat nog altijd naar het volgende gewicht ({idx})", idx == 1)

    # ---------- B2: Enter in de kleine velden van de formulepagina
    page.evaluate("() => { const d = document.getElementById('notesBox'); if (d) d.open = true; const s = document.getElementById('scaleBox'); if (s) s.open = true; }")
    page.wait_for_timeout(200)
    nt = page.evaluate(f"() => (DATA.formulas.find(x => x.id === '{fid}').versions.at(-1).trials || []).length")
    page.fill("#trialText", "Enter werkt"); page.press("#trialText", "Enter"); page.wait_for_timeout(300)
    nt2 = page.evaluate(f"() => (DATA.formulas.find(x => x.id === '{fid}').versions.at(-1).trials || []).length")
    check(f"B2: Enter in het proeflog voegt de notitie toe ({nt} → {nt2})", nt2 == nt + 1)
    page.evaluate("() => { const s = document.getElementById('scaleBox'); if (s) s.open = true; }"); page.wait_for_timeout(200)
    tot = page.evaluate("() => calc(currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines).totalW")
    page.fill("#scaleF", "2"); page.press("#scaleF", "Enter"); page.wait_for_timeout(300)
    tot2 = page.evaluate("() => calc(currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines).totalW")
    check(f"B2: Enter in Apply factor past de factor toe ({tot:.3f} → {tot2:.3f})", abs(tot2 - 2 * tot) < 1e-6)

    # ---------- B4: de volgorde van Batch scaling, en 50 g op 20 % in die volgorde
    page.evaluate("() => { const s = document.getElementById('scaleBox'); if (s) s.open = true; }"); page.wait_for_timeout(200)
    labels = page.evaluate("() => [...document.querySelectorAll('#scaleBox .scaleGrid > span:first-child, #scaleBox .scaleGrid > span')].map(s => s.textContent.trim()).filter(t => /^(Concentration|Target total|Apply factor)/.test(t))")
    check(f"B4: Batch scaling in de volgorde concentratie, totaal, factor ({labels})",
          labels[:3] == ["Concentration (abs %)", "Target total", "Apply factor"])
    check(f"B4: de knop van de concentratie heet Set EtOH ({page.text_content('#btnSetAbs')!r})", page.text_content("#btnSetAbs").strip() == "Set EtOH")
    page.fill("#targetAbs", "20"); page.press("#targetAbs", "Enter"); page.wait_for_timeout(400)
    page.evaluate("() => { const s = document.getElementById('scaleBox'); if (s) s.open = true; }"); page.wait_for_timeout(200)
    page.fill("#scaleW", "50"); page.press("#scaleW", "Enter"); page.wait_for_timeout(400)
    K = page.evaluate("() => { const K = calc(currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines); return [K.totalW, K.totalAbsPct]; }")
    check(f"B4 en B2: 20 % en dan 50 g, met Enter, geeft 50 g op 20 % ({K[0]:.3f} g, {K[1]:.2f} %)", abs(K[0] - 50) < 1e-6 and abs(K[1] - 20) < 1e-6)

    # ---------- B6: Preserve weight vooraf op een regel die net met Add line kwam; niet op een oude regel
    page.fill("#addMat", "Geraniol"); page.press("#addMat", "Enter"); page.wait_for_timeout(400)
    i_new = page.evaluate("() => currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines.length - 1")
    page.locator("input.w").nth(i_new).click(); page.keyboard.press("Control+A"); page.keyboard.type("0.5"); page.keyboard.press("Enter"); page.wait_for_timeout(300)
    opts = page.evaluate(f"() => [...document.querySelector('[data-dil=\"{i_new}\"]').options].map(o => o.value)")
    other = [o for o in opts if o not in ("100", "custom")][0]
    page.select_option(f'[data-dil="{i_new}"]', other); page.wait_for_timeout(400)
    chosen = page.evaluate("() => document.querySelector('#dlg input[name=dm]:checked')?.value")
    check(f"B6: Change dilution op een regel die net kwam kiest Preserve weight vooraf ({chosen!r})", chosen == "keepw")
    page.click("#dlgOk"); page.wait_for_timeout(300)
    wn = page.evaluate(f"() => currentVersion(DATA.formulas.find(x => x.id === VIEW.id)).lines[{i_new}].weightG")
    check(f"B6: en het gewicht blijft 0,5 g ({wn})", abs(wn - 0.5) < 1e-9)
    # een regel die er al stond
    j = page.evaluate("""() => { const v = currentVersion(DATA.formulas.find(x => x.id === VIEW.id));
        return v.lines.findIndex((l, k) => k < v.lines.length - 1 && (l.weightG || 0) > 0 && !matById(l.materialId).isSolvent
          && (matById(l.materialId).dilutions || []).length > 1); }""")
    if j >= 0:
        opts = page.evaluate(f"() => [...document.querySelector('[data-dil=\"{j}\"]').options].filter(o => !o.selected && o.value !== 'custom').map(o => o.value)")
        page.select_option(f'[data-dil="{j}"]', opts[0]); page.wait_for_timeout(400)
        chosen = page.evaluate("() => document.querySelector('#dlg input[name=dm]:checked')?.value")
        check(f"B6: op een regel die er al stond blijft de keuze van vroeger ({chosen!r})", chosen in ("exchange", "keeprel"))
        page.click("#dlgCancel"); page.wait_for_timeout(300)
    else:
        check("B6: een oude regel met twee diluties gevonden", False)

    # ---------- B8: schikken in de bench view zet de datum niet, en Undo neemt het terug
    page.evaluate("() => { const f = DATA.formulas.find(x => x.id === VIEW.id); f.modified = '2020-01-01T00:00:00'; }")
    page.evaluate("() => { VIEW.sub.bench = true; render(); }"); page.wait_for_timeout(400)
    moved = page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === VIEW.id), item = currentVersion(f);
        const k = item.lines[0].id; benchMove(f, item, [k], "0", null); render();
        return [f.modified, (item.bench && item.bench.groups[0].keys.length) || 0]; }""")
    check(f"B8: een regel in een groep zetten laat de datum van de formule staan ({moved})", moved[0] == "2020-01-01T00:00:00" and moved[1] == 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    back = page.evaluate("() => { const it = currentVersion(DATA.formulas.find(x => x.id === VIEW.id)); return it.bench ? it.bench.groups[0].keys.length : 0; }")
    check(f"B8: Ctrl+Z neemt het schikken terug ({back})", back == 0)
    page.evaluate("() => { VIEW.sub.bench = false; render(); }"); page.wait_for_timeout(300)

    # ---------- B7: Move into… zonder doel: Move grijs
    page.evaluate("""() => { const src = DATA.formulas.find(x => x.id !== VIEW.id);   // de starterformules hebben twee versies
        const f = {...structuredClone(src), id: "f-b7", name: "B7 single", versions: [structuredClone(src.versions[0])]};
        DATA.formulas.push(f); switchTab('F', f.id, {type:'v', idx:0}); }"""); page.wait_for_timeout(400)
    page.click("#btnMoveF"); page.wait_for_timeout(300)
    page.select_option("#mvTarget", ""); page.dispatch_event("#mvTarget", "change"); page.wait_for_timeout(100)
    dis = page.evaluate("() => document.getElementById('dlgOk').disabled")
    n0 = len(msgs); page.keyboard.press("Enter"); page.wait_for_timeout(200)
    check(f"B7: zonder doel staat Move grijs, en Enter geeft geen melding ({dis}, {msgs[n0:]})", dis and len(msgs) == n0)
    opt = page.evaluate("() => [...document.querySelectorAll('#mvTarget option')].map(o => o.value).find(v => v)")
    page.select_option("#mvTarget", opt); page.wait_for_timeout(100)
    check("B7: met een doel staat Move weer aan", not page.evaluate("() => document.getElementById('dlgOk').disabled"))
    page.click("#dlgCancel"); page.wait_for_timeout(200)

    # ---------- B2: Enter op de materiaalpagina en in de bestellijst
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); switchTab('M', m.id); }"); page.wait_for_timeout(400)
    nd = page.evaluate("() => DATA.materials.find(x => x.name === 'Geraniol').dilutions.length")
    page.fill("#newDil", "3"); page.press("#newDil", "Enter"); page.wait_for_timeout(300)
    nd2 = page.evaluate("() => DATA.materials.find(x => x.name === 'Geraniol').dilutions.length")
    check(f"B2: Enter in het dilutieveld voegt de dilutie toe ({nd} → {nd2})", nd2 == nd + 1)
    page.evaluate("() => { const d = [...document.querySelectorAll('details')].find(x => /Stock/.test(x.textContent)); if (d) d.open = true; }")
    page.fill("#stTake", "12"); page.press("#stTake", "Enter"); page.wait_for_timeout(300)
    ev = page.evaluate("() => (DATA.materials.find(x => x.name === 'Geraniol').stockEvents || []).map(e => e.t)")
    check(f"B2: Enter in Stocktake zet de stocktake ({ev})", "take" in ev)
    page.evaluate("() => { const d = [...document.querySelectorAll('details')].find(x => /Stock/.test(x.textContent)); if (d) d.open = true; }")
    page.fill("#stBuyAmt", "10"); page.press("#stBuyAmt", "Enter"); page.wait_for_timeout(300)
    ev = page.evaluate("() => (DATA.materials.find(x => x.name === 'Geraniol').stockEvents || []).map(e => e.t)")
    check(f"B2: Enter in Purchase boekt de aankoop ({ev})", "buy" in ev)
    page.evaluate("() => switchTab('T')"); page.wait_for_timeout(400)
    no = page.evaluate("() => DATA.orderList.length")
    page.fill("#ordName", "Hedione"); page.press("#ordName", "Enter"); page.wait_for_timeout(400)
    check(f"B2: Enter in het bestelveld zet het materiaal op de lijst ({no} → {page.evaluate('DATA.orderList.length')})",
          page.evaluate("DATA.orderList.length") == no + 1)

    # ================= ronde 3 (bouw 260930b) =================
    # ---------- B9: Supplier stelt de leveranciers van je eigen materialen voor
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); switchTab('M', m.id); }"); page.wait_for_timeout(400)
    page.fill("#mf_supplier", "Hekserij Testhuis"); page.press("#mf_supplier", "Tab"); page.wait_for_timeout(300)
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Linalool'); switchTab('M', m.id); }"); page.wait_for_timeout(400)
    sup = page.evaluate("() => [...document.querySelectorAll('#supList option')].map(o => o.value)")
    check(f"B9: een leverancier die je zelf typte, wordt bij een ander materiaal voorgesteld ({len(sup)} in de lijst)", "Hekserij Testhuis" in sup)

    # ---------- B10: één regel per formule, met de versies ernaast
    uses = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === 'Linalool');
        const line = id => ({id, materialId: m.id, dilutionPct: 100, weightG: 1, remark: 1});
        DATA.formulas.push({id: "f-use1", name: "Gebruik drie", category: "Uncategorised", created: today(),
          versions: [1, 2, 3].map(v => ({v, date: today(), lines: [line("a" + v)]}))});
        DATA.formulas.push({id: "f-use2", name: "Gebruik gat", category: "Uncategorised", created: today(),
          versions: [{v: 1, date: today(), lines: [line("b1")]}, {v: 2, date: today(), lines: []}, {v: 3, date: today(), lines: [line("b3")]}]});
        buildUsage(); switchTab('M', m.id);
        const box = document.querySelector('.panelBox.usage');
        const rows = [...box.querySelectorAll('[data-go]')].map(a => a.closest('div').innerText.replace(/\s+/g, ' ').trim());
        const nF = new Set(USAGE[m.id].map(u => u.fid)).size;
        return {kop: box.querySelector('h3').textContent, rows, nF}; }""")
    drie = [r for r in uses["rows"] if r.startswith("Gebruik drie")]
    gat = [r for r in uses["rows"] if r.startswith("Gebruik gat")]
    check(f"B10: één regel per formule, met de versies als reeks ({drie}, {gat})",
          drie == ["Gebruik drie v1–v3"] and gat == ["Gebruik gat v1, v3"])
    check(f"B10: de kop telt formules ({uses['kop']!r}, {uses['nF']} formules)", uses["kop"].endswith(f"({uses['nF']})") and len(uses["rows"]) == min(uses["nF"], 60))
    page.click(".panelBox.usage a[data-go='f-use1']"); page.wait_for_timeout(400)
    check("B10: de link opent de laatste versie", page.evaluate("() => VIEW.id === 'f-use1' && VIEW.sub && VIEW.sub.idx === 2"))
    page.evaluate("() => { DATA.formulas = DATA.formulas.filter(f => !/^f-use/.test(f.id)); buildUsage(); }")

    # ---------- B12 en B11: de bestellijst en Delivered…
    page.evaluate("() => switchTab('T')"); page.wait_for_timeout(400)
    ph = page.evaluate("() => [...document.querySelectorAll('[data-oamt], [data-oprice]')].map(i => i.placeholder)")
    check(f"B12: Amount en Price op de bestellijst tonen geen cijfers als voorbeeld ({ph})", ph and all(x == "" for x in ph))
    i = page.evaluate("() => DATA.orderList.findIndex(o => /hedione/i.test(o.name))")
    page.click(f"[data-odeliv='{i}']"); page.wait_for_timeout(400)
    ph2 = page.evaluate("() => [document.getElementById('dvAmt').placeholder, document.getElementById('dvPrice').placeholder]")
    check(f"B12: ook in Delivered… niet ({ph2})", ph2 == ["", ""])
    page.fill("#dvAmt", "10"); page.fill("#dvPrice", "€ 15"); page.click("#dlgOk"); page.wait_for_timeout(500)
    cg = page.evaluate("() => (DATA.materials.find(x => /^hedione$/i.test(x.name)) || {}).costPerGram")
    check(f"B11: een prijs '€ 15' voor 10 g geeft 1,50 per gram ({cg})", cg is not None and abs(cg - 1.5 / (page.evaluate("() => basePct(DATA.materials.find(x => /^hedione$/i.test(x.name)))") / 100)) < 1e-4)

    # ================= ronde 4: minder woorden, en de volgorde van de menu's (bouw 260930c) =================
    page.evaluate("() => { VIEW.sub = null; switchTab('F', null, null); }"); page.wait_for_timeout(300)
    # B20: elke starterformule heeft een verdunde v2 op 100 g (in het bestand zelf: de test heeft er intussen aan gewerkt)
    b20 = page.evaluate("""async () => (await (await fetch("data/miformulas-starter.json")).json()).formulas.map(f => { const v = f.versions.at(-1), K = calc(v.lines);
        return [f.name, f.versions.length, v.name, Math.round(K.totalW * 1000) / 1000, Math.round(K.totalAbsPct * 100) / 100]; })""")
    check(f"B20: elke starterformule heeft twee versies, de tweede op 100 g en op het percentage van haar label ({b20[:2]}…)",
          len(b20) == 16 and all(n == 2 and w == 100 and abs(a - float(lbl.rstrip('%'))) < 0.01 for _, n, lbl, w, a in b20))
    # E1 en F1: Import & export, eerst import, dan export, dan de wegen terug; korte hints
    page.click("#btnIO"); page.wait_for_timeout(400)
    ids = page.evaluate("() => [...document.querySelectorAll('#dlg button, #dlg a.btn')].map(b => b.id).filter(id => !id.startsWith('dlg'))")
    check(f"F1: het venster begint met Import formula… en eindigt met de wegen terug ({ids})",
          ids[:4] == ["btnImpF", "ioCsv", "btnImpL", "ioFormulair"] and ids[4:8] == ["btnExpF", "btnExpM", "btnExpJ", "btnExpL"] and ids[8] == "ioRestore")
    hints = page.evaluate("() => [...document.querySelectorAll('#dlg .toolRow .hint')].map(h => h.textContent.trim().length)")
    check(f"E1: elke hint in het venster is kort ({max(hints)} tekens op zijn langst)", hints and max(hints) <= 130)
    check("F1: Import from Formulair… is een gewone knop, niet de oranje", "accent" not in (page.get_attribute("#ioFormulair", "class") or ""))
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    # E2 en F3: Settings, de library vóór de server
    page.click("#btnSettings"); page.wait_for_timeout(400)
    volg = page.evaluate("() => { const a = document.getElementById('setListImp'), b = document.getElementById('setServer'); return !!(a && b && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING)); }")
    check("F3: in Settings staat de library vóór de server", volg)
    tekst = page.text_content("#dlg")
    check(f"E2: Settings is korter ({len(tekst)} tekens)", "A server is optional" not in tekst and len(tekst) < 900)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    # E3: de amberen balk in één regel
    bar = page.text_content("#storageHintText") or ""
    check(f"E3: de balk is één korte regel ({bar!r})", bar == "Your data lives in this browser – keep a Backup.")
    # E4: tooltips in plaats van de uitlegregel onder de vier knoppen
    page.evaluate("() => { const f = DATA.formulas.find(x => x.starter); switchTab('F', f.id, {type:'v', idx: f.versions.length - 1}); }"); page.wait_for_timeout(500)
    tips = page.evaluate("() => ['btnSheet', 'btnCsv', 'btnShare', 'btnPrint'].map(i => document.getElementById(i)?.title)")
    check(f"E4: de vier uitvoerknoppen zeggen in hun tooltip voor wie ze zijn ({tips})", all(tips) and "for someone with it" not in page.text_content("#content"))
    check("E4: Mark as prepared legt uit in zijn tooltip", "stock" in (page.get_attribute("#btnPrep", "title") or ""))
    # F4: + Add group vooraan, en geen Close bench meer
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    rij = page.evaluate("() => [...document.querySelectorAll('.benchArea .toolRow:first-child button, .benchArea .toolRow:first-child select')].map(e => e.id)")
    check(f"F4: + Add group staat vooraan, Close bench is weg ({rij})", rij[:2] == ["btnAddGroup", "bMoveSel"] and "btnBenchClose" not in rij)
    page.click("#btnBenchToggle"); page.wait_for_timeout(400)
    check("F4: Table view sluit de bench", page.locator(".benchArea").count() == 0 and page.locator("input.w").count() > 0)
    # F2: wat het materiaal is (piramide, solvent, IFRA) vóór wat je ervan kocht
    page.evaluate("() => switchTab('M', DATA.materials.find(m => m.starter && !m.isSolvent).id)"); page.wait_for_timeout(400)
    lab = page.evaluate("() => [...document.querySelectorAll('#content label, #content .flabel')].map(l => l.textContent.trim())")
    pos = {k: next((i for i, t in enumerate(lab) if t.startswith(k)), -1) for k in ("Pyramid", "Solvent", "IFRA", "Supplier", "Amount", "Cost", "Storage")}
    check(f"F2: Pyramid, Solvent, IFRA, dan Supplier, Amount, Cost, Storage ({pos})",
          -1 not in pos.values() and list(pos.values()) == sorted(pos.values()))
    # E6: Welcome met eigen werk: één regel naar Import & export
    page.evaluate("() => { DATA.formulas[0].starter = false; DATA.formulas[0].modified = now(); }"); page.click("#btnHome"); page.wait_for_timeout(500)
    check("E6: met eigen werk wijst Welcome in één regel naar Import & export",
          page.locator("#homeIO").count() == 1 and page.locator("#btnImpCsv").count() == 0)
    check(f"geen paginafouten in ronde 4 ({errs[:1]})", not errs)

    check(f"no page errors ({errs[:2]})", not errs)
    ctx.close()

    # ================= ronde 3 tegen de echte worker.js =================
    HERE = os.path.dirname(os.path.abspath(__file__)); PORT = 8797; BASE = f"http://127.0.0.1:{PORT}"
    def ctl(q="", body=None):
        req = urllib.request.Request(BASE + "/__ctl?" + q, data=body.encode() if body else None, method="POST" if body else "GET")
        return json.loads(urllib.request.urlopen(req).read())
    srv = subprocess.Popen(["node", os.path.join(HERE, "worker-server.mjs"), str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        if "listening" not in srv.stdout.readline():
            check("worker-server.mjs start", False)
        else:
            ctl("clear=1")
            ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page(); m2 = []; e2 = []
            pg.on("dialog", lambda d: (m2.append(d.message), d.accept("") if d.type == "prompt" else d.accept()))
            pg.on("pageerror", lambda e: e2.append(str(e)))
            pg.goto(BASE + "/index.html"); pg.wait_for_timeout(800)
            # eerst in de browser gewerkt: de starterset en een eigen formule
            pg.click("#btnStarter"); pg.wait_for_timeout(1200)
            pg.evaluate("""() => { DATA.formulas.push({id: "f-eigen", name: "Mijn eigen werk", category: "Uncategorised", created: today(),
                versions: [{v: 1, date: today(), lines: []}]}); markDirty(true); }"""); pg.wait_for_timeout(800)
            pg.evaluate(f"""async () => {{ await idb.set('serverUrl', {json.dumps(BASE + '/api')}); await idb.set('token', 'tok-test'); }}""")
            pg.reload(); pg.wait_for_timeout(1500)
            # B17: Connect to server op een lege server
            n0 = len(m2); pg.click("#btnOpen"); pg.wait_for_timeout(600)
            check(f"B17: Connect to server op een lege server zegt het ({m2[n0:]})", any("no data file yet" in x for x in m2[n0:]))
            # B16: de data van deze browser naar de server
            vis = pg.evaluate("() => { const e = document.getElementById('btnLandBrowser'); return !!e && getComputedStyle(e).display !== 'none'; }")
            check("B16: het lege serverscherm biedt de data van deze browser aan", vis)
            if vis: pg.click("#btnLandBrowser"); pg.wait_for_timeout(1500)
            onsrv = '"Mijn eigen werk"' in (ctl()["data"] or "")
            check(f"B16: een klik zet ze op de server ({pg.locator('#saveState').inner_text()!r})", onsrv and pg.evaluate("REMOTE && !DIRTY"))
            ctx.close()
            # B18 en B19: een verkeerd token, op een server die data heeft
            ctx = b.new_context(viewport={"width": 1280, "height": 900}); pg = ctx.new_page(); m3 = []; asked = []
            def dlg3(d):
                m3.append(d.message)
                if d.type == "prompt": asked.append(d.message); d.dismiss()
                else: d.accept()
            pg.on("dialog", dlg3)
            pg.goto(BASE + "/index.html"); pg.wait_for_timeout(800)
            pg.evaluate(f"""async () => {{ await idb.set('serverUrl', {json.dumps(BASE + '/api')}); await idb.set('token', 'tok-fout'); }}""")
            pg.reload(); pg.wait_for_timeout(1500)
            check(f"B18: een geweigerd token wordt zo genoemd ({asked})", asked and "refused" in asked[0])
            hint = pg.text_content("#landingHint") or ""
            check(f"B19: daarna zegt het startscherm wat er mis is ({hint[:70]!r})", "did not answer as expected" in hint and "Saving is automatic" not in hint)
            ctx.close()
    finally:
        srv.terminate()
    b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
