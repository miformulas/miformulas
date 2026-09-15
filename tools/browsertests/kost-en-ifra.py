"""Cost per gram of pure material, the IFRA panel with 0 and with a figure below zero, a file that
is not a data file, a materials library with rubbish in it, and a server without a data file
(build 260914d). Needs the local web server on port 8765 (see README)."""
import json
from playwright.sync_api import sync_playwright

URL = "http://localhost:8765/index.html"
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

def start(ctx, errs, msgs, extra=""):
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    if extra: pg.add_init_script(extra)
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.click("#btnStarter"); pg.wait_for_timeout(1500)
    return pg

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    errs = []; msgs = []
    page = start(ctx, errs, msgs)

    # ---------- 1. Delivered: the price lands per gram of pure material ----------
    page.evaluate("""() => {
      DATA.materials.push({id:"m-dil", name:"Gekochte verdunning", category:"Test", pyramid:3, isSolvent:false,
        dilutions:[{pct:10, isBase:true}, {pct:100}]});
      invalidateMats();
      (DATA.orderList ||= []).push({id:"o-1", materialId:"m-dil", name:"Gekochte verdunning", added:today()});
      markDirty(); VIEW = {tab:"T", id:null, sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(500)
    page.fill("[data-oamt='0']", "10"); page.locator("[data-oamt='0']").press("Tab"); page.wait_for_timeout(300)
    page.fill("[data-oprice='0']", "5"); page.locator("[data-oprice='0']").press("Tab"); page.wait_for_timeout(300)
    page.click("[data-odeliv='0']"); page.wait_for_timeout(500)
    check("Delivered explains the base dilution", "base dilution of 10 %" in page.text_content("#dlg"))
    page.click("#dlgOk"); page.wait_for_timeout(700)
    cpg = page.evaluate("""(() => (DATA.materials.find(m => m.id === "m-dil")||{}).costPerGram)()""")
    check(f"10 g at 10 % for € 5 is € 5 per gram of pure material ({cpg})", abs(cpg - 5) < 0.0001)
    cost = page.evaluate("""(() => calc([{materialId:"m-dil", dilutionPct:10, weightG:2}]).totalCost)()""")
    check(f"so two grams of that dilution cost € 1 ({cost})", abs(cost - 1) < 0.0001)

    # ---------- 2. a predilution does not change what the formula costs ----------
    page.evaluate("""() => {
      DATA.materials.push(
        {id:"m-a", name:"Kost A", category:"Test", pyramid:2, isSolvent:false, costPerGram:1, dilutions:[{pct:100,isBase:true}]},
        {id:"m-b", name:"Kost B", category:"Test", pyramid:4, isSolvent:false, costPerGram:10, dilutions:[{pct:100,isBase:true},{pct:10}]},
        {id:"m-e", name:"Ethanol kost", category:"Solvents", pyramid:5, isSolvent:true, dilutions:[{pct:100,isBase:true}]});
      invalidateMats();
      DATA.formulas.push({id:"f-k", name:"Kosttest", category:"Uncategorised", created:today(), versions:[
        {v:1, date:today(), lines:[
          {materialId:"m-a", dilutionPct:100, weightG:10, remark:1},
          {materialId:"m-b", dilutionPct:10,  weightG:0.01, remark:1},
          {materialId:"m-e", dilutionPct:100, weightG:89.99, remark:1}]}]});
      markDirty(); VIEW = {tab:"F", id:"f-k", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    c1 = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-k");
      return +calc(f.versions[0].lines).totalCost.toFixed(4); })()""")
    page.check('input.selCb[data-i="1"]'); page.wait_for_timeout(200)
    page.click("#btnPredil"); page.wait_for_timeout(500)
    page.fill("#pdK", "100"); page.wait_for_timeout(300)
    page.click("#dlgOk"); page.wait_for_timeout(900)
    after = page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-k"), v = f.versions[f.versions.length-1];
      const pm = DATA.materials.find(m => m.category === "Predils");
      return {n: f.versions.length, cost: +calc(v.lines).totalCost.toFixed(4), pmCost: pm && pm.costPerGram, dil: pm && pm.dilutions[0].pct,
              inv: pm && pm.inventory, ifra: pm && ("ifraLimit" in pm)}; })()""")
    check(f"the new version costs the same as the old one ({c1} → {after['cost']})", abs(after["cost"] - c1) < 0.0005)
    check(f"the predilution material is priced per gram of pure material ({after['pmCost']} €/g at {after['dil']} %)",
          after["pmCost"] is not None and abs(after["pmCost"] - 10.0) < 0.5)
    check(f"and records the amount made and an empty IFRA limit (build 260915; inventory {after['inv']!r})",
          isinstance(after["inv"], str) and after["inv"].endswith(" g") and after["ifra"])
    page.click("#content h2"); page.keyboard.press("Control+z"); page.wait_for_timeout(600)

    # ---------- 3. IFRA: 0 is prohibited, below zero is not a limit ----------
    page.evaluate("""() => {
      const a = DATA.materials.find(m => m.id === "m-a"), bm = DATA.materials.find(m => m.id === "m-b");
      a.ifraLimit = 0; bm.ifraLimit = -1;
      IDOSE = null; IFRAOPEN = true; markDirty(); render(); }""")
    page.wait_for_timeout(600)
    panel = page.text_content("#ifraBox")
    check(f"a limit of 0 reads as prohibited", "prohibited" in panel and "not allowed" in panel)
    check("a figure below zero counts as not yet verified",
          "Not yet verified" in panel and "Kost B" in panel.split("Not yet verified")[1])
    check("and it is not counted as over limit",
          page.evaluate("""(() => { const f = DATA.formulas.find(x => x.id === "f-k"), v = f.versions[0];
            const K = calc(v.lines); const agg = new Map();
            for (const r of K.rows){ if (r.m.isSolvent) continue; const e = agg.get(r.m.id) || {m:r.m, rel:0}; e.rel += r.rel||0; agg.set(r.m.id, e); }
            return [...agg.values()].filter(e => e.m.ifraLimit != null && e.m.ifraLimit >= 0 && e.m.ifraLimit < 99).length; })()""") == 1)

    # ---------- 4. a materials library with rubbish in it ----------
    LIB = {"type": "miformulas-materials", "name": "Rommel", "version": "1", "materials": [
        {"name": "Goede stof", "aliases": "Alias een; Alias twee", "cas": 12345, "pyramid": "3",
         "ifraLimit": "0.5", "odour": "musky; warm", "use": {"mean": "1", "n": 1}},
        {"cas": "111-11-1"},                      # no name: must be dropped
        {"name": "   "},                          # empty name: dropped as well
    ]}
    page.evaluate("""pkg => { const p = normLibrary(pkg); setMaterialList(p); render(); }""", LIB)
    page.wait_for_timeout(400)
    lib = page.evaluate("""(() => { const m = DATA.materialList.materials;
      return {n: m.length, a: m[0].aliases, pyr: m[0].pyramid, ifra: m[0].ifraLimit, odour: m[0].odour, cas: m[0].cas}; })()""")
    check(f"entries without a name are dropped ({lib['n']} left)", lib["n"] == 1)
    check(f"aliases and odour become lists, numbers become numbers ({lib})",
          lib["a"] == ["Alias een", "Alias twee"] and lib["odour"] == ["musky", "warm"]
          and lib["pyr"] == 3 and abs(lib["ifra"] - 0.5) < 1e-9 and lib["cas"] == "12345")
    page.click("#tabM"); page.wait_for_timeout(300)
    page.fill("#searchBox", "Goede stof"); page.wait_for_timeout(500)
    check("and the search still works", "Not in your inventory" in page.text_content("#list"))
    page.click("#list button[data-add]"); page.wait_for_timeout(600)
    added = page.evaluate("""(() => { const m = DATA.materials.find(x => x.name === "Goede stof");
      return m && {pyr: m.pyramid, ifra: m.ifraLimit, d: m.description}; })()""")
    check(f"the facts land as numbers on the new material ({added})",
          added and added["pyr"] == 3 and abs(added["ifra"] - 0.5) < 1e-9 and "1 formula" in added["d"])
    page.fill("#searchBox", ""); page.wait_for_timeout(200)
    check("no page errors so far", not errs)
    ctx.close()

    # ---------- 5. a file that is not a data file ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    errs2 = []; msgs2 = []
    pg = start(ctx, errs2, msgs2, """
      window.__file = JSON.stringify({type: "miformulas-materials", materials: [{name: "X"}]});
      function FakeHandle(name){ this.name = name; this.kind = "file"; this.__fake = true; }
      FakeHandle.prototype.queryPermission = async () => "granted";
      FakeHandle.prototype.requestPermission = async () => "granted";
      FakeHandle.prototype.getFile = async function(){ return new File([window.__file], this.name); };
      FakeHandle.prototype.createWritable = async () => ({ write: async s => { window.__file = s; }, close: async () => {} });
      window.showOpenFilePicker = async () => [new FakeHandle("iets.json")];
    """)
    before = pg.evaluate("DATA.formulas.length")
    msgs2.clear()
    pg.evaluate("""() => { (async () => { const [h] = await window.showOpenFilePicker(); await loadFromHandle(h); })(); }""")
    pg.wait_for_timeout(900)
    check(f"opening a library as data file is refused ({msgs2})",
          any("not a miFormulas data file" in m for m in msgs2))
    check("and the data in the app is untouched", pg.evaluate("DATA.formulas.length") == before)
    check("with no page errors", not errs2)
    ctx.close()

    # ---------- 6. a server that has no data file yet ----------
    ctx = b.new_context(viewport={"width": 1200, "height": 900})
    errs3 = []; msgs3 = []
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs3.append(str(e)))
    pg.on("dialog", lambda d: (msgs3.append(d.message), d.accept()))
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="not here")
             if r.request.method == "GET" else r.fulfill(status=200, body="{}", headers={"ETag": "E1"}))
    pg.add_init_script("""() => {}""")
    pg.goto(URL); pg.wait_for_timeout(600)
    pg.evaluate("""() => idb.set("serverUrl", "data.php")""")
    pg.goto(URL); pg.wait_for_timeout(1500)
    check("the app is in server mode", pg.evaluate("[REMOTE, SERVER_EMPTY]") == [True, True])
    check("the landing says the server is still empty", "has no data file yet" in pg.text_content("#landingHint"))
    check("and offers the starter set", pg.locator("#btnStarter").is_visible())
    pg.click("#btnStarter"); pg.wait_for_timeout(3400)
    check("which starts the app and writes it to the server",
          pg.evaluate("DATA && DATA.formulas.length") == 16
          and pg.locator("#saveState").inner_text().startswith("Saved"))
    check("no page errors", not errs3)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
