"""Bouw 261010b: Check for updates in Settings van de gedownloade app (file://, Chrome en Edge), en Download the app in
Settings op de site. De site wordt nagebootst met page.route (https://miformulas.com/index.html, met een andere
bouwstempel), het opslagvenster met een nep-handle die in localStorage bijhoudt wat er geschreven wordt.
Deel A en B via file:// (public\\index.html), deel C en D op de lokale webserver (poort 8765, zie README)."""
import json, os, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.abspath(os.path.join(HERE, "..", ".."))
APP = "file://" + os.path.join(PUB, "index.html")
SRC = open(os.path.join(PUB, "index.html"), encoding="utf-8").read()
STARTER = open(os.path.join(PUB, "data", "miformulas-starter.json"), encoding="utf-8").read()
BUILD = re.search(r'id="build"[^>]*>([^<]+)<', SRC).group(1).strip()
LATER = "991231z"   # later than any real build
NO_FS = "delete window.showOpenFilePicker; delete window.showSaveFilePicker;"   # Safari, Firefox


def site_html(stamp):
    """De app zoals de site ze zou geven, met een andere bouwstempel."""
    return re.sub(r'(id="build"[^>]*>)[^<]+(<)', lambda m: m.group(1) + stamp + m.group(2), SRC, count=1)


ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)


# nep-bestandstoegang: het databestand in localStorage 'fakefile', de app in 'fakeapp', elke schrijfbeurt in 'writelog'
FAKE_FS = """
  function FakeHandle(name){ this.name = name; this.kind = 'file'; this.__fake = true; }
  FakeHandle.prototype.queryPermission = async () => 'granted';
  FakeHandle.prototype.requestPermission = async () => 'granted';
  FakeHandle.prototype.getFile = async function(){ return new File([localStorage.getItem('fakefile') || '{}'], this.name); };
  FakeHandle.prototype.createWritable = async function(){
    const name = this.name, app = !name.endsWith('.json');
    if (app && localStorage.getItem('failwrite')) throw new DOMException('read-only', 'NoModificationAllowedError');
    return { write: async (s) => {
        const t = typeof s === 'string' ? s : new TextDecoder().decode(s);
        const log = JSON.parse(localStorage.getItem('writelog') || '[]'); log.push(name);
        localStorage.setItem('writelog', JSON.stringify(log));
        localStorage.setItem(app ? 'fakeapp' : 'fakefile', t);
      }, close: async () => {} };
  };
  const desc = Object.getOwnPropertyDescriptor(IDBRequest.prototype, 'result');
  Object.defineProperty(IDBRequest.prototype, 'result', { get(){ const v = desc.get.call(this); if (v && v.__fake) Object.setPrototypeOf(v, FakeHandle.prototype); return v; } });
  window.showOpenFilePicker = async () => { throw new Error('no picker in test'); };
  window.showSaveFilePicker = async (o) => {
    if (localStorage.getItem('cancelpicker')) throw new DOMException('cancel', 'AbortError');
    localStorage.setItem('pickeropts', JSON.stringify({suggestedName: o.suggestedName,
      startIn: o.startIn && typeof o.startIn === 'object' ? o.startIn.name : o.startIn, types: o.types}));
    return new FakeHandle(o.suggestedName);
  };
"""

SITE = {"body": site_html(BUILD), "abort": False}   # wat https://miformulas.com/index.html antwoordt


def serve_site(route):
    if SITE["abort"]:
        return route.abort()
    route.fulfill(status=200, content_type="text/html; charset=utf-8", body=SITE["body"],
                  headers={"Access-Control-Allow-Origin": "*"})


def serve_starter(route):
    route.fulfill(status=200, content_type="application/json", body=STARTER, headers={"Access-Control-Allow-Origin": "*"})


def dlg_open(page):
    return page.evaluate("document.querySelector('#dlg').open")


