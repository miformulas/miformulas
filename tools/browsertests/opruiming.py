"""Build 260915: the tail of the review of 260913g. Search, confirmations, ellipsis,
the library credit and the alias list, and read-only on a phone.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

LIB = {"type": "miformulas-materials", "name": "Credited library", "version": "2026-09-15",
       "licence": "CC BY 4.0", "attribution": "Facts by A. Colleague, CC BY 4.0",
       "source": "https://example.org/library", "materials": [
    {"name": "Ambroxide", "aliases": ["Ambroxan", "Ambrofix"], "cas": "6790-58-5",
     "category": "Woody - amber", "pyramid": 4},
    {"name": "Proefstof Q", "category": "Test", "pyramid": 1}]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []; mode = {"v": "accept"}
    page.on("pageerror", lambda e: errs.append(str(e)))
    def on_dialog(d):
        msgs.append(d.message)
        d.accept() if mode["v"] == "accept" else d.dismiss()
    page.on("dialog", on_dialog)
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # ---------- ellipsis on the buttons that open a window ----------
    check("+ New formula…", page.text_content("#btnNew").strip() == "+ New formula…")
    check("+ New material…", page.text_content("#btnNewMat").strip() == "+ New material…")
    check("Backup zonder beletselteken: het opent geen venster van de app, en de handleiding noemt hem 29 keer zo",
          page.text_content("#btnBackup").strip() == "Backup")
    page.evaluate("() => { const f = DATA.formulas.find(x => x.versions.length); switchTab('F', f.id, {type:'v', idx:0}); }")
    page.wait_for_timeout(500)
    check("Rename…", page.text_content("#btnRenameF").strip() == "Rename…")
    check("Copy to new formula…", page.text_content("#btnCopyF").strip() == "Copy to new formula…")
    check("Change category…", page.text_content("#btnCatF").strip() == "Change category…")
    check("the pencil says so in its tooltip", page.get_attribute("#btnNameV", "title") == "Name this version…")
    check("the replace arrows say so in their tooltip",
          (page.get_attribute("[data-repl]", "title") or "").endswith("…"))

    # ---------- a trial note asks before it goes ----------
    page.fill("#trialText", "Smells of pear drops."); page.click("#btnAddTrial"); page.wait_for_timeout(400)
    check("the trial note is there", page.locator("[data-deltrial]").count() == 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.click("[data-deltrial]"); page.wait_for_timeout(400)
    check(f"removing asks first ({msgs})", any("Remove this trial note?" in m for m in msgs))
    check("saying no keeps it", page.locator("[data-deltrial]").count() == 1)
    mode["v"] = "accept"
    page.click("[data-deltrial]"); page.wait_for_timeout(400)
    check("saying yes removes it", page.locator("[data-deltrial]").count() == 0)

    # ---------- a bench group asks too ----------
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    before = page.locator("[data-bdel]").count()
    page.click("#btnAddGroup"); page.wait_for_timeout(400)
    check("a bench group was added", page.locator("[data-bdel]").count() == before + 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.locator("[data-bdel]").last.click(); page.wait_for_timeout(400)
    check(f"deleting a group asks first ({msgs[:1]})", any("Delete this bench group?" in m for m in msgs))
    check("saying no keeps the group", page.locator("[data-bdel]").count() == before + 1)
    mode["v"] = "accept"
    page.locator("[data-bdel]").last.click(); page.wait_for_timeout(400)
    check("saying yes deletes it", page.locator("[data-bdel]").count() == before)
    page.click("#btnBenchToggle"); page.wait_for_timeout(400)

    # ---------- a stock entry asks too ----------
    page.evaluate("() => { const m = DATA.materials[0]; switchTab('M', m.id, null); }")
    page.wait_for_timeout(500)
    def open_stock():   # the stock panel is a <details>, closed again after every render
        page.evaluate("() => { const d = document.querySelector('#stBuyAmt')?.closest('details'); if (d) d.open = true; }")
        page.wait_for_timeout(200)
    open_stock()
    n0 = page.locator("[data-delev]").count()
    page.fill("#stBuyAmt", "25"); page.fill("#stBuyNote", "Test supplier")
    page.click("#btnBuy"); page.wait_for_timeout(400); open_stock()
    check("the purchase is logged", page.locator("[data-delev]").count() == n0 + 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.locator("[data-delev]").first.click(); page.wait_for_timeout(400); open_stock()
    check(f"removing a stock entry asks first ({msgs[:1]})", any("Remove this stock entry?" in m for m in msgs))
    check("saying no keeps it", page.locator("[data-delev]").count() == n0 + 1)
    mode["v"] = "accept"
    page.locator("[data-delev]").first.click(); page.wait_for_timeout(400); open_stock()
    check("saying yes removes it", page.locator("[data-delev]").count() == n0)

    # ---------- searching for the starter set ----------
    page.evaluate("() => { switchTab('M', null, null); }"); page.wait_for_timeout(400)
    page.fill("#searchBox", "arter"); page.wait_for_timeout(400)
    check("a substring of “starter set” no longer shows every starter material",
          page.locator("#list .item").count() == 0)
    page.fill("#searchBox", "sta"); page.wait_for_timeout(400)
    check("the beginning of “starter set” still finds them", page.locator("#list .item").count() > 100)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # the same in Formulas, which §8 of the manual promises too (build 260917d)
    page.evaluate("() => { switchTab('F', null, null); }"); page.wait_for_timeout(400)
    n_alle = page.locator("#list .item").count()
    gemerkt = page.locator("#list .item", has_text="starter").count()
    check(f"every starter formula wears its label in the list ({gemerkt} of {n_alle})", gemerkt == 16)
    page.fill("#searchBox", "sta"); page.wait_for_timeout(400)
    check("“sta” lists the sixteen starter formulas", page.locator("#list .item").count() == 16)
    page.fill("#searchBox", "arter"); page.wait_for_timeout(400)
    check("a substring of “starter set” shows none of them, as in Materials",
          page.locator("#list .item").count() == 0)
    page.fill("#searchBox", "rose"); page.wait_for_timeout(400)
    naam = page.locator("#list .item").first.inner_text().lower()
    check(f"searching a name still works ({naam.splitlines()[0]})",
          page.locator("#list .item").count() >= 1 and "rose" in naam)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # ---------- a value that rounds to nothing keeps no minus sign ----------
    check("fmt(-0.0000001) is 0, not -0", page.evaluate("fmt(-0.0000001, 3)").replace(",", ".") == "0.000")
    check("fmtS(-0.0000001) too", "-" not in page.evaluate("fmtS(-0.0000001, 2)"))

    # ---------- the library: alternative names in the list, the credit in Settings ----------
    f = os.path.join(tempfile.mkdtemp(), "lib.json")
    open(f, "w", encoding="utf-8").write(json.dumps(LIB))
    page.evaluate("() => { HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); }")
    page.wait_for_timeout(400)
    msgs.clear()
    page.set_input_files("#impList", f); page.wait_for_timeout(700)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    opts = page.locator("#nmList option").evaluate_all("els => els.map(e => e.value)")
    check(f"the list offers the names and the alternative names ({len(opts)})",
          "Ambroxide" in opts and "Ambroxan" in opts and "Ambrofix" in opts and "Proefstof Q" in opts)
    check("and offers each of them once", len(opts) == len(set(opts)))
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    dlg = page.text_content("#dlg")
    check("Settings shows the attribution", "Facts by A. Colleague, CC BY 4.0" in dlg)
    check("and the source as a link", page.locator('#dlg a[href="https://example.org/library"]').count() == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---------- read-only on a phone ----------
    page.set_viewport_size({"width": 400, "height": 800})
    page.evaluate("() => { DEMO = false; HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); }")
    page.wait_for_timeout(500)
    check("the CSV import on Welcome is out of reach", page.locator("#btnImpCsv").is_disabled())
    page.click("#btnIO"); page.wait_for_timeout(400)     # the window sits outside #content, so it disables its own import buttons
    check("importing is out of reach", page.locator("#btnImpF").is_disabled() and page.locator("#btnImpL").is_disabled()
          and page.locator("#ioCsv").is_disabled())
    check("exporting stays within reach", not page.locator("#btnExpF").is_disabled()
          and not page.locator("#btnExpM").is_disabled() and not page.locator("#btnExpL").is_disabled())
    page.click("#dlgOk"); page.wait_for_timeout(300)
    page.evaluate("""() => {
        IMPORTP = {type:"miformulas-import", name:"Proef", lines:[{name:"Ambroxide", weightG:1}]};
        HOMEVIEW = false; render();
    }""")
    page.wait_for_timeout(500)
    check("an import preview can still be left", not page.locator("#btnImpCancel").is_disabled())
    check("but not confirmed", page.locator("#btnImpOk").is_disabled())

    # ---------- bouw 260918d: een lege lijst, een dode knop en een dubbelklik ----------
    page.set_viewport_size({"width": 1280, "height": 950})        # de vorige sectie stond op een telefoon zonder opslag
    page.evaluate("() => { DEMO = true; IMPORTP = null; switchTab('M', null, null); }"); page.wait_for_timeout(500)
    page.fill("#searchBox", "zzzzgeenenkeletreffer"); page.wait_for_timeout(500)
    lijst = page.text_content("#list")
    check(f"zoeken zonder treffer geeft uitleg in plaats van een wit scherm ({lijst.strip()[:60]!r})",
          "Nothing here matches" in lijst and "zzzzgeenenkeletreffer" in lijst)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    page.evaluate("""() => { DATA.orderList = [
        {id: "o-los", materialId: null, name: "Nog te kiezen stof", added: today()},
        {id: "o-vast", materialId: DATA.materials[0].id, name: DATA.materials[0].name, added: today()}];
        markDirty(); switchTab("T", null, null); }""")
    page.wait_for_timeout(600)
    rollen = page.evaluate("""() => [...document.querySelectorAll("#list .item")].map(
        e => [e.dataset.id, e.getAttribute("role"), e.getAttribute("tabindex")])""")
    check(f"een bestelregel zonder materiaal wordt niet als knop aangekondigd ({rollen})",
          any(r[0] == "o-los" and r[1] is None and r[2] is None for r in rollen)
          and any(r[0] == "o-vast" and r[1] == "button" for r in rollen))

    page.evaluate("""() => { const f = DATA.formulas.find(x => !x.frozenImport && x.versions.length
            && !x.versions[x.versions.length - 1].frozen && !x.versions[x.versions.length - 1].imported);
        window.__dv = f.id; switchTab("F", f.id, {type: "v", idx: f.versions.length - 1}); }""")
    page.wait_for_timeout(700)
    check("de knop + New version staat er", page.locator("#btnNewV").count() == 1)
    n0 = page.evaluate("""() => DATA.formulas.find(x => x.id === window.__dv).versions.length""")
    page.evaluate("""() => { const b = document.querySelector("#btnNewV"); b.click(); b.click(); }""")
    page.wait_for_timeout(900)
    n1 = page.evaluate("""() => DATA.formulas.find(x => x.id === window.__dv).versions.length""")
    check(f"een dubbelklik op + New version maakt \u00e9\u00e9n versie ({n0} \u2192 {n1})", n1 == n0 + 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    vakjes = page.evaluate("""() => [...document.querySelectorAll("input.selCb")].map(c => c.getAttribute("aria-label"))""")
    check(f"elk aankruisvakje van een regel draagt de naam van zijn materiaal ({(vakjes or [None])[0]!r})",
          vakjes and all(v and len(v) > 8 for v in vakjes))

    # ---------- bouw 260918e: het materiaal in een oudere versie, de knop naar de winkels, Delete version ----------
    page.evaluate("""() => { DATA.orderList = []; DATA.materials.push(
        {id:"m-oud", name:"Alleen in v1", category:"Test", pyramid:2, isSolvent:false, dilutions:[{pct:100, isBase:true}]},
        {id:"m-nu",  name:"Ook in v2",    category:"Test", pyramid:2, isSolvent:false, dilutions:[{pct:100, isBase:true}]});
      invalidateMats();
      DATA.formulas.push({id:"f-oud", name:"Oude versie", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[{materialId:"m-oud", dilutionPct:100, weightG:5, remark:1},
                                   {materialId:"m-nu",  dilutionPct:100, weightG:5, remark:1}]},
        {v:2, date:today(), lines:[{materialId:"m-nu",  dilutionPct:100, weightG:5, remark:1}]}]});
      buildUsage(); markDirty(); switchTab("M", "m-oud", null); }""")
    page.wait_for_timeout(700)
    msgs.clear()
    page.click("#btnDelMat"); page.wait_for_timeout(600)
    check(f"een materiaal dat alleen in een oudere versie zit, zegt wat je wel kan doen ({[m[-70:] for m in msgs]})",
          any("older or frozen version" in m and "Delete version" in m for m in msgs))
    check("en het materiaal staat er nog", page.evaluate("""() => !!matById("m-oud")"""))
    page.evaluate("""() => switchTab("M", "m-nu", null)"""); page.wait_for_timeout(600)
    msgs.clear()
    page.click("#btnDelMat"); page.wait_for_timeout(600)
    check(f"een materiaal in de laatste versie krijgt die zin niet ({[m[-60:] for m in msgs]})",
          msgs and not any("older or frozen version" in m for m in msgs))

    # Delete version: welke formule, wat er overblijft, en dat Undo het terughaalt
    page.evaluate("""() => switchTab("F", "f-oud", {type:"v", idx:1})"""); page.wait_for_timeout(700)
    msgs.clear(); mode["v"] = "dismiss"
    page.click("#btnDelV"); page.wait_for_timeout(600)
    eerste = (msgs[0] if msgs else "")
    check(f"Delete version noemt de formule ({eerste[:60]!r})",
          any("Oude versie" in m for m in msgs))
    check("en wijst op Ctrl+Z", any("Ctrl+Z" in m for m in msgs))
    check("bij twee versies zegt het niets over een formule zonder regels",
          not any("without lines" in m for m in msgs))
    check("en Cancel laat de versie staan",
          page.evaluate("""() => DATA.formulas.find(x => x.id === "f-oud").versions.length""") == 2)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-oud");
        f.versions.splice(1,1); markDirty(); switchTab("F", "f-oud", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)
    msgs.clear()
    page.click("#btnDelV"); page.wait_for_timeout(600)
    laatste_msg = (msgs[0] if msgs else "")
    check(f"bij de laatste versie zegt het wat er overblijft ({laatste_msg[-90:]!r})",
          any("only version" in m and "without lines" in m and "Delete formula" in m for m in msgs))
    mode["v"] = "accept"
    page.evaluate("""() => { DATA.formulas = DATA.formulas.filter(x => x.id !== "f-oud");
        DATA.materials = DATA.materials.filter(x => x.id !== "m-oud" && x.id !== "m-nu");
        invalidateMats(); buildUsage(); markDirty(); switchTab("T", null, null); }""")
    page.wait_for_timeout(500)

    # de knop naast een bestelregel belooft niets wat ze niet kan waarmaken
    page.evaluate("""() => { DATA.orderList = [{id:"o-1", materialId:null, name:"Iets te zoeken", added:today()}];
        markDirty(); render(); }""")
    page.wait_for_timeout(500)
    knop = page.evaluate("""() => { const b = document.querySelector("[data-osearch='0']");
        return b && {tekst: b.textContent.trim(), titel: b.getAttribute("title"), winkels: (DATA.shopSites||[]).length}; }""")
    check(f"de starterset begint zonder winkels, dus zegt de knop dat ze het hele web doorzoekt ({knop})",
          knop and knop["winkels"] == 0 and knop["tekst"] == "Search the web" and "whole web" in (knop["titel"] or ""))
    page.evaluate("""() => { DATA.shopSites = ["perfumersapprentice.com", "hermitageoils.com"]; markDirty(); render(); }""")
    page.wait_for_timeout(500)
    knop2 = page.evaluate("""() => { const b = document.querySelector("[data-osearch='0']");
        return b && {tekst: b.textContent.trim(), titel: b.getAttribute("title")}; }""")
    check(f"zodra je er zelf toevoegt, zoekt ze in je winkels ({knop2})",
          knop2 and knop2["tekst"] == "Search my shops" and "2 shop(s)" in (knop2["titel"] or ""))
    page.evaluate("""() => { DATA.shopSites = []; DATA.orderList = []; markDirty(); render(); }""")
    page.wait_for_timeout(400)

    # ---------- B13 (bouw 260920d): een formule zonder versies is geen doodlopende weg ----------
    # Delete version op de enige versie zegt letterlijk dat Delete formula de formule zelf verwijdert; die knop
    # stond op dat scherm nergens, en de lijst heeft er bewust geen.
    page.evaluate("""() => { DATA.formulas.push({id:"f-leeg", name:"Leeggelopen", category:"Uncategorised",
        created:today(), frozenImport:false, versions:[]});
        buildUsage(); markDirty(); switchTab("F", "f-leeg", null); }""")
    page.wait_for_timeout(700)
    aanwezig = page.evaluate("""() => ["btnRenameF","btnCatF","btnDelF","btnNewV","btnCopyF"]
        .filter(id => !!document.getElementById(id))""")
    check(f"een formule zonder versies houdt Rename, Change category en Delete formula ({aanwezig})",
          all(k in aanwezig for k in ("btnRenameF", "btnCatF", "btnDelF", "btnNewV")))
    check("en geen Copy to new formula, want er is geen versie om te kopiëren", "btnCopyF" not in aanwezig)
    check("de uitleg staat er nog",
          "Empty formula" in page.evaluate("""() => document.querySelector("#content").innerText"""))
    mode["v"] = "accept"; msgs.clear()
    page.click("#btnDelF"); page.wait_for_timeout(700)
    check(f"en Delete formula werkt er ook echt ({[m[:40] for m in msgs]})",
          page.evaluate("""() => !DATA.formulas.some(x => x.id === "f-leeg")"""))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("Ctrl+Z brengt ze terug", page.evaluate("""() => DATA.formulas.some(x => x.id === "f-leeg")"""))
    page.evaluate("""() => { DATA.formulas = DATA.formulas.filter(x => x.id !== "f-leeg");
        buildUsage(); switchTab("F", null, null); }""")
    page.wait_for_timeout(400)

    # ---------- staart 12, 13, 14, 15, 18 en 19 (bouw 260920k) ----------
    page.evaluate("""() => {
      const m = DATA.materials[0], m2 = DATA.materials[1];
      DATA.formulas.push({id:"f-staart", name:"Staarttest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:"2026-09-01", notes:"Nota van v1", trials:[{date:"2026-09-02", text:"dag 1, te scherp"}],
         lines:[{id:"l-1", materialId:m.id, dilutionPct:100, weightG:10, remark:1},
                {id:"l-2", materialId:m.id, dilutionPct:100, weightG:5, remark:1},
                {id:"l-3", materialId:m2.id, dilutionPct:10, weightG:2, remark:1}]},
        {v:2, date:"2026-09-10", lines:[{id:"l-4", materialId:m.id, dilutionPct:100, weightG:12, remark:1}]}]});
      buildUsage(); switchTab("F", "f-staart", {type:"v", idx:0}); }""")
    page.wait_for_timeout(600)

    # 12: Compare vanaf de eerste versie zet de oudste in A
    page.click("#btnCmp"); page.wait_for_timeout(500)
    ab = page.evaluate("""() => ({a: VIEW.sub.a, b: VIEW.sub.b})""")
    check(f"Compare vanaf de eerste versie: de oudste in A, de volgende in B ({ab})", ab == {"a": "v0", "b": "v1"})
    page.evaluate("""() => switchTab("F", "f-staart", {type:"v", idx:1})"""); page.wait_for_timeout(400)
    page.click("#btnCmp"); page.wait_for_timeout(500)
    ab2 = page.evaluate("""() => ({a: VIEW.sub.a, b: VIEW.sub.b})""")
    check(f"en vanaf een latere versie blijft die zelf de B-kant ({ab2})", ab2 == {"a": "v0", "b": "v1"})

    # 14: Ctrl+P in Compare zegt wat er aan de hand is, met een formule open
    page.evaluate("""() => { document.querySelector("#printArea").innerHTML = "";
        window.dispatchEvent(new Event("beforeprint")); }""")
    pa = page.evaluate("""() => document.querySelector("#printArea").innerText""")
    check(f"Ctrl+P in Compare noemt Close compare in plaats van “open a formula” ({pa[:60]!r})",
          "Close compare" in pa and "Open a formula" not in pa)

    # 13: Close compare brengt je terug in de bench view waar je vandaan kwam
    page.evaluate("""() => switchTab("F", "f-staart", {type:"v", idx:0, bench:true})"""); page.wait_for_timeout(500)
    check("de bench view staat open", page.locator(".brow").count() > 0)
    page.click("#btnCmp"); page.wait_for_timeout(500)
    page.click("#btnCmpClose"); page.wait_for_timeout(500)
    check(f"Close compare komt terug in de bench view ({page.evaluate('() => VIEW.sub')})",
          page.evaluate("""() => !!VIEW.sub.bench""") and page.locator(".brow").count() > 0)
    # en van versie wisselen houdt de bench view vast
    page.select_option("#verSel", "1"); page.wait_for_timeout(500)
    check("van versie wisselen houdt de bench view vast",
          page.evaluate("""() => VIEW.sub.idx === 1 && !!VIEW.sub.bench""") and page.locator(".brow").count() > 0)

    # 18: de waarschuwing over dubbele regels blijft staan in de bench view
    page.evaluate("""() => switchTab("F", "f-staart", {type:"v", idx:0, bench:true})"""); page.wait_for_timeout(500)
    txt = page.evaluate("""() => document.querySelector("#content").innerText""")
    check(f"de dubbele regels worden ook in de bench view gemeld ({'Duplicate lines' in txt})",
          "Duplicate lines" in txt)
    page.evaluate("""() => switchTab("F", "f-staart", {type:"v", idx:0})"""); page.wait_for_timeout(400)
    check("en in de tabel nog altijd",
          "Duplicate lines" in page.evaluate("""() => document.querySelector("#content").innerText"""))

    # 15: Print full formula toont de kolom Cost pas met een prijs
    prijzen = page.evaluate("""() => { const had = DATA.materials.filter(m => m.costPerGram);
        had.forEach(m => { m._bewaard = m.costPerGram; m.costPerGram = null; }); return had.length; }""")
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-staart"), it = f.versions[0];
        const K = calc(it.lines); formulaSheetPrint(f, it, it.lines, K); }""")
    page.wait_for_timeout(300)
    zonder = page.evaluate("""() => document.querySelector("#printArea").innerText""")
    check(f"Print full formula zonder één prijs heeft geen kolom Cost ({prijzen} prijzen weggehaald)",
          "Cost" not in zonder and "Rel %" in zonder)
    page.evaluate("""() => { DATA.materials.forEach(m => { if (m._bewaard != null){ m.costPerGram = m._bewaard; delete m._bewaard; } });
        if (!DATA.materials.some(m => m.costPerGram)) DATA.materials[0].costPerGram = 1.5;
        const f = DATA.formulas.find(x => x.id === "f-staart"), it = f.versions[0];
        const K = calc(it.lines); formulaSheetPrint(f, it, it.lines, K); }""")
    page.wait_for_timeout(300)
    check("en met een prijs staat ze er wel",
          "Cost" in page.evaluate("""() => document.querySelector("#printArea").innerText"""))
    page.evaluate("""() => { document.querySelector("#printArea").innerHTML = ""; }""")

    # 19: Copy to new formula neemt de notities en het proeflog mee
    page.evaluate("""() => switchTab("F", "f-staart", {type:"v", idx:0})"""); page.wait_for_timeout(400)
    page.click("#btnCopyF"); page.wait_for_timeout(400)
    page.fill("#cpName", "Staarttest kopie"); page.click("#dlgOk"); page.wait_for_timeout(700)
    kop = page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "Staarttest kopie");
        return f ? {notes: f.versions[0].notes, trials: (f.versions[0].trials||[]).length} : null; }""")
    check(f"de kopie draagt Copied from … met de notities van de bron eronder ({kop})",
          kop and kop["notes"].startswith("Copied from Staarttest") and "Nota van v1" in kop["notes"])
    check("en het proeflog gaat mee", kop and kop["trials"] == 1)
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("Ctrl+Z neemt de kopie terug",
          page.evaluate("""() => !DATA.formulas.some(x => x.name === "Staarttest kopie")"""))

    check(f"no page errors ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
