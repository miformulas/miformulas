"""Wat de app moet overleven en wat het toetsenbord moet kunnen (deel C van de review van bouw 260914m):
een databestand met ontbrekende velden en dubbele id's, een server die elke url met een html-pagina
beantwoordt, een onleesbare browserkopie, onleesbare tekst in een getalveld, Enter in een dialoog,
Tab vanaf het startscherm, klikbare elementen zonder knop, en Undo dat teruggaat naar de wijziging.
Vereist de lokale webserver op poort 8765 (zie README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(900)

    # ---------- 1. Tab vanaf het startscherm blijft op het startscherm ----------
    focus = []
    for _ in range(8):
        page.keyboard.press("Tab"); page.wait_for_timeout(60)
        focus.append(page.evaluate("() => document.activeElement.id || document.activeElement.tagName"))
    check(f"Tab loopt niet door de verborgen app ({focus[:4]})",
          all(f in ("btnStarter", "btnOpen", "btnEmpty", "btnSettingsLanding", "btnManual", "btnFeedback",
                    "btnDownload", "btnInstall", "btnFormulair", "btnReopen", "btnSnap", "BODY", "HTML") for f in focus))
    check("de koptekst en de pagina zijn inert tot de app opstart",
          page.evaluate("() => !!document.querySelector('header').inert && !!(document.querySelector('#main') || {}).inert"))
    page.click("#btnStarter"); page.wait_for_timeout(1400)
    check("en daarna niet meer",
          page.evaluate("() => !document.querySelector('header').inert && !(document.querySelector('#main') || {}).inert"))

    # ---------- 2. Enter bevestigt een dialoog ----------
    page.click("#btnNew"); page.wait_for_timeout(400)
    page.fill("#nfName", "Entertest"); page.keyboard.press("Enter"); page.wait_for_timeout(700)
    check("Enter in New formula maakt de formule", page.evaluate("() => DATA.formulas.some(f => f.name === 'Entertest')"))
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    page.fill("#nmName", "Enterstof"); page.keyboard.press("Enter"); page.wait_for_timeout(700)
    check("Enter in + New material maakt het materiaal", page.evaluate("() => DATA.materials.some(m => m.name === 'Enterstof')"))

    # de Enter-luisteraar hangt sinds bouw 260917c één keer aan de dialoog, niet bij elke opening opnieuw:
    # tel hoe vaak de Apply-afhandeling loopt na één druk op Enter
    page.evaluate('''() => { window.__oks = 0; const o = window.openDialog;
        window.openDialog = (b, l, onOk, w) => o(b, l, () => { window.__oks++; return onOk(); }, w); }''')
    for i in range(4):
        page.click("#btnNew"); page.wait_for_timeout(250)
        page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.click("#btnNew"); page.wait_for_timeout(400)
    page.evaluate("() => { window.__oks = 0; }")
    page.fill("#nfName", "Enterproef2"); page.keyboard.press("Enter"); page.wait_for_timeout(800)
    n_ok = page.evaluate("() => window.__oks")
    check(f"na vijf keer openen loopt Enter de dialoog één keer af, niet vijf keer ({n_ok}x)", n_ok == 1)
    check("en de formule is er één keer", page.evaluate("() => DATA.formulas.filter(f => f.name === 'Enterproef2').length") == 1)

    # ---------- 3. klikbare elementen zijn met het toetsenbord te bedienen ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 3);
        switchTab("F", f.id, {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    zonder = page.evaluate("""() => [...document.querySelectorAll(".matlink,.sortable,.swatch,[data-go],[data-gof],[data-gom]")]
        .filter(e => !e.hasAttribute("href") && !e.hasAttribute("tabindex")).length""")
    check(f"elk klikbaar element is met Tab bereikbaar ({zonder} zonder)", zonder == 0)
    gesorteerd = page.evaluate("""() => { const s = document.querySelector(".sortable"); s.focus();
        const gefocust = document.activeElement === s; return {gefocust, rol: s.getAttribute("role")}; }""")
    page.keyboard.press("Enter"); page.wait_for_timeout(400)
    check(f"Enter op een sorteerkop sorteert ({gesorteerd})", gesorteerd["gefocust"] and page.evaluate("() => SORT.key") != "orig")
    page.evaluate("() => { SORT = {key:'orig', dir:1}; render(); }"); page.wait_for_timeout(300)
    page.evaluate("""() => document.querySelector("#content .matlink").focus()""")
    page.keyboard.press("Enter"); page.wait_for_timeout(600)
    check("Enter op een materiaalnaam opent het materiaal", page.evaluate("() => VIEW.tab") == "M")

    # ---------- 4. een getalveld met tekst erin houdt zijn waarde ----------
    page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Enterstof"); m.costPerGram = 2.5;
        switchTab("M", m.id, null); }""")
    page.wait_for_timeout(500)
    msgs.clear()
    page.evaluate("""() => { const i = document.querySelector('[data-f="costPerGram"]'); i.value = "twee euro";
        i.dispatchEvent(new Event("change", {bubbles:true})); }""")
    page.wait_for_timeout(500)
    kost = page.evaluate("""() => { const m = DATA.materials.find(x => x.name === "Enterstof"); return m.costPerGram; }""")
    check(f"onleesbare tekst wist de prijs niet ({kost}, {[m[:30] for m in msgs]})", kost == 2.5 and any("not a number" in m for m in msgs))
    msgs.clear()
    page.evaluate("""() => { const i = document.querySelector('[data-f="costPerGram"]'); i.value = "";
        i.dispatchEvent(new Event("change", {bubbles:true})); }""")
    page.wait_for_timeout(500)
    check("maar leegmaken mag wel", page.evaluate("""() => DATA.materials.find(x => x.name === "Enterstof").costPerGram""") is None)

    # ---------- 5. Undo keert terug naar de plek van de wijziging ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.versions[0].lines.length > 3);
        switchTab("F", f.id, {type:"v", idx:0});
        window.__fid = f.id; }""")
    page.wait_for_timeout(500)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === window.__fid);
        snapF(f); f.versions[0].lines[0].weightG = 42; markDirty(); render();
        switchTab("M", DATA.materials[0].id, null); }""")
    page.wait_for_timeout(500)
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    na = page.evaluate("() => ({tab: VIEW.tab, id: VIEW.id, fid: window.__fid})")
    check(f"Undo brengt je terug naar de formule waar de wijziging op zat ({na})",
          na["tab"] == "F" and na["id"] == na["fid"])

    # ---------- 6. een databestand met gaten en dubbele id's ----------
    stuk = {"formulas": [{"id": "dup", "name": "Eerste", "versions": [{"v": 1}]},
                         {"id": "dup", "versions": [{"v": 1, "lines": []}]},
                         {"id": "f-x", "name": "Derde"}],
            "materials": [{"id": "m-x"}, {"id": "m-x", "name": "Tweede stof"}]}
    errs.clear()
    page.evaluate("(t) => { DATA = migrate(JSON.parse(t)); boot(); }", json.dumps(stuk))
    page.wait_for_timeout(900)
    d = page.evaluate("""() => ({fid: DATA.formulas.map(f => f.id), mid: DATA.materials.map(m => m.id),
        namen: DATA.formulas.map(f => f.name), mnamen: DATA.materials.map(m => m.name),
        lines: DATA.formulas.flatMap(f => f.versions.map(v => Array.isArray(v.lines))),
        versies: DATA.formulas.map(f => Array.isArray(f.versions)),
        dils: DATA.materials.map(m => (m.dilutions || []).length)})""")
    check(f"dubbele id's zijn hernummerd ({d['fid']}, {d['mid']})",
          len(set(d["fid"])) == 3 and len(set(d["mid"])) == 2)
    check(f"een formule en een materiaal zonder naam krijgen er een ({d['namen']}, {d['mnamen']})",
          all(d["namen"]) and all(d["mnamen"]))
    check(f"elke versie heeft regels en elk materiaal een dilutie ({d['lines']}, {d['dils']})",
          all(d["lines"]) and all(d["versies"]) and all(d["dils"]))
    page.evaluate("""() => { switchTab("F", DATA.formulas[1].id, {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    check(f"de tweede formule met hetzelfde id is bereikbaar ({errs[:1]})",
          page.locator("#content h2").count() == 1 and not errs)
    # C-a 8 (bouw 260922j): twee regels met één id in één versie. De bench view en haar blad toonden er één van;
    # migrate geeft de tweede een eigen id, zodat ze in Unsorted staat, terwijl de eerste in haar groep blijft.
    tweeling = {"formulas": [{"id": "f-tw", "name": "Tweeling", "versions": [{"v": 1,
                    "lines": [{"id": "l-tw", "materialId": "m-tw", "weightG": 1}, {"id": "l-tw", "materialId": "m-tw", "weightG": 2}],
                    "bench": {"groups": [{"id": "g1", "title": "Eerst", "keys": ["l-tw"]}], "byId": True}}]}],
                "materials": [{"id": "m-tw", "name": "Tweelingstof", "dilutions": [{"pct": 100, "isBase": True}]}]}
    page.evaluate("(t) => { DATA = migrate(JSON.parse(t)); boot(); switchTab('F', 'f-tw', {type:'v', idx:0, bench:true}); }", json.dumps(tweeling))
    page.wait_for_timeout(800)
    tw = page.evaluate("""() => ({ids: DATA.formulas[0].versions[0].lines.map(l => l.id), rijen: document.querySelectorAll(".brow").length,
        groep: document.querySelectorAll("[data-bgi] .brow").length})""")
    check(f"C-a 8: twee regels met één id krijgen er elk een, en de bench view toont ze allebei ({tw})",
          len(set(tw["ids"])) == 2 and tw["ids"][0] == "l-tw" and tw["rijen"] == 2 and tw["groep"] == 1)
    # ---------- 6b. bouw 260918a: een bestand met regels die geen regel zijn ----------
    rommel = {"formulas": [{"id": "f-1", "name": "Goed", "versions": [{"v": 1, "lines": []}]},
                           None, 42, "een formule als tekst",
                           {"id": "f-2", "name": "Zonder nummers", "versions": [{"lines": []}, {"lines": []}, {"v": 7, "lines": []}]},
                           {"id": "f-3", "name": "Rommelregels", "versions": [{"v": 1, "lines": [None, {"materialId": "m-1", "dilutionPct": 100, "weightG": 5}, 3]}]},
                           {"id": "f-4", "name": "Versies geen lijst", "versions": 5}],
              "materials": [{"id": "m-1", "name": "Stof"}, None,
                            {"id": "m-2", "name": "Lege dilutie", "dilutions": [None, {"pct": 100, "isBase": True}]}],
              "orderList": [None, {"id": "o-1", "name": "Iets"}]}
    errs.clear(); msgs.clear()
    page.evaluate("(t) => { DATA = migrate(JSON.parse(t)); boot(); }", json.dumps(rommel))
    page.wait_for_timeout(900)
    r = page.evaluate("""() => ({f: DATA.formulas.map(f => f.name), m: DATA.materials.map(m => m.name),
        vs: (DATA.formulas.find(f => f.name === "Zonder nummers") || {versions: []}).versions.map(v => v.v),
        geenlijst: Array.isArray((DATA.formulas.find(f => f.name === "Versies geen lijst") || {}).versions),
        regels: ((DATA.formulas.find(f => f.name === "Rommelregels") || {versions: [{}]}).versions[0].lines || []).length,
        dils: ((DATA.materials.find(m => m.name === "Lege dilutie") || {}).dilutions || []).length,
        bestel: (DATA.orderList || []).length})""")
    check(f"formules en materialen die geen object zijn vallen weg ({r['f']}, {r['m']})",
          r["f"] == ["Goed", "Zonder nummers", "Rommelregels", "Versies geen lijst"] and r["m"] == ["Stof", "Lege dilutie"])
    check(f"versies zonder nummer worden doorgenummerd, bestaande nummers blijven ({r['vs']})", r["vs"] == [1, 2, 7])
    check(f"een versies-veld dat geen lijst is wordt er een ({r['geenlijst']})", r["geenlijst"] is True)
    check(f"stukke regels, diluties en bestelregels vallen weg ({r['regels']}, {r['dils']}, {r['bestel']})",
          r["regels"] == 1 and r["dils"] == 1 and r["bestel"] == 1)
    check(f"en de app draait erop zonder paginafouten ({errs[:1]})", not errs)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Zonder nummers");
        switchTab("F", f.id, {type:"v", idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(600)
    page.click("#btnNewV"); page.wait_for_timeout(700)
    nieuw = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Zonder nummers");
        return f.versions[f.versions.length - 1].v; }""")
    check(f"+ New version rekent verder op een echt nummer, geen vNaN ({nieuw})", nieuw == 8)

    # ---------- 6c. mini-audit C15: aliases als lijst, de vorm van het bibliotheekformaat ----------
    # Een met de hand of door een AI geschreven bestand kopieert die vorm, en alles achteraan leest één
    # tekst met kommapunten: matByName, ownNames, het zoeken en het hernoemen stopten erop.
    alias = {"formulas": [{"id": "f-al", "name": "Met aliassen", "versions": [{"v": 1, "lines": [
                 {"id": "l-al", "materialId": "m-al", "dilutionPct": 100, "weightG": 5}]}]}],
             "materials": [{"id": "m-al", "name": "Ambroxide", "aliases": ["Ambroxan", "Ambrofix"],
                            "dilutions": [{"pct": 100, "isBase": True}]},
                           {"id": "m-rm", "name": "Rommelalias", "aliases": 42,
                            "dilutions": [{"pct": 100, "isBase": True}]}]}
    errs.clear()
    page.evaluate("(t) => { DATA = migrate(JSON.parse(t)); boot(); }", json.dumps(alias))
    page.wait_for_timeout(900)
    al = page.evaluate("""() => DATA.materials.map(m => m.aliases)""")
    check(f"een lijst met aliassen wordt één tekst met kommapunten ({al})", al == ["Ambroxan; Ambrofix", ""])
    page.evaluate("""() => switchTab("F", "f-al", {type:"v", idx:0})"""); page.wait_for_timeout(700)
    check(f"de formulepagina opent ({errs[:1]})", page.locator("#content h2").count() == 1 and not errs)
    proef = page.evaluate("""() => { const uit = {};
        for (const [k, fn] of [["matByName", () => (matByName("Ambroxan")||{}).name],
                               ["ownNames",  () => [...ownNames()].length],
                               ["lijst",     () => { MATLIST = null; return matListHtml().includes("Ambroxan; Ambrofix"); }]])
          { try { uit[k] = fn(); } catch(e){ uit[k] = "FOUT: " + e.message; } }
        return uit; }""")
    check(f"en de opzoeklogica leest de aliassen ({proef})",
          proef["matByName"] == "Ambroxide" and proef["ownNames"] == 4 and proef["lijst"] is True)
    check(f"geen paginafouten op zo'n bestand ({errs[:1]})", not errs)
    msgs.clear()
    kapot = page.evaluate("() => migrateSafe(null)")
    page.wait_for_timeout(300)
    check(f"wat migrate niet aankan, meldt zich als onleesbaar bestand ({[m[:30] for m in msgs]})",
          kapot is None and any("could not be read" in m for m in msgs))

    page.click("#btnNew"); page.wait_for_timeout(400)
    check("+ New formula werkt in zo'n bestand", page.locator("#nfName").count() == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    check(f"geen paginafouten ({errs[:2]})", not errs)
    ctx.close()

    # ---------- 7. een host die elke url met zijn indexpagina beantwoordt ----------
    ctx2 = b.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx2.new_page(); pg.on("dialog", lambda d: d.accept())
    pg.route("**/data.php*", lambda r: r.fulfill(status=200, content_type="text/html", body="<!doctype html><html><body>index</body></html>"))
    pg.goto(URL); pg.wait_for_timeout(1500)
    mode = pg.evaluate("() => ({remote: REMOTE, demo: DEMO, landing: !!document.querySelector('#landing').offsetParent})")
    check(f"een html-antwoord op data.php is geen server ({mode})", not mode["remote"] and mode["demo"])
    check("dus het startscherm biedt gewoon de starterset aan", pg.locator("#btnStarter").is_visible())
    ctx2.close()

    # ---------- 8. een onleesbare browserkopie zegt wat er aan de hand is ----------
    ctx3 = b.new_context(viewport={"width": 1280, "height": 900})
    pg3 = ctx3.new_page(); pg3.on("dialog", lambda d: d.accept())
    pg3.goto(URL); pg3.wait_for_timeout(900)
    pg3.evaluate("""() => idb.set("demoData", "{dit is geen json")""")
    pg3.reload(); pg3.wait_for_timeout(1400)
    hint = pg3.text_content("#landingHint")
    check(f"het startscherm legt uit dat de browserkopie stuk is ({hint[:60]!r})", "could not be read" in hint and "Backup" in hint)
    ctx3.close()

    # ---------- 9. B16 (bouw 260920d): een beschadigd bench-object legt de bench view niet stil ----------
    # bench was de enige structuur die migrate niet dichttimmerde, en juist de structuur met ondoorzichtige
    # sleutellijsten. {} gaf een TypeError bij elke render, ook na een herstart, want VIEW.sub.bench bleef staan.
    ctx4 = b.new_context(viewport={"width": 1280, "height": 900})
    pg4 = ctx4.new_page(); e4 = []
    pg4.on("pageerror", lambda e: e4.append(str(e)))
    pg4.on("dialog", lambda d: d.accept())
    pg4.goto(URL); pg4.wait_for_timeout(900)
    pg4.click("#btnStarter"); pg4.wait_for_timeout(1400)
    mig = pg4.evaluate("""() => { const d = migrate({meta:{schema:1}, materials:[], formulas:[
        {id:"x", name:"x", versions:[{v:1, lines:[], bench:{}}, {v:2, lines:[], bench:{groups:null}},
                                     {v:3, lines:[], bench:[1,2]}, {v:4, lines:[], bench:{groups:[{title:5, keys:"nee"}]}}]}]});
        return d.formulas[0].versions.map(v => JSON.stringify(v.bench ?? null)); }""")
    check(f"migrate maakt van elke vorm een bruikbare bench ({mig})",
          all(m == "null" or ('"groups":[' in m) for m in mig)
          and '"keys":[]' in mig[3] and '"title":"Group"' in mig[3])
    for naam, vorm in (("{}", "{}"), ("{groups:null}", "{groups:null}")):
        e4.clear()
        pg4.evaluate("""(vorm) => { const m = DATA.materials[0];
            DATA.formulas = DATA.formulas.filter(x => x.id !== "f-bench");
            DATA.formulas.push({id:"f-bench", name:"Benchstuk", category:"Uncategorised", created:today(),
              frozenImport:false, versions:[{v:1, date:today(), bench: eval("(" + vorm + ")"),
                lines:[{id:"b1", materialId:m.id, dilutionPct:100, weightG:5, remark:1}]}]});
            buildUsage(); switchTab("F", "f-bench", {type:"v", idx:0, bench:true}); }""", vorm)
        pg4.wait_for_timeout(800)
        r = pg4.evaluate("""() => ({rijen: document.querySelectorAll(".brow").length,
            knop: !!document.querySelector("#btnAddGroup")})""")
        check(f"een bench {naam} opent gewoon ({r}, fouten {[x[:40] for x in e4]})", r["rijen"] == 1 and not e4)
        pg4.evaluate("() => render()"); pg4.wait_for_timeout(400)
        check(f"en een tweede render gooit evenmin ({[x[:40] for x in e4]})", not e4)
    pg4.click("#btnAddGroup"); pg4.wait_for_timeout(600)
    check(f"+ Add group heeft weer een lijst om in te duwen ({[x[:40] for x in e4]})",
          not e4 and pg4.evaluate("""() => (DATA.formulas.find(x => x.id === "f-bench").versions[0].bench.groups||[]).length""") > 0)
    ctx4.close()

    # ---------- 10. B8 (bouw 260920h): gelezen maar niet geopend is iets anders dan stuk ----------
    # Het catch dekte ook boot(), dus een fout in render of buildUsage meldde dat de browserkopie beschadigd was,
    # op een startscherm dat boot() op zijn eerste regel al verborgen had: een lege pagina met één console.warn.
    ctx5 = b.new_context(viewport={"width": 1280, "height": 900})
    pg5 = ctx5.new_page(); e5 = []
    pg5.on("pageerror", lambda e: e5.append(str(e)))
    pg5.on("dialog", lambda d: d.accept())
    pg5.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg5.goto(URL); pg5.wait_for_timeout(900)
    pg5.click("#btnStarter"); pg5.wait_for_timeout(1500)
    r = pg5.evaluate("""() => { const demo = serialize();          // een gave kopie
        const oud = render; render = () => { throw new TypeError("iets in render gaat stuk"); };
        const uit = startFromBrowserCopy(demo);
        const zicht = id => getComputedStyle(document.querySelector("#" + id)).display !== "none";
        const r = {uit, landing: zicht("landing"), hint: document.querySelector("#landingHint").textContent,
                   backup: zicht("btnLandBak"), starter: zicht("btnStarter"), leeg: zicht("btnEmpty"),
                   open: zicht("btnOpen"), landopen: zicht("btnLandOpen"), reopen: zicht("btnReopen"),
                   zichtbaar: [...document.querySelectorAll("#landing button")]
                     .filter(x => x.offsetParent).map(x => x.id),
                   formules: DATA ? DATA.formulas.length : null};
        render = oud; return r; }""")
    check(f"een fout ín boot() heet niet 'de kopie is stuk' ({r['uit']})", r["uit"] == "stuck")
    check(f"het startscherm komt terug, zodat je de melding kan zien ({r['landing']})", r["landing"] is True)
    check(f"en die melding zegt wat er echt gebeurde ({r['hint'][:60]!r})",
          "could not open it" in r["hint"] and "iets in render gaat stuk" in r["hint"])
    check(f"er staat een Backup-knop ({r['backup']})", r["backup"] is True)
    check(f"en geen knop die over je data heen zou starten ({r['starter']}, {r['leeg']})",
          r["starter"] is False and r["leeg"] is False)
    check(f"de data die gelezen was, staat er nog ({r['formules']})", r["formules"] == 16)
    # A4 van de mini-audit (bouw 260922a): Open data file wist de browserkopie die dit scherm net veilig
    # noemde, want loadFromHandle zet demoData op null zodra het een bestand heeft. Alle drie de wegen daarheen
    # gaan weg; na de Backup geeft F5 het gewone startscherm terug.
    check(f"geen weg die de browserkopie zou wissen ({r['open']}, {r['landopen']}, {r['reopen']})",
          r["open"] is False and r["landopen"] is False and r["reopen"] is False)
    check(f"de Backup is werkelijk het enige wat er staat ({r['zichtbaar']})",
          [x for x in r["zichtbaar"] if x != "btnSettingsLanding"] == ["btnLandBak"])
    r2 = pg5.evaluate("""() => startFromBrowserCopy("{dit is geen json")""")
    check(f"een onleesbare kopie heet nog altijd stuk ({r2})", r2 == "broken")
    r3 = pg5.evaluate("""() => { document.querySelector("#landing").style.display = "";
        return startFromBrowserCopy(serialize()); }""")
    check(f"en een gave kopie start gewoon op ({r3})", r3 == "ok")
    check(f"geen paginafouten ({e5[:1]})", not e5)
    ctx5.close()

    # ---------- 11. C8 (bouw 260922h): een getal of een lijst waar tekst hoort, in het databestand zelf ----------
    # Een categorie 5 legde het opstarten stil, een materiaalnaam 1234 de materiaalpagina, notities als lijst de
    # formulepagina en Export all my formulas, een beschrijving als lijst Export all materials (Excel).
    ctx6 = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    pg6 = ctx6.new_page(); e6 = []
    pg6.on("pageerror", lambda e: e6.append(str(e)))
    pg6.on("dialog", lambda d: d.accept())
    pg6.goto(URL); pg6.wait_for_timeout(900)
    pg6.click("#btnStarter"); pg6.wait_for_timeout(1400)
    pg6.evaluate("""async () => { const d = JSON.parse(serialize());
        d.formulas[0].category = 5; d.formulas[0].versions[0].notes = ["eerste regel", "tweede regel"];
        d.formulas[1].name = 1881; d.formulas[1].versions[0].name = 2;
        d.materials[0].name = 1234; d.materials[1].description = ["x", "y"]; d.materials[2].cas = 4940111; d.materials[3].supplier = {naam: "z"};
        await idb.set("demoData", JSON.stringify(d)); }""")
    pg6.reload(); pg6.wait_for_timeout(1800)
    vorm = pg6.evaluate("""() => DATA && [DATA.formulas[0].category, DATA.formulas[0].versions[0].notes, DATA.formulas[1].name,
        DATA.formulas[1].versions[0].name, DATA.materials.some(m => m.name === "1234"), DATA.materials.map(m => m.description).includes("x\\ny"),
        DATA.materials.some(m => m.cas === "4940111"), DATA.materials.every(m => typeof (m.supplier ?? "") === "string")]""")
    check(f"C8: de app start en maakt tekst van elk veld ({vorm})",
          vorm == ["5", "eerste regel\ntweede regel", "1881", "2", True, True, True, True] and not e6)
    pg6.evaluate("""() => switchTab("F", DATA.formulas[0].id, {type: "v", idx: 0})"""); pg6.wait_for_timeout(600)
    check(f"C8: de formulepagina opent ({e6[:1]})", "eerste regel" in (pg6.text_content("#content") or "") and not e6)
    pg6.evaluate("""() => switchTab("M", DATA.materials.find(m => m.name === "1234").id, null)"""); pg6.wait_for_timeout(600)
    check(f"C8: de materiaalpagina opent ({e6[:1]})", not e6 and "1234" in (pg6.text_content("#content") or ""))
    pg6.click("#btnIO"); pg6.wait_for_timeout(400)
    with pg6.expect_download() as d6:
        pg6.click("#btnExpJ")
    check(f"C8: Export all my formulas schrijft ({e6[:1]})", bool(d6.value.suggested_filename) and not e6)
    pg6.wait_for_timeout(300)
    if not pg6.locator("#btnExpM").is_visible(): pg6.click("#btnIO"); pg6.wait_for_timeout(400)
    with pg6.expect_download() as d7:
        pg6.click("#btnExpM")
    check(f"C8: Export all materials (Excel) schrijft ({e6[:1]})", bool(d7.value.suggested_filename) and not e6)
    ctx6.close()

    # ---------- 12. B2 (bouw 260922i): een getal als tekst in het databestand zelf ----------
    # "2,5" las alleen de formuletabel goed: Compare en Export all my formulas zetten 0, Apply factor maakte er NaN
    # van (null na opslaan), een IFRA-limiet "0,5" las als "not allowed" en een prijs "0,5" gaf een kost NaN.
    ctx7 = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    pg7 = ctx7.new_page(); e7 = []; m7 = []
    pg7.on("pageerror", lambda e: e7.append(str(e)))
    pg7.on("dialog", lambda d: (m7.append(d.message), d.accept()))
    pg7.goto(URL); pg7.wait_for_timeout(900)
    pg7.click("#btnStarter"); pg7.wait_for_timeout(1400)
    ids = pg7.evaluate("""async () => { const d = JSON.parse(serialize());
        const f = d.formulas.find(x => x.versions[0].lines.length >= 3), v = f.versions[0];
        const m0 = d.materials.find(m => m.id === v.lines[0].materialId);
        v.lines[0].weightG = "2,5"; v.lines[1].weightG = "7,5"; v.lines[1].dilutionPct = "10"; v.lines[2].weightG = "abc";
        m0.ifraLimit = "0,5"; m0.costPerGram = "0,5"; m0.density = "0,9"; m0.dilutions.push({pct: "7,5", isBase: false, date: "", notes: ""});
        await idb.set("demoData", JSON.stringify(d)); return {f: f.id, m: m0.id}; }""")
    pg7.reload(); pg7.wait_for_timeout(1800)
    getal = pg7.evaluate("""(ids) => { const f = DATA.formulas.find(x => x.id === ids.f), L = f.versions[0].lines, m = DATA.materials.find(x => x.id === ids.m);
        return {w: L.slice(0, 3).map(l => l.weightG), d: L[1].dilutionPct, lim: m.ifraLimit, cost: m.costPerGram, dens: m.density,
                dils: m.dilutions.map(x => x.pct)}; }""", ids)
    check(f"B2: gewichten, dilutie, limiet, prijs en dichtheid zijn getallen, en \"abc\" leest als 0 g ({getal})",
          getal["w"] == [2.5, 7.5, 0] and getal["d"] == 10 and getal["lim"] == 0.5 and getal["cost"] == 0.5
          and getal["dens"] == 0.9 and 7.5 in getal["dils"])
    check(f"B2: de app zegt één keer wat geen getal was ({[x[:70] for x in m7]})",
          len([x for x in m7 if "not a number" in x]) == 1 and any("1 value(s)" in x for x in m7))
    zelfde = pg7.evaluate("""(id) => { const L = DATA.formulas.find(x => x.id === id).versions[0].lines, K = calc(L), A = aggLines(L);
        return [K.totalW, A.tw, +K.totalAbsPct.toFixed(9), +A.abs.toFixed(9), isFinite(K.totalCost)]; }""", ids["f"])
    check(f"B2: Compare rekent hetzelfde als de tabel, en de kost is een getal ({zelfde})",
          zelfde[0] == zelfde[1] and zelfde[2] == zelfde[3] and zelfde[4])
    pg7.evaluate("""(id) => { SCALEOPEN = true; switchTab("F", id, {type: "v", idx: 0}); }""", ids["f"]); pg7.wait_for_timeout(600)
    pg7.fill("#scaleF", "2"); pg7.click("#btnApplyFactor"); pg7.wait_for_timeout(500)
    na = pg7.evaluate("""(id) => DATA.formulas.find(x => x.id === id).versions[0].lines.slice(0, 2).map(l => l.weightG)""", ids["f"])
    check(f"B2: Apply factor 2 geeft 5 en 15 g, geen NaN ({na})", na == [5, 15])
    ifra = pg7.evaluate("""(id) => { IFRAOPEN = true; render(); return document.querySelector("#ifraBox").textContent; }""", ids["f"])
    check("B2: de IFRA-limiet 0,5 leest als limiet, niet als \"not allowed\"", "not allowed" not in ifra)
    pg7.click("#btnIO"); pg7.wait_for_timeout(400)
    with pg7.expect_download() as d8:
        pg7.click("#btnExpJ")
    pad8 = os.path.join(tempfile.mkdtemp(), "formules.json"); d8.value.save_as(pad8)
    uit = json.load(open(pad8, encoding="utf-8"))
    naam = pg7.evaluate("""(id) => DATA.formulas.find(x => x.id === id).name""", ids["f"])
    w8 = [L["weightG"] for L in next(f for f in uit["formulas"] if f["name"] == naam)["versions"][0]["lines"][:2]]
    check(f"B2: Export all my formulas schrijft de gewichten, niet 0 ({w8})", w8 == [5, 15])
    check(f"geen paginafouten in deel 12 ({e7[:1]})", not e7)
    ctx7.close()
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
