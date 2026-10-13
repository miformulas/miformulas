"""Bouw 261013a: ronde 1 van de audit v3 (op bouw 261012a). Faalt op 261012a.
A1  Import materials inventory from CSV… cureert niet: elke rij met een naam wordt een materiaal, ook dezelfde naam drie
    keer in het blad (hetzelfde materiaal uit drie winkels) en een naam die de alternatieve naam is van een eerdere rij,
    van een eerder materiaal of van wat de library aan een eerdere rij hing. Alleen de eigen naam van een materiaal dat er
    al was, wordt overgeslagen. Het venster belooft wat er komt, de melding noemt de namen die nu bij meer dan één
    materiaal horen, één Undo neemt alles terug, en een formuleregel landt op het materiaal met die eigen naam. Staat
    miformulas-data.json naast public (de proef), dan ook de rondgang van die inventaris (Export all materials (Excel) en
    terug in een lege app), zonder en met de library (de gepubliceerde als die naast public staat).
B1  Het opslagvenster van Update…, Save to a data file…, de starterset van de gedownloade app en Backup biedt "All
    files" niet aan, en een bestand met de verkeerde extensie wordt niet beschreven (nep-bestandstoegang).
B2  ✎ op de bestellijst: Escape na typen laat de link zoals ze was, zonder Undo-stap.
B3  Download the app niet op een telefoon (Chrome op Android, Chrome en Safari op een iPhone), wel op een computer.
Vereist de lokale webserver op poort 8765 (zie README); B1 ook via file:// (public\\index.html)."""
import json, os, re, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
SRC = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
EIGEN = os.path.join(PUB, "..", "miformulas-data.json")
GEPUB = os.path.join(PUB, "..", "miformulas-materials.json")
LATER = "991231z"
ANDROID_UA = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36"
IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.6 "
             "Mobile/15E148 Safari/604.1")
CRIOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/129.0.6668.69 "
            "Mobile/15E148 Safari/604.1")
NO_FS = "delete window.showOpenFilePicker; delete window.showSaveFilePicker;"
TMP = tempfile.mkdtemp()

ok = fail = 0
def check(naam, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + naam)

def schrijf(naam, tekst):
    p = os.path.join(TMP, naam); open(p, "w", encoding="utf-8", newline="").write(tekst); return p

def pagina(b, url=URL, **kw):
    ctx = b.new_context(viewport=kw.pop("viewport", {"width": 1400, "height": 900}), accept_downloads=True, **kw)
    p = ctx.new_page(); p.msgs = []; p.errs = []
    p.on("dialog", lambda d: (p.msgs.append(d.message), d.accept()))
    p.on("pageerror", lambda e: p.errs.append(str(e)))
    return ctx, p

def namen(p):
    return p.evaluate("DATA.materials.map(m => m.name)")

def csv_in(p, pad):
    p.set_input_files("#impCsv", pad); p.wait_for_timeout(900)
    return p.text_content("#csvCount")

def importeer(p, wacht=1200):
    if p.locator("#dlgOk").is_disabled():   # niets te importeren (de vorige bouw): het venster dicht, verder
        p.click("#dlgCancel"); p.wait_for_timeout(200); return ""
    p.msgs.clear(); p.click("#dlgOk"); p.wait_for_timeout(wacht)
    return p.msgs[-1] if p.msgs else ""

def site_html(stamp):
    return re.sub(r'(id="build"[^>]*>)[^<]+(<)', lambda m: m.group(1) + stamp + m.group(2), SRC, count=1)

