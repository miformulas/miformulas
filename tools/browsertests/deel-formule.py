"""Share this version: what the file holds, and the way back in at the other end.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

TOEGESTAAN = {"type", "name", "versionName", "category", "source", "notes", "lines"}
REGELVELDEN = {"material", "dilutionPct", "weightG", "cas", "solvent"}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    # ---------- een versie met een label, notities, een eigen dilutie, een solventregel en een spoorregel ----------
    page.evaluate("""() => {
        const f = DATA.formulas.find(x => x.versions.length && x.versions[0].lines.length > 3);
        const v = f.versions[0];
        v.name = "45gr";                                   // het label van de versie
        v.notes = "Second trial, more geraniol.";
        const m = matById(v.lines[0].materialId);
        m.costPerGram = 2.5; m.supplier = "Somebody"; m.inventory = "50 g";
        m.dilutions.push({pct: 7, isBase: false, date: today(), notes: ""});   // een dilutie die een ander niet heeft
        v.lines[0].dilutionPct = 7;
        v.lines[1].weightG = 0.0004;                       // een spoorregel: mag niet naar 0 afronden
        const solv = DATA.materials.find(x => x.isSolvent);
        v.lines.push({materialId: solv.id, dilutionPct: 100, weightG: 191, remark: 1});
        window.__f = f.name; window.__mat = m.name; window.__cas = m.cas || "";
        window.__solv = solv.name;
        window.__lines = v.lines.length;
        window.__volgorde = v.lines.map(l => matById(l.materialId).name);
        SORT = {key: "name", dir: -1};                     // het scherm staat op naam, omgekeerd
        switchTab("F", f.id, {type: "v", idx: 0});
    }""")
    page.wait_for_timeout(600)
    naam = page.evaluate("window.__f"); mat = page.evaluate("window.__mat")
    solvnaam = page.evaluate("window.__solv")
    nlines = page.evaluate("window.__lines"); volgorde = page.evaluate("window.__volgorde")

    # ---------- de knop en zijn buren ----------
    check("de uitvoerrij heeft vier knoppen",
          all(page.locator(s).count() == 1 for s in ("#btnSheet", "#btnCsv", "#btnShare", "#btnPrint")))
    # sinds bouw 260920n zonder beletselteken: de knop schrijft meteen het bestand, ze vraagt niets in te vullen
    check("Share this version", page.text_content("#btnShare").strip() == "Share this version")
    check("de twee afdrukken dragen elk een eigen naam",
          page.text_content("#btnSheet").strip() == "Print full formula"
          and page.text_content("#btnPrint").strip() == "Print weighing sheet")
    check("de uitvoer naar Excel heet Excel export", page.text_content("#btnCsv").strip() == "Excel export")
    check("de hint zegt welke voor wie is",
          "Excel export for someone without miFormulas" in page.text_content("#content")
          and "the weighing sheet for the bench" in page.text_content("#content"))

    # ---------- uitvoeren ----------
    with page.expect_download() as dl:
        page.click("#btnShare")
    d = dl.value
    f = os.path.join(tempfile.mkdtemp(), d.suggested_filename)
    d.save_as(f)
    pkg = json.load(open(f, encoding="utf-8"))
    check(f"de bestandsnaam draagt formule en versie ({d.suggested_filename})",
          naam in d.suggested_filename and d.suggested_filename.endswith(".json"))
    check("het type maakt het invoerbaar", pkg["type"] == "miformulas-import")
    check("naam en categorie gaan mee", pkg["name"] == naam and pkg.get("category"))
    check(f"versionName is het label alleen, zonder nummer ({pkg.get('versionName')!r})",
          pkg.get("versionName") == "45gr")
    check(f"de herkomst staat erbij ({pkg.get('source')})", "Shared from miFormulas" in pkg.get("source", ""))
    check("de notities van de versie gaan mee", pkg.get("notes") == "Second trial, more geraniol.")
    check("elke regel is meegegaan", len(pkg["lines"]) == nlines)
    check(f"in de volgorde van de versie, niet die van het scherm",
          [L["material"] for L in pkg["lines"]] == volgorde)
    stray = set(pkg) - TOEGESTAAN
    check(f"geen ander veld bovenaan ({sorted(stray)})", not stray)
    lstray = {k for L in pkg["lines"] for k in L} - REGELVELDEN
    check(f"geen ander veld op een regel ({sorted(lstray)})", not lstray)
    check("geen materialId, dat bij een ander op het verkeerde materiaal kan vallen",
          not any("materialId" in L for L in pkg["lines"]))
    check("geen prijs, leverancier of voorraad", "costPerGram" not in json.dumps(pkg)
          and "Somebody" not in json.dumps(pkg) and "50 g" not in json.dumps(pkg))
    check("een solventregel draagt geen (solvent) in zijn naam",
          not any("(solvent)" in L["material"] for L in pkg["lines"]))
    solvL = next((L for L in pkg["lines"] if L["material"] == solvnaam), None)
    check(f"de solventregel is als solvent gemerkt ({solvnaam})", solvL and solvL.get("solvent") is True)
    check("en de andere regels niet",
          not any(L.get("solvent") for L in pkg["lines"] if L["material"] != solvnaam))
    spoor = next((L for L in pkg["lines"] if abs(L["weightG"] - 0.0004) < 1e-9), None)
    check(f"een spoorregel van 0,0004 g overleeft de afronding ({spoor and spoor['weightG']})", spoor is not None)
    eigen = next((L for L in pkg["lines"] if L["material"] == mat), None)
    check(f"de eigen dilutie gaat mee zoals ze is ({eigen and eigen.get('dilutionPct')})",
          eigen and eigen["dilutionPct"] == 7)

    # ---------- een lege versie en een verweesde regel ----------
    msgs.clear()
    page.evaluate("""() => {
        DATA.formulas.push({id: "f-leeg", name: "Leeg", category: "Uncategorised", created: today(),
          versions: [{v: 1, date: today(), lines: []}]});
        buildUsage(); switchTab("F", "f-leeg", {type: "v", idx: 0});
    }""")
    page.wait_for_timeout(500)
    page.click("#btnShare"); page.wait_for_timeout(400)
    check(f"een lege versie wordt niet gedeeld ({[m[:40] for m in msgs]})",
          any("no lines to share" in m for m in msgs))
    msgs.clear()
    page.evaluate("""() => {
        const f = DATA.formulas.find(x => x.id === "f-leeg");
        const m = DATA.materials[0];
        f.versions[0].lines = [{materialId: m.id, dilutionPct: 100, weightG: 5, remark: 1},
                               {materialId: "m-bestaat-niet", dilutionPct: 100, weightG: 3, remark: 1}];
        buildUsage(); render();
    }""")
    page.wait_for_timeout(400)
    with page.expect_download() as dl2:
        page.click("#btnShare")
    weespkg = json.load(open(dl2.value.path(), encoding="utf-8"))
    check(f"een regel naar een verdwenen materiaal wordt gemeld ({[m[:40] for m in msgs]})",
          any("no longer exists" in m for m in msgs))
    check("en gaat niet mee in het bestand", len(weespkg["lines"]) == 1)

    # ---------- de rondgang: bij iemand anders, die het materiaal en het solvent niet heeft ----------
    page2 = ctx.new_page()
    msgs2 = []
    page2.on("pageerror", lambda e: errs.append(str(e)))
    page2.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page2.goto(URL); page2.wait_for_timeout(900)
    page2.evaluate("() => idb.set('demoData', null)")
    page2.reload(); page2.wait_for_timeout(900)
    page2.click("#btnStarter"); page2.wait_for_timeout(1300)
    page2.evaluate("""(a) => {              // hij heeft dat ene materiaal en het solvent niet, en de formule evenmin
        for (const n of [a.mat, a.solv]){
            const i = DATA.materials.findIndex(m => m.name === n);
            if (i >= 0) DATA.materials.splice(i, 1);
        }
        DATA.formulas = DATA.formulas.filter(f => f.name !== a.formule);
        invalidateMats(); buildUsage(); render();
    }""", {"mat": mat, "solv": solvnaam, "formule": naam})
    page2.click("#btnHome"); page2.wait_for_timeout(400)
    page2.set_input_files("#impFile", f); page2.wait_for_timeout(900)
    voorbeeld = page2.text_content("#content")
    check("de voorvertoning noemt de formule", naam in voorbeeld)
    check("en de herkomst", "Shared from miFormulas" in voorbeeld)
    check(f"het ontbrekende materiaal is nieuw", "new · to order" in voorbeeld)
    check("de hint over een rond totaal blijft weg bij een gedeeld bestand",
          "suggests a complete transcription" not in voorbeeld)
    page2.click("#btnImpOk"); page2.wait_for_timeout(900)
    got = page2.evaluate("""(naam) => { const f = DATA.formulas.find(x => x.name === naam);
        const v = f.versions[f.versions.length - 1];
        const K = calc(v.lines);
        return {naam: f.name, cat: f.category, notes: v.notes, n: v.lines.length, label: v.name,
                abs: +K.totalAbsPct.toFixed(2), gewichten: v.lines.map(l => l.weightG)}; }""", naam)
    check(f"de formule is aangekomen ({got['naam']}, {got['n']} regels)", got["n"] == nlines)
    check(f"met het label van de afzender ({got['label']!r})", got["label"] == "45gr")
    check("met de notities erbij", "more geraniol" in (got["notes"] or ""))
    check("en met de gewichten van de afzender",
          [round(w, 6) for w in got["gewichten"]] == [round(L["weightG"], 6) for L in pkg["lines"]])
    nieuw = page2.evaluate("""(naam) => { const m = DATA.materials.find(x => x.name === naam);
        return m && {cas: m.cas, wish: !!m.wishlist, pct: m.dilutions[0].pct}; }""", mat)
    check(f"het ontbrekende materiaal is aangemaakt als to order ({nieuw})", nieuw and nieuw["wish"])
    if page.evaluate("window.__cas"):
        check("met het CAS-nummer uit het bestand", nieuw["cas"] == page.evaluate("window.__cas"))
    check("op de dilutie van de afzender", nieuw and nieuw["pct"] == 7)
    check("en het staat op de bestellijst", page2.evaluate(
        "(naam) => (DATA.orderList || []).some(o => o.name === naam)", mat))
    solvm = page2.evaluate("(n) => { const m = DATA.materials.find(x => x.name === n); return m && !!m.isSolvent; }", solvnaam)
    check(f"het solvent is bij de ontvanger als solvent aangemaakt", solvm is True)
    check(f"dus klopt de concentratie meteen ({got['abs']} %)", got["abs"] < 50)

    # ---------- de ontvanger die de formule al heeft: nieuwe versie voorgesteld ----------
    page2.click("#btnHome"); page2.wait_for_timeout(400)
    page2.set_input_files("#impFile", f); page2.wait_for_timeout(900)
    sel = page2.evaluate("""() => { const s = document.querySelector("#impTarget");
        return {waarde: s.value, tekst: s.options[s.selectedIndex].textContent}; }""")
    check(f"de gelijknamige formule staat voorgekozen ({sel['tekst']})",
          sel["waarde"] and naam in sel["tekst"])
    check("met een regel die het uitlegt", page2.locator("#impTwin").count() == 1)
    page2.click("#btnImpCancel"); page2.wait_for_timeout(300)

    check(f"geen paginafouten ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
