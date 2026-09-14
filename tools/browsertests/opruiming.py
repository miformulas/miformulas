"""Build 260915: the tail of the review of 260913g. Search, confirmations, ellipsis,
the library credit and the alias list, a frozen variation, and read-only on a phone.
Needs the local web server on port 8765 (see README)."""
import json, os, tempfile
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

LIB = {"type": "miformulas-materials", "name": "Credited library", "version": "2026-09-15",
       "licence": "CC BY 4.0", "attribution": "Facts by A. Colleague, CC BY 4.0",
       "source": "https://example.org/library", "materials": [
    {"name": "Ambroxide", "aliases": ["Ambroxan", "Ambrofix"], "cas": "6790-58-5",
     "category": "Woody - amber", "pyramid": 4},
    {"name": "Proefstof Q", "category": "Test", "pyramid": 1}]}

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errs = []; msgs = []; mode = {"v": "accept"}
    page.on("pageerror", lambda e: errs.append(str(e)))
    def on_dialog(d):
        msgs.append(d.message)
        d.accept() if mode["v"] == "accept" else d.dismiss()
    page.on("dialog", on_dialog)
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)

    # ---------- ellipsis on the buttons that open a window ----------
    check("+ New formula…", page.text_content("#btnNew").strip() == "+ New formula…")
    check("+ New material…", page.text_content("#btnNewMat").strip() == "+ New material…")
    check("Backup…", page.text_content("#btnBackup").strip() == "Backup…")
    page.evaluate("() => { const f = DATA.formulas.find(x => x.versions.length); switchTab('F', f.id, {type:'v', idx:0}); }")
    page.wait_for_timeout(500)
    check("Rename…", page.text_content("#btnRenameF").strip() == "Rename…")
    check("Copy to new formula…", page.text_content("#btnCopyF").strip() == "Copy to new formula…")
    check("Change category…", page.text_content("#btnCatF").strip() == "Change category…")
    check("+ New variation…", page.text_content("#btnNewVar").strip() == "+ New variation…")
    check("the pencil says so in its tooltip", page.get_attribute("#btnNameV", "title") == "Name this version…")
    check("the replace arrows say so in their tooltip",
          (page.get_attribute("[data-repl]", "title") or "").endswith("…"))

    # ---------- a trial note asks before it goes ----------
    page.fill("#trialText", "Smells of pear drops."); page.click("#btnAddTrial"); page.wait_for_timeout(400)
    check("the trial note is there", page.locator("[data-deltrial]").count() == 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.click("[data-deltrial]"); page.wait_for_timeout(400)
    check(f"removing asks first ({msgs})", any("Remove this trial note?" in m for m in msgs))
    check("saying no keeps it", page.locator("[data-deltrial]").count() == 1)
    mode["v"] = "accept"
    page.click("[data-deltrial]"); page.wait_for_timeout(400)
    check("saying yes removes it", page.locator("[data-deltrial]").count() == 0)

    # ---------- a bench group asks too ----------
    page.click("#btnBenchToggle"); page.wait_for_timeout(500)
    before = page.locator("[data-bdel]").count()
    page.click("#btnAddGroup"); page.wait_for_timeout(400)
    check("a bench group was added", page.locator("[data-bdel]").count() == before + 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.locator("[data-bdel]").last.click(); page.wait_for_timeout(400)
    check(f"deleting a group asks first ({msgs[:1]})", any("Delete this bench group?" in m for m in msgs))
    check("saying no keeps the group", page.locator("[data-bdel]").count() == before + 1)
    mode["v"] = "accept"
    page.locator("[data-bdel]").last.click(); page.wait_for_timeout(400)
    check("saying yes deletes it", page.locator("[data-bdel]").count() == before)
    page.click("#btnBenchToggle"); page.wait_for_timeout(400)

    # ---------- a stock entry asks too ----------
    page.evaluate("() => { const m = DATA.materials[0]; switchTab('M', m.id, null); }")
    page.wait_for_timeout(500)
    def open_stock():   # the stock panel is a <details>, closed again after every render
        page.evaluate("() => { const d = document.querySelector('#stBuyAmt')?.closest('details'); if (d) d.open = true; }")
        page.wait_for_timeout(200)
    open_stock()
    n0 = page.locator("[data-delev]").count()
    page.fill("#stBuyAmt", "25"); page.fill("#stBuyNote", "Test supplier")
    page.click("#btnBuy"); page.wait_for_timeout(400); open_stock()
    check("the purchase is logged", page.locator("[data-delev]").count() == n0 + 1)
    msgs.clear(); mode["v"] = "dismiss"
    page.locator("[data-delev]").first.click(); page.wait_for_timeout(400); open_stock()
    check(f"removing a stock entry asks first ({msgs[:1]})", any("Remove this stock entry?" in m for m in msgs))
    check("saying no keeps it", page.locator("[data-delev]").count() == n0 + 1)
    mode["v"] = "accept"
    page.locator("[data-delev]").first.click(); page.wait_for_timeout(400); open_stock()
    check("saying yes removes it", page.locator("[data-delev]").count() == n0)

    # ---------- searching for the starter set ----------
    page.evaluate("() => { switchTab('M', null, null); }"); page.wait_for_timeout(400)
    page.fill("#searchBox", "arter"); page.wait_for_timeout(400)
    check("a substring of “starter set” no longer shows every starter material",
          page.locator("#list .item").count() == 0)
    page.fill("#searchBox", "sta"); page.wait_for_timeout(400)
    check("the beginning of “starter set” still finds them", page.locator("#list .item").count() > 100)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # ---------- a value that rounds to nothing keeps no minus sign ----------
    check("fmt(-0.0000001) is 0, not -0", page.evaluate("fmt(-0.0000001, 3)").replace(",", ".") == "0.000")
    check("fmtS(-0.0000001) too", "-" not in page.evaluate("fmtS(-0.0000001, 2)"))

    # ---------- a frozen variation drops the recipe of differences ----------
    page.evaluate("""() => {
        const f = DATA.formulas.find(x => x.versions.length && x.versions[0].lines.length > 1);
        f.variations.push({id: "va-t", label: "test", date: "2026-09-15", baseV: f.versions[0].v,
                           dilutionOverrides: {"x|100": 10}, solventDeltaG: 1.5, solventBaseC: 2, targetWeightG: 50});
        window.__fid = f.id; switchTab('F', f.id, {type:'var', idx: f.variations.length - 1});
    }""")
    page.wait_for_timeout(500)
    mode["v"] = "accept"
    page.click("#btnFreeze"); page.wait_for_timeout(600)
    va = page.evaluate("() => DATA.formulas.find(x => x.id === window.__fid).variations.find(v => v.id === 'va-t')")
    check("freezing fixes the lines", va.get("frozen") is True and isinstance(va.get("lines"), list))
    check("and drops the differences it no longer needs",
          not {"dilutionOverrides", "solventDeltaG", "solventBaseC", "targetWeightG"} & set(va))
    check("while the base version it came from is kept", "frozenFrom" in va and va.get("frozenFromName"))

    # ---------- the library: alternative names in the list, the credit in Settings ----------
    f = os.path.join(tempfile.mkdtemp(), "lib.json")
    open(f, "w", encoding="utf-8").write(json.dumps(LIB))
    page.evaluate("() => { HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); }")
    page.wait_for_timeout(400)
    msgs.clear()
    page.set_input_files("#impList", f); page.wait_for_timeout(700)
    page.click("#btnNewMat"); page.wait_for_timeout(400)
    opts = page.locator("#nmList option").evaluate_all("els => els.map(e => e.value)")
    check(f"the list offers the names and the alternative names ({len(opts)})",
          "Ambroxide" in opts and "Ambroxan" in opts and "Ambrofix" in opts and "Proefstof Q" in opts)
    check("and offers each of them once", len(opts) == len(set(opts)))
    page.click("#dlgCancel"); page.wait_for_timeout(300)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    dlg = page.text_content("#dlg")
    check("Settings shows the attribution", "Facts by A. Colleague, CC BY 4.0" in dlg)
    check("and the source as a link", page.locator('#dlg a[href="https://example.org/library"]').count() == 1)
    page.click("#dlgCancel"); page.wait_for_timeout(300)

    # ---------- read-only on a phone ----------
    page.set_viewport_size({"width": 400, "height": 800})
    page.evaluate("() => { DEMO = false; HOMEVIEW = true; VIEW = {tab:'F', id:null, sub:null}; render(); }")
    page.wait_for_timeout(500)
    check("importing is out of reach", page.locator("#btnImpF").is_disabled() and page.locator("#btnImpL").is_disabled())
    check("exporting stays within reach", not page.locator("#btnExpF").is_disabled()
          and not page.locator("#btnExpM").is_disabled() and not page.locator("#btnExpL").is_disabled())
    page.evaluate("""() => {
        IMPORTP = {type:"miformulas-import", name:"Proef", lines:[{name:"Ambroxide", weightG:1}]};
        HOMEVIEW = false; render();
    }""")
    page.wait_for_timeout(500)
    check("an import preview can still be left", not page.locator("#btnImpCancel").is_disabled())
    check("but not confirmed", page.locator("#btnImpOk").is_disabled())

    check(f"no page errors ({errs[:2]})", not errs)
    ctx.close(); b.close()

print(f"\n{ok} ok, {fail} fail")
raise SystemExit(1 if fail else 0)
