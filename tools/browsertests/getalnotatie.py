"""Number format and the fixes of build 260914: thousands separators, IFRA dose per formula,
undo under a dialog, Replace + Cancel, and the usage index after adding a line.
Needs the local web server on port 8765 (see README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def start(ctx, errs, msgs):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.click("#btnStarter"); pg.wait_for_timeout(1200)
    return pg

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- 1. English locale: a batch of 1500 g stays 1500 g ----------
    ctx = b.new_context(viewport={"width": 1280, "height": 900}, locale="en-GB")
    errs = []; msgs = []
    page = start(ctx, errs, msgs)

    nums = page.evaluate("""() => ({
      en: parseNum("1,234.56"), be: parseNum("1.234,56"), fr: parseNum("1 234,56"),
      nbsp: parseNum("1\\u00A0234,56"), dot: parseNum("2.5"), comma: parseNum("2,5"),
      big: parseNum("1.234.567"), plain: parseNum("1500")})""")
    check(f"parseNum reads both notations ({nums})",
          nums["en"] == 1234.56 and nums["be"] == 1234.56 and nums["fr"] == 1234.56
          and nums["nbsp"] == 1234.56 and nums["dot"] == 2.5 and nums["comma"] == 2.5
          and nums["big"] == 1234567 and nums["plain"] == 1500)

    page.click("#tabF"); page.wait_for_timeout(300)
    page.click("#list .item"); page.wait_for_timeout(500)
    page.click("#scaleBox summary"); page.wait_for_timeout(300)
    page.fill("#scaleW", "1500"); page.click("#btnApplyScale"); page.wait_for_timeout(600)
    page.click("#scaleBox summary") if not page.locator("#scaleW").is_visible() else None
    page.wait_for_timeout(200)
    shown = page.locator("#scaleW").input_value()
    check(f"the target total is shown without a thousands separator ({shown!r})", "," not in shown)
    total1 = page.evaluate("(() => { const f = DATA.formulas.find(x => x.id === VIEW.id); const v = f.versions[f.versions.length-1]; return v.lines.reduce((s,l) => s + (l.weightG||0), 0); })()")
    page.click("#btnApplyScale"); page.wait_for_timeout(600)      # Apply without touching the field
    total2 = page.evaluate("(() => { const f = DATA.formulas.find(x => x.id === VIEW.id); const v = f.versions[f.versions.length-1]; return v.lines.reduce((s,l) => s + (l.weightG||0), 0); })()")
    check(f"Apply without editing keeps the batch ({total1:.3f} → {total2:.3f})", abs(total2 - total1) < 0.01 and total2 > 1000)

    w = page.locator("input.w").first.input_value()
    check(f"line weights are shown without a thousands separator ({w!r})", "," not in w)

    # ---------- 2. Delivered: 1000 g for € 20 is € 0.02 / g ----------
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Hedione"); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(400)
    page.click("#btnToOrder"); page.wait_for_timeout(500)
    page.click("#tabT"); page.wait_for_timeout(400)
    page.fill("[data-oamt='0']", "1000"); page.locator("[data-oamt='0']").press("Tab"); page.wait_for_timeout(300)
    page.fill("[data-oprice='0']", "20"); page.locator("[data-oprice='0']").press("Tab"); page.wait_for_timeout(300)
    amt = page.locator("[data-oamt='0']").input_value()
    check(f"the order amount is shown without a thousands separator ({amt!r})", "," not in amt and "." not in amt)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(500)
    dv = page.locator("#dvAmt").input_value()
    check(f"Delivered prefills the amount without a separator ({dv!r})", dv.startswith("1000"))
    page.click("#dlgOk"); page.wait_for_timeout(600)
    cpg = page.evaluate("(() => { const m = DATA.materials.find(x => x.name === 'Hedione'); return m && m.costPerGram; })()")
    check(f"cost per gram is price / 1000 g ({cpg})", cpg is not None and abs(cpg - 0.02) < 0.0001)

    # ---------- 2b. build 260918e: Amount purchased is a number with a unit ----------
    zonder = page.evaluate("""() => { const m = DATA.materials.find(x => x.density == null && x.costPerGram == null
        && (x.dilutions||[]).some(d => d.isBase && d.pct === 100)); return m && m.name; }""")
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", zonder); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(400)
    page.click("#btnToOrder"); page.wait_for_timeout(500)
    page.click("#tabT"); page.wait_for_timeout(400)
    page.fill("[data-oamt='0']", "100"); page.locator("[data-oamt='0']").press("Tab"); page.wait_for_timeout(300)
    page.fill("[data-oprice='0']", "50"); page.locator("[data-oprice='0']").press("Tab"); page.wait_for_timeout(300)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(600)
    check(f"Amount purchased carries a unit, on gram to start with ({zonder})",
          page.locator("#dvU").is_visible() and page.locator("#dvU").input_value() == "g")
    check("and the density stays out of sight as long as you buy grams",
          page.locator("#dvDensW").count() == 1 and page.locator("#dvDensW").is_hidden())
    page.select_option("#dvU", "ml"); page.wait_for_timeout(400)
    check(f"millilitres without a density ask for one ({page.text_content('#dvDensW').strip()[:46]!r})",
          page.locator("#dvDensW").is_visible())
    page.fill("#dvDens", "0,5"); page.wait_for_timeout(200)
    page.click("#dlgOk"); page.wait_for_timeout(800)
    na = page.evaluate("""(nm) => { const m = DATA.materials.find(x => x.name === nm);
        return {cost: m.costPerGram, dens: m.density, inv: m.inventory}; }""", zonder)
    check(f"100 ml at 0,5 g/ml is 50 g, so EUR 50 makes EUR 1 per gram ({na['cost']})",
          na["cost"] is not None and abs(na["cost"] - 1) < 0.0001)
    check(f"the density typed in the window is kept ({na['dens']})", na["dens"] == 0.5)
    check(f"and the amount is written with its unit ({na['inv']!r})", (na["inv"] or "").endswith(" ml"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    page.fill("#searchBox", ""); page.wait_for_timeout(300)

    # ---------- 3. build 260922i: the IFRA check has no dosage field any more ----------
    # it used to belong to one formula at a time; diluting a concentrate now happens in the formula itself
    page.fill("#searchBox", ""); page.click("#tabF"); page.wait_for_timeout(400)
    items = page.locator("#list .item")
    items.nth(0).click(); page.wait_for_timeout(500)
    page.click("#ifraBox summary"); page.wait_for_timeout(300)
    check("the IFRA check has no dosage field", page.locator("#ifraDose").count() == 0)
    check("and no dosage state behind it", page.evaluate("typeof IDOSE") == "undefined")

    # ---------- 4. Ctrl+Z does not run under an open dialog ----------
    items.nth(0).click(); page.wait_for_timeout(500)
    before = page.evaluate("DATA.formulas.length")
    page.click("#btnCopyF"); page.wait_for_timeout(400)
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    page.fill("#cpName", "Copy under a dialog"); page.click("#dlgOk"); page.wait_for_timeout(600)
    after = page.evaluate("DATA.formulas.length")
    check(f"the copy made under the dialog is kept ({before} → {after})", after == before + 1)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(500)
    items = page.locator("#list .item")

    # ---------- 5. Replace + Cancel leaves the line as it was ----------
    page.click("#tabF"); page.wait_for_timeout(300)
    items.nth(0).click(); page.wait_for_timeout(500)
    first = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === VIEW.id), v = f.versions[f.versions.length-1];
      return {id: v.lines[0].materialId, name: (DATA.materials.find(m => m.id === v.lines[0].materialId)||{}).name, dil: v.lines[0].dilutionPct}; })()""")
    other = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === VIEW.id), v = f.versions[f.versions.length-1];
      const cur = v.lines[0].dilutionPct ?? 100;
      const m = DATA.materials.find(m => m.id !== v.lines[0].materialId && (m.dilutions||[]).length && !(m.dilutions||[]).some(d => d.pct === cur));
      return m && m.name; })()""")
    undo_before = page.evaluate("UNDO.length")
    page.click("[data-repl='0']"); page.wait_for_timeout(400)
    page.fill("#rmNew", other); page.click("#dlgOk"); page.wait_for_timeout(500)
    check("the dilution dialog opens for a material without that dilution", page.locator("#dlg").is_visible() and "Change dilution" in page.text_content("#dlg"))
    page.click("#dlgCancel"); page.wait_for_timeout(500)
    back = page.evaluate("(() => { const f = DATA.formulas.find(x => x.id === VIEW.id), v = f.versions[f.versions.length-1]; return v.lines[0].materialId; })()")
    check(f"Cancel puts the old material back ({first['name']} → {other} → cancelled)", back == first["id"])
    check("and leaves no undo step behind", page.evaluate("UNDO.length") == undo_before)

    # ---------- 5b. build 260918e: Escape on the dilution window puts the picker back ----------
    keuze = page.evaluate("""() => { const s = document.querySelector("[data-dil='0']");
        if (!s) return null;
        const echt = s.value;
        s.value = "custom";                       // as the list stands after picking custom...
        const f = DATA.formulas.find(x => x.id === VIEW.id), v = f.versions[f.versions.length-1];
        const m = matById(v.lines[0].materialId) || {};
        const cur = v.lines[0].dilutionPct ?? 100;
        const d2 = (m.dilutions||[]).map(d => d.pct).find(p => p !== cur) || (cur === 1 ? 2 : 1);
        changeDilution(f, v, 0, d2);
        return echt; }""")
    page.wait_for_timeout(500)
    check("picking a dilution opens the method window", page.locator("#dlg").is_visible()
          and "Change dilution" in page.text_content("#dlg"))
    page.keyboard.press("Escape"); page.wait_for_timeout(600)
    check("Escape closes it", not page.locator("#dlg").is_visible())
    nu = page.evaluate("""() => { const s = document.querySelector("[data-dil='0']"); return s && s.value; }""")
    check(f"and the picker shows the dilution of the line again, not custom... ({nu!r} was {keuze!r})",
          nu == keuze and nu != "custom")

    # ---------- 6. a material used by a line just added cannot be deleted ----------
    unused = page.evaluate("""(() => { buildUsage();
      const m = DATA.materials.find(x => !(USAGE[x.id]||[]).length); return m && m.name; })()""")
    page.fill("#addMat", unused); page.wait_for_timeout(200)
    page.click("#btnAddLine"); page.wait_for_timeout(600)
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", unused); page.wait_for_timeout(400)
    page.click("#list .item"); page.wait_for_timeout(400)
    msgs.clear(); page.click("#btnDelMat"); page.wait_for_timeout(500)
    gone = page.evaluate(f"!DATA.materials.some(x => x.name === {unused!r})")
    check(f"the line just added counts as usage, so {unused} cannot be deleted ({msgs})",
          not gone and any("Cannot delete" in m for m in msgs))

    # ---------- 7. the number fields on a material page, and its grid ----------
    page.evaluate("""() => {
        const m = DATA.materials[0];
        m.ifraLimit = 0.005; m.costPerGram = 1234.5; m.density = 0.998;
        window.__mid = m.id; switchTab("M", m.id, null);
    }""")
    page.wait_for_timeout(500)
    vals = page.evaluate("""() => ({ifra: document.getElementById("mf_ifraLimit").value,
        cost: document.getElementById("mf_costPerGram").value,
        dens: document.querySelector('[data-f="density"]').value})""")
    check(f"an IFRA limit of 0.005 is not rounded to 0.01 ({vals})", vals["ifra"] == "0.005")
    check("a cost is filled without a thousands separator", vals["cost"] in ("1234.5", "1234,5"))
    check("and a density keeps its three decimals", vals["dens"] in ("0.998", "0,998"))
    page.fill('[data-f="supplier"]', "Somebody"); page.dispatch_event('[data-f="supplier"]', "change")
    page.wait_for_timeout(500)
    kept = page.evaluate("() => { const m = DATA.materials.find(x => x.id === window.__mid); return [m.ifraLimit, m.costPerGram, m.density]; }")
    check(f"editing another field does not round them away ({kept})", kept == [0.005, 1234.5, 0.998])
    grid = page.evaluate("""() => {
        const lab = document.querySelector('label[for="mf_ifraLimit"]').getBoundingClientRect();
        const inp = document.getElementById("mf_ifraLimit").getBoundingClientRect();
        const cl = document.querySelector('label[for="mf_costPerGram"]').getBoundingClientRect();
        const ci = document.getElementById("mf_costPerGram").getBoundingClientRect();
        const overlap = (a, b) => a.bottom > b.top + 1 && b.bottom > a.top + 1;
        return {sameRow: overlap(lab, inp), labelLeft: lab.left < inp.left,
                costSameRow: overlap(cl, ci), costLabelLeft: cl.left < ci.left};
    }""")
    check(f"the IFRA label sits beside its own field ({grid})", grid["sameRow"] and grid["labelLeft"])
    check("and so does the cost label, hint and all", grid["costSameRow"] and grid["costLabelLeft"])

    # ---------- the export keeps the weight it was given (build 260920b) ----------
    w = page.evaluate("""() => [wCsv(12.5), wCsv(0.0025), wCsv(0.0005), wCsv(0.0004), wCsv(0), wCsv(100.00005)]""")
    check(f"wCsv writes six decimals only where three would change the weight ({w})",
          w[0] == "12.500" and w[1] == "0.002500" and w[2] == "0.000500" and w[3] == "0.000400"
          and w[4] == "0.000" and w[5] == "100.000050")

    # ---------- Apply on a target total nobody typed changes nothing (build 260920b) ----------
    page.evaluate("""() => { SCALEOPEN = true;
        DATA.formulas.push({id:"f-round", name:"Rounding", category:"Uncategorised", versions:[{v:1, date:today(), lines:[
          {id:"r1", materialId:DATA.materials[0].id, dilutionPct:100, weightG:3.3333, remark:1},
          {id:"r2", materialId:DATA.materials[1].id, dilutionPct:100, weightG:96.66675, remark:1}]}]});
        buildUsage(); switchTab("F", "f-round", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    veld = page.locator("#scaleW").input_value()
    voor = page.evaluate("""() => DATA.formulas.find(x=>x.id==="f-round").versions[0].lines.map(l=>l.weightG)""")
    page.click("#btnApplyScale"); page.wait_for_timeout(700)
    na = page.evaluate("""() => DATA.formulas.find(x=>x.id==="f-round").versions[0].lines.map(l=>l.weightG)""")
    check(f"Apply on an untouched target total leaves every weight alone ({veld!r}: {voor} -> {na})", voor == na)
    page.fill("#scaleW", "200"); page.click("#btnApplyScale"); page.wait_for_timeout(700)
    tot = page.evaluate("""() => DATA.formulas.find(x=>x.id==="f-round").versions[0].lines.reduce((s,l)=>s+l.weightG,0)""")
    check(f"but a target you type is applied ({tot})", abs(tot - 200) < 1e-9)

    # ---------- staart 21 (bouw 260920l): een dilutie die wegrondt naar "0" ----------
    # twee regels met een factor tien verschil droegen hetzelfde opschrift, ook op de weegstaat
    page.evaluate("""() => {
      const m = DATA.materials[0];
      if (!(m.dilutions||[]).some(d => d.pct === 0.001)) m.dilutions.push({pct:0.001, date:today(), notes:""});
      if (!(m.dilutions||[]).some(d => d.pct === 0.0001)) m.dilutions.push({pct:0.0001, date:today(), notes:""});
      DATA.formulas.push({id:"f-spoor", name:"Spoortest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[{id:"s-1", materialId:m.id, dilutionPct:0.001, weightG:1, remark:1},
                                   {id:"s-2", materialId:m.id, dilutionPct:0.0001, weightG:1, remark:1}]}]});
      buildUsage(); switchTab("F", "f-spoor", {type:"v", idx:0}); }""")
    page.wait_for_timeout(700)
    opschrift = page.evaluate("""() => [...document.querySelectorAll("#content table.lines tbody tr")]
      .map(tr => (tr.querySelector("select.d") ? tr.querySelector("select.d").selectedOptions[0].textContent : tr.cells[2].textContent).trim())""")
    check(f"twee dilutiestappen onder 0,005 % lezen niet allebei “0%” ({opschrift})",
          len(set(opschrift)) == len(opschrift) and not any(x in ("0%", "0 %") for x in opschrift))
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-spoor"), it = f.versions[0];
        document.querySelector("#printArea").innerHTML = sheetHtml(f, it, it.lines); }""")
    blad = page.evaluate("""() => document.querySelector("#printArea").innerText""")
    check(f"en op de weegstaat evenmin ({[x for x in blad.split(chr(10)) if '%' in x][:2]})",
          "0,001%" in blad.replace(".", ",") and "0,0001%" in blad.replace(".", ","))
    page.evaluate("""() => { document.querySelector("#printArea").innerHTML = "";
        DATA.formulas = DATA.formulas.filter(x => x.id !== "f-spoor");
        const m = DATA.materials[0]; m.dilutions = (m.dilutions||[]).filter(d => d.pct > 0.005);
        buildUsage(); switchTab("F", null, null); }""")
    page.wait_for_timeout(400)
    check("een echte nul blijft gewoon 0", page.evaluate("""() => fmtS(0)""") == "0")

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
