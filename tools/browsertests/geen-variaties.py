"""No variations any more (build 260915b): a formula has versions only. A data file from an earlier
build that still holds variations is loaded with one warning, the field is left in the file untouched
and nothing of it is shown; every place that used to know about variations (formula page, Move into…,
Copy, Compare, the Welcome tile, the export of all formulas, the list counter) knows versions only.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
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

    # ---------- 1. a data file with variations: one warning, the field kept, nothing shown ----------
    old = page.evaluate("JSON.parse(serialize())")
    f0 = old["formulas"][0]
    f0["variations"] = [{"id": "va-old", "label": "20%", "frozen": True, "date": "2026-09-01", "notes": "old",
                         "lines": [{"materialId": f0["versions"][0]["lines"][0]["materialId"], "dilutionPct": 100, "weightG": 1, "remark": 1}]},
                        {"id": "va-old2", "label": "44gr", "frozen": False, "date": "2026-09-02", "dilutionOverrides": {}, "targetWeightG": 44}]
    path = os.path.join(tempfile.mkdtemp(), "oud.json")
    open(path, "w", encoding="utf-8").write(json.dumps(old))
    msgs.clear()
    page.click("#btnHome"); page.wait_for_timeout(300)
    page.evaluate("""() => idb.set("demoData", null)""")
    page.reload(); page.wait_for_timeout(900)
    page.set_input_files("#fileFallback", path); page.wait_for_timeout(1500)
    check(f"the old file loads with one warning that names the variations ({[m[:60] for m in msgs]})",
          sum("variation(s) from an earlier miFormulas" in m for m in msgs) == 1 and "2 variation" in " ".join(msgs))
    check("the formula is there, with its versions", page.evaluate("DATA.formulas[0].versions.length") == len(f0["versions"]))
    kept = page.evaluate("JSON.parse(serialize()).formulas[0].variations")
    check("the variations stay in the file untouched", kept == f0["variations"])
    page.evaluate("""() => { switchTab('F', DATA.formulas[0].id, {type:'v', idx:0}); }""")
    page.wait_for_timeout(500)
    txt = page.text_content("#content")
    check("but nothing of them is shown on the formula page",
          "20%" not in page.locator(".chipRow").all_inner_texts()[0] and "Variations" not in txt and "44gr" not in txt)
    check("no variation buttons", all(page.locator(s).count() == 0 for s in ("#btnNewVar", "#btnFreeze", "#btnDelVar", "#varBase", "[data-va]")))
    check("the Welcome tile counts versions", (page.evaluate("() => { HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); return document.querySelector('.tiles').textContent; }") or "").count("versions") == 1
          and "variations" not in page.text_content(".tiles"))
    check("the list counter reads versions", "versions" in page.locator("#list .item").first.inner_text() or "1 version" in page.locator("#list .item").first.inner_text())

    # ---------- 2. Move into… offers versions only; Copy has no variations box; Compare lists versions ----------
    page.evaluate("""() => {
      const m = DATA.materials[0].id;
      DATA.formulas.push({id:"f-i1", name:"Imp v01", category:"Uncategorised", created:today(), frozenImport:true,
        versions:[{v:1, date:today(), imported:true, sourceName:"Imp v01", lines:[{materialId:m, dilutionPct:100, weightG:2, remark:1}]}]});
      DATA.formulas.push({id:"f-i2", name:"Imp v02", category:"Uncategorised", created:today(), frozenImport:true,
        versions:[{v:1, date:today(), imported:true, sourceName:"Imp v02", lines:[{materialId:m, dilutionPct:100, weightG:3, remark:1}]}]});
      buildUsage(); markDirty(); switchTab('F', "f-i2", {type:'v', idx:0}); }""")
    page.wait_for_timeout(500)
    page.click("#btnMoveF"); page.wait_for_timeout(400)
    check("Move into… knows versions only", page.locator("#mvLabel").count() == 0 and page.locator("input[name=mvMode]").count() == 0
          and "a new version" in page.text_content("#dlg"))
    page.click("#dlgOk"); page.wait_for_timeout(600)
    got = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-i1"); return f.versions.map(v => v.sourceName); })()""")
    check(f"and moves the formula in as a version ({got})", got == ["Imp v01", "Imp v02"])
    check("the list counter reads 2 versions", "2 versions" in page.locator("#list .item", has_text="Imp v01").first.inner_text())
    page.click("#btnCopyF"); page.wait_for_timeout(400)
    check("Copy to new formula has no variations box", page.locator("#cpVars").count() == 0 and page.locator("#cpName").count() == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.click("#btnCmp"); page.wait_for_timeout(500)
    opts = page.evaluate("[...document.querySelectorAll('#cmpA option')].map(o => o.textContent)")
    check(f"Compare lists the two versions and nothing else ({opts})", len(opts) == 2 and all(o.startswith("v") for o in opts))
    page.click("#btnCmpClose"); page.wait_for_timeout(400)

    # ---------- 3. the export of all formulas covers versions, and nothing named variation is left in the page ----------
    page.click("#btnHome"); page.wait_for_timeout(400)
    page.click("#btnIO"); page.wait_for_timeout(400)
    with page.expect_download() as dl:
        page.click("#btnExpF")
    csv = open(dl.value.path(), encoding="utf-8-sig").read()
    check("the export names versions only", "variation" not in csv and "\tv1" in csv.replace(";", "\t").replace(",", "\t") or "v1" in csv)
    check("the word variation appears nowhere in the app's pages",
          "variation" not in page.text_content("#content").lower() and "variation" not in page.text_content("header").lower())
    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
