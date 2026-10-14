"""Bouw 261011a (opruiming en de index van de library, bouw 2 van de analyse van 10/10): niets dat je ziet verandert.
Twee browsers naast elkaar: de referentie REF uit git (eerst 261010d, sinds 261011b bouw 261011a, sinds 261011c bouw
261011b, sinds 261011d bouw 261011c, sinds 261011e bouw 261011d, sinds 261012a bouw 261011e, sinds 261013a bouw 261012a, sinds 261014a bouw 261013a) en de bouw van de repo, met dezelfde data, dezelfde
klok en hetzelfde toeval (de ids). Na elke stap is de HTML van de pagina byte voor byte gelijk (kop, lijst, pagina,
open venster en afdrukgebied; zonder het script, de ingebedde handleiding als sjabloon en de bewaarmelding, en met de
bouwstempel weggelaten), net als serialize() en de meldingen. Wat een bouw bewust toevoegt, staat in NIEUW en telt niet
mee (261012a: de versie als tekst in de bench view, en de lijst zolang er een zoekterm staat, want die is één lijst op
naam geworden; zoeken-op-naam.py test haar), en wat een bouw bewust in de HTML omzet, staat in REPL en RX (261011e:
Change category… weg; de categorie op de materiaalpagina op één regel, die als @CAT@ telt; sinds 261012a leeg); in Help
telt alleen de balk, want de tekst van de handleiding
verandert met de handleiding en help.py test ze. Het piramide-icoontje telt als zijn niveau, maat en kleur: sinds 261011c
is het één span met een masker in plaats van een svg (geselecteerde-rij-en-icoon.py test hoe het eruitziet).
Zolang er een zoekterm staat, telt de lijst niet mee, maar vinden beide bouwen dezelfde rijen (sinds 261012a).
De stappen: Welcome, Settings en Help; elke versie en de bench view van elke formule; alle sorteringen van de tabel,
de bench en Compare; elk materiaal; zoeken in beide lijsten; To order; Browse the library…, + New material… en Add
line met een naam uit de library; de kleurmerken, Lower en Create premix…; Import materials inventory from CSV…
met namen die je al hebt en alternatieve namen (sinds 261013a zonder een naam twee keer in het blad of een rij die een
eerdere rij als alternatieve naam draagt: die cureert de invoer niet meer, audit-v3-ronde1.py test dat); Import formula… (één formule, meerdere, een blad van formules); Undo; alleen-lezen
en een telefoon; rijen in de lijst aangeklikt met de muis. Staat miformulas-data.json naast public (de proef), dan ook
elke versie en elk materiaal daarvan;
staat de gepubliceerde library er, dan is zij de library, anders een kleine eigen.
Daarna wat bouw 261011a zelf veranderde, en dat faalt op 261010d: geen icoon van 512 px, geen ownFind, de cache van
listIndex ook zonder library, listFind, csvPlan en de CSV-import via de index, en de melding na Restore daily
snapshot met de klasse wide.
Bouw 3 houdt deze referentie; een bouw met een zichtbare wijziging zet REF op de vorige bouw.
Vereist de lokale webserver op poort 8765 (zie README) en git met de geschiedenis van de repo."""
import json, os, subprocess, tempfile, time
from playwright.sync_api import sync_playwright

