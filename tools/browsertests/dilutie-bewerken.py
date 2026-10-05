"""The date and the note of a dilution change in place on the page of a material (build 261005a). The table Dilutions
has a date field and a note field per dilution, each with a name; a change is one Undo step and comes back with Redo,
a note is kept without the spaces around it, a change that changes nothing makes no step, and an empty date is
allowed. Add dilution still gives a new dilution today's date. What was changed is still there in a second window,
which only reads, so its fields are there but disabled; on a phone (390 px) the whole date stays in view. Also the
sentence in the Help (section 3) and the docstring of tools/bouw-docs.py, which no longer names deploy/.
Needs the local web server on port 8765 (see README)."""
import os, sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
PUB = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

GER = "() => DATA.materials.find(m => m.name === 'Geraniol')"
def open_geraniol(pg):
    pg.evaluate(f"() => {{ VIEW = {{tab: 'M', id: ({GER})().id}}; setTabs(); render(); }}")
    pg.wait_for_timeout(400)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    page = ctx.new_page(); errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.set_default_timeout(4000)                      # a build without the fields fails here, it does not hang
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1600)
    # Geraniol of the starter set: 100 % (the base) and 10 %, without a date or a note
    open_geraniol(page)
    i = page.evaluate(f"() => ({GER})().dilutions.findIndex(d => d.pct === 10)")
    DATE, NOTE = f'[data-dildate="{i}"]', f'[data-dilnote="{i}"]'
    dil = lambda: page.evaluate(f"() => {{ const d = ({GER})().dilutions[{i}]; return [d.date || '', d.notes || '']; }}")
    steps = lambda: page.evaluate("UNDO.length")

    n = page.evaluate(f"() => ({GER})().dilutions.length")
    check("the table has a date field and a note field for every dilution",
          page.locator("[data-dildate]").count() == n == page.locator("[data-dilnote]").count())
    try:
        check("the date field is a date field", page.get_attribute(DATE, "type") == "date")
        check("each field is named after its dilution",
              page.get_attribute(DATE, "aria-label") == "Date of the 10% dilution"
              and page.get_attribute(NOTE, "aria-label") == "Note with the 10% dilution")

        s = steps(); page.fill(DATE, "2026-09-12"); page.wait_for_timeout(300)
        check(f"a date is stored, as one Undo step ({dil()}, {steps() - s} step)", dil()[0] == "2026-09-12" and steps() == s + 1)
        page.click("#btnUndo"); page.wait_for_timeout(500)
        check("Undo takes the date back, in the data and in the field", dil()[0] == "" and page.input_value(DATE) == "")
        page.click("#btnRedo"); page.wait_for_timeout(500)
        check("Redo brings it back", dil()[0] == "2026-09-12" and page.input_value(DATE) == "2026-09-12")

        s = steps(); page.fill(NOTE, "  in ethanol, from the 2025 bottle  "); page.press(NOTE, "Tab"); page.wait_for_timeout(300)
        check(f"a note is kept without the spaces around it, in the data and in the field ({dil()[1]!r})",
              dil()[1] == "in ethanol, from the 2025 bottle" and page.input_value(NOTE) == "in ethanol, from the 2025 bottle")
        check("that is one Undo step", steps() == s + 1)
        s = steps(); page.fill(NOTE, "in ethanol, from the 2025 bottle "); page.press(NOTE, "Tab"); page.wait_for_timeout(300)
        check("a space more is no change: no Undo step, and the field without it",
              steps() == s and page.input_value(NOTE) == "in ethanol, from the 2025 bottle")
        page.click("#btnUndo"); page.wait_for_timeout(500)
        check("Undo takes the note back", dil() == ["2026-09-12", ""])
        page.click("#btnRedo"); page.wait_for_timeout(500)

        s = steps(); page.fill(DATE, ""); page.wait_for_timeout(300)
        check("an empty date is allowed", dil()[0] == "" and steps() == s + 1)
        page.fill(DATE, "2026-09-12"); page.wait_for_timeout(300)

        page.fill("#newDil", "5"); page.fill("#newDilNote", "trial"); page.click("#btnAddDil"); page.wait_for_timeout(400)
        nieuw = page.evaluate(f"() => {{ const m = ({GER})(), j = m.dilutions.findIndex(d => d.pct === 5); "
                              f"return [j, m.dilutions[j].date, m.dilutions[j].notes, today()]; }}")
        check(f"Add dilution still gives a new dilution today's date, in the data and in its field ({nieuw})",
              nieuw[1] == nieuw[3] and nieuw[2] == "trial" and page.input_value(f'[data-dildate="{nieuw[0]}"]') == nieuw[3])
    except Exception as e:
        check(f"the fields respond ({str(e).splitlines()[0][:90]})", False)

    # saved, and read in a second window: that one only reads, so its fields are there but cannot be changed
    page.click("#btnSave"); page.wait_for_timeout(800)
    pg2 = ctx.new_page(); pg2.on("dialog", lambda d: d.accept()); pg2.set_default_timeout(4000)
    pg2.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg2.goto(URL); pg2.wait_for_function("() => typeof DATA !== 'undefined' && DATA && DATA.formulas", timeout=10000)
    pg2.wait_for_timeout(600)
    open_geraniol(pg2)
    try:
        check("in a second window the date and the note are still there",
              pg2.input_value(DATE) == "2026-09-12" and pg2.input_value(NOTE) == "in ethanol, from the 2025 bottle")
        check("and that window only reads: its fields are disabled",
              pg2.evaluate("readOnly()") is True and pg2.locator(DATE).is_disabled() and pg2.locator(NOTE).is_disabled())
    except Exception as e:
        check(f"the second window shows the fields ({str(e).splitlines()[0][:90]})", False)
    pg2.close()

    # a phone: the whole date stays in view and the table stays in its box
    tel = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pt = tel.new_page(); pt.on("dialog", lambda d: d.accept()); pt.set_default_timeout(4000)
    pt.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pt.goto(URL); pt.wait_for_timeout(800)
    pt.click("#btnStarter"); pt.wait_for_timeout(1600)
    open_geraniol(pt)
    maat = pt.evaluate("""() => { const d = document.querySelector('[data-dildate]'), t = d && d.closest('table');
      return d ? [Math.round(d.getBoundingClientRect().width), t.scrollWidth, t.clientWidth] : null; }""")
    check(f"on 390 px the date field is wide enough for a whole date, and the table fits ({maat})",
          bool(maat) and maat[0] >= 120 and maat[1] <= maat[2] + 1)
    tel.close()

    helptxt = page.evaluate("document.getElementById('manualTpl').innerHTML")
    check("the Help says that the date and the note can be changed",
          "The date and the note of a dilution can be changed in the table." in helptxt)
    doc = open(os.path.join(PUB, "tools", "bouw-docs.py"), encoding="utf-8").read()
    check("the docstring of bouw-docs.py no longer names deploy/", "deploy/" not in doc)
    check("no JavaScript errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
