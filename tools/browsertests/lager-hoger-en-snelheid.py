"""Lower and Higher in the tick bar, which no test used before (only screenshots.py), and the two speed-ups of build
261005b: the number format keeps one formatter per notation, and the list on the left is read in again only when it
changed.
- Lower on 1881 for men v2 of the starter set (as in the release GIF): the six lines with the lowest rel % still at
  100 % go to their 10 % dilution, rel % and the total stay, the ethanol gives up what they gained; Undo takes it back;
  a line already at its lowest dilution and a ticked solvent are skipped and reported; Higher takes a line back up.
- The number format: drawing a formula page calls toLocaleString no more, and fmt, fmtS, fmtIn and fmtSIn give what
  toLocaleString gives, for every number format in Settings.
- The list: an edit on a formula or a material page leaves its rows in place; a new name, a search, another tab and
  another item still change it.
Needs the local web server on port 8765 (see README)."""
import sys
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
SIX = ["Ionone Pure", "Cashmeran", "Eucalyptus Oil", "Adoxal", "Scotch Pine", "Isobutyl Quinoline"]
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 950}, locale="en-GB")
    page = ctx.new_page(); errs = []; msgs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1600)

    fid = page.evaluate("DATA.formulas.find(f => f.name === '1881 for men').id")
    def show():
        page.evaluate("id => switchTab('F', id, {type:'v', idx:1})", fid); page.wait_for_timeout(400)
    def lines():
        return page.evaluate("""id => { const f = DATA.formulas.find(x => x.id === id), v = f.versions[1];
          const K = calc(v.lines);
          return v.lines.map((l, i) => ({name: matById(l.materialId).name, dil: l.dilutionPct, w: l.weightG, rel: K.rows[i].rel})); }""", fid)
    def tick(names):
        L = lines()
        for n in names:
            i = next(k for k, l in enumerate(L) if l["name"] == n)
            page.check(f'table.ftable input.selCb[data-i="{i}"]')
        page.wait_for_timeout(200)
    def by(L, n): return next(l for l in L if l["name"] == n)

    # ---- Lower: the six lines with the lowest rel % that still stand at 100 %
    show()
    voor = lines()
    tick(SIX); n0 = len(msgs)
    page.click("#btnDilDown"); page.wait_for_timeout(500)
    na = lines()
    check(f"Lower takes the six lines to their 10 % dilution ({[by(na, n)['dil'] for n in SIX]})", all(by(na, n)["dil"] == 10 for n in SIX))
    check(f"and they weigh ten times as much ({[round(by(na, n)['w'], 3) for n in SIX]})",
          [round(by(na, n)["w"], 3) for n in SIX] == [0.2, 0.2, 0.2, 0.1, 0.1, 0.1])
    eth = round(by(na, "Ethanol")["w"], 3)
    check(f"the ethanol gives up what they gained: 88.852 g becomes {eth} g", eth == 88.042)
    tot = sum(l["w"] for l in na)
    check(f"the total stays at 100 g ({round(tot, 6)})", abs(tot - 100) < 1e-9)
    drift = max(abs((a["rel"] or 0) - (c["rel"] or 0)) for a, c in zip(voor, na))
    check(f"rel % stays the same on every line (largest difference {drift:.2e})", drift < 1e-9)
    check("nothing was skipped, so no message", len(msgs) == n0)
    check("the ticks are cleared", page.locator("table.ftable input.selCb:checked").count() == 0)
    page.click("#btnUndo"); page.wait_for_timeout(500)
    check("Undo takes the six lines and the ethanol back", lines() == voor)

    # ---- skipped and reported: a line at its lowest dilution, and a ticked solvent
    show(); n0 = len(msgs)
    tick(["Ionone Pure", "Isodamascone", "Ethanol"])
    page.click("#btnDilDown"); page.wait_for_timeout(500)
    m = msgs[n0] if len(msgs) > n0 else ""
    check(f"a line at its lowest dilution and the solvent are reported as skipped ({m!r})",
          "Shifted 1 line(s)" in m and "Skipped (already at extreme): Isodamascone" in m and "Skipped (solvent): Ethanol" in m)
    L = lines()
    check("the other line went down all the same", by(L, "Ionone Pure")["dil"] == 10 and by(L, "Isodamascone")["dil"] == 10)

    # ---- Higher takes it back up
    show(); n0 = len(msgs)
    tick(["Ionone Pure"])
    page.click("#btnDilUp"); page.wait_for_timeout(500)
    L = lines()
    check(f"Higher takes Ionone Pure back to 100 % and 0.020 g ({by(L, 'Ionone Pure')['dil']} %, {round(by(L, 'Ionone Pure')['w'], 3)} g)",
          by(L, "Ionone Pure")["dil"] == 100 and round(by(L, "Ionone Pure")["w"], 3) == 0.02 and round(by(L, "Ethanol")["w"], 3) == 88.852)
    check("without a message", len(msgs) == n0)

    # ---- the number format
    show()
    calls = page.evaluate("""() => { let n = 0; const orig = Number.prototype.toLocaleString;
      Number.prototype.toLocaleString = function(...a){ n++; return orig.apply(this, a); };
      try{ render(); } finally { Number.prototype.toLocaleString = orig; } return n; }""")
    check(f"drawing a formula page calls toLocaleString no more ({calls} calls)", calls == 0)
    diffs = page.evaluate("""() => {
      const out = [], keep = LOCALE;
      const xs = [0, -0.0000001, 0.0004, 0.001, 0.012, 1, 2.5, 12.345678, 999.9995, 1500, 1234567.891, -3.21, "7.5", "abc"];
      for (const loc of [undefined, "nl-BE", "de-DE", "fr-FR", "en-GB", "en-US"]){
        LOCALE = loc;
        for (const x of xs) for (const d of [0, 2, 3]){
          const n = noNegZero(x, d);
          const want = [
            x==null||isNaN(x) ? "–" : n.toLocaleString(loc, {minimumFractionDigits:d, maximumFractionDigits:d}),
            x==null||isNaN(x) ? "–" : (+x > 0 && n === 0 ? (+x).toLocaleString(loc, {minimumFractionDigits:0, maximumFractionDigits:8}) : n.toLocaleString(loc, {minimumFractionDigits:0, maximumFractionDigits:d})),
            x==null||isNaN(x) ? "" : n.toLocaleString(loc, {minimumFractionDigits:d, maximumFractionDigits:d, useGrouping:false}),
            x==null||isNaN(x) ? "" : n.toLocaleString(loc, {minimumFractionDigits:0, maximumFractionDigits:d, useGrouping:false})];
          const got = [fmt(x, d), fmtS(x, d), fmtIn(x, d), fmtSIn(x, d)];
          if (JSON.stringify(want) !== JSON.stringify(got)) out.push([loc, x, d, want, got]);
        }
      }
      LOCALE = keep; return out; }""")
    check(f"fmt, fmtS, fmtIn and fmtSIn give what toLocaleString gives, in every number format of Settings ({diffs[:2]})", not diffs)
    html_gb = page.evaluate("() => { render(); return document.querySelector('#content').innerHTML; }")
    swapped = page.evaluate("""() => { const keep = LOCALE; LOCALE = "de-DE"; render(); const h = document.querySelector('#content').innerHTML;
      LOCALE = keep; render(); return [h, document.querySelector('#content').innerHTML]; }""")
    check("another number format redraws the page in that format, and back", "88,852" in swapped[0] and swapped[1] == html_gb)

    # ---- the list on the left
    show()
    page.evaluate("() => { window.__row = document.querySelector('#list .item'); }")
    wi = page.locator("table.ftable input.w").first
    wi.fill("0.111"); wi.press("Tab"); page.wait_for_timeout(500)
    check("a weight on a formula page leaves the rows of the list in place",
          page.evaluate("() => window.__row.isConnected && window.__row === document.querySelector('#list .item')"))
    page.evaluate("id => { const f = DATA.formulas.find(x => x.id === id); f.name = '1881 for men (renamed)'; render(); }", fid)
    check("a new name is in the list at once", "1881 for men (renamed)" in page.locator("#list").inner_text())
    other = page.evaluate("DATA.formulas.find(f => f.name === 'Angel').id")
    page.evaluate("id => switchTab('F', id, {type:'v', idx:0})", other); page.wait_for_timeout(400)
    check("another formula is marked as the one that is open",
          page.evaluate("id => document.querySelector('#list .item.sel')?.dataset.id === id", other))
    page.click("#tabM"); page.wait_for_timeout(400)
    page.locator("#list .item", has_text="Geraniol").first.click(); page.wait_for_timeout(400)
    page.evaluate("() => { window.__row = document.querySelector('#list .item'); }")
    sup = page.locator('#content input[data-f="supplier"]').first
    sup.fill("A supplier of mine"); sup.press("Tab"); page.wait_for_timeout(500)
    check("a field on a material page leaves the rows of the list in place",
          page.evaluate("() => window.__row.isConnected && window.__row === document.querySelector('#list .item')"))
    page.fill("#searchBox", "geran"); page.wait_for_timeout(500)
    names = page.locator("#list .item").all_inner_texts()
    allm = page.evaluate("DATA.materials.length")
    check(f"a search still filters the list ({len(names)} of {allm} rows)", any("Geraniol" in n for n in names) and 0 < len(names) < allm)
    page.fill("#searchBox", ""); page.wait_for_timeout(400)
    page.click("#tabF"); page.wait_for_timeout(400)
    check("the Formulas tab shows formulas again", "Angel" in page.locator("#list").inner_text() and "Geraniol" not in page.locator("#list").inner_text())
    check(f"no errors in the page ({errs[:2]})", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
sys.exit(1 if fail else 0)
