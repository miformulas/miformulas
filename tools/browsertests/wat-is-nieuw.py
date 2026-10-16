"""What's new (bouw 261017a): de pagina docs/whats-new.html en de links ernaar in de app.
Draait op de lokale webserver (poort 8765, zie README); de pagina's worden uit de repo zelf gelezen."""
import os, re
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
WN = "https://miformulas.com/docs/whats-new.html"
HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, "..", "..", "docs"))
lees = lambda n: open(os.path.join(DOCS, n), encoding="utf-8").read() if os.path.exists(os.path.join(DOCS, n)) else ""

ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

# ---------------- 1. de pagina ----------------
wn, man = lees("whats-new.html"), lees("manual.html")
check("docs/whats-new.md en docs/whats-new.html bestaan", bool(wn) and bool(lees("whats-new.md")))
check("de titel is What’s new in miFormulas", "<h1" in wn and "What’s new in miFormulas" in wn)
for n in ("manual.html", "ai-prompts.html", "first-five-minutes.html", "whats-new.html"):
    check(f"de navigatie van {n} noemt What’s new", 'href="whats-new.html"' in lees(n) or (n == "whats-new.html" and "<span>What’s new</span>" in wn))
ankers = sorted(set(re.findall(r'href="manual\.html#([^"]+)"', wn)))
check(f"elk punt verwijst naar de handleiding ({len(ankers)} secties)", len(ankers) >= 5)
mis = [a for a in ankers if f'id="{a}"' not in man]
check(f"elke verwijzing naar de handleiding bestaat ({mis or 'alle'})", not mis)
h2 = [m.start() for m in re.finditer(r"<h2", wn)]
bq = wn.find("<blockquote")
check("de kader staat tussen de laatste en de voorlaatste update", len(h2) >= 2 and h2[0] < bq < h2[1])
check("de kader zegt hoe je bijwerkt", "Do you have the latest version?" in wn and "Check for updates" in wn)
check("geen em-dash op de pagina", "—" not in lees("whats-new.md"))
check("de handleiding noemt de pagina", WN in lees("manual.md"))

# ---------------- 2. de links in de app ----------------
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1280, "height": 900})
    errs = []; page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(URL); page.wait_for_timeout(800)
    a = page.locator("#btnWhatsNew")
    check("het startscherm: What’s new naast Manual, in een nieuw tabblad",
          a.count() == 1 and a.is_visible() and a.get_attribute("href") == WN and a.get_attribute("target") == "_blank")
    if a.count():
        kleur = page.evaluate("() => [getComputedStyle(document.querySelector('#btnWhatsNew')).color, getComputedStyle(document.querySelector('#btnManual')).color]")
        check(f"in de kleur van Manual ({kleur})", kleur[0] == kleur[1])
        check("direct na Manual", page.evaluate("() => document.querySelector('#btnManual').nextElementSibling.id === 'btnWhatsNew'"))
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.click("#btnHelp"); page.wait_for_timeout(400)
    h = page.locator("#helpWhatsNew")
    check("de Help-balk: What’s new", h.count() == 1 and h.is_visible() and h.get_attribute("href") == WN and h.get_attribute("target") == "_blank")
    check("geen fouten op de pagina", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