# nep-bestandstoegang (zoals update-knop.py): het databestand in localStorage 'fakefile', de app in 'fakeapp', elke
# schrijfbeurt in 'writelog', de opties van het laatste opslagvenster in 'pickeropts'; 'savename' is de naam die je kiest
FAKE_FS = """
  function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
  FakeHandle.prototype.queryPermission = async function(){ return 'granted'; };
  FakeHandle.prototype.requestPermission = async function(){ return 'granted'; };
  FakeHandle.prototype.isSameEntry = async function(o){ return !!o && o.name === this.name; };
  FakeHandle.prototype.getFile = async function(){ return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
  FakeHandle.prototype.createWritable = async function(){
    const name = this.name, app = !name.endsWith('.json');
    return { write: async (s) => {
        const t = typeof s === 'string' ? s : new TextDecoder().decode(s);
        const log = JSON.parse(localStorage.getItem('writelog') || '[]'); log.push(name);
        localStorage.setItem('writelog', JSON.stringify(log));
        localStorage.setItem(app ? 'fakeapp' : 'fakefile', t);
      }, close: async () => {} };
  };
  const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
  Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
  window.showOpenFilePicker = async () => [new FakeHandle(localStorage.getItem('openname') || 'miformulas-data.json')];
  window.showSaveFilePicker = async (o) => {
    localStorage.setItem('pickeropts', JSON.stringify({suggestedName: o.suggestedName, excludeAcceptAllTypes: !!o.excludeAcceptAllTypes}));
    return new FakeHandle(localStorage.getItem('savename') || o.suggestedName);
  };
"""
def opgeslagen(p):
    return p.evaluate("JSON.parse(localStorage.getItem('writelog') || '[]')")
def venster(p):
    return p.evaluate("JSON.parse(localStorage.getItem('pickeropts') || '{}')")
def kies(p, naam):
    p.evaluate("n => { localStorage.setItem('savename', n); localStorage.removeItem('writelog'); localStorage.removeItem('pickeropts'); }", naam)


