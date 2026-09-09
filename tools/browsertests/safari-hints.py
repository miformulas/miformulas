"""Safari on macOS: Add to Dock hint, download warning, read-only file:// start screen (build 260909).
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
    pg.click("#dlgOk"); pg.wait_for_timeout(200)
    check("Safari: dialog closes", not pg.evaluate("document.getElementById('dlg').open"))

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
    ctx.close()

    # 3. site in Chrome: no Add to Dock link, download goes straight through
    ctx = b.new_context(user_agent=CHROME_UA); pg = ctx.new_page()
    pg.goto(URL); pg.wait_for_timeout(700)
    check("Chrome: install link hidden until the browser offers it", not pg.locator("#btnInstall").is_visible())
    with pg.expect_download() as dl:
        pg.click("#btnDownload")
    check("Chrome: download without dialog", dl.value.suggested_filename == "miFormulas.html" and not pg.evaluate("document.getElementById('dlg').open"))
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
