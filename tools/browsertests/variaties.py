"""Live variations (build 260914c): the differences of a variation hang on the line of the base
version (material + its dilution there), not on the material alone or on a line number, and the
solvent correction scales with the base version. Also: a predilution made from a variation keeps
the content of the version it lands in.
Needs the local web server on port 8765 (see README)."""
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

# one formula, built straight into the data: material M at 100 % and at 10 %, plus ethanol
BUILD = """() => {
  DATA.materials.push(
    {id:"m-t1", name:"Testolide", category:"Test", pyramid:4, isSolvent:false,
     dilutions:[{pct:100,isBase:true},{pct:10}]},
    {id:"m-t2", name:"Tweede stof", category:"Test", pyramid:2, isSolvent:false,
     dilutions:[{pct:100,isBase:true},{pct:10}]},
    {id:"m-eth", name:"Ethanol test", category:"Solvents", pyramid:5, isSolvent:true,
     dilutions:[{pct:100,isBase:true}]});
  invalidateMats();
  DATA.formulas.push({id:"f-t", name:"Variatietest", category:"Uncategorised", created:today(), versions:[
    {v:1, date:today(), lines:[
      {materialId:"m-t1", dilutionPct:100, weightG:1, remark:1},
      {materialId:"m-t1", dilutionPct:10,  weightG:1, remark:1},
      {materialId:"m-t2", dilutionPct:100, weightG:1, remark:1},
      {materialId:"m-eth", dilutionPct:100, weightG:200, remark:1}]}],
    variations:[{id:"va-t", label:"live", frozen:false, date:today(), notes:"", dilutionOverrides:{}}]});
  markDirty();
  VIEW = {tab:"F", id:"f-t", sub:{type:"var", idx:0}}; HOMEVIEW = false; setTabs(); render();
}"""

