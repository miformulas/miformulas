"""Bouw 261010a: zoeken op woorden in elke volgorde, en de knoppen TGSC en Olfactorian met de link uit de library.
- Zoeken: een spatie scheidt de woorden, elk woord moet in dezelfde naam staan (elk extra woord maakt de lijst kleiner),
  een woord blijft een stuk tekst en een koppelteken scheidt niets. In de lijst (Materials, Formulas, To order), de
  suggesties uit de library, Browse the library… (ook de categorie), Export my inventory as a library… en Which
  material? na Add line. CAS en beschrijving blijven de hele term zoals getypt; één woord zoekt zoals voordien.
- Knoppen: de directe link uit de library bij de eigen naam, een eigen alternatieve naam of de alternatieve naam van één
  librarymateriaal; DuckDuckGo bij twee kandidaten, een adres dat geen pagina van die site is, alleen een gelijk CAS,
  een materiaal dat de library niet kent, en na Remove the library (Undo brengt de links terug).
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

T = "https://www.thegoodscentscompany.com/data/"
O = "https://olfactorian.com/materials/"
DDG = "https://duckduckgo.com/?q="
LIB = {"type": "miformulas-materials", "name": "Zoeken en links", "version": "2026-10-10", "licence": "CC BY 4.0",
       "materials": [
    {"name": "Decalactone gamma", "cas": "706-14-9", "category": "Fruits", "tgsc": T + "rw1001101.html",
     "olfactorian": O + "gamma-decalactone"},
    {"name": "Damascone delta", "aliases": ["delta-damascone"], "cas": "57378-68-4", "category": "Fruits"},
    {"name": "Jasmin sambac abs.", "cas": "91770-14-8", "category": "Flowers - white"},
    {"name": "Ambroxide", "aliases": ["Ambrox", "Ambrofix"], "cas": "6790-58-5", "category": "Woody - amber",
     "tgsc": T + "rw1016071.html", "olfactorian": O + "ambroxide"},
    {"name": "Furaneol", "aliases": ["strawberry furanone"], "cas": "3658-77-3", "category": "Fruits",
     "tgsc": T + "rw1000931.html", "olfactorian": O + "strawberry-furanone"},
    {"name": "Cypriol", "aliases": ["cyperus scariosus root oil"], "category": "Woody", "tgsc": T + "rw1000002.html",
     "olfactorian": O + "cypriol"},
    {"name": "Cypriol cœur", "aliases": ["cyperus scariosus root oil"], "category": "Woody",
     "tgsc": T + "rw1000003.html", "olfactorian": O + "cypriol-coeur"},
    {"name": "Vreemde link", "category": "Woody", "tgsc": "https://example.com/data/rw1000004.html",
     "olfactorian": "javascript:alert(1)"},
    {"name": "Alleen TGSC", "category": "Woody", "tgsc": T + "es1000005.html"}]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # eigen materialen naast de starterset (die al Decalactone gamma en Damascone Alpha heeft)
    page.evaluate("""() => {
        let n = 0;   // een eigen id per materiaal: "Aldehyde C-11 proef" en "Aldehyde C11 proef" gaven er één
        const maak = (naam, extra) => Object.assign({id: "m-proef" + (++n), name: naam, category: "Fruits",
            pyramid: 2, isSolvent: false, cas: "", aliases: "", supplier: "", description: "",
            dilutions: [{pct: 100, isBase: true, date: today(), notes: ""}]}, extra);
        DATA.materials.push(
            maak("Peach lactone", {aliases: "gamma-undecalactone; Aldehyde C14"}),
            maak("Rose otto proef", {category: "Flowers - red", description: "floral\\nwith traces of gamma decalactone"}),
            maak("Cis-3-hexenol proef", {category: "Herbal - Green"}),
            maak("Aldehyde C-11 proef", {category: "Aldehydes"}),
            maak("Aldehyde C11 proef", {category: "Aldehydes"}),
            maak("Ambrofix (Giv)", {category: "Woody - amber", aliases: "Ambroxide"}),
            maak("Strawberry furanone", {}),
            maak("Cyperus scariosus root oil", {category: "Woody"}),
            maak("Vreemde link", {category: "Woody"}),
            maak("Alleen TGSC", {category: "Woody"}),
            maak("Lactone met CAS", {cas: "706-14-9"}),
            maak("Twee namen", {aliases: "Ambroxide; Furaneol"}));
        DATA.materials.sort((a, b) => a.name.localeCompare(b.name)); invalidateMats();
        DATA.orderList.push({id: "o-proef", materialId: null, name: "Hedione high cis proef", note: "", price: "", added: today()});
        render(); }""")
    page.wait_for_timeout(300)

    def lijst(term, tab="M"):
        page.click("#tab" + tab); page.wait_for_timeout(250)
        page.fill("#searchBox", term); page.wait_for_timeout(400)
        return page.evaluate("""() => [...document.querySelectorAll("#list .item[data-id]")].map(e => {
            const id = e.dataset.id, x = DATA.materials.find(m => m.id === id) || DATA.formulas.find(f => f.id === id)
              || (DATA.orderList || []).find(o => o.id === id);
            return x ? x.name : "?"; })""")

    # ---------- Materials ----------
    r = lijst("gamma decalactone")
    check(f"'gamma decalactone' vindt Decalactone gamma ({r})", "Decalactone gamma" in r)
    check("en Peach lactone via de alternatieve naam gamma-undecalactone", "Peach lactone" in r)
    check("en Rose otto proef via de beschrijving, die de term letterlijk heeft", "Rose otto proef" in r)
    via = page.evaluate("""() => Object.fromEntries(matSearch("gamma decalactone").map(h => [h.m.name, h.via]))""")
    check(f"matSearch zegt waarop het vond ({via})", via.get("Decalactone gamma") == "name"
          and via.get("Peach lactone") == "alias" and via.get("Rose otto proef") == "description")
    r = lijst("decalactone gamma")
    check(f"'decalactone gamma': de naam wel, de beschrijving niet, want die zoekt de term zoals getypt ({r})",
          "Decalactone gamma" in r and "Rose otto proef" not in r)
    r = lijst("alpha damascone")
    check(f"'alpha damascone' vindt Damascone Alpha ({r})", "Damascone Alpha" in r)
    r = lijst("cis 3 hexenol")
    check(f"'cis 3 hexenol' vindt Cis-3-hexenol proef: een woord is een stuk tekst ({r})", "Cis-3-hexenol proef" in r)
    r = lijst("c-11")
    check(f"'c-11' blijft één woord: Aldehyde C-11 proef wel, Aldehyde C11 proef niet ({r})",
          "Aldehyde C-11 proef" in r and "Aldehyde C11 proef" not in r)
    g, gl = lijst("gamma"), lijst("gamma lactone")
    check(f"elk woord erbij maakt de lijst kleiner: 'gamma' {len(g)}, 'gamma lactone' {len(gl)} ({gl})",
          0 < len(gl) < len(g) and set(gl) <= set(g) and "Decalactone gamma" in gl)
    r = lijst("peach gamma")
    check(f"de woorden moeten in dezelfde naam staan: 'peach gamma' vindt Peach lactone niet ({r})", "Peach lactone" not in r)
    zelfde = page.evaluate("""() => ["lacton", "c11", "ambro", "hexenol", "706-14", "floral"].every(t => {
        const nu = matSearch(t).map(h => h.m.name).sort();
        const was = DATA.materials.filter(m => fold(m.name).includes(t) || fold(m.aliases).includes(t) || fold(m.cas).includes(t)
            || fold(m.supplier).includes(t) || fold(m.description).includes(t)).map(m => m.name).sort();
        return JSON.stringify(nu) === JSON.stringify(was); })""")
    check("één woord zoekt zoals voordien (naam, alternatieve naam, CAS, leverancier, beschrijving)", zelfde)

    # ---------- Formulas en To order ----------
    r = lijst("men 1881", "F")
    check(f"Formulas: 'men 1881' vindt 1881 for men ({r})", r == ["1881 for men"])
    r = lijst("men for", "F")
    check(f"Formulas: 'men for' vindt de vier 'for men', A Men niet ({r})",
          sorted(r) == ["1881 for men", "Acqua di Gio for men", "Bv for men", "Cool Water for men"])
    r = lijst("cis hedione", "T")
    check(f"To order: 'cis hedione' vindt Hedione high cis proef ({r})", r == ["Hedione high cis proef"])
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # ---------- de library ----------
    f = os.path.join(tempfile.mkdtemp(), "zoeken-en-links.json")
    open(f, "w", encoding="utf-8").write(json.dumps(LIB))
    page.click("#btnHome"); page.wait_for_timeout(400)
    page.set_input_files("#impList", f); page.wait_for_timeout(800)
    check("de testlibrary is geladen", page.evaluate("DATA.materialList && DATA.materialList.materials.length") == 9)

    lijst("delta damascone"); lst = page.text_content("#list")
    check(f"de lijst biedt Damascone delta uit de library aan bij 'delta damascone'",
          "In the materials library" in lst and page.locator('#list button[data-add="Damascone delta"]').count() == 1)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    page.click("#btnNewMat"); page.wait_for_timeout(300)
    page.click("#nmBrowse"); page.wait_for_timeout(400)
    def browse(term):
        page.fill("#brQ", term); page.wait_for_timeout(300)
        return page.evaluate("""() => [...document.querySelectorAll("#brRows input[data-n]")].map(i => i.dataset.n)""")
    r = browse("delta damascone")
    check(f"Browse: 'delta damascone' vindt Damascone delta ({r})", r == ["Damascone delta"])
    r = browse("white flowers")
    check(f"Browse: 'white flowers' vindt wat in Flowers - white staat ({r})", r == ["Jasmin sambac abs."])
    r = browse("jasmin white")
    check(f"Browse: naam en categorie tellen niet samen: 'jasmin white' vindt niets ({r})", r == [])
    r = browse("706-14-9")
    check(f"Browse: het CAS zoals getypt ({r})", r == ["Decalactone gamma"])
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    page.click("#btnHome"); page.wait_for_timeout(400)
    page.click("#btnIO"); page.wait_for_timeout(400)
    page.click("#btnExpL"); page.wait_for_timeout(500)
    def export(term):
        page.fill("#exQ", term); page.wait_for_timeout(300)
        return page.evaluate("""() => [...document.querySelectorAll("#exRows input[data-i]")].map(i =>
            DATA.materials.find(m => m.id === i.dataset.i).name)""")
    r = export("gamma decalactone")
    check(f"Export: 'gamma decalactone' vindt Decalactone gamma en Peach lactone ({r})",
          "Decalactone gamma" in r and "Peach lactone" in r)
    r = export("lactone peach")
    check(f"Export: 'lactone peach' vindt Peach lactone ({r})", r == ["Peach lactone"])
    r = export("woody amber")
    check(f"Export: 'woody amber' vindt de categorie Woody - amber ({r})", "Ambrofix (Giv)" in r)
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # Which material? na Add line
    lijst("1881", "F"); page.click("#list .item >> nth=0"); page.wait_for_timeout(500)
    page.fill("#addMat", "gamma decalactone"); page.click("#btnAddLine"); page.wait_for_timeout(500)
    opts = page.evaluate("""() => [...document.querySelectorAll("#pkMat option")].map(o => o.textContent)""")
    check(f"Add line: Which material? biedt Decalactone gamma aan ({opts})", any(o.startswith("Decalactone gamma") for o in opts))
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.fill("#searchBox", ""); page.wait_for_timeout(200)

    # ---------- de knoppen ----------
    links = page.evaluate("""(namen) => Object.fromEntries(namen.map(n => {
        const m = DATA.materials.find(x => x.name === n), d = document.createElement("div");
        d.innerHTML = lookupLinks(m);
        return [n, [...d.querySelectorAll("a")].map(a => [a.textContent.trim(), a.getAttribute("href"), a.title])]; }))""",
        ["Decalactone gamma", "Ambrofix (Giv)", "Strawberry furanone", "Cyperus scariosus root oil", "Vreemde link",
         "Alleen TGSC", "Lactone met CAS", "Twee namen", "Damascone Alpha"])
    def href(n, i): return links[n][i][1] if len(links.get(n, [])) == 3 else None
    def zoekt(n, i): return (href(n, i) or "").startswith(DDG) and "via DuckDuckGo" in links[n][i][2]
    def direct(n, i, url): return href(n, i) == url and "link from the materials library" in links[n][i][2]
    check(f"eigen naam: de pagina's uit de library ({links['Decalactone gamma'][:2]})",
          direct("Decalactone gamma", 0, T + "rw1001101.html") and direct("Decalactone gamma", 1, O + "gamma-decalactone"))
    check("een eigen alternatieve naam die de naam van een librarymateriaal is (Ambrofix (Giv) met Ambroxide)",
          direct("Ambrofix (Giv)", 0, T + "rw1016071.html") and direct("Ambrofix (Giv)", 1, O + "ambroxide"))
    check("de alternatieve naam van één librarymateriaal (Strawberry furanone bij Furaneol)",
          direct("Strawberry furanone", 0, T + "rw1000931.html") and direct("Strawberry furanone", 1, O + "strawberry-furanone"))
    check("twee librarymaterialen met die alternatieve naam: zoeken", zoekt("Cyperus scariosus root oil", 0)
          and zoekt("Cyperus scariosus root oil", 1))
    check(f"een adres dat geen pagina van die site is: zoeken ({links['Vreemde link'][:2]})",
          zoekt("Vreemde link", 0) and zoekt("Vreemde link", 1))
    check("alleen een TGSC-link: TGSC direct, Olfactorian zoekt",
          direct("Alleen TGSC", 0, T + "es1000005.html") and zoekt("Alleen TGSC", 1))
    check("alleen hetzelfde CAS: zoeken, op het CAS", zoekt("Lactone met CAS", 0) and zoekt("Lactone met CAS", 1)
          and "706-14-9" in (href("Lactone met CAS", 0) or ""))
    check("twee alternatieve namen voor twee librarymaterialen: zoeken", zoekt("Twee namen", 0) and zoekt("Twee namen", 1))
    check("een materiaal dat de library niet kent: zoeken", zoekt("Damascone Alpha", 0) and zoekt("Damascone Alpha", 1))
    check("IFRA blijft de library van IFRA", all(l[2][1] == "https://ifrafragrance.org/safe-use/library"
          for l in links.values() if len(l) == 3) and len(links) == 9)

    # op de pagina zelf, en na Remove the library en Undo
    lijst("Decalactone gamma"); page.click("#list .item >> nth=0"); page.wait_for_timeout(400)
    def opdepagina():
        return page.evaluate("""() => [...document.querySelectorAll("#content .metaLine a.lookup")].map(a =>
            [a.textContent.trim(), a.getAttribute("href"), a.target, a.rel])""")
    pg = opdepagina()
    check(f"de materiaalpagina toont de directe links, in een nieuw tabblad ({pg[:2]})", len(pg) == 3
          and pg[0][:2] == ["TGSC ↗", T + "rw1001101.html"] and pg[1][:2] == ["Olfactorian ↗", O + "gamma-decalactone"]
          and all(l[2] == "_blank" and "noopener" in l[3] for l in pg))
    page.click("#btnSettings"); page.wait_for_timeout(400)
    page.click("#setListDel"); page.wait_for_timeout(500)
    pg = opdepagina()
    check(f"zonder library zoeken de knoppen weer ({pg[:2]})", page.evaluate("DATA.materialList") is None
          and len(pg) == 3 and pg[0][1].startswith(DDG) and pg[1][1].startswith(DDG))
    page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    pg = opdepagina()
    check(f"Undo brengt de library en de directe links terug ({pg[:2]})", len(pg) == 3
          and pg[0][1] == T + "rw1001101.html" and pg[1][1] == O + "gamma-decalactone")

    check(f"geen paginafouten ({errs[:2]})", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