with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------- A. de gedownloade app in Chrome of Edge, met een databestand ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs, msgs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("https://miformulas.com/data/miformulas-starter.json", serve_starter)
    page.route("https://miformulas.com/index.html", serve_site)
    page.add_init_script(FAKE_FS)
    page.goto(APP); page.wait_for_timeout(900)
    check("protocol is file:", page.evaluate("location.protocol") == "file:")
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.click("#dlgOk"); page.wait_for_timeout(1500)          # Choose location…: het databestand
    check("de gedownloade app is opgestart met een databestand", page.evaluate("!!DATA && !!HANDLE"))
    page.evaluate("() => localStorage.removeItem('pickeropts')")

    def settings():
        page.click("#btnSettings"); page.wait_for_timeout(400)
        return page.locator("#setUpdate").count() == 1

    heeft = settings()
    check("Settings van de gedownloade app heeft Check for updates", heeft)
    check(f"met de bouw van deze kopie ernaast (build {BUILD})", f"this copy: build {BUILD}" in page.text_content("#dlg"))
    check("en geen Download the app", page.locator("#setDownload").count() == 0)
    page.click("#dlgCancel"); page.wait_for_timeout(200)

    def check_for_update():   # Settings, Check for updates: het antwoord is een melding of het venster Update miFormulas
        msgs.clear()
        if not settings():
            page.click("#dlgCancel"); page.wait_for_timeout(200)
            return False
        page.click("#setUpdate"); page.wait_for_timeout(900)
        return True

    if heeft:
        # 1. de site heeft dezelfde bouw
        SITE.update(body=site_html(BUILD))
        check_for_update()
        check(f"dezelfde bouw: up to date ({msgs[:1]})", any(f"This copy is up to date: build {BUILD}." in m for m in msgs))
        check("dezelfde bouw: geen venster", not dlg_open(page))
        check("dezelfde bouw: geen opslagvenster", page.evaluate("localStorage.getItem('pickeropts')") is None)

        # 2. de site antwoordt niet
        SITE.update(abort=True)
        check_for_update()
        check(f"geen verbinding: de app zegt het ({msgs[:1]})", any("could not be fetched" in m for m in msgs))
        check("geen verbinding: geen venster", not dlg_open(page))
        SITE.update(abort=False)

        # 3. wat terugkomt is de app niet: een aanmeldpagina van een netwerk, of een pagina met een stempel maar zonder
        # de titel van de app
        SITE.update(body="<!doctype html><title>Sign in to the network</title><p>Accept the terms to continue.</p>")
        check_for_update()
        check(f"een andere pagina: niets aangeboden ({msgs[:1]})", any("could not be fetched" in m for m in msgs) and not dlg_open(page))
        SITE.update(body=site_html(LATER).replace("<title>miFormulas</title>", "<title>Not found</title>", 1))
        check_for_update()
        check(f"een stempel zonder de titel van de app: niets aangeboden ({msgs[:1]})",
              any("could not be fetched" in m for m in msgs) and not dlg_open(page))

        # 4. de site heeft een nieuwere bouw: het venster
        SITE.update(body=site_html(LATER))
        check_for_update()
        tekst = page.text_content("#dlg") if dlg_open(page) else ""
        check("nieuwere bouw: het venster Update miFormulas", "Update miFormulas" in tekst)
        check(f"met beide stempels ({LATER}, {BUILD})", f"Build {LATER} is available; this copy is build {BUILD}." in tekst)
        check("met de naam van dit bestand", "choose this app file, index.html," in tekst)
        check("en dat het databestand blijft", "your data file is not touched" in tekst)
        check("de knop heet Update…", dlg_open(page) and page.locator("#dlgOk").inner_text().strip() == "Update…")

        # 4a. het opslagvenster geannuleerd: niets geschreven, niet herladen
        page.evaluate("() => { localStorage.setItem('cancelpicker', '1'); localStorage.removeItem('writelog'); window.__blijft = 1; }")
        if dlg_open(page):
            page.click("#dlgOk"); page.wait_for_timeout(800)
        check("geannuleerd: niets geschreven", page.evaluate("localStorage.getItem('writelog')") is None)
        check("geannuleerd: niet herladen", page.evaluate("window.__blijft") == 1)
        page.evaluate("() => localStorage.removeItem('cancelpicker')")

        # 4b. het bestand kan niet geschreven worden
        check_for_update()
        page.evaluate("() => { localStorage.setItem('failwrite', '1'); localStorage.removeItem('writelog'); }")
        if dlg_open(page):
            page.click("#dlgOk"); page.wait_for_timeout(800)
        check(f"niet schrijfbaar: de app zegt het ({msgs[-1:]})", any("could not be written" in m for m in msgs))
        check("niet schrijfbaar: de app staat er niet", page.evaluate("localStorage.getItem('fakeapp')") is None)
        check("niet schrijfbaar: niet herladen", page.evaluate("window.__blijft") == 1)
        page.evaluate("() => localStorage.removeItem('failwrite')")

        # 4c. Update…: eerst het opslagvenster, dan de laatste wijziging, dan de nieuwe app, en herladen
        check_for_update()
        page.evaluate("""() => { DATA.formulas[0].name += ' (bijgewerkt)'; markDirty();
            localStorage.removeItem('writelog'); localStorage.removeItem('pickeropts'); }""")
        check("er is een wijziging die nog niet bewaard is", page.evaluate("DIRTY"))
        if dlg_open(page):
            page.click("#dlgOk")
        page.wait_for_timeout(2500)   # schrijven en herladen
        log = page.evaluate("JSON.parse(localStorage.getItem('writelog') || '[]')")
        check(f"eerst het databestand, dan de app ({log})", log == ["miformulas-data.json", "index.html"])
        check("de laatste wijziging staat in het databestand", "(bijgewerkt)" in (page.evaluate("localStorage.getItem('fakefile')") or ""))
        check("de app is byte voor byte die van de site", page.evaluate("localStorage.getItem('fakeapp')") == site_html(LATER))
        opts = page.evaluate("JSON.parse(localStorage.getItem('pickeropts') || 'null')") or {}
        check(f"het opslagvenster stelt de naam van dit bestand voor ({opts.get('suggestedName')})", opts.get("suggestedName") == "index.html")
        check(f"en begint in de map van het databestand ({opts.get('startIn')})", opts.get("startIn") == "miformulas-data.json")
        check("en vraagt een html-bestand", (opts.get("types") or [{}])[0].get("accept") == {"text/html": [".html"]})
        check("de app herlaadt", page.evaluate("window.__blijft") is None)
        check(f"na het herladen: dit venster opende een ander bestand ({msgs[-1:]})",
              any(f"build {LATER}, was saved" in m and f"another file: build {BUILD}" in m for m in msgs))
        check("na het herladen weer aan het werk, met de laatste wijziging",
              page.evaluate("!!DATA && DATA.formulas[0].name.endsWith('(bijgewerkt)')"))

        # 5. na een geslaagde update: dit venster opende het vervangen bestand
        msgs.clear()
        page.evaluate("b => sessionStorage.setItem('mfUpdatedTo', b)", BUILD)
        page.reload(); page.wait_for_timeout(1500)
        check(f"na een geslaagde update zegt de app welke bouw ze is ({msgs[:1]})", f"miFormulas is updated to build {BUILD}." in msgs)
        msgs.clear()
        page.reload(); page.wait_for_timeout(1500)
        check("die melding komt maar één keer", not any("updated to build" in m for m in msgs))
    check(f"geen paginafouten in de gedownloade app ({errs[:2]})", not errs)
    ctx.close()

    # ---------------- A2. de gedownloade app op het startscherm, nog zonder databestand ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs2, msgs2 = [], []
    page.on("pageerror", lambda e: errs2.append(str(e)))
    page.on("dialog", lambda d: (msgs2.append(d.message), d.accept()))
    page.route("https://miformulas.com/index.html", serve_site)
    page.add_init_script(FAKE_FS)
    page.goto(APP); page.wait_for_timeout(900)
    page.click("#btnSettingsLanding"); page.wait_for_timeout(400)
    heeft = page.locator("#setUpdate").count() == 1
    check("op het startscherm, nog zonder databestand, heeft Settings Check for updates ook", heeft)
    if heeft:
        SITE.update(body=site_html(LATER))
        page.click("#setUpdate"); page.wait_for_timeout(900)
        if dlg_open(page):
            page.click("#dlgOk")
        page.wait_for_timeout(2000)
        opts = page.evaluate("JSON.parse(localStorage.getItem('pickeropts') || 'null')") or {}
        check(f"zonder databestand begint het opslagvenster in Documents ({opts.get('startIn')})", opts.get("startIn") == "documents")
        check("en de app is geschreven", page.evaluate("localStorage.getItem('fakeapp')") == site_html(LATER))
        check(f"en na het herladen de melding ({msgs2[-1:]})", any(f"build {LATER}, was saved" in m for m in msgs2))
        check("en weer het startscherm", page.locator("#landing").is_visible())
    check(f"geen paginafouten op het startscherm ({errs2[:2]})", not errs2)
    ctx.close()

    # ---------------- B. de gedownloade app in een browser zonder bestandstoegang (Safari, Firefox) ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    page.add_init_script(NO_FS)
    page.on("dialog", lambda d: d.accept())
    page.goto(APP); page.wait_for_timeout(900)
    check("zonder bestandstoegang is de gedownloade app alleen-lezen", page.evaluate("FALLBACK"))
    page.click("#btnSettingsLanding"); page.wait_for_timeout(400)
    check("en heeft ze geen Check for updates: ze kan de nieuwe versie niet schrijven", page.locator("#setUpdate").count() == 0)
    ctx.close()

    # ---------------- C. op de site in Chrome of Edge ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs3 = []
    page.on("pageerror", lambda e: errs3.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    with page.expect_download() as dl:
        page.click("#btnDownload")
    check("startscherm: Download the app geeft miFormulas.html, zoals voordien", dl.value.suggested_filename == "miFormulas.html")
    check("startscherm: de hint zegt waar het bestand staat", "Downloads folder" in page.text_content("#landingHint"))
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    # de browser biedt de installatie aan, zoals Chrome en Edge op de site
    page.evaluate("window.dispatchEvent(Object.assign(new Event('beforeinstallprompt'), {preventDefault(){}, prompt: async()=>{}}))")
    page.click("#btnSettings"); page.wait_for_timeout(400)
    heeft = page.locator("#setDownload").count() == 1
    check("Settings op de site heeft Download the app", heeft)
    check("en geen Check for updates: de site werkt zelf bij", page.locator("#setUpdate").count() == 0)
    ids = page.evaluate("() => [...document.querySelectorAll('#dlg button[id]')].map(b => b.id)")
    check("Install as an app staat vlak boven Download the app",
          "setInstall" in ids and "setDownload" in ids and ids.index("setInstall") + 1 == ids.index("setDownload"))
    uitleg = page.evaluate("""() => [...document.querySelectorAll('#dlg button[id]')].filter(b => ['setInstall', 'setDownload'].includes(b.id))
        .map(b => b.id + ': ' + (b.nextElementSibling ? b.nextElementSibling.textContent : ''))""")
    check(f"Install as an app: eigen venster, draait van de site en werkt zelf bij ({uitleg[:1]})",
          "setInstall: with its own window and icon; it runs from this site and updates by itself" in uitleg)
    check(f"Download the app: een bestand, werkt offline, je werkt het zelf bij ({uitleg[1:2]})",
          "setDownload: as a file on your own computer; it works offline, and you update it yourself" in uitleg)
    if heeft:
        with page.expect_download() as dl:
            page.click("#setDownload")
        d = dl.value
        check("Settings: het bestand heet miFormulas.html", d.suggested_filename == "miFormulas.html")
        check("Settings: het is de app van de site, byte voor byte", open(d.path(), encoding="utf-8").read() == SRC)
        hint = page.text_content("#setDownloadHint")
        check("Settings: de hint zegt waar het bestand staat en wat ermee", "Downloads folder" in hint and "in place of the copy you have" in hint)
        check("Settings: en hoe de data van de site meegaat", "click Backup and open that file in the downloaded app" in hint)
        check("Settings blijft open", dlg_open(page))
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.evaluate("() => { window.__r = REMOTE; REMOTE = true; }")     # met een server, zoals op het startscherm: geen link
    page.click("#btnSettings"); page.wait_for_timeout(400)
    check("met een server heeft Settings geen Download the app", page.locator("#setDownload").count() == 0)
    page.click("#dlgCancel"); page.wait_for_timeout(200)
    page.evaluate("() => { REMOTE = window.__r; }")
    check(f"geen paginafouten op de site ({errs3[:2]})", not errs3)
    ctx.close()

    # ---------------- D. op de site zonder bestandstoegang (Safari, Firefox): eerst het venster ----------------
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    page = ctx.new_page()
    errs4 = []
    page.on("pageerror", lambda e: errs4.append(str(e)))
    page.add_init_script(NO_FS)
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnDownload"); page.wait_for_timeout(300)
    tekst = page.text_content("#dlg") if dlg_open(page) else ""
    check("startscherm zonder bestandstoegang: eerst het venster", "needs Chrome or Edge" in tekst and "Download anyway" in tekst)
    if dlg_open(page):
        with page.expect_download() as dl:
            page.click("#dlgOk")
        check("Download anyway geeft miFormulas.html", dl.value.suggested_filename == "miFormulas.html")
    check("en de hint op het startscherm", "Downloads folder" in page.text_content("#landingHint"))
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    heeft = page.locator("#setDownload").count() == 1
    check("Settings zonder bestandstoegang heeft Download the app ook", heeft)
    if heeft:
        page.click("#setDownload"); page.wait_for_timeout(300)
        tekst = page.text_content("#dlg") if dlg_open(page) else ""
        check("en toont eerst hetzelfde venster", "needs Chrome or Edge" in tekst and "Download anyway" in tekst)
        if dlg_open(page):
            with page.expect_download() as dl:
                page.click("#dlgOk")
            check("en dan de download", dl.value.suggested_filename == "miFormulas.html")
    check(f"geen paginafouten zonder bestandstoegang ({errs4[:2]})", not errs4)
    ctx.close()

    print("\n%d OK, %d FAIL" % (ok, fail))
    b.close()
    raise SystemExit(1 if fail else 0)