REF, REF_BOUW = "d384b78", "261013a"
URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
EIGEN = os.path.join(PUB, "..", "miformulas-data.json")
GEPUB = os.path.join(PUB, "..", "miformulas-materials.json")
STARTER = json.load(open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8"))
NIEUW = ["#searchBox:not(:placeholder-shown) + #list"]   # bewust toegevoegd of omgezet sinds REF (261012a: de versie
# als tekst boven de bank en de lijst met een zoekterm; 261014a: de lijst met een zoekterm, want een treffer op
# alternatieve naam, CAS of leverancier zegt in het grijze regeltje wat er trof; beide bouwen vinden wel dezelfde rijen)
# bewust omgezet sinds REF: als tekst [weg, in de plaats] en als patroon [patroon, in de plaats] (261011e: Change
# category… en de categorie op de materiaalpagina; 261013a: de teller van de CSV-import; 261014a: keuzelijst, kleurvakje
# en + New category van een formule als één groep, en de bron van de library als tooltip van de attributie in Settings)
REPL = [['<span class="fcatctl">', ""]]
RX = [[r'(id="btnNewFCat"[^>]*>\+ New category</button>)</span>', "$1"],
      [r'<div class="hint"(?: title="[^"]*")?>(miFormulas materials library, https://miformulas\.com)(?: · [^<]*)?</div>', '<div class="hint">$1</div>']]
TMP = tempfile.mkdtemp()
ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

try:
    REF_HTML = subprocess.run(["git", "-C", PUB, "show", f"{REF}:index.html"], capture_output=True, check=True).stdout
except Exception as e:   # een kopie zonder git (of zonder die commit) kan niet vergelijken
    REF_HTML = None

KLEIN = {"type": "miformulas-materials", "name": "Kleine library", "version": "2026-10-11", "licence": "CC BY 4.0",
         "materials": [
    {"name": "Decalactone gamma", "aliases": ["4-Decanolide", "gamma-Decanolactone", "Peach Lactone"], "cas": "706-14-9",
     "category": "Fruity", "pyramid": 1},
    {"name": "Vetiver Haïti", "aliases": ["vetiveria zizanioides stapf."], "cas": "8016-96-4", "category": "Woody", "pyramid": 4},
    {"name": "Patchouli cœur", "aliases": ["pogostemon cablin oil"], "cas": "8014-09-3", "category": "Woody", "pyramid": 4},
    {"name": "Aldehyde C-11 undecylenic", "aliases": ["Undecylenic aldehyde"], "cas": "112-45-8", "category": "Aldehydic", "pyramid": 0},
    {"name": "İstanbul rose", "aliases": ["Rosa damascena Türkiye"], "category": "Floral", "pyramid": 2},
    {"name": "Rose oxide", "aliases": ["Rosenoxid"], "cas": "16409-43-1", "category": "Floral", "pyramid": 1},
    {"name": "Ambroxide", "aliases": ["Ambroxan", "Ambrofix"], "cas": "6790-58-5", "category": "Amber", "pyramid": 4}]}
LIB = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else KLEIN

# ---- de vergelijking ----
SEED = """(() => { let a = 20261011; Math.random = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; })();"""
CAP = """async ({hash, repl, rx, nieuw}) => {
  const b = document.body.cloneNode(true);
  b.querySelectorAll(["script", "template", ...nieuw].join(", ")).forEach(x => x.remove());
  // in Help telt alleen de balk: de handleiding verandert met de handleiding, ook haar alinea's en de regeleinden ertussen
  b.querySelectorAll(".help").forEach(h => [...h.childNodes].forEach(n => { if (!n.classList?.contains("helpbar")) n.remove(); }));
  const s = b.querySelector("#saveState");
  if (s){ s.textContent = ""; for (const a of ["class", "title", "data-short"]) s.removeAttribute(a); }
  let h = (document.body.className + "\\n" + b.innerHTML).split(">" + BUILD + "<").join(">@B@<").split("build " + BUILD).join("build @B@");
  for (const [x, y] of repl) h = h.split(x).join(y);
  for (const [p, y] of rx) h = h.replace(new RegExp(p, "g"), y);
  // het piramide-icoontje als niveau, maat en kleur: een svg tot 261011b, één span met een masker sinds 261011c
  h = h.replace(/<svg class="pyricon" width="(\\d+)" height="\\d+" viewBox="0 0 14 14" aria-hidden="true">(.*?)<\\/svg>/g, (_, z, binnen) => {
      const lv = [...binnen.matchAll(/fill="([^"]*)"/g)].findIndex(m => m[1] !== "none");
      return `[pyr ${lv < 0 ? "x" : lv} ${z} ${(binnen.match(/stroke="([^"]*)"/) || [])[1]}]`; })
    .replace(/<span class="pyricon lv(\\w)" style="width:(\\d+)px;height:\\d+px;background:([^"]*)" aria-hidden="true"><\\/span>/g,
      (_, lv, z, k) => `[pyr ${lv} ${z} ${k}]`);
  if (!hash) return h;
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(h));
  return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2, "0")).join("");
}"""
SER = """async () => { const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(serialize()));
  return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2, "0")).join(""); }"""
GROEPEN = {}   # groep -> [stappen, eerste verschil]

def opstarten(b, ref, breed=1400):
    c = b.new_context(viewport={"width": breed, "height": 900}, locale="en-GB", timezone_id="Europe/Brussels",
                      accept_downloads=True)
    c.clock.set_fixed_time("2026-10-11T10:00:00")
    c.add_init_script(SEED)
    if ref:
        for u in (URL, URL + "index.html"):
            c.route(u, lambda r: r.fulfill(status=200, body=REF_HTML, headers={"content-type": "text/html; charset=utf-8"}))
    c.set_default_timeout(10000)
    p = c.new_page(); p.msgs = []; p.errs = []
    p.on("dialog", lambda d: (p.msgs.append(d.message), d.accept()))
    p.on("pageerror", lambda e: p.errs.append(str(e)))
    p.goto(URL); p.wait_for_timeout(800)
    return p

def verschil(x, y):
    i = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
    return f"op {i}: {x[max(0, i-70):i+70]!r} | {y[max(0, i-70):i+70]!r}"

def stap(groep, actie=None, data=False, wacht=0, hash=False):
    """Dezelfde handeling in beide; daarna dezelfde HTML, meldingen en (met data) dezelfde serialize()."""
    for p in (R, A):
        p.msgs.clear()
        if actie: actie(p)
        if wacht: p.wait_for_timeout(wacht)
    g = GROEPEN.setdefault(groep, [0, None]); g[0] += 1
    if g[1]: return
    r = R.evaluate(CAP, {"hash": hash, "repl": REPL, "rx": RX, "nieuw": NIEUW}); a = A.evaluate(CAP, {"hash": hash, "repl": REPL, "rx": RX, "nieuw": NIEUW})
    if r != a:
        g[1] = f"stap {g[0]}: " + ("de HTML verschilt" if hash else verschil(r, a)); return
    if R.msgs != A.msgs:
        g[1] = f"stap {g[0]}: de meldingen verschillen: {R.msgs} | {A.msgs}"; return
    if data and R.evaluate(SER) != A.evaluate(SER):
        g[1] = f"stap {g[0]}: serialize() verschilt"

def verslag():
    for groep, (n, eerste) in GROEPEN.items():
        check(f"{groep} ({n} stappen)" + (f": {eerste}" if eerste else ""), not eerste)
    GROEPEN.clear()

ev = lambda js, arg=None: (lambda p: p.evaluate(js, arg))
klik = lambda sel: (lambda p: p.click(sel))
vul = lambda sel, t: (lambda p: p.fill(sel, t))
def vink(*idx):
    def f(p):
        for i in idx: p.check(f'#content input.selCb[data-i="{i}"]')
    return f
def reeks(*fs):
    def f(p):
        for x in fs: x(p)
    return f
def bestand(naam, inhoud):
    pad = os.path.join(TMP, naam)
    open(pad, "w", encoding="utf-8").write(inhoud if isinstance(inhoud, str) else json.dumps(inhoud))
    return pad
kies = lambda sel, pad: (lambda p: p.set_input_files(sel, pad))
VIEW = "v => { VIEW = v; HOMEVIEW = false; HELPVIEW = false; IMPORTP = null; render(); }"

with sync_playwright() as pw:
    b = pw.chromium.launch()
    t0 = time.time()

    # ======================= 1. dezelfde schermen op de starterset =======================
    check(f"de referentie {REF_BOUW} staat in git ({REF})", REF_HTML is not None)
    if REF_HTML is not None:
        R, A = opstarten(b, True), opstarten(b, False)
        check(f"links {REF_BOUW}, rechts de bouw van de repo ({R.evaluate('BUILD')}, {A.evaluate('BUILD')})",
              R.evaluate("BUILD") == REF_BOUW)
        stap("het startscherm")
        stap("de starterset met een library", reeks(klik("#btnStarter"), lambda p: p.wait_for_timeout(1500),
             ev("pkg => { setMaterialList(normLibrary(pkg)); render(); }", LIB)), data=True, wacht=300)
        stap("Welcome, Settings en Help", klik("#btnHome"), wacht=200)
        stap("Welcome, Settings en Help", klik("#btnSettings"), wacht=300)
        stap("Welcome, Settings en Help", lambda p: p.keyboard.press("Escape"), wacht=200)
        stap("Welcome, Settings en Help", klik("#btnHelp"), wacht=300)
        check("de link naar de eerste vijf minuten staat nu in beide (de referentie is 261011b)",
              A.locator("#firstFive").count() == 1 and R.locator("#firstFive").count() == 1)
        stap("Welcome, Settings en Help", klik("#helpClose"), wacht=200)

        F = A.evaluate("DATA.formulas.map(f => ({id: f.id, n: f.versions.length}))")
        for f in F:
            for i in range(f["n"]):
                stap("elke versie van elke formule", ev(VIEW, {"tab": "F", "id": f["id"], "sub": {"type": "v", "idx": i}}))
            stap("de bench view van elke formule", ev(VIEW, {"tab": "F", "id": f["id"], "sub": {"type": "v", "idx": f["n"] - 1, "bench": True}}))
        groot = A.evaluate("DATA.formulas.reduce((x, f) => f.versions.at(-1).lines.length > x.versions.at(-1).lines.length ? f : x).id")
        laatste = {"tab": "F", "id": groot, "sub": {"type": "v", "idx": 1}}
        for k in ["name", "dil", "weight", "rel", "abs", "cat", "pyr", "pyrb", "orig"]:
            for d in (1, -1):
                stap("de tabel in elke sortering", ev("([v, k, d]) => { SORT = {key: k, dir: d}; VIEW = v; render(); }", [laatste, k, d]))
        for k in ["orig", "name", "dil", "weight", "rel", "cat", "pyr", "pyrb"]:
            stap("de bench in elke sortering", ev("([v, k]) => { BSORT = k; VIEW = v; render(); }",
                 [{**laatste, "sub": {**laatste["sub"], "bench": True}}, k]))
        stap("de bench in elke sortering", ev("() => { BSORT = 'orig'; render(); }"))
        for f in F:
            stap("Compare op elke formule", reeks(ev(VIEW, {"tab": "F", "id": f["id"], "sub": {"type": "v", "idx": f["n"] - 1}}), klik("#btnCmp")))
            if f["id"] == groot:
                for k in ["diff", "name", "wA", "relA", "wB", "relB", "dlt", "cat", "pyr", "pyrb"]:
                    for d in (1, -1):
                        stap("Compare in elke sortering", ev("([k, d]) => { CSORT = {key: k, dir: d}; render(); }", [k, d]))
            stap("Compare op elke formule", klik("#btnCmpClose"))
        verslag()

        M = A.evaluate("DATA.materials.map(m => m.id)")
        stap("elk materiaal", ev(VIEW, {"tab": "M", "id": None, "sub": None}))
        iconen = [p.evaluate("() => [document.querySelectorAll('#list svg.pyricon').length, document.querySelectorAll('#list span.pyricon').length]") for p in (R, A)]
        check(f"beide tekenen het icoontje als één span (sinds 261011c); de vergelijking telt niveau, maat en kleur ({iconen})",
              iconen[0][0] == 0 and iconen[1][0] == 0 and iconen[0][1] > 100 and iconen[1][1] == iconen[0][1])
        stap("elk materiaal", ev(VIEW, {"tab": "M", "id": M[5], "sub": None}))
        for k in (3, 10, 11, 40, 3):
            stap("rijen in de lijst aanklikken", klik(f"#list .item >> nth={k}"), wacht=50)
        stap("rijen in de lijst aanklikken", ev(VIEW, {"tab": "F", "id": None, "sub": None}))
        for k in (0, 7, 2):
            stap("rijen in de lijst aanklikken", klik(f"#list .item >> nth={k}"), wacht=50)
        stap("elk materiaal", ev(VIEW, {"tab": "M", "id": None, "sub": None}))
        for m in M:
            stap("elk materiaal", ev(VIEW, {"tab": "M", "id": m, "sub": None}))
        # sinds 261012a telt de lijst niet mee zolang er een zoekterm staat (NIEUW: één lijst op naam in plaats van groepen);
        # wat ze vindt, moet wel hetzelfde zijn: dezelfde rijen, de rijen met ✎ en wat de library aanbiedt
        TREFFERS = """() => [[...document.querySelectorAll('#list .item')].map(e => e.dataset.id + (e.textContent.includes('✎') ? ' ✎' : '')).sort(),
            [...document.querySelectorAll('#list .sugRow button')].map(b => b.dataset.add).sort()]"""
        anders = []
        for q in ["a", "ros", "gamma decalactone", "decalactone", "haiti", "Haïti", "cœur", "coeur", "C-11", "c11",
                  "İstanbul", "istanbul", "ambr", "6790-58-5", "woody", "starter", "musk e", ""]:
            stap("zoeken in Materials", reeks(ev(VIEW, {"tab": "M", "id": None, "sub": None}), vul("#searchBox", q)))
            if R.evaluate(TREFFERS) != A.evaluate(TREFFERS): anders.append("M " + q)
        for q in ["cool", "for men", "v2", "rose", "zzz", ""]:
            stap("zoeken in Formulas", reeks(ev(VIEW, {"tab": "F", "id": None, "sub": None}), vul("#searchBox", q)))
            if R.evaluate(TREFFERS) != A.evaluate(TREFFERS): anders.append("F " + q)
        check(f"zoeken vindt in beide bouwen dezelfde rijen, met ✎ en de library (anders: {anders})", not anders)
        m0 = A.evaluate("DATA.materials[3].id")
        stap("To order", ev("""m => { DATA.orderList.push({id: "o-1", materialId: m, name: "", note: "restock", price: "", added: today()},
            {id: "o-2", materialId: null, name: "Iets nieuws", note: "", price: "", added: today()}); markDirty(); switchTab("T"); }""", m0),
             data=True)
        stap("To order", klik('#list .item[data-id="o-1"]'), wacht=100)
        verslag()

        # ---- wat iets maakt: de library, de kleurmerken, Lower, een premix, de imports ----
        stap("Browse the library…", ev("() => { switchTab('M', null, null); browseList(); }"), wacht=100)
        stap("Browse the library…", vul("#brQ", "ros"))
        stap("Browse the library…", vul("#brQ", "decalactone"))
        stap("Browse the library…", reeks(vul("#brQ", ""), lambda p: p.locator("#brRows input[data-n]:not([disabled])").nth(1).click(),
             lambda p: p.locator("#brRows input[data-n]:not([disabled])").nth(4).click()))
        stap("Browse the library…", klik("#dlgOk"), data=True, wacht=200)
        stap("Browse the library…", ev("() => undo()"), data=True)
        vrij = A.evaluate("() => listMaterials().filter(e => !ownsEntry(e, ownNames(), new Set(DATA.materials.map(m => normName(m.name))))).map(e => e.name)")
        naam = next((n for n in ["Patchouli cœur", "Vetiver Haïti", "Rose oxide"] if n in vrij), vrij[0])
        stap("+ New material… met een naam uit de library", klik("#btnNewMat"), wacht=100)
        stap("+ New material… met een naam uit de library", reeks(vul("#nmName", naam), lambda p: p.dispatch_event("#nmName", "change")), wacht=100)
        stap("+ New material… met een naam uit de library", klik("#dlgOk"), data=True, wacht=200)
        stap("+ New material… met een naam uit de library", ev("() => undo()"), data=True)
        stap("Add line met een naam uit de library", ev(VIEW, laatste))
        stap("Add line met een naam uit de library", reeks(vul("#addMat", naam), klik("#btnAddLine")), data=True, wacht=300)
        stap("de kleurmerken", reeks(vink(0, 1), klik('#content [data-mark="4"]')), data=True, wacht=100)
        stap("de kleurmerken", reeks(vink(2), klik('#content [data-mark="0"]')), data=True, wacht=100)
        stap("de kleurmerken", reeks(vink(1), klik('#content [data-mark="1"]')), data=True, wacht=100)
        stap("Lower en Higher", reeks(vink(3, 4), klik("#btnDilDown")), data=True, wacht=200)
        stap("Lower en Higher", reeks(vink(3), klik("#btnDilUp")), data=True, wacht=200)
        stap("Create premix…", reeks(vink(5, 6), klik("#btnPredil")), wacht=200)
        stap("Create premix…", klik("#dlgOk"), data=True, wacht=300)
        stap("Create premix…", ev("() => undo()"), data=True)
        verslag()

        eerste = STARTER["materials"][0]["name"]
        # sinds 261013a zonder "Foo Bar" (de alternatieve naam van Testolide X), een tweede Testolide X en "vetiver haiti":
        # die slaat 261012a over en komen nu binnen (audit v3, A1)
        csv = "\n".join(["Name;CAS;Aliases;Category;Dilutions;Stock g (tracked)",
                         "Decalactone gamma;;;;100 / 10;5", "Peach Lactone;;;;;", "Testolide X;;Foo Bar;Musks;;",
                         f"{eerste};;;;;", ";;;;;", "Vetiver Haïti;;;;;",
                         "Brand New Stuff;123-45-6;;;10;", "Ambroxan;;;;;"]) + "\n"
        stap("Import materials inventory from CSV…", reeks(ev("() => switchTab('M', null, null)"), kies("#impCsv", bestand("blad.csv", csv))), wacht=400)
        stap("Import materials inventory from CSV…", lambda p: p.select_option('#csvMap select[data-k="aliases"]', ""), wacht=50)
        stap("Import materials inventory from CSV…", lambda p: p.select_option('#csvMap select[data-k="aliases"]', "2"), wacht=50)
        stap("Import materials inventory from CSV…", klik("#dlgOk"), data=True, wacht=300)
        check(f"de melding van de CSV-import telt de namen die je al hebt zoals voorheen ({A.msgs[-1:]})",
              bool(A.msgs) and "skipped" in A.msgs[-1])
        stap("Import materials inventory from CSV…", ev("() => undo()"), data=True)

        een = {"type": "miformulas-import", "name": "Proefimport", "date": "2026-10-11", "lines": [
            {"material": eerste, "dilutionPct": 100, "weightG": 1.5}, {"material": "Peach Lactone", "dilutionPct": 10, "weightG": 0.5},
            {"material": naam, "weightG": 2}, {"material": "Volkomen Onbekend", "weightG": 0.25},
            {"material": "Ethanol", "weightG": 8, "solvent": True}, {"material": "Kapot", "weightG": "x"}]}
        stap("Import formula…", kies("#impFile", bestand("een.json", een)), wacht=300)
        een["lines"].pop()
        stap("Import formula…", kies("#impFile", bestand("een2.json", een)), wacht=300)
        stap("Import formula…", klik("#btnImpOk"), data=True, wacht=300)
        stap("Import formula…", ev("() => undo()"), data=True)
        veel = {"type": "miformulas-import", "formulas": [
            {"name": "Bulk A", "versions": [{"name": "eerste", "lines": een["lines"][:3]}, {"lines": een["lines"][1:]}]},
            {"name": STARTER["formulas"][0]["name"], "versions": [{"lines": [{"material": "Rose oxide", "weightG": 1}]}]}]}
        stap("Import formula… met meerdere formules", kies("#impFile", bestand("veel.json", veel)), wacht=300)
        stap("Import formula… met meerdere formules", klik("#btnImpOk"), data=True, wacht=300)
        stap("Import formula… met meerdere formules", ev("() => undo()"), data=True)
        fcsv = "\n".join(["Formula;Version;Material;Dilution %;Weight g", "Blad;1;" + eerste + ";100;2", "Blad;1;Decalactone gamma;10;0,5",
                          "Blad;2;" + eerste + ";100;2,5"]) + "\n"
        stap("Import formula… met een blad van formules", kies("#impFile", bestand("formules.csv", fcsv)), wacht=400)
        stap("Import formula… met een blad van formules", klik("#dlgOk"), wacht=300)
        stap("Import formula… met een blad van formules", klik("#btnImpCancel"), wacht=100)
        verslag()

        stap("alleen-lezen", ev("v => { LOCKED = true; VIEW = v; render(); }", laatste))
        stap("alleen-lezen", ev(VIEW, {"tab": "M", "id": M[5], "sub": None}))
        stap("alleen-lezen", ev("() => { LOCKED = false; render(); }"))
        for p in (R, A): p.set_viewport_size({"width": 430, "height": 932})
        stap("op een telefoon", ev(VIEW, laatste), wacht=100)
        stap("op een telefoon", ev(VIEW, {"tab": "M", "id": M[5], "sub": None}), wacht=100)
        stap("op een telefoon", ev(VIEW, {"tab": "M", "id": None, "sub": None}), wacht=100)
        verslag()
        check(f"geen fouten in de pagina ({R.errs[:1]}, {A.errs[:1]})", not R.errs and not A.errs)
        R.context.close(); A.context.close()

    # ======================= 2. dezelfde schermen op je eigen data =======================
    if REF_HTML is not None and os.path.exists(EIGEN):
        tekst = open(EIGEN, encoding="utf-8").read()
        R, A = opstarten(b, True), opstarten(b, False)
        laad = reeks(klik("#btnStarter"), lambda p: p.wait_for_timeout(1500),
                     ev("([t, pkg]) => { DATA = migrate(JSON.parse(t)); invalidateMats(); setMaterialList(normLibrary(pkg)); clampView(); setTabs(); render(); }", [tekst, LIB]))
        stap("je eigen data, geladen", laad, data=True, wacht=200, hash=True)
        F = A.evaluate("DATA.formulas.map(f => ({id: f.id, n: f.versions.length}))")
        for f in F:
            for i in range(f["n"]):
                stap("je eigen data: elke versie van elke formule", ev(VIEW, {"tab": "F", "id": f["id"], "sub": {"type": "v", "idx": i}}), hash=True)
            stap("je eigen data: de bench view van elke formule", ev(VIEW, {"tab": "F", "id": f["id"], "sub": {"type": "v", "idx": f["n"] - 1, "bench": True}}), hash=True)
        for m in A.evaluate("DATA.materials.map(m => m.id)"):
            stap("je eigen data: elk materiaal", ev(VIEW, {"tab": "M", "id": m, "sub": None}), hash=True)
        anders = []
        for q in ["a", "ros", "gamma decalactone", "haiti", "cœur", "C-11", "dpg", "ambr", ""]:
            stap("je eigen data: zoeken in Materials", reeks(ev(VIEW, {"tab": "M", "id": None, "sub": None}), vul("#searchBox", q)), hash=True)
            if R.evaluate(TREFFERS) != A.evaluate(TREFFERS): anders.append(q)
        check(f"je eigen data: zoeken vindt in beide bouwen dezelfde rijen, met ✎ en de library (anders: {anders})", not anders)
        stap("je eigen data: zoeken in Materials", None, data=True, hash=True)
        verslag()
        check(f"geen fouten in de pagina ({R.errs[:1]}, {A.errs[:1]})", not R.errs and not A.errs)
        R.context.close(); A.context.close()
    elif REF_HTML is not None:
        print("     (je eigen data staat niet naast public: alleen de starterset)")

    # ======================= 3. wat bouw 261011a zelf veranderde =======================
    c = b.new_context(viewport={"width": 1280, "height": 900}); p = c.new_page(); errs = []
    p.on("pageerror", lambda e: errs.append(str(e))); p.on("dialog", lambda d: d.accept())
    p.goto(URL); p.wait_for_timeout(800); p.click("#btnStarter"); p.wait_for_timeout(1500)
    iconen = p.evaluate("""() => [...document.querySelectorAll("link[rel=icon]")].map(l => l.getAttribute("sizes"))
        .concat(document.querySelectorAll("link[rel=apple-touch-icon]").length ? ["apple"] : [])""")
    check(f"geen icoon van 512 px meer, wel 32, 192 en de apple-touch-icon ({iconen})", iconen == ["32x32", "192x192", "apple"])
    check("ownFind, die niemand aanriep, is weg", p.evaluate("typeof ownFind") == "undefined")
    check("zonder library houdt de cache van listIndex", p.evaluate(
        "() => { const L = DATA.materialList; DATA.materialList = null; const a = listIndex(), b = listIndex(); DATA.materialList = L; return a === b; }"))
    check("listFind zoekt in de index van listIndex, niet meer door de hele library",
          p.evaluate("() => { const s = listFind.toString(); return s.includes('listIndex()') && !s.includes('.find('); }"))
    check("csvPlan bouwt geen eigen verzameling van alle namen in de library meer",
          p.evaluate("() => !csvPlan.toString().includes('listMaterials()')"))
    check("de CSV-import bouwt de naamindex niet meer per rij (één invalidateMats(), geen matByName)",
          p.evaluate("() => { const s = applyCsvImport.toString(); return !s.includes('matByName(') && (s.match(/invalidateMats\\(\\)/g) || []).length === 1; }"))
    c.close()
    c = b.new_context(viewport={"width": 1280, "height": 900}); p = c.new_page(); p.on("dialog", lambda d: d.accept())
    p.goto(URL); p.wait_for_timeout(800)
    p.evaluate("""async () => { await idb.set("dailyBak", {date: "2026-10-10", json: JSON.stringify({meta: {schema: 1},
        formulas: [{id: "f-old", name: "Months of work", category: "Uncategorised", versions: [{v: 1, date: "2026-10-10", lines: []}]}],
        materials: []})}); await idb.set("demoData", "{broken"); }""")
    p.reload(); p.wait_for_timeout(1500)
    p.click("#btnSnap"); p.wait_for_timeout(300)
    st = p.evaluate("() => [$('#saveState').textContent, $('#saveState').className]")
    check(f"na Restore daily snapshot houdt de lange melding de klasse wide, zoals elke lange melding ({st})",
          "Snapshot loaded" in st[0] and "wide" in st[1] and "dirty" in st[1])
    check(f"geen fouten in de pagina ({errs[:1]})", not errs)
    c.close()
    b.close()
    print(f"     ({round(time.time() - t0)} s)")

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