with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ================= A1. Import materials inventory from CSV… cureert niet =================
    ctx, p = pagina(b); p.goto(URL); p.wait_for_timeout(700); p.click("#btnEmpty"); p.wait_for_timeout(1000)
    blad = schrijf("drie-winkels.csv",
        "Name;Alternative names;Supplier\r\n"
        "Ethyl rosate;ethyl safranate;\r\nEthyl safranate;;\r\nFuraneol in DPG;strawberry furanone;\r\nStrawberry furanone;;\r\n"
        "Iso E Super;;Shop A\r\nIso E Super;;Shop B\r\niso e super;;Shop C\r\n;;zonder naam\r\n")
    tel = csv_in(p, blad)
    check(f"A1 het venster belooft zeven materialen, slaat niets over en telt de rij zonder naam ({tel.strip()!r})",
          "7 material(s) will be created" in tel and "skipped" not in tel and "1 row(s) without a name" in tel)
    check("A1 de knop telt mee", p.text_content("#dlgOk").strip() == "Import 7")
    msg = importeer(p)
    n = namen(p)
    check(f"A1 alle zeven komen binnen, ook de naam die een eerdere rij als alternatieve naam draagt ({len(n)}: {n})",
          len(n) == 7 and "Ethyl safranate" in n and "Strawberry furanone" in n)
    lev = p.evaluate("DATA.materials.filter(m => normName(m.name) === 'iso e super').map(m => m.supplier).sort()")
    check(f"A1 hetzelfde materiaal uit drie winkels blijft drie materialen ({lev})", lev == ["Shop A", "Shop B", "Shop C"])
    check(f"A1 de melding: zeven, niets overgeslagen, en de naam die nu bij meer dan één materiaal hoort ({msg!r})",
          msg.startswith("7 material(s) imported") and "skipped" not in msg and "earlier row" not in msg
          and "1 name(s) now belong to more than one of your materials: " in msg and "iso e super" in msg.lower()
          and "Ethyl safranate" not in msg)
    # een formuleregel landt op het materiaal met die eigen naam, niet op het materiaal dat de naam als alias draagt
    imp = {"type": "miformulas-import", "name": "Gevolg", "lines": [
        {"material": "Strawberry furanone", "dilutionPct": 100, "weightG": 1}, {"material": "Ethyl safranate", "dilutionPct": 100, "weightG": 1}]}
    p.set_input_files("#impFile", schrijf("gevolg.json", json.dumps(imp))); p.wait_for_timeout(800)
    rijen = p.evaluate("() => [...document.querySelectorAll('#content tbody tr')].map(r => r.innerText.replace(/\\s+/g, ' '))")
    check(f"A1 de formuleregels landen op hun eigen materiaal ({rijen})",
          len(rijen) == 2 and not any("←" in r for r in rijen) and all("matched" in r for r in rijen))
    p.click("#btnImpCancel"); p.wait_for_timeout(300)
    # hetzelfde blad nog eens: elke rij heeft nu de eigen naam van een materiaal
    tel = csv_in(p, blad)
    check(f"A1 een tweede keer: alles overgeslagen, de knop uit ({tel.strip()!r})",
          "0 material(s) will be created" in tel and "7 skipped: name already in your inventory" in tel and p.locator("#dlgOk").is_disabled())
    p.click("#dlgCancel"); p.wait_for_timeout(200)
    # een alternatieve naam van een materiaal dat je al had, telt niet; de eigen naam wel, ook in andere hoofdletters
    tel = csv_in(p, schrijf("hoofdletters.csv", "Name\r\nSafranate test\r\nFURANEOL IN DPG\r\n"))
    check(f"A1 de eigen naam in andere hoofdletters is overgeslagen, de rest komt ({tel.strip()!r})",
          "1 material(s) will be created" in tel and "1 skipped" in tel)
    p.click("#dlgCancel"); p.wait_for_timeout(200)
    p.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Ethyl safranate'); DATA.materials = DATA.materials.filter(x => x !== m); invalidateMats(); render(); }")
    tel = csv_in(p, schrijf("alias2.csv", "Name\r\nEthyl safranate\r\n"))
    check(f"A1 een naam die alleen als alternatieve naam van een eigen materiaal bestaat, wordt een materiaal ({tel.strip()!r})",
          "1 material(s) will be created" in tel and "skipped" not in tel)
    importeer(p)
    check("A1 en komt binnen", "Ethyl safranate" in namen(p))
    # één Undo neemt een hele import terug
    voor = p.evaluate("DATA.materials.length")
    p.keyboard.press("Control+z"); p.wait_for_timeout(500)
    check(f"A1 één Undo neemt de import terug ({voor} → {p.evaluate('DATA.materials.length')})", p.evaluate("DATA.materials.length") == voor - 1)
    check(f"A1 geen paginafouten ({p.errs[:2]})", not p.errs)
    ctx.close()

    # de namen die de library aan een rij hangt, slokken geen volgende rij meer op
    ctx, p = pagina(b); p.goto(URL); p.wait_for_timeout(700); p.click("#btnEmpty"); p.wait_for_timeout(1000)
    p.evaluate("""() => { setMaterialList(normLibrary({type: "miformulas-materials", name: "Proeflibrary", version: "1",
        materials: [{name: "Bourgeonal", aliases: ["Ligeonal"], cas: "18127-01-0", category: "Floral", pyramid: 2},
                    {name: "Karmawood", aliases: ["Norlimbanol"], category: "Woody", pyramid: 4}]})); render(); }""")
    tel = csv_in(p, schrijf("library.csv", "Name;Supplier\r\nBourgeonal;A\r\nLigeonal;B\r\nKarmawood;C\r\nNorlimbanol;D\r\n"))
    check(f"A1 met de library: vier beloofd, de library kent ze alle vier ({tel.strip()!r})",
          "4 material(s) will be created" in tel and "knows 4 of them" in tel and "skipped" not in tel)
    importeer(p)
    n = sorted(namen(p))
    check(f"A1 en alle vier komen binnen ({n})", n == ["Bourgeonal", "Karmawood", "Ligeonal", "Norlimbanol"])
    lig = p.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Ligeonal'); return m && {cas: m.cas, cat: m.category, sup: m.supplier}; }")
    check(f"A1 de library vult de feiten aan, ook op de rij met de alternatieve naam ({lig})",
          lig == {"cas": "18127-01-0", "cat": "Floral", "sup": "B"})
    ctx.close()

    # de rondgang van de eigen inventaris (alleen in de proef, met miformulas-data.json naast public)
    if os.path.exists(EIGEN):
        eigen = open(EIGEN, encoding="utf-8").read()
        lib = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else None
        ctx, p = pagina(b); p.goto(URL); p.wait_for_timeout(700); p.click("#btnStarter"); p.wait_for_timeout(1200)
        p.evaluate("([t, pkg]) => { DATA = migrate(JSON.parse(t)); invalidateMats(); if (pkg) setMaterialList(normLibrary(pkg)); render(); }", [eigen, lib])
        p.wait_for_timeout(500)
        bron = sorted(namen(p))
        p.click("#btnIO"); p.wait_for_timeout(400)
        with p.expect_download() as dl:
            p.click("#btnExpM")
        pad = os.path.join(TMP, "inventaris.csv"); dl.value.save_as(pad)
        ctx.close()
        for met in ([False, True] if lib else [False]):
            ctx, p = pagina(b); p.goto(URL); p.wait_for_timeout(700); p.click("#btnEmpty"); p.wait_for_timeout(1000)
            if met:
                p.evaluate("pkg => { setMaterialList(normLibrary(pkg)); render(); }", lib); p.wait_for_timeout(300)
            tel = csv_in(p, pad)
            importeer(p, 3000)
            n = sorted(namen(p))
            wat = "met de library" if met else "zonder library"
            check(f"A1 de rondgang van de eigen inventaris {wat}: {len(bron)} beloofd, {len(n)} binnen, dezelfde namen ({tel.strip()[:60]!r})",
                  f"{len(bron)} material(s) will be created" in tel and n == bron)
            ctx.close()
    else:
        print("     (geen miformulas-data.json naast public: de rondgang van de eigen inventaris overgeslagen)")

    # ================= B1. het opslagvenster beschrijft geen bestand met de verkeerde extensie =================
    def site(route):
        route.fulfill(status=200, content_type="text/html; charset=utf-8", body=site_html(LATER), headers={"Access-Control-Allow-Origin": "*"})
    def starter(route):
        route.fulfill(status=200, content_type="application/json", body=STARTER, headers={"Access-Control-Allow-Origin": "*"})

    # (a) Update… in de gedownloade app, met het databestand gekozen in plaats van de app
    ctx, p = pagina(b, viewport={"width": 1280, "height": 900})
    p.route("https://miformulas.com/data/miformulas-starter.json", starter)
    p.route("https://miformulas.com/index.html", site)
    p.add_init_script(FAKE_FS)
    p.goto(APP); p.wait_for_timeout(900)
    p.click("#btnStarter"); p.wait_for_timeout(1200); p.click("#dlgOk"); p.wait_for_timeout(1500)
    check("B1 de gedownloade app werkt met een databestand", p.evaluate("!!DATA && !!HANDLE"))
    data_voor = p.evaluate("localStorage.getItem('fakefile')")
    kies(p, "miformulas-data.json")
    p.click("#btnSettings"); p.wait_for_timeout(300); p.click("#setUpdate"); p.wait_for_timeout(900)
    p.msgs.clear(); p.click("#dlgOk"); p.wait_for_timeout(1500)
    check(f"B1 Update…: het venster biedt All files niet aan ({venster(p)})", venster(p).get("excludeAcceptAllTypes") is True)
    check(f"B1 Update… met het databestand gekozen: niets geschreven ({opgeslagen(p)})", opgeslagen(p) == [])
    check("B1 het databestand is nog de data", p.evaluate("localStorage.getItem('fakefile')") == data_voor and p.evaluate("!!DATA"))
    check(f"B1 de melding zegt het ({p.msgs[-1:]})", any("is not an app file" in m and "nothing was written" in m for m in p.msgs))
    # de app zelf kiezen werkt nog (op de vorige bouw staat de app dan al op het startscherm, zonder data)
    kies(p, "miFormulas.html")
    if p.evaluate("!!DATA"):
        p.click("#btnSettings"); p.wait_for_timeout(300); p.click("#setUpdate"); p.wait_for_timeout(900)
        p.click("#dlgOk"); p.wait_for_timeout(2500)
    check(f"B1 Update… met de app gekozen schrijft de app ({opgeslagen(p)})", opgeslagen(p)[-1:] == ["miFormulas.html"])
    ctx.close()

    # (b) Backup in de gedownloade app, met de app gekozen
    ctx, p = pagina(b, viewport={"width": 1280, "height": 900})
    p.route("https://miformulas.com/data/miformulas-starter.json", starter)
    p.add_init_script(FAKE_FS)
    p.goto(APP); p.wait_for_timeout(900)
    p.click("#btnStarter"); p.wait_for_timeout(1200); p.click("#dlgOk"); p.wait_for_timeout(1500)
    kies(p, "miFormulas.html"); p.msgs.clear()
    p.click("#btnBackup"); p.wait_for_timeout(800)
    check(f"B1 Backup: het venster biedt All files niet aan ({venster(p)})", venster(p).get("excludeAcceptAllTypes") is True)
    check(f"B1 Backup met de app gekozen: niets geschreven ({opgeslagen(p)}, {p.msgs[-1:]})",
          opgeslagen(p) == [] and any("is not a data file" in m for m in p.msgs))
    kies(p, "261013_1200_miformulas-data.json")
    p.click("#btnBackup"); p.wait_for_timeout(800)
    check(f"B1 Backup met een .json schrijft ({opgeslagen(p)})", opgeslagen(p) == ["261013_1200_miformulas-data.json"])
    ctx.close()

    # (c) de starterset van de gedownloade app, met de app gekozen als databestand
    ctx, p = pagina(b, viewport={"width": 1280, "height": 900})
    p.route("https://miformulas.com/data/miformulas-starter.json", starter)
    p.add_init_script(FAKE_FS)
    p.goto(APP); p.wait_for_timeout(900)
    kies(p, "miFormulas.html"); p.msgs.clear()
    p.click("#btnStarter"); p.wait_for_timeout(1200); p.click("#dlgOk"); p.wait_for_timeout(1500)
    check(f"B1 starterset: het venster biedt All files niet aan ({venster(p)})", venster(p).get("excludeAcceptAllTypes") is True)
    check(f"B1 starterset met de app gekozen: niets geschreven, geen data, de uitleg op het startscherm ({opgeslagen(p)}, {p.msgs[-1:]})",
          opgeslagen(p) == [] and p.evaluate("!DATA && !HANDLE") and any("is not a data file" in m for m in p.msgs)
          and "No data file was created" in p.text_content("#landingHint"))
    ctx.close()

    # (d) Save to a data file… op de site, met de app gekozen
    ctx, p = pagina(b, viewport={"width": 1280, "height": 900})
    p.add_init_script(FAKE_FS)
    p.goto(URL); p.wait_for_timeout(700); p.click("#btnStarter"); p.wait_for_timeout(1200)
    kies(p, "miFormulas.html"); p.msgs.clear()
    p.click("#storageHintSave"); p.wait_for_timeout(300); p.click("#dlgOk"); p.wait_for_timeout(1500)
    check(f"B1 Save to a data file…: het venster biedt All files niet aan ({venster(p)})", venster(p).get("excludeAcceptAllTypes") is True)
    check(f"B1 Save to a data file… met de app gekozen: niets geschreven, de data blijft in de browser ({opgeslagen(p)}, {p.msgs[-1:]})",
          opgeslagen(p) == [] and p.evaluate("!HANDLE && DEMO") and any("is not a data file" in m for m in p.msgs))
    kies(p, "miformulas-data.json")
    p.click("#btnSettings"); p.wait_for_timeout(300)
    if p.locator("#setToFile").count():   # op de vorige bouw is de app al het databestand geworden
        p.click("#setToFile"); p.wait_for_timeout(300); p.click("#dlgOk"); p.wait_for_timeout(1500)
    check(f"B1 met miformulas-data.json gekozen wordt de data het bestand ({opgeslagen(p)})",
          opgeslagen(p)[:1] == ["miformulas-data.json"] and p.evaluate("HANDLE && HANDLE.name") == "miformulas-data.json")
    ctx.close()

    # ================= B2. ✎ op de bestellijst: Escape annuleert =================
    ctx, p = pagina(b); p.goto(URL); p.wait_for_timeout(700); p.click("#btnStarter"); p.wait_for_timeout(1200)
    p.evaluate("DATA.orderList.push({id: 'o-t', name: 'Proefstof', url: 'www.hekserij.nl/product/123', added: ''}); switchTab('T', null, null)")
    p.wait_for_timeout(200)
    i = p.evaluate("DATA.orderList.findIndex(o => o.id === 'o-t')")
    n0 = p.evaluate("UNDO.length")
    p.click(f"[data-oedit='{i}']"); p.wait_for_timeout(150)
    p.keyboard.type("gewijzigd"); p.keyboard.press("Escape"); p.wait_for_timeout(300)
    url = p.evaluate("DATA.orderList.find(o => o.id === 'o-t').url")
    check(f"B2 Escape na typen laat de link zoals ze was ({url!r})", url == "www.hekserij.nl/product/123")
    check("B2 zonder Undo-stap", p.evaluate("UNDO.length") == n0)
    check("B2 de link staat weer als link", p.evaluate(f"!!document.querySelector(\"[data-oedit='{i}']\")") and "hekserij.nl" in p.text_content("#content"))
    p.click(f"[data-oedit='{i}']"); p.wait_for_timeout(150)
    p.keyboard.press("Control+a"); p.keyboard.type("example.com/x"); p.keyboard.press("Tab"); p.wait_for_timeout(300)
    check(f"B2 Tab bewaart wel ({p.evaluate('DATA.orderList.find(o => o.id === \"o-t\").url')!r})",
          p.evaluate("DATA.orderList.find(o => o.id === 'o-t').url") == "example.com/x")
    check(f"B2 geen paginafouten ({p.errs[:2]})", not p.errs)
    ctx.close()

    # ================= B3. Download the app niet op een telefoon =================
    def download_te_zien(ua=None, telefoon=False, zonder_fs=False):
        kw = {"user_agent": ua} if ua else {}
        if telefoon:
            kw.update(viewport={"width": 430, "height": 932}, is_mobile=True, has_touch=True)
        ctx, p = pagina(b, **kw)
        if zonder_fs:
            p.add_init_script(NO_FS)
        p.goto(URL); p.wait_for_timeout(700)
        start = p.locator("#btnDownload").is_visible()
        p.click("#btnStarter"); p.wait_for_timeout(1200)
        p.click("#btnSettings"); p.wait_for_timeout(300)
        inst = p.locator("#setDownload").count() > 0
        ctx.close()
        return start, inst
    for naam, ua, zonder in (("Chrome op Android", ANDROID_UA, True), ("Chrome op een iPhone", CRIOS_UA, True),
                             ("Safari op een iPhone", IPHONE_UA, True)):
        start, inst = download_te_zien(ua, telefoon=True, zonder_fs=zonder)
        check(f"B3 {naam}: geen Download the app op het startscherm en in Settings ({start}, {inst})", not start and not inst)
    start, inst = download_te_zien()
    check(f"B3 Chrome op een computer: Download the app op het startscherm en in Settings ({start}, {inst})", start and inst)

    b.close()
print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
