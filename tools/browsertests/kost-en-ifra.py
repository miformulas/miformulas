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

    # ---------- 2b. build 260918e: the preview names the smallest line you will have to weigh ----------
    page.evaluate("""() => { VIEW = {tab:"F", id:"f-k", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(600)
    page.check('input.selCb[data-i="0"]'); page.check('input.selCb[data-i="1"]'); page.wait_for_timeout(300)
    page.click("#btnPredil"); page.wait_for_timeout(600)
    prev1 = page.text_content("#pdPrev").replace(",", ".")
    check(f"the preview names the smallest line in grams, like every other weight ({prev1!r})",
          "smallest line 0.010 g" in prev1 and "mg" not in prev1)
    page.fill("#pdK", "100"); page.wait_for_timeout(400)
    prev2 = page.text_content("#pdPrev").replace(",", ".")
    check(f"and it follows the batch factor ({prev2!r})", "smallest line 1.000 g" in prev2 and "mg" not in prev2)
    page.click("#dlgCancel"); page.wait_for_timeout(400)
    page.evaluate("""() => render()"""); page.wait_for_timeout(400)
    check("the ticks are gone again",
          page.evaluate("""() => document.querySelectorAll("input.selCb:checked").length""") == 0)

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

    # ---------- 3b. bouw 260920l: de dosering staat op de volledige inhoud, solventen inbegrepen ----------
    # IFRA-limieten gelden in het eindproduct, en dat is alles wat in de fles zit: de tabel rekent met
    # abs % en een aangevinkt solvent staat er gewoon in, met zijn eigen percentage.
    page.evaluate("""() => {
      const a = DATA.materials.find(m => m.id === "m-a"), bm = DATA.materials.find(m => m.id === "m-b");
      a.ifraLimit = 99; bm.ifraLimit = 99;                       // nagekeken, geen beperking
      const e = DATA.materials.find(m => m.id === "m-e");
      e.ifraLimit = 0.681; e.name = "Benzylbenzoaat (drager)";   // een solvent met een echte limiet
      invalidateMats(); IDOSE = null; IFRAOPEN = true; markDirty(); render(); }""")
    page.wait_for_timeout(600)
    panel = page.text_content("#ifraBox")
    kop = page.text_content("#ifraBox summary")
    check(f"het solvent staat in de tabel zelf, met zijn limiet ({page.locator('#ifraSolv').count()} apart blok)",
          page.locator("#ifraSolv").count() == 0
          and "Benzylbenzoaat (drager)" in page.text_content("#ifraBox table") and "0,681" in panel.replace(".", ","))
    rij = page.evaluate("""() => { const tr = [...document.querySelectorAll("#ifraBox table tbody tr")]
        .find(t => t.cells[0].textContent.includes("Benzylbenzoaat"));
      return tr ? [...tr.cells].map(td => td.textContent.trim()) : null; }""")
    check(f"met 89,99 % van het eindproduct, zijn gewichtsaandeel ({rij})",
          rij and rij[1].replace(",", ".").startswith("89.99"))
    check(f"en het kopje telt het mee ({kop!r})", "1 over limit" in kop)
    veld = page.evaluate("""() => document.querySelector("#ifraDose").value""")
    check(f"de dosering staat standaard op 100 % ({veld!r})", veld.replace(",", ".").startswith("100"))
    check("met de uitleg dat deze formule zelf het eindproduct is",
          "solvents included, is the finished product" in panel)

    # de rekening: abs % maal de dosering, niet rel %
    page.evaluate("""() => { const a = DATA.materials.find(m => m.id === "m-a"); a.ifraLimit = 5;
      IDOSE = null; markDirty(); render(); }""")
    page.wait_for_timeout(500)
    rijA = page.evaluate("""() => { const tr = [...document.querySelectorAll("#ifraBox table tbody tr")]
        .find(t => t.cells[0].textContent.includes("Kost A"));
      return tr ? [...tr.cells].map(td => td.textContent.trim()) : null; }""")
    check(f"Kost A staat op 10 g van 100 g, dus 10 % van het eindproduct ({rijA})",
          rijA and rijA[1].replace(",", ".").startswith("10.0"))
    page.fill("#ifraDose", "50"); page.dispatch_event("#ifraDose", "change"); page.wait_for_timeout(500)
    rijA2 = page.evaluate("""() => { const tr = [...document.querySelectorAll("#ifraBox table tbody tr")]
        .find(t => t.cells[0].textContent.includes("Kost A"));
      return tr ? [...tr.cells].map(td => td.textContent.trim()) : null; }""")
    check(f"gaat de hele formule voor 50 % in het product, dan is dat 5 % ({rijA2})",
          rijA2 and rijA2[1].replace(",", ".").startswith("5.0"))
    page.evaluate("""() => { IDOSE = null; const a = DATA.materials.find(m => m.id === "m-a"); a.ifraLimit = 99;
      const e = DATA.materials.find(m => m.id === "m-e"); e.ifraLimit = null; e.name = "Ethanol kost";
      invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(500)

    # staart 8: een regel naar een gewist materiaal telt wel in de gewichten, maar is niets om na te kijken
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-k");
      f.versions[0].lines.push({id:"l-weg", materialId:"m-bestaat-niet", dilutionPct:100, weightG:1, remark:1});
      markDirty(); render(); }""")
    page.wait_for_timeout(500)
    panel = page.text_content("#ifraBox")
    check(f"een regel naar een gewist materiaal wordt apart gemeld ({page.locator('#ifraGone').count()})",
          page.locator("#ifraGone").count() == 1 and "no longer exists" in panel)
    check(f"en staat niet meer als “undefined” bij de niet-nagekeken materialen ({panel[:0]})",
          "undefined" not in panel)
    page.evaluate("""() => { const f = DATA.formulas.find(x => x.id === "f-k");
      f.versions[0].lines = f.versions[0].lines.filter(l => l.id !== "l-weg"); markDirty(); render(); }""")
    page.wait_for_timeout(400)

    # ---------- 3c. niets nagekeken is geen vrijgave ----------
    page.evaluate("""() => { for (const m of DATA.materials) m.ifraLimit = null;
      invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(600)
    kop = page.text_content("#ifraBox summary")
    check(f"het dichtgeklapte kopje zegt dat er niets nagekeken is ({kop!r})", "nothing verified yet" in kop)
    check("en binnenin staat dezelfde zin, niet 'no restricted materials'",
          "carries an IFRA limit yet" in page.text_content("#ifraBox") and "No restricted materials present" not in page.text_content("#ifraBox"))
    page.evaluate("""() => { const a = DATA.materials.find(m => m.id === "m-a"); a.ifraLimit = 99;
      invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(500)
    check("één nagekeken materiaal maakt er weer 'no restricted materials' van",
          "no restricted materials" in page.text_content("#ifraBox summary"))
    page.evaluate("""() => { for (const m of DATA.materials) m.ifraLimit = null;
      const e = DATA.materials.find(m => m.id === "m-a"); e.isSolvent = true;   // alles solvent: ook dan geen vrijgave
      invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(600)
    check(f"ook een formule van louter solventen krijgt geen vrijgave ({page.text_content('#ifraBox summary').strip()!r})",
          "nothing verified yet" in page.text_content("#ifraBox summary"))
    page.evaluate("""() => { const e = DATA.materials.find(m => m.id === "m-a"); e.isSolvent = false;
      invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(400)

    # ---------- 3d. Deduct base rekent met de basisdilutie ----------
    page.evaluate("""() => {
      DATA.materials.push({id:"m-st", name:"Voorraadstof", category:"Test", pyramid:2, isSolvent:false,
        dilutions:[{pct:10, isBase:true}, {pct:1}], stockEvents:[{t:"take", date: today(), g: 100}]});
      invalidateMats(); markDirty(); VIEW = {tab:"M", id:"m-st", sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    page.wait_for_timeout(700)
    page.fill("#stDilPct", "1"); page.fill("#stDilG", "50")
    page.click("#btnDil"); page.wait_for_timeout(700)
    st = page.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-st");
        const e = m.stockEvents[m.stockEvents.length - 1];
        return {g: e.g, base: e.base, qty: stockCalc(m).qty}; }""")
    check(f"50 g van 1 % uit een basis van 10 % kost 5 g, niet 0,5 g ({st})",
          abs(st["g"] - 5) < 0.0001 and st["base"] == 10 and abs(st["qty"] - 95) < 0.0001)
    check("en de regel in het logboek noemt de basis", "base 10%" in page.text_content("#content"))
    msgs.clear()
    page.fill("#stDilPct", "50"); page.fill("#stDilG", "10")
    page.click("#btnDil"); page.wait_for_timeout(600)
    check(f"een dilutie sterker dan de basis wordt geweigerd ({[m[:45] for m in msgs]})",
          any("cannot be made out of" in m for m in msgs)
          and page.evaluate("""() => DATA.materials.find(x => x.id === "m-st").stockEvents.length""") == 2)

    # ---------- 3e. de laatste dilutie blijft staan ----------
    msgs.clear()
    page.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-st"); m.dilutions = [{pct: 10, isBase: true}];
        invalidateMats(); markDirty(); render(); }""")
    page.wait_for_timeout(600)
    page.click("[data-deldil='0']"); page.wait_for_timeout(600)
    check(f"de laatste dilutie kan niet weg ({[m[:45] for m in msgs]})",
          any("without a dilution" in m for m in msgs)
          and page.evaluate("""() => DATA.materials.find(x => x.id === "m-st").dilutions.length""") == 1)

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
    ctx.close()

    # ---------- 7. a predilution switches the IFRA check off (build 260920a) ----------
    # The app cannot look inside a predilution: its materials are text in the description, not lines. Before
    # 260920a the panel simply stopped counting them, so a formula three times over the limit read "no
    # restricted materials" right after Create predilution…
    ctx = b.new_context(viewport={"width": 1280, "height": 950})
    errs4 = []; msgs4 = []
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs4.append(str(e)))
    pg.on("dialog", lambda d: (msgs4.append(d.message), d.accept()))
    pg.route("**/data.php*", lambda r: r.fulfill(status=404, body="no"))
    pg.goto(URL); pg.wait_for_timeout(700)
    pg.click("#btnStarter"); pg.wait_for_timeout(1600)
    pg.evaluate("""() => {
        IFRAOPEN = true;
        const mk = (id,n,lim,sol) => ({id, name:n, category:"Uncategorised", ifraLimit:lim, isSolvent:!!sol,
                                       dilutions:[{pct:100, isBase:true}], aliases:"", cas:""});
        DATA.materials.push(mk("q1","Restricted A",0.5), mk("q2","Restricted B",1), mk("q3","EtOH test",99,true));
        invalidateMats();
        DATA.formulas.push({id:"f-q", name:"IFRA test", category:"Uncategorised", versions:[{v:1, date:today(), lines:[
            {id:"a1", materialId:"q1", dilutionPct:100, weightG:4, remark:1},
            {id:"a2", materialId:"q2", dilutionPct:100, weightG:3, remark:1},
            {id:"a3", materialId:"q3", dilutionPct:100, weightG:93, remark:1}]}]});
        VIEW = {tab:"F", id:"f-q", sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    pg.wait_for_timeout(700)
    head = pg.text_content("#ifraBox summary")
    check(f"without a predilution the check runs ({head!r})", "over limit" in head)
    # a dosage of 0 or below used to read every material as within limits (build 260920b)
    for bad in ("0", "-5"):
        pg.fill("#ifraDose", bad); pg.locator("#ifraDose").press("Tab"); pg.wait_for_timeout(600)
        head = pg.text_content("#ifraBox summary")
        check(f"a dosage of {bad} is refused and the verdict stands ({head!r})", "over limit" in head)
    pg.fill("#ifraDose", "20"); pg.locator("#ifraDose").press("Tab"); pg.wait_for_timeout(600)
    head = pg.text_content("#ifraBox summary")
    check(f"a dosage above 0 is still taken ({head!r})", "over limit" in head or "within limits" in head)
    pg.evaluate("""() => { document.querySelectorAll("#content input[type=checkbox][data-i]").forEach(cb => {
        if (+cb.dataset.i <= 1){ cb.checked = true; cb.dispatchEvent(new Event("change", {bubbles:true})); } }); }""")
    pg.wait_for_timeout(400)
    pg.click("#btnPredil"); pg.wait_for_timeout(700)
    pg.click("#dlgOk"); pg.wait_for_timeout(1400)
    head = pg.text_content("#ifraBox summary"); body = pg.text_content("#ifraBox")
    check(f"with a predilution in the version the check is off and says so ({head!r})", "off (predilution" in head)
    check("the panel names the predilution and the way to check it anyway",
          "does not look inside" in body and "Predilutions" in body)
    check("no verdict and no dosage field while it is off",
          "no restricted materials" not in body and "within limits" not in body and pg.locator("#ifraDose").count() == 0)
    check("the predilution material carries the marker",
          pg.evaluate("""() => { const m = DATA.materials.find(x => x.isPredil); return !!m && m.category === "Predils"; }"""))
    pg.evaluate("""() => { const pf = DATA.formulas.find(f => f.category === "Predilutions");
        VIEW = {tab:"F", id:pf.id, sub:{type:"v", idx:0}}; HOMEVIEW = false; setTabs(); render(); }""")
    pg.wait_for_timeout(600)
    head = pg.text_content("#ifraBox summary")
    check(f"the predilution formula itself is still checked ({head!r})", "over limit" in head)
    # ---------- staart 6 (bouw 260920l): Delivered vraagt of de oude voorraad op is ----------
    pg.evaluate("""() => {
      DATA.materials.push({id:"m-vrd", name:"Voorraadtest", category:"Test", pyramid:3, isSolvent:false,
        dilutions:[{pct:100, isBase:true}], stockEvents:[{t:"take", date:"2026-09-01", g:40}]});
      invalidateMats();
      (DATA.orderList ||= []).push({id:"o-vrd", materialId:"m-vrd", name:"Voorraadtest", added:today()});
      markDirty(); VIEW = {tab:"T", id:null, sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    pg.wait_for_timeout(600)
    rij = pg.evaluate("""() => [...document.querySelectorAll("[data-odeliv]")].findIndex(b =>
      b.closest("tr").textContent.includes("Voorraadtest"))""")
    pg.fill(f"[data-oamt='{rij}']", "10"); pg.locator(f"[data-oamt='{rij}']").press("Tab"); pg.wait_for_timeout(300)
    pg.click(f"[data-odeliv='{rij}']"); pg.wait_for_timeout(600)
    check(f"Delivered vraagt of de oude voorraad op is, met de stand erbij ({pg.locator('#dvFresh').count()})",
          pg.locator("#dvFresh").count() == 1 and not pg.locator("#dvFresh").is_checked()
          and "40" in pg.text_content("#dlg"))
    pg.click("#dlgOk"); pg.wait_for_timeout(900)
    na = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-vrd"); return stockCalc(m).qty; }""")
    check(f"laat je het vakje uit, dan telt de aankoop erbij: 40 + 10 = 50 g ({na})", abs(na - 50) < 1e-9)
    pg.keyboard.press("Control+z"); pg.wait_for_timeout(700)
    terug = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-vrd");
      return {q: stockCalc(m).qty, order: (DATA.orderList||[]).some(o => o.id === "o-vrd")}; }""")
    check(f"Ctrl+Z zet de voorraad en de bestelregel terug ({terug})", abs(terug["q"] - 40) < 1e-9 and terug["order"])
    pg.evaluate("""() => { VIEW = {tab:"T", id:null, sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    pg.wait_for_timeout(500)
    rij = pg.evaluate("""() => [...document.querySelectorAll("[data-odeliv]")].findIndex(b =>
      b.closest("tr").textContent.includes("Voorraadtest"))""")
    pg.fill(f"[data-oamt='{rij}']", "10"); pg.locator(f"[data-oamt='{rij}']").press("Tab"); pg.wait_for_timeout(300)
    pg.click(f"[data-odeliv='{rij}']"); pg.wait_for_timeout(600)
    pg.check("#dvFresh"); pg.click("#dlgOk"); pg.wait_for_timeout(900)
    vers = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-vrd");
      return {q: stockCalc(m).qty, ev: (m.stockEvents||[]).map(e => e.t + ":" + e.g + (e.note ? " " + e.note : ""))}; }""")
    check(f"vink je het aan, dan begint het boek opnieuw: 10 g ({vers})", abs(vers["q"] - 10) < 1e-9)
    check(f"met een stocktake van 0 g en de reden erbij ({vers['ev'][-2:]})",
          any(e.startswith("take:0") and "used up" in e for e in vers["ev"]))
    regels = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-vrd");
      return (m.stockEvents||[]).map(e => evLabel(e)); }""")
    check(f"en het boek zegt het ook in woorden ({regels[-2:]})",
          any("stocktake" in r and "used up" in r for r in regels))

    # ---------- A3 (bouw 260922a): Delivered weigert een negatieve prijs ----------
    # De materiaalpagina en de CSV-invoer weigeren een negatieve prijs al, want ze maakt de kost van elke
    # formule met dat materiaal negatief. Delivered was de ene weg naar binnen.
    pg.evaluate("""() => {
      DATA.materials.push({id:"m-neg", name:"Negatief", category:"Test", pyramid:3, isSolvent:false,
        dilutions:[{pct:100, isBase:true}]});
      invalidateMats();
      (DATA.orderList ||= []).push({id:"o-neg", materialId:"m-neg", name:"Negatief", added:today()});
      markDirty(); VIEW = {tab:"T", id:null, sub:null}; HOMEVIEW = false; setTabs(); render(); }""")
    pg.wait_for_timeout(600)
    rij = pg.evaluate("""() => [...document.querySelectorAll("[data-odeliv]")].findIndex(b =>
      b.closest("tr").textContent.includes("Negatief"))""")
    pg.fill(f"[data-oamt='{rij}']", "10"); pg.locator(f"[data-oamt='{rij}']").press("Tab"); pg.wait_for_timeout(300)
    pg.click(f"[data-odeliv='{rij}']"); pg.wait_for_timeout(600)
    pg.fill("#dvAmt", "10"); pg.fill("#dvPrice", "-50")
    n0 = len(msgs4)
    pg.click("#dlgOk"); pg.wait_for_timeout(700)
    gezegd = msgs4[n0:]
    check(f"een negatieve prijs wordt geweigerd, met de reden ({gezegd[:1]})",
          any("price cannot be negative" in m for m in gezegd))
    check("het venster blijft open, dus je kan het verbeteren", pg.locator("#dvPrice").count() == 1)
    kost = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-neg"); return m.costPerGram; }""")
    check(f"en er staat geen negatieve kost per gram op het materiaal ({kost})", not (kost != None and kost < 0))
    pg.fill("#dvPrice", "50"); pg.click("#dlgOk"); pg.wait_for_timeout(800)
    kost2 = pg.evaluate("""() => { const m = DATA.materials.find(x => x.id === "m-neg"); return m.costPerGram; }""")
    check(f"met een gewone prijs gaat het wel door ({kost2} EUR/g)", abs((kost2 or 0) - 5) < 1e-9)

    check("no page errors", not errs4)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