SHOW = """() => { const f = DATA.formulas.find(x => x.id === "f-t"), va = f.variations[0];
  const L = variationLines(f, va);
  return {w: L.map(l => +(l.weightG||0).toFixed(3)), d: L.map(l => l.dilutionPct),
          marks: L.map(l => l.remark ?? null), total: +calc(L).totalW.toFixed(3),
          content: +calc(L).content.toFixed(4), short: !!L._solventShort}; }"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    errs = []; msgs = []
    page = ctx.new_page()
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1500)
    page.evaluate(BUILD); page.wait_for_timeout(600)
    check("the live variation shows the base version", page.evaluate(SHOW)["w"] == [1, 1, 1, 200])

    # ---------- 1. a dilution change hits one line, not every line of that material ----------
    page.select_option('[data-vardil="0"]', "10"); page.wait_for_timeout(500)
    check("the dilution dialog opens", "Change dilution" in page.text_content("#dlg"))
    page.click("#dlgOk"); page.wait_for_timeout(600)
    st = page.evaluate(SHOW)
    check(f"only the ticked line moved to 10 % ({st['w']}, dilutions {st['d']})",
          st["w"][0] == 10 and st["d"][0] == 10 and st["w"][1] == 1 and st["d"][1] == 10)
    check(f"the solvent gave the weight back, total unchanged ({st['total']})", abs(st["total"] - 203) < 0.01)
    check("the override carries the dilution of the base line in its key",
          page.evaluate("""(() => Object.keys(DATA.formulas.find(x => x.id === "f-t").variations[0].dilutionOverrides))()""") == ["m-t1|100"])

    # ---------- 2. Lower on two lines of the same material ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-t");
      f.variations[0].dilutionOverrides = {}; delete f.variations[0].solventDeltaG; delete f.variations[0].solventBaseC; render(); }""")
    page.wait_for_timeout(400)
    page.check('input.selCb[data-i="0"]'); page.check('input.selCb[data-i="1"]'); page.wait_for_timeout(200)
    page.click("#btnDilDown"); page.wait_for_timeout(700)
    st = page.evaluate(SHOW)
    check(f"Lower shifts both lines on their own dilution ({st['w']}, {st['d']})",
          st["w"][0] == 10 and st["d"][0] == 10 and st["w"][1] == 1 and st["d"][1] == 10)
    check(f"and the total stays put ({st['total']})", abs(st["total"] - 203) < 0.01)

    # ---------- 3. the solvent correction follows a rescaled base version ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-t");
      f.versions[0].lines.forEach(l => l.weightG = (l.weightG||0) * 0.1); markDirty(); render(); }""")
    page.wait_for_timeout(500)
    st = page.evaluate(SHOW)
    check(f"nothing goes negative ({st['w']})", all(w >= 0 for w in st["w"]) and not st["short"])
    check(f"everything scaled by a tenth ({st['total']})", abs(st["total"] - 20.3) < 0.01)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-t");
      f.versions[0].lines.forEach(l => l.weightG = (l.weightG||0) * 10); markDirty(); render(); }""")
    page.wait_for_timeout(500)
    check("and back again", abs(page.evaluate(SHOW)["total"] - 203) < 0.01)

    # ---------- 4. a colour mark stays on its own material ----------
    page.check('input.selCb[data-i="2"]'); page.wait_for_timeout(200)
    page.click('[data-mark="2"]'); page.wait_for_timeout(600)
    st = page.evaluate(SHOW)
    check(f"the mark sits on the third line ({st['marks']})", st["marks"][2] == 2)
    check("and is keyed by the line of the base version",
          page.evaluate("""(() => Object.keys(DATA.formulas.find(x => x.id === "f-t").variations[0].remarks))()""") == ["m-t2|100"])
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-t");
      f.versions[0].lines.splice(0, 1); markDirty(); render(); }""")
    page.wait_for_timeout(500)
    st = page.evaluate(SHOW)
    mat = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-t");
      return variationLines(f, f.variations[0]).map(l => l.materialId); })()""")
    marked = [mat[i] for i, m in enumerate(st["marks"]) if m == 2]
    check(f"after a line was removed from the base it is still on the same material ({marked})", marked == ["m-t2"])

    # ---------- 5. a predilution made in a variation keeps the content of the version ----------
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-t");
      f.versions[0].lines = [{materialId:"m-t1", dilutionPct:100, weightG:1, remark:1},
                             {materialId:"m-t2", dilutionPct:100, weightG:1, remark:1},
                             {materialId:"m-eth", dilutionPct:100, weightG:20, remark:1}];
      const va = f.variations[0]; va.dilutionOverrides = {}; delete va.remarks;
      delete va.solventDeltaG; delete va.solventBaseC; markDirty(); render(); }""")
    page.wait_for_timeout(500)
    v1c = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-t");
      return +calc(f.versions[0].lines).content.toFixed(4); })()""")
    page.select_option('[data-vardil="1"]', "10"); page.wait_for_timeout(500)
    page.click("#dlgOk"); page.wait_for_timeout(600)
    st = page.evaluate(SHOW)
    check(f"the variation shows the second material at 10 % ({st['w']}, {st['d']})", st["w"][1] == 10 and st["d"][1] == 10)
    page.check('input.selCb[data-i="0"]'); page.check('input.selCb[data-i="1"]'); page.wait_for_timeout(200)
    page.click("#btnPredil"); page.wait_for_timeout(600)
    check("the predilution dialog names the replacement weight", "predil line of" in page.text_content("#dlg"))
    page.click("#dlgOk"); page.wait_for_timeout(900)
    v2 = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-t"), v = f.versions[f.versions.length-1];
      const pl = v.lines.find(l => (matById(l.materialId)||{}).category === "Predils");
      return {n: f.versions.length, content: +calc(v.lines).content.toFixed(4),
              w: pl && +pl.weightG.toFixed(3), dil: pl && pl.dilutionPct}; })()""")
    check(f"a new version was made ({v2['n']} versions)", v2["n"] == 2)
    check(f"with the same content as v1 ({v1c} → {v2['content']})", abs(v2["content"] - v1c) < 0.0005)
    check(f"and a predil line of 11 g at 18.18 % ({v2['w']} g, {v2['dil']} %)",
          abs(v2["w"] - 11) < 0.01 and abs(v2["dil"] - 18.1818) < 0.01)
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)
    check("one undo takes the predilution back",
          page.evaluate("""(() => DATA.formulas.find(x => x.id === "f-t").versions.length)()""") == 1
          and page.evaluate("!DATA.materials.some(m => m.category === 'Predils')"))

    check("no page errors", not errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
