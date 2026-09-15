"""Appearance and output (build 260914h): the CSV follows the number format of the app and cannot be
read as a formula by Excel, the file name survives a slash in a formula name, printing puts white
behind the page, both themes carry the soft red, the header does not break at 1280 px, and every
field, row and cross can be reached and understood without a mouse.
Needs the local web server on port 8765 (see README)."""
import io
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950}, accept_downloads=True)
    errs = []; msgs = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1600)

    # ---------- 1. the CSV follows the number format of the app ----------
    check("Belgian: semicolon and a comma in the figures",
          page.evaluate("""(() => { LOCALE = "nl-BE"; return [csvSep(), nBE("1.5")]; })()""") == [";", "1,5"])
    check("English: comma and a point",
          page.evaluate("""(() => { LOCALE = "en-GB"; return [csvSep(), nBE("1.5")]; })()""") == [",", "1.5"])
    check("no setting: the browser decides",
          page.evaluate("""(() => { LOCALE = undefined; return csvSep(); })()""")
          == ("," if page.evaluate("navigator.language").lower().startswith("en") else ";"))

    # ---------- 2. a formula with an awkward name ----------
    page.evaluate("""() => { LOCALE = "nl-BE";
      DATA.materials.push({id:"m-x", name:"=Gevaarlijk", category:"Test", pyramid:2, isSolvent:false,
        costPerGram:1, dilutions:[{pct:100, isBase:true}]});
      invalidateMats();
      DATA.formulas.push({id:"f-x", name:"A/B: proef", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[{materialId:"m-x", dilutionPct:100, weightG:1.5, remark:1}]}]});
      markDirty(); VIEW = {tab:"F", id:"f-x", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(700)
    with page.expect_download() as dl:
        page.click("#btnCsv")
    d = dl.value
    name = d.suggested_filename
    body = io.open(d.path(), encoding="utf-8-sig", newline="").read()
    rows = body.split("\r\n")
    check(f"the slash and the colon are out of the file name ({name})",
          "/" not in name and ":" not in name and "A-B- proef" in name)
    check(f"the rows end the way Excel expects and the separator is the semicolon ({len(rows)} rows)",
          len(rows) == 4 and rows[1].count(";") == 5 and "," not in rows[1])
    check("a material that starts with = cannot be read as a formula",
          '"\'=Gevaarlijk"' in body)
    check(f"and the weight carries a comma", '"1,500"' in body)

    # ---------- 3. printing ----------
    page.emulate_media(media="print")
    pr = page.evaluate("""(() => { const s = getComputedStyle(document.body);
      return {bg: s.backgroundColor}; })()""")
    check(f"the page prints on white ({pr['bg']})", pr["bg"] == "rgb(255, 255, 255)")
    page.emulate_media(media="screen")

    # ---------- 4. the soft red in both themes ----------
    soft = page.evaluate("""(() => getComputedStyle(document.documentElement).getPropertyValue('--danger-soft').trim())()""")
    check(f"the light theme has the soft red ({soft})", soft == "#FBE9E5")
    dark = page.evaluate("""(() => { document.documentElement.setAttribute("data-theme", "dark");
      const s = getComputedStyle(document.documentElement);
      const out = [s.getPropertyValue('--danger-soft').trim(), s.colorScheme];
      document.documentElement.setAttribute("data-theme", "light"); return out; })()""")
    check(f"and so does the dark one, which also tells the browser it is dark ({dark})",
          dark[0] == "#3A1E1A" and "dark" in dark[1])

    # ---------- 5. the header stays on one line at 1280 px ----------
    h = page.evaluate("""(() => { const b = [...document.querySelectorAll("header button")].filter(x => x.offsetParent);
      const tops = new Set(b.map(x => Math.round(x.getBoundingClientRect().top)));
      return {rows: tops.size, wrap: getComputedStyle(b[0]).whiteSpace}; })()""")
    check(f"all header buttons sit on one line ({h})", h["rows"] == 1 and h["wrap"] == "nowrap")
    page.set_viewport_size({"width": 850, "height": 800})       # wider than a phone, too narrow for one row
    page.wait_for_timeout(300)
    h2 = page.evaluate("""(() => { const b = [...document.querySelectorAll("header button")].filter(x => x.offsetParent);
      const st = document.getElementById("saveState"), w = document.documentElement.clientWidth;
      const over = b.filter(x => x.getBoundingClientRect().right > w + 1).map(x => x.id || x.textContent.trim());
      const rows = [...new Set(b.map(x => Math.round(x.getBoundingClientRect().top)))].sort((p,q)=>p-q);
      return {over, rows: rows.length, stateTop: Math.round(st.getBoundingClientRect().top),
              lastRow: rows[rows.length-1],
              stateLines: Math.round(st.getBoundingClientRect().height / parseFloat(getComputedStyle(st).fontSize) / 1.2),
              wrap: getComputedStyle(st).whiteSpace}; })()""")
    check(f"at 850 px no header button runs off the screen ({h2['over']})", not h2["over"])
    check(f"the state gets a line of its own below the buttons ({h2})",
          h2["stateTop"] > h2["lastRow"] and h2["stateLines"] <= 1 and h2["wrap"] == "nowrap")
    page.set_viewport_size({"width": 1280, "height": 800}); page.wait_for_timeout(300)

    # ---------- 6. without a mouse ----------
    page.click("#tabM"); page.wait_for_timeout(400)
    first = page.locator("#list .item").first
    check("a row in the list takes focus", first.get_attribute("tabindex") == "0")
    first.focus(); page.keyboard.press("Enter"); page.wait_for_timeout(600)
    check("and Enter opens it", page.locator("#content h2").count() > 0 and page.evaluate("VIEW.id") is not None)
    labs = page.evaluate("""(() => [...document.querySelectorAll('.fieldGrid label[for]')]
      .map(x => [x.getAttribute('for'), !!document.getElementById(x.getAttribute('for'))]))()""")
    check(f"every field label points at its own field ({len(labs)} labels)",
          len(labs) >= 9 and all(v for _, v in labs))
    check("so clicking the label lands in the field",
          page.evaluate("""(() => { document.querySelector('.fieldGrid label[for="mf_name"]').click();
            return document.activeElement.dataset.f; })()""") == "name")
    check("the cross on a dilution says what it removes",
          page.locator("[data-deldil]").first.get_attribute("title") == "Delete this dilution")
    check("and the gear says what it opens", "Settings" in (page.locator("#btnSettings").get_attribute("title") or ""))

    # ---------- 7. one dash throughout ----------
    check("no em dashes anywhere on the page", page.evaluate("!document.body.innerHTML.includes('\\u2014')"))
    check("the search box says it finds formulas too",
          "Formulas" in (page.locator("#searchBox").get_attribute("title") or ""))
    page.click("#tabT"); page.wait_for_timeout(400)
    page.click("#btnShops"); page.wait_for_timeout(500)
    check("the shop dialog names the button it belongs to",
          "Web shops for the “Search” button" in page.text_content("#dlg"))
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---------- 8. the head of a formula (build 260915c): version row, Delete version, pyramid chart ----------
    page.click("#tabF"); page.wait_for_timeout(300)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.name === "1881 for men");   // five pyramid levels: the tallest chart
      f.versions.push({v: 2, date: today(), notes: "", lines: f.versions[0].lines.map(l => ({...l}))});
      switchTab("F", f.id, {type: "v", idx: 1}); }""")
    page.wait_for_timeout(500)
    head = page.evaluate("""() => { const r = s => { const e = document.querySelector(s); return e ? e.getBoundingClientRect() : null; };
      const del = document.querySelector("#btnDelV"), cs = getComputedStyle(del);
      return {cmp: r("#btnCmp"), del: r("#btnDelV"), sel: r("#verSel"), order: r("#sortSel"), chart: r(".fpyr"),
              border: parseFloat(cs.borderTopWidth), colour: cs.color, bg: cs.backgroundColor}; }""")
    check("Delete version is a bordered button in red next to Compare…",
          head["border"] > 0 and head["colour"] == "rgb(196, 47, 31)" and head["bg"] != "rgba(0, 0, 0, 0)"
          and abs(head["del"]["y"] - head["cmp"]["y"]) < 4 and head["del"]["x"] > head["cmp"]["x"])
    check(f"the Order row follows the version row directly ({head['order']['y'] - head['sel']['y'] - head['sel']['height']:.0f} px)",
          head["order"]["y"] - (head["sel"]["y"] + head["sel"]["height"]) < 32)
    check("the pyramid chart stays inside the head, above the Order row",
          head["chart"] and head["chart"]["y"] + head["chart"]["height"] <= head["order"]["y"] + 1)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(400)

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
