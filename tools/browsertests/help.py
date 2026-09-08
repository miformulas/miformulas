"""Help button: the manual embedded in the app (template#manualTpl), shown in the page pane.
Needs the local web server on port 8765 (see README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    page = ctx.new_page()
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(800)

    check("landing has a Manual link to the online manual",
          page.locator("#btnManual").is_visible() and page.locator("#btnManual").get_attribute("href") == "https://miformulas.com/docs/manual.html")
    check("template with the manual is present and not empty", page.evaluate("document.querySelector('#manualTpl').innerHTML.length > 30000"))
    check("template holds no script", page.evaluate("!/<script/i.test(document.querySelector('#manualTpl').innerHTML)"))
    check("help button does nothing before data is loaded", page.evaluate("(() => { document.querySelector('#btnHelp').click(); return document.querySelector('#content').innerHTML === ''; })()"))

    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.click("#btnHelp"); page.wait_for_timeout(300)
    check("help view renders the manual", page.locator("#content .help h1").inner_text().strip() == "miFormulas manual")
    check("contents list is linked", page.locator("#content .help ol.toc a").count() == 24)
    check("figures became links to the online manual", page.locator("#content .help .helpfig a").count() >= 40
          and page.locator("#content .help img").count() == 0)
    check("external links open in a new tab", page.evaluate("[...document.querySelectorAll('#content .help a[href^=\"http\"]')].every(a => a.target === '_blank')"))
    # a contents link scrolls to the section instead of changing the URL
    before = page.evaluate("location.href")
    page.locator("#content .help ol.toc a", has_text="Bench view and printing").click(); page.wait_for_timeout(300)
    top = page.evaluate("(() => { const c = document.querySelector('#content'), h = c.querySelector('#s14-bench-view-and-printing'); return h.getBoundingClientRect().top - c.getBoundingClientRect().top; })()")
    check("contents link scrolls to section 14 inside the pane", -5 <= top <= 60)
    check("URL unchanged by the contents link", page.evaluate("location.href") == before)
    page.click("#helpTop"); page.wait_for_timeout(300)
    check("Contents button scrolls back up", page.evaluate("document.querySelector('#content').scrollTop") < 1200)
    # second click on ? closes the help again
    page.click("#btnHelp"); page.wait_for_timeout(300)
    check("? again returns to the previous view (Welcome)", page.locator("#content h2").first.inner_text().strip() == "Welcome")
    page.click("#btnHelp"); page.wait_for_timeout(300)
    page.click("#helpClose"); page.wait_for_timeout(300)
    check("Close returns to the previous view", page.locator("#content h2").first.inner_text().strip() == "Welcome")
    # navigating elsewhere leaves the help view
    page.click("#btnHelp"); page.wait_for_timeout(300)
    page.locator("#list").get_by_text("Rose de Mai 68", exact=True).click(); page.wait_for_timeout(400)
    check("picking a formula leaves the help view", page.locator("#content h2").first.inner_text().startswith("Rose de Mai 68"))
    page.click("#btnHelp"); page.wait_for_timeout(300)
    page.click("#tabM"); page.wait_for_timeout(300)
    check("switching tab leaves the help view", not page.locator("#content .help").count())
    page.click("#btnHelp"); page.wait_for_timeout(300)
    page.click("#btnHome"); page.wait_for_timeout(300)
    check("Home leaves the help view", page.locator("#content h2").first.inner_text().strip() == "Welcome")
    check("no page errors", not errs)
    b.close()
print(f"\n{ok} OK, {fail} FAIL")
