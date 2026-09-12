"""Safari on macOS: Add to Dock hint, download warning, read-only file:// start screen, storage bar per
situation (tab, Dock app once), Import from Formulair on the Welcome page, importer in the Dock app (build 260909d).
Chromium plays Safari via the user agent; file access is removed with an init script.
Needs the local webserver (cd public && python -m http.server 8765)."""
import os, pathlib
from playwright.sync_api import sync_playwright
URL = "http://localhost:8765/"
INDEX = pathlib.Path(__file__).resolve().parents[2] / "index.html"
SAFARI_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15"
CHROME_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
NO_FS = "delete window.showOpenFilePicker; delete window.showSaveFilePicker;"
fouten = []
def check(m, c):
    print(("OK   " if c else "FOUT ") + m)
    if not c: fouten.append(m)

with sync_playwright() as p:
    b = p.chromium.launch()

    # 1. site in Safari: Add to Dock link and dialog
    ctx = b.new_context(user_agent=SAFARI_UA); ctx.add_init_script(NO_FS); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(700)
    check("Safari: install link visible with text Add to Dock…", pg.locator("#btnInstall").is_visible() and "Add to Dock" in pg.text_content("#btnInstall"))
    pg.click("#btnInstall"); pg.wait_for_timeout(300)
    dlg = pg.text_content("#dlg")
    check("Safari: dialog explains File › Add to Dock and the separate storage", "Add to Dock" in dlg and "storage of its own" in dlg)
    check("Safari: dialog says what to do after Add", "open miFormulas from the Dock" in dlg)
    pg.click("#dlgOk"); pg.wait_for_timeout(200)
    check("Safari: dialog closes", not pg.evaluate("document.getElementById('dlg').open"))
    check("Safari: hint on the start screen after OK", "Add to Dock" in pg.text_content("#landingHint") and "continue there" in pg.text_content("#landingHint"))
    check("Safari: Add to Dock… link stays on one line", pg.evaluate("(() => { const r = document.getElementById('btnInstall').getClientRects(); return r.length === 1; })()"))

    # 2. site in Safari: download link warns first, no download without confirmation
    downloads = []; pg.on("download", lambda d: downloads.append(d))
    pg.click("#btnDownload"); pg.wait_for_timeout(400)
    dlg = pg.text_content("#dlg")
    check("Safari: download shows a warning dialog", pg.evaluate("document.getElementById('dlg').open") and "Chrome or Edge" in dlg and "Add to Dock" in dlg)
    check("Safari: nothing downloaded yet", len(downloads) == 0)
    pg.click("#dlgCancel"); pg.wait_for_timeout(300)
    check("Safari: Cancel leaves the hint unchanged", "Downloads folder" not in pg.text_content("#landingHint"))
    with pg.expect_download() as dl:
        pg.click("#btnDownload"); pg.wait_for_timeout(300); pg.click("#dlgOk")
    check("Safari: Download anyway downloads miFormulas.html", dl.value.suggested_filename == "miFormulas.html")
    check("Safari: hint after download", "Downloads folder" in pg.text_content("#landingHint"))
    check("Safari: no JavaScript errors", not errs)
    # 2b. storage bar in a Safari tab: "browser's storage", stays between sessions, comes back every start
    pg.click("#btnStarter"); pg.wait_for_timeout(1200)
    bar = pg.text_content("#storageHintText")
    check("Safari tab: bar says the data stays between sessions and names Chrome or Edge", "stays there between sessions" in bar and "Chrome or Edge" in bar and not pg.evaluate("document.getElementById('storageHint').hidden"))
    check("Safari tab: no Save to a data file button", not pg.locator("#storageHintSave").is_visible())
    check("Safari tab: Welcome page offers Import from Formulair…", pg.locator("#btnImpFormulair").is_visible() and pg.get_attribute("#btnImpFormulair", "href") == "formulair-import.html")
    check("Safari tab: no Cowork mention on the Welcome page", "Cowork" not in pg.text_content("#content"))
    pg.click("#btnSave"); pg.wait_for_timeout(600)   # make sure the browser storage holds the data
    pg2 = ctx.new_page(); pg2.goto(URL); pg2.wait_for_timeout(1200)
    persisted = pg2.evaluate("navigator.storage.persisted()")
    check("Safari tab: data back in a new visit", pg2.locator("#btnImpFormulair").is_visible())
    check(f"Safari tab: bar shows again in a new visit unless persisted (persisted={persisted})", pg2.evaluate("document.getElementById('storageHint').hidden") == persisted)
    pg2.close()
    ctx.close()

    # 2c. Safari Dock app (standalone): "app's storage", shown once
    ctx = b.new_context(user_agent=SAFARI_UA); ctx.add_init_script(NO_FS + " Object.defineProperty(navigator, 'standalone', {get: () => true});")
    pg = ctx.new_page(); errs2 = []; pg.on("pageerror", lambda e: errs2.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(700)
    check("Dock app: no Add to Dock link when already installed", not pg.locator("#btnInstall").is_visible())
    pg.click("#btnStarter"); pg.wait_for_timeout(1200)
    bar = pg.text_content("#storageHintText")
    check("Dock app: bar says app's storage and Backup now and then", "this app's storage" in bar and "Backup" in bar and not pg.evaluate("document.getElementById('storageHint').hidden"))
    pg.wait_for_timeout(3500)   # first autosave asks for persistence and re-evaluates the bar
    check("Dock app: bar still there after the first save", not pg.evaluate("document.getElementById('storageHint').hidden"))
    pg.click("#btnSave"); pg.wait_for_timeout(600)
    pg.close(); pg = ctx.new_page(); errs2b = []; pg.on("pageerror", lambda e: errs2b.append(str(e)))   # a restart: new session, same storage
    pg.goto(URL); pg.wait_for_timeout(1200)
    check("Dock app: bar shown only once (hidden after a restart)", pg.evaluate("document.getElementById('storageHint').hidden"))
    check("Dock app: data still there after the restart", pg.locator("#btnImpFormulair").is_visible())
    check("Dock app: no JavaScript errors", not errs2)
    pg.click("#btnImpFormulair"); pg.wait_for_timeout(700)
    check("Dock app: importer opens with a Back link", pg.url.endswith("formulair-import.html") and pg.locator("#back").is_visible())
    check("Dock app: importer speaks of adding, not replacing", "adds your formulas" in pg.text_content("main") and "Replace" not in pg.text_content("main"))
    pg.click("#back"); pg.wait_for_timeout(1000)
    check("Dock app: Back returns to the app with the data", pg.locator("#btnImpFormulair").is_visible())
    ctx.close()

    # 3b. importer in Chrome: Back button, text speaks of adding
    ctx = b.new_context(user_agent=CHROME_UA); pg = ctx.new_page()
    pg.goto(URL + "formulair-import.html"); pg.wait_for_timeout(500)
    check("Chrome: importer has the Back button and speaks of adding", pg.locator("a.btn#back").is_visible() and "adds your formulas" in pg.text_content("main"))
    ctx.close()

    # 3. site in Chrome: no Add to Dock link, download goes straight through
    ctx = b.new_context(user_agent=CHROME_UA); pg = ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(700)
    check("Chrome: install link hidden until the browser offers it", not pg.locator("#btnInstall").is_visible())
    with pg.expect_download() as dl:
        pg.click("#btnDownload")
    check("Chrome: download without dialog", dl.value.suggested_filename == "miFormulas.html" and not pg.evaluate("document.getElementById('dlg').open"))
    # after installing: a message saying where the app went and that this tab can be closed
    pg.evaluate("window.dispatchEvent(new Event('appinstalled'))"); pg.wait_for_timeout(300)
    dlg = pg.text_content("#dlg")
    check("Chrome: a message after installing", pg.evaluate("document.getElementById('dlg').open") and "sits with your other apps" in dlg)
    check("Chrome: the message names the Home screen route and the shared data", "press and hold its icon" in dlg and "same data" in dlg)
    pg.click("#dlgOk"); pg.wait_for_timeout(200)
    check("Chrome: the same text stays on the start screen", "sits with your other apps" in pg.text_content("#landingHint"))
    ctx.close()

    # 4. file:// without file access (Safari, Firefox): read-only message with a link to the site
    ctx = b.new_context(user_agent=SAFARI_UA); ctx.add_init_script(NO_FS); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(INDEX.as_uri()); pg.wait_for_timeout(700)
    hint = pg.text_content("#landingHint")
    check("file://: read-only message names Chrome or Edge and Add to Dock", "read-only" in hint and "Chrome or Edge" in hint and "Add to Dock" in hint)
    check("file://: link to miformulas.com", pg.locator("#landingHint a[href='https://miformulas.com']").count() == 1)
    check("file://: no Add to Dock link on the start screen", not pg.locator("#btnInstall").is_visible())
    check("file://: no JavaScript errors", not errs)
    ctx.close(); b.close()

print("\n" + ("alles in orde" if not fouten else f"{len(fouten)} fout(en)"))
raise SystemExit(1 if fouten else 0)
