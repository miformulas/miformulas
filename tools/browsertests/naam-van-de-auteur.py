"""No window of the app carries the name of the author (build 261007a): the start screen, Welcome, the Import & export
window, Settings (with the published materials library loaded, when a copy of it sits next to public/, as for
screenshots.py), the Help with all its sections, and the online manual. Section 23 still says that the name miFormulas
is reserved and that every copy carries the attribution of the file NOTICE; NOTICE and README keep the name, as the
attribution itself. Needs the local webserver (cd public && python -m http.server 8765). The script ends with exit
code 1 when a check fails."""
import os, re, sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
PUB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LIBRARY = os.path.join(PUB, "..", "miformulas-materials.json")
NAME = re.compile(r"Mathieu|Isenbaert", re.I)
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def found(text):
    return sorted({m.group(0) for m in NAME.finditer(text)})

with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 1000})
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(700)
    t = page.inner_text("body")
    check(f"the start screen does not name the author {found(t)}", not found(t))
    page.locator("#btnStarter").click(); page.wait_for_timeout(900)
    t = page.inner_text("body")
    check(f"nor does Welcome {found(t)}", not found(t))
    page.locator("#btnIO").click(); page.wait_for_timeout(400)
    t = page.inner_text("#dlg")
    check(f"nor the Import & export window {found(t)}", not found(t))
    page.keyboard.press("Escape"); page.wait_for_timeout(300)

    have = os.path.exists(LIBRARY)
    if have:
        page.set_input_files("#impList", LIBRARY); page.wait_for_timeout(1500)
    page.locator("#btnSettings").click(); page.wait_for_timeout(400)
    t = page.inner_text("#dlg")
    check(f"nor Settings, {'with the published library loaded' if have else 'without a library (no copy next to public/)'} "
          f"{found(t)}", not found(t) and (not have or "materials library" in t))
    page.keyboard.press("Escape"); page.wait_for_timeout(300)

    page.locator("#btnHelp").click(); page.wait_for_timeout(600)
    help_text = page.inner_text("#content")
    check(f"nor the Help, all of it ({len(help_text)} characters) {found(help_text)}", len(help_text) > 50000 and not found(help_text))
    lic = re.search(r"23\. Licence\s*(.+?)(?:\n\n|$)", help_text, re.S)
    lic = lic.group(1) if lic else ""
    check(f"section 23 still names the reserved name and the attribution of NOTICE ({lic[:150]!r})",
          "name miFormulas is reserved" in lic and "attribution" in lic and "NOTICE" in lic)
    b.close()

manual = re.sub(r"<[^>]+>", " ", open(os.path.join(PUB, "docs", "manual.html"), encoding="utf-8").read())
check(f"the online manual does not name the author {found(manual)}", not found(manual))
notice = open(os.path.join(PUB, "NOTICE"), encoding="utf-8").read()
check("NOTICE keeps the attribution with the name, as the licence asks", "Based on miFormulas by" in notice and found(notice))

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
