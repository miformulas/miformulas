"""Share this version…: what the file holds, and the way back in at the other end.
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
REGELVELDEN = {"material", "dilutionPct", "weightG", "cas"}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1300)

    # ---------- een versie met notities, een eigen dilutie en een prijs op een materiaal ----------
    page.evaluate("""() => {
        const f = DATA.formulas.find(x => x.versions.length && x.versions[0].lines.length > 3);
        const v = f.versions[0];
        v.notes = "Second trial, more geraniol.";
        const m = matById(v.lines[0].materialId);
        m.costPerGram = 2.5; m.supplier = "Somebody"; m.inventory = "50 g";
        m.dilutions.push({pct: 7, isBase: false, date: today(), notes: ""});   // een dilutie die een ander niet heeft
        v.lines[0].dilutionPct = 7;
        window.__f = f.name; window.__mat = m.name; window.__cas = m.cas || "";
        window.__lines = v.lines.length;
        switchTab("F", f.id, {type: "v", idx: 0});
    }""")
    page.wait_for_timeout(600)
    naam = page.evaluate("window.__f"); mat = page.evaluate("window.__mat")
    nlines = page.evaluate("window.__lines")

    # ---------- de knop en zijn buren ----------
    check("de uitvoerrij heeft vier knoppen",
          all(page.locator(s).count() == 1 for s in ("#btnSheet", "#btnCsv", "#btnShare", "#btnPrint")))
    check("Share this version…", page.text_content("#btnShare").strip() == "Share this version…")
    check("de hint zegt welke voor wie is",
          "Excel for someone without miFormulas" in page.text_content("#content"))

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
    check("naam, versie en categorie gaan mee",
          pkg["name"] == naam and pkg.get("versionName") and pkg.get("category"))
    check(f"de herkomst staat erbij ({pkg.get('source')})", "Shared from miFormulas" in pkg.get("source", ""))
    check("de notities van de versie gaan mee", pkg.get("notes") == "Second trial, more geraniol.")
    check("elke regel is meegegaan", len(pkg["lines"]) == nlines)
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
    eigen = next((L for L in pkg["lines"] if L["material"] == mat), None)
    check(f"de eigen dilutie gaat mee zoals ze is ({eigen and eigen.get('dilutionPct')})",
          eigen and eigen["dilutionPct"] == 7)

    # ---------- de rondgang: bij iemand anders, die één materiaal niet heeft ----------
    page2 = ctx.new_page()
    msgs2 = []
    page2.on("pageerror", lambda e: errs.append(str(e)))
    page2.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page2.goto(URL); page2.wait_for_timeout(900)
    page2.evaluate("() => idb.set('demoData', null)")
    page2.reload(); page2.wait_for_timeout(900)
    page2.click("#btnStarter"); page2.wait_for_timeout(1300)
    page2.evaluate("""(a) => {              // hij heeft dat ene materiaal niet, en de formule evenmin
        const i = DATA.materials.findIndex(m => m.name === a.mat);
        if (i >= 0) DATA.materials.splice(i, 1);
        DATA.formulas = DATA.formulas.filter(f => f.name !== a.formule);
        invalidateMats(); buildUsage(); render();
    }""", {"mat": mat, "formule": naam})
    page2.click("#btnHome"); page2.wait_for_timeout(400)
    page2.set_input_files("#impFile", f); page2.wait_for_timeout(900)
    voorbeeld = page2.text_content("#content")
    check("de voorvertoning noemt de formule", naam in voorbeeld)
    check("en de herkomst", "Shared from miFormulas" in voorbeeld)
    check(f"het ontbrekende materiaal is nieuw", "new · to order" in voorbeeld)
    page2.click("#btnImpOk"); page2.wait_for_timeout(900)
    got = page2.evaluate("""(naam) => { const f = DATA.formulas.find(x => x.name === naam);
        const v = f.versions[f.versions.length - 1];
        return {naam: f.name, cat: f.category, notes: v.notes, n: v.lines.length,
                gewichten: v.lines.map(l => l.weightG)}; }""", naam)
    check(f"de formule is aangekomen ({got['naam']}, {got['n']} regels)", got["n"] == nlines)
    check("met de notities erbij", "more geraniol" in (got["notes"] or ""))
    check("en met de gewichten van de afzender",
          [round(w, 3) for w in got["gewichten"]] == [round(L["weightG"], 3) for L in pkg["lines"]])
    nieuw = page2.evaluate("""(naam) => { const m = DATA.materials.find(x => x.name === naam);
        return m && {cas: m.cas, wish: !!m.wishlist, pct: m.dilutions[0].pct}; }""", mat)
    check(f"het ontbrekende materiaal is aangemaakt als to order ({nieuw})", nieuw and nieuw["wish"])
    if page.evaluate("window.__cas"):
        check("met het CAS-nummer uit het bestand", nieuw["cas"] == page.evaluate("window.__cas"))
    check("op de dilutie van de afzender", nieuw and nieuw["pct"] == 7)
    check("en het staat op de bestellijst", page2.evaluate(
        "(naam) => (DATA.orderList || []).some(o => o.name === naam)", mat))

    check(f"geen paginafouten ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
