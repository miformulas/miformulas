"""Bouw 261019b: de materiaalpagina naar analogie met de formulapagina (kop in twee rijen met ⋯, de velden in twee kolommen,
de vier panelen twee aan twee), de herinnering aan de library in + New material (Get the latest library zonder het venster te
verliezen; Don’t remind me als vlag in het databestand; Remove the library zet ze ook), en de placeholder van Alternative names.
Draait op de lokale webserver (poort 8765, zie README)."""
import json, os
from playwright.sync_api import sync_playwright

URL = os.environ.get("MIF_URL", "http://localhost:8765/")
HERE = os.path.dirname(os.path.abspath(__file__))
GEPUB = os.path.join(HERE, "..", "..", "..", "miformulas-materials.json")
LIB = json.load(open(GEPUB, encoding="utf-8")) if os.path.exists(GEPUB) else {
    "type": "miformulas-materials", "name": "Kleine library", "version": "2026-10-19", "licence": "CC BY 4.0",
    "materials": [{"name": "Javanol", "aliases": ["Sandal Cyclopropane"], "cas": "198404-98-7", "category": "Woody - sandal", "pyramid": 4, "ifraLimit": 99}]}
ok = fail = 0
def check(name, cond):
    global ok, fail
    ok += bool(cond); fail += (not cond)
    print(("OK   " if cond else "FAIL ") + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1366, "height": 660})
    page = ctx.new_page()
    errs, msgs = [], []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.on("dialog", lambda d: (msgs.append(d.message), d.accept()))
    page.route("https://data.miformulas.com/**", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(LIB)))
    page.goto(URL); page.wait_for_timeout(800)
    page.click("#btnStarter"); page.wait_for_timeout(1200)
    page.add_style_tag(content="#storageHint{display:none!important}")
    box = lambda s: page.evaluate("s => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return r.width || r.height ? {x: r.x, y: r.y, w: r.width, h: r.height} : null; }", s)
    vis = lambda s: page.locator(s).count() > 0 and page.locator(s).first.is_visible()
    def klik(s):   # op een oudere bouw zonder dat element: een FAIL in plaats van een wachttijd van 30 s
        if vis(s): page.click(s); page.wait_for_timeout(150); return True
        check(f"{s} is er", False); return False
    txt = lambda s: (page.locator(s).first.text_content() or "") if page.locator(s).count() else ""
    def open_m(name):
        page.evaluate("n => { const m = DATA.materials.find(x => x.name === n); switchTab('M', m.id, null); }", name); page.wait_for_timeout(500)

    # ---------- 1. de kop in twee rijen ----------
    open_m("Geraniol")
    r1 = {s: box(s) for s in ("#content h2", "#btnToOrder", "#mMore summary")}
    check(f"eerste rij: de naam, Add to order list en ⋯ op één lijn, ⋯ rechts ({ {k: v and round(v['y']) for k, v in r1.items()} })",
          all(r1.values()) and max(abs(r1["#content h2"]["y"] + r1["#content h2"]["h"] / 2 - (v["y"] + v["h"] / 2)) for v in r1.values()) < 6
          and r1["#mMore summary"]["x"] > r1["#btnToOrder"]["x"])
    meta = txt(".fMeta")
    links = page.evaluate("() => [...document.querySelectorAll('.fMeta .fLinks a.lookup')].map(a => a.textContent.trim())")
    check(f"tweede rij: CAS, categorie, starter set en de drie opzoeklinks ({meta.strip()[:60]!r}, {links})",
          "106-24-1" in meta and "Flowers - red" in meta and "starter set" in meta and [l.split()[0] for l in links] == ["TGSC", "Olfactorian", "IFRA"])
    check("Delete material staat niet in zicht", page.locator("#btnDelMat").count() == 1 and not vis("#btnDelMat"))
    klik("#mMore summary")
    st = page.evaluate("() => { const b = document.querySelector('#btnDelMat'); return [getComputedStyle(b).color, !!b.closest('#mMore .menuPop')]; }")
    check(f"⋯ opent het menu met Delete material, in rood ({st})", vis("#btnDelMat") and st[1] and st[0] == "rgb(196, 47, 31)")
    page.keyboard.press("Escape"); page.wait_for_timeout(150)
    check("Escape sluit het", not vis("#btnDelMat"))

    # ---------- 2. de velden in twee kolommen ----------
    f = {s: box(s) for s in ("#mf_name", "#mf_supplier", "#mf_ifraLimit", "#mf_inventory")}
    check("Name en Supplier naast elkaar, IFRA links en Amount purchased rechts",
          all(f.values()) and abs(f["#mf_name"]["y"] - f["#mf_supplier"]["y"]) < 6 and f["#mf_supplier"]["x"] > f["#mf_name"]["x"] + f["#mf_name"]["w"]
          and f["#mf_inventory"]["x"] > f["#mf_ifraLimit"]["x"] + f["#mf_ifraLimit"]["w"])
    ph = page.get_attribute("#mf_aliases", "placeholder") or ""
    check(f"de placeholder van Alternative names zegt hoe ({ph!r})", ph == "Use a semicolon to separate names, e.g. Ambroxan; Ambrofix.")
    t = page.evaluate("() => { const b = document.querySelector('.fblocks'); return b ? b.getBoundingClientRect().top - document.querySelector('#content').getBoundingClientRect().top : 9999; }")
    check(f"de panelen beginnen binnen het venster ({t:.0f} px onder de bovenkant)", t < 420)

    # ---------- 3. de vier panelen ----------
    ids = page.evaluate("() => [...document.querySelectorAll('.fblocks > details')].map(d => d.id)")
    check(f"vier panelen in deze volgorde ({ids})", ids == ["dilBox", "stockBox", "descBox", "useBox"])
    pb = {s: box(s) for s in ("#dilBox", "#stockBox", "#descBox", "#useBox")}
    check("twee aan twee op 1366 px", all(pb.values()) and abs(pb["#dilBox"]["y"] - pb["#stockBox"]["y"]) < 2 and abs(pb["#descBox"]["y"] - pb["#useBox"]["y"]) < 2
          and pb["#descBox"]["y"] > pb["#dilBox"]["y"])
    opn = page.evaluate("() => ['dilBox','stockBox','descBox','useBox'].map(i => document.getElementById(i)?.open)")
    check(f"Dilutions en Usage open, Stock en Description dicht ({opn})", opn == [True, False, False, True])
    sums = page.evaluate("() => [...document.querySelectorAll('.fblocks > details > summary')].map(s => s.textContent.trim())")
    check(f"de titels noemen de stand ({sums})", len(sums) == 4 and sums[0].startswith("Dilutions – 100% base") and sums[1] == "Stock – not tracked"
          and sums[2] == "Description – empty" and sums[3].startswith("Usage in formulas – ") and sums[3].endswith("formulas"))
    cs = page.evaluate("() => { const s = document.querySelector('#dilBox summary'); if (!s) return null; const c = getComputedStyle(s); return [c.textTransform, c.color]; }")
    check(f"de titels zijn gewoon, in de kleur van de tekst ({cs})", cs == ["none", "rgb(33, 42, 51)"])
    klik("#descBox summary"); page.fill('textarea[data-f="description"]', "fresh rosy"); page.press('textarea[data-f="description"]', "Tab"); page.wait_for_timeout(300)
    s2 = txt("#descBox summary").strip()
    check(f"met een beschrijving blijft het paneel open en zegt de titel niets meer ({s2!r})", s2 == "Description –" or s2 == "Description" or s2.startswith("Description"))
    check("Description open na de render", page.evaluate("!!document.querySelector('#descBox')?.open"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    page.set_viewport_size({"width": 800, "height": 660}); page.wait_for_timeout(300)
    f = {s: box(s) for s in ("#mf_name", "#mf_supplier")}; pb = {s: box(s) for s in ("#dilBox", "#stockBox")}
    check("op 800 px één kolom, velden en panelen", all(f.values()) and all(pb.values()) and f["#mf_supplier"]["y"] > f["#mf_name"]["y"] + 20 and pb["#stockBox"]["y"] > pb["#dilBox"]["y"] + 20)
    page.set_viewport_size({"width": 1366, "height": 660}); page.wait_for_timeout(200)

    # ---------- 4. to order: Mark as owned in de kop ----------
    page.evaluate("() => { const m = DATA.materials.find(x => x.name === 'Geraniol'); m.wishlist = true; render(); }"); page.wait_for_timeout(300)
    check("een materiaal to order dat niet op de lijst staat: Mark as owned in de kop, geen Add to order list",
          vis("#btnOwned") and page.locator("#btnToOrder").count() == 0 and "to order" in txt(".fMeta"))
    klik("#btnOwned"); page.wait_for_timeout(200)
    check("Mark as owned werkt", not page.evaluate("DATA.materials.find(x => x.name === 'Geraniol').wishlist") and vis("#btnToOrder"))

    # ---------- 5. + New material zonder library: de herinnering ----------
    check("zonder library geen Browse-knop", page.evaluate("!DATA.materialList"))
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    check("de herinnering staat in het venster, met Get the latest library en Don’t remind me",
          vis("#nmLibHint") and vis("#nmLibGet") and vis("#nmLibOff") and "No materials library loaded" in txt("#nmLibHint"))
    page.fill("#nmName", "Javanol"); page.fill("#nmDil", "10")
    klik("#nmLibGet"); page.wait_for_timeout(1200)
    check("Get the latest library laadt de library zonder het venster te verliezen",
          page.evaluate("!!DATA.materialList") and page.locator("#dlg").evaluate("d => d.open") and page.input_value("#nmName") == "Javanol" and page.input_value("#nmDil") == "10")
    check("en het venster toont nu de suggestie en Browse the library…",
          "Javanol" in (page.text_content("#nmFound") or "") and vis("#nmBrowse") and page.locator("#nmLibHint").count() == 0)
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)   # de library weer weg
    check("Undo neemt de library terug", page.evaluate("!DATA.materialList"))
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    klik("#nmLibOff")
    check("Don’t remind me haalt de herinnering weg en zet een vlag in het databestand",
          page.locator("#nmLibHint").count() == 0 and page.evaluate("DATA.libraryHintOff === true") and "libraryHintOff" in page.evaluate("serialize()"))
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    page.click("#btnNewMat"); page.wait_for_timeout(300)
    check("de volgende keer geen herinnering", page.locator("#nmLibHint").count() == 0)
    page.keyboard.press("Escape"); page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("Undo zet de vlag terug", page.evaluate("DATA.libraryHintOff == null"))
    # Remove the library in Settings zet de vlag ook
    page.evaluate("async () => { setMaterialList(await (await fetch('https://data.miformulas.com/x')).json()); render(); }"); page.wait_for_timeout(400)
    page.click("#btnSettings"); page.wait_for_timeout(400)
    klik("#setListDel"); page.wait_for_timeout(300)
    check("Remove the library in Settings zet de herinnering uit", page.evaluate("!DATA.materialList && DATA.libraryHintOff === true"))
    page.keyboard.press("Control+z"); page.wait_for_timeout(300)
    check("één Undo neemt library en vlag samen terug", page.evaluate("!!DATA.materialList && DATA.libraryHintOff == null"))
    open_m("Geraniol")
    page.evaluate("() => { document.body.classList.add('ro'); }"); page.wait_for_timeout(100)   # na de render: die zet de klasse naar readOnly()
    check("in alleen-lezen verdwijnt ⋯", page.locator("#mMore").count() == 1 and not vis("#mMore"))
    page.evaluate("() => document.body.classList.remove('ro')")

    check("geen fouten op de pagina", not errs)
    if errs: print(errs)
    b.close()

print(f"\n{ok} OK, {fail} FAIL")
raise SystemExit(1 if fail else 0)
